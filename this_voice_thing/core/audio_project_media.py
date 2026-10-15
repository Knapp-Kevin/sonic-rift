"""Content-addressed voice takes and verified existing Sound Library assets.

Project JSON contains opaque IDs only. A VoiceLibrary voice ID represents a
speaker/reference, NOT a generated narration take: those are imported separately.
"""
import hashlib
import os
from pathlib import Path
import re
import tempfile

import soundfile as sf

from this_voice_thing.core.audio_timeline_mix import _source_pcm
from this_voice_thing.core.soundscape import mastering

VOICE_ID = re.compile(r"voice_([a-f0-9]{64})\Z")
SOUND_ID = re.compile(r"sound_([a-f0-9]{12})\Z")
MAX_SOURCE_SECONDS = 900


def _digest(path):
    result = hashlib.sha256()
    with open(path, "rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            result.update(part)
    return result.hexdigest()


class ProjectMedia:
    """Resolve only project-owned voice takes or checksum-verified Sound assets."""

    def __init__(self, app_dir, sound_library):
        self.app_root = Path(app_dir).resolve()
        self.voice_root = self.app_root / "project_media" / "voice"
        self.sound_library = sound_library

    def import_voice_take(self, audio, sample_rate):
        """Persist generated narration PCM without changing the Voice Library."""
        if type(sample_rate) is not int or not 8000 <= sample_rate <= 192000:
            raise ValueError("Invalid voice sample rate")
        pcm = _source_pcm((audio, sample_rate), sample_rate)
        if len(pcm) > MAX_SOURCE_SECONDS * sample_rate:
            raise ValueError("Voice take exceeds maximum duration")
        self.voice_root.mkdir(parents=True, exist_ok=True)
        if not self.voice_root.resolve().is_relative_to(self.app_root):
            raise ValueError("Unsafe project media directory")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.voice_root, prefix=".voice-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
            mastering.write_audio(str(temporary), pcm, sample_rate, "wav")
            digest = _digest(temporary)
            destination = self.voice_root / (digest + ".wav")
            if destination.exists():
                if not destination.is_file() or _digest(destination) != digest:
                    raise ValueError("Existing voice media does not match expected checksum")
            else:
                os.replace(temporary, destination)
                temporary = None
            return "voice_" + digest
        finally:
            if temporary and temporary.exists():
                temporary.unlink()

    def resolve(self, asset_id):
        if not isinstance(asset_id, str):
            raise ValueError("Invalid project asset identifier")
        voice = VOICE_ID.fullmatch(asset_id)
        sound = SOUND_ID.fullmatch(asset_id)
        if voice:
            path = self.voice_root / (voice.group(1) + ".wav")
            if not path.resolve().is_relative_to(self.app_root):
                raise ValueError("Unsafe voice asset path")
            expected = voice.group(1)
        elif sound:
            asset = self.sound_library.get(sound.group(1))
            if asset is None:
                raise FileNotFoundError(f"Unknown Sound Library asset: {asset_id}")
            filename = asset.file
            if not isinstance(filename, str) or filename != Path(filename).name or not re.fullmatch(r"[A-Za-z0-9_.-]+\.wav", filename):
                raise ValueError("Unsafe Sound Library filename")
            audio_root = Path(self.sound_library.audio_dir).resolve()
            path = audio_root / filename
            if not path.resolve().is_relative_to(audio_root):
                raise ValueError("Sound Library file escapes its directory")
            expected = asset.sha256
        else:
            raise ValueError("Unknown project asset namespace")
        if not path.is_file():
            raise FileNotFoundError(f"Missing project audio asset: {asset_id}")
        if _digest(path) != expected:
            raise ValueError(f"Project audio checksum mismatch: {asset_id}")
        info = sf.info(str(path))
        if info.channels not in (1, 2) or not 8000 <= info.samplerate <= 192000 or info.frames <= 0 or info.frames > MAX_SOURCE_SECONDS * info.samplerate:
            raise ValueError("Unsupported project audio format or duration")
        data, rate = sf.read(str(path), dtype="float32", always_2d=True)
        return _source_pcm((data, rate), rate), rate
