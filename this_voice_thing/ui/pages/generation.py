"""Running a generation: preview and full renders, progress, Stop, and the finished take."""

from dataclasses import replace
import os
import time

from PySide6.QtWidgets import QMessageBox

from this_voice_thing.core import documents
from this_voice_thing.ui.common import preview_cut
from this_voice_thing.ui.threads import AudioGeneratorThread
from this_voice_thing.ui.pages.player import clock, take_label

TICK_MS = 1000                 # the countdown next to the progress bar refreshes once a second
IDLE_LABEL, RUNNING_LABEL, STOPPING_LABEL = "Generate", "Stop", "Stopping..."
READY_STATUS = "Status: Ready."
STATUS_ERROR_CHARS = 70        # an error's first line is cut to this length in the status bar
USER_STOP_MARKER = "stopped by user"   # the render thread's wording for a Stop


def error_status(message):
    """(status text, whether it was a Stop) for an error the render thread reported."""
    if USER_STOP_MARKER in message.lower():
        return "Status: Stopped. Nothing was saved.", True
    status = "Status: Couldn't generate the audio."
    if message:
        first_line = next(iter(message.splitlines()), "")
        if len(first_line) > STATUS_ERROR_CHARS:
            first_line = first_line[:STATUS_ERROR_CHARS - 3] + "..."
        status += f" ({first_line})"
    return status, False


def section_span(first, last):
    """'3' for one section, '3–5' for a batch."""
    return str(first) if first == last else f"{first}–{last}"


def render_refusal(owner):
    """Why Speech can't start a render right now, as (status text, dialog text); None: it can."""
    if getattr(owner, "live_voice_busy", False):
        return "Status: Live Voice is generating; stop it before starting a file render.", None
    if owner.api_busy:
        return "Status: Busy with a request from the local API; try again in a moment.", None
    if owner.making_voice_clip():
        return "Status: Making a voice clip; try again when it's done.", None
    if owner.model is None:
        return None, ("Speech", "Load a speech model first: pick one in the Model list or on the Models page.")
    return None


