"""Regressions from the Live Voice integration review: busy checks, stale frames after Stop,
close order, soundboard recovery, API error connections, VoxCPM2 step-aware pad caches."""

import http.client
import json
import os
import socket
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from this_voice_thing.core.soundboard import SoundboardStore  # noqa: E402
from this_voice_thing.integrations.local_api import LocalApiServer  # noqa: E402
from this_voice_thing.ui.pages.live_voice import LiveVoicePage  # noqa: E402
from this_voice_thing.ui.pages.models import ModelPage  # noqa: E402


class BusyChecks(unittest.TestCase):
    def window(self, **flags):
        values = dict(model_is_loading=False, is_generating=False, api_busy=False, studio_busy=False,
                      live_voice_busy=False, speak_thread=None)
        values.update(flags)
        return SimpleNamespace(**values)

    def test_live_counts_as_model_busy_for_other_features(self):
        self.assertFalse(ModelPage.model_busy(self.window()))
        self.assertTrue(ModelPage.model_busy(self.window(live_voice_busy=True)))
        running = mock.Mock(isRunning=mock.Mock(return_value=True))
        self.assertTrue(ModelPage.model_busy(self.window(speak_thread=running)))

    def test_live_waits_for_the_studio_and_hear_it_but_not_itself(self):
        busy = LiveVoicePage.model_busy_outside_live
        self.assertFalse(busy(self.window(live_voice_busy=True)))   # lines still queue while speaking
        self.assertTrue(busy(self.window(studio_busy=True)))
        running = mock.Mock(isRunning=mock.Mock(return_value=True))
        self.assertTrue(busy(self.window(speak_thread=running)))


class StaleFrames(unittest.TestCase):
    def test_frame_from_a_stopped_thread_is_dropped(self):
        output = mock.Mock()
        stopped = mock.Mock(stop_requested=mock.Mock(return_value=True))
        window = SimpleNamespace(live_speech_thread=stopped, live_voice_current=None, live_audio_output=output,
                                 live_monitor_output=mock.Mock(route_description=mock.Mock(return_value="")))
        window.on_live_frame = lambda frame: LiveVoicePage.on_live_frame(window, frame)
        frame = SimpleNamespace(pcm=b"\0\0", sample_rate=24000)
        LiveVoicePage.on_live_speech_frame(window, frame)
        output.push.assert_not_called()
        window.live_speech_thread = None
        LiveVoicePage.on_live_speech_frame(window, frame)
        output.push.assert_not_called()

    def test_microphone_frames_play_with_no_speech_thread(self):
        """Regression: the stale-frame guard once dropped every Mic Effects frame."""
        output = mock.Mock()
        mic = mock.Mock(is_active=mock.Mock(return_value=True))
        window = SimpleNamespace(live_speech_thread=None, live_voice_current=None, live_audio_output=output,
                                 live_mic_input=mic,
                                 live_monitor_output=mock.Mock(route_description=mock.Mock(return_value="")))
        window.on_live_frame = lambda frame: LiveVoicePage.on_live_frame(window, frame)
        LiveVoicePage.on_live_mic_frame(window, SimpleNamespace(pcm=b"\1\0", sample_rate=48000))
        output.push.assert_called_once_with(b"\1\0")


class CloseOrder(unittest.TestCase):
    def test_settings_are_saved_before_waiting_for_live_speech(self):
        with open(os.path.join(ROOT, "this_voice_thing", "ui", "main_window.py"), encoding="utf-8") as handle:
            source = handle.read()
        close = source[source.index("def closeEvent"):]
        self.assertLess(close.index("self.save_app_settings()"), close.index("self.live_speech_thread.wait()"))


class SoundboardRecovery(unittest.TestCase):
    def test_corrupt_boards_file_is_kept_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SoundboardStore(folder)
            with open(store.index_path, "w", encoding="utf-8") as handle:
                handle.write('{"boards": [ broken')
            reloaded = SoundboardStore(folder)
            backups = [n for n in os.listdir(reloaded.dir) if ".corrupt-" in n]
            self.assertEqual(len(backups), 1)
            with open(os.path.join(reloaded.dir, backups[0]), encoding="utf-8") as handle:
                self.assertIn("broken", handle.read())
            self.assertTrue(reloaded.boards)   # a usable board to carry on with

    def test_non_object_json_does_not_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            store = SoundboardStore(folder)
            with open(store.index_path, "w", encoding="utf-8") as handle:
                json.dump(["not", "an", "object"], handle)
            self.assertTrue(SoundboardStore(folder).boards)


class _Backend:
    def health(self):
        return {"status": "ready"}


