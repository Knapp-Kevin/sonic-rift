"""'A World in Sound: Evening Tide, The Beacon' (v0.9.1 cut): one real, scripted session of the
published Sonic Rift 0.9.1, installed from the signed installer.

    QT_SCALE_FACTOR=1.5 MEDIA_PROFILE=<profile> GUIDE_DIR=<guide> REELS=<voice designs> \
        <install>\.venv\Scripts\python.exe film_v091.py <install dir> <out dir> dark 1600x900

Same method as the approved film (scratchpad q120/beacon_film.py): the real window, grabbed
off-screen at 12 fps; waits for renders and model loads condensed to one frame; the app's players
muted and the soundtrack assembled afterwards from the audio files the app produced, at the logged
video times, plus the approved Guide voice-over (docs/marketing/audio, unchanged).

Story beats: an empty project; the Keeper and the Traveler speak (Speech, Qwen3 voice cloning of the
owner-picked voice designs); procedural ocean waves (Sounds, seed 53 = the approved waves); the
Keeper's voice cloned with VoxCPM2 for a new line; music (Music: ACE-Step composes a take on
camera; the owner-picked kept take D is auditioned and added with the waves lane selected, so it
gets its own track); the lines placed, the lanes balanced with their sliders, Check balance, save;
the uninterrupted Studio mix; Export.
"""
import shutil

from harness import *  # noqa: F401,F403
from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFileDialog

import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE = os.environ["GUIDE_DIR"]
REELS = os.environ["REELS"]
FPS = 12
FRAMES = os.path.join(OUT, "frames")
EXPORT_DIR = os.path.join(OUT, "export")
for d in (FRAMES, EXPORT_DIR):
    os.makedirs(d, exist_ok=True)
TITLE = "Evening Tide: The Beacon"
KEEPER = ("Keeper", "The beacon is still burning. Follow it toward shore.")
TRAVELER = ("Traveler", "I see it now. Keep the light on.")
CLONE_LINE = "I'll keep it burning until you're home."
MUSIC_NAME = "Harbor light theme"
MUSIC_PROMPT = ("Solo cello with a soft acoustic string ensemble, slow, gentle, warm original instrumental underscore "
                "for a quiet seaside night, hopeful and tender, unhurried and sparse, purely acoustic, no piano, "
                "no woodwinds, no synthesizer, no electronic sounds, no percussion, no vocals")
PROJECT_FILE = os.path.join(EXPORT_DIR, "evening-tide-the-beacon.sonicrift.json")
CHOICE = {"item": ("voice", True), "double": (-6.0, True)}
patch.object(QFileDialog, "getExistingDirectory", lambda *a, **k: EXPORT_DIR).start()
patch.object(QFileDialog, "getSaveFileName", lambda *a, **k: (PROJECT_FILE, "")).start()
patch.object(QInputDialog, "getItem", lambda *a, **k: CHOICE["item"]).start()
patch.object(QInputDialog, "getDouble", lambda *a, **k: CHOICE["double"]).start()
CLIP_PROPS = {}
_dialog_exec = QDialog.exec


def _answer_clip_props(self):
    """Clip properties, answered by the script: set the named fields, then OK."""
    if self.windowTitle() != "Clip properties" or not CLIP_PROPS:
        return _dialog_exec(self)
    from PySide6.QtWidgets import QFormLayout
    form = self.layout()
    for row in range(form.rowCount()):
        label = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
        field = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
        if label and field and label.widget().text() in CLIP_PROPS:
            field.widget().setValue(CLIP_PROPS[label.widget().text()])
    return QDialog.DialogCode.Accepted


QDialog.exec = _answer_clip_props
ST = {"t": 0.0, "n": 0, "frames": [], "events": [], "chapters": [], "vo_end": 0.0, "answered": [], "waits": []}


def frame(duration):
    path = os.path.join(FRAMES, f"f{ST['n']:05d}.jpg")
    w.grab().save(path, "JPG", 93)
    ST["frames"].append((path, duration))
    ST["n"] += 1
    ST["t"] += duration


def hold(seconds):
    pump(0.12)
    frame(seconds)


