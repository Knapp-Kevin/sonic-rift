"""The Studio: the project editor as a page of the main window, where output from Speech and
Sounds comes together; plus the status bar keeping whole messages when the window grows."""

import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

sys.argv = ["main.py"]


class StudioPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from this_voice_thing import paths
        from this_voice_thing.ui import main_window
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = tempfile.mkdtemp()
        with patch.object(paths, "ROOT", cls.tmp), \
                patch.object(main_window.SonicRiftApp, "start_default_model_load", lambda self: None), \
                patch.object(main_window.SonicRiftApp, "restart_api_server", lambda self: None):
            cls.window = main_window.SonicRiftApp()
        cls.window.output_directory = cls.tmp

    @classmethod
    def tearDownClass(cls):
        editor = getattr(cls.window, "project_editor", None)
        if editor is not None:
            editor._mark_clean()
        cls.window.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def pump(self, condition, timeout=10):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(0.01)
        return False

    def test_the_editor_is_a_page_not_a_window(self):
        w = self.window
        editor = w.open_project_editor()
        self.assertEqual(w.pages.currentIndex(), w.PAGE_PROJECT)
        self.assertFalse(editor.isWindow())
        self.assertTrue(w.pages.widget(w.PAGE_PROJECT).isAncestorOf(editor))
        self.assertIs(w.open_project_editor(), editor)               # one Studio

    def test_the_sidebar_opens_a_working_studio(self):
        w = self.window
        w.show_page(w.PAGE_PROJECT)
        self.assertIsNotNone(getattr(w, "project_editor", None))
        self.assertTrue(w.pages.widget(w.PAGE_PROJECT).isAncestorOf(w.project_editor))

    def test_esc_does_not_close_the_studio(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        w = self.window
        editor = w.open_project_editor()
        QTest.keyClick(editor, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertIs(w.project_editor, editor)
        self.assertFalse(editor.isHidden())

    def test_unsaved_studio_edits_are_asked_about_even_from_another_page(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        editor = w.open_project_editor()
        editor.session.add_track("sound", "Ambience")
        editor.refresh()
        w.show_page(w.PAGE_GENERATE)                                   # Studio not showing
        asked = []
        with patch.object(QMessageBox, "question",
                          lambda *a, **k: (asked.append(a[2]), QMessageBox.StandardButton.No)[1]):
            self.assertFalse(w.close_project_editor())
        self.assertTrue(asked)
        self.assertIs(w.project_editor, editor)
        editor.undo()
        editor._mark_clean()

    def test_speech_take_goes_to_the_studio(self):
        w = self.window
        path = os.path.join(self.tmp, "take.wav")
        t = np.arange(24000) / 24000
        sf.write(path, (0.2 * np.sin(2 * np.pi * 220 * t)).astype("float32"), 24000)
        w.current_audio_file = path
        w.take_texts = {os.path.abspath(path): "Breathe in slowly."}     # what Speech rendered
        w.speech_takes_list.clear()
        w.add_take_to_studio()
        editor = w.project_editor
        self.assertEqual(w.pages.currentIndex(), w.PAGE_PROJECT)
        self.assertTrue(self.pump(lambda: editor.import_worker is None))
        clips = [c for t in editor.session.project.tracks for c in t.clips]
        self.assertEqual(len(clips), 1)
        self.assertEqual((clips[0].kind, clips[0].frame_count), ("voice", 48000))
        self.assertEqual(clips[0].text, "Breathe in slowly.")             # the clip shows its words
        # A second take joins the same Narration track, one second after the first (not on top of it)
        editor.tree.setCurrentItem(None)
        w.add_take_to_studio()
        self.assertTrue(self.pump(lambda: editor.import_worker is None))
        tracks = [t for t in editor.session.project.tracks if t.kind == "voice"]
        self.assertEqual([t.name for t in tracks], ["Narration"])
        self.assertEqual([c.start_frame for c in tracks[0].clips], [0, 48000 + 48000])
        editor.undo()
        editor.undo()
        editor._mark_clean()

    def test_music_gets_its_own_track_even_with_the_waves_selected(self):
        from this_voice_thing.core.audio_project import AudioProject
        from this_voice_thing.core.audio_project_session import ProjectSession
        w = self.window
        editor = w.open_project_editor()
        previous = editor.session
        editor.session = ProjectSession(AudioProject("scene", "Evening Tide"))
        editor.refresh()
        self.addCleanup(lambda: (setattr(editor, "session", previous), editor.refresh(), editor._mark_clean()))
        rate = 48000
        hush = np.zeros((rate, 2), dtype="float32")
        waves = w.sound_library.add(hush, rate, "Shoreline waves", "procedural", True)
        surf = w.sound_library.add(hush, rate, "Surf", "procedural", True)
        theme = w.sound_library.add(hush, rate, "Harbor light", "ace_step_15", False, kind="music")
        coda = w.sound_library.add(hush, rate, "Coda", "ace_step_15", False, kind="music")

        def add(asset, select_track=None):
            if select_track is not None:
                track = next(t for t in editor.session.project.tracks if t.name == select_track)
                self._select_track(editor, track.id)
            editor.add_sound(asset)
            self.assertTrue(self.pump(lambda: editor.import_worker is None))

        def lanes():
            return {t.name: [c.asset_id for c in t.clips] for t in editor.session.project.tracks}

        add(waves)
        add(theme, select_track="Shoreline waves")        # music doesn't stack on the waves
        self.assertEqual(lanes(), {"Shoreline waves": ["sound_" + waves.id], "Harbor light": ["sound_" + theme.id]})
        add(coda, select_track="Harbor light")            # more music joins the selected music track
        add(surf, select_track="Shoreline waves")         # more ambience joins the waves
        self.assertEqual(lanes(), {"Shoreline waves": ["sound_" + waves.id, "sound_" + surf.id],
                                   "Harbor light": ["sound_" + theme.id, "sound_" + coda.id]})
        add(waves, select_track="Harbor light")           # ambience doesn't stack on the music either
        self.assertEqual(len(editor.session.project.tracks), 3)

    def test_levels_panel_balances_tracks_and_checks_the_balance(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from this_voice_thing.core.audio_project import AudioProject
        from this_voice_thing.core.audio_project_session import ProjectSession
        w = self.window
        editor = w.open_project_editor()
        previous = editor.session
        editor.session = ProjectSession(AudioProject("scene", "Evening Tide"))
        editor.refresh()
        self.addCleanup(lambda: (setattr(editor, "session", previous), editor.refresh(), editor._mark_clean()))
        rate = 48000
        t = np.arange(6 * rate) / rate
        bed = np.stack([0.3 * np.sin(2 * np.pi * 330 * t)] * 2, axis=1).astype("float32")
        music = w.sound_library.add(bed, rate, "Cello theme", "ace_step_15", False, kind="music")
        path = os.path.join(self.tmp, "line.wav")
        line = np.concatenate([np.zeros(rate), 0.3 * np.sin(2 * np.pi * 220 * t[:2 * rate])]).astype("float32")
        sf.write(path, line, rate)
        editor.add_voice_take(path)
        self.assertTrue(self.pump(lambda: editor.import_worker is None))
        editor.tree.setCurrentItem(None)
        editor.add_sound(music)
        self.assertTrue(self.pump(lambda: editor.import_worker is None))
        tracks = editor.session.project.tracks
        voice, theme = tracks[0], tracks[1]
        panel = editor.levels
        self.assertEqual(set(panel.rows), {voice.id, theme.id})

        # Dragging the music slider: nothing changes until release, then one undo step
        slider = panel.rows[theme.id]["slider"]
        revision = editor.session.project.revision
        slider.setSliderDown(True)
        slider.setValue(round(-14 / 0.5))
        self.assertEqual(editor.session.project.revision, revision)
        self.assertEqual(panel.rows[theme.id]["value"].text(), "−14.0 dB")
        slider.setSliderDown(False)
        slider.sliderReleased.emit()
        self.assertEqual(editor.session.project.tracks[1].gain_db, -14.0)
        self.assertEqual(editor.session.project.revision, revision + 1)
        editor.undo()
        self.assertEqual(editor.session.project.tracks[1].gain_db, 0.0)
        self.assertEqual(slider.value(), 0)                       # the slider follows undo
        editor.redo()
        QTest.keyClick(slider, Qt.Key.Key_Left)                   # keys commit at once, 0.5 dB a step
        self.assertEqual(editor.session.project.tracks[1].gain_db, -14.5)

        panel.rows[theme.id]["mute"].setChecked(True)
        self.assertTrue(editor.session.project.tracks[1].muted)
        panel.rows[theme.id]["mute"].setChecked(False)
        panel.duck_slider.setValue(round(-16 / 0.5))
        self.assertEqual(editor.session.project.duck_db, -16.0)
        self.assertEqual(panel.duck_value.text(), "−16 dB")

        panel.check_button.click()
        self.assertTrue(self.pump(lambda: editor.balance_worker is None, timeout=30))
        readout = panel.rows[theme.id]["readout"].text()
        self.assertIn("dB under the voices", readout)
        gap = float(readout.split(" dB")[0])
        self.assertAlmostEqual(gap, 14.5 + 16.0, delta=1.5)        # track gain + ducking, same-level sources
        self.assertIn("Voices speak for 2.0 s", panel.summary.text())
        panel.duck_slider.setValue(round(-10 / 0.5))             # any edit makes the readout stale
        self.assertEqual(panel.rows[theme.id]["readout"].text(), "")
        self.assertIn("Check balance again", panel.summary.text())

    @staticmethod
    def _select_track(editor, track_id):
        from PySide6.QtCore import Qt
        for i in range(editor.tree.topLevelItemCount()):
            item = editor.tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == ("track", track_id):
                editor.tree.setCurrentItem(item)
                return
        raise LookupError(track_id)

    def test_the_export_note_names_the_folder_not_the_home_path(self):
        from PySide6.QtWidgets import QMessageBox
        editor = self.window.open_project_editor()
        with patch.object(QMessageBox, "information", lambda *a, **k: None):
            editor._export_done(os.path.join("C:\\", "Users", "someone", "Exports", "Evening Tide", "master.wav"), "")
        self.assertIn("Evening Tide", editor.note.text())
        self.assertNotIn("someone", editor.note.text())
        self.assertIn("someone", editor.note.toolTip())

    def test_sounds_needs_a_selection(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.window
        shown = []
        with patch.object(QMessageBox, "information", lambda *a, **k: shown.append(a[2])):
            w.sound_asset_list.setCurrentItem(None)
            w.add_sound_to_studio()
        self.assertIn("Select a sound", shown[-1])

    def test_picking_a_saved_sound_shows_names_not_ids(self):
        source = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "this_voice_thing", "ui", "pages", "project_editor.py"), encoding="utf-8").read()
        self.assertNotIn('f"{a.name}  |  {a.id}"', source)


class TakeNames(unittest.TestCase):
    def test_generated_files_get_readable_names(self):
        from this_voice_thing.ui.pages.player import take_label
        self.assertEqual(take_label("chatterbox_20261030_024505_seed903277_full_stitched.wav"),
                         "Take · 30 Oct, 02:45:05")
        self.assertEqual(take_label("chatterbox_20261030_024505_seed1_partial.mp3"),
                         "Take · 30 Oct, 02:45:05 · stopped early · MP3")
        self.assertEqual(take_label("Chapter one_20261030_024505_seed7.wav"), "Chapter one · 30 Oct, 02:45:05")
        self.assertEqual(take_label("ocean.wav"), "ocean.wav")


class TakeHistoryRefinement(unittest.TestCase):
    def test_same_second_takes_have_stable_distinct_labels(self):
        from this_voice_thing.ui.pages.player import history_take_labels
        one = "C:/audio/chatterbox_20261030_030738_seed111_full_stitched.wav"
        two = "C:/audio/chatterbox_20261030_030738_seed222_full_stitched.wav"
        labels = history_take_labels([two, one])
        self.assertNotEqual(labels[one], labels[two])
        self.assertEqual(labels[one], "Take · 30 Oct, 03:07:38 · variation 1/2")
        self.assertEqual(labels[two], "Take · 30 Oct, 03:07:38 · variation 2/2")
        self.assertEqual(history_take_labels([one, two]), labels)
        self.assertEqual(history_take_labels([one])[one], "Take · 30 Oct, 03:07:38")

    def test_other_files_and_formats_keep_readable_names(self):
        from this_voice_thing.ui.pages.player import history_take_labels
        one = "ocean.wav"
        two = "chatterbox_20261030_030738_seed55_partial.mp3"
        labels = history_take_labels([one, two])
        self.assertEqual(labels[one], "ocean.wav")
        self.assertEqual(labels[two], "Take · 30 Oct, 03:07:38 · stopped early · MP3")

    def test_refresh_preserves_user_selection_and_unique_rows(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from this_voice_thing import paths
        from this_voice_thing.ui import main_window
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(paths, "ROOT", tmp), \
                    patch.object(main_window.SonicRiftApp, "start_default_model_load", lambda self: None), \
                    patch.object(main_window.SonicRiftApp, "restart_api_server", lambda self: None):
                w = main_window.SonicRiftApp()
            try:
                one = os.path.join(tmp, "chatterbox_20261030_030738_seed111_full_stitched.wav")
                two = os.path.join(tmp, "chatterbox_20261030_030738_seed222_full_stitched.wav")
                for path in (one, two):
                    with open(path, "wb") as audio:
                        audio.write(b"unused test fixture")
                w.output_directory = tmp
                w.update_output_log()
                self.assertEqual(w.speech_takes_list.count(), 2)
                self.assertNotEqual(w.speech_takes_list.item(0).text(),
                                    w.speech_takes_list.item(1).text())
                w.speech_takes_list.setCurrentRow(1)
                selected = w.speech_takes_list.currentItem().data(Qt.ItemDataRole.UserRole)
                w.update_output_log()
                self.assertEqual(w.speech_takes_list.currentItem().data(
                    Qt.ItemDataRole.UserRole), selected)
            finally:
                w.close()
                app.processEvents()

    def test_add_to_studio_prefers_newest_visible_take_when_nothing_selected(self):
        from unittest.mock import Mock
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication, QListWidgetItem
        from this_voice_thing import paths
        from this_voice_thing.ui import main_window
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(paths, "ROOT", tmp), \
                    patch.object(main_window.SonicRiftApp, "start_default_model_load", lambda self: None), \
                    patch.object(main_window.SonicRiftApp, "restart_api_server", lambda self: None):
                w = main_window.SonicRiftApp()
            try:
                latest = os.path.join(tmp, "latest.wav")
                stale = os.path.join(tmp, "stale.wav")
                for path in (latest, stale):
                    with open(path, "wb") as audio:
                        audio.write(b"not decoded by this test")
                w.current_audio_file = stale
                w.speech_takes_list.clear()
                for path in (latest, stale):
                    row = QListWidgetItem(os.path.basename(path))
                    row.setData(Qt.ItemDataRole.UserRole, path)
                    w.speech_takes_list.addItem(row)
                w.speech_takes_list.setCurrentRow(-1)  # explicitly clear selection
                editor = Mock()
                with patch.object(w, "open_project_editor", return_value=editor):
                    w.add_take_to_studio()
                editor.add_voice_take.assert_called_once_with(latest, text="")
            finally:
                w.close()
                app.processEvents()


class ClosingDuringDiscovery(unittest.TestCase):
    def test_close_waits_for_a_running_hugging_face_search(self):
        """Closing while Models' search ran destroyed a running QThread: exit code 127."""
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "this_voice_thing", "ui", "main_window.py"), encoding="utf-8").read()
        close = src[src.index("def closeEvent"):]
        self.assertIn('discover = getattr(self, "discover_thread", None)', close)
        self.assertIn("discover.wait(", close)


class StatusBarKeepsWholeMessages(unittest.TestCase):
    def test_a_message_cut_short_is_shown_whole_when_the_bar_grows(self):
        from PySide6.QtWidgets import QApplication
        from this_voice_thing import paths
        from this_voice_thing.ui import main_window
        QApplication.instance() or QApplication([])
        tmp = tempfile.mkdtemp()
        try:
            with patch.object(paths, "ROOT", tmp), \
                    patch.object(main_window.SonicRiftApp, "start_default_model_load", lambda self: None), \
                    patch.object(main_window.SonicRiftApp, "restart_api_server", lambda self: None):
                w = main_window.SonicRiftApp()
            from PySide6.QtCore import Qt
            w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)   # resize events need a shown window
            w.show()
            QApplication.processEvents()
            message = "Kokoro voices is ready on the GPU, and this sentence is long enough to be cut short."
            w.resize(w.minimumWidth(), w.height())
            QApplication.processEvents()
            w.set_status_message(message * 3)
            self.assertNotEqual(w.status_bar.text(), message * 3)
            w.resize(2600, w.height())
            QApplication.processEvents()
            message = message * 3
            self.assertEqual(w.status_bar.text(), message)
            w.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