class ApiErrors(unittest.TestCase):
    def test_error_before_the_body_closes_the_connection(self):
        server = LocalApiServer(_Backend(), port=0, log=lambda _m: None)
        server.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
            connection.request("POST", "/v1/audio/speech", body=b"x" * 10,
                               headers={"Content-Type": "application/json", "Content-Length": str(64 * 2**20)})
            response = connection.getresponse()
            self.assertEqual(response.status, 413)
            self.assertEqual((response.getheader("Connection") or "").lower(), "close")
            response.read()
            connection.close()
        finally:
            server.stop()

    def test_handler_times_out_stalled_clients(self):
        from this_voice_thing.integrations import local_api
        self.assertTrue(0 < local_api._Handler.timeout <= 60)
        self.assertIsInstance(socket.getdefaulttimeout() or 0, (int, float))


class PadCacheSteps(unittest.TestCase):
    def test_voxcpm_pad_key_follows_the_live_step_setting_without_a_model(self):
        combo = mock.Mock()
        window = SimpleNamespace(
            voice_library=mock.Mock(get=mock.Mock(return_value=None)),
            pronunciations=SimpleNamespace(enabled=False, rules=[]),
            live_voxcpm_steps_combo=combo, model=None)
        window._soundboard_pronunciation_fingerprint = lambda: []
        pad = SimpleNamespace(voice_id="", temperature=0.8, exaggeration=0.5, cfg_weight=0.5,
                              repetition_penalty=1.2, min_p=0.05, top_p=1.0, model_backend="voxcpm")
        combo.currentData.return_value = "low_latency"
        six = LiveVoicePage._soundboard_synthesis_context(window, pad)["live_steps"]
        combo.currentData.return_value = "full"
        ten = LiveVoicePage._soundboard_synthesis_context(window, pad)["live_steps"]
        self.assertEqual((six, ten), (6, 10))
        pad.model_backend = "kokoro"
        self.assertIsNone(LiveVoicePage._soundboard_synthesis_context(window, pad)["live_steps"])



class PadSpeaker(unittest.TestCase):
    def test_speaker_persists_and_is_part_of_the_cache_key(self):
        from this_voice_thing.core.soundboard import Pad
        with tempfile.TemporaryDirectory() as folder:
            store = SoundboardStore(folder)
            pad = store.add_pad(Pad(label="Hi", text="Hello there.", speaker="af_heart", model_backend="kokoro"))
            self.assertEqual(SoundboardStore(folder).get_pad(pad.id).speaker, "af_heart")
        heart = SoundboardStore.cache_digest(Pad(label="a", text="t", speaker="af_heart"), {})
        bella = SoundboardStore.cache_digest(Pad(label="a", text="t", speaker="af_bella"), {})
        self.assertNotEqual(heart, bella)

    def test_pads_without_a_speaker_keep_their_old_cache_key(self):
        from this_voice_thing.core import soundboard
        pad = soundboard.Pad(label="a", text="t")
        payload = {"schema_version": soundboard.SCHEMA_VERSION, "pad": {
            k: getattr(pad, k) for k in ("kind", "text", "voice_id", "model_repo_id", "model_backend", "model_mode",
                                         "language", "style", "temperature", "exaggeration", "cfg_weight",
                                         "repetition_penalty", "min_p", "top_p")}, "synthesis": {}}
        import hashlib
        old = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                        separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(SoundboardStore.cache_digest(pad, {}), old)

    def test_rebuild_needs_the_pads_own_built_in_voice(self):
        page = mock.Mock()
        page.loaded_entry.return_value = {"repo_id": "hexgrad/Kokoro-82M", "backend": "kokoro"}
        page.active_qwen_model.return_value = mock.Mock(speakers=["af_heart", "af_bella"])
        page.qwen_instruct_input.text.return_value = ""
        page.active_voice_id = None
        page.language_combo.currentData.return_value = "en"
        for name in ("temp_slider", "exaggeration_slider", "cfg_slider"):
            getattr(page, name).get_value.return_value = 0.5
        page.repetition_penalty, page.min_p, page.top_p = 1.2, 0.05, 1.0
        page._current_model_speaker = lambda: "af_bella"
        pad = SimpleNamespace(voice_id="", speaker="af_heart", model_repo_id="hexgrad/Kokoro-82M",
                              model_backend="kokoro", model_mode="", language="en", style="", temperature=0.5,
                              exaggeration=0.5, cfg_weight=0.5, repetition_penalty=1.2, min_p=0.05, top_p=1.0)
        self.assertFalse(LiveVoicePage._current_context_matches_pad(page, pad))
        page._current_model_speaker = lambda: "af_heart"
        self.assertTrue(LiveVoicePage._current_context_matches_pad(page, pad))
        pad.speaker = ""                      # saved before speakers were recorded
        page._current_model_speaker = lambda: "af_bella"
        self.assertTrue(LiveVoicePage._current_context_matches_pad(page, pad))


if __name__ == "__main__":
    unittest.main()
