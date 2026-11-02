"""The Generate page: the text and delivery cards, sliders and language options."""

import os

from PySide6.QtCore import QMargins
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMenu
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QProgressBar
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QSpinBox
from PySide6.QtWidgets import QTextEdit
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from this_voice_thing.ui import theme as ui_theme
from this_voice_thing.ui.common import BACKEND_MULTILINGUAL
from this_voice_thing.ui.common import DEFAULT_LANGUAGE_TEST_TEXTS
from this_voice_thing.ui.common import DEFAULT_PREVIEW_CHARS
from this_voice_thing.ui.common import DUAL_MODE_BACKENDS
from this_voice_thing.ui.common import KOKORO_BACKEND
from this_voice_thing.ui.common import PREVIEW_LENGTHS
from this_voice_thing.ui.common import QWEN_BACKEND
from this_voice_thing.ui.common import VIBEVOICE_BACKEND
from this_voice_thing.ui.common import languages_for_backend
from this_voice_thing.ui.widgets import ElidingChip
from this_voice_thing.ui.widgets import SliderWithValue
from this_voice_thing.ui.pages.generation import IDLE_LABEL

# Delivery sliders: (minimum, maximum, step, default) per engine option.
SLIDER_RANGES = {
    "exaggeration": (0.25, 2.0, 0.05, 0.5),
    "cfg_weight": (0.2, 1.0, 0.05, 0.5),
    "temperature": (0.05, 5.0, 0.05, 0.8),
}
MAX_TAKE_NUMBER = 1_000_000_000
# Backends with a real language choice; the English Chatterbox model speaks English only.
MULTI_LANGUAGE_BACKENDS = frozenset({BACKEND_MULTILINGUAL, QWEN_BACKEND, KOKORO_BACKEND,
                                     VIBEVOICE_BACKEND, *DUAL_MODE_BACKENDS})
LANGUAGE_TIP = "Language of the text. The list depends on the selected model."
ENGLISH_ONLY_TIP = "This model speaks English only."


def language_choices(entry):
    """For a model entry: ([(label, language id)], id to select or None, whether the list
    can be changed). The entry's own language wins, then English, then the first listed."""
    names = languages_for_backend(entry.get("backend", BACKEND_MULTILINGUAL))
    rows = [(f"{name} [{code}]", code) for code, name in names.items()]
    codes = [code for _label, code in rows]
    preferred = [code for code in (entry.get("language_id", "en"), "en") if code in codes]
    wanted = (preferred or codes or [None])[0]
    return rows, wanted, entry.get("backend") in MULTI_LANGUAGE_BACKENDS


def sample_text(entry, language):
    """The Sample button's text: the entry's own sample for the language; for multilingual
    Chatterbox the built-in one (English when the language has none); then the entry's
    general sample. None when there is nothing. No language means the entry's own."""
    language = language or entry.get("language_id", "en")
    candidates = [entry.get("test_texts", {}).get(language)]
    if entry.get("backend") == BACKEND_MULTILINGUAL:
        candidates.append(DEFAULT_LANGUAGE_TEST_TEXTS.get(language) or DEFAULT_LANGUAGE_TEST_TEXTS["en"])
    candidates.append(entry.get("test_text"))
    return next((text for text in candidates if text), None)


