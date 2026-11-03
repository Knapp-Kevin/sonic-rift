"""Scene rehearsal (no final capture): the S06 music route under the real S07 scene.

Real Sonic Rift v0.9.0-alpha window, disposable profile (ROOT = this worktree), dark theme,
1600x900 at 1.5x. Steps, all through the app's own UI methods unless noted:
  Studio: New project, Dialogue track, Save.
  Studio > Add > Narration file...: approved 02 Keeper, 04 Traveler, 08 Keeper clone (unchanged files).
  Sounds: Procedural Ocean waves, Generate, Keep in library, Add to Studio.
  Music: ACE-Step instrumental, Generate 3 takes, Keep and add to Studio (take A).
  Studio: Track gain dialog for waves (-6 dB) and music (-14 dB); music clip fades set through
          ProjectSession.update_clip (the model behind Clip properties; noted in the log).
  Studio: Save, Play mix (render + playback), Export mix (WAV, stems, manifest).
Dialogs are answered by the script and logged. Evidence goes to film_work/scene/.
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.argv = ["main.py"]
OUT = HERE / "scene"
OUT.mkdir(exist_ok=True)
LOG = open(OUT / "scene_log.txt", "a", encoding="utf-8")
APPROVED = Path(r"C:\LocalAI\Voice\Chatterbox\sr-demo\docs\marketing\audio")


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


os.environ.setdefault("QT_SCALE_FACTOR", "1.5")
from PySide6.QtCore import QSize, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox  # noqa: E402
from this_voice_thing import __version__  # noqa: E402
from this_voice_thing.ui import main_window, taskbar  # noqa: E402
from this_voice_thing.ui import theme as ui_theme  # noqa: E402

taskbar.set_process_app_id()
app = QApplication.instance() or QApplication(sys.argv)
app.setApplicationName(ui_theme.APP_NAME)
app.setApplicationDisplayName(ui_theme.APP_NAME)
app.setApplicationVersion(__version__)
app.styleHints().setColorScheme(Qt.ColorScheme.Dark)   # what Windows dark mode does; the app follows it
ui_theme.apply_theme(app)

PROMPT = ("Understated original instrumental underscore for a quiet seaside night: soft felt piano, "
          "warm low strings, slow and calm, gentle, sparse, no percussion, no vocals")
MUSIC_SECONDS, MUSIC_TAKES, SEED = 30, 3, 2026


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


shots = []
def grab(window, name):
    pump(0.4)
    path = OUT / f"{len(shots) + 1:02d}_{name}.png"
    window.grab().save(str(path))
    shots.append(path.name)
    log(f"screenshot {path.name}")


answers = {}
def fake_text(parent, title, label, *a, **k):
    value = answers.get((title, label), answers.get(title, k.get("text", "")))
    log(f"dialog getText '{title}/{label}' -> {value!r}")
    return value, True
def fake_item(parent, title, label, items, *a, **k):
    value = answers.get((title, label), answers.get(title, items[0]))
    log(f"dialog getItem '{title}/{label}' -> {value!r}")
    return value, True
def fake_double(parent, title, label, value=0.0, *a, **k):
    v = answers[title]
    log(f"dialog getDouble '{title}/{label}' -> {v}")
    return v, True
def fake_save(parent, caption, directory="", *a, **k):
    log(f"dialog getSaveFileName '{caption}' -> {answers[caption]}")
    return answers[caption], ""
def fake_open(parent, caption, directory="", *a, **k):
    value = answers["open_queue"].pop(0)
    log(f"dialog getOpenFileName '{caption}' -> {value}")
    return value, ""
def fake_dir(parent, caption, directory="", *a, **k):
    log(f"dialog getExistingDirectory '{caption}' -> {answers[caption]}")
    return answers[caption]
def fake_info(parent, title, text, *a, **k):
    log(f"dialog QMessageBox '{title}': {text}")
    return QMessageBox.StandardButton.Ok
def fake_question(parent, title, text, *a, **k):
    log(f"dialog question '{title}': {text} -> Yes")
    return QMessageBox.StandardButton.Yes


def select_track(editor, name):
    tree = editor.tree
    for i in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(i)
        data = item.data(0, Qt.ItemDataRole.UserRole)
        track = next((t for t in editor.session.project.tracks if data and t.id == data[1]), None)
        if track is not None and track.name == name:
            tree.setCurrentItem(item)
            return track
    raise LookupError(name)


def main():
    stamp = time.strftime("%H%M%S")
    project_path = OUT / "Evening Tide - The Beacon.sonicrift.json"
    (OUT / "exports").mkdir(exist_ok=True)
    answers.update({
        "New project": "Evening Tide: The Beacon",
        ("Track", "Type"): "voice", ("Track", "Name"): "Dialogue",
        "Save project": str(project_path),
        "open_queue": [str(APPROVED / n) for n in ("02-keeper-the-beacon.wav", "04-traveler-i-see-it-now.wav",
                                                    "08-keeper-clone-ill-keep-it-burning.wav")],
        "Keep in library": "Shoreline waves",
        "Keep music": "Harbor light underscore",
        "Choose export location": str(OUT / "exports"),
        "Export formats": "WAV",
        "Export folder": f"Scene_Rehearsal_{stamp}",
    })
    with patch.object(main_window.ChatterboxApp, "start_default_model_load", lambda self: None), \
            patch.object(main_window.ChatterboxApp, "restart_api_server", lambda self: None):
        w = main_window.SonicRiftApp()
    taskbar.set_window_identity(w)
    w.output_directory = str(OUT / "outputs")
    os.makedirs(w.output_directory, exist_ok=True)
    w.resize(QSize(1600, 900))
    w.show()
    w.move(-4000, 40)
    pump(1.0)
    log(f"Sonic Rift {__version__} up (dark theme), ROOT={ROOT}")
    w.confirm_heavy_job = lambda cost, title: (log(f"heavy-job warning accepted by script: {cost.label} "
                                                   f"(~{cost.minutes:.1f} min, {cost.gpu_gb} GB GPU)"), True)[1]

    with patch.object(QInputDialog, "getText", staticmethod(fake_text)), \
            patch.object(QInputDialog, "getItem", staticmethod(fake_item)), \
            patch.object(QInputDialog, "getDouble", staticmethod(fake_double)), \
            patch.object(QFileDialog, "getSaveFileName", staticmethod(fake_save)), \
            patch.object(QFileDialog, "getOpenFileName", staticmethod(fake_open)), \
            patch.object(QFileDialog, "getExistingDirectory", staticmethod(fake_dir)), \
            patch.object(QMessageBox, "information", staticmethod(fake_info)), \
            patch.object(QMessageBox, "warning", staticmethod(fake_info)), \
            patch.object(QMessageBox, "question", staticmethod(fake_question)):
        editor = w.open_project_editor()
        editor.new_project()
        editor.add_track()
        editor.save_project()
        grab(w, "studio_empty_project")

        for _ in range(3):
            select_track(editor, "Dialogue")
            editor.add_voice_take()
            wait_for(lambda: editor.import_worker is None, 60, "narration file import")
        grab(w, "studio_three_lines")

        # Sounds: procedural ocean
        w.show_page(w.PAGE_SOUNDSCAPE)
        w.sound_engine_combo.setCurrentIndex(w.sound_engine_combo.findData("procedural"))
        w.sound_preset_combo.setCurrentIndex(w.sound_preset_combo.findData("ocean"))
        w.sound_seconds_spin.setValue(20.0)
        w.sound_takes_spin.setValue(2)
        w.start_sound_render()
        wait_for(lambda: w.sound_render_thread is None, 120, "ocean waves render")
        log(f"sounds status: {w.sound_status.text()}")
        grab(w, "sounds_ocean_takes")
        w.keep_sound_take()
        w.add_sound_to_studio()
        wait_for(lambda: editor.import_worker is None, 60, "waves into Studio")

        # Music
        w.show_page(w.PAGE_MUSIC)
        w.music_prompt_input.setPlainText(PROMPT)
        w.music_instrumental_checkbox.setChecked(True)
        w.music_seconds_spin.setValue(MUSIC_SECONDS)
        w.music_takes_spin.setValue(MUSIC_TAKES)
        w.music_seed_spin.setValue(SEED)
        w.refresh_music_controls()
        grab(w, "music_request")
        w.start_music()
        wait_for(lambda: w.music_task is None, 900, "music model start")
        if w.music_model is None:
            log("FAILED: music model did not start")
            return 2
        wait_for(lambda: w.music_job is not None, 60, "music job begins")
        pump(5)
        grab(w, "music_composing")
        wait_for(lambda: w.music_job is None, 1500, "music takes")
        log(f"music status: {w.music_status.text()}")
        takes = w.music_takes()
        for i, take in enumerate(takes):
            dest = OUT / f"music_candidate_{chr(65 + i)}_seed{take.seed if hasattr(take, 'seed') else SEED + i}.wav"
            shutil.copy2(take.path, dest)
            log(f"candidate {chr(65 + i)} -> {dest.name}")
        w.music_take_list.setCurrentRow(0)
        grab(w, "music_takes")
        # Fix check: the waves track stays selected, as in try 1; the music must get its own track.
        select_track(editor, "Shoreline waves")
        log("selected track before Keep and add to Studio: Shoreline waves")
        w.keep_music_take(to_studio=True)
        wait_for(lambda: editor.import_worker is None, 60, "music into Studio")
        grab(w, "studio_music_added")

        # Balance: track gain dialogs, music fades
        for name, gain in (("Shoreline waves", -6.0), ("Harbor light underscore", -14.0)):
            select_track(editor, name)
            answers["Track gain"] = gain
            answers[("Track name", "Name")] = name
            editor.edit_selected()
            pump(0.2)
        music_track = next(t for t in editor.session.project.tracks if t.name == "Harbor light underscore")
        rate = editor.session.project.sample_rate
        clip_id = music_track.clips[0].id
        editor._mutate(lambda: editor.session.update_clip(clip_id, fade_in_frames=2 * rate,
                                                           fade_out_frames=4 * rate), clip_id)
        log("music clip fades 2 s in / 4 s out via ProjectSession.update_clip (Clip properties model)")
        editor.save_project()
        tracks = [{"name": t.name, "kind": t.kind, "gain_db": t.gain_db,
                   "clips": [{"kind": c.kind, "asset": c.asset_id, "start_s": c.start_frame / rate,
                              "len_s": c.frame_count / rate, "fade_in_s": c.fade_in_frames / rate,
                              "fade_out_s": c.fade_out_frames / rate} for c in t.clips]}
                  for t in editor.session.project.tracks]
        log(f"tracks: {json.dumps(tracks)}")
        grab(w, "studio_balanced_saved")

        editor.play_preview()
        wait_for(lambda: editor.preview_worker is None, 120, "Play mix render")
        shutil.copy2(editor.preview_file, OUT / "studio_play_mix_preview.wav")
        pump(5.0)
        grab(w, "studio_play_mix_playing")
        editor.stop_preview()

        editor.export()
        wait_for(lambda: editor.worker is None, 300, "Export mix")
        log(f"export note: {editor.note.text()}")
        grab(w, "studio_export_complete")
        folder = OUT / "exports" / answers["Export folder"]
        files = sorted(str(p.relative_to(folder)) for p in folder.rglob("*"))
        log(f"export files: {files}")
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        (OUT / "scene_result.json").write_text(json.dumps({
            "version": __version__, "prompt": PROMPT, "music_seconds": MUSIC_SECONDS, "music_takes": MUSIC_TAKES,
            "seed": SEED, "tracks": tracks, "project": str(editor.session.path), "export": str(folder),
            "export_files": files, "manifest": manifest, "screenshots": shots}, indent=2))
        w.release_music_model()
        pump(1.0)
    log("scene rehearsal complete")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        import traceback
        log("EXCEPTION " + "".join(traceback.format_exception(exc)))
        code = 1
    os._exit(code)
