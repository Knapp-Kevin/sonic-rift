"""Generate the new Guide line for the music beat in the installed Sonic Rift 0.9.1, the way the
approved Guide lines were made: the Guide voice saved from the owner-picked voice design (Voices ›
New voice › Clone, clip as is), then Speech with Qwen3 voice cloning. Several takes; not filmed.

    QT_SCALE_FACTOR=1.5 MEDIA_PROFILE=<fresh profile> REELS=<voice designs> TAKES=4 \
        <install>\.venv\Scripts\python.exe gen_guide.py <install dir> <out dir> dark 1600x900
"""
import shutil

from harness import *  # noqa: F401,F403

REELS = os.environ["REELS"]
LINE = os.environ.get("LINE", "Now give the scene its own music. Describe the mood, generate a few possibilities, "
                              "and keep the one that feels right.")
TAKES = int(os.environ.get("TAKES", "4"))
try:
    from this_voice_thing import __version__
    from this_voice_thing.ui.pages import studio as studio_page
    LOG["app"] = {"version": __version__, "root": ROOT, "python": sys.executable}
    w.load_model(next(e for e in w.model_entries if e.get("label") == "Qwen3 voice cloning"))
    wait_for(lambda: w.model is not None and not w.model_is_loading, 900, 0.3)

    class _SaveVoice:
        def __init__(self, _title, voice, *_a, **_k):
            self.voice = voice

        def exec(self):
            return 1

        def apply(self):
            self.voice.name = "Guide"
            self.voice.tags = ["Evening Tide", "synthetic"]
    studio_page.VoiceDetailsDialog = _SaveVoice
    w.studio_play_take = lambda *a, **k: None
    w.show_page(w.PAGE_STUDIO)
    w.set_studio_mode("clone")
    w.studio_set_source(os.path.join(REELS, "guide-A.wav"), "A world can begin with just a few words.", "Guide (designed)")
    row = max(i for i, take in enumerate(w.studio_takes) if take.origin == "source")
    w.studio_take_list.setCurrentRow(row)
    w.studio_save_voice()
    guide = next(v for v in w.voice_library.voices if v.name == "Guide")
    w.take_audio_out.setVolume(0.0)
    w.show_page(w.PAGE_GENERATE)
    w.use_voice(guide)
    w.text_input.setPlainText(LINE)
    takes = []
    for n in range(TAKES):
        before = w.current_audio_file
        w.start_generation()
        wait_for(lambda: not w.is_generating and w.current_audio_file != before, 900, 0.1)
        dest = os.path.join(OUT, f"guide-music-take{n + 1}.wav")
        shutil.copyfile(w.current_audio_file, dest)
        takes.append({"file": dest, "app_output": w.current_audio_file})
        w.stop_audio()
    shot("guide_speech_page")
    LOG["guide"] = {"line": LINE, "voice": guide.name, "model": "Qwen3 voice cloning", "takes": takes,
                    "source_design": os.path.join(REELS, "guide-A.wav")}
except Exception:
    LOG["exception"] = traceback.format_exc()
finish()
