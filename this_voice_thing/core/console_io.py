"""Small, GUI-independent stream forwarding for Sonic Rift diagnostics.

A stream is a stream, not a speech-engine setting. The caller provides the
optional live sink so this module never imports the UI or stores application
state globally.
"""


def configure_console_stream(stream):
    """Request UTF-8 output when the supplied stream supports reconfiguration."""
    configure = getattr(stream, "reconfigure", None)
    if not callable(configure):
        return
    try:
        configure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        # A terminal, redirected pipe or custom test stream may reject this.
        pass


def safe_console_text(value):
    """Render any value as pure ASCII for legacy Windows console diagnostics."""
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


class ForwardingStream:
    """Write to the original stream and optionally notify a best-effort sink."""

    def __init__(self, wrapped_stream, sink_supplier=None):
        self.wrapped_stream = wrapped_stream
        self._sink_supplier = sink_supplier
        self.encoding = getattr(wrapped_stream, "encoding", "utf-8")

    def write(self, value):
        text = str(value)
        written = self.wrapped_stream.write(text)
        supplier = self._sink_supplier
        if text and supplier is not None:
            try:
                sink = supplier()
                if sink is not None:
                    sink(text)
            except Exception:
                # UI listeners are observational and must not break stdout.
                pass
        return written

    def flush(self):
        return self.wrapped_stream.flush()

    def isatty(self):
        reporter = getattr(self.wrapped_stream, "isatty", None)
        return bool(reporter()) if callable(reporter) else False

    def reconfigure(self, *args, **kwargs):
        configure = getattr(self.wrapped_stream, "reconfigure", None)
        return configure(*args, **kwargs) if callable(configure) else None
