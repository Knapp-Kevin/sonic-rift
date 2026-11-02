"""Small reusable widgets: the eliding voice chip, labelled sliders, the level meter, and the
design-system pieces every page shares (button roles, menu buttons, empty states)."""

from collections import deque

from PySide6.QtCore import QMargins, QObject, Qt
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import (QAbstractScrollArea, QAbstractSpinBox, QApplication, QComboBox, QDialog,
                               QHBoxLayout, QLabel, QMenu, QSizePolicy, QSlider, QToolButton, QVBoxLayout,
                               QWidget)

from this_voice_thing.ui import theme as ui_theme


class ElidedLabel(QLabel):
    """Shows as much of its text as fits its width, ending in an ellipsis (full text in the
    tooltip), so long text never sets the window's minimum width."""

    def __init__(self, text=""):
        super().__init__()
        self.full_text = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(40)
        self.setText(text)

    def setText(self, text):
        self.full_text = text or ""
        self.setToolTip(self.full_text)
        self._fit()

    def text(self):
        return self.full_text

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self):
        super().setText(self.fontMetrics().elidedText(self.full_text, Qt.TextElideMode.ElideRight,
                                                      max(0, self.width())))


class ElidingChip(QLabel):
    """A label that shortens long text with an ellipsis instead of widening the window."""

    MAX_WIDTH = 180
    PADDING = 28  # the chip's left/right padding and border in the stylesheet

    def __init__(self, text=""):
        super().__init__()
        self.setMaximumWidth(self.MAX_WIDTH)
        self.setText(text)

    def setText(self, text):
        self.full_text = text
        super().setText(self.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight,
                                                      self.MAX_WIDTH - self.PADDING))

    def text(self):
        return self.full_text


class SliderWithValue(QWidget):
    """A horizontal slider over a real-valued range, with its current value shown beside it.

    QSlider only holds integers, so the slider counts steps: position n means n * step."""

    def __init__(self, min_val, max_val, step_val, default_val, value_format="{:.2f}"):
        super().__init__()
        self.step, self.value_format = step_val, value_format
        self.value_label = self._readout(value_format.format(min_val), value_format.format(max_val))
        self.value_label.setText(value_format.format(default_val))
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setSingleStep(1)
        self.slider.setRange(self._steps(min_val), self._steps(max_val))
        self.slider.setValue(self._steps(default_val))
        self.slider.valueChanged.connect(self._show_position)
        row = QHBoxLayout(self)
        row.setContentsMargins(QMargins())
        for part in (self.slider, self.value_label):
            row.addWidget(part)

    @staticmethod
    def _readout(*extremes):
        """A label wide enough for the longest value, so the slider doesn't shift as it changes."""
        label = QLabel()
        label.setMinimumWidth(label.fontMetrics().horizontalAdvance(max(extremes, key=len)) + 6)
        return label

    def _steps(self, value):
        # round(), not int(): int(0.25 / 0.05) truncates to 4.
        return round(value / self.step)

    def _value_at(self, position):
        return position * self.step

    def _show_position(self, position):
        self.value_label.setText(self.value_format.format(self._value_at(position)))

    def get_value(self):
        """The slider's value in real units."""
        return self._value_at(self.slider.value())

    def set_value(self, value):
        self.slider.setValue(self._steps(value))


def dialog_accepted(result):
    return int(getattr(result, "value", result)) == QDialog.DialogCode.Accepted.value


class LevelHistoryWidget(QWidget):
    """Scrolling bar graph of recent microphone peak levels."""

    def __init__(self, bars=72, parent=None):
        super().__init__(parent)
        self.levels = deque([0.0] * bars, maxlen=bars)
        self.active = False
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def push(self, level):
        self.levels.append(level)
        self.update()

    def set_active(self, active):
        self.active = active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        width, height = self.width(), self.height()
        painter.fillRect(self.rect(), self.palette().color(self.backgroundRole()).darker(108))
        if self.active:
            normal = self.palette().color(QPalette.ColorRole.Highlight)
        else:
            normal = self.palette().color(QPalette.ColorRole.Mid)
        bar_width = width / len(self.levels)
        middle = height / 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        theme = ui_theme.current()
        for index, level in enumerate(self.levels):
            # Square-root scaling so normal speech fills a useful part of the height.
            bar_height = max(2.0, min(1.0, level) ** 0.5 * (height - 6))
            top = middle - bar_height / 2
            if level >= 0.98:
                brush = QColor(theme["error_text"])  # clipping stays red
            elif self.active:
                brush = ui_theme.brand_gradient(0, 0, width, 0)  # the waveform wears the brand
            else:
                brush = normal
            painter.setBrush(brush)
            bar = max(1.0, bar_width - 2)
            painter.drawRoundedRect(index * bar_width + 1, top, bar, bar_height, bar / 2, bar / 2)
        painter.end()


