"""Choosing and loading models: the model switcher, loading, releasing and voice-mode switches."""

import gc

import torch
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from this_voice_thing.core import model_registry
from this_voice_thing.ui.common import BACKEND_MULTILINGUAL
from this_voice_thing.ui.common import CHATTERBOX_AVAILABLE, needs_chatterbox
from this_voice_thing.ui.common import DEFAULT_MODEL_REPO
from this_voice_thing.ui.common import DEFAULT_MULTILINGUAL_T3_MODEL
from this_voice_thing.ui.common import DUAL_MODE_BACKENDS
from this_voice_thing.ui.common import DUAL_MODE_TYPES
from this_voice_thing.ui.common import WORKER_MODEL_TYPES
from this_voice_thing.ui.threads import ModelLoaderThread

# The status-bar load indicator per state: (range minimum, range maximum, enabled).
# A (0, 0) range is Qt's moving "busy" bar.
LOAD_INDICATOR = {True: (0, 0, True), False: (0, 1, False)}

CPU_FALLBACK_NOTE = "This PC has an NVIDIA GPU, but PyTorch can't use it, so the model runs on the CPU."


def is_default_multilingual(entry):
    """The official multilingual Chatterbox entry: the picker's fallback choice."""
    return entry["repo_id"] == DEFAULT_MODEL_REPO and entry.get("backend") == BACKEND_MULTILINGUAL


def refresh_pick_details(owner):
    """The picker's tooltip and the Language list follow the picked model."""
    for refresh in (owner.refresh_model_repo_tooltip, owner.refresh_language_options):
        refresh()


