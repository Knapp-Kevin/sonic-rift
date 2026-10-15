"""The Soundscape page: ambience and sound effects, kept in the Asset Library."""

import os
import random
import tempfile
import time

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
)

from this_voice_thing.core.soundscape import assets as sound_assets
from this_voice_thing.core.soundscape import catalog, mastering, procedural, render
from this_voice_thing.engines import sound_models
from this_voice_thing.ui.threads import SoundRenderThread, TaskThread

EXPORT_FILTER = "WAV master (*.wav);;OGG Vorbis (*.ogg);;MP3 (*.mp3)"


def take_summary(index, candidate):
    metrics = candidate.metrics
    parts = [f"Take {index + 1}", f"seed {candidate.seed}", f"{metrics['seconds']:.1f} s",
             f"{metrics['integrated_lufs']:.1f} LUFS", f"peak {metrics['true_peak_db']:.1f} dBTP"]
    if "loudness_range_db" in metrics:
        parts.append(f"swings {metrics['loudness_range_db']:.0f} dB")
    if "seam" in metrics:
        parts.append("no seam detected" if metrics["seam"]["seamless"] else "seam detected: listen to the loop")
    return " · ".join(parts)


class SoundscapePage:
    """Soundscape: make ambience and effects with any sound engine. Mixed into ChatterboxApp."""

    def _build_soundscape_page(self):
        self.sound_library = sound_assets.AssetLibrary(self.script_dir)
        self.sound_model = None
        self.sound_takes = []
        self.sound_render_thread = None
        self.sound_task_thread = None
        self.sound_temp_dir = tempfile.mkdtemp(prefix="soundscape_")
        self.sound_player = QMediaPlayer(self)
        self.sound_audio_output = QAudioOutput(self)
        self.sound_player.setAudioOutput(self.sound_audio_output)
        settings = self.app_settings.get("soundscape", {})

        page, layout = self._make_page(
            "Sounds", "Ambience, loops and sound effects, and the library of sounds you've kept.")

        make_card, make_layout = self._make_card("Make a sound")
        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("Engine"))
        self.sound_engine_combo = QComboBox()
        for engine in catalog.ENGINES.values():
            self.sound_engine_combo.addItem(engine.label, engine.key)
        engine_row.addWidget(self.sound_engine_combo)
        self.sound_engine_status = QLabel()
        self.sound_engine_status.setObjectName("Muted")
        self.sound_engine_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        engine_row.addWidget(self.sound_engine_status, 1)
        self.sound_engine_button = QPushButton()
        self.sound_engine_button.clicked.connect(self.sound_engine_action)
        engine_row.addWidget(self.sound_engine_button)
        make_layout.addLayout(engine_row)

        self.sound_preset_row = QHBoxLayout()
        self.sound_preset_label = QLabel("Preset")
        self.sound_preset_row.addWidget(self.sound_preset_label)
        self.sound_preset_combo = QComboBox()
        for preset in procedural.PRESETS.values():
            self.sound_preset_combo.addItem(preset.label, preset.key)
        self.sound_preset_combo.currentIndexChanged.connect(self.on_sound_preset_changed)
        self.sound_preset_row.addWidget(self.sound_preset_combo, 1)
        self.sound_prompt_input = QLineEdit()
        self.sound_prompt_input.setPlaceholderText("Describe the sound")
        self.sound_preset_row.addWidget(self.sound_prompt_input, 1)
        make_layout.addLayout(self.sound_preset_row)

        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Length"))
        self.sound_seconds_spin = QDoubleSpinBox()
        self.sound_seconds_spin.setRange(1.0, 600.0)
        self.sound_seconds_spin.setDecimals(1)
        self.sound_seconds_spin.setSuffix(" s")
        self.sound_seconds_spin.setValue(float(settings.get("seconds", 60.0)))
        options_row.addWidget(self.sound_seconds_spin)
        self.sound_loop_checkbox = QCheckBox("Seamless loop")
        self.sound_loop_checkbox.setChecked(bool(settings.get("loop", True)))
        self.sound_loop_checkbox.setToolTip("Make the end join the start with no audible seam.")
        options_row.addWidget(self.sound_loop_checkbox)
        options_row.addWidget(QLabel("Seed"))
        self.sound_seed_spin = QSpinBox()
        self.sound_seed_spin.setRange(0, 2_000_000_000)
        self.sound_seed_spin.setValue(int(settings.get("seed", 53)))
        self.sound_seed_spin.setToolTip("The same engine, settings and seed give the same sound again.")
        options_row.addWidget(self.sound_seed_spin)
        dice = self._link(QPushButton("New seed"))
        dice.clicked.connect(lambda: self.sound_seed_spin.setValue(random.randint(0, 999_999)))
        options_row.addWidget(dice)
        options_row.addWidget(QLabel("Takes"))
        self.sound_takes_spin = QSpinBox()
        self.sound_takes_spin.setRange(1, 6)
        self.sound_takes_spin.setValue(int(settings.get("takes", 3)))
        self.sound_takes_spin.setToolTip("Several takes with consecutive seeds, to pick from.")
        options_row.addWidget(self.sound_takes_spin)
        options_row.addStretch(1)
        make_layout.addLayout(options_row)

        shaping_row = QHBoxLayout()
        shaping_row.addWidget(QLabel("Loudness"))
        self.sound_lufs_spin = QDoubleSpinBox()
        self.sound_lufs_spin.setRange(-40.0, -10.0)
        self.sound_lufs_spin.setDecimals(1)
        self.sound_lufs_spin.setSingleStep(1.0)
        self.sound_lufs_spin.setSuffix(" LUFS")
        self.sound_lufs_spin.setToolTip("How loud the finished sound is. Calm background ambience sits around "
                                        "-24 to -27 LUFS; lower is quieter.")
        shaping_row.addWidget(self.sound_lufs_spin)
        self.sound_soft_start_checkbox = QCheckBox("Start soft")
        self.sound_soft_start_checkbox.setChecked(bool(settings.get("start_soft", True)))
        self.sound_soft_start_checkbox.setToolTip(
            "Begin the loop at its quietest moment, so it opens softly and builds. Nothing is faded; "
            "the loop stays seamless.")
        shaping_row.addWidget(self.sound_soft_start_checkbox)
        self.sound_even_checkbox = QCheckBox("Even out dynamics")
        self.sound_even_checkbox.setChecked(bool(settings.get("even_dynamics", True)))
        self.sound_even_checkbox.setToolTip(
            "Gently level the loud and quiet stretches over several seconds, so swells don't jump out at "
            "high volume. Each take shows how much its level swings.")
        shaping_row.addWidget(self.sound_even_checkbox)
        shaping_row.addStretch(1)
        make_layout.addLayout(shaping_row)

        self.sound_sliders = {}
        self.sound_slider_row = QHBoxLayout()
        for key, label in (("intensity", "Intensity"), ("brightness", "Brightness"), ("width", "Width")):
            caption = QLabel(label)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(round(100 * float(settings.get(key, 0.5)))))
            self.sound_slider_row.addWidget(caption)
            self.sound_slider_row.addWidget(slider, 1)
            self.sound_sliders[key] = (caption, slider)
        make_layout.addLayout(self.sound_slider_row)

        generate_row = QHBoxLayout()
        self.sound_status = QLabel()
        self.sound_status.setObjectName("Muted")
        self.sound_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        generate_row.addWidget(self.sound_status, 1)
        self.sound_progress = QProgressBar()
        self.sound_progress.setFixedHeight(6)
        self.sound_progress.setTextVisible(False)
        self.sound_progress.setVisible(False)
        self.sound_progress.setFixedWidth(160)
        generate_row.addWidget(self.sound_progress)
        self.sound_stop_button = QPushButton("Stop")
        self.sound_stop_button.setEnabled(False)
        self.sound_stop_button.clicked.connect(self.stop_sound_render)
        generate_row.addWidget(self.sound_stop_button)
        self.sound_generate_button = self._accent(QPushButton("Generate"))
        self.sound_generate_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sound_generate_button.setMinimumWidth(160)
        self.sound_generate_button.clicked.connect(self.start_sound_render)
        generate_row.addWidget(self.sound_generate_button)
        make_layout.addLayout(generate_row)
        layout.addWidget(make_card)

        takes_card, takes_layout = self._make_card("Takes")
        self.sound_take_list = QListWidget()
        self.sound_take_list.setMaximumHeight(130)
        self.sound_take_list.itemDoubleClicked.connect(lambda _item: self.play_sound_take())
        takes_layout.addWidget(self.sound_take_list)
        take_row = QHBoxLayout()
        play_take = QPushButton("Play")
        play_take.setToolTip("Loops play repeatedly, so you can listen for the seam.")
        play_take.clicked.connect(self.play_sound_take)
        take_row.addWidget(play_take)
        stop_play = QPushButton("Stop playback")
        stop_play.clicked.connect(self.sound_player.stop)
        take_row.addWidget(stop_play)
        take_row.addStretch(1)
        export_take = QPushButton("Export...")
        export_take.clicked.connect(self.export_sound_take)
        take_row.addWidget(export_take)
        keep_take = self._accent(QPushButton("Keep in library..."))
        keep_take.clicked.connect(self.keep_sound_take)
        take_row.addWidget(keep_take)
        takes_layout.addLayout(take_row)
        layout.addWidget(takes_card)

        library_card, library_layout = self._make_card("Asset Library")
        self.sound_asset_list = QListWidget()
        self.sound_asset_list.itemDoubleClicked.connect(lambda _item: self.play_sound_asset())
        library_layout.addWidget(self.sound_asset_list, 1)
        asset_row = QHBoxLayout()
        play_asset = QPushButton("Play")
        play_asset.clicked.connect(self.play_sound_asset)
        asset_row.addWidget(play_asset)
        rename_asset = QPushButton("Rename...")
        rename_asset.clicked.connect(self.rename_sound_asset)
        asset_row.addWidget(rename_asset)
        delete_asset = QPushButton("Delete")
        delete_asset.clicked.connect(self.delete_sound_asset)
        asset_row.addWidget(delete_asset)
        asset_row.addStretch(1)
        export_asset = QPushButton("Export...")
        export_asset.clicked.connect(self.export_sound_asset)
        asset_row.addWidget(export_asset)
        library_layout.addLayout(asset_row)
        layout.addWidget(library_card, 1)
        self.pages.addWidget(page)

        index = self.sound_engine_combo.findData(settings.get("engine", "procedural"))
        self.sound_engine_combo.setCurrentIndex(max(0, index))
        preset_index = self.sound_preset_combo.findData(settings.get("preset", "ocean"))
        self.sound_preset_combo.setCurrentIndex(max(0, preset_index))
        self.sound_prompt_input.setText(settings.get("prompt", ""))
        self.sound_engine_combo.currentIndexChanged.connect(self.refresh_sound_engine)
        self.refresh_sound_engine()
        self.on_sound_preset_changed()
        self.refresh_sound_assets()

    # --- engine state ------------------------------------------------------------------
    def current_sound_engine(self):
        return catalog.ENGINES[self.sound_engine_combo.currentData()]

    def sound_busy(self):
        return any(thread is not None and thread.isRunning()
                   for thread in (self.sound_render_thread, self.sound_task_thread))

    def refresh_sound_engine(self):
        engine = self.current_sound_engine()
        procedural_engine = engine.kind == "procedural"
        self.sound_preset_combo.setVisible(procedural_engine)
        self.sound_preset_label.setText("Preset" if procedural_engine else "Prompt")
        self.sound_prompt_input.setVisible(not procedural_engine)
        self.sound_prompt_input.setPlaceholderText(engine.prompt_hint or "Describe the sound")
        for key, (caption, slider) in self.sound_sliders.items():
            # Mono models get stereo width from the app; their other character comes from the prompt.
            shown = procedural_engine or (key == "width" and engine.channels == 1)
            caption.setVisible(shown)
            slider.setVisible(shown)
        self.sound_sliders["width"][1].setToolTip(
            "" if procedural_engine else f"{engine.label} makes mono sound; this spreads it into stereo "
                                         "without changing the mono mix.")
        running = self.sound_model is not None and self.sound_model.key == engine.key
        if procedural_engine:
            self.sound_engine_status.setText("Runs on your CPU; nothing to download.")
            self.sound_engine_button.setVisible(False)
        elif not sound_models.is_installed(engine.key):
            self.sound_engine_status.setText(f"Not installed · {engine.license_name}")
            self.sound_engine_button.setText("Install...")
            self.sound_engine_button.setVisible(True)
        elif running:
            self.sound_engine_status.setText(f"Ready on {self.sound_model.device} · {engine.license_name}")
            self.sound_engine_button.setText("Unload")
            self.sound_engine_button.setVisible(True)
        else:
            self.sound_engine_status.setText(f"Installed · starts when you generate · {engine.license_name}")
            self.sound_engine_button.setText("Start")
            self.sound_engine_button.setVisible(True)
        self.sound_engine_status.setToolTip(engine.description + "\n\n" + (
            catalog.consent_text(engine) if engine.kind == "model" else ""))
        self.sound_seconds_spin.setMaximum(600.0 if procedural_engine else 300.0)
        self.on_sound_preset_changed()
        busy = self.sound_busy()
        self.sound_generate_button.setEnabled(not busy)
        self.sound_engine_button.setEnabled(not busy)

    def on_sound_preset_changed(self, *_args):
        if not hasattr(self, "sound_sliders"):
            return
        engine = self.current_sound_engine()
        preset = procedural.PRESETS[self.sound_preset_combo.currentData()]
        self.sound_sliders["intensity"][0].setText(preset.intensity_label)
        one_shot = engine.kind == "procedural" and not preset.loop
        self.sound_seconds_spin.setEnabled(not one_shot)
        self.sound_loop_checkbox.setEnabled(not one_shot)
        self.sound_soft_start_checkbox.setEnabled(not one_shot)
        self.sound_even_checkbox.setEnabled(not one_shot)
        # Each preset (and each model) suggests its own level; the user can change it.
        self.sound_lufs_spin.setValue(preset.target_lufs if engine.kind == "procedural"
                                      else render.DEFAULT_MODEL_LUFS)

    def sound_engine_action(self):
        engine = self.current_sound_engine()
        if self.sound_model is not None and self.sound_model.key == engine.key:
            self.release_sound_model()
            self.refresh_sound_engine()
        elif not sound_models.is_installed(engine.key):
            self.install_sound_engine(engine)
        else:
            self.start_sound_engine(engine)

    def install_sound_engine(self, engine):
        box = QMessageBox(self)
        box.setWindowTitle(f"Install {engine.label}")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"Install {engine.label}?")
        box.setInformativeText(catalog.consent_text(engine))
        accept = box.addButton("Accept license and install", QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() is not accept:
            return
        if engine.gated and not os.environ.get("HF_TOKEN"):
            QMessageBox.information(
                self, engine.label,
                f"{engine.label} is gated on Hugging Face. Accept its terms at "
                f"https://huggingface.co/{engine.repo_id} while signed in, then add your Hugging Face "
                "token on the Models page. The environment installs now; the model downloads when it "
                "first starts.")
        self.app_settings.setdefault("soundscape", {}).setdefault("accepted_licenses", {})[engine.key] = \
            engine.license_name
        self.save_app_settings()
        self.run_sound_task(lambda: sound_models.install(engine.key, log=print),
                            f"Installing {engine.label} (several GB; progress in the log (Settings))...",
                            lambda _result: self.set_status_message(f"Status: {engine.label} installed."))

    def free_gpu_for(self, engine):
        """A big sound model and a loaded voice model don't fit on one 16 GB GPU together.
        Returns False if the user would rather not start it."""
        if engine.vram_gb < 8 or self.model is None or getattr(self, "device_used", "cpu") == "cpu":
            return True
        answer = QMessageBox.question(
            self, engine.label,
            f"{engine.label} needs about {engine.vram_gb:.0f} GB of GPU memory, and a voice model is "
            "loaded. Unload the voice model first? (Reload it from the Models page afterwards.)\n\n"
            "Starting alongside it can make each take many times slower.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Yes:
            self.release_model()
        return True

    def start_sound_engine(self, engine, then=None):
        if not self.free_gpu_for(engine):
            return

        def started(model):
            self.release_sound_model()
            self.sound_model = model
            self.set_status_message(f"Status: {engine.label} is ready on {model.device}.")
            if then:
                then()
        self.run_sound_task(lambda: sound_models.SoundModel(engine.key, log=print),
                            f"Starting {engine.label} (the first start downloads the model)...", started)

    def run_sound_task(self, function, status, on_success):
        self.set_status_message(f"Status: {status}")
        self.sound_engine_status.setText(status)
        self.sound_progress.setRange(0, 0)
        self.sound_progress.setVisible(True)
        thread = TaskThread(function, self)

        def done(result, error):
            self.sound_progress.setVisible(False)
            self.sound_task_thread = None
            if error:
                self.set_status_message(f"Status: {error}")
                QMessageBox.warning(self, "Sounds", f"{error}\n\nDetails are in the log (Settings).")
            else:
                on_success(result)
            self.refresh_sound_engine()

        thread.done.connect(done)
        self.sound_task_thread = thread
        thread.start()
        self.refresh_sound_engine()

    def release_sound_model(self):
        if self.sound_model is not None:
            try:
                self.sound_model.close()
            finally:
                self.sound_model = None

    # --- generating --------------------------------------------------------------------
    def sound_request(self):
        engine = self.current_sound_engine()
        sliders = {key: slider.value() / 100.0 for key, (_caption, slider) in self.sound_sliders.items()}
        return render.SoundRequest(
            engine=engine.key, seconds=self.sound_seconds_spin.value(),
            loop=self.sound_loop_checkbox.isChecked(), seed=self.sound_seed_spin.value(),
            candidates=self.sound_takes_spin.value(), preset=self.sound_preset_combo.currentData(),
            prompt=self.sound_prompt_input.text().strip(), target_lufs=self.sound_lufs_spin.value(),
            start_soft=self.sound_soft_start_checkbox.isChecked(),
            even_dynamics=self.sound_even_checkbox.isChecked(), **sliders)

    def save_sound_settings(self, request):
        stored = self.app_settings.setdefault("soundscape", {})
        stored.update(engine=request.engine, preset=request.preset, prompt=request.prompt,
                      seconds=request.seconds, loop=request.loop, seed=request.seed, takes=request.candidates,
                      intensity=request.intensity, brightness=request.brightness, width=request.width,
                      start_soft=request.start_soft, even_dynamics=request.even_dynamics)

    def start_sound_render(self):
        if self.sound_busy():
            return
        request = self.sound_request()
        engine = catalog.ENGINES[request.engine]
        if engine.kind == "model":
            if not request.prompt:
                QMessageBox.information(self, "Sounds", "Describe the sound you want first.")
                return
            if not sound_models.is_installed(engine.key):
                self.install_sound_engine(engine)
                return
            if self.sound_model is None or self.sound_model.key != engine.key:
                self.start_sound_engine(engine, then=self.start_sound_render)
                return
        self.save_sound_settings(request)
        self.sound_takes = []
        self.sound_take_list.clear()
        self.sound_progress.setRange(0, request.candidates)
        self.sound_progress.setValue(0)
        self.sound_progress.setVisible(True)
        self.sound_stop_button.setEnabled(True)
        thread = SoundRenderThread(request, self.sound_model if engine.kind == "model" else None, self)
        self.sound_render_started = time.monotonic()
        self.sound_status.setText(f"Making take 1 of {request.candidates}...")
        thread.progressed.connect(self.on_sound_progress)
        thread.done.connect(lambda results, error: self.on_sound_render_done(request, results, error))
        self.sound_render_thread = thread
        thread.start()
        self.set_status_message(f"Status: Generating {request.candidates} take(s) with {engine.label}...")
        self.refresh_sound_engine()

    def on_sound_progress(self, done, total):
        self.sound_progress.setValue(done)
        if done < total:
            self.sound_status.setText(f"Making take {done + 1} of {total}...")

    def stop_sound_render(self):
        if self.sound_render_thread is not None:
            self.sound_render_thread.stop()
            self.set_status_message("Status: Stopping after the current take...")

    def on_sound_render_done(self, request, results, error):
        self.sound_render_thread = None
        self.sound_progress.setVisible(False)
        self.sound_stop_button.setEnabled(False)
        self.refresh_sound_engine()
        if error:
            self.sound_status.setText("Couldn't generate; see the log (Settings).")
            self.set_status_message(f"Status: Couldn't generate: {error}")
            QMessageBox.warning(self, "Sounds", f"Couldn't generate the sound.\n\n{error}")
            return
        self.sound_status.setText(f"{len(results)} take(s) in "
                                  f"{time.monotonic() - self.sound_render_started:.1f} s")
        self.sound_takes = [(request, candidate) for candidate in results]
        for index, (_request, candidate) in enumerate(self.sound_takes):
            item = QListWidgetItem(take_summary(index, candidate))
            self.sound_take_list.addItem(item)
        if self.sound_takes:
            self.sound_take_list.setCurrentRow(0)
        self.set_status_message(f"Status: {len(results)} take(s) ready. Play them, then keep the best.")

    def selected_sound_take(self):
        row = self.sound_take_list.currentRow()
        return self.sound_takes[row] if 0 <= row < len(self.sound_takes) else (None, None)

    def play_sound_file(self, path, loop):
        self.sound_player.stop()
        self.sound_player.setSource(QUrl.fromLocalFile(path))
        self.sound_player.setLoops(QMediaPlayer.Loops.Infinite if loop else 1)
        self.sound_player.play()

    def play_sound_take(self):
        request, candidate = self.selected_sound_take()
        if candidate is None:
            return
        path = os.path.join(self.sound_temp_dir, f"take_{self.sound_take_list.currentRow()}_{candidate.seed}.wav")
        if not os.path.exists(path):
            mastering.write_audio(path, candidate.audio, candidate.sample_rate, "wav")
        self.play_sound_file(path, "seam" in candidate.metrics)

    def keep_sound_take(self):
        request, candidate = self.selected_sound_take()
        if candidate is None:
            return
        engine = catalog.ENGINES[request.engine]
        default = (procedural.PRESETS[request.preset].label if engine.kind == "procedural"
                   else request.prompt[:40])
        name, ok = QInputDialog.getText(self, "Keep in library", "Name", text=default)
        if not ok:
            return
        provenance = dict(seed=candidate.seed, license=engine.license_name, metrics=candidate.metrics,
                          settings={"seconds": request.seconds, "loop": request.loop,
                                    "target_lufs": render.target_lufs(request), "start_soft": request.start_soft,
                                    "even_dynamics": request.even_dynamics})
        if engine.kind == "procedural":
            provenance.update(preset=request.preset)
            provenance["settings"].update(intensity=request.intensity, brightness=request.brightness,
                                          width=request.width)
        else:
            provenance.update(model=engine.repo_id, prompt=request.prompt)
            provenance["settings"].update(sound_models.SPECS[engine.key].defaults)
        asset = self.sound_library.add(candidate.audio, candidate.sample_rate, name, engine.key,
                                       "seam" in candidate.metrics, **provenance)
        self.refresh_sound_assets(select=asset.id)
        self.set_status_message(f"Status: Kept “{asset.name}” in the Asset Library.")

    def ask_sound_export_path(self, stem):
        path, chosen = QFileDialog.getSaveFileName(
            self, "Export sound", os.path.join(self.output_directory, stem), EXPORT_FILTER)
        if not path:
            return None, None
        fmt = os.path.splitext(path)[1].lower().lstrip(".")
        if fmt not in mastering.EXPORT_FORMATS:
            fmt = "ogg" if "ogg" in chosen.lower() else "mp3" if "mp3" in chosen.lower() else "wav"
        return os.path.splitext(path)[0], fmt

    def export_sound_take(self):
        request, candidate = self.selected_sound_take()
        if candidate is None:
            return
        base, fmt = self.ask_sound_export_path(f"sound_seed{candidate.seed}")
        if base:
            saved = mastering.export(candidate.audio, candidate.sample_rate, base, (fmt,))[fmt]
            self.set_status_message(f"Status: Exported {os.path.basename(saved)}.")

    # --- library -----------------------------------------------------------------------
    def refresh_sound_assets(self, select=None):
        self.sound_asset_list.clear()
        for asset in self.sound_library.assets:
            engine = catalog.ENGINES.get(asset.engine)
            parts = [asset.name, engine.label if engine else asset.engine, f"{asset.seconds:.1f} s"]
            if asset.loop:
                parts.append("loop")
            label = " · ".join(parts)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, asset.id)
            item.setToolTip(self.sound_library.provenance_text(asset))
            self.sound_asset_list.addItem(item)
            if asset.id == select:
                self.sound_asset_list.setCurrentItem(item)
        if not self.sound_library.assets:
            placeholder = QListWidgetItem("Sounds you keep appear here, with how they were made.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.sound_asset_list.addItem(placeholder)

    def selected_sound_asset(self):
        item = self.sound_asset_list.currentItem()
        asset_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        return self.sound_library.get(asset_id) if asset_id else None

    def play_sound_asset(self):
        asset = self.selected_sound_asset()
        if asset:
            self.play_sound_file(self.sound_library.path(asset), asset.loop)

    def rename_sound_asset(self):
        asset = self.selected_sound_asset()
        if not asset:
            return
        name, ok = QInputDialog.getText(self, "Rename sound", "Name", text=asset.name)
        if ok and name.strip():
            self.sound_library.rename(asset.id, name)
            self.refresh_sound_assets(select=asset.id)

    def delete_sound_asset(self):
        asset = self.selected_sound_asset()
        if not asset:
            return
        answer = QMessageBox.question(self, "Delete sound", f"Delete “{asset.name}” and its audio?")
        if answer == QMessageBox.StandardButton.Yes:
            self.sound_player.stop()
            self.sound_library.remove(asset.id)
            self.refresh_sound_assets()

    def export_sound_asset(self):
        asset = self.selected_sound_asset()
        if not asset:
            return
        base, fmt = self.ask_sound_export_path(sound_assets.safe_stem(asset.name))
        if base:
            saved = self.sound_library.export(asset.id, base, (fmt,))[fmt]
            self.set_status_message(f"Status: Exported {os.path.basename(saved)}.")
