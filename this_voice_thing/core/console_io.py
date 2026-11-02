"""Small, GUI-independent stream forwarding for Sonic Rift diagnostics.

A stream is a stream, not a speech-engine setting. The caller provides the
optional live sink so this module never imports the UI or stores application
state globally.
"""

# What every console stream is switched to when it allows it: UTF-8, and characters
# the console still can't take come out as \x.. escapes instead of raising.
UTF8_CONSOLE = {"encoding": "utf-8", "errors": "backslashreplace"}


def configure_console_stream(console):
    """Switch a stream to UTF8_CONSOLE when it supports reconfigure(); otherwise do nothing."""
    try:
        console.reconfigure(**UTF8_CONSOLE)
    except Exception:
        # None (pythonw), a redirected pipe or a test stream without reconfigure().
        pass


def safe_console_text(value):
    """Render any value as pure ASCII for legacy Windows console diagnostics.

    Each non-ASCII character becomes its Python escape (\\xe9, \\u20ac, \\U0001f600)."""
    text = str(value)
    if text.isascii():
        return text
    return "".join(ch if ch.isascii() else ch.encode("unicode_escape").decode("ascii") for ch in text)


def stream_encoding(stream):
    """The encoding a stream reports; UTF-8 for an object without that attribute."""
    return getattr(stream, "encoding", "utf-8")


def stream_is_terminal(stream):
    """True only when the stream exists and says it is an interactive terminal."""
    try:
        return bool(stream.isatty())
    except Exception:
        return False


class ForwardingStream:
    """Write to the original stream and optionally notify a best-effort sink.

    sink_supplier is called on every write, so the listener can change (or go away)
    while the stream stays installed as sys.stdout."""

    def __init__(self, target, sink_supplier=None):
        self.target = target
        self.encoding = stream_encoding(target)
        self._listener_for = sink_supplier or (lambda: None)

    def _tell_listener(self, text):
        try:
            listener = self._listener_for()
            if listener is not None:
                listener(text)
        except Exception:
            pass   # UI listeners only observe; they must never break stdout

    def write(self, value):
        text = str(value)
        result = self.target.write(text)
        if text:
            self._tell_listener(text)
        return result

    def flush(self):
        return self.target.flush()

    def isatty(self):
        return stream_is_terminal(self.target)

    def reconfigure(self, *args, **options):
        """Pass reconfigure() through; streams that lack it are left as they are."""
        if not hasattr(self.target, "reconfigure"):
            return None
        return self.target.reconfigure(*args, **options)
