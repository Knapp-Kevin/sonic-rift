"""Music round 2 for owner review: A's mood, slower and acoustic. Real Sonic Rift window on the fix
build (bc84a4a), disposable profile, dark theme. Reuses the scene-rehearsal harness (dialogs,
screenshots, logging) from rehearse_scene.py.

Music page: Tempo on 70 BPM, key A major, 4 beats per bar, Instrumental, Plan first, 3 x 30 s.
Studio: approved 02/04/08 lines + procedural Ocean waves; each take Keep and add to Studio with the
waves selected (each gets its own track); music tracks -14 dB, 2 s / 4 s fades; one Export mix per take
with the other two music tracks muted (Selection > Mute / unmute track).
"""
import json
import os
import shutil
import time
from pathlib import Path

import rehearse_scene as rs

OUT = rs.HERE / "round2"
OUT.mkdir(exist_ok=True)
rs.OUT = OUT
rs.LOG = open(OUT / "round2_log.txt", "a", encoding="utf-8")
log, grab, pump, wait_for, answers, select_track = rs.log, rs.grab, rs.pump, rs.wait_for, rs.answers, rs.select_track

COMMON = ("slow, gentle, warm original instrumental underscore for a quiet seaside night, hopeful and tender, "
          "unhurried and sparse, purely acoustic, no piano, no woodwinds, no synthesizer, no electronic sounds, "
          "no percussion, no vocals")
VARIANTS = (("D", "Solo cello with a soft acoustic string ensemble, " + COMMON),
            ("E", "Fingerpicked nylon-string acoustic guitar, " + COMMON),
            ("F", "Gentle concert harp with soft sustained acoustic strings, " + COMMON))
BPM, KEY, METER, SEED, SECONDS = 70, "A major", 4, 3101, 30


