"""The Asset Library: kept sounds with their provenance.

Each asset is a 24-bit WAV master in sound_library/audio/ plus an entry in
sound_library/assets.json recording how it was made (engine, model and license,
preset or prompt, settings, seed) and what it measured (loudness, peak, seam).
Exports to OGG/MP3 are re-encoded from the master on demand.
"""

import hashlib
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field

import soundfile as sf

from this_voice_thing.core.soundscape import mastering

DIRNAME = "sound_library"
INDEX = "assets.json"
SCHEMA = 1


@dataclass
class Asset:
    id: str
    name: str
    file: str                       # relative to the library's audio/ folder
    engine: str                     # catalog key
    loop: bool
    seconds: float
    sample_rate: int
    sha256: str
    created: float
    model: str = ""                 # repo id for model engines
    license: str = ""
    preset: str = ""
    prompt: str = ""
    seed: int = 0
    settings: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    notes: str = ""


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_stem(name):
    stem = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in name).strip()
    return (stem or "sound")[:40].replace(" ", "_")


class AssetLibrary:
    def __init__(self, app_dir):
        self.root = os.path.join(app_dir, DIRNAME)
        self.audio_dir = os.path.join(self.root, "audio")
        self.index_path = os.path.join(self.root, INDEX)
        self.assets = []
        self.load()

    def load(self):
        self.assets = []
        if not os.path.exists(self.index_path):
            return
        with open(self.index_path, encoding="utf-8") as handle:
            payload = json.load(handle)
        known = set(Asset.__dataclass_fields__)
        for item in payload.get("assets", []):
            self.assets.append(Asset(**{k: v for k, v in item.items() if k in known}))

    def save(self):
        os.makedirs(self.root, exist_ok=True)
        tmp = self.index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump({"schema": SCHEMA, "assets": [asdict(a) for a in self.assets]}, handle, indent=1)
        os.replace(tmp, self.index_path)   # never leave a half-written index

    def path(self, asset):
        return os.path.join(self.audio_dir, asset.file)

    def get(self, asset_id):
        return next((a for a in self.assets if a.id == asset_id), None)

    def add(self, audio, sample_rate, name, engine, loop, **provenance):
        """Store `audio` as a new asset; provenance keys are Asset fields (model, prompt…)."""
        os.makedirs(self.audio_dir, exist_ok=True)
        asset_id = uuid.uuid4().hex[:12]
        filename = f"{safe_stem(name)}_{asset_id}.wav"
        path = os.path.join(self.audio_dir, filename)
        mastering.write_audio(path, audio, sample_rate, "wav")
        metrics = provenance.pop("metrics", None) or mastering.measure(audio, sample_rate, loop)
        asset = Asset(id=asset_id, name=name.strip() or "Sound", file=filename, engine=engine,
                      loop=bool(loop), seconds=round(len(audio) / sample_rate, 3),
                      sample_rate=int(sample_rate), sha256=_sha256(path), created=time.time(),
                      metrics=metrics, **provenance)
        self.assets.insert(0, asset)
        self.save()
        return asset

    def rename(self, asset_id, name):
        asset = self.get(asset_id)
        if asset and name.strip():
            asset.name = name.strip()
            self.save()
        return asset

    def remove(self, asset_id):
        asset = self.get(asset_id)
        if asset is None:
            return False
        self.assets.remove(asset)
        self.save()
        try:
            os.remove(self.path(asset))
        except FileNotFoundError:
            pass
        return True

    def verify(self, asset):
        """True when the master is present and unchanged since it was kept."""
        path = self.path(asset)
        return os.path.exists(path) and _sha256(path) == asset.sha256

    def export(self, asset_id, destination_without_extension, formats=("wav",)):
        asset = self.get(asset_id)
        audio, sample_rate = sf.read(self.path(asset), dtype="float32", always_2d=True)
        return mastering.export(audio, sample_rate, destination_without_extension, formats)

    def provenance_text(self, asset):
        parts = [asset.engine]
        if asset.model:
            parts.append(asset.model)
        if asset.preset:
            parts.append(f"preset {asset.preset}")
        if asset.prompt:
            parts.append(f"“{asset.prompt}”")
        parts.append(f"seed {asset.seed}")
        if asset.license:
            parts.append(asset.license)
        return " · ".join(parts)
