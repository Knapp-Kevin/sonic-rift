"""Timeline drag-to-move and non-destructive trim (#71): model, mixer, session and pointer."""

import json
import os
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from this_voice_thing.core.audio_project import (AudioProject, Clip, Track, from_dict, read_project,  # noqa: E402
                                                 save_project, to_dict)
from this_voice_thing.core.audio_project_session import ProjectSession  # noqa: E402
from this_voice_thing.core.audio_timeline_mix import render_timeline  # noqa: E402

RATE = 48000


def mouse(view, kind, x, y, button=None, buttons=None):
    """Send a real QMouseEvent (press/move/release) to the view."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    left = Qt.MouseButton.LeftButton
    event = QMouseEvent(kind, QPointF(x, y), view.mapToGlobal(QPointF(x, y)),
                        left if button is None else button,
                        left if buttons is None else buttons, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(view, event)


def press(view, x, y):
    from PySide6.QtCore import QEvent
    mouse(view, QEvent.Type.MouseButtonPress, x, y)
    mouse(view, QEvent.Type.MouseButtonRelease, x, y)


def project(loop=False):
    voice = Clip("v1", "voice", 2 * RATE, 2 * RATE, asset_id="voice_" + "a" * 64)
    other = Clip("v2", "voice", 6 * RATE, RATE, asset_id="voice_" + "b" * 64)
    script = Clip("s1", "voice", 9 * RATE, 0, text="Later line.")
    sound = Clip("o1", "sound", 0, 10 * RATE, asset_id="sound_abc", loop=True, fade_in_frames=RATE)
    return AudioProject("p", "Drag", tracks=[Track("tv", "voice", "Narrator", clips=[voice, other, script]),
                                             Track("ts", "sound", "Ocean", clips=[sound])])


class Model(unittest.TestCase):
    def test_offset_saved_only_when_used(self):
        p = project()
        clips = [c for t in to_dict(p)["tracks"] for c in t["clips"]]
        self.assertTrue(all("source_offset_frames" not in c for c in clips))   # earlier builds still read it
        p.tracks[0].clips[0].source_offset_frames = 4800
        data = to_dict(p)
        self.assertEqual(data["tracks"][0]["clips"][0]["source_offset_frames"], 4800)
        self.assertEqual(from_dict(data).tracks[0].clips[0].source_offset_frames, 4800)

    def test_round_trip_on_disk(self):
        p = project()
        p.tracks[0].clips[0].source_offset_frames = 123
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "p.sonicrift.json")
            save_project(path, p)
            self.assertEqual(read_project(path).tracks[0].clips[0].source_offset_frames, 123)
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["tracks"][1]["clips"][0].get("source_offset_frames"), None)

    def test_offset_needs_audio(self):
        script = Clip("s", "voice", 0, 0, text="x", source_offset_frames=10)
        with self.assertRaises(ValueError):
            script.validate()


class Mixer(unittest.TestCase):
    def resolve(self, asset_id):
        ramp = np.arange(4 * RATE, dtype=np.float32) / (4 * RATE)       # sample i holds i / N
        return np.stack([ramp, ramp], axis=1), RATE

    def test_trimmed_start_skips_source_frames(self):
        clip = Clip("c", "sound", 0, RATE, asset_id="sound_x", source_offset_frames=RATE)
        p = AudioProject("p", "T", tracks=[Track("t", "sound", "S", clips=[clip])])
        mix = render_timeline(p, self.resolve)
        self.assertAlmostEqual(float(mix.stems["t"][0, 0]), RATE / (4 * RATE), places=5)

    def test_trim_past_the_audio_is_refused(self):
        clip = Clip("c", "sound", 0, 2 * RATE, asset_id="sound_x", source_offset_frames=3 * RATE)
        p = AudioProject("p", "T", tracks=[Track("t", "sound", "S", clips=[clip])])
        with self.assertRaises(ValueError):
            render_timeline(p, self.resolve)

    def test_looped_source_wraps_from_the_offset(self):
        clip = Clip("c", "sound", 0, 2 * RATE, asset_id="sound_x", loop=True, source_offset_frames=3 * RATE)
        p = AudioProject("p", "T", tracks=[Track("t", "sound", "S", clips=[clip])])
        stem = render_timeline(p, self.resolve).stems["t"][:, 0]
        self.assertAlmostEqual(float(stem[0]), 0.75, places=4)          # starts 3 s in
        self.assertAlmostEqual(float(stem[RATE]), 0.0, places=4)        # wrapped to the start


class Session(unittest.TestCase):
    def test_place_clip_is_one_undoable_edit(self):
        s = ProjectSession(project())
        before = s.project.revision
        self.assertTrue(s.place_clip("v1", 3 * RATE, RATE, RATE // 2))
        clip = s.project.tracks[0].clips[0]
        self.assertEqual((clip.start_frame, clip.frame_count, clip.source_offset_frames), (3 * RATE, RATE, RATE // 2))
        self.assertEqual(s.project.revision, before + 1)
        s.undo()
        clip = s.project.tracks[0].clips[0]
        self.assertEqual((clip.start_frame, clip.frame_count, clip.source_offset_frames), (2 * RATE, 2 * RATE, 0))
        s.redo()
        self.assertEqual(s.project.tracks[0].clips[0].source_offset_frames, RATE // 2)

    def test_dropping_a_clip_where_it_was_changes_nothing(self):
        s = ProjectSession(project())
        revision = s.project.revision
        self.assertFalse(s.place_clip("v1", 2 * RATE, 2 * RATE, 0))
        self.assertEqual(s.project.revision, revision)                   # not "unsaved"
        self.assertFalse(s.can_undo)

    def test_limits(self):
        s = ProjectSession(project())
        for bad in ((-1, RATE, 0), (0, 0, 0), (0, RATE, -5), (0.5, RATE, 0)):
            with self.assertRaises(ValueError):
                s.place_clip("v1", *bad)
        with self.assertRaises(ValueError):
            s.place_clip("s1", 0, RATE, 0)                               # scripts have no audio to trim

    def test_fades_shrink_with_the_clip(self):
        s = ProjectSession(project())
        s.place_clip("o1", 0, RATE // 2, 0)
        self.assertEqual(s.project.tracks[1].clips[0].fade_in_frames, RATE // 2)

    def test_new_take_or_new_script_clears_a_trim(self):
        s = ProjectSession(project())
        s.place_clip("v1", 2 * RATE, RATE, RATE)
        s.attach_narration_take("v1", "voice_" + "c" * 64, 3 * RATE)
        self.assertEqual(s.project.tracks[0].clips[0].source_offset_frames, 0)
        s.place_clip("v1", 2 * RATE, RATE, RATE)
        s.update_narration_text("v1", "A new script.")
        self.assertEqual(s.project.tracks[0].clips[0].source_offset_frames, 0)

    def test_identity_and_neighbours_untouched(self):
        s = ProjectSession(project())
        s.place_clip("v1", 6 * RATE, RATE, 0)                            # now overlaps v2 on the same track
        ids = [c.id for c in s.project.tracks[0].clips]
        self.assertEqual(ids, ["v1", "v2", "s1"])
        v2 = s.project.tracks[0].clips[1]
        self.assertEqual((v2.start_frame, v2.frame_count), (6 * RATE, RATE))


class Pointer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def view(self, loop_source=None):
        from this_voice_thing.ui.project_timeline import TimelineView
        view = TimelineView(lambda clip: clip.id)
        view.resize(1200, 200)
        view.set_project(project())
        view.set_peaks("voice_" + "a" * 64, np.ones(200, dtype=np.float32), 4 * RATE)   # 4 s source
        view.set_peaks("voice_" + "b" * 64, np.ones(50, dtype=np.float32), RATE)
        view.set_peaks("sound_abc", np.ones(500, dtype=np.float32), 10 * RATE)
        view.grab()
        placed = []
        view.clipPlaced.connect(lambda *args: placed.append(args))
        return view, placed

    def lane_y(self, view, index):
        return view.RULER + index * view.LANE + view.LANE / 2

    def rect(self, view, clip_id):
        return next(r for r, cid in view._hits if cid == clip_id)

    def drag(self, view, x0, y, x1, *, finish=True):
        from PySide6.QtCore import QEvent, Qt
        mouse(view, QEvent.Type.MouseButtonPress, x0, y)
        mouse(view, QEvent.Type.MouseMove, (x0 + x1) / 2, y, button=Qt.MouseButton.NoButton)
        mouse(view, QEvent.Type.MouseMove, x1, y, button=Qt.MouseButton.NoButton)
        if finish:
            mouse(view, QEvent.Type.MouseButtonRelease, x1, y, buttons=Qt.MouseButton.NoButton)

    def test_move(self):
        view, placed = self.view()
        r = self.rect(view, "v1")
        fpp = view._frames_per_pixel()
        self.drag(view, r.center().x(), self.lane_y(view, 0), r.center().x() + 100)
        (clip_id, start, count, offset), = placed
        self.assertEqual((clip_id, count, offset), ("v1", 2 * RATE, 0))
        self.assertEqual(start, 2 * RATE + round(100 * fpp))
        self.assertTrue(all(type(v) is int for v in (start, count, offset)))

    def test_move_stops_at_zero(self):
        view, placed = self.view()
        r = self.rect(view, "v1")
        self.drag(view, r.center().x(), self.lane_y(view, 0), view.HEADER - 300)
        self.assertEqual(placed[0][1], 0)

    def test_trim_start_keeps_the_end_and_skips_source(self):
        view, placed = self.view()
        r = self.rect(view, "v1")
        fpp = view._frames_per_pixel()
        self.drag(view, r.left() + 2, self.lane_y(view, 0), r.left() + 42)
        (_, start, count, offset), = placed
        d = round(40 * fpp)
        self.assertEqual((start, count, offset), (2 * RATE + d, 2 * RATE - d, d))
        self.assertEqual(start + count, 4 * RATE)                        # the end didn't move

    def test_trim_start_cannot_reach_before_the_audio(self):
        view, placed = self.view()
        r = self.rect(view, "v1")
        self.drag(view, r.left() + 2, self.lane_y(view, 0), r.left() - 80)   # offset is 0: nothing to reveal
        self.assertEqual(placed, [])

    def test_trim_end_stops_at_the_end_of_the_audio(self):
        view, placed = self.view()
        r = self.rect(view, "v1")
        self.drag(view, r.right() - 2, self.lane_y(view, 0), r.right() + 400)
        self.assertEqual(placed[0][2], 4 * RATE)                         # source is 4 s long

    def test_trim_has_a_minimum_length(self):
        view, placed = self.view()
        r = self.rect(view, "v1")
        self.drag(view, r.right() - 2, self.lane_y(view, 0), r.left() - 50)
        self.assertEqual(placed[0][2], round(view.MIN_CLIP_SECONDS * RATE))

    def test_looping_sound_can_be_stretched(self):
        view, placed = self.view()
        r = self.rect(view, "o1")
        self.drag(view, r.right() - 2, self.lane_y(view, 1), r.right() + 30)
        self.assertGreater(placed[0][2], 10 * RATE)

    def test_escape_and_right_click_cancel(self):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtTest import QTest
        view, placed = self.view()
        r = self.rect(view, "v1")
        y = self.lane_y(view, 0)
        self.drag(view, r.center().x(), y, r.center().x() + 120, finish=False)
        QTest.keyClick(view, Qt.Key.Key_Escape)
        mouse(view, QEvent.Type.MouseButtonRelease, r.center().x() + 120, y, buttons=Qt.MouseButton.NoButton)
        self.drag(view, r.center().x(), y, r.center().x() + 120, finish=False)
        mouse(view, QEvent.Type.MouseButtonPress, r.center().x() + 120, y, button=Qt.MouseButton.RightButton,
              buttons=Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        mouse(view, QEvent.Type.MouseButtonRelease, r.center().x() + 120, y, buttons=Qt.MouseButton.NoButton)
        self.assertEqual(placed, [])
        self.assertIsNone(view._drag)

    def test_click_without_moving_places_nothing(self):
        view, placed = self.view()
        r = self.rect(view, "v1")
        press(view, r.center().x(), self.lane_y(view, 0))
        self.assertEqual(placed, [])

    def test_scale_holds_still_while_dragging_past_the_end(self):
        view, placed = self.view()
        total = view.total_seconds()
        r = self.rect(view, "o1")
        self.drag(view, r.center().x(), self.lane_y(view, 1), r.center().x() + 2000, finish=False)
        self.assertEqual(view.total_seconds(), total)
        shown = view._shown(view._clip("o1"))
        self.assertGreater(shown.start_frame, 0)                         # the preview moved with the pointer

    def test_script_clip_moves_but_does_not_trim(self):
        view, placed = self.view()
        r = self.rect(view, "s1")
        self.drag(view, r.left() + 2, self.lane_y(view, 0), r.left() + 60)
        (clip_id, start, count, offset), = placed
        self.assertEqual((clip_id, count, offset), ("s1", 0, 0))
        self.assertGreater(start, 9 * RATE)

    def test_overlapping_clips_pick_the_one_drawn_on_top(self):
        from this_voice_thing.ui.project_timeline import TimelineView
        p = project()
        p.tracks[0].clips[1].start_frame = 2 * RATE                       # v2 now sits on top of v1
        view = TimelineView()
        view.resize(1200, 200)
        view.set_project(p)
        view.grab()
        point_x = view._x(2.5)
        from PySide6.QtCore import QPointF
        self.assertEqual(view._clip_at(QPointF(point_x, self.lane_y(view, 0))), "v2")


if __name__ == "__main__":
    unittest.main()
