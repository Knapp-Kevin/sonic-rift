"""Speech's take player: transport, playhead and take list behave as users expect."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QPushButton, QSlider  # noqa: E402

from this_voice_thing.ui.pages import player as player_module  # noqa: E402
from this_voice_thing.ui.pages.player import Player, clock, newest_takes  # noqa: E402

APP = QApplication.instance() or QApplication([])
State, Status = QMediaPlayer.PlaybackState, QMediaPlayer.MediaStatus


class FakeMediaPlayer:
    def __init__(self):
        self.state, self.status, self.position, self._source = State.StoppedState, Status.NoMedia, 0, QUrl()
        self.calls = []

    def playbackState(self):
        return self.state

    def mediaStatus(self):
        return self.status

    def source(self):
        return self._source

    def setSource(self, url):
        self._source, self.position, self.status = url, 0, Status.LoadedMedia
        self.calls.append(("source", url.toLocalFile()))

    def setPosition(self, ms):
        self.position = ms
        self.calls.append(("position", ms))

    def play(self):
        self.state = State.PlayingState
        self.calls.append(("play", self.position))

    def pause(self):
        self.state = State.PausedState
        self.calls.append(("pause", self.position))

    def stop(self):
        self.state, self.position = State.StoppedState, 0
        self.calls.append(("stop",))

    def errorString(self):
        return "Unsupported format"


def owner():
    w = SimpleNamespace(media_player=FakeMediaPlayer(), current_audio_file=None, statuses=[])
    w.play_pause_button, w.stop_button = QPushButton("Play"), QPushButton("Stop")
    w.playhead_slider = QSlider()
    w.current_time_label, w.duration_label, w.current_file_label = QLabel(), QLabel(), QLabel()
    w.output_log_listwidget = QListWidget()
    w.set_status_message = w.statuses.append
    for name in ("toggle_play_pause", "stop_audio", "load_take", "play_selected_from_log", "update_output_log",
                 "_set_transport_enabled", "_scrub", "_finish_scrub", "_show_position", "_show_duration",
                 "_show_transport_state", "_report_playback_error"):
        setattr(w, name, MethodType(getattr(Player, name), w))
    return w


class SameFile(unittest.TestCase):
    def test_qt_and_windows_spellings_of_one_path_match(self):
        from this_voice_thing.ui.pages.player import same_file
        path = os.path.join(tempfile.gettempdir(), "Take.wav")
        self.assertTrue(same_file(QUrl.fromLocalFile(path).toLocalFile(), path))
        self.assertFalse(same_file(path, path + "x"))
        self.assertFalse(same_file("", path))


class Clock(unittest.TestCase):
    def test_minutes_and_seconds(self):
        self.assertEqual([clock(0), clock(999), clock(61_000), clock(3_725_000), clock(-5), clock(None)],
                         ["00:00", "00:00", "01:01", "62:05", "00:00", "00:00"])


class Transport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.take = os.path.join(self.tmp.name, "take.wav")
        Path(self.take).write_bytes(b"RIFF")
        self.w = owner()

    def tearDown(self):
        self.tmp.cleanup()

    def test_nothing_loaded_warns_and_does_not_play(self):
        with mock.patch.object(player_module.QMessageBox, "warning") as warning:
            self.w.toggle_play_pause()
        warning.assert_called_once()
        self.assertEqual(self.w.media_player.calls, [])

    def test_load_take_enables_controls_and_autoplays_only_when_asked(self):
        self.w.load_take(self.take, "Last generated: Take")
        self.assertTrue(self.w.play_pause_button.isEnabled() and self.w.playhead_slider.isEnabled())
        self.assertEqual(self.w.media_player.calls, [("source", QUrl.fromLocalFile(self.take).toLocalFile())])
        self.w.load_take(self.take, "Playing: Take", autoplay=True)
        self.assertEqual(self.w.media_player.calls[-1], ("play", 0))
        self.assertEqual(self.w.current_file_label.text(), "Playing: Take")

    def test_pause_then_play_resumes_where_it_was(self):
        self.w.load_take(self.take, "x", autoplay=True)
        self.w.media_player.position = 1500
        self.w.toggle_play_pause()                      # pause
        self.w.toggle_play_pause()                      # resume
        self.assertEqual(self.w.media_player.calls[-2:], [("pause", 1500), ("play", 1500)])

    def test_play_after_the_end_starts_again(self):
        self.w.load_take(self.take, "x", autoplay=True)
        self.w.media_player.state, self.w.media_player.status = State.StoppedState, Status.EndOfMedia
        self.w.media_player.position = 4000
        self.w.toggle_play_pause()
        self.assertEqual(self.w.media_player.calls[-2:], [("position", 0), ("play", 0)])

    def test_a_different_current_take_is_loaded_before_playing(self):
        other = os.path.join(self.tmp.name, "other.wav")
        Path(other).write_bytes(b"RIFF")
        self.w.load_take(self.take, "x")
        self.w.current_audio_file = other               # e.g. Speech made a new take
        self.w.toggle_play_pause()
        self.assertEqual(self.w.media_player.calls[-2:], [("source", QUrl.fromLocalFile(other).toLocalFile()), ("play", 0)])

    def test_stop_and_button_text_follow_the_player(self):
        self.w.load_take(self.take, "x", autoplay=True)
        self.w._show_transport_state(State.PlayingState)
        self.assertEqual(self.w.play_pause_button.text(), "Pause")
        self.w.stop_audio()
        self.w._show_transport_state(State.StoppedState)
        self.assertEqual((self.w.media_player.calls[-1], self.w.play_pause_button.text()), (("stop",), "Play"))

    def test_playback_error_is_reported_and_disables_the_transport(self):
        self.w.load_take(self.take, "x")
        self.w._show_duration(5000)
        with mock.patch.object(player_module.QMessageBox, "warning") as warning:
            self.w._report_playback_error()
        self.assertIn("Unsupported format", warning.call_args[0][2])
        self.assertFalse(self.w.play_pause_button.isEnabled() or self.w.playhead_slider.isEnabled())
        self.assertEqual((self.w.duration_label.text(), self.w.playhead_slider.maximum()), ("00:00", 0))


class Playhead(unittest.TestCase):
    def test_follows_playback_but_not_while_dragged(self):
        w = owner()
        w._show_duration(10_000)
        w._show_position(2_000)
        self.assertEqual((w.playhead_slider.value(), w.current_time_label.text()), (2_000, "00:02"))
        w.playhead_slider.setSliderDown(True)           # the user is dragging
        w.playhead_slider.setValue(7_000)
        w._show_position(2_500)
        self.assertEqual(w.playhead_slider.value(), 7_000)
        w._scrub(7_000)
        w.playhead_slider.setSliderDown(False)
        w._finish_scrub()
        self.assertEqual(w.media_player.calls[-1], ("position", 7_000))
        self.assertEqual(w.current_time_label.text(), "00:07")


class TakeList(unittest.TestCase):
    def test_newest_first_audio_only_and_selection_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            names = ["a.wav", "b.mp3", "notes.txt", "c.wav"]
            for i, name in enumerate(names):
                path = os.path.join(folder, name)
                Path(path).write_bytes(b"x")
                os.utime(path, (time.time() + i, time.time() + i))
            self.assertEqual([os.path.basename(p) for p in newest_takes(folder)], ["c.wav", "b.mp3", "a.wav"])
            self.assertEqual(newest_takes(os.path.join(folder, "missing")), [])
            w = owner()
            w.output_directory = folder
            w.update_output_log()
            w.output_log_listwidget.setCurrentRow(1)
            w.update_output_log()
            self.assertEqual(os.path.basename(w.output_log_listwidget.currentItem().data(256)), "b.mp3")

    def test_activating_a_missing_take_warns_and_refreshes(self):
        with tempfile.TemporaryDirectory() as folder:
            w = owner()
            w.output_directory = folder
            item = SimpleNamespace(data=lambda _role: os.path.join(folder, "gone.wav"), text=lambda: "Take")
            with mock.patch.object(player_module.QMessageBox, "warning") as warning:
                w.play_selected_from_log(item)
            warning.assert_called_once()
            self.assertEqual(w.media_player.calls, [])


if __name__ == "__main__":
    unittest.main()