class ModelLoading:
    """Model switching and loading. Mixed into ChatterboxApp."""

    def start_default_model_load(self):
        """Startup: load the model picked on Speech. Skipped when chatterbox-tts didn't import;
        the user then picks an engine on the Models page."""
        if CHATTERBOX_AVAILABLE:
            self.load_model()
        else:
            print("Startup: chatterbox-tts isn't available, so no model is loaded automatically.")

    def on_model_repo_changed(self, _index):
        entry = self.get_selected_model_entry()
        self.selected_model_repo = entry["repo_id"]
        refresh_pick_details(self)
        if self.entry_key(entry) != self.loaded_entry_key():
            voice = next((item for item in self.voice_library.voices if item.id == self.active_voice_id), None)
            if (voice is not None and voice.has_clip and self.generate_voice_kind() == "design"
                    and model_registry.capability_for(entry) == "clone"):
                self.pending_clip_pick = voice  # a frozen designed voice moves to the cloning model
            self.load_model(entry)

    def get_visible_model_entries(self):
        """Enabled models; the first configured one when every model is switched off."""
        visible = [entry for entry in self.model_entries if entry.get("enabled", True)]
        return visible if visible else self.model_entries[:1]

    def _fill_model_picker(self, combo, visible):
        """Models that can speak the voice in use, grouped by capability under bold headers.
        Each row's data is its position in `visible`; headers have None."""
        fitting = [entry for entry in visible if self.entry_fits_voice(entry)] or visible
        header_font = QFont(combo.font())
        header_font.setBold(True)
        header_colour = QApplication.palette().color(QPalette.ColorRole.Link)
        for _capability, title, members in model_registry.group_by_capability(fitting):
            combo.addItem(title.upper(), None)
            header = combo.model().item(combo.count() - 1)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setFont(header_font)
            header.setForeground(header_colour)
            for entry in members:
                combo.addItem(entry["label"], visible.index(entry))
                hint = f"{entry['repo_id']} · {model_registry.engine_label(entry)}"
                combo.setItemData(combo.count() - 1, hint, Qt.ItemDataRole.ToolTipRole)

    def _picker_row_to_select(self, combo, visible, previous_label):
        """The row picked before the rebuild if it is still there; else the loaded model,
        the official multilingual model, or the first model, whichever is listed first."""
        if previous_label:
            row = combo.findText(previous_label)
            if row >= 0 and combo.itemData(row) is not None:
                return row
        loaded_key = self.loaded_entry_key()
        for wanted in (lambda entry: self.entry_key(entry) == loaded_key, is_default_multilingual):
            position = next((pos for pos, entry in enumerate(visible) if wanted(entry)), None)
            if position is not None:
                row = combo.findData(position)
                if row >= 0:
                    return row
        return combo.findData(0) if visible else -1

    def refresh_model_repo_options(self):
        """Rebuild Speech's Model picker without triggering a model load."""
        combo = self.model_repo_combo
        previous_label = combo.currentText() if combo.count() else None
        visible = self.get_visible_model_entries()
        combo.blockSignals(True)
        try:
            combo.clear()
            self._fill_model_picker(combo, visible)
            row = self._picker_row_to_select(combo, visible, previous_label)
            if row >= 0:
                combo.setCurrentIndex(row)
        finally:
            combo.blockSignals(False)

    def show_loaded_model_in_picker(self):
        """Speech's Model picker names the model that is loaded, however it was loaded (a voice
        pick, the Models page, Voices), not the last one picked there."""
        key = self.loaded_entry_key()
        for index, entry in enumerate(self.get_visible_model_entries()):
            if self.entry_key(entry) == key:
                picker = self.model_repo_combo
                found = picker.findData(index)
                if found >= 0 and found != picker.currentIndex():
                    picker.blockSignals(True)  # already loaded: nothing to load
                    picker.setCurrentIndex(found)
                    picker.blockSignals(False)
                    self.selected_model_repo = entry["repo_id"]
                    refresh_pick_details(self)
                return

    def get_selected_model_entry(self):
        """The model entry of the picker's current row (the first model for a header row)."""
        entries = self.get_visible_model_entries()
        by_position = dict(enumerate(entries))
        return by_position.get(self.model_repo_combo.currentData(), entries[0])

    def refresh_model_repo_tooltip(self):
        entry = self.get_selected_model_entry()
        lines = [f"{entry['repo_id']} · {model_registry.engine_for(entry).label}",
                 "Switching loads the model. Manage models on the Models page."]
        if entry.get("notes"):
            lines += ["", entry["notes"]]
        self.model_repo_combo.setToolTip("\n".join(lines))

    def show_model_loading(self, loading):
        """Busy indicator on, model controls locked while a model loads; the reverse after."""
        loading = bool(loading)
        low, high, active = LOAD_INDICATOR[loading]
        indicator = self.model_load_progress
        indicator.setRange(low, high)
        indicator.setValue(low)
        indicator.setEnabled(active)
        self.model_is_loading = loading
        if hasattr(self, "live_model_label"):
            self.refresh_live_voice_summary()
        for control in (self.model_repo_combo, self.use_preset_button):
            control.setEnabled(not loading)
        self.update_model_details()
        if loading:
            self.language_combo.setDisabled(True)
        else:
            self.refresh_language_options()  # also decides whether the list is usable

    def release_model(self):
        """Free the current model (and stop a Qwen worker) before loading another."""
        old_model, self.model = self.model, None
        if isinstance(old_model, WORKER_MODEL_TYPES):
            old_model.close()
        del old_model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if hasattr(self, "qwen_row"):
            self.update_engine_controls()

    def _set_take_buttons(self, enabled):
        for button in (self.generate_button, self.preview_button):
            button.setEnabled(enabled)

    def _model_switch_blocked(self):
        """True (after telling the user why) when a load can't start now. Frees the music
        model first otherwise: one big model on the GPU at a time."""
        if getattr(self, "model_is_loading", False):
            return True
        if getattr(self, "live_voice_busy", False):
            QMessageBox.information(self, "Live Voice", "Stop Live Voice before switching models.")
            return True
        if getattr(self, "music_model", None) is not None:
            if self.music_busy():
                QMessageBox.information(self, "Music", "Music is being composed. Load the voice model when it finishes.")
                return True
            self.release_music_model()
            self.refresh_music_controls()
        return False

    def load_model(self, selected_entry=None):
        """Load an entry (default: the one picked on Speech) on a background thread. A
        dual-mode model that is already loaded only switches mode."""
        if self._model_switch_blocked():
            return
        entry = selected_entry or self.get_selected_model_entry()
        backend = entry.get("backend", BACKEND_MULTILINGUAL)
        if needs_chatterbox(backend) and not CHATTERBOX_AVAILABLE:
            QMessageBox.critical(
                self, "Chatterbox unavailable",
                "The Chatterbox engine isn't available: the chatterbox-tts library failed to import "
                "(see the log in Settings). Other engines still work; pick one on the Models page.")
            return
        same_model = (backend in DUAL_MODE_BACKENDS and isinstance(self.model, DUAL_MODE_TYPES)
                      and (self.model.backend, self.model.repo_id) == (backend, entry["repo_id"]))
        if same_model:
            self.switch_voice_mode(entry)
        else:
            self._start_model_loader(entry, backend)

    def _start_model_loader(self, entry, backend):
        t3_version = entry.get("multilingual_t3_model", DEFAULT_MULTILINGUAL_T3_MODEL)
        (self.current_model_repo, self.current_model_backend,
         self.current_multilingual_t3_model) = entry["repo_id"], backend, t3_version
        self.set_status_message(
            f"Status: Loading {entry['label']}. A model that isn't downloaded yet "
            "is fetched first; progress appears in the log (Settings)."
        )
        self._set_take_buttons(False)
        self.release_model()
        self.show_model_loading(True)
        self.current_mode = model_registry.entry_mode(entry)
        loader = ModelLoaderThread(entry["repo_id"], backend, t3_version)
        loader.mode = self.current_mode
        loader.model_loaded.connect(self.on_model_loaded)
        loader.error_occurred.connect(self.on_model_load_error)
        self.cuda_runtime_issue = loader.cuda_probe_error
        self.model_loader_thread = loader   # kept so the thread outlives this call
        loader.start()

    def switch_voice_mode(self, entry):
        """Switch a loaded dual-mode model between cloning and design without reloading."""
        self.current_mode = model_registry.entry_mode(entry)
        self.model.set_mode(self.current_mode)
        self.set_status_message(f"Status: Switched to {entry['label']} (same model, no reload). Ready.")
        for refresh in (self.update_engine_controls, self.refresh_language_options, self.update_text_stats,
                        self.render_model_tiles, self.after_voice_model_ready):
            refresh()

    def after_voice_model_ready(self):
        if self.pending_voice is not None:
            self.apply_pending_voice()
        clip_voice = getattr(self, "pending_clip_voice", None)
        if clip_voice is not None:
            self.pending_clip_voice = None
            if self.voice_is_active(clip_voice):
                self.make_voice_clip(clip_voice)
        for step in (self.apply_pending_clip_pick, self.remember_clone_entry, self.refresh_model_repo_options,
                     self.render_voice_tiles, self.run_pending_studio):
            step()
        if hasattr(self, "live_model_label"):
            self.refresh_live_voice_summary()

    def _end_model_load(self, status, ready):
        """Common to success and failure: status, take buttons, indicator, Models page."""
        self.set_status_message(status)
        self._set_take_buttons(ready)
        self.show_model_loading(False)
        self.refresh_models_page()

    def on_model_loaded(self, model, device):
        """The loader thread delivered a model (runs on the UI thread)."""
        self.model, self.device_used, self.model_is_warm = model, device, False
        name = (self.loaded_entry() or {}).get("label") or self.current_model_repo
        place = "the GPU" if str(device).startswith("cuda") else "the CPU"
        gpu_left_idle = bool(self.system_has_nvidia_gpu) and device == "cpu"
        status = f"Status: {name} is ready on {place}."
        if gpu_left_idle:
            status += " " + CPU_FALLBACK_NOTE
        self._end_model_load(status, ready=True)
        for step in (self.update_text_stats, self.update_engine_controls, self.after_voice_model_ready,
                     self.show_loaded_model_in_picker):  # picker sync last: the steps before rebuild it
            step()
        if gpu_left_idle:
            self._explain_cpu_fallback()

    def _explain_cpu_fallback(self):
        reason = self.cuda_runtime_issue or "The installed PyTorch is the CPU-only build."
        QMessageBox.warning(
            self, "Running on the CPU",
            f"{CPU_FALLBACK_NOTE} Generating will be much slower.\n\nReason: {reason}\n\n"
            "Run the installer again to install the CUDA build of PyTorch.")

    def on_model_load_error(self, message):
        """The loader thread failed (runs on the UI thread): no model, say why."""
        self.model = self.pending_studio = None
        self._end_model_load(f"Status: Couldn't load the model. {message}", ready=False)
        if hasattr(self, "live_model_label"):
            self.refresh_live_voice_summary()
        QMessageBox.critical(self, "Model", message)
