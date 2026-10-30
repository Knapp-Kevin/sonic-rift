"""Sonic Rift's light/dark theme, following the Windows app mode.

Colours are semantic tokens: widgets ask for "accent", "warning_text" or
"selected_bg", never for a hex value, so the brand can change without changing
what a colour means. The brand family is cyan / electric blue / purple / pink on
deep navy; amber is reserved for warnings and caution (uncertain licenses,
tight hardware, things needing attention), red for errors, green for success.

Depth and texture are painted by a few small widgets (cards with soft
shadows, sound-wave page backgrounds, a gradient sidebar) instead of
QGraphicsDropShadowEffect, which renders whole subtrees offscreen and makes
text fields and lists slow and glitchy.
"""

import os


from this_voice_thing import paths
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QApplication, QFrame, QWidget

APP_NAME = "Sonic Rift"
TAGLINE = "Make worlds you can hear."

# Every theme defines exactly these roles (tests check both themes match).
SEMANTIC_ROLES = (
    "window",          # app background
    "surface",         # elevated surface (cards, inputs, menus)
    "surface_alt",     # secondary surface (fields, hover rows)
    "border", "border_strong",
    "text",            # primary text
    "muted",           # secondary/muted text
    "accent", "accent_hover", "accent_pressed",  # primary accent: links, primary actions
    "accent_text",     # text/icons on an accent fill
    "selected_bg",     # selected / active background (sidebar item, tile, menu row)
    "focus",           # keyboard focus ring
    "brand_blue", "brand_secondary", "brand_tertiary",  # electric blue, purple, pink: decoration
    "success_bg", "success_text",
    "warning_bg", "warning_text",  # amber: caution, uncertain license, tight hardware
    "error_bg", "error_text",
    "disabled", "disabled_bg",
)

DARK = {
    "window": "#0b1020",
    "surface": "#131a2e",
    "surface_alt": "#19213a",
    "border": "#27314f",
    "border_strong": "#35416a",
    "text": "#e7ecf6",
    "muted": "#9ba7c3",
    "accent": "#22d3ee",          # cyan
    "accent_hover": "#67e8f9",
    "accent_pressed": "#06b6d4",
    "accent_text": "#03131c",
    "selected_bg": "#0f2b40",
    "focus": "#67e8f9",
    "brand_blue": "#4f7bff",
    "brand_secondary": "#a78bfa",  # purple
    "brand_tertiary": "#f472b6",   # pink
    "success_bg": "#0f2e22", "success_text": "#6ee7a8",
    "warning_bg": "#36290d", "warning_text": "#fbbf24",
    "error_bg": "#3b1622", "error_text": "#fb7185",
    "disabled": "#5b6688",
    "disabled_bg": "#161d31",
    # depth and texture
    "page_top": "#0e1429", "page_bottom": "#080c18",
    "sidebar_top": "#0b1124", "sidebar_bottom": "#070a15",
    "surface_top": "#161e35", "surface_bottom": "#121a2d",
    "button_top": "#1d2642", "button_bottom": "#172038",
    "shadow": "#000000", "shadow_strength": 0.6,
    "edge_highlight": "#ffffff12",
}

LIGHT = {
    "window": "#f4f6fb",
    "surface": "#ffffff",
    "surface_alt": "#f3f6fb",
    "border": "#d5dce9",
    "border_strong": "#bfc9db",
    "text": "#121a2e",
    "muted": "#525d78",
    "accent": "#0e7490",          # deep cyan: readable on white (5.4:1)
    "accent_hover": "#0b6680",
    "accent_pressed": "#155e75",
    "accent_text": "#ffffff",
    "selected_bg": "#ddf3f9",
    "focus": "#0891b2",
    "brand_blue": "#2f5bea",
    "brand_secondary": "#7c3aed",
    "brand_tertiary": "#db2777",
    "success_bg": "#dcf3e5", "success_text": "#166534",
    "warning_bg": "#fdefcc", "warning_text": "#7a4a00",
    "error_bg": "#fbe2e6", "error_text": "#9f1239",
    "disabled": "#8d97ab",
    "disabled_bg": "#e8ecf3",
    "page_top": "#f7f9fd", "page_bottom": "#ebeff7",
    "sidebar_top": "#eef2f9", "sidebar_bottom": "#e2e8f3",
    "surface_top": "#ffffff", "surface_bottom": "#f8fafd",
    "button_top": "#ffffff", "button_bottom": "#eef2f8",
    "shadow": "#1b2a4a", "shadow_strength": 0.14,
    "edge_highlight": "#ffffff",
}

