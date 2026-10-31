"""The Music page: compose instrumentals and songs, audition takes, keep them, send them to Studio."""

import os
import random
import shutil
import tempfile
import threading
import time

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
)

from this_voice_thing.core.music import catalog as music_catalog
from this_voice_thing.core.music import contract, service
from this_voice_thing.core.soundscape import assets as sound_assets
from this_voice_thing.core.soundscape import mastering
from this_voice_thing.engines import music_models
from this_voice_thing.ui.threads import TaskThread
from this_voice_thing.ui.widgets import set_empty_text, set_role

EXPORT_FILTER = "WAV master (*.wav);;OGG Vorbis (*.ogg);;MP3 (*.mp3)"
ENGINE_DECIDES = "Let the model decide"


class MusicJobThread(QThread):
    """Runs one Music request through the service off the UI thread."""

    progressed = Signal(int, int)
    done = Signal(object, str)      # MusicResult or None, error

    def __init__(self, music_service, request, parent=None):
        super().__init__(parent)
        self.service, self.request = music_service, request
        self.cancel_event = threading.Event()

    def run(self):
        try:
            result = self.service.generate(self.request, cancelled=self.cancel_event.is_set,
                                           progress=lambda done, total: self.progressed.emit(done, total))
            self.done.emit(result, "")
        except contract.MusicRequestError as exc:
            self.done.emit(None, "\n".join(exc.problems))
        except Exception as exc:
            self.done.emit(None, f"{type(exc).__name__}: {exc}")


def music_take_summary(index, take):
    parts = [f"Take {chr(ord('A') + index)}", f"seed {take.seed}", f"{take.seconds:.0f} s",
             f"{take.metrics['integrated_lufs']:.0f} LUFS"]
    chose = take.engine_notes
    if chose.get("bpm"):
        parts.append(f"{chose['bpm']} BPM")
    if chose.get("keyscale"):
        parts.append(str(chose["keyscale"]))
    parts.append(f"made in {take.elapsed_seconds:.0f} s")
    return " · ".join(parts)


