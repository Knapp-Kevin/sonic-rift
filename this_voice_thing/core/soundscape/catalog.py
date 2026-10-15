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

# Stable Audio 3 Small SFX was evaluated and removed (2026-10-14): its ocean, rain and tonal
# output was rejected in the owner's listening review, and it carried license conditions.
ENGINES = {engine.key: engine for engine in (PROCEDURAL, MOSS_SFX_V2)}


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
                      "its terms first, and add your Hugging Face token on the Models page."]
    lines += ["", "By installing it you accept this license for your own use of the model and of "
                  "what you generate with it."]
    return "\n".join(lines)