def main():
    from unittest.mock import patch
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
    from this_voice_thing import __version__
    from this_voice_thing.ui import main_window, taskbar

    project_path = OUT / "Evening Tide - The Beacon (music round 2).sonicrift.json"
    (OUT / "exports").mkdir(exist_ok=True)
    answers.update({
        "New project": "Evening Tide: The Beacon",
        ("Track", "Type"): "voice", ("Track", "Name"): "Dialogue",
        "Save project": str(project_path),
        "open_queue": [str(rs.APPROVED / n) for n in ("02-keeper-the-beacon.wav", "04-traveler-i-see-it-now.wav",
                                                       "08-keeper-clone-ill-keep-it-burning.wav")],
        "Keep in library": "Shoreline waves",
        "Choose export location": str(OUT / "exports"),
        "Export formats": "WAV",
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
    log(f"Sonic Rift {__version__} up (dark), ROOT={rs.ROOT}")
    w.confirm_heavy_job = lambda cost, title: (log(f"heavy-job warning accepted by script: {cost.label} "
                                                   f"(~{cost.minutes:.1f} min, {cost.gpu_gb} GB GPU)"), True)[1]
    with patch.object(QInputDialog, "getText", staticmethod(rs.fake_text)), \
            patch.object(QInputDialog, "getItem", staticmethod(rs.fake_item)), \
            patch.object(QInputDialog, "getDouble", staticmethod(rs.fake_double)), \
            patch.object(QFileDialog, "getSaveFileName", staticmethod(rs.fake_save)), \
            patch.object(QFileDialog, "getOpenFileName", staticmethod(rs.fake_open)), \
            patch.object(QFileDialog, "getExistingDirectory", staticmethod(rs.fake_dir)), \
            patch.object(QMessageBox, "information", staticmethod(rs.fake_info)), \
            patch.object(QMessageBox, "warning", staticmethod(rs.fake_info)), \
            patch.object(QMessageBox, "question", staticmethod(rs.fake_question)):
        editor = w.open_project_editor()
        editor.new_project()
        editor.add_track()
        editor.save_project()
        for _ in range(3):
            select_track(editor, "Dialogue")
            editor.add_voice_take()
            wait_for(lambda: editor.import_worker is None, 60, "narration file import")
        w.show_page(w.PAGE_SOUNDSCAPE)
        w.sound_engine_combo.setCurrentIndex(w.sound_engine_combo.findData("procedural"))
        w.sound_preset_combo.setCurrentIndex(w.sound_preset_combo.findData("ocean"))
        w.sound_seconds_spin.setValue(20.0)
        w.sound_takes_spin.setValue(2)
        w.start_sound_render()
        wait_for(lambda: w.sound_render_thread is None, 120, "ocean waves render")
        w.keep_sound_take()
        w.add_sound_to_studio()
        wait_for(lambda: editor.import_worker is None, 60, "waves into Studio")

        names = []
        for index, (letter, prompt) in enumerate(VARIANTS):
            w.show_page(w.PAGE_MUSIC)
            w.music_prompt_input.setPlainText(prompt)
            w.music_instrumental_checkbox.setChecked(True)
            w.music_seconds_spin.setValue(SECONDS)
            w.music_takes_spin.setValue(1)
            w.music_seed_spin.setValue(SEED + index)
            w.music_bpm_checkbox.setChecked(True)
            w.music_bpm_spin.setValue(BPM)
            w.music_key_combo.setCurrentIndex(w.music_key_combo.findData(KEY))
            w.music_meter_combo.setCurrentIndex(w.music_meter_combo.findData(METER))
            w.refresh_music_controls()
            req = w.music_request()
            log(f"{letter} request: prompt={req.prompt!r} bpm={req.bpm} key={req.key} meter={req.time_signature} "
                f"plan={req.plan} seed={req.seed}")
            if index == 0:
                grab(w, "music_request_D")
            w.start_music()
            if w.music_task is not None:
                wait_for(lambda: w.music_task is None, 900, "music model start")
            if w.music_model is None:
                log("FAILED: music model did not start")
                return 2
            wait_for(lambda: w.music_job is None, 900, f"take {letter}")
            take = w.music_takes()[0]
            log(f"take {letter}: seed {take.seed}, {take.seconds:.1f} s, engine chose {take.engine_notes}, "
                f"metrics {take.metrics}")
            shutil.copy2(take.path, OUT / f"music_candidate_{letter}_seed{take.seed}.wav")
            grab(w, f"music_take_{letter}")
            name = f"Round 2 {letter}"
            names.append((letter, name))
            answers["Keep music"] = name
            w.music_take_list.setCurrentRow(0)
            select_track(editor, "Shoreline waves")
            w.keep_music_take(to_studio=True)
            wait_for(lambda: editor.import_worker is None, 60, f"{name} into Studio")
        grab(w, "studio_three_music_tracks")
        rate = editor.session.project.sample_rate
        for _, name in names:
            select_track(editor, name)
            answers["Track gain"] = -14.0
            answers[("Track name", "Name")] = name
            editor.edit_selected()
            clip_id = next(t for t in editor.session.project.tracks if t.name == name).clips[0].id
            editor._mutate(lambda: editor.session.update_clip(clip_id, fade_in_frames=2 * rate,
                                                               fade_out_frames=4 * rate), clip_id)
        select_track(editor, "Shoreline waves")
        answers["Track gain"] = -6.0
        answers[("Track name", "Name")] = "Shoreline waves"
        editor.edit_selected()
        editor.save_project()

        def set_muted(name, muted):
            track = select_track(editor, name)
            if track.muted != muted:
                editor.toggle_track_mute()
        for letter, name in names:
            for _, other in names:
                set_muted(other, other != name)
            editor.save_project()
            answers["Export folder"] = f"Scene_with_{letter}_{time.strftime('%H%M%S')}"
            editor.export()
            wait_for(lambda: editor.worker is None, 300, f"Export mix with {letter}")
            folder = OUT / "exports" / answers["Export folder"]
            shutil.copy2(folder / "master.wav", OUT / f"scene_with_{letter}.wav")
            log(f"scene with {letter}: {folder.name}; muted={[(t.name, t.muted) for t in editor.session.project.tracks]}")
        grab(w, "studio_after_exports")
        w.release_music_model()
        pump(1.0)
    log("round 2 complete")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        import traceback
        log("EXCEPTION " + "".join(traceback.format_exception(exc)))
        code = 1
    os._exit(code)