ASSETS_DIR = paths.ASSETS_DIR
SHADOW = 7          # pixels around each card reserved for its painted shadow
CARD_RADIUS = 10
_current = DARK


def _asset(name):
    return os.path.join(ASSETS_DIR, name).replace("\\", "/")


DARK["chevron"] = _asset("chevron_down_dark.svg")
LIGHT["chevron"] = _asset("chevron_down_light.svg")
DARK["chevron_up"] = _asset("chevron_up_dark.svg")
LIGHT["chevron_up"] = _asset("chevron_up_light.svg")
DARK["check"] = _asset("check_dark.svg")    # dark tick on the cyan fill
LIGHT["check"] = _asset("check_light.svg")  # white tick on the deep-cyan fill

# The Sonic Rift app icon: one PNG per size, built by scripts/build_icons.py. The small
# sizes are redrawn for legibility, so the icon carries every size and Qt picks the closest
# (title bar ~16-24 px, Alt+Tab and taskbar 32-48 px, larger elsewhere).
APP_ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256, 512)
BRAND_ICON = _asset("branding/app-icon/sonic-rift-512.png")
FALLBACK_ICON = _asset("logo.svg")


def app_icon_path():
    """The brand icon if it's there and decodes (a truncated file would give the window
    no icon at all), otherwise the fallback."""
    if os.path.exists(BRAND_ICON) and not QImage(BRAND_ICON).isNull():
        return BRAND_ICON
    return FALLBACK_ICON


def app_icon_files():
    """The per-size icon PNGs that exist and decode."""
    files = []
    for size in APP_ICON_SIZES:
        path = _asset(f"branding/app-icon/sonic-rift-{size}.png")
        if os.path.exists(path) and not QImage(path).isNull():
            files.append((size, path))
    return files


def app_icon():
    files = app_icon_files()
    if not files:
        return QIcon(app_icon_path())
    icon = QIcon()
    for size, path in files:
        icon.addFile(path, QSize(size, size))
    return icon


def current():
    return _current


def brand_gradient(x1, y1, x2, y2, colors=None):
    """The cyan -> blue -> purple brand stroke, for small identity moments only
    (progress, the recording waveform), never for panels, text or warnings."""
    c = colors or _current
    gradient = QLinearGradient(QPointF(x1, y1), QPointF(x2, y2))
    gradient.setColorAt(0, _color(c["accent"]))
    gradient.setColorAt(0.55, _color(c["brand_blue"]))
    gradient.setColorAt(1, _color(c["brand_secondary"]))
    return gradient


def _color(value):
    color = QColor(value)
    if isinstance(value, str) and len(value) == 9:  # #rrggbbaa
        color = QColor(value[:7])
        color.setAlpha(int(value[7:], 16))
    return color


# --- contrast (used by tests, and handy when tuning tokens) ---

