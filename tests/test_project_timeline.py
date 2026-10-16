"""Project timeline: waveform envelopes, layout, hit-testing, fades and the preview mix."""

import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from this_voice_thing.core.audio_project import AudioProject, Clip, Track  # noqa: E402
from this_voice_thing.ui.project_timeline import PEAKS_PER_SECOND, TimelineView, envelope, preview_mix  # noqa: E402

RATE = 48000


def project():
    ocean = Clip("ocean", "sound", 0, 60 * RATE, asset_id="sound_abc123abc123", loop=True,
                 fade_in_frames=3 * RATE, fade_out_frames=4 * RATE)
    line = Clip("line", "voice", 4 * RATE, 4 * RATE, asset_id="voice_" + "a" * 64)
    script = Clip("script", "voice", 30 * RATE, 0, text="Breathe in slowly.")
    return AudioProject("p", "Wind-down", tracks=[Track("v", "voice", "Narrator", clips=[line, script]),
                                                   Track("s", "sound", "Ocean", clips=[ocean])])


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


class Envelope(unittest.TestCase):
    def test_rate_and_normalisation(self):
        tone = 0.25 * np.sin(np.linspace(0, 2 * np.pi * 440, 2 * RATE)).astype(np.float32)
        peaks = envelope(tone, RATE)
        self.assertEqual(len(peaks), 2 * PEAKS_PER_SECOND)
        self.assertAlmostEqual(float(peaks.max()), 1.0, places=5)

    def test_stereo_and_silence(self):
        stereo = np.zeros((RATE, 2), dtype=np.float32)
        stereo[:, 1] = 0.5
        self.assertTrue(np.all(envelope(stereo, RATE) == 1.0))
        self.assertTrue(np.all(envelope(np.zeros(RATE, dtype=np.float32), RATE) == 0.0))
        self.assertEqual(len(envelope(np.zeros(3, dtype=np.float32), RATE)), 1)


class View(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def view(self):
        view = TimelineView(lambda clip: clip.text or clip.id)
        view.resize(1000, 200)
        view.set_project(project())
        view.set_peaks("sound_abc123abc123", np.linspace(0, 1, 60 * PEAKS_PER_SECOND, dtype=np.float32))
        view.grab()                       # paints: lanes, clips, waveforms, fades, ruler
        return view

    def test_click_selects_the_clip_under_the_pointer(self):
        from PySide6.QtCore import QPointF
        view = self.view()
        picked = []
        view.clipSelected.connect(picked.append)
        top_lane_middle = view.RULER + view.LANE / 2
        x = view._x(6.0)                  # inside the 4..8 s narration clip
        press(view, x, top_lane_middle)
        self.assertEqual(picked, ["line"])
        self.assertEqual(view.selected, "line")

    def test_ruler_click_seeks(self):
        from PySide6.QtCore import QPointF
        view = self.view()
        sought = []
        view.seekRequested.connect(sought.append)
        press(view, view._x(20.0), 5)
        self.assertAlmostEqual(sought[0], 20.0, places=1)

    def test_script_clip_without_audio_is_drawn_and_clickable(self):
        view = self.view()
        self.assertIn("script", [clip_id for _rect, clip_id in view._hits])

    def test_fade_gain_shape(self):
        clip = project().tracks[1].clips[0]
        self.assertAlmostEqual(TimelineView._fade_gain(clip, 0.0), 0.0)
        self.assertAlmostEqual(TimelineView._fade_gain(clip, 0.025), 0.5, places=2)   # 1.5 s into a 3 s fade
        self.assertAlmostEqual(TimelineView._fade_gain(clip, 0.5), 1.0)
        self.assertLess(TimelineView._fade_gain(clip, 0.99), 0.2)

    def test_empty_project_paints(self):
        view = TimelineView()
        view.resize(600, 120)
        view.set_project(AudioProject("e", "Empty"))
        view.grab()
        self.assertEqual(view._hits, [])


class Preview(unittest.TestCase):
    def test_preview_mix_never_clips_and_matches_the_timeline(self):
        clip = Clip("c", "sound", 0, RATE, asset_id="sound_x1")
        proj = AudioProject("p", "Loud", tracks=[Track("t", "sound", "Loud", clips=[clip])])

        class Media:
            def resolve(self, asset_id):
                return np.full((RATE, 2), 1.5, dtype=np.float32), RATE

        audio, rate = preview_mix(proj, Media(), duck=False)
        self.assertEqual(rate, RATE)
        self.assertEqual(len(audio), RATE)
        self.assertLessEqual(float(np.max(np.abs(audio))), 0.99 + 1e-6)


class EditorWiring(unittest.TestCase):
    def test_editor_hosts_the_timeline_and_waits_for_its_jobs(self):
        source = open(os.path.join(ROOT, "this_voice_thing", "ui", "pages", "project_editor.py"),
                      encoding="utf-8").read()
        self.assertIn("TimelineView(self._clip_label)", source)
        self.assertIn("self.timeline.set_project(project)", source)
        self.assertEqual(source.count("self._finish_quick_jobs()"), 2)   # reject() and closeEvent()


if __name__ == "__main__":
    unittest.main()
