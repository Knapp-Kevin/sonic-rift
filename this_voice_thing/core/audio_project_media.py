"""Content-addressed voice takes and verified existing Sound Library assets.

Project JSON contains opaque IDs only. A VoiceLibrary voice ID represents a
speaker/reference, NOT a generated narration take: those are imported separately.
"""
import hashlib
import json
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
ORIGIN_SCHEMA_VERSION = 1
ORIGIN_SUFFIX = ".origin.json"  # private local claim, NOT a C2PA credential


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
        """Persist imported voice PCM without asserting who or what made it."""
        asset_id, _created = self._store_voice_take(audio, sample_rate, generated=False)
        return asset_id

    def _ambiguous_voice_origin_path(self, digest):
        """The content digest was reused in incompatible provenance contexts."""
        return self.voice_root / (digest + ".origin-ambiguous")

    def _mark_voice_origin_ambiguous(self, digest):
        """Fail safe for same-bytes import/TTS collisions, without overwrites."""
        path = self._ambiguous_voice_origin_path(digest)
        try:
            with path.open("xb") as handle:
                handle.write(b"origin_context_collision_v1\\n")
        except FileExistsError:
            pass

    def _store_voice_take(self, audio, sample_rate, *, generated):
        """Write once, reporting whether this exact content address was new."""
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
            created = False
            if destination.exists() or destination.is_symlink():
                if not destination.is_file() or _digest(destination) != digest:
                    raise ValueError("Existing voice media does not match expected checksum")
                if not generated:
                    # A direct import of the same bytes can have a different
                    # creation history. One hash must not assert two histories.
                    self._mark_voice_origin_ambiguous(digest)
                elif self.read_voice_origin("voice_" + digest) is None:
                    # A generated take collides with a previously unrecorded
                    # asset: don't assign AI origin to earlier imported clips.
                    self._mark_voice_origin_ambiguous(digest)
            else:
                os.replace(temporary, destination)
                temporary = None
                created = True
            return "voice_" + digest, created
        finally:
            if temporary and temporary.exists():
                temporary.unlink()

    def _voice_origin_path(self, digest):
        """Digest-derived name only: no caller-provided paths or user filenames."""
        if type(digest) is not str or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid voice digest")
        return self.voice_root / (digest + ORIGIN_SUFFIX)

    def read_voice_origin(self, asset_id):
        """Read only a matching, integrity-checked, *unsigned* TTS origin claim.

        A checksum binds this metadata to WAV bytes, but the JSON is mutable and
        cannot establish identity or signature trust. Missing, malformed and
        tampered claims never upgrade origin out of unknown.
        """
        match = VOICE_ID.fullmatch(asset_id) if type(asset_id) is str else None
        if match is None:
            return None
        digest = match.group(1)
        audio_path = self.voice_root / (digest + ".wav")
        origin_path = self._voice_origin_path(digest)
        if (not audio_path.is_file() or not origin_path.is_file()
                or self._ambiguous_voice_origin_path(digest).exists()):
            return None
        # Refuse symlinks that escape the app-owned voice media directory.
        root = self.voice_root.resolve()
        if (not audio_path.resolve().is_relative_to(root)
                or not origin_path.resolve().is_relative_to(root)):
            return None
        if _digest(audio_path) != digest or origin_path.stat().st_size > 4096:
            return None
        try:
            record = json.loads(origin_path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError, OSError):
            return None
        if (type(record) is not dict or set(record) != {
                "schema_version", "origin", "engine", "media_sha256", "evidence_status"}
                or type(record["schema_version"]) is not int
                or record["schema_version"] != ORIGIN_SCHEMA_VERSION
                or record["origin"] != "ai_generated"
                or record["engine"] != "studio_tts_worker"
                or record["media_sha256"] != digest
                or record["evidence_status"] != "unsigned_local_generation_event"):
            return None
        return record

    def import_generated_voice_take(self, audio, sample_rate):
        """Keep a WAV produced by Studio's own TTS worker and its origin claim.

        Only call from the actual successful `generate_narration` worker result.
        Regular file imports must use `import_voice_take` and remain unknown.
        This record identifies the *AI generation method*, not a specific model
        revision, signer, prompt, speaker, user, or external C2PA authority.
        """
        asset_id, created = self._store_voice_take(audio, sample_rate, generated=True)
        digest = asset_id[len("voice_"):]
        if not created and self.read_voice_origin(asset_id) is None:
            # The same WAV was already present from an unknown/import context.
            # Keep playback functional but refuse to upgrade its origin.
            return asset_id
        origin_path = self._voice_origin_path(digest)
        record = {
            "schema_version": ORIGIN_SCHEMA_VERSION,
            "origin": "ai_generated",
            "engine": "studio_tts_worker",
            "media_sha256": digest,
            "evidence_status": "unsigned_local_generation_event",
        }
        if origin_path.exists() or origin_path.is_symlink():
            if self.read_voice_origin(asset_id) != record:
                raise ValueError("Existing voice origin record is invalid or conflicts")
            return asset_id
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                    dir=self.voice_root, prefix=".origin-",
                    suffix=".tmp", mode="w", encoding="utf-8", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(record, handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            # Atomic create-without-overwrite. Two workers producing identical
            # bytes may race, but neither may replace the other's origin claim.
            try:
                os.link(temporary, origin_path)
            except FileExistsError:
                if self.read_voice_origin(asset_id) != record:
                    raise ValueError("Existing voice origin record is invalid or conflicts")
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
        return asset_id

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