class Generation:
    """Starting, tracking and finishing a generation. Mixed into ChatterboxApp."""

    def _set_speech_controls(self, enabled, include_picker=True):
        """Generate, Preview, Open and (unless a model is loading) the Model picker."""
        for control in (self.generate_button, self.preview_button, self.open_document_button):
            control.setEnabled(enabled)
        if include_picker:
            self.model_repo_combo.setEnabled(enabled and not getattr(self, "model_is_loading", False))

    def handle_generate_stop_toggle(self):
        if getattr(self, "editor_generation_active", False):
            self.set_status_message("Status: The Studio is generating narration; cancel it there "
                                    "or wait for it to finish.")
            return
        if not self.is_generating:
            self.start_generation(preview=False)
            return
        thread = getattr(self, "audio_generator_thread", None)
        if thread is None or not thread.isRunning():
            print("UI: Stop pressed with no render running; resetting Speech.")
            self.on_render_thread_finished()
            return
        print("UI: Stop pressed; asking the render to finish its current section.")
        thread.stop()
        button = self.generate_button
        button.setText(STOPPING_LABEL)
        button.setEnabled(False)
        self.set_status_message(
            "Status: Stopping after the current section. Finished sections will be kept.")

    def preview_text(self):
        """(text, character budget): a selection is previewed whole; otherwise a short
        excerpt from the start of the text, about the length picked next to Preview."""
        selected = self.text_input.textCursor().selectedText().replace(" ", "\n").strip()
        if selected:
            return selected, None
        return documents.excerpt(self.text_input.toPlainText(), self.preview_length_combo.currentData()), None

    def start_generation(self, preview=False):
        if self.is_generating:
            return
        refusal = render_refusal(self)
        if refusal is not None:
            status, dialog = refusal
            if status:
                self.set_status_message(status)
            else:
                QMessageBox.warning(self, *dialog)
            return
        # Keep the settings this render uses even if the app is closed abruptly later.
        self.save_app_settings()
        text, preview_budget = self.preview_text() if preview else (self.text_input.toPlainText().strip(), None)
        if not text:
            QMessageBox.warning(self, "Speech", "Type or open some text to read first.")
            return
        qwen_problem = self.prepare_qwen_generation()
        if qwen_problem:
            QMessageBox.information(self, "Voice", qwen_problem)
            return
        self._plan_render(text, preview, preview_budget)
        self._lock_for_render(preview)
        self._launch_render(text, preview, preview_budget)

    def _plan_render(self, text, preview, preview_budget):
        """Section plan and time estimate for the countdown."""
        self.is_generating = True
        self.generation_is_preview = preview
        self.generation_outcome_shown = False
        self.generation_char_count = len(text)
        plan_entry = self.loaded_entry() or self.get_selected_model_entry()
        lengths = self.section_lengths(text, plan_entry)
        if preview:
            lengths = lengths[:preview_cut(lengths, preview_budget)]
        self.generation_plan = self.batch_plan(plan_entry, lengths)
        self.generation_estimate = sum(step[2] for step in self.generation_plan)
        self.progress_range = None
        self.progress_done_cost = self.progress_done_time = 0.0
        self.generation_started_at = time.monotonic()

    def _lock_for_render(self, preview):
        """Speech while rendering: Generate becomes Stop, everything else waits."""
        self.keep_take_button.setVisible(False)
        for control in (self.preview_button, self.open_document_button, self.model_repo_combo):
            control.setEnabled(False)
        stop_button = self.generate_button
        stop_button.setText(RUNNING_LABEL)
        stop_button.setEnabled(True)
        bar = self.generation_progress
        bar.setValue(0)
        bar.setVisible(True)
        self.activity_label.setText("Previewing..." if preview else "Starting...")
        self.generation_timer.start(TICK_MS)
        self.update_generation_time_display()

    def _launch_render(self, text, preview, preview_budget):
        thread = self._generator_thread(
            text, self.output_directory, self.current_finishing_settings(),
            output_name=self.current_document_name, preview=preview)
        thread.preview_chars = preview_budget
        for signal, handler in ((thread.generation_complete, self.on_generation_complete),
                                (thread.error_occurred, self.on_generation_error),
                                (thread.chunk_generated, self.on_chunk_generated_progress),
                                (thread.section_timed, self.on_section_timed),
                                (thread.finished, self.on_render_thread_finished)):
            signal.connect(handler)
        self.audio_generator_thread = thread
        thread.start()

    def _generator_thread(self, text, output_dir, finishing, output_name=None, preview=False):
        """A render of `text` with the voice and settings currently chosen on Speech."""
        sampling = {
            "exaggeration": self.exaggeration_slider.get_value(),
            "temperature": self.temp_slider.get_value(),
            "cfg_weight": self.cfg_slider.get_value(),
            "language_id": self.language_combo.currentData() or "en",
            "repetition_penalty": self.repetition_penalty,
            "min_p": self.min_p,
            "top_p": self.top_p,
        }
        thread = AudioGeneratorThread(
            self.model, text, self.reference_path, seed=self.seed_input.value(), output_dir=output_dir,
            finishing=finishing, output_name=output_name, preview=preview, **sampling)
        thread.pronunciations = self.pronunciations
        return thread

    # ---- narration for the Studio ----
    def narration_generation_problem(self, voice_id=""):
        """Why the Studio can't render narration right now (None: it can).

        `voice_id` is the voice a script was written for ("" = any): the take must not
        silently come out in a different voice."""
        if self.model is None or getattr(self, "model_is_loading", False):
            return ("Load a speech model in Models first (this window can stay open)."
                    if self.model is None else "A model is still loading; try again when it's ready.")
        if self.model_busy_outside_live() or getattr(self, "live_voice_busy", False):
            return "The voice model is busy (Speech, Live, the local API, Voices or a preview). Try again when it's free."
        if voice_id and voice_id != (self.active_voice_id or ""):
            voice = self.voice_library.get(voice_id)
            if voice is None:
                return ("This script was written for a voice that is no longer in the Voice Library. "
                        "Edit the script to use the current voice, or restore that voice.")
            return (f"This script was written for the voice “{voice.name}”. "
                    "Pick that voice on Speech, then generate again.")
        return None

    def narration_generator(self, text, output_dir):
        """A ready (not started) render of one narration script for the Studio.

        Uses Speech's voice and settings but never changes Speech's text, last take or player.
        Always WAV and no captions: the take is imported into project media afterwards."""
        problem = self.prepare_qwen_generation(text)
        if problem:
            raise ValueError(problem)
        finishing = replace(self.current_finishing_settings(), output_format="WAV", save_subtitles=False)
        return self._generator_thread(text, output_dir, finishing, output_name="narration")

    def begin_editor_generation(self):
        """The model is in use by the Studio: Speech, Live, the API, Voices (Make clip and New
        voice) and model switching all see `is_generating` and wait."""
        self.is_generating = True
        self.editor_generation_active = True
        self._set_speech_controls(False)
        self.set_status_message("Status: Generating narration in the Studio…")

    def end_editor_generation(self):
        if not getattr(self, "editor_generation_active", False):
            return
        self.editor_generation_active = self.is_generating = False
        self._set_speech_controls(True)
        self.update_model_details()
        self.set_status_message(READY_STATUS)

    def keep_preview_take(self):
        if self.last_preview_seed:
            self.seed_input.setValue(self.last_preview_seed)
            self.keep_take_button.setVisible(False)
            self.activity_label.setText(f"Take {self.last_preview_seed} locked")

    def on_render_thread_finished(self):
        """The render thread ended, however it ended: unlock Speech and settle the status."""
        timer = self.generation_timer
        if timer.isActive():
            timer.stop()
        self.is_generating = False
        self.generate_button.setText(IDLE_LABEL)
        self._set_speech_controls(True)
        self.update_model_details()
        self.generation_progress.setVisible(False)
        if not self.keep_take_button.isVisible():
            self.activity_label.clear()
        self.update_text_stats()
        # The complete/error handlers already said how it ended; otherwise (say, the
        # thread died before reporting) leave no "Stopping..." behind.
        if not getattr(self, "generation_outcome_shown", False):
            self.set_status_message(READY_STATUS)
        print("UI: render thread finished; Speech is ready again.")

    def update_generation_time_display(self):
        """Timer tick: refresh the countdown while rendering; the timer stops itself when idle."""
        if self.is_generating:
            self.refresh_progress_activity()
        elif self.generation_timer.isActive():
            self.generation_timer.stop()

    def elapsed_generation_text(self):
        """Time since the current (or last) render started, as mm:ss; None before any render."""
        started = getattr(self, "generation_started_at", None)
        if started is None:
            return None
        return clock((time.monotonic() - started) * 1000)

    def on_chunk_generated_progress(self, first, last, total):
        if not self.is_generating:
            return
        done = first - 1
        elapsed = time.monotonic() - self.generation_started_at
        # Everything before this batch has just finished: calibrate against the plan.
        self.progress_done_cost = sum(cost for _f, end, cost in getattr(self, "generation_plan", [])
                                      if end <= done)
        self.progress_done_time = elapsed
        self.progress_range = (first, last, total)
        self.generation_progress.setMaximum(total)
        self.generation_progress.setValue(done)
        self.set_status_message(f"Status: Generating section {section_span(first, last)} of {total}...")
        self.refresh_progress_activity()

    def refresh_progress_activity(self):
        """Activity text with a countdown; called on progress and every second."""
        if not self.is_generating or not getattr(self, "progress_range", None):
            return
        first, last, total = self.progress_range
        elapsed = time.monotonic() - self.generation_started_at
        estimate = getattr(self, "generation_estimate", 0.0)
        if self.progress_done_cost > 0:
            projected = self.progress_done_time / self.progress_done_cost * estimate
        else:
            projected = estimate
        remaining = max(projected - elapsed, 0.0)
        activity = f"{section_span(first, last)}/{total}"
        if self.generation_is_preview:
            activity = f"Preview {activity}"
        if estimate > 0:
            activity += f" · {self.format_clock(remaining)} left" if remaining >= 1 else " · finishing"
        self.activity_label.setText(activity)

    def _finished_take_status(self, thread, path):
        """Status line for a finished render: preview, partial (after Stop) or full take."""
        elapsed = self.elapsed_generation_text()
        took = f" (took {elapsed})" if elapsed else ""
        name = os.path.basename(path)
        if thread.preview:
            return f"Status: Preview ready{took}."
        if thread.partial_info:
            done, total = thread.partial_info
            missing = f"section {total}" if done + 1 == total else f"sections {done + 1}-{total}"
            return (f"Status: Stopped, so {missing} of {total} weren't generated. "
                    f"Saved the first {done}: {name}")
        captions = f" + {os.path.basename(thread.subtitle_path)}" if thread.subtitle_path else ""
        return f"Status: Saved {take_label(name)}{captions}{took}."

    def on_generation_complete(self, path, _sample_rate):
        """A take was saved (the thread's finished signal follows and unlocks Speech)."""
        thread = self.audio_generator_thread
        self.generation_progress.setValue(self.generation_progress.maximum())
        self.set_status_message(self._finished_take_status(thread, path))
        self.generation_outcome_shown = True
        if thread.preview:
            self.last_preview_seed = thread.actual_seed_used
            self.activity_label.setText(f"Preview take {self.last_preview_seed}")
            self.keep_take_button.setVisible(self.seed_input.value() == 0)
        else:
            # What the take says, for its clip in the Studio (Add to Studio).
            self.take_texts = getattr(self, "take_texts", {})
            self.take_texts[os.path.abspath(path)] = thread.original_text
        caption = f"Latest take: {take_label(os.path.basename(path))}"
        self.load_take(path, caption, autoplay=thread.preview or self.autoplay_checkbox.isChecked())
        self.update_output_log()

    def on_generation_error(self, message):
        """The render ended without a take: a Stop is only noted, a failure is explained."""
        status, was_stop = error_status(message)
        self.set_status_message(status)
        self.generation_outcome_shown = True
        if was_stop:
            print(f"UI: render ended by Stop ({message})")
        else:
            QMessageBox.critical(self, "Speech", message)
