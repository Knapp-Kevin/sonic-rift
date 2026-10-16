"""Small reusable widgets: the eliding voice chip, labelled sliders, the level meter, and the
design-system pieces every page shares (button roles, menu buttons, empty states)."""

from collections import deque

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import (QAbstractScrollArea, QAbstractSpinBox, QApplication, QComboBox, QDialog,
                               QHBoxLayout, QLabel, QMenu, QSizePolicy, QSlider, QToolButton, QWidget)

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
    def __init__(self, min_val, max_val, step_val, default_val, value_format="{:.2f}"):
        super().__init__()
        self._step_val = step_val
        self._value_format = value_format
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        # round(), not int(): e.g. int(0.25 / 0.05) truncates to 4.
        self.slider.setMinimum(round(min_val / step_val))
        self.slider.setMaximum(round(max_val / step_val))
        self.slider.setValue(round(default_val / step_val))
        self.slider.setSingleStep(1)
        self.value_label = QLabel(value_format.format(default_val))
        widest = max((value_format.format(v) for v in (min_val, max_val)), key=len)
        self.value_label.setMinimumWidth(self.value_label.fontMetrics().horizontalAdvance(widest) + 6)
        self.slider.valueChanged.connect(
            lambda val: self.value_label.setText(self._value_format.format(val * self._step_val))
        )
        layout.addWidget(self.slider)
        layout.addWidget(self.value_label)

    def get_value(self):
        return self.slider.value() * self._step_val

    def set_value(self, value):
        self.slider.setValue(round(value / self._step_val))


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
        view.viewport().installEventFilter(self)
        self.sync()

    def _detach(self, *_args):
        for signal in self.signals:
            try:
                signal.disconnect(self.sync)
            except (RuntimeError, TypeError):
                pass
        self.signals = ()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize:
            self.label.resize(watched.size())
        return False

    def sync(self, *_args):
        try:
            self.label.resize(self.view.viewport().size())
            self.label.setVisible(self.view.model().rowCount() == 0)
        except RuntimeError:   # the view is already gone (application shutdown)
            self._detach()


class WheelGuard(QObject):
    """Pages scroll with the wheel. Without this, wheeling over a combo box, spin box or slider
    that isn't focused changes its value (e.g. Live's Source) instead of scrolling the page.
    Those controls take the wheel only once clicked or tabbed into."""

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.Wheel or not isinstance(watched, (QComboBox, QAbstractSpinBox, QSlider)):
            return False
        if watched.hasFocus():
            return False
        parent = watched.parentWidget()
        while parent is not None and not isinstance(parent, QAbstractScrollArea):
            parent = parent.parentWidget()
        if parent is not None:
            QApplication.sendEvent(parent.viewport(), event)
        return True


def install_wheel_guard(app):
    guard = WheelGuard(app)
    app.installEventFilter(guard)
    return guard


def set_empty_text(view, text):
    """Give a list/tree view a hint that shows while it has no rows."""
    existing = getattr(view, "_empty_state", None)
    if existing is not None:
        existing.label.setText(text)
        return existing
    view._empty_state = _EmptyState(view, text)
    return view._empty_state
