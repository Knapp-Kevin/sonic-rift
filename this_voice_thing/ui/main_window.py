"""The main window: sidebar, pages and app settings. Run as __main__ to start the app."""

import base64
import os
import sys

import torch
from PySide6.QtCore import QMargins, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QStackedWidget,
    QStyledItemDelegate,
    QTabBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from this_voice_thing import __version__, paths
from this_voice_thing.core import config_io, pronunciation, transcription, voice_library
from this_voice_thing.integrations import google_docs, local_api
from this_voice_thing.ui import common, taskbar
from this_voice_thing.ui import theme as ui_theme
from this_voice_thing.ui.api_bridge import ApiBridge
from this_voice_thing.ui.common import (
    APP_SETTINGS_FILENAME, BACKEND_MULTILINGUAL, CHATTERBOX_AVAILABLE, DEFAULT_MODEL_REPO,
    DEFAULT_MULTILINGUAL_T3_MODEL, MODEL_CONFIG_FILENAME, REFERENCE_RECORDINGS_DIRNAME, WORKER_MODEL_TYPES,
    has_system_nvidia_gpu, load_models_config, resolve_multilingual_t3_model,
    write_json_payload,
)
from this_voice_thing.ui.pages.advanced import AdvancedPage
from this_voice_thing.ui.pages.api_server import ApiServer
from this_voice_thing.ui.pages.discover import Discover
from this_voice_thing.ui.pages.documents import Documents
from this_voice_thing.ui.pages.engine_controls import EngineControls
from this_voice_thing.ui.pages.estimates import Estimates
from this_voice_thing.ui.pages.finishing import Finishing
from this_voice_thing.ui.pages.generate import GeneratePage
from this_voice_thing.ui.pages.generation import Generation
from this_voice_thing.ui.pages.library import Library
from this_voice_thing.ui.pages.live_voice import LiveVoicePage
from this_voice_thing.ui.pages.model_loading import ModelLoading
from this_voice_thing.ui.pages.model_settings import ModelSettings
from this_voice_thing.ui.pages.music import MusicPage
from this_voice_thing.ui.pages.models import ModelPage
from this_voice_thing.ui.pages.performance import PerformancePage
from this_voice_thing.ui.pages.player import Player
from this_voice_thing.ui.pages.pronunciations import Pronunciations
from this_voice_thing.ui.pages.recording import Recording
from this_voice_thing.ui.pages.soundscape import SoundscapePage
from this_voice_thing.ui.pages.studio import StudioPage
from this_voice_thing.ui.pages.transcribe import TranscribePage
from this_voice_thing.ui.pages.voice import VoicePage
from this_voice_thing.ui.pages.voice_picker import VoicePicker
from this_voice_thing.ui.pages.voice_use import VoiceUse
from this_voice_thing.ui.widgets import install_wheel_guard


class SidebarDelegate(QStyledItemDelegate):
    """Paints sidebar group headings (MAKE, PERFORM, SETUP) as small muted labels; the
    stylesheet colours every item the same, so headings are drawn here instead."""

    def paint(self, painter, option, index):
        if index.data(Qt.ItemDataRole.UserRole) is not None:
            return super().paint(painter, option, index)
        painter.save()
        painter.setFont(index.data(Qt.ItemDataRole.FontRole) or option.font)
        painter.setPen(QColor(ui_theme.current()["muted"]))
        rect = option.rect.adjusted(14, 0, -8, -6)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom), index.data())
        painter.restore()


# app_settings.json keys for the window's size, position and state. Settings files written by
# older versions use the same keys, so they restore the window unchanged.
GEOMETRY_KEY, MAXIMIZED_KEY, FULLSCREEN_KEY = "window_geometry", "window_maximized", "window_fullscreen"


def read_app_settings(path):
    """app_settings.json as a dict. A missing, damaged or non-object file gives {}: the problem
    goes to the log and the file is left untouched."""
    settings, problem = config_io.read_json(path, error_label=f"app settings '{path}'")
    if isinstance(settings, dict):
        return settings
    if problem:
        print(problem)
    return {}