def live(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        start = time.monotonic()
        frame(1.0 / FPS)
        pump(max(0.005, 1.0 / FPS - (time.monotonic() - start)))


def chapter(text):
    ST["chapters"].append((round(ST["t"], 2), text))


def sound(path, role, length=None, gain_db=0.0, fade=0.25, text=""):
    keep = os.path.join(OUT, "audio", f"{len(ST['events']):02d}-{role.lower().replace(' ', '-').replace('(', '').replace(')', '')}.wav")
    os.makedirs(os.path.dirname(keep), exist_ok=True)
    shutil.copyfile(path, keep)
    seconds = sf.info(keep).duration
    ST["events"].append(dict(at=round(ST["t"], 3), path=keep, source=path, role=role, length=length or seconds,
                             gain_db=gain_db, fade=fade, text=text, file_seconds=round(seconds, 3)))
    return min(seconds, length or seconds)


def guide(number, lead=0.3):
    path = os.path.join(GUIDE, f"guide-{number:02d}.wav")
    text = json.load(open(os.path.join(GUIDE, "guide-lines.json"), encoding="utf-8"))[f"guide-{number:02d}.wav"]
    at = ST["t"] + lead
    keep = os.path.join(OUT, "audio", f"vo-{number:02d}.wav")
    os.makedirs(os.path.dirname(keep), exist_ok=True)
    shutil.copyfile(path, keep)
    seconds = sf.info(keep).duration
    ST["events"].append(dict(at=round(at, 3), path=keep, source=path, role="Guide", length=seconds, gain_db=0.0,
                             fade=0.02, text=text, file_seconds=round(seconds, 3)))
    ST["vo_end"] = at + seconds
    return ST["vo_end"]


def until_vo_done(pad=0.35):
    remaining = ST["vo_end"] + pad - ST["t"]
    if remaining > 0.05:
        hold(remaining)


def condensed(label, cond, timeout, shown=0.9):
    """A render or model load: one frame on screen, the real wait logged."""
    pump(0.1)
    frame(shown)
    waited = wait_for(cond, timeout, 0.05)
    ST["waits"].append({"what": label, "real_seconds": None if waited is None else round(waited, 1), "shown_seconds": shown})
    if waited is None:
        raise RuntimeError(f"timed out: {label}")


def mouse(view, kind, x, y, buttons):
    button = Qt.MouseButton.LeftButton if kind != QEvent.Type.MouseMove else Qt.MouseButton.NoButton
    QApplication.sendEvent(view, QMouseEvent(kind, QPointF(x, y), view.mapToGlobal(QPointF(x, y)), button,
                                             buttons, Qt.KeyboardModifier.NoModifier))


def drag_clip(editor, clip_id, to_seconds, steps=9):
    tl = editor.timeline
    tl.grab()
    rect = next(r for r, cid in tl._hits if cid == clip_id)
    clip = next(c for t in editor.session.project.tracks for c in t.clips if c.id == clip_id)
    x0, y = rect.center().x(), rect.center().y()
    dx = (to_seconds * editor.session.project.sample_rate - clip.start_frame) / tl._frames_per_pixel()
    mouse(tl, QEvent.Type.MouseButtonPress, x0, y, Qt.MouseButton.LeftButton)
    for k in range(1, steps + 1):
        mouse(tl, QEvent.Type.MouseMove, x0 + dx * k / steps, y, Qt.MouseButton.LeftButton)
        frame(1.0 / FPS)
        pump(0.01)
    mouse(tl, QEvent.Type.MouseButtonRelease, x0 + dx, y, Qt.MouseButton.NoButton)
    pump(0.1)


def slide(editor, track_name, target_db, seconds=1.1):
    """Drag a lane's level slider to `target_db`: shown moving, committed once on release."""
    track = next(t for t in editor.session.project.tracks if t.name == track_name)
    slider = editor.timeline.controls[track.id]["slider"]
    start, end = slider.value(), round(target_db / 0.5)
    steps = max(2, int(seconds * FPS))
    slider.setSliderDown(True)
    for k in range(1, steps + 1):
        slider.setValue(round(start + (end - start) * k / steps))
        frame(1.0 / FPS)
        pump(0.005)
    slider.setSliderDown(False)
    slider.sliderReleased.emit()
    pump(0.15)
    got = next(t for t in editor.session.project.tracks if t.id == track.id).gain_db
    assert got == target_db, (track_name, got)
    ST["answered"].append(f"Lane slider: {track_name} {target_db:+.1f} dB (one undoable edit)")


def type_text(widget, text, seconds):
    steps = max(1, int(seconds * FPS))
    setter = widget.setPlainText if hasattr(widget, "setPlainText") else widget.setText
    for i in range(1, steps + 1):
        setter(text[: round(len(text) * i / steps)])
        frame(1.0 / FPS)
        pump(0.003)


def generate_on_speech(label):
    before = w.current_audio_file
    w.start_generation()
    condensed(label, lambda: not w.is_generating and w.current_audio_file != before, 900)
    w.speech_takes_list.setCurrentRow(0)
    pump(0.15)
    return w.current_audio_file


def to_studio(add):
    add()
    editor = w.project_editor
    wait_for(lambda: editor.import_worker is None, 120, 0.05)
    wait_for(lambda: editor.peak_worker is None, 60, 0.05)
    pump(0.2)
    return editor


try:
    # ---------------- pre-roll (not filmed) ----------------
    from this_voice_thing import __version__
    LOG["app"] = {"version": __version__, "root": ROOT, "python": sys.executable}
    w.confirm_heavy_job = lambda cost, title: (ST["answered"].append(f"Heavy-job notice ({title}): {cost.label}"), True)[1]
    w.load_model(next(e for e in w.model_entries if e.get("label") == "Qwen3 voice cloning"))
    wait_for(lambda: w.model is not None and not w.model_is_loading, 900, 0.3)
    from this_voice_thing.ui.pages import studio as studio_page

    class _SaveVoice:
        NAME = ""

        def __init__(self, _title, voice, *_a, **_k):
            self.voice = voice

        def exec(self):
            return 1

        def apply(self):
            self.voice.name = _SaveVoice.NAME
            self.voice.tags = ["Evening Tide", "synthetic"]
    studio_page.VoiceDetailsDialog = _SaveVoice
    w.studio_play_take = lambda *a, **k: None
    CAST = {"Guide": ("guide-A.wav", "A world can begin with just a few words."),
            "Keeper": ("keeper-A.wav", KEEPER[1]), "Traveler": ("traveler-A.wav", TRAVELER[1])}
    voices = {}
    for role, (clip, text) in CAST.items():
        w.show_page(w.PAGE_STUDIO)
        w.set_studio_mode("clone")
        w.studio_set_source(os.path.join(REELS, clip), text, f"{role} (designed)")
        row = max(i for i, take in enumerate(w.studio_takes) if take.origin == "source")
        w.studio_take_list.setCurrentRow(row)
        _SaveVoice.NAME = role
        w.studio_save_voice()
        voices[role] = next(v for v in w.voice_library.voices if v.name == role)
    while w.studio_takes:
        w.studio_take_list.setCurrentRow(0)
        w.studio_remove_take()
    ST["answered"].append("Pre-roll: Guide, Keeper and Traveler saved as voices from the owner-picked Qwen3 voice designs")
    for output in (w.take_audio_out, w.preview_audio_output, w.sound_audio_output, w.studio_audio_output,
                   w.music_audio_output):
        output.setVolume(0.0)
    w.play_when_done_checkbox.setChecked(True)
    editor = w.open_project_editor()
    editor.audio_out.setVolume(0.0)
    INPUT["text"] = TITLE
    editor.rename_project()
    CHOICE["item"] = ("voice", True)
    INPUT["text"] = "Dialogue"
    editor.add_track()
    editor.save_project()
    ST["answered"] += ["Rename project: title", "Add track: kind voice, name Dialogue", "Save project: file name"]
    w.set_status_message("Ready.")
    pump(0.4)
    shot("00_studio_empty")

    # ---------------- an empty world ----------------
    chapter("An empty world")
    hold(1.2)
    guide(1)
    until_vo_done(0.7)

    # ---------------- the Keeper ----------------
    chapter("Give it a keeper")
    w.show_page(w.PAGE_GENERATE)
    w.text_input.clear()
    hold(0.8)
    w.use_voice(voices["Keeper"])
    pump(0.3)
    hold(1.1)
    type_text(w.text_input, KEEPER[1], 2.6)
    hold(0.4)
    keeper_take = generate_on_speech("Speech: Keeper take (Qwen3 cloning)")
    sound(keeper_take, "Keeper", text=KEEPER[1])
    live(sf.info(keeper_take).duration + 0.6)
    w.stop_audio()
    hold(0.3)
    editor = to_studio(w.add_take_to_studio)
    hold(2.0)

    # ---------------- the Traveler ----------------
    chapter("Someone answers")
    w.show_page(w.PAGE_GENERATE)
    guide(2, lead=0.2)
    hold(0.8)
    w.use_voice(voices["Traveler"])
    pump(0.3)
    hold(1.0)
    type_text(w.text_input, TRAVELER[1], 2.0)
    until_vo_done(0.2)
    traveler_take = generate_on_speech("Speech: Traveler take (Qwen3 cloning)")
    sound(traveler_take, "Traveler", text=TRAVELER[1])
    live(sf.info(traveler_take).duration + 0.6)
    w.stop_audio()
    shot("10_speech")
    hold(0.3)
    editor = to_studio(w.add_take_to_studio)
    hold(2.0)

    # ---------------- the shoreline ----------------
    chapter("Give it a shoreline")
    w.show_page(w.PAGE_SOUNDSCAPE)
    w.sound_seconds_spin.setValue(20.0)
    w.sound_takes_spin.setValue(2)
    w.sound_seed_spin.setValue(53)
    guide(3, lead=0.2)
    hold(1.4)
    w.start_sound_render()
    condensed("Sounds: procedural ocean, 2 takes", lambda: not w.sound_busy() and w.sound_take_list.count() >= 2, 300, 0.7)
    w.sound_take_list.setCurrentRow(0)
    until_vo_done(0.2)
    w.play_sound_take()
    pump(0.1)
    sound(w.sound_player.source().toLocalFile(), "Ocean", length=3.8, fade=0.6, text="[ocean waves]")
    live(3.8)
    w.sound_player.stop()
    INPUT["text"] = "Shoreline waves"
    w.keep_sound_take()
    ST["answered"].append("Keep in library: name Shoreline waves")
    wait_for(lambda: any(a.name == "Shoreline waves" for a in w.sound_library.assets), 60, 0.05)
    w.refresh_sound_assets()
    waves_row = next(i for i in range(w.sound_asset_list.count()) if "Shoreline waves" in w.sound_asset_list.item(i).text())
    w.sound_asset_list.setCurrentRow(waves_row)
    hold(1.0)
    shot("20_sounds")
    editor = to_studio(w.add_sound_to_studio)
    hold(2.0)

    # ---------------- the Keeper again ----------------
    chapter("Keep a character's voice")
    _SaveVoice.NAME = "Keeper (cloned)"
    ST["answered"].append("Save voice: name Keeper (cloned)")
    w.show_page(w.PAGE_STUDIO)
    w.set_studio_mode("clone")
    w.studio_set_source(keeper_take, KEEPER[1], "Keeper (Speech take)")
    ST["answered"].append("Open file: the Keeper take from Speech")
    for i in range(w.studio_engine_combo.count()):
        if "VoxCPM" in w.studio_engine_combo.itemText(i):
            w.studio_engine_combo.setCurrentIndex(i)
    w.studio_count_spin.setValue(2)
    w.studio_test_input.setText(CLONE_LINE)
    guide(4, lead=0.2)
    hold(1.6)
    w.studio_make_takes()
    condensed("Voices: VoxCPM2 loads and clones 2 takes",
              lambda: sum(t.origin == "clone" for t in w.studio_takes) >= 2 and not w.studio_busy, 1200, 0.9)
    w.studio_take_list.setCurrentRow(next(i for i, t in enumerate(w.studio_takes) if t.origin == "clone"))
    until_vo_done(0.3)
    hold(1.2)
    shot("30_voices_clone")
    w.studio_save_voice()
    pump(0.3)
    w.show_page(w.PAGE_VOICE)
    hold(1.3)
    voice = next(v for v in w.voice_library.voices if v.name == "Keeper (cloned)")
    w.show_page(w.PAGE_GENERATE)
    w.use_voice(voice)
    pump(0.4)
    hold(1.0)
    type_text(w.text_input, CLONE_LINE, 1.8)
    hold(0.3)
    clone_take = generate_on_speech("Speech: Keeper (cloned) take (VoxCPM2)")
    sound(clone_take, "Keeper (clone)", text=CLONE_LINE)
    live(sf.info(clone_take).duration + 0.6)
    w.stop_audio()
    hold(0.3)
    editor = to_studio(w.add_take_to_studio)
    hold(1.6)

    # ---------------- music ----------------
    chapter("Give it music")
    waves = next(t for t in editor.session.project.tracks if t.name == "Shoreline waves")
    editor.timeline.trackSelected.emit(waves.id)       # the waves lane is selected, as a user would leave it
    pump(0.2)
    hold(1.0)
    ST["answered"].append("Studio: waves lane selected before adding music")
    w.show_page(w.PAGE_MUSIC)
    w.music_instrumental_checkbox.setChecked(True)
    w.music_plan_checkbox.setChecked(True)
    w.music_seconds_spin.setValue(30)
    w.music_takes_spin.setValue(1)
    w.music_seed_spin.setValue(3201)
    w.music_bpm_checkbox.setChecked(True)
    w.music_bpm_spin.setValue(70)
    w.music_key_combo.setCurrentIndex(w.music_key_combo.findData("A major"))
    w.music_meter_combo.setCurrentIndex(w.music_meter_combo.findData(4))
    w.refresh_music_assets()
    w.music_prompt_input.clear()
    hold(0.6)
    type_text(w.music_prompt_input, MUSIC_PROMPT, 2.2)
    hold(0.4)
    w.start_music()
    condensed("Music: ACE-Step starts and composes 1 take",
              lambda: w.music_task is None and w.music_job is None and len(w.music_takes()) >= 1, 1500, 1.0)
    w.music_take_list.setCurrentRow(0)
    new_take = w.music_takes()[0]
    ST["new_music_take"] = {"path": new_take.path, "seed": new_take.seed, "engine_notes": new_take.engine_notes,
                            "metrics": new_take.metrics}
    w.play_music_take(0)
    pump(0.1)
    sound(new_take.path, "Music (new take)", length=2.6, fade=0.5, text="[a new take plays]")
    live(2.6)
    w.music_player.stop()
    shot("35_music_takes")
    kept = next(a for a in w.sound_library.assets if a.name == MUSIC_NAME)
    w.refresh_music_assets(select=kept.id)
    hold(0.9)
    w.play_music_asset()
    pump(0.1)
    sound(w.sound_library.path(kept), "Music (kept)", length=3.6, fade=0.6, text="[cello and strings]")
    live(3.6)
    w.music_player.stop()
    n_tracks = len(editor.session.project.tracks)
    editor = to_studio(w.add_music_to_studio)
    tracks = editor.session.project.tracks
    music_track = tracks[-1]
    waves_now = next(t for t in tracks if t.id == waves.id)
    assert len(tracks) == n_tracks + 1 and len(waves_now.clips) == 1 and music_track.clips[0].asset_id == "sound_" + kept.id
    ST["answered"].append(f"Kept music > Add to Studio: new track {music_track.name!r}; waves lane unchanged")
    hold(2.2)
    shot("40_studio_music_track")

    # ---------------- arrange, balance, check, save ----------------
    chapter("Arrange, balance and save")
    project = editor.session.project
    dialogue = next(t for t in project.tracks if t.name == "Dialogue")
    keeper_id, traveler_id, clone_id = [c.id for c in dialogue.clips][:3]
    guide(5, lead=0.2)
    rate = project.sample_rate
    drag_clip(editor, keeper_id, 2.0)
    hold(0.25)
    keeper_clip = next(c for c in editor.session.project.tracks[0].clips if c.id == keeper_id)
    drag_clip(editor, traveler_id, round((keeper_clip.start_frame + keeper_clip.frame_count) / rate + 0.7, 2))
    hold(0.25)
    traveler_clip = next(c for c in editor.session.project.tracks[0].clips if c.id == traveler_id)
    drag_clip(editor, clone_id, round((traveler_clip.start_frame + traveler_clip.frame_count) / rate + 0.9, 2))
    hold(0.25)
    clone_clip = next(c for c in editor.session.project.tracks[0].clips if c.id == clone_id)
    scene_end = round((clone_clip.start_frame + clone_clip.frame_count) / rate + 3.5, 2)
    for name, fades in (("Shoreline waves", (1.5, 3.0)), (MUSIC_NAME, (2.0, 4.0))):
        clip = next(t for t in editor.session.project.tracks if t.name == name).clips[0]
        CLIP_PROPS.update({"Duration (seconds)": scene_end, "Fade in (seconds)": fades[0], "Fade out (seconds)": fades[1]})
        editor.refresh(clip.id)
        editor.edit_selected()
        CLIP_PROPS.clear()
        ST["answered"].append(f"Clip properties: {name} {scene_end} s, fade in {fades[0]} s, fade out {fades[1]} s")
        pump(0.15)
    slide(editor, "Shoreline waves", -6.0)
    hold(0.3)
    slide(editor, MUSIC_NAME, -15.0)
    hold(0.4)
    editor.balance_button.click()
    wait_for(lambda: editor.balance_worker is None, 120, 0.05)
    badges = {t.name: editor.timeline.badges.get(t.id, "") for t in editor.session.project.tracks}
    ST["balance"] = {"badges": badges, "summary": editor.balance_note.text()}
    hold(2.4)
    shot("45_studio_balanced")
    editor.save_project()
    pump(0.2)
    until_vo_done(0.3)
    hold(0.6)
    guide(6, lead=0.1)
    until_vo_done(0.5)

    # ---------------- hear the scene ----------------
    chapter("Hear the scene")
    editor.play_preview()
    wait_for(lambda: editor.player.playbackState() == editor.player.PlaybackState.PlayingState, 120, 0.02)
    mix_copy = os.path.join(OUT, "studio-preview-mix.wav")
    shutil.copyfile(editor.preview_file, mix_copy)
    sound(mix_copy, "Studio mix", length=scene_end, fade=0.3, text="[scene]")
    live(scene_end)
    editor.stop_preview()
    hold(0.4)

    # ---------------- export ----------------
    chapter("Export the mix")
    CHOICE["item"] = ("WAV", True)
    INPUT["text"] = "Evening Tide The Beacon"
    editor.export()
    ST["answered"].append("Export: folder, WAV, folder name")
    wait_for(lambda: editor.worker is None, 300, 0.05)
    hold(2.6)
    shot("50_studio_exported")
    chapter("Sonic Rift")
    end_card_at = ST["t"]
    brand = os.path.join(GUIDE, "brand-tagline.wav")
    keep = os.path.join(OUT, "audio", "vo-brand.wav")
    shutil.copyfile(brand, keep)
    seconds = sf.info(keep).duration
    ST["events"].append(dict(at=round(end_card_at + 0.5, 3), path=keep, source=brand, role="Brand narrator",
                             length=seconds, gain_db=0.0, fade=0.02, text="Sonic Rift. Make worlds you can hear.",
                             file_seconds=round(seconds, 3)))
    ST["end_card"] = (round(end_card_at, 3), round(0.5 + seconds + 1.6, 3))

    LOG["film"] = {"video_seconds": round(ST["t"], 2), "frames": ST["n"], "chapters": ST["chapters"],
                   "events": ST["events"], "end_card": ST["end_card"], "answered": ST["answered"],
                   "waits": ST["waits"], "balance": ST.get("balance"), "new_music_take": ST.get("new_music_take"),
                   "takes": {"keeper": keeper_take, "traveler": traveler_take, "clone": clone_take},
                   "scene_end": scene_end, "project_file": PROJECT_FILE,
                   "export": sorted(os.listdir(EXPORT_DIR)), "heading": editor.heading.text(),
                   "clips": [(t.name, [(c.text[:30], c.start_frame / rate, c.frame_count / rate, c.gain_db,
                                        c.asset_id) for c in t.clips], t.gain_db, t.muted)
                             for t in editor.session.project.tracks],
                   "duck_db": editor.session.project.duck_db}
    with open(os.path.join(OUT, "frames.txt"), "w", encoding="utf-8") as handle:
        for path, duration in ST["frames"]:
            handle.write(f"file '{path.replace(os.sep, '/')}'\nduration {duration:.4f}\n")
        handle.write(f"file '{ST['frames'][-1][0].replace(os.sep, '/')}'\n")
except Exception:
    LOG["exception"] = traceback.format_exc()
    LOG["film_partial"] = {"t": ST["t"], "chapters": ST["chapters"], "answered": ST["answered"], "waits": ST["waits"]}
finish()
