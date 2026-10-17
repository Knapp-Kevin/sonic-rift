"""Voices > Make clip uses the TTS model: it must wait for other model work, and other
model work (Create, Live, the local API, model switching, Studio) must wait for it."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from this_voice_thing.integrations import local_api  # noqa: E402
from this_voice_thing.ui.pages.api_server import ApiServer  # noqa: E402
from this_voice_thing.ui.pages.generation import Generation  # noqa: E402
from this_voice_thing.ui.pages.live_voice import LiveVoicePage  # noqa: E402
from this_voice_thing.ui.pages.models import ModelPage  # noqa: E402
from this_voice_thing.ui.pages.voice_use import VoiceUse  # noqa: E402


def running():
    return mock.Mock(isRunning=mock.Mock(return_value=True))


def window(**flags):
    values = dict(model_is_loading=False, is_generating=False, api_busy=False, studio_busy=False,
                  live_voice_busy=False, speak_thread=None, clip_thread=None, model=object(),
                  api_loading_entry=None)
    values.update(flags)
    w = SimpleNamespace(**values)
    w.making_voice_clip = lambda: VoiceUse.making_voice_clip(w)
    w.model_busy = lambda: ModelPage.model_busy(w)
    w.messages = []
    w.set_status_message = w.messages.append
    return w


class OthersWaitForAClip(unittest.TestCase):
    def test_model_switching_studio_and_voices_see_it(self):
        self.assertFalse(ModelPage.model_busy(window()))
        self.assertTrue(ModelPage.model_busy(window(clip_thread=running())))
        finished = mock.Mock(isRunning=mock.Mock(return_value=False))
        self.assertFalse(ModelPage.model_busy(window(clip_thread=finished)))

    def test_live_waits(self):
        self.assertTrue(LiveVoicePage.model_busy_outside_live(window(clip_thread=running())))

    def test_create_waits(self):
        w = window(clip_thread=running())
        Generation.start_generation(w)
        self.assertFalse(w.is_generating)
        self.assertIn("voice clip", w.messages[-1])

    def test_local_api_waits(self):
        w = window(clip_thread=running())
        with self.assertRaises(local_api.ApiError) as raised:
            ApiServer.api_begin(w, {"model": None, "voice": None})
        self.assertEqual(raised.exception.status, 503)


class AClipWaitsForOthers(unittest.TestCase):
    """The Make clip menu is enabled when the tiles are drawn; the click is checked again."""

    def make(self, **flags):
        w = window(**flags)
        w.voice_is_active = mock.Mock(return_value=True)
        w.prepare_qwen_generation = mock.Mock(return_value=None)
        w.generate_button = mock.Mock()
        w.language_combo = mock.Mock(currentData=mock.Mock(return_value="en"))
        with mock.patch("this_voice_thing.ui.pages.voice_use.QMessageBox") as box, \
                mock.patch("this_voice_thing.ui.pages.voice_use.MakeClipThread") as thread:
            VoiceUse.make_voice_clip(w, SimpleNamespace(name="Narrator"))
        return box, thread

    def test_refused_while_the_model_is_busy(self):
        for flag in ("is_generating", "api_busy", "live_voice_busy", "studio_busy", "model_is_loading"):
            with self.subTest(flag):
                box, thread = self.make(**{flag: True})
                thread.assert_not_called()
                self.assertIn("busy", box.information.call_args[0][2])
        box, thread = self.make(clip_thread=running())             # a second clip
        thread.assert_not_called()

    def test_starts_when_free(self):
        box, thread = self.make()
        thread.assert_called_once()
        box.information.assert_not_called()


if __name__ == "__main__":
    unittest.main()