def write_app_settings(path, settings):
    """Write app_settings.json. Returns None, or the exception that stopped the write."""
    try:
        write_json_payload(path, settings)
    except Exception as exc:   # e.g. a read-only folder
        return exc
    return None


def geometry_to_text(geometry):
    """saveGeometry() bytes as the base64 text stored under GEOMETRY_KEY."""
    return str(base64.b64encode(bytes(geometry)), "ascii")


class StatusLine(QLabel):
    """The status bar's message: one line, cut with an ellipsis to the width it has (re-fitted
    whenever that changes); the whole message is its tooltip."""

    def __init__(self, text):
        super().__init__(text)
        self.message = None   # the start-up text stays until the first message

    def show_message(self, message):
        self.message = message
        self.setToolTip(message)
        self.fit_message()

    def fit_message(self):
        if self.message is not None:
            room = max(120, self.width() - 8)
            self.setText(self.fontMetrics().elidedText(self.message, Qt.TextElideMode.ElideRight, room))

    def resizeEvent(self, event):
        self.fit_message()
        super().resizeEvent(event)


def geometry_from_text(text):
    """Bytes for restoreGeometry(), or None when nothing was saved. Raises on corrupt text."""
    if not isinstance(text, str) or not text:
        return None
    return base64.b64decode(text)


def _finish_thread(thread, ask_to_stop):
    """Ask a worker thread that is still running to end, then wait for it."""
    if thread is not None and thread.isRunning():
        ask_to_stop(thread)
        thread.wait()