# ---------- design system ----------
# Button roles, one meaning everywhere:
#   primary     the single action a card exists for (filled accent; at most one per card)
#   secondary   ordinary actions (outlined; the default)
#   tertiary    quiet, low-stakes actions next to what they affect (text link)
#   destructive actions that remove something (outlined, error-coloured text)
# Rarely used or related actions go in a MenuButton instead of another row of links.

def set_role(button, role):
    """Give a QPushButton one of the roles above."""
    button.setProperty("accent", role == "primary")
    button.setProperty("role", role)
    button.setFlat(role == "tertiary")
    if role == "tertiary":
        button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.style().unpolish(button)
    button.style().polish(button)
    return button


class MenuButton(QToolButton):
    """One button that opens a menu of related actions, so a card keeps one short action row."""

    def __init__(self, text, items=(), parent=None):
        super().__init__(parent)
        self.setObjectName("MenuButton")
        self.setText(text)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setMenu(QMenu(self))
        for item in items:
            self.add(*item) if item else self.menu().addSeparator()

    def add(self, label, callback, tooltip=""):
        action = self.menu().addAction(label)
        action.triggered.connect(lambda _checked=False: callback())
        if tooltip:
            action.setToolTip(tooltip)
        self.menu().setToolTipsVisible(True)
        return action


class _EmptyState(QObject):
    """Shows a muted hint inside an empty list, instead of a large blank box."""

    def __init__(self, view, text):
        super().__init__(view)
        self.view = view
        self.label = QLabel(text, view.viewport())
        self.label.setObjectName("EmptyState")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        model = view.model()
        self.signals = (model.rowsInserted, model.rowsRemoved, model.modelReset, model.layoutChanged)
        for signal in self.signals:
            signal.connect(self.sync)
        view.destroyed.connect(self._detach)   # the model outlives the view while both are torn down
        # A layout keeps the hint the viewport's size in C++. It used to be a Python event filter
        # on the viewport, called for every paint and mouse event; a model-loading thread
        # importing modules at the same moment crashed the app there (PySide's import hook).
        layout = QVBoxLayout(view.viewport())
        layout.setContentsMargins(QMargins())
        layout.addWidget(self.label)
        self.sync()

    def _detach(self, *_args):
        for signal in self.signals:
            try:
                signal.disconnect(self.sync)
            except (RuntimeError, TypeError):
                pass
        self.signals = ()

    def sync(self, *_args):
        try:
            self.label.setVisible(self.view.model().rowCount() == 0)
        except RuntimeError:   # the view is already gone (application shutdown)
            self._detach()


class WheelGuard(QObject):
    """Pages scroll with the wheel. Without this, wheeling over a combo box, spin box or slider
    that isn't focused changes its value (e.g. Live's Source) instead of scrolling the page.
    Those controls take the wheel only once clicked or tabbed into.

    It overrides wheelEvent on those control classes, so Python runs only for wheel events. It
    used to be an application-wide event filter: Python for every event in the app. With an
    engine rendering on another thread, that filter is where the app crashed (access violation),
    reproducibly in voice renders; without it the same renders complete."""


_GUARDED_CONTROLS = (QComboBox, QAbstractSpinBox, QSlider)


def _guarded_wheel(original):
    def wheelEvent(self, event):
        if self.hasFocus():
            return original(self, event)
        parent = self.parentWidget()
        while parent is not None and not isinstance(parent, QAbstractScrollArea):
            parent = parent.parentWidget()
        if parent is not None:
            QApplication.sendEvent(parent.viewport(), event)
        else:
            event.ignore()
    wheelEvent.sonic_rift_guard = True
    return wheelEvent


def install_wheel_guard(app):
    for control in _GUARDED_CONTROLS:
        if not getattr(control.wheelEvent, "sonic_rift_guard", False):
            control.wheelEvent = _guarded_wheel(control.wheelEvent)
    return WheelGuard(app)


def set_empty_text(view, text):
    """Give a list/tree view a hint that shows while it has no rows."""
    existing = getattr(view, "_empty_state", None)
    if existing is not None:
        existing.label.setText(text)
        return existing
    view._empty_state = _EmptyState(view, text)
    return view._empty_state
