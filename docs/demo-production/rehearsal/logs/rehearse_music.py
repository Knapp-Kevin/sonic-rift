"""Technical rehearsal: Music -> Keep and add to Studio -> Save -> Play mix render -> Export mix.

Drives the real Sonic Rift main window (this worktree = disposable profile, ROOT is this
folder) with real ACE-Step. Dialogs are answered by the script and logged. Screenshots via
QWidget.grab. Writes evidence to film_work/rehearsal/.
"""
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.argv = ["main.py"]
OUT = HERE / "rehearsal"
OUT.mkdir(exist_ok=True)
LOG = open(OUT / "rehearsal_log.txt", "a", encoding="utf-8")


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox  # noqa: E402

os.environ.setdefault("QT_SCALE_FACTOR", "1.5")   # same as the approved captures: 1600x900 logical at 1.5x
from this_voice_thing import __version__  # noqa: E402
from this_voice_thing.ui import main_window, taskbar  # noqa: E402
from this_voice_thing.ui import theme as ui_theme  # noqa: E402
# Same start-up as this_voice_thing/ui/main_window.py's __main__ block.
taskbar.set_process_app_id()
app = QApplication.instance() or QApplication(sys.argv)
app.setApplicationName(ui_theme.APP_NAME)
app.setApplicationDisplayName(ui_theme.APP_NAME)
app.setApplicationVersion(__version__)
ui_theme.apply_theme(app)

PROMPT = ("Understated original instrumental underscore for a quiet seaside night: soft felt piano, "
          "warm low strings, slow and calm, gentle, sparse, no percussion, no vocals")
SECONDS, TAKES, SEED = int(os.environ.get("SR_SECONDS", 30)), int(os.environ.get("SR_TAKES", 2)), 1103


def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def wait_for(cond, timeout, what):
    start = time.monotonic()
    while not cond():
        app.processEvents()
        time.sleep(0.05)
        if time.monotonic() - start > timeout:
            raise TimeoutError(what)
    log(f"{what}: done in {time.monotonic() - start:.1f} s")


def grab(window, name):
    pump(0.3)
    path = OUT / f"{name}.png"
    window.grab().save(str(path))
    log(f"screenshot {path.name}")


answers = {}
def fake_text(parent, title, label, *a, **k):
    value = answers.get(title, k.get("text", ""))
    log(f"dialog QInputDialog.getText '{title}/{label}' -> {value!r}")
    return value, True
def fake_item(parent, title, label, items, *a, **k):
    value = answers.get(title, items[0])
    log(f"dialog QInputDialog.getItem '{title}/{label}' -> {value!r}")
    return value, True
def fake_save(parent, caption, directory="", *a, **k):
    value = answers[caption]
    log(f"dialog QFileDialog.getSaveFileName '{caption}' -> {value}")
    return value, ""
def fake_dir(parent, caption, directory="", *a, **k):
    value = answers[caption]
    log(f"dialog QFileDialog.getExistingDirectory '{caption}' -> {value}")
    return value
def fake_info(parent, title, text, *a, **k):
    log(f"dialog QMessageBox '{title}': {text}")
    return QMessageBox.StandardButton.Ok
def fake_question(parent, title, text, *a, **k):
    log(f"dialog QMessageBox.question '{title}': {text} -> Yes")
    return QMessageBox.StandardButton.Yes