class SonicRiftApp(GeneratePage, Generation, Documents, Estimates, Finishing, EngineControls, Player,
                    LiveVoicePage, StudioPage, SoundscapePage, MusicPage, VoicePage, VoicePicker, Library, VoiceUse, Recording, TranscribePage, ModelPage, Discover, ModelLoading, ModelSettings,
                    AdvancedPage, ApiServer, Pronunciations, PerformancePage, QMainWindow):
    console_text = Signal(str)   # console output, delivered to the log view on the UI thread

    def __init__(self):
        super().__init__()
        self.setWindowTitle(ui_theme.APP_NAME)
        self.setWindowIcon(ui_theme.app_icon())
        self.resize(1000, 820)
        # No model is loaded yet; the default Chatterbox model is selected.
        self.model, self.device_used, self.cuda_runtime_issue = None, "cpu", None
        self.current_model_repo = self.selected_model_repo = DEFAULT_MODEL_REPO
        self.current_model_backend, self.current_multilingual_t3_model = (
            BACKEND_MULTILINGUAL, resolve_multilingual_t3_model(DEFAULT_MULTILINGUAL_T3_MODEL))
        gpu_present = has_system_nvidia_gpu()
        self.system_has_nvidia_gpu = gpu_present
        data_dir = paths.ROOT   # app data stays in the project folder
        self.script_dir = data_dir
        models_file = os.path.join(data_dir, MODEL_CONFIG_FILENAME)
        self.model_config_path, self.model_entries = models_file, load_models_config(models_file)
        self.app_settings_path = os.path.join(data_dir, APP_SETTINGS_FILENAME)
        self.app_settings = read_app_settings(self.app_settings_path)
        self.apply_resource_limits()   # before any model or engine worker starts
        self.apply_hf_token_setting()
        # In the project folder like all other app data, wherever the app was started from.
        self.output_directory = os.path.join(data_dir, "chatterbox_outputs")
        os.makedirs(self.output_directory, exist_ok=True)
        self.current_audio_file, self.last_reference_audio_dir = None, data_dir
        self.recordings_directory = os.path.join(
            self.script_dir, REFERENCE_RECORDINGS_DIRNAME)
        self.voice_library = voice_library.VoiceLibrary(self.script_dir, self.recordings_directory)
        self.pronunciations = pronunciation.Dictionary(os.path.join(self.script_dir, pronunciation.FILENAME))
        self.api_settings = dict({"enabled": False, "port": local_api.DEFAULT_PORT, "token": ""},
                                 **self.app_settings.get("api", {}))
        self.api_server = None
        self.api_bridge = ApiBridge(self)
        self.api_busy = False
        self.api_loading_entry = None
        self.google_account = google_docs.GoogleAccount(self.script_dir)
        self.transcriber = transcription.Transcriber()
        self.transcript = None
        self.active_voice_id = None
        self.pending_voice = None
        self.media_devices = QMediaDevices(self)
        self.recording_format = None
        self.recording_buffer = bytearray()

        self.preview_player = QMediaPlayer(self)
        self.preview_audio_output = QAudioOutput(self)
        self.preview_player.setAudioOutput(self.preview_audio_output)
        self.preview_button_playing = None
        self.preview_player.playbackStateChanged.connect(self._on_preview_state_changed)

        self._build_take_player()

        self.generation_timer = self._make_timer(self.update_generation_time_display)
        self.generation_start_time, self.is_generating = None, False
        self.model_is_warm = False
        self.generation_is_preview = False
        self.generation_started_at = None
        self.generation_char_count = 0
        self.current_document_name = None
        self.last_preview_seed = None
        self.text_stats_timer = self._make_timer(self.update_text_stats, interval=350, single_shot=True)
        sampling = self.app_settings.get("sampling", {})
        self.repetition_penalty = float(sampling.get("repetition_penalty", 1.2))
        self.min_p = float(sampling.get("min_p", 0.05))
        self.top_p = float(sampling.get("top_p", 1.0))

        self.console_text.connect(self.append_console_log)
        self._init_ui()
        self.update_minimum_size()
        self.fit_default_geometry()
        self.restore_window_state()
        self.fit_to_screen()   # a size saved on a bigger screen (or by older versions) may not fit
        self._wheel_guard = install_wheel_guard(QApplication.instance())
        self.attach_log_sink()
        self.update_output_log()

        # Started once the event loop runs, in this order. Before show() the frame (title bar,
        # borders) has no size yet, so the screen fit is checked again first.
        deferred = [self.fit_to_screen]
        if CHATTERBOX_AVAILABLE:
            if gpu_present and not torch.cuda.is_available():
                print("WARNING: this PC has an NVIDIA GPU, but the installed PyTorch has no CUDA "
                      "support, so models run on the CPU.")
            self.set_status_message("Ready. The default model starts loading in a moment; the first "
                                    "run may download its files, which can take several minutes.")
            deferred.append(self.start_default_model_load)
        else:
            # The Chatterbox engine can't load, but every other engine runs in its own environment.
            self.set_status_message(
                "Status: The Chatterbox engine is unavailable (see the log in Settings); load another model on "
                "the Models page.")
        deferred.append(self.restart_api_server)
        for job in deferred:
            QTimer.singleShot(0, job)

    # Pages in the stack (build order). The sidebar is grouped by what you're doing: the Studio
    # brings everything together; MAKE holds the generators (each keeps its own page); PERFORM
    # plays live; SETUP is models and settings.
    PAGE_GENERATE, PAGE_VOICE, PAGE_SOUNDSCAPE, PAGE_LIVE_VOICE, PAGE_TRANSCRIBE, PAGE_MODEL, PAGE_ADVANCED, \
        PAGE_PROJECT, PAGE_MUSIC = range(9)
    PAGE_STUDIO = "studio"        # the New voice tab of Voices (the voice studio), not the Studio page
    PAGE_LOG = PAGE_ADVANCED      # the log is a card on Settings
    SIDEBAR = (("Studio", PAGE_PROJECT),
               ("Make", None), ("Speech", PAGE_GENERATE), ("Sounds", PAGE_SOUNDSCAPE), ("Music", PAGE_MUSIC),
               ("Voices", PAGE_VOICE),
               ("Transcribe", PAGE_TRANSCRIBE),
               ("Perform", None), ("Live", PAGE_LIVE_VOICE),
               ("Setup", None), ("Models", PAGE_MODEL), ("Settings", PAGE_ADVANCED))

    def _make_card(self, title=None):
        card = ui_theme.CardFrame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        if title:
            title_label = QLabel(title)
            title_label.setObjectName("CardTitle")
            layout.addWidget(title_label)
        return card, layout

    def _make_page(self, title, subtitle):
        """A page with a title. With title None it's a section inside a page (no title, no margins)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        if title is None:
            layout.setContentsMargins(QMargins())
            layout.setSpacing(2)
            return page, layout
        # Cards carry their own shadow margin, so page spacing is tighter.
        layout.setContentsMargins(17, 14, 17, 10)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        # Line up with the cards' visible edge (inside their shadow margin).
        for label in (title_label, subtitle_label):
            label.setContentsMargins(ui_theme.SHADOW, 0, ui_theme.SHADOW, 0)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(6)
        return page, layout

    @staticmethod
    def _accent(button):
        button.setProperty("accent", True)
        return button

    @staticmethod
    def _link(button):
        button.setFlat(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _init_ui(self):
        window_body = QWidget()
        self.setCentralWidget(window_body)
        root_layout = QHBoxLayout(window_body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar_panel = ui_theme.SidebarPanel()
        sidebar_panel.setObjectName("SidebarPanel")
        sidebar_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar_layout = QVBoxLayout(sidebar_panel)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(180)
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for label, page in self.SIDEBAR:
            item = QListWidgetItem(label if page is not None else label.upper())
            item.setData(Qt.ItemDataRole.UserRole, page)
            if page is None:      # a group heading: not selectable, skipped by the arrow keys
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                heading = QFont(self.sidebar.font())
                heading.setPointSizeF(8)
                heading.setBold(True)
                heading.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 112)
                item.setFont(heading)
                # Taller row with the label at the bottom: space above separates the groups.
                item.setSizeHint(QSize(0, 42))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            self.sidebar.addItem(item)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(18, 16, 12, 10)
        title_row.setSpacing(9)
        logo = QLabel()
        logo.setPixmap(ui_theme.app_icon().pixmap(26, 26))
        title_row.addWidget(logo)
        app_title = QLabel(ui_theme.APP_NAME)
        app_title.setObjectName("AppTitle")
        app_title.setToolTip(f"{ui_theme.TAGLINE}\nCreative audio, made locally.")
        title_row.addWidget(app_title)
        title_row.addStretch(1)
        sidebar_layout.addLayout(title_row)
        sidebar_layout.addWidget(self.sidebar)
        self.pages = QStackedWidget()
        self.sidebar.currentRowChanged.connect(self._on_sidebar_row)
        self.sidebar.setItemDelegate(SidebarDelegate(self.sidebar))
        try:   # follow light/dark switches, like the rest of the theme
            QApplication.instance().styleHints().colorSchemeChanged.connect(
                lambda *_args: QTimer.singleShot(0, self._color_sidebar_headings))
        except AttributeError:
            pass
        content_area = ui_theme.TexturedArea()
        self.background_area = content_area
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.pages)
        root_layout.addWidget(sidebar_panel)
        root_layout.addWidget(content_area, 1)

        self._build_generate_page()
        self._build_voices_section()
        self._build_soundscape_page()
        self._build_live_voice_page()
        self._build_transcribe_page()
        self._build_model_page()
        self._build_advanced_page()
        self._build_project_page()     # the Studio: its own splitter, so it isn't wrapped in a scroll area
        self._build_music_page()

        self._make_pages_scroll()
        # Tab moves to the next control everywhere: in a text box it used to type a tab, so
        # keyboard users could never leave Create's or Live's text (only 4 of Create's controls
        # were reachable). Text that needs a literal tab can still be pasted.
        for kind in (QPlainTextEdit, QTextEdit):
            for editor in self.findChildren(kind):
                editor.setTabChangesFocus(True)
        self.show_page(self.PAGE_GENERATE)

        self._build_status_bar()
        # Fill the model, language and models-page lists from model_entries.
        for refresh in (self.refresh_model_repo_options, self.refresh_language_options, self.refresh_models_page):
            refresh()
        self.update_hf_token_status()
        self.set_tuning_expanded(bool(self.app_settings.get("tuning_expanded", False)))
        self.refresh_recordings_list()
        self.set_reference_audio(None)

    def _build_status_bar(self):
        """One line of status text (elided to fit; the whole message is its tooltip) and, on
        the right, the model-load progress bar (idle until a model loads)."""
        message = StatusLine("Status: Initializing...")
        message.setTextFormat(Qt.TextFormat.PlainText)
        message.setWordWrap(False)
        # Status text is elided to fit; it must never set the window's minimum width.
        message.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        message.setMinimumWidth(120)
        message.setFixedHeight(message.sizeHint().height() + 4)

        progress = QProgressBar()
        progress.setTextVisible(False)
        progress.setFixedSize(120, 8)
        progress.setRange(0, 1)
        progress.setValue(0)
        progress.setEnabled(False)

        bar = self.statusBar()
        bar.setSizeGripEnabled(False)
        bar.addWidget(message, 1)
        bar.addPermanentWidget(progress)
        self.status_bar, self.model_load_progress = message, progress

    def _make_timer(self, on_timeout, interval=None, single_shot=False):
        """A QTimer owned by the window that calls on_timeout (started by its users)."""
        timer = QTimer(self)
        timer.setSingleShot(single_shot)
        if interval is not None:
            timer.setInterval(interval)
        timer.timeout.connect(on_timeout)
        return timer

    def _build_voices_section(self):
        """Voices: the library and New voice (the voice studio) as tabs of one page."""
        page, layout = self._make_page(
            "Voices", "Your saved voices, and new ones made from a recording, a description or another voice.")
        self.voices_tabs = QTabBar()
        self.voices_tabs.setObjectName("CapabilityTabs")
        self.voices_tabs.setDrawBase(False)
        self.voices_tabs.setExpanding(False)
        self.voices_tabs.setUsesScrollButtons(False)
        self.voices_tabs.setElideMode(Qt.TextElideMode.ElideNone)
        self.voices_tabs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voices_tabs.addTab("Library")
        self.voices_tabs.addTab("New voice")
        tabs_row = QHBoxLayout()
        tabs_row.setContentsMargins(ui_theme.SHADOW, 0, ui_theme.SHADOW, 4)
        tabs_row.addWidget(self.voices_tabs)
        tabs_row.addStretch(1)
        layout.addLayout(tabs_row)
        self.voices_stack = QStackedWidget()
        layout.addWidget(self.voices_stack, 1)
        self._build_voice_page()      # adds the library to voices_stack
        self._build_studio_page()     # adds New voice (the voice studio) to voices_stack
        self.voices_tabs.currentChanged.connect(self._on_voices_tab)
        self.pages.addWidget(page)

    def _on_voices_tab(self, index):
        self.voices_stack.setCurrentIndex(index)
        if self.pages.currentIndex() == self.PAGE_VOICE:
            self.background_area.set_scene(self.studio_mode() if index == 1 else "voices")
        if index == 1:
            self.on_page_changed(self.PAGE_STUDIO)

    def _on_sidebar_row(self, row):
        item = self.sidebar.item(row)
        page = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if page is None:
            return
        self.pages.setCurrentIndex(page)
        scenes = {
            self.PAGE_PROJECT: "studio", self.PAGE_GENERATE: "speech",
            self.PAGE_SOUNDSCAPE: "sounds", self.PAGE_MUSIC: "music", self.PAGE_VOICE: "voices",
            self.PAGE_TRANSCRIBE: "transcribe", self.PAGE_LIVE_VOICE: "live",
        }
        scene = scenes.get(page, "neutral")
        if page == self.PAGE_VOICE and self.voices_tabs.currentIndex() == 1:
            scene = self.studio_mode()
        self.background_area.set_scene(scene)
        self.on_page_changed(page)
        if page == self.PAGE_VOICE and self.voices_tabs.currentIndex() == 1:
            self.on_page_changed(self.PAGE_STUDIO)

    def _color_sidebar_headings(self):
        """Repaint the group headings (their colour comes from the theme at paint time)."""
        self.sidebar.viewport().update()

    def show_page(self, page):
        """Go to a page; PAGE_STUDIO opens Voices on its New voice tab."""
        if page == self.PAGE_STUDIO:
            self.voices_tabs.setCurrentIndex(1)
            page = self.PAGE_VOICE
        elif page == self.PAGE_VOICE:
            self.voices_tabs.setCurrentIndex(0)
        for row in range(self.sidebar.count()):
            if self.sidebar.item(row).data(Qt.ItemDataRole.UserRole) == page:
                self.sidebar.setCurrentRow(row)
                return

    def _build_log_card(self):
        log_card, log_layout = self._make_card("Log")
        hint = QLabel("Technical output from model loading and generation.")
        hint.setObjectName("Muted")
        log_layout.addWidget(hint)
        view = QPlainTextEdit()
        view.setObjectName("LogView")
        view.setReadOnly(True)
        view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        view.setMaximumBlockCount(1000)   # oldest lines drop off
        view.setMinimumHeight(160)
        log_layout.addWidget(view, 1)
        self.console_log_view = view
        return log_card

    def attach_log_sink(self):
        # the console tee in common forwards to this sink; the signal hops to the UI thread
        common.APP_LOG_SINK = self.console_text.emit

    def append_console_log(self, chunk):
        """Add console output at the end of the Settings log and scroll to it."""
        try:
            view = self.console_log_view
        except AttributeError:
            return   # output from before the log card was built
        view.moveCursor(QTextCursor.MoveOperation.End)   # output goes at the end, whatever is selected
        view.insertPlainText(f"{chunk}")
        view.ensureCursorVisible()

    def load_app_settings(self):
        """The settings in app_settings.json ({} when there are none)."""
        return read_app_settings(self.app_settings_path)

    # The window never has to be larger than this: pages scroll inside it instead.
    # 960 x 600 fits a 1366 x 768 laptop at 125% scaling with the taskbar showing.
    MIN_WINDOW = QSize(960, 560)   # fits 1366 x 768 at 125 % (about 582 px tall above the taskbar)

    def _make_pages_scroll(self):
        """Put every page in a scroll area, so the tallest or widest page sets no window
        minimum (Live alone needed 1560 x 1489 and pushed the window off the screen)."""
        for index in range(self.pages.count()):
            page = self.pages.widget(index)
            if isinstance(page, QScrollArea) or page.property("noScroll"):
                continue
            self.pages.removeWidget(page)
            scroll = QScrollArea()
            scroll.setObjectName("PageScroll")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(page)
            self.pages.insertWidget(index, scroll)

    def update_minimum_size(self):
        """Pages scroll, so the window keeps one fixed minimum whatever they contain."""
        self.setMinimumSize(self.MIN_WINDOW)

    def fit_to_screen(self):
        """Keep the whole window, title bar included, on the screen it's on."""
        if self.isMaximized() or self.isFullScreen():
            return
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame_extra = self.frameGeometry().size() - self.geometry().size()
        width = min(self.width(), available.width() - frame_extra.width())
        height = min(self.height(), available.height() - frame_extra.height())
        if (width, height) != (self.width(), self.height()):
            self.resize(max(width, self.MIN_WINDOW.width()), max(height, self.MIN_WINDOW.height()))
        frame = self.frameGeometry()
        if not available.contains(frame):
            frame.moveLeft(max(available.left(), min(frame.left(), available.right() - frame.width())))
            frame.moveTop(max(available.top(), min(frame.top(), available.bottom() - frame.height())))
            self.move(frame.topLeft())

    def fit_default_geometry(self):
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(min(1280, available.width() - 80), min(900, available.height() - 80))
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def restore_window_state(self):
        """Put the window back as the last session left it (see remember_window_state)."""
        saved = self.app_settings
        try:
            geometry = geometry_from_text(saved.get(GEOMETRY_KEY))
            if geometry is not None:
                self.restoreGeometry(geometry)
        except Exception as exc:
            print(f"Could not restore the saved window size and position: {exc}")
        # Maximized wins over full screen when a damaged file has both.
        for key, show in ((MAXIMIZED_KEY, self.showMaximized), (FULLSCREEN_KEY, self.showFullScreen)):
            if saved.get(key):
                show()
                break

    def remember_window_state(self):
        """Record the window's geometry and maximized/full-screen state in app_settings
        (written to disk by save_app_settings)."""
        try:
            state = {GEOMETRY_KEY: geometry_to_text(self.saveGeometry()),
                     MAXIMIZED_KEY: self.isMaximized(),
                     FULLSCREEN_KEY: self.isFullScreen()}
        except Exception as exc:
            print(f"Could not record the window size and position: {exc}")
            return
        self.app_settings.update(state)

    def save_app_settings(self):
        """Write app_settings.json; the Finishing panel's settings are included once it exists."""
        settings = self.app_settings
        if hasattr(self, "speed_slider"):
            settings.update(finishing=self.current_finishing_settings().to_dict(),
                                     finishing_expanded=not self.finishing_panel.isHidden())
        failure = write_app_settings(self.app_settings_path, settings)
        if failure is not None:   # say so, but let the app close
            QMessageBox.warning(self, "Settings Error", f"Could not save {APP_SETTINGS_FILENAME}: {failure}")

    def set_status_message(self, text):
        """Show a message on the status line; the full text stays in its tooltip."""
        # One line, and without the old "Status: " prefix: the bar itself says this is status.
        text = " ".join(str(text).split()).removeprefix("Status: ")
        # StatusLine re-fits the message whenever its width changes: eliding only when a message
        # arrived left it cut short if the window grew afterwards.
        self.status_bar.show_message(text)

    OPENAI_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"}

    def on_page_changed(self, page):
        if page == self.PAGE_PROJECT:
            self.ensure_project_editor()      # the Studio's editor is made on first visit
        if page == self.PAGE_LIVE_VOICE:
            self.refresh_live_voice_summary()
            self.refresh_live_audio_devices()
            if not getattr(self, "live_board_defaults_applied", False)                     and self.soundboard_defaults_can_apply():
                self.apply_soundboard_board_defaults(self.soundboard_store.active_board())
                self.live_board_defaults_applied = True
        if page == self.PAGE_STUDIO and not self.studio_busy:
            self._fill_studio_engines()  # models may have been added or installed meanwhile
        if page == self.PAGE_MODEL and getattr(self, "discover_results", None) is None \
                and getattr(self, "discover_thread", None) is None:
            self.start_discover()

    def closeEvent(self, event):
        # An open project editor asks about unsaved edits first; keep the app open if it stays.
        if not self.close_project_editor():
            event.ignore()
            return
        if hasattr(self, "live_hotkeys"):
            self.live_hotkeys.close()
        if hasattr(self, "live_mic_input"):
            self.live_mic_input.stop()
        if hasattr(self, "live_audio_output"):
            self.live_audio_output.stop()
        if hasattr(self, "live_monitor_output"):
            self.live_monitor_output.stop()
        if getattr(self, "live_speech_thread", None) is not None:
            self.live_speech_thread.stop()   # waited for below, after settings are saved
        # the console tee in common forwards to this sink
        if self.api_server is not None:
            self.api_server.stop()
        if common.APP_LOG_SINK == self.console_text.emit:
            common.APP_LOG_SINK = None
        self.remember_window_state()
        self.save_app_settings()
        # A buffered (non-streaming) engine can't be interrupted mid-line, so wait only after saving.
        if getattr(self, "live_speech_thread", None) is not None:
            self.live_speech_thread.wait()
        _finish_thread(getattr(self, "model_loader_thread", None), lambda worker: worker.quit())
        _finish_thread(getattr(self, "audio_generator_thread", None), lambda worker: worker.stop())
        _finish_thread(self.sound_render_thread, lambda worker: worker.stop())
        discover = getattr(self, "discover_thread", None)
        if discover is not None and discover.isRunning():
            # A Hugging Face search can't be interrupted. Destroying its thread while it ran
            # ended the process with an error at exit; it normally finishes within seconds.
            discover.wait(5000)
        self.release_sound_model()
        self.shut_down_music()
        if isinstance(self.model, WORKER_MODEL_TYPES):
            self.model.close()
        event.accept()




# Historical import remains available for downstream scripts during migration.
# This is an alias, not a separate implementation or claim of new authorship.
ChatterboxApp = SonicRiftApp

if __name__ == "__main__":
    taskbar.set_process_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(ui_theme.APP_NAME)
    app.setApplicationDisplayName(ui_theme.APP_NAME)
    app.setApplicationVersion(__version__)
    ui_theme.apply_theme(app)
    window = SonicRiftApp()
    # Before show(): the taskbar button then never asks a busy window for its icon
    # (start-up work can block the UI thread, and Windows would cache the generic icon).
    taskbar.set_window_identity(window)
    window.show()
    sys.exit(app.exec())