def relative_luminance(hex_color):
    channels = []
    for index in (1, 3, 5):
        value = int(hex_color[index:index + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground, background):
    lighter, darker = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _vertical(rect, top, bottom):
    gradient = QLinearGradient(QPointF(rect.left(), rect.top()), QPointF(rect.left(), rect.bottom()))
    gradient.setColorAt(0, _color(top))
    gradient.setColorAt(1, _color(bottom))
    return gradient


class CardFrame(QFrame):
    """A raised card: soft shadow, gentle top-to-bottom gradient, top highlight."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setContentsMargins(SHADOW, SHADOW - 3, SHADOW, SHADOW + 3)

    def body_rect(self):
        return QRectF(self.rect()).adjusted(SHADOW, SHADOW - 3, -SHADOW, -(SHADOW + 3))

    def paintEvent(self, _event):
        c = _current
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = self.body_rect()
        shadow = _color(c["shadow"])
        painter.setPen(Qt.PenStyle.NoPen)
        for spread in range(SHADOW, 0, -1):
            layer = QColor(shadow)
            layer.setAlphaF(c["shadow_strength"] / SHADOW * (1 - spread / (SHADOW + 1)))
            painter.setBrush(layer)
            painter.drawRoundedRect(body.adjusted(-spread, -spread + 3, spread, spread + 3),
                                    CARD_RADIUS + spread, CARD_RADIUS + spread)
        painter.setBrush(_vertical(body, c["surface_top"], c["surface_bottom"]))
        painter.setPen(QPen(_color(c["border"]), 1))
        painter.drawRoundedRect(body.adjusted(0.5, 0.5, -0.5, -0.5), CARD_RADIUS, CARD_RADIUS)
        painter.setPen(QPen(_color(c["edge_highlight"]), 1))
        painter.drawLine(QPointF(body.left() + CARD_RADIUS, body.top() + 1.5),
                         QPointF(body.right() - CARD_RADIUS, body.top() + 1.5))
        painter.end()


SONIC_SCENES = {
    # frequency, phase, centreline. One visual family, subtle differences per workflow.
    "studio": (1.0, 0.0, 0.46), "speech": (0.77, -0.35, 0.49),
    "sounds": (1.14, 0.48, 0.56), "voices": (0.69, 0.12, 0.46),
    "clone": (0.86, 0.65, 0.50), "design": (1.16, 0.90, 0.46),
    "remix": (1.27, -0.65, 0.51), "transcribe": (0.70, -0.40, 0.44),
    "live": (1.40, 0.20, 0.50), "neutral": (0.48, 0.05, 0.51),
}


def _paint_sonic_waves(painter, rect, colors, scene):
    """Stable, subtle wave contours: no grain, timers, external files or image effects."""
    from math import pi, sin

    frequency, phase, center = SONIC_SCENES[scene]
    width, height = rect.width(), rect.height()
    if width <= 0 or height <= 0:
        return
    dark = colors is DARK
    blue = _color(colors["brand_blue"])
    violet = _color(colors["brand_secondary"])
    cyan = _color(colors["accent"])
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipRect(rect)
    # Broad rings near the edges read as sound propagation and echo.
    for side, tint in ((-0.06, blue), (1.09, violet)):
        for ring in range(9):
            radius = (0.11 + 0.083 * ring) * min(width, height) * 1.6
            ink = QColor(tint)
            ink.setAlpha(max(3, (15 if dark else 19) - ring))
            painter.setPen(QPen(ink, 0.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(width * side, height * (center + 0.015)),
                                radius, radius * 0.91)

    # Layered harmonic paths. Profiles change the composition, not the app palette.
    for layer in range(3):
        count = 12 if layer == 1 else 9
        tint = (cyan, blue, violet)[layer]
        for track in range(count):
            path = QPainterPath()
            offset = (track - (count - 1) / 2) * 0.012
            for step in range(85):
                t = step / 84.0
                wave = sin(2 * pi * (frequency * 1.18 * t + phase + layer * 0.21))
                overtone = 0.28 * sin(2 * pi * (t * (2.3 + layer * 0.34) + phase * 0.7))
                y = height * (center + (layer - 1) * 0.097 + offset +
                              (0.032 + 0.024 * frequency) * (wave + overtone))
                x = width * t
                if step == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            ink = QColor(tint)
            ink.setAlpha(max(5, (22 if dark else 27) - abs(track - count / 2) * 2 - layer * 2))
            painter.setPen(QPen(ink, 0.85))
            painter.drawPath(path)
    painter.restore()


class TexturedArea(QWidget):
    """Paint a low-contrast acoustic field behind pages, without static noise."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = "neutral"

    def set_scene(self, scene):
        if scene not in SONIC_SCENES:
            raise ValueError(f"Unknown sonic background scene: {scene}")
        if self.scene != scene:
            self.scene = scene
            self.update()

    def paintEvent(self, _event):
        c = _current
        painter = QPainter(self)
        rect = QRectF(self.rect())
        painter.fillRect(rect, _vertical(rect, c["page_top"], c["page_bottom"]))
        _paint_sonic_waves(painter, rect, c, self.scene)
        edge = QLinearGradient(QPointF(0, 0), QPointF(12, 0))
        shade = _color(c["shadow"])
        shade.setAlphaF(c["shadow_strength"] * 0.45)
        edge.setColorAt(0, shade)
        shade.setAlphaF(0)
        edge.setColorAt(1, shade)
        painter.fillRect(QRectF(0, 0, 12, rect.height()), edge)
        painter.end()


class SidebarPanel(QWidget):
    """Sidebar: darker gradient with grain, a crisp right edge, and a thin brand
    stroke along its top as the one decorative use of the full brand gradient."""

    def paintEvent(self, _event):
        c = _current
        painter = QPainter(self)
        rect = QRectF(self.rect())
        painter.fillRect(rect, _vertical(rect, c["sidebar_top"], c["sidebar_bottom"]))
        # Clean gradient; the former noise tile resembled television static.
        stroke = brand_gradient(0, 0, rect.width(), 0, c)
        stroke.setColorAt(1, _color(c["brand_tertiary"]))
        painter.fillRect(QRectF(0, 0, rect.width(), 2), stroke)
        painter.setPen(QPen(_color(c["border"]), 1))
        painter.drawLine(QPointF(rect.right() - 0.5, 0), QPointF(rect.right() - 0.5, rect.bottom()))
        painter.end()


def _is_dark(app):
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


def _palette(c):
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: c["window"],
        QPalette.ColorRole.WindowText: c["text"],
        QPalette.ColorRole.Base: c["surface"],
        QPalette.ColorRole.AlternateBase: c["surface_alt"],
        QPalette.ColorRole.Text: c["text"],
        QPalette.ColorRole.Button: c["surface"],
        QPalette.ColorRole.ButtonText: c["text"],
        QPalette.ColorRole.ToolTipBase: c["surface"],
        QPalette.ColorRole.ToolTipText: c["text"],
        QPalette.ColorRole.PlaceholderText: c["muted"],
        QPalette.ColorRole.Highlight: c["accent"],
        QPalette.ColorRole.HighlightedText: c["accent_text"],
        QPalette.ColorRole.Link: c["accent"],
        QPalette.ColorRole.Mid: c["disabled"],
    }
    for role, value in roles.items():
        p.setColor(role, QColor(value))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor(c["disabled"]))
    return p


