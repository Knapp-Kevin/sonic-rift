"""Security and repeatability gates for the Phase A agent planning contract."""
import unittest

from this_voice_thing.core.agent_jobs import InvalidJob, capabilities, plan_request


class AgentJobPlanTests(unittest.TestCase):
    def request(self, **edits):
        value = {"kind": "music.generate", "model_id": "ACE-Step/ace-2b",
                 "prompt": "Original instrumental sea voyage score",
                 "duration_seconds": 60, "seed": 7, "instrumental": True}
        value.update(edits)
        return value

    def test_capabilities_fail_closed(self):
        result = capabilities()
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["control_plane"], "read_only")
        self.assertEqual({i["id"] for i in result["capabilities"]},
                         {"music.generate", "speech.generate", "sound.generate"})
        self.assertTrue(all(not item["agent_execution"] for item in result["capabilities"]))

    def test_plan_has_stable_digest_and_never_echoes_prompt(self):
        a = plan_request(self.request())
        b = plan_request(self.request())
        self.assertEqual(a, b)
        self.assertEqual(len(a["plan_id"]), 64)
        self.assertEqual(a["status"], "plan_only")
        self.assertFalse(a["execution_enabled"])
        self.assertNotIn("prompt", a)
        self.assertNotIn("sea voyage", repr(a))
        self.assertEqual(a["model_installed"], "unverified")

    def test_changing_input_changes_plan_identity(self):
        original = plan_request(self.request())["plan_id"]
        for change in ({"seed": 9}, {"duration_seconds": 40},
                       {"prompt": "A new composition"}, {"instrumental": False},
                       {"model_id": "Stable-Audio/medium"}):
            with self.subTest(change=change):
                self.assertNotEqual(original, plan_request(self.request(**change))["plan_id"])

    def test_fails_closed_on_untrusted_fields_and_paths(self):
        for change in ({"path": "C:/Users/private"}, {"output_dir": "../../secret"},
                       {"command": "powershell"}, {"url": "https://example.org"},
                       {"model_id": "../../escape"}, {"model_id": "https://evil/path"},
                       {"model_id": "foo//bar"}, {"unknown": True}):
            with self.subTest(change=change), self.assertRaises(InvalidJob):
                plan_request(self.request(**change))

    def test_types_and_limits_are_strict(self):
        for change in ({"duration_seconds": True}, {"duration_seconds": 0},
                       {"duration_seconds": 601}, {"seed": -1}, {"seed": 2**32},
                       {"seed": True}, {"instrumental": 1},
                       {"prompt": ""}, {"prompt": "\x00injected"},
                       {"prompt": "x" * 4001}, {"kind": "shell.execute"},
                       {"model_id": ""}):
            with self.subTest(change=str(change)[:70]), self.assertRaises(InvalidJob):
                plan_request(self.request(**change))

    def test_non_music_request_rejects_instrumental_flag(self):
        with self.assertRaises(InvalidJob):
            plan_request(self.request(kind="speech.generate"))
        p = self.request(kind="speech.generate")
        p.pop("instrumental")
        result = plan_request(p)
        self.assertIsNone(result["instrumental"])
        self.assertFalse(result["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
