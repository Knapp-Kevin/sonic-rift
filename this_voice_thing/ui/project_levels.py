"""Studio's Levels panel: a gain slider and mute switch per track, how far sound tracks dip under
voices, and Check balance. It only shows and asks; the editor makes each edit (one undo step per
slider release) and runs the balance check off the UI thread."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSlider,
    QVBoxLayout, QWidget,
)

from this_voice_thing.core.audio_project import DUCK_DB_RANGE

STEP = 0.5                  # dB per slider step
GAIN_RANGE = (-40.0, 12.0)  # the slider's span; the Edit… dialog still reaches the model's -60…+24


def gain_text(db):
    return f"{db:+.1f} dB".replace("-", "−")


def duck_text(db):
    return "Off" if db == 0 else f"{db:.0f} dB".replace("-", "−")


class _Slider(QSlider):
    """A horizontal slider in STEP-dB units that says when a change is final: on release after a
    drag, or at once for keys, the wheel and clicks on the groove."""

    committed = Signal(float)

    def __init__(self, low, high, accessible_name):
        super().__init__(Qt.Orientation.Horizontal)
        self.setRange(round(low / STEP), round(high / STEP))
        self.setSingleStep(1)
        self.setPageStep(round(3 / STEP))
        self.setAccessibleName(accessible_name)
        self.setMinimumWidth(140)
        self.quiet = False      # set while the panel itself moves the slider
        self.sliderReleased.connect(lambda: self.committed.emit(self.db()))
        self.valueChanged.connect(self._changed)

    def db(self):
        return self.value() * STEP

    def set_db(self, db):
        self.quiet = True
        self.setValue(round(max(self.minimum() * STEP, min(self.maximum() * STEP, db)) / STEP))
        self.quiet = False

    def _changed(self, _value):
        if not self.quiet and not self.isSliderDown():
            self.committed.emit(self.db())


class LevelsPanel(QFrame):
    gainCommitted = Signal(str, float)      # track id, dB
    muteToggled = Signal(str, bool)
    duckCommitted = Signal(float)
    checkRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LevelsPanel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 6, 10, 6)
        outer.setSpacing(4)
        title = QLabel("Levels")
        title.setObjectName("CardTitle")
        outer.addWidget(title)
        hint = QLabel("Drag to balance each track. Play mix and Export use these levels.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        self.rows_widget = QWidget()
        self.grid = QGridLayout(self.rows_widget)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(2)
        self.grid.setColumnStretch(1, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.rows_widget)
        outer.addWidget(scroll, 1)

        duck_row = QHBoxLayout()
        duck_label = QLabel("Duck under voices")
        duck_label.setToolTip("How far music and sound tracks dip while someone speaks. Off keeps them level.")
        duck_row.addWidget(duck_label)
        self.duck_slider = _Slider(DUCK_DB_RANGE[0], DUCK_DB_RANGE[1], "Duck under voices")
        self.duck_slider.setRange(round(-24 / STEP), 0)        # deeper than -24 dB is in the model, not useful here
        self.duck_slider.setPageStep(round(2 / STEP))
        self.duck_slider.committed.connect(self.duckCommitted.emit)
        self.duck_slider.valueChanged.connect(lambda _v: self.duck_value.setText(duck_text(self.duck_slider.db())))
        duck_row.addWidget(self.duck_slider, 1)
        self.duck_value = QLabel()
        self.duck_value.setMinimumWidth(56)
        self.duck_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        duck_row.addWidget(self.duck_value)
        outer.addLayout(duck_row)

        check_row = QHBoxLayout()
        self.check_button = QPushButton("Check balance")
        self.check_button.setToolTip("Measure how loud each track is while the voices speak and on its own.")
        self.check_button.clicked.connect(self.checkRequested.emit)
        check_row.addWidget(self.check_button)
        self.summary = QLabel()
        self.summary.setObjectName("Muted")
        self.summary.setWordWrap(True)
        check_row.addWidget(self.summary, 1)
        outer.addLayout(check_row)

        self.rows = {}          # track id -> dict of widgets
        self._layout_key = None

    # ---- showing the project ----
    def set_project(self, project):
        key = tuple((t.id, t.name, t.kind) for t in project.tracks)
        if key != self._layout_key:
            self._rebuild(project)
            self._layout_key = key
        for track in project.tracks:
            row = self.rows[track.id]
            if not row["slider"].isSliderDown():
                row["slider"].set_db(track.gain_db)
            row["value"].setText(gain_text(track.gain_db))
            row["mute"].blockSignals(True)
            row["mute"].setChecked(track.muted)
            row["mute"].blockSignals(False)
            row["slider"].setEnabled(not track.muted)
        if not self.duck_slider.isSliderDown():
            self.duck_slider.set_db(project.duck_db)
        self.duck_value.setText(duck_text(project.duck_db))

    def _rebuild(self, project):
        while self.grid.count():
            widget = self.grid.takeAt(0).widget()
            if widget is not None:
                widget.hide()               # deleteLater alone left the old row painted until it ran
                widget.setParent(None)
                widget.deleteLater()
        self.rows = {}
        if not project.tracks:
            empty = QLabel("Add tracks to balance them.")
            empty.setObjectName("Muted")
            self.grid.addWidget(empty, 0, 0, 1, 4)
            return
        for index, track in enumerate(project.tracks):
            name = QLabel(track.name)
            name.setToolTip(f"{track.name} ({track.kind})")
            name.setMinimumWidth(90)
            name.setMaximumWidth(170)
            slider = _Slider(*GAIN_RANGE, f"{track.name} level")
            slider.committed.connect(lambda db, track_id=track.id: self.gainCommitted.emit(track_id, db))
            value = QLabel()
            value.setMinimumWidth(64)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            slider.valueChanged.connect(lambda _v, s=slider, label=value: label.setText(gain_text(s.db())))
            mute = QCheckBox("Mute")
            mute.setAccessibleName(f"Mute {track.name}")
            mute.toggled.connect(lambda on, track_id=track.id: self.muteToggled.emit(track_id, on))
            readout = QLabel()
            readout.setObjectName("Muted")
            row = index * 2
            self.grid.addWidget(name, row, 0)
            self.grid.addWidget(slider, row, 1)
            self.grid.addWidget(value, row, 2)
            self.grid.addWidget(mute, row, 3)
            self.grid.addWidget(readout, row + 1, 1, 1, 3)
            self.rows[track.id] = {"name": name, "slider": slider, "value": value, "mute": mute, "readout": readout}

    # ---- balance readouts ----
    def show_balance(self, texts, summary):
        for track_id, row in self.rows.items():
            row["readout"].setText(texts.get(track_id, ""))
        self.summary.setText(summary)

    def clear_balance(self, summary=""):
        self.show_balance({}, summary)

    def set_checking(self, checking):
        self.check_button.setEnabled(not checking)
        if checking:
            self.summary.setText("Measuring the mix…")
