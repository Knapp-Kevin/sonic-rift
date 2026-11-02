"""The output list and audio player under the Generate page."""

from datetime import datetime
import os
import re

from PySide6.QtCore import QUrl
from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QAudioOutput
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QCheckBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QListWidget
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QSlider

from this_voice_thing.core import audio_effects
from this_voice_thing.ui.widgets import set_empty_text, set_role

_TAKE_NAME = re.compile(r"^(?P<prefix>.+?)_(?P<date>\d{8})_(?P<time>\d{6})_seed\d+(?P<suffix>_partial|_full_stitched)?"
                        r"\.(?P<ext>\w+)$")


def take_label(filename):
    """A readable name for a generated file: "Take · 30 Oct, 02:45:05" (a document's name instead
    of "Take" when it has one). Files keep their names on disk; other files show as they are."""
    match = _TAKE_NAME.match(filename)
    if not match:
        return filename
    try:
        when = datetime.strptime(match["date"] + match["time"], "%Y%m%d%H%M%S")
    except ValueError:
        return filename
    prefix = match["prefix"]
    name = "Take" if prefix in ("chatterbox", "narration") else prefix
    label = f"{name} \u00b7 {when.day} {when:%b}, {when:%H:%M:%S}"
    if match["suffix"] == "_partial":
        label += " \u00b7 stopped early"
    if match["ext"].lower() != "wav":
        label += f" \u00b7 {match['ext'].upper()}"
    return label


def history_take_labels(paths):
    """Readable labels that distinguish renders created within the same second.

    Assign a stable variation index by filename, independent of filesystem
    enumeration order or modification times. Original filenames remain in tooltips.
    """
    groups = {}
    for path in paths:
        groups.setdefault(take_label(os.path.basename(path)), []).append(path)
    labels = {}
    for label, group in groups.items():
        if len(group) == 1:
            labels[group[0]] = label
        else:
            ordered = sorted(group, key=lambda p: (os.path.basename(p).casefold(), p.casefold()))
            for number, path in enumerate(ordered, 1):
                labels[path] = f"{label} · variation {number}/{len(group)}"
    return labels


