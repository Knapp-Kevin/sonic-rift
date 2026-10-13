"""The sound engines the Soundscape page offers, and what each one asks of the user.

The app is a front end: whoever installs and runs a model accepts that model's
license. Each model engine therefore carries the facts the consent step shows
before anything is downloaded.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SoundEngine:
    key: str
    label: str
    description: str
    kind: str                 # "procedural" or "model"
    repo_id: str = ""
    license_name: str = ""
    license_url: str = ""
    license_summary: str = ""
    commercial: str = ""      # plain-language commercial-use note
    gated: bool = False       # the user must accept terms on Hugging Face first
    download_gb: float = 0.0  # model weights
    env_gb: float = 0.0       # its own Python environment (PyTorch included)
    max_seconds: float = 0.0  # per generation; longer clips are stitched
    sample_rate: int = 48000
    channels: int = 2         # mono engines are widened to stereo (Width slider)
    gpu: str = ""             # what it needs or prefers
    vram_gb: float = 0.0      # measured peak on the GPU (0 = CPU or not measured)
    prompt_hint: str = ""


PROCEDURAL = SoundEngine(
    key="procedural", label="Procedural (no model)",
    description="Ambience and chimes built from sound synthesis on your CPU. Nothing to download; "
                "loops are seamless by construction.",
    kind="procedural", license_name="Your own work", commercial="Yes: you made it.",
    max_seconds=600.0, sample_rate=48000, gpu="None (CPU)")

SA3_SMALL_SFX = SoundEngine(
    key="sa3_small_sfx", label="Stable Audio 3 Small SFX",
    description="Stability AI's sound-effects model: text to sound, up to 120 s of 44.1 kHz audio "
                "per take (two channels, but nearly mono in practice), and it can regenerate a loop's "
                "seam. Runs on GPU or CPU; a 30 s loop takes about 1.5 s on an RTX 5070 Ti.",
    kind="model", repo_id="stabilityai/stable-audio-3-small-sfx",
    license_name="Stability AI Community License",
    license_url="https://stability.ai/license",
    license_summary="Free for research, non-commercial use, and commercial use by individuals and "
                    "organizations with under US$1M in total annual revenue. Commercial users must "
                    "register with Stability AI and display \"Powered by Stability AI\". Above US$1M "
                    "an enterprise license is required.",
    commercial="Conditional: under US$1M annual revenue, with registration and attribution.",
    gated=True, download_gb=3.5, env_gb=6.0, max_seconds=120.0, sample_rate=44100, channels=1,
    gpu="Optional (about 2–3 GB VRAM); runs on CPU",
    prompt_hint="e.g. gentle ocean waves rolling onto a sandy beach, distant gulls")

MOSS_SFX_V2 = SoundEngine(
    key="moss_sfx_v2", label="MOSS-SoundEffect v2",
    description="OpenMOSS's sound-effects model: environments, cities, creatures and actions, "
                "up to 30 s of 48 kHz mono per take (longer clips are stitched). Each take takes "
                "about 23 s on an RTX 5070 Ti, whatever its length.",
    kind="model", repo_id="OpenMOSS-Team/MOSS-SoundEffect-v2.0",
    license_name="Apache License 2.0",
    license_url="https://www.apache.org/licenses/LICENSE-2.0",
    license_summary="Permissive: commercial use allowed. Keep the license and notices when "
                    "redistributing the model. The training data is not disclosed.",
    commercial="Yes (Apache-2.0).",
    gated=False, download_gb=11.2, env_gb=7.0, max_seconds=30.0, sample_rate=48000, channels=1,
    gpu="NVIDIA GPU with 16 GB (about 15 GB at peak); unload the voice model first", vram_gb=15.2,
    prompt_hint="e.g. heavy rain on a tin roof with distant thunder")

ENGINES = {engine.key: engine for engine in (PROCEDURAL, SA3_SMALL_SFX, MOSS_SFX_V2)}


def consent_text(engine):
    """What the user agrees to before a model engine is installed."""
    lines = [
        f"{engine.label} ({engine.repo_id})",
        "",
        f"License: {engine.license_name}",
        engine.license_summary,
        f"Commercial use: {engine.commercial}",
        f"Read the license: {engine.license_url}",
        "",
        f"Downloads: about {engine.download_gb:.1f} GB of model weights and a "
        f"{engine.env_gb:.0f} GB Python environment, into this app's folders.",
        f"Hardware: {engine.gpu}.",
    ]
    if engine.gated:
        lines += ["", "This model is gated: sign in to Hugging Face, open the model page and accept "
                      "its terms first, and add your Hugging Face token on the Model page."]
    lines += ["", "By installing it you accept this license for your own use of the model and of "
                  "what you generate with it."]
    return "\n".join(lines)
