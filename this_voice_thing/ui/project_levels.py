"""Studio's level controls: the slider each timeline lane header carries, and Mix settings
(how far sound tracks duck under voices). They only show and ask; the editor makes the edits."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout

from this_voice_thing.core.audio_project import DEFAULT_DUCK_DB

STEP = 0.5                  # dB per slider step
GAIN_RANGE = (-40.0, 12.0)  # the slider's span; Edit… still reaches the model's -60…+24
DUCK_RANGE = (-24.0, 0.0)   # deeper than -24 dB is valid in the model, not useful here


def gain_text(db):
    return f"{db:+.1f} dB".replace("-", "−")


def duck_text(db):
    return "Off" if db == 0 else f"{db:.0f} dB".replace("-", "−")


class LevelSlider(QSlider):
    """A horizontal slider in STEP-dB units that says when a change is final: on release after a
    drag, or at once for keys, the wheel and clicks on the groove."""

    committed = Signal(float)

    def __init__(self, low, high, accessible_name, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(round(low / STEP), round(high / STEP))
        self.setSingleStep(1)
        self.setPageStep(round(3 / STEP))
        self.setAccessibleName(accessible_name)
        self.quiet = False      # set while the view itself moves the slider
        self.sliderReleased.connect(lambda: self.committed.emit(self.db()))
        self.valueChanged.connect(self._changed)

    def db(self):
        return self.value() * STEP

    def set_db(self, db):
        if self.isSliderDown():
            return              # don't yank it from under the pointer
        self.quiet = True
        self.setValue(round(max(self.minimum() * STEP, min(self.maximum() * STEP, db)) / STEP))
        self.quiet = False

    def _changed(self, _value):
        if not self.quiet and not self.isSliderDown():
            self.committed.emit(self.db())


class MixSettingsDialog(QDialog):
    """Project › Mix settings…: how far music and sound tracks dip while a voice speaks."""

    def __init__(self, duck_db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mix settings")
        layout = QVBoxLayout(self)
        label = QLabel("Duck under voices")
        label.setObjectName("CardTitle")
        layout.addWidget(label)
        hint = QLabel(f"How far music and sound tracks dip while someone speaks. "
                      f"Off keeps them level. The default is {duck_text(DEFAULT_DUCK_DB)}.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        row = QHBoxLayout()
        self.slider = LevelSlider(*DUCK_RANGE, "Duck under voices")
        self.slider.setPageStep(round(2 / STEP))
        self.slider.setMinimumWidth(260)
        self.slider.set_db(duck_db)
        self.value = QLabel(duck_text(duck_db))
        self.value.setMinimumWidth(56)
        self.slider.valueChanged.connect(lambda _v: self.value.setText(duck_text(self.slider.db())))
        row.addWidget(self.slider, 1)
        row.addWidget(self.value)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def duck_db(self):
        return self.slider.db()