class MusicPage:
    """Music: one engine at a time, takes to compare, kept music in the Sound library. Mixed into the window."""

    def _build_music_page(self):
        self.music_model = None
        self.music_service = None
        self.music_result = None
        self.music_job = None
        self.music_task = None
        self.music_cancelling = False
        self.music_player = QMediaPlayer(self)
        self.music_audio_output = QAudioOutput(self)
        self.music_player.setAudioOutput(self.music_audio_output)
        self.music_playing_row = None
        self.music_work_dir = tempfile.mkdtemp(prefix="sonic_rift_music_")
        settings = self.app_settings.get("music", {})

        page, layout = self._make_page(
            "Music", "Original instrumentals and songs, made on this PC. Keep the takes you like and "
                     "arrange them in Studio.")

        card, form = self._make_card("Compose")
        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("Model"))
        self.music_engine_combo = QComboBox()
        self.music_engine_combo.setAccessibleName("Music model")
        for engine in music_catalog.ENGINES.values():
            self.music_engine_combo.addItem(engine.label, engine.key)
        engine_row.addWidget(self.music_engine_combo)
        self.music_engine_status = QLabel()
        self.music_engine_status.setObjectName("Muted")
        self.music_engine_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        engine_row.addWidget(self.music_engine_status, 1)
        self.music_engine_button = QPushButton()
        self.music_engine_button.clicked.connect(self.music_engine_action)
        engine_row.addWidget(self.music_engine_button)
        form.addLayout(engine_row)

        form.addWidget(QLabel("Describe the music"))
        self.music_prompt_input = QPlainTextEdit()
        self.music_prompt_input.setAccessibleName("Music description")
        self.music_prompt_input.setFixedHeight(58)
        self.music_prompt_input.setPlainText(settings.get("prompt", ""))
        form.addWidget(self.music_prompt_input)

        style_row = QHBoxLayout()
        self.music_style_inputs = {}
        for key, label, hint in (("genre", "Genre", "e.g. cinematic, lo-fi, folk"),
                                 ("mood", "Mood", "e.g. hopeful, tense"),
                                 ("instrumentation", "Instruments", "e.g. piano, cello, soft drums")):
            style_row.addWidget(QLabel(label))
            field = QLineEdit(settings.get(key, ""))
            field.setPlaceholderText(hint)
            field.setAccessibleName(label)
            style_row.addWidget(field, 1)
            self.music_style_inputs[key] = field
        form.addLayout(style_row)

        options = QHBoxLayout()
        self.music_instrumental_checkbox = QCheckBox("Instrumental")
        self.music_instrumental_checkbox.setChecked(bool(settings.get("instrumental", True)))
        self.music_instrumental_checkbox.setToolTip("No singing. Switch off to write lyrics for a song.")
        self.music_instrumental_checkbox.toggled.connect(self.refresh_music_controls)
        options.addWidget(self.music_instrumental_checkbox)
        options.addSpacing(10)
        options.addWidget(QLabel("Length"))
        self.music_seconds_spin = QSpinBox()
        self.music_seconds_spin.setSuffix(" s")
        self.music_seconds_spin.setAccessibleName("Length in seconds")
        options.addWidget(self.music_seconds_spin)
        options.addWidget(QLabel("Takes"))
        self.music_takes_spin = QSpinBox()
        self.music_takes_spin.setAccessibleName("Number of takes")
        self.music_takes_spin.setToolTip("Several takes with consecutive seeds, to compare.")
        options.addWidget(self.music_takes_spin)
        options.addWidget(QLabel("Seed"))
        self.music_seed_spin = QSpinBox()
        self.music_seed_spin.setRange(0, contract.MAX_SEED)
        self.music_seed_spin.setValue(int(settings.get("seed", 1234)))
        self.music_seed_spin.setAccessibleName("Seed")
        self.music_seed_spin.setToolTip("A starting point for the model. The same seed and settings give a "
                                        "similar take, not always an identical one.")
        options.addWidget(self.music_seed_spin)
        dice = self._link(QPushButton("New seed"))
        dice.clicked.connect(lambda: self.music_seed_spin.setValue(random.randint(0, 999_999)))
        options.addWidget(dice)
        options.addStretch(1)
        form.addLayout(options)

        self.music_lyrics_label = QLabel("Lyrics: your own words. Mark sections with [verse], [chorus], [bridge].")
        self.music_lyrics_label.setObjectName("Muted")
        form.addWidget(self.music_lyrics_label)
        self.music_lyrics_input = QPlainTextEdit()
        self.music_lyrics_input.setAccessibleName("Lyrics")
        self.music_lyrics_input.setFixedHeight(90)
        self.music_lyrics_input.setPlainText(settings.get("lyrics", ""))
        form.addWidget(self.music_lyrics_input)

        musical = QHBoxLayout()
        self.music_bpm_checkbox = QCheckBox("Tempo")
        self.music_bpm_checkbox.setChecked(bool(settings.get("bpm_on", False)))
        self.music_bpm_checkbox.toggled.connect(self.refresh_music_controls)
        musical.addWidget(self.music_bpm_checkbox)
        self.music_bpm_spin = QSpinBox()
        self.music_bpm_spin.setSuffix(" BPM")
        self.music_bpm_spin.setAccessibleName("Tempo in beats per minute")
        musical.addWidget(self.music_bpm_spin)
        musical.addWidget(QLabel("Key"))
        self.music_key_combo = QComboBox()
        self.music_key_combo.setAccessibleName("Key")
        self.music_key_combo.addItem(ENGINE_DECIDES, "")
        for name in contract.KEYS:
            self.music_key_combo.addItem(name, name)
        musical.addWidget(self.music_key_combo)
        musical.addWidget(QLabel("Beats per bar"))
        self.music_meter_combo = QComboBox()
        self.music_meter_combo.setAccessibleName("Beats per bar")
        self.music_meter_combo.addItem(ENGINE_DECIDES, None)
        for beats in contract.TIME_SIGNATURES:
            self.music_meter_combo.addItem(str(beats), beats)
        musical.addWidget(self.music_meter_combo)
        musical.addStretch(1)
        form.addLayout(musical)

        self.music_limits_label = QLabel()
        self.music_limits_label.setObjectName("Muted")
        self.music_limits_label.setWordWrap(True)
        form.addWidget(self.music_limits_label)

        go = QHBoxLayout()
        self.music_status = QLabel()
        self.music_status.setObjectName("Muted")
        self.music_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        go.addWidget(self.music_status, 1)
        self.music_progress = QProgressBar()
        self.music_progress.setFixedHeight(6)
        self.music_progress.setFixedWidth(160)
        self.music_progress.setTextVisible(False)
        self.music_progress.setVisible(False)
        go.addWidget(self.music_progress)
        self.music_cancel_button = QPushButton("Cancel")
        self.music_cancel_button.setEnabled(False)
        self.music_cancel_button.setToolTip("Stop now. The model unloads and starts again on the next Generate.")
        self.music_cancel_button.clicked.connect(self.cancel_music)
        go.addWidget(self.music_cancel_button)
        self.music_generate_button = self._accent(QPushButton("Generate"))
        self.music_generate_button.setMinimumWidth(160)
        self.music_generate_button.clicked.connect(self.start_music)
        go.addWidget(self.music_generate_button)
        form.addLayout(go)
        layout.addWidget(card)

        takes_card, takes_layout = self._make_card("Takes")
        self.music_take_list = QListWidget()
        self.music_take_list.setAccessibleName("Music takes")
        set_empty_text(self.music_take_list, "Takes appear here after Generate. Play them, compare, keep the best.")
        self.music_take_list.setMaximumHeight(120)
        self.music_take_list.itemActivated.connect(lambda _item: self.play_music_take())
        takes_layout.addWidget(self.music_take_list)
        take_row = QHBoxLayout()
        play = QPushButton("Play")
        play.clicked.connect(self.play_music_take)
        take_row.addWidget(play)
        self.music_ab_button = QPushButton("Switch A/B")
        self.music_ab_button.setToolTip("Jump to the other take at the same moment, to compare them.")
        self.music_ab_button.clicked.connect(self.switch_music_take)
        take_row.addWidget(self.music_ab_button)
        stop = QPushButton("Stop playback")
        stop.clicked.connect(self.music_player.stop)
        take_row.addWidget(stop)
        take_row.addStretch(1)
        keep = QPushButton("Keep in library...")
        keep.clicked.connect(lambda: self.keep_music_take())
        take_row.addWidget(keep)
        keep_studio = self._accent(QPushButton("Keep and add to Studio..."))
        keep_studio.clicked.connect(lambda: self.keep_music_take(to_studio=True))
        take_row.addWidget(keep_studio)
        takes_layout.addLayout(take_row)
        layout.addWidget(takes_card)

        library_card, library_layout = self._make_card("Kept music")
        self.music_asset_list = QListWidget()
        self.music_asset_list.setAccessibleName("Kept music")
        set_empty_text(self.music_asset_list, "Music you keep is stored here with how it was made.")
        self.music_asset_list.itemActivated.connect(lambda _item: self.play_music_asset())
        library_layout.addWidget(self.music_asset_list, 1)
        asset_row = QHBoxLayout()
        for label, action in (("Play", self.play_music_asset), ("Rename...", self.rename_music_asset)):
            button = QPushButton(label)
            button.clicked.connect(action)
            asset_row.addWidget(button)
        delete = set_role(QPushButton("Delete"), "destructive")
        delete.clicked.connect(self.delete_music_asset)
        asset_row.addWidget(delete)
        asset_row.addStretch(1)
        export = QPushButton("Export...")
        export.clicked.connect(self.export_music_asset)
        asset_row.addWidget(export)
        to_studio = set_role(QPushButton("Add to Studio"), "primary")
        to_studio.clicked.connect(self.add_music_to_studio)
        asset_row.addWidget(to_studio)
        library_layout.addLayout(asset_row)
        layout.addWidget(library_card, 1)
        self.pages.addWidget(page)

        index = self.music_engine_combo.findData(settings.get("engine", "ace_step_15"))
        self.music_engine_combo.setCurrentIndex(max(0, index))
        self.music_engine_combo.currentIndexChanged.connect(self.refresh_music_controls)
        self.refresh_music_controls()
        self.music_seconds_spin.setValue(int(settings.get("seconds", 30)))
        self.music_takes_spin.setValue(int(settings.get("takes", 2)))
        self.music_bpm_spin.setValue(int(settings.get("bpm", 90)))
        self.music_key_combo.setCurrentIndex(max(0, self.music_key_combo.findData(settings.get("key", ""))))
        meter = self.music_meter_combo.findData(settings.get("time_signature"))
        self.music_meter_combo.setCurrentIndex(max(0, meter))
        self.refresh_music_assets()

    # --- engine state ------------------------------------------------------------------
    def current_music_engine(self):
        return music_catalog.ENGINES[self.music_engine_combo.currentData()]

    def music_busy(self):
        return any(thread is not None and thread.isRunning() for thread in (self.music_job, self.music_task))

    def refresh_music_controls(self, *_args):
        engine = self.current_music_engine()
        caps = engine.capabilities
        self.music_seconds_spin.setRange(int(caps.min_seconds), int(caps.max_seconds))
        self.music_takes_spin.setRange(1, caps.max_candidates)
        self.music_bpm_spin.setRange(*caps.bpm_range)
        self.music_prompt_input.setPlaceholderText(engine.prompt_hint)
        vocal = not self.music_instrumental_checkbox.isChecked()
        self.music_instrumental_checkbox.setEnabled(caps.vocals and caps.instrumental)
        if not caps.vocals:
            self.music_instrumental_checkbox.setToolTip(caps.unsupported.get("vocals", "This model can't sing."))
        for widget in (self.music_lyrics_label, self.music_lyrics_input):
            widget.setVisible(vocal)
        for control, flag, name in ((self.music_bpm_checkbox, caps.bpm, "bpm"), (self.music_key_combo, caps.key, "key"),
                                    (self.music_meter_combo, caps.time_signature, "time_signature")):
            control.setEnabled(flag)
            control.setToolTip("" if flag else caps.unsupported.get(name, f"{engine.label} doesn't offer this."))
        self.music_bpm_spin.setEnabled(caps.bpm and self.music_bpm_checkbox.isChecked())
        self.music_limits_label.setText("Limits: " + " ".join(engine.limits) if engine.limits else "")
        running = self.music_model is not None and self.music_model.key == engine.key
        if not music_models.is_installed(engine.key):
            self.music_engine_status.setText(f"Not installed · {engine.license_name}")
            self.music_engine_button.setText("Install...")
        elif running:
            self.music_engine_status.setText(f"Ready on {self.music_model.device} · {engine.license_name}")
            self.music_engine_button.setText("Unload")
        else:
            self.music_engine_status.setText(f"Installed · starts when you generate · {engine.license_name}")
            self.music_engine_button.setText("Start")
        self.music_engine_status.setToolTip(engine.description + "\n\n" + music_catalog.consent_text(engine))
        busy = self.music_busy()
        self.music_generate_button.setEnabled(not busy)
        self.music_engine_button.setEnabled(not busy)

    def music_engine_action(self):
        engine = self.current_music_engine()
        if self.music_model is not None and self.music_model.key == engine.key:
            self.release_music_model()
            self.refresh_music_controls()
        elif not music_models.is_installed(engine.key):
            self.install_music_engine(engine)
        else:
            self.start_music_engine(engine)

    def install_music_engine(self, engine):
        box = QMessageBox(self)
        box.setWindowTitle(f"Install {engine.label}")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"Install {engine.label}?")
        box.setInformativeText(music_catalog.consent_text(engine))
        accept = box.addButton("Accept license and install", QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() is not accept:
            return
        self.app_settings.setdefault("music", {}).setdefault("accepted_licenses", {})[engine.key] = {
            "license": engine.license_name, "model_revision": engine.model_revision,
            "source_revision": engine.source_revision, "accepted": time.time()}
        self.save_app_settings()
        self.run_music_task(lambda: music_models.install(engine.key, log=print),
                            f"Installing {engine.label} (about {engine.download_gb + engine.env_gb:.0f} GB; "
                            "progress in the log (Settings))...",
                            lambda _result: self.set_status_message(f"Status: {engine.label} installed."))

    def free_gpu_for_music(self, engine):
        """One big model on the GPU at a time: music needs the voice and sound models unloaded.
        Returns False if the user would rather not start it."""
        sound = getattr(self, "sound_model", None)
        voice_on_gpu = self.model is not None and getattr(self, "device_used", "cpu") != "cpu"
        if sound is None and not voice_on_gpu:
            return True
        if hasattr(self, "sound_busy") and self.sound_busy():
            QMessageBox.information(self, "Music", "A sound model is busy. Start music when it finishes.")
            return False
        loaded = " and ".join(name for name, on in (("a voice model", voice_on_gpu), ("a sound model", sound))
                              if on)
        answer = QMessageBox.question(
            self, engine.label,
            f"{engine.label} needs most of the GPU, and {loaded} is loaded. Unload it to start the music "
            "model? (Reload it later from the Models page.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes:
            return False
        if sound is not None:
            self.release_sound_model()
            self.refresh_sound_engine()
        if voice_on_gpu:
            self.release_model()
        return True

    def start_music_engine(self, engine, then=None):
        if getattr(self, "live_voice_busy", False):
            QMessageBox.information(self, "Music", "Stop Live Voice before starting a music model.")
            return
        if not self.free_gpu_for_music(engine):
            return

        def started(model):
            self.release_music_model()
            self.music_model = model
            self.music_service = service.MusicService(model, self.music_work_dir)
            self.set_status_message(f"Status: {engine.label} is ready on {model.device} "
                                    f"(loaded in {model.load_seconds:.0f} s).")
            if then:
                then()
        self.run_music_task(lambda: music_models.MusicModel(engine.key, log=print),
                            f"Starting {engine.label}...", started)

    def run_music_task(self, function, status, on_success):
        self.set_status_message(f"Status: {status}")
        self.music_status.setText(status)
        self.music_progress.setRange(0, 0)
        self.music_progress.setVisible(True)
        thread = TaskThread(function, self)

        def done(result, error):
            self.music_progress.setVisible(False)
            self.music_task = None
            self.music_status.setText("")
            if error:
                self.set_status_message(f"Status: {error}")
                QMessageBox.warning(self, "Music", f"{error}\n\nDetails are in the log (Settings).")
            else:
                on_success(result)
            self.refresh_music_controls()

        thread.done.connect(done)
        self.music_task = thread
        thread.start()
        self.refresh_music_controls()

    def release_music_model(self):
        model = self.music_model
        self.music_model = self.music_service = None
        if model is not None:
            try:
                model.close()
            except Exception as exc:
                print(f"Music model didn't close cleanly: {exc}")

    # --- generating --------------------------------------------------------------------
    def music_request(self):
        engine = self.current_music_engine()
        instrumental = self.music_instrumental_checkbox.isChecked()
        return contract.MusicRequest(
            engine=engine.key, prompt=self.music_prompt_input.toPlainText().strip(),
            seconds=float(self.music_seconds_spin.value()), instrumental=instrumental,
            lyrics="" if instrumental else self.music_lyrics_input.toPlainText().strip(),
            candidates=self.music_takes_spin.value(), seed=self.music_seed_spin.value(),
            bpm=self.music_bpm_spin.value() if self.music_bpm_checkbox.isChecked() and engine.capabilities.bpm else None,
            key=self.music_key_combo.currentData() or "", time_signature=self.music_meter_combo.currentData(),
            **{key: field.text().strip() for key, field in self.music_style_inputs.items()})

    def save_music_settings(self, request):
        stored = self.app_settings.setdefault("music", {})
        stored.update(engine=request.engine, prompt=request.prompt, seconds=request.seconds,
                      instrumental=request.instrumental, lyrics=self.music_lyrics_input.toPlainText(),
                      takes=request.candidates, seed=request.seed, bpm_on=self.music_bpm_checkbox.isChecked(),
                      bpm=self.music_bpm_spin.value(), key=request.key, time_signature=request.time_signature,
                      genre=request.genre, mood=request.mood, instrumentation=request.instrumentation)

    def start_music(self):
        if self.music_busy():
            return
        request = self.music_request()
        engine = music_catalog.ENGINES[request.engine]
        problems = contract.validate(request, engine.capabilities)
        if problems:
            QMessageBox.information(self, "Music", "\n".join(problems))
            return
        if not music_models.is_installed(engine.key):
            self.install_music_engine(engine)
            return
        if self.music_model is not None and not self.music_model.alive():
            self.music_model = self.music_service = None      # its worker ended (e.g. cancelled)
        if self.music_model is None or self.music_model.key != engine.key:
            self.start_music_engine(engine, then=self.start_music)
            return
        self.save_music_settings(request)
        self.music_player.stop()
        self.music_player.setSource(QUrl())
        self.music_take_list.clear()
        if self.music_result is not None:
            self.music_service.discard_takes(self.music_result)   # replaced; kept ones are in the library
        self.music_result = None
        self.music_cancelling = False
        self.music_progress.setRange(0, request.candidates)
        self.music_progress.setValue(0)
        self.music_progress.setVisible(True)
        self.music_cancel_button.setEnabled(True)
        self.music_started = time.monotonic()
        job = MusicJobThread(self.music_service, request, self)
        job.progressed.connect(self.on_music_progress)
        job.done.connect(self.on_music_done)
        self.music_job = job
        job.start()
        self.music_status.setText(f"Composing take A of {request.candidates}...")
        self.set_status_message(f"Status: Composing {request.candidates} take(s) with {engine.label}...")
        self.refresh_music_controls()

    def on_music_progress(self, done, total):
        self.music_progress.setValue(done)
        if done < total:
            self.music_status.setText(f"Composing take {chr(ord('A') + done)} of {total}...")

    def cancel_music(self):
        job = self.music_job
        if job is None or not job.isRunning():
            return
        self.music_cancelling = True
        job.cancel_event.set()
        self.music_cancel_button.setEnabled(False)
        self.music_status.setText("Cancelling...")
        if self.music_model is not None:
            self.music_model.terminate()       # a take can run for a minute; don't wait for it

    def on_music_done(self, result, error):
        self.music_job = None
        self.music_progress.setVisible(False)
        self.music_cancel_button.setEnabled(False)
        if self.music_model is not None and not self.music_model.alive():
            self.music_model = self.music_service = None     # cancelled mid-take: it restarts next time
        self.refresh_music_controls()
        if error and not self.music_cancelling:
            self.music_status.setText("Couldn't compose; see the log (Settings).")
            self.set_status_message(f"Status: Couldn't compose: {error}")
            QMessageBox.warning(self, "Music", f"Couldn't compose the music.\n\n{error}")
            return
        takes = result.takes if result is not None else []
        self.music_result = result
        for index, take in enumerate(takes):
            self.music_take_list.addItem(QListWidgetItem(music_take_summary(index, take)))
        if takes:
            self.music_take_list.setCurrentRow(0)
        elapsed = time.monotonic() - self.music_started
        if self.music_cancelling or (result is not None and result.cancelled):
            self.music_status.setText(f"Cancelled after {elapsed:.0f} s; {len(takes)} take(s) finished.")
            self.set_status_message("Status: Music cancelled.")
        else:
            self.music_status.setText(f"{len(takes)} take(s) in {elapsed:.0f} s")
            self.set_status_message(f"Status: {len(takes)} take(s) ready. Play and compare them, then keep the best.")

    # --- auditioning -------------------------------------------------------------------
    def music_takes(self):
        return self.music_result.takes if self.music_result is not None else []

    def play_music_take(self, row=None, position_ms=0):
        takes = self.music_takes()
        row = self.music_take_list.currentRow() if row is None else row
        if not 0 <= row < len(takes):
            return
        self.music_player.stop()
        self.music_player.setSource(QUrl.fromLocalFile(takes[row].path))
        if position_ms:
            self.music_player.setPosition(position_ms)
        self.music_player.play()
        self.music_playing_row = row

    def switch_music_take(self):
        """A/B: play the other take (or the next one) from the same moment."""
        takes = self.music_takes()
        if len(takes) < 2:
            return
        current = self.music_playing_row if self.music_playing_row is not None else self.music_take_list.currentRow()
        selected = self.music_take_list.currentRow()
        target = selected if selected != current else (current + 1) % len(takes)
        position = self.music_player.position()
        self.music_take_list.setCurrentRow(target)
        self.play_music_take(target, position)

    def keep_music_take(self, to_studio=False):
        takes, row = self.music_takes(), self.music_take_list.currentRow()
        if not 0 <= row < len(takes):
            QMessageBox.information(self, "Music", "Generate music and select a take first.")
            return
        request = self.music_result.request
        name, ok = QInputDialog.getText(self, "Keep music", "Name", text=request.prompt[:40])
        if not ok:
            return
        try:
            asset = service.keep(self.sound_library, self.music_result, takes[row], name)
        except Exception as exc:
            QMessageBox.warning(self, "Music", f"Couldn't keep the take.\n\n{exc}")
            return
        self.refresh_music_assets(select=asset.id)
        if hasattr(self, "refresh_sound_assets"):
            self.refresh_sound_assets()
        self.set_status_message(f"Status: Kept “{asset.name}”.")
        if to_studio:
            self.open_project_editor().add_sound(asset)

    # --- kept music ---------------------------------------------------------------------
    def music_assets(self):
        return [asset for asset in self.sound_library.assets if asset.kind == "music"]

    def refresh_music_assets(self, select=None):
        self.music_asset_list.clear()
        for asset in self.music_assets():
            engine = music_catalog.ENGINES.get(asset.engine)
            item = QListWidgetItem(" · ".join((asset.name, engine.label if engine else asset.engine,
                                               f"{asset.seconds:.0f} s")))
            item.setData(Qt.ItemDataRole.UserRole, asset.id)
            item.setToolTip(self.sound_library.provenance_text(asset))
            self.music_asset_list.addItem(item)
            if asset.id == select:
                self.music_asset_list.setCurrentItem(item)

    def selected_music_asset(self):
        item = self.music_asset_list.currentItem()
        asset_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        return self.sound_library.get(asset_id) if asset_id else None

    def play_music_asset(self):
        asset = self.selected_music_asset()
        if asset:
            self.music_player.stop()
            self.music_player.setSource(QUrl.fromLocalFile(self.sound_library.path(asset)))
            self.music_player.play()
            self.music_playing_row = None

    def rename_music_asset(self):
        asset = self.selected_music_asset()
        if not asset:
            return
        name, ok = QInputDialog.getText(self, "Rename music", "Name", text=asset.name)
        if ok and name.strip():
            self.sound_library.rename(asset.id, name)
            self.refresh_music_assets(select=asset.id)

    def delete_music_asset(self):
        asset = self.selected_music_asset()
        if not asset:
            return
        if QMessageBox.question(self, "Delete music", f"Delete “{asset.name}” and its audio?") \
                == QMessageBox.StandardButton.Yes:
            self.music_player.stop()
            self.sound_library.remove(asset.id)
            self.refresh_music_assets()
            if hasattr(self, "refresh_sound_assets"):
                self.refresh_sound_assets()

    def export_music_asset(self):
        asset = self.selected_music_asset()
        if not asset:
            return
        path, chosen = QFileDialog.getSaveFileName(
            self, "Export music", os.path.join(self.output_directory, sound_assets.safe_stem(asset.name)),
            EXPORT_FILTER)
        if not path:
            return
        fmt = os.path.splitext(path)[1].lower().lstrip(".")
        if fmt not in mastering.EXPORT_FORMATS:
            fmt = "ogg" if "ogg" in chosen.lower() else "mp3" if "mp3" in chosen.lower() else "wav"
        saved = self.sound_library.export(asset.id, os.path.splitext(path)[0], (fmt,))[fmt]
        self.set_status_message(f"Status: Exported {os.path.basename(saved)}.")

    def add_music_to_studio(self):
        asset = self.selected_music_asset()
        if asset is None:
            QMessageBox.information(self, "Studio", "Select kept music first.")
            return
        self.open_project_editor().add_sound(asset)

    def shut_down_music(self):
        """On close: stop a running job at once and unload the model."""
        if self.music_job is not None and self.music_job.isRunning():
            self.music_cancelling = True
            self.music_job.cancel_event.set()
            if self.music_model is not None:
                self.music_model.terminate()
            self.music_job.wait(15000)
        self.release_music_model()
        self.music_player.stop()
        self.music_player.setSource(QUrl())
        shutil.rmtree(self.music_work_dir, ignore_errors=True)
