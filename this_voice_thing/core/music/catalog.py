"""The music engines the Music page offers, with the facts shown before installing one.

Like the sound catalog, each entry pins the exact upstream source commit and model
weights revision, so an install is reproducible and every kept take records what
made it. Candidates evaluated and not offered are listed in docs/music/.
"""

from dataclasses import dataclass, field

from this_voice_thing.core.music.contract import MusicCapabilities


@dataclass(frozen=True)
class MusicEngine:
    key: str
    label: str
    description: str
    repo_id: str
    model_revision: str             # Hugging Face commit of the weights
    source_url: str
    source_revision: str            # git commit of the engine's code
    license_name: str
    license_id: str
    license_url: str
    license_summary: str
    commercial: str
    capabilities: MusicCapabilities
    download_gb: float
    env_gb: float
    gpu: str
    vram_gb: float = 0.0            # measured peak (0 = not measured yet)
    speed_note: str = ""
    prompt_hint: str = ""
    limits: tuple = field(default_factory=tuple)   # plain-language limitations shown on the page


ACE_STEP_15 = MusicEngine(
    key="ace_step_15", label="ACE-Step 1.5 (2B turbo)",
    description="ACE-Step's open music model: instrumentals and songs with your own lyrics, at "
                "48 kHz stereo. A 1.7B planner sketches tempo, key and structure; the 2B turbo "
                "model renders it in 8 steps.",
    repo_id="ACE-Step/Ace-Step1.5", model_revision="19671f406d603126926c1b7e2adc169acbcade22",
    source_url="https://github.com/ace-step/ACE-Step-1.5",
    source_revision="ca1e85fe9430179831e6bc6be790c332190a3866",
    license_name="MIT License", license_id="mit",
    license_url="https://github.com/ace-step/ACE-Step-1.5/blob/main/LICENSE",
    license_summary="Permissive: commercial use allowed for the code and weights. The authors say "
                    "the training data is licensed, royalty-free or synthetic; that is their claim, "
                    "not a guarantee that a given output resembles no existing song.",
    commercial="Yes (MIT), subject to your own lyrics and prompts.",
    capabilities=MusicCapabilities(
        min_seconds=10.0, max_seconds=240.0, max_candidates=4, sample_rate=48000, channels=2,
        instrumental=True, vocals=True, bpm=True, bpm_range=(30, 300), key=True, time_signature=True,
        seed=True, planner=True,
        unsupported={}),
    download_gb=10.0, env_gb=7.0,
    gpu="NVIDIA GPU with 12 GB or more; unload the voice and sound models first",
    prompt_hint="e.g. gentle piano and cello underscore for a reflective scene",
    limits=("Tempo and key are requests the model follows closely but not exactly; check the take.",
            "Lyrics must be your own. Sung words can be unclear, especially in fast passages.",
            "Longer than 4 minutes isn't offered yet: Studio's mix memory limit (#71)."))

ENGINES = {engine.key: engine for engine in (ACE_STEP_15,)}


def consent_text(engine):
    """What the user agrees to before a music engine is installed."""
    return "\n".join([
        f"{engine.label} ({engine.repo_id} @ {engine.model_revision[:7]})",
        f"Code: {engine.source_url} @ {engine.source_revision[:7]}",
        "",
        f"License: {engine.license_name}",
        engine.license_summary,
        f"Commercial use: {engine.commercial}",
        f"Read the license: {engine.license_url}",
        "",
        f"Downloads: about {engine.download_gb:.0f} GB of model weights and a {engine.env_gb:.0f} GB "
        "Python environment, into this app's engines folder. Nothing else on your PC changes.",
        f"Hardware: {engine.gpu}.",
        "",
        "By installing it you accept this license for your own use of the model and of what you "
        "generate with it.",
    ])
