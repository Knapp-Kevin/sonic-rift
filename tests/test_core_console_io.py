"""Pure-Python tests for Sonic Rift console forwarding without Qt or models."""
import io
import unittest

from this_voice_thing.core import console_io


class _Target(io.StringIO):
    def __init__(self):
        super().__init__()
        self.applied = []

    def reconfigure(self, *args, **kwargs):
        self.applied.append((args, kwargs))


class ConsoleIOTests(unittest.TestCase):
    def test_original_output_and_observational_sink(self):
        target = _Target()
        observed = []
        tee = console_io.ForwardingStream(target, lambda: observed.append)
        self.assertEqual(tee.write("hello"), 5)
        self.assertEqual(target.getvalue(), "hello")
        self.assertEqual(observed, ["hello"])
        self.assertEqual(tee.encoding, target.encoding)

    def test_sink_does_not_run_for_empty_output(self):
        target = _Target()
        called = []
        tee = console_io.ForwardingStream(target, lambda: called.append)
        tee.write("")
        self.assertEqual(called, [])

    def test_sink_switches_dynamically(self):
        target = _Target()
        a, b = [], []
        selected = [a.append]
        tee = console_io.ForwardingStream(target, lambda: selected[0])
        tee.write("first")
        selected[0] = b.append
        tee.write("second")
        self.assertEqual(a, ["first"])
        self.assertEqual(b, ["second"])

    def test_sink_errors_never_break_canonical_stdout(self):
        target = _Target()
        def broken(_text):
            raise RuntimeError("widget was closed")
        tee = console_io.ForwardingStream(target, lambda: broken)
        self.assertEqual(tee.write("log"), 3)
        self.assertEqual(target.getvalue(), "log")

    def test_supports_stream_operations(self):
        target = _Target()
        tee = console_io.ForwardingStream(target)
        self.assertFalse(tee.isatty())
        self.assertEqual(tee.reconfigure(errors="replace"), None)
        self.assertEqual(target.applied, [((), {"errors": "replace"})])
        self.assertIsNone(tee.flush())

    def test_console_configuration_failure_is_nonfatal(self):
        class Broken:
            def reconfigure(self, **_kw):
                raise OSError("unsupported")
        console_io.configure_console_stream(Broken())
        console_io.configure_console_stream(None)
        target = _Target()
        console_io.configure_console_stream(target)
        self.assertEqual(target.applied, [((), {"encoding": "utf-8", "errors": "backslashreplace"})])

    def test_legacy_console_safe_text_escapes_unicode(self):
        self.assertEqual(console_io.safe_console_text("café"), "caf\\xe9")
        self.assertEqual(console_io.safe_console_text("plain"), "plain")


if __name__ == "__main__":
    unittest.main()