def _gradient(top, bottom):
    return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {top}, stop:1 {bottom})"


def _stylesheet(c):
    button = _gradient(c["button_top"], c["button_bottom"])
    # The brand stroke (cyan -> blue -> purple): progress bars only.
    brand = (f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c['accent']}, "
             f"stop:0.55 {c['brand_blue']}, stop:1 {c['brand_secondary']})")
    return f"""
    QWidget {{ font-family: "Segoe UI Variable Text", "Segoe UI"; font-size: 10pt; }}
    QToolTip {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 4px; }}

    QListWidget#Sidebar {{
        background: transparent; border: none; padding: 6px 8px; outline: 0; font-size: 11pt;
    }}
    QListWidget#Sidebar::item {{
        padding: 10px 12px; margin: 2px 0; border-radius: 8px; color: {c['muted']};
    }}
    QListWidget#Sidebar::item:hover {{ background: {c['surface_alt']}; color: {c['text']}; }}
    QListWidget#Sidebar::item:selected {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c['selected_bg']}, stop:1 transparent);
        color: {c['text']}; border-left: 3px solid {c['accent']}; font-weight: 600;
    }}
    QListWidget#Sidebar:focus {{ border: none; }}
    QListWidget#Sidebar::item:selected:focus {{ border: 1px solid {c['focus']}; border-left: 3px solid {c['accent']}; }}
    QLabel#AppTitle {{
        font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 14pt; font-weight: 700;
        color: {c['text']};
    }}

    QLabel#PageTitle {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 17pt; font-weight: 600; }}
    QLabel#PageSubtitle, QLabel#Muted {{ color: {c['muted']}; }}
    QFrame#Card {{ background: transparent; border: none; }}
    QLabel#CardTitle {{ font-weight: 700; font-size: 10.5pt; }}
    QLabel#RecordingPhase {{ font-size: 12pt; font-weight: 700; }}
    QLabel#RecordingClock {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 28pt; font-weight: 700; }}
    QLabel#ReadAloud {{ font-size: 12.5pt; }}
    QPlainTextEdit#LogView {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 9.5pt; }}
    QLabel#Note {{
        background: {c['warning_bg']}; border-left: 3px solid {c['warning_text']};
        border-radius: 6px; padding: 8px 10px; color: {c['text']};
    }}
    QLabel#VoiceChip {{
        background: {c['selected_bg']}; border: 1px solid {c['selected_bg']}; border-bottom-color: {c['border_strong']};
        border-radius: 12px; padding: 4px 12px; font-weight: 600; color: {c['text']};
    }}
    QLabel[tone="success"], QLabel#Muted[tone="success"], QLabel#RecordingPhase[tone="success"] {{ color: {c['success_text']}; }}
    QLabel[tone="warning"], QLabel#Muted[tone="warning"], QLabel#RecordingPhase[tone="warning"] {{ color: {c['warning_text']}; }}
    QLabel[tone="error"], QLabel#Muted[tone="error"], QLabel#RecordingPhase[tone="error"] {{ color: {c['error_text']}; }}

    QFrame#Tile {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {c['surface_top']}, stop:1 {c['surface_bottom']});
        border: 1px solid {c['border']}; border-bottom-color: {c['border_strong']}; border-radius: 10px;
    }}
    QFrame#Tile:hover {{ border-color: {c['accent']}; }}
    QFrame#Tile[active="true"] {{ background: {c['selected_bg']}; border: 2px solid {c['accent']}; }}
    QLabel#TileTitle {{ font-weight: 700; }}
    QLabel#TileNeeds {{ font-size: 9pt; font-weight: 600; color: {c['muted']}; }}
    QLabel#TileNeeds[kind="good"] {{ color: {c['success_text']}; }}
    QLabel#TileNeeds[kind="tight"] {{ color: {c['warning_text']}; }}
    QLabel#TileNeeds[kind="short"] {{ color: {c['error_text']}; }}
    QPushButton#TileMenu {{
        background: transparent; border: none; border-radius: 5px; padding: 0; font-size: 12pt; color: {c['muted']};
    }}
    QPushButton#TileMenu:hover, QPushButton#TileMenu:focus {{ background: {c['selected_bg']}; color: {c['text']}; }}
    QLabel#Badge {{
        border-radius: 8px; padding: 1px 7px; font-size: 8.5pt; font-weight: 600;
        background: {c['surface_alt']}; color: {c['muted']}; border: 1px solid {c['border']};
    }}
    QLabel#Badge[kind="permissive"] {{ background: {c['success_bg']}; color: {c['success_text']}; border-color: {c['success_bg']}; }}
    QLabel#Badge[kind="noncommercial"] {{ background: {c['error_bg']}; color: {c['error_text']}; border-color: {c['error_bg']}; }}
    QLabel#Badge[kind="unknown"] {{ background: {c['warning_bg']}; color: {c['warning_text']}; border-color: {c['warning_bg']}; }}
    QLabel#Badge[kind="active"] {{ background: {c['accent']}; color: {c['accent_text']}; border-color: {c['accent_pressed']}; }}
    QTabBar#CapabilityTabs {{ font-size: 10.5pt; }}
    QTabBar#CapabilityTabs::tab {{
        background: transparent; border: none; border-bottom: 2px solid transparent;
        padding: 6px 10px 7px 10px; margin-right: 2px; color: {c['muted']};
    }}
    QTabBar#CapabilityTabs::tab:hover {{ color: {c['text']}; }}
    QTabBar#CapabilityTabs::tab:selected {{ color: {c['text']}; border-bottom-color: {c['accent']}; font-weight: 600; }}
    QTabBar#CapabilityTabs:focus {{ outline: none; }}
    QTabBar#CapabilityTabs::tab:focus {{ color: {c['text']}; border-bottom-color: {c['focus']}; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['border_strong']}; border-radius: 3px; min-height: 28px; }}
    QScrollBar::handle:horizontal {{ background: {c['border_strong']}; border-radius: 3px; min-width: 28px; }}
    QScrollBar::handle:hover {{ background: {c['accent']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; background: none; border: none; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    QLabel#SectionLabel {{ color: {c['muted']}; font-size: 8.5pt; font-weight: 700; letter-spacing: 1px; }}

    QPushButton {{
        background: {button}; border: 1px solid {c['border']}; border-bottom-color: {c['border_strong']};
        border-radius: 7px; padding: 6px 14px; color: {c['text']};
    }}
    QPushButton:hover {{ border-color: {c['accent']}; }}
    QPushButton:focus {{ border: 1px solid {c['focus']}; }}
    QPushButton:pressed {{ background: {c['selected_bg']}; border-bottom-color: {c['border']}; }}
    QPushButton:disabled {{ color: {c['disabled']}; border-color: {c['border']}; background: {c['disabled_bg']}; }}
    QPushButton[accent="true"] {{
        background: {c['accent']}; color: {c['accent_text']}; border: 1px solid {c['accent_pressed']};
        font-weight: 700; padding: 9px 22px;
    }}
    QPushButton[accent="true"]:hover {{ background: {c['accent_hover']}; }}
    QPushButton[accent="true"]:focus {{ border: 2px solid {c['focus']}; padding: 8px 21px; }}
    QPushButton[accent="true"]:pressed {{ background: {c['accent_pressed']}; }}
    QPushButton[accent="true"]:disabled {{ background: {c['disabled_bg']}; color: {c['disabled']}; border-color: {c['border']}; }}
    QPushButton[role="destructive"] {{ color: {c['error_text']}; }}
    QPushButton[role="destructive"]:hover {{ border-color: {c['error_text']}; }}
    QPushButton[flat="true"] {{ background: transparent; border: none; color: {c['accent']}; padding: 4px 6px; }}
    QPushButton[flat="true"]:hover {{ text-decoration: underline; }}
    QPushButton[flat="true"]:focus {{ text-decoration: underline; border: 1px dotted {c['focus']}; }}
    QPushButton[flat="true"]:disabled {{ color: {c['disabled']}; }}

    QTextEdit, QPlainTextEdit, QListWidget, QComboBox, QSpinBox, QLineEdit, QDoubleSpinBox, QTableWidget, QTreeWidget {{
        background: {c['surface_alt']}; border: 1px solid {c['border']}; border-top-color: {c['border_strong']};
        border-radius: 7px; padding: 4px 6px; color: {c['text']};
        selection-background-color: {c['accent']}; selection-color: {c['accent_text']};
    }}
    QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QLineEdit:focus,
    QDoubleSpinBox:focus, QListWidget:focus, QTableWidget:focus, QTreeWidget:focus {{
        border: 1px solid {c['focus']};
    }}
    QComboBox {{ background: {button}; border-top-color: {c['border']}; border-bottom-color: {c['border_strong']}; }}
    QListWidget::item {{ padding: 4px; border-radius: 5px; }}
    QListWidget::item:selected {{ background: {c['selected_bg']}; color: {c['text']}; }}
    QHeaderView::section {{
        background: {c['surface']}; color: {c['muted']}; border: none; border-bottom: 1px solid {c['border']};
        padding: 4px 6px; font-weight: 600;
    }}
    QTableWidget::item:selected, QTreeWidget::item:selected {{ background: {c['selected_bg']}; color: {c['text']}; }}
    QTreeWidget::item {{ padding: 3px 2px; }}

    QAbstractSpinBox {{ padding-right: 22px; }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
        subcontrol-origin: border; width: 20px; border: none; border-left: 1px solid {c['border']}; background: transparent;
    }}
    QAbstractSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 7px; }}
    QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 7px; }}
    QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {c['selected_bg']}; }}
    QAbstractSpinBox::up-arrow {{ image: url({c['chevron_up']}); width: 9px; height: 6px; }}
    QAbstractSpinBox::down-arrow {{ image: url({c['chevron']}); width: 9px; height: 6px; }}
    QAbstractSpinBox::up-arrow:disabled, QAbstractSpinBox::down-arrow:disabled {{ image: none; }}

    QToolButton#MenuButton {{
        background: {button}; border: 1px solid {c['border']}; border-bottom-color: {c['border_strong']};
        border-radius: 7px; padding: 6px 26px 6px 14px; color: {c['text']};
    }}
    QToolButton#MenuButton:hover {{ border-color: {c['accent']}; }}
    QToolButton#MenuButton:focus {{ border: 1px solid {c['focus']}; }}
    QToolButton#MenuButton:disabled {{ color: {c['disabled']}; background: {c['disabled_bg']}; }}
    QToolButton#MenuButton::menu-indicator {{
        image: url({c['chevron']}); subcontrol-origin: padding; subcontrol-position: center right;
        width: 10px; height: 7px; right: 9px;
    }}
    QLabel#EmptyState {{ color: {c['muted']}; padding: 18px; }}

    QSlider::groove:horizontal {{ height: 4px; background: {c['border']}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: 2px; }}
    QSlider::handle:horizontal {{
        background: {c['surface_top']}; border: 3px solid {c['accent']};
        width: 10px; height: 10px; margin: -6px 0; border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{ border-color: {c['accent_hover']}; }}
    QSlider:focus {{ outline: none; }}
    QSlider::handle:horizontal:focus {{ border-color: {c['focus']}; background: {c['selected_bg']}; }}
    QSlider::handle:horizontal:disabled {{ border-color: {c['disabled']}; }}
    QSlider::sub-page:horizontal:disabled {{ background: {c['disabled']}; }}

    QProgressBar {{ background: {c['border']}; border: none; border-radius: 4px; }}
    QProgressBar::chunk {{ background: {brand}; border-radius: 4px; }}

    QCheckBox::indicator {{
        width: 16px; height: 16px; border-radius: 4px; border: 1px solid {c['border_strong']};
        background: {c['surface_alt']};
    }}
    QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent_pressed']}; image: url({c['check']}); }}
    QCheckBox::indicator:focus {{ border: 2px solid {c['focus']}; }}
    QCheckBox::indicator:disabled {{ background: {c['disabled_bg']}; border-color: {c['border']}; }}
    QCheckBox {{ spacing: 8px; }}

    QGroupBox {{ border: 1px solid {c['border']}; border-radius: 8px; margin-top: 10px; padding-top: 6px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {c['muted']}; }}
    QStatusBar {{ background: {c['sidebar_bottom']}; color: {c['muted']}; border-top: 1px solid {c['border']}; }}
    QStatusBar QLabel {{ padding-left: 8px; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox::down-arrow {{ image: url({c['chevron']}); width: 12px; height: 8px; margin-right: 8px; }}
    QComboBox QAbstractItemView {{
        background: {c['surface']}; border: 1px solid {c['border']}; color: {c['text']};
        selection-background-color: {c['selected_bg']}; selection-color: {c['text']};
    }}
    QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; padding: 4px; color: {c['text']}; }}
    QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {c['selected_bg']}; color: {c['text']}; }}
    QMenu::item:disabled {{ color: {c['disabled']}; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QSplitter::handle {{ background: transparent; }}
    """


def set_tone(label, tone):
    """Colour a status label by meaning ("success", "warning", "error", or "" for normal)."""
    label.setProperty("tone", tone or "")
    label.style().unpolish(label)
    label.style().polish(label)


def use(app, colors):
    """Apply one colour set now (also used by tests to force light or dark)."""
    global _current
    _current = colors
    app.setPalette(_palette(colors))
    app.setStyleSheet(_stylesheet(colors))
    for widget in QApplication.allWidgets():
        QWidget.update(widget)  # item views overload update(index)


def apply_theme(app):
    """Apply the palette and stylesheet, and follow later light/dark switches."""
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(app_icon())

    def refresh(*_args):
        use(app, DARK if _is_dark(app) else LIGHT)

    refresh()
    try:
        app.styleHints().colorSchemeChanged.connect(refresh)
    except AttributeError:
        pass