def clock(milliseconds):
    """Player time as minutes and seconds ("03:07"). Negative or missing times show as zero."""
    minutes, seconds = divmod(max(0, int(milliseconds or 0)) // 1000, 60)
    return f"{minutes:02d}:{seconds:02d}"


def same_file(a, b):
    """Whether two paths name the same file. Qt hands a Windows path back with forward
    slashes, so a plain string comparison would treat the current take as a new one."""
    if not a or not b:
        return False
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def newest_takes(folder):
    """Audio files in `folder`, newest first (ties by name, so the order is stable)."""
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    paths = [os.path.join(folder, name) for name in names if name.lower().endswith(audio_effects.AUDIO_EXTENSIONS)]
    return sorted(paths, key=lambda path: (-os.path.getmtime(path), path.casefold()))


class Player:
    """Speech's take player: transport, playhead and the list of recent takes.

    One QMediaPlayer (`take_player`) plays the selected take. Qt keeps the position across
    pause and resume, and the playhead slider follows playback except while the user drags it.
    Mixed into the main window."""

    def _build_take_player(self):
        """The media player and its signals (called once, from the window's constructor)."""
        self.take_player = QMediaPlayer()
        self.take_audio_out = QAudioOutput()
        self.take_player.setAudioOutput(self.take_audio_out)
        self.take_player.positionChanged.connect(self._show_position)
        self.take_player.durationChanged.connect(self._show_duration)
        self.take_player.playbackStateChanged.connect(self._show_transport_state)
        self.take_player.errorOccurred.connect(self._report_playback_error)

    def _build_player_card(self):
        card, layout = self._make_card()

        header = QHBoxLayout()
        title = QLabel("Player")
        title.setObjectName("CardTitle")
        self.play_when_done_checkbox = QCheckBox("Auto-play results")
        self.play_when_done_checkbox.setChecked(True)
        self.current_file_label = QLabel("No take selected")
        self.current_file_label.setObjectName("Muted")
        self.current_file_label.setWordWrap(False)
        # A long document name must not set the window's minimum width.
        self.current_file_label.setMinimumWidth(0)
        self.current_file_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        header.addWidget(title)
        header.addSpacing(12)
        header.addWidget(self.play_when_done_checkbox)
        header.addStretch(1)
        header.addWidget(self.current_file_label)
        layout.addLayout(header)

        transport = QHBoxLayout()
        self.take_play_button = self._transport_button("Play", self.toggle_play_pause)
        self.stop_button = self._transport_button("Stop", self.stop_audio)
        self.take_time_label = QLabel(clock(0))
        self.take_length_label = QLabel(clock(0))
        self.take_scrubber = QSlider(Qt.Orientation.Horizontal)
        self.take_scrubber.setEnabled(False)
        self.take_scrubber.sliderMoved.connect(self._scrub)
        self.take_scrubber.sliderReleased.connect(self._finish_scrub)
        for widget in (self.take_play_button, self.stop_button):
            transport.addWidget(widget)
        transport.addSpacing(8)
        transport.addWidget(self.take_time_label)
        transport.addWidget(self.take_scrubber, 1)
        transport.addWidget(self.take_length_label)
        layout.addLayout(transport)

        list_header = QHBoxLayout()
        hint = QLabel("Recent takes (Enter or double-click to play)")
        hint.setObjectName("Muted")
        to_studio = set_role(QPushButton("Add to Studio"), "tertiary")
        to_studio.setToolTip("Add the selected take, or the newest result, to the Studio timeline.")
        to_studio.clicked.connect(self.add_take_to_studio)
        list_header.addWidget(hint, 1)
        list_header.addWidget(to_studio)
        layout.addLayout(list_header)

        self.speech_takes_list = QListWidget()
        set_empty_text(self.speech_takes_list, "Audio you generate appears here. Double-click to play it.")
        # itemActivated fires for Enter as well as a double-click.
        self.speech_takes_list.itemActivated.connect(self.play_selected_from_log)
        self.speech_takes_list.setMinimumHeight(70)
        self.speech_takes_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.speech_takes_list, 1)
        return card

    @staticmethod
    def _transport_button(text, action):
        button = QPushButton(text)
        button.setMinimumWidth(80)
        button.setEnabled(False)
        button.clicked.connect(action)
        return button

    def _set_transport_enabled(self, enabled):
        for control in (self.take_play_button, self.stop_button, self.take_scrubber):
            control.setEnabled(enabled)

    # ---- the take list ----

    def update_output_log(self):
        """Refill the list from the output folder, keeping the selected take selected."""
        current = self.speech_takes_list.currentItem()
        keep = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        paths = newest_takes(self.output_directory)
        labels = history_take_labels(paths)
        self.speech_takes_list.clear()
        for path in paths:
            item = QListWidgetItem(labels[path])
            item.setToolTip(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.speech_takes_list.addItem(item)
            if path == keep:
                self.speech_takes_list.setCurrentItem(item)

    def play_selected_from_log(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Take missing", "That take is no longer in the output folder.")
            self.update_output_log()
            return
        self.load_take(path, f"Playing: {item.text()}", autoplay=True)

    def load_take(self, path, caption, autoplay=False):
        """Make `path` the player's take (shown as `caption`); play it now if `autoplay`."""
        self.current_audio_file = path
        self.current_file_label.setText(caption)
        self.current_file_label.setToolTip(os.path.basename(path))
        self.take_player.setSource(QUrl.fromLocalFile(path))
        self._set_transport_enabled(True)
        if autoplay:
            self.take_player.play()

    # ---- transport ----

    def toggle_play_pause(self):
        player = self.take_player
        if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            player.pause()                  # Qt keeps the position for the next play()
            return
        path = getattr(self, "current_audio_file", None)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Nothing to play", "Generate a take or pick one from the list first.")
            return
        if not same_file(player.source().toLocalFile(), path):
            player.setSource(QUrl.fromLocalFile(path))
        elif player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            player.setPosition(0)           # finished: Play starts it again
        player.play()

    def stop_audio(self):
        self.take_player.stop()

    # ---- playhead ----

    def _scrub(self, milliseconds):
        self.take_player.setPosition(milliseconds)
        self.take_time_label.setText(clock(milliseconds))

    def _finish_scrub(self):
        self.take_player.setPosition(self.take_scrubber.value())

    def _show_position(self, milliseconds):
        if not self.take_scrubber.isSliderDown():   # don't fight the user's drag
            self.take_scrubber.setValue(milliseconds)
        self.take_time_label.setText(clock(milliseconds))

    def _show_duration(self, milliseconds):
        length = max(0, milliseconds)
        self.take_scrubber.setRange(0, length)
        self.take_length_label.setText(clock(length))
        if not length:
            self.take_time_label.setText(clock(0))

    def _show_transport_state(self, state):
        self.take_play_button.setText("Pause" if state == QMediaPlayer.PlaybackState.PlayingState else "Play")

    def _report_playback_error(self, *_error):
        message = self.take_player.errorString()
        if message:
            QMessageBox.warning(self, "Playback", f"This take can't be played: {message}")
        self.set_status_message("Status: Playback failed.")
        self._set_transport_enabled(False)
        self._show_duration(0)
