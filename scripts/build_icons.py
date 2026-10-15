"""Build the Sonic Rift app icon set from its SVG masters.

    python scripts/build_icons.py

Small sizes are drawn from simplified masters so the rift ring and waveform stay legible
on the taskbar; 48 px and up come from the approved symbol:

    16, 20        assets/branding/sonic-rift-icon-16.svg
    24, 32, 40    assets/branding/sonic-rift-icon-small.svg
    48 ... 512    assets/branding/sonic-rift-icon.svg

Writes assets/branding/app-icon/sonic-rift-<size>.png and assets/branding/sonic-rift.ico
(every size embedded as PNG, which Windows Vista and later read at all sizes).
"""
import io
import os
import struct
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDING = os.path.join(ROOT, "assets", "branding")
PNG_DIR = os.path.join(BRANDING, "app-icon")
ICO_PATH = os.path.join(BRANDING, "sonic-rift.ico")
SOURCES = {
    "sonic-rift-icon-16.svg": (16, 20),
    "sonic-rift-icon-small.svg": (24, 32, 40),
    "sonic-rift-icon.svg": (48, 64, 96, 128, 256, 512),
}
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)   # .ico entries stop at 256


def render(svg_path, size):
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        raise ValueError(f"Can't read {svg_path}")
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def png_bytes(image):
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def write_ico(path, entries):
    """entries: [(size, png_bytes)]. ICONDIR + ICONDIRENTRY per image + the PNG payloads."""
    out = io.BytesIO()
    out.write(struct.pack("<HHH", 0, 1, len(entries)))
    offset = 6 + 16 * len(entries)
    for size, data in entries:
        side = 0 if size >= 256 else size            # 0 means 256 in the directory
        out.write(struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    for _size, data in entries:
        out.write(data)
    with open(path, "wb") as handle:
        handle.write(out.getvalue())


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841 (Qt needs it)
    os.makedirs(PNG_DIR, exist_ok=True)
    pngs = {}
    for source, sizes in SOURCES.items():
        for size in sizes:
            data = png_bytes(render(os.path.join(BRANDING, source), size))
            with open(os.path.join(PNG_DIR, f"sonic-rift-{size}.png"), "wb") as handle:
                handle.write(data)
            pngs[size] = data
    write_ico(ICO_PATH, [(size, pngs[size]) for size in ICO_SIZES])
    print(f"Wrote {len(pngs)} PNGs to {os.path.relpath(PNG_DIR, ROOT)} and {os.path.relpath(ICO_PATH, ROOT)}")


if __name__ == "__main__":
    main()