class GeneratePage:
    """The Generate page cards. Mixed into ChatterboxApp."""

    """The Generate page: cards and the generation run. Mixed into ChatterboxApp."""

    """The Generate page: text, documents, estimates, generation and finishing. Mixed into ChatterboxApp."""

    def _build_generate_page(self):
        generate_page, generate_layout = self._make_page(
            "Speech", "Write or open your text, pick a voice and delivery, then generate.")

        voice_row = QHBoxLayout()
        voice_row.setContentsMargins(ui_theme.SHADOW, 0, ui_theme.SHADOW, 2)
        voice_row.addWidget(QLabel("Voice"))
        self.voice_chip = ElidingChip("Default voice")
        self.voice_chip.setObjectName("VoiceChip")
        self.voice_chip.setTextFormat(Qt.TextFormat.PlainText)
        voice_row.addWidget(self.voice_chip)
        change_voice_button = self._link(QPushButton("Change"))
        change_voice_button.setToolTip("Pick one of your voices, or a model's built-in voices. The model list "
                                       "then shows the models that can speak it.")
        change_voice_button.setMenu(self._build_voice_menu())
        voice_row.addWidget(change_voice_button)
        voice_row.addStretch(1)
        voice_row.addWidget(QLabel("Model"))
        model_picker = QComboBox(minimumWidth=190)
        model_picker.currentIndexChanged.connect(self.on_model_repo_changed)
        voice_row.addWidget(model_picker)
        self.model_repo_combo = model_picker
        generate_layout.addLayout(voice_row)

        generate_layout.addWidget(self._build_text_card(), 3)
        self._build_engine_rows()
        generate_layout.addWidget(self._build_delivery_card())
        generate_layout.addWidget(self._build_player_card(), 2)
        self.pages.addWidget(generate_page)

    def _build_project_page(self):
        """The Studio: where speech, sounds and voices from every page come together on one
        timeline. The project editor lives here as a page (it used to be a separate window)."""
        page = QWidget()
        page.setProperty("noScroll", True)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(QMargins())   # the editor draws its own frame
        self.project_page_layout = layout
        self.pages.addWidget(page)

    def ensure_project_editor(self):
        """The Studio's editor, made the first time it's needed (or again after it closed)."""
        editor = getattr(self, "project_editor", None)
        if editor is None:
            from this_voice_thing.ui.pages.project_editor import ProjectEditorDialog
            editor = ProjectEditorDialog(self, embedded=True)
            editor.finished.connect(self._project_editor_closed)
            self.project_page_layout.addWidget(editor)
            self.project_editor = editor
            editor.show()
        return editor

    def open_project_editor(self):
        """Go to the Studio. Speech, Sounds and the rest stay usable meanwhile."""
        self.ensure_project_editor()
        self.show_page(self.PAGE_PROJECT)
        return self.project_editor

    def _project_editor_closed(self, _result=0):
        editor, self.project_editor = getattr(self, "project_editor", None), None
        if editor is not None:
            editor.deleteLater()

    def close_project_editor(self):
        """Ask the Studio to close (it prompts for unsaved edits and waits for running jobs);
        False if it stays. It asks even when another page is showing."""
        editor = getattr(self, "project_editor", None)
        if editor is None:
            return True
        return editor.close()

    def add_take_to_studio(self):
        """Speech -> Studio: the selected (or latest) take goes onto the timeline."""
        item = self.output_log_listwidget.currentItem()
        if item is None and self.output_log_listwidget.count():
            item = self.output_log_listwidget.item(0)  # newest visible result, not a stale player path
        path = item.data(Qt.ItemDataRole.UserRole) if item is not None else self.current_audio_file
        if not path or not os.path.isfile(path):
            QMessageBox.information(self, "Studio", "Generate a take first, or select one in the list.")
            return
        text = getattr(self, "take_texts", {}).get(os.path.abspath(path), "")
        self.open_project_editor().add_voice_take(path, text=text)

    def add_sound_to_studio(self):
        """Sounds -> Studio: the selected kept sound goes onto the timeline."""
        asset = self.selected_sound_asset()
        if asset is None:
            QMessageBox.information(self, "Studio", "Select a sound in the Sound library first.")
            return
        self.open_project_editor().add_sound(asset)

    def _build_text_card(self):
        text_card, text_card_layout = self._make_card()
        text_header = QHBoxLayout()
        text_title = QLabel("Text")
        text_title.setObjectName("CardTitle")
        text_header.addWidget(text_title)
        self.document_label = QLabel()
        self.document_label.setObjectName("Muted")
        self.document_label.setTextFormat(Qt.TextFormat.PlainText)
        self.document_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text_header.addWidget(self.document_label, 1)
        text_card_layout.addLayout(text_header)
        self.text_input = QTextEdit(
            placeholderText=("Type or paste the text to read, or open a document. Long text is split "
                             "where a reader would pause and joined back together."),
            minimumHeight=90, acceptRichText=False)
        self.text_input.textChanged.connect(self.on_text_changed)
        # Fill the leftover height instead of forcing the page to scroll.
        self.text_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        text_card_layout.addWidget(self.text_input, 1)

        text_status_row = QHBoxLayout()
        text_status_row.setSpacing(10)
        self.estimate_button = self._link(QPushButton())
        self.estimate_button.setToolTip(
            "Estimated generation time with the active model. Click to compare every model.")
        self.estimate_button.clicked.connect(self.show_estimate_menu)
        self.estimate_button.setVisible(False)
        text_status_row.addWidget(self.estimate_button)
        self.text_stats_label = QLabel()
        self.text_stats_label.setObjectName("Muted")
        self.text_stats_label.setTextFormat(Qt.TextFormat.PlainText)
        self.text_stats_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.text_stats_label.setToolTip(
            "Updates as you edit. Times are learned per model from the sections you generate.")
        text_status_row.addWidget(self.text_stats_label, 1)
        self.activity_label = QLabel()
        self.activity_label.setTextFormat(Qt.TextFormat.PlainText)
        self.activity_label.setToolTip("Section being generated / total sections, and time left.")
        text_status_row.addWidget(self.activity_label)
        self.generation_progress = QProgressBar()
        self.generation_progress.setTextVisible(False)
        self.generation_progress.setFixedHeight(8)
        self.generation_progress.setFixedWidth(100)
        self.generation_progress.setVisible(False)
        text_status_row.addWidget(self.generation_progress)
        self.keep_take_button = self._link(QPushButton("Keep this take"))
        self.keep_take_button.setToolTip(
            "Lock the take number used by the preview so the full render matches it.")
        self.keep_take_button.clicked.connect(self.keep_preview_take)
        self.keep_take_button.setVisible(False)
        text_status_row.addWidget(self.keep_take_button)
        status_row_widget = QWidget()
        status_row_widget.setLayout(text_status_row)
        text_status_row.setContentsMargins(0, 0, 0, 0)
        status_row_widget.setFixedHeight(QPushButton("X").sizeHint().height())
        text_card_layout.addWidget(status_row_widget)

        actions = QHBoxLayout()
        self.open_document_button = QPushButton("Open...")
        self.open_document_button.setToolTip("Load a .txt, .md or .docx file, or a Google Doc, to read aloud.")
        open_menu = QMenu(self.open_document_button)
        open_menu.addAction("From this computer...").triggered.connect(lambda _checked=False: self.open_document())
        open_menu.addAction("From Google Docs...").triggered.connect(lambda _checked=False: self.open_google_doc())
        self.open_document_button.setMenu(open_menu)
        self.open_menu = open_menu
        actions.addWidget(self.open_document_button)
        sample_button = QPushButton("Sample")
        sample_button.setToolTip("Fill in a short test sentence for the selected language.")
        sample_button.clicked.connect(self.fill_sample_text)
        actions.addWidget(sample_button)
        self.use_preset_button = sample_button
        actions.addStretch(1)
        self.preview_length_combo = QComboBox()
        for label, characters in PREVIEW_LENGTHS:
            self.preview_length_combo.addItem(label, characters)
        saved_length = self.preview_length_combo.findData(self.app_settings.get("preview_chars", DEFAULT_PREVIEW_CHARS))
        if saved_length < 0:  # a length from an older version
            saved_length = self.preview_length_combo.findData(DEFAULT_PREVIEW_CHARS)
        self.preview_length_combo.setCurrentIndex(saved_length)
        self.preview_length_combo.setToolTip(
            "About how long Preview reads: the opening sentence or two of the text (headings "
            "skipped). Select text to preview exactly that instead.")
        self.preview_length_combo.currentIndexChanged.connect(
            lambda _index: self.app_settings.update(preview_chars=self.preview_length_combo.currentData()))
        self.preview_length_combo.setFixedWidth(84)
        actions.addWidget(self.preview_length_combo)
        self.preview_button = QPushButton("Preview")
        self.preview_button.setToolTip(
            "Generate a short sample with the current settings before rendering everything: "
            "the selected text, or the opening of the text (length chosen on the left).")
        self.preview_button.clicked.connect(lambda: self.start_generation(preview=True))
        self.preview_button.setEnabled(False)
        actions.addWidget(self.preview_button)
        generate = self._accent(QPushButton(IDLE_LABEL))
        generate.clicked.connect(self.handle_generate_stop_toggle)
        # It turns into Stop while rendering: never let Space or Enter (say, meant for the
        # player) press it by accident and cut a long render short.
        generate.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        generate.setEnabled(False)       # until a model is loaded
        generate.setMinimumWidth(140)
        actions.addWidget(generate)
        self.generate_button = generate
        text_card_layout.addLayout(actions)
        return text_card

    def _build_delivery_card(self):
        delivery_card, delivery_layout = self._make_card("Delivery")
        delivery_layout.addWidget(self.qwen_row)
        params_layout = QGridLayout()
        params_layout.setHorizontalSpacing(14)
        params_layout.setVerticalSpacing(8)
        for control_column in (1, 3):
            params_layout.setColumnStretch(control_column, 1)

        def add_control(row, column, title, widget, tooltip):
            label = QLabel(title)
            label.setToolTip(tooltip)
            widget.setToolTip(tooltip)
            params_layout.addWidget(label, row, column)
            params_layout.addWidget(widget, row, column + 1)
            return label

        self.exaggeration_slider = self._create_slider(*SLIDER_RANGES["exaggeration"])
        self.exaggeration_label = add_control(0, 0, "Expressiveness", self.exaggeration_slider,
                    "How animated and emotional the delivery sounds. 0.5 is neutral; "
                    "higher is more dramatic (and often a bit faster). [exaggeration]")
        self.cfg_slider = self._create_slider(*SLIDER_RANGES["cfg_weight"])
        self.cfg_label = add_control(0, 2, "Pacing", self.cfg_slider,
                    "Lower gives slower, more deliberate speech; higher is brisker and "
                    "follows the reference voice's style more closely. Try 0.3 for "
                    "expressive or fast-talking voices. [cfg_weight]")
        self.temp_slider = self._create_slider(*SLIDER_RANGES["temperature"])
        add_control(1, 0, "Variation", self.temp_slider,
                    "How different each take sounds. Higher is livelier but can become "
                    "unstable; lower is steadier and more predictable. [temperature]")
        self.seed_input = QSpinBox(minimum=0, maximum=MAX_TAKE_NUMBER, value=0)
        self.seed_input.setSpecialValueText("New take each time")
        self.seed_input.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.language_combo = languages = QComboBox()
        languages.currentIndexChanged.connect(lambda _i: self.on_language_changed())
        add_control(2, 0, "Language", self.language_combo,
                    "Language of the text. The list depends on the selected model.")
        add_control(1, 2, "Take number", self.seed_input,
                    "Leave on 'New take each time' for a fresh result on every run. Enter a "
                    "number to reproduce the same take exactly; the number used is shown in "
                    "the file name. [seed]")
        params_layout.addWidget(self.qwen_watermark_checkbox, 2, 2, 1, 2)
        delivery_layout.addLayout(params_layout)
        delivery_hint = QLabel(
            "Tip: commas and ellipses add pauses; question marks lift the ending.")
        delivery_hint.setObjectName("Muted")
        delivery_hint.setToolTip("Advanced sampling options are under Model > Sampling.")
        delivery_layout.addWidget(delivery_hint)
        self._build_finishing_panel(delivery_layout)
        return delivery_card

    def _create_slider(self, min_val, max_val, step_val, default_val, value_format="{:.2f}"):
        return SliderWithValue(min_val, max_val, step_val, default_val, value_format)

    def refresh_language_options(self):
        """Fill the Language list for the picked model and select its preferred language."""
        rows, wanted, usable = language_choices(self.get_selected_model_entry())
        combo = self.language_combo
        combo.blockSignals(True)
        try:
            combo.clear()
            for label, code in rows:
                combo.addItem(label, code)
            if wanted is not None:
                combo.setCurrentIndex(combo.findData(wanted))
            combo.setEnabled(usable)
            combo.setToolTip(LANGUAGE_TIP if usable else ENGLISH_ONLY_TIP)
        finally:
            combo.blockSignals(False)

    def fill_sample_text(self):
        """Sample button: replace the text with a short test sentence for the model and language."""
        text = sample_text(self.get_selected_model_entry(), self.language_combo.currentData())
        if not text:
            return
        self.current_document_name = None   # a sample isn't a document
        self.document_label.clear()
        self.text_input.setPlainText(text)