def main():
    project_path = OUT / "Evening Tide - The Beacon.sonicrift.json"
    export_parent = OUT / "exports"
    export_parent.mkdir(exist_ok=True)
    stamp = time.strftime("%H%M%S")
    answers.update({
        "New project": "Evening Tide: The Beacon",
        "Track": "Dialogue",
        "Save project": str(project_path),
        "Keep music": "Harbor light underscore",
        "Choose export location": str(export_parent),
        "Export formats": "WAV",
        "Export folder": f"Rehearsal_Mix_{stamp}",
    })
    with patch.object(main_window.ChatterboxApp, "start_default_model_load", lambda self: None), \
            patch.object(main_window.ChatterboxApp, "restart_api_server", lambda self: None):
        w = main_window.SonicRiftApp()
    taskbar.set_window_identity(w)
    w.output_directory = str(OUT / "outputs")
    os.makedirs(w.output_directory, exist_ok=True)
    w.resize(QSize(1600, 900))
    w.show()
    w.move(-4000, 40)   # real Windows window, kept off the visible desktop; captured with QWidget.grab
    pump(1.0)
    log(f"Sonic Rift {__version__} window up; ROOT={ROOT}")

    heavy = []
    def confirm(cost, title):
        heavy.append(cost.label)
        log(f"heavy-job warning shown and accepted by script: {cost.label} (~{cost.minutes:.1f} min, "
            f"{cost.gpu_gb} GB GPU)")
        return True
    w.confirm_heavy_job = confirm

    with patch.object(QInputDialog, "getText", staticmethod(fake_text)), \
            patch.object(QInputDialog, "getItem", staticmethod(fake_item)), \
            patch.object(QFileDialog, "getSaveFileName", staticmethod(fake_save)), \
            patch.object(QFileDialog, "getExistingDirectory", staticmethod(fake_dir)), \
            patch.object(QMessageBox, "information", staticmethod(fake_info)), \
            patch.object(QMessageBox, "warning", staticmethod(fake_info)), \
            patch.object(QMessageBox, "question", staticmethod(fake_question)):
        editor = w.open_project_editor()
        editor.new_project()
        answers["Track"] = "voice"
        _orig_text = QInputDialog.getText
        def track_text(parent, title, label, *a, **k):
            if title == "Track":
                log("dialog QInputDialog.getText 'Track/Name' -> 'Dialogue'")
                return "Dialogue", True
            return fake_text(parent, title, label, *a, **k)
        with patch.object(QInputDialog, "getText", staticmethod(track_text)):
            editor.add_track()
        pump(0.3)
        editor.save_project()
        grab(w, "01_studio_empty_project")

        # Music page
        w.show_page(w.PAGE_MUSIC) if hasattr(w, "PAGE_MUSIC") else None
        w.music_prompt_input.setPlainText(PROMPT)
        w.music_instrumental_checkbox.setChecked(True)
        w.music_seconds_spin.setValue(SECONDS)
        w.music_takes_spin.setValue(TAKES)
        w.music_seed_spin.setValue(SEED)
        w.refresh_music_controls()
        grab(w, "02_music_request")
        log(f"Generate: engine={w.current_music_engine().label} seconds={SECONDS} takes={TAKES} seed={SEED}")
        t0 = time.monotonic()
        w.start_music()
        wait_for(lambda: w.music_task is None, 900, "music model start")
        log(f"status line: {w.status_bar.toolTip() if hasattr(w.status_bar, 'toolTip') else ''}")
        if w.music_model is None:
            log("FAILED: music model did not start")
            return 2
        log(f"music model on {w.music_model.device}, load {w.music_model.load_seconds:.0f} s")
        wait_for(lambda: w.music_job is not None, 60, "music job begins")
        grab(w, "03_music_composing")
        wait_for(lambda: w.music_job is None, 1200, "music takes")
        log(f"music status: {w.music_status.text()} (wall {time.monotonic() - t0:.0f} s incl. start)")
        takes = w.music_takes()
        if not takes:
            log("FAILED: no takes")
            return 3
        for i, take in enumerate(takes):
            log(f"take {chr(65 + i)}: {take.path} {getattr(take, 'seconds', '')}")
        w.music_take_list.setCurrentRow(0)
        grab(w, "04_music_takes")

        # copy takes for owner listening before keep (the service discards on next generate)
        import shutil
        for i, take in enumerate(takes):
            shutil.copy2(take.path, OUT / f"music_take_{chr(65 + i)}_seed{SEED}.wav")

        w.keep_music_take(to_studio=True)
        wait_for(lambda: editor.import_worker is None, 120, "music clip import into Studio")
        pump(0.5)
        tracks = [(t.kind, t.name, [(c.kind, c.asset_id, c.frame_count if hasattr(c, 'frame_count') else None)
                                    for c in t.clips]) for t in editor.session.project.tracks]
        log(f"project tracks after Keep and add to Studio: {tracks}")
        log(f"editor note: {editor.note.text()}")
        grab(w, "05_studio_music_clip_added")
        editor.save_project()
        log(f"saved project: {editor.session.path}")

        editor.play_preview()
        wait_for(lambda: editor.preview_worker is None, 120, "Play mix render")
        log(f"preview file: {editor.preview_file}; note: {editor.note.text()}")
        pump(2.0)
        grab(w, "06_studio_play_mix")
        editor.stop_preview()

        editor.export()
        wait_for(lambda: editor.worker is None, 300, "Export mix")
        log(f"export note: {editor.note.text()}")
        grab(w, "07_studio_exported")
        folder = export_parent / answers["Export folder"]
        files = sorted(p.name for p in folder.rglob("*")) if folder.exists() else []
        log(f"export folder files: {files}")
        manifest = next(folder.rglob("*manifest*.json"), None) if folder.exists() else None
        if manifest:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            log(f"manifest asset_ids: {data.get('asset_ids')}")
        (OUT / "rehearsal_result.json").write_text(json.dumps({
            "version": __version__, "prompt": PROMPT, "seconds": SECONDS, "takes": TAKES, "seed": SEED,
            "tracks": tracks, "project": str(editor.session.path), "preview": editor.preview_file,
            "export_folder": str(folder), "export_files": files, "heavy_jobs": heavy}, indent=2))

        w.release_music_model()
        pump(1.0)
    log("rehearsal complete")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        import traceback
        log("EXCEPTION " + "".join(traceback.format_exception(exc)))
        code = 1
    os._exit(code)
