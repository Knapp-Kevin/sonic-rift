"""Non-destructive, unsigned source-origin inventory for Sonic Rift Studio.

This is a *local evidence inventory*, not an AI detector and not a C2PA
Content Credential. Local asset metadata can be forged by someone with write
access; even a matching media digest does not authenticate its origin.

No source media is changed and no prompts, lyrics, file paths, user identifiers,
seeds, or private settings leave this module. The C2PA claim generator will
consume reviewed provenance from a later, separately qualified component.
"""

import re

from this_voice_thing.core.music.catalog import ENGINES as MUSIC_ENGINES
from this_voice_thing.core.soundscape.catalog import ENGINES as SOUND_ENGINES

SCHEMA_VERSION = 1
_SOUND_ASSET = re.compile(r"sound_([a-f0-9]{12})\Z")
_VOICE_ASSET = re.compile(r"voice_([a-f0-9]{64})\Z")

AI = "ai_generated"
NON_AI_SYNTHESIS = "non_ai_synthesis"
UNKNOWN = "unknown"


def _sound_origin(asset, *, content_verified):
    """Make only the assertions supported by a recognized local engine record.

    A successful media checksum proves agreement with the local index, not a
    trustworthy chain of custody. Imported or tampered records stay unknown.
    """
    if not content_verified:
        return UNKNOWN, "media_missing_or_modified", None, None, None
    engine_id = getattr(asset, "engine", None)
    claimed_model = getattr(asset, "model", "") or ""
    if engine_id == "procedural" and not claimed_model:
        return NON_AI_SYNTHESIS, "unverified_local_engine_claim", "procedural", None, None
    if engine_id in MUSIC_ENGINES:
        catalog = MUSIC_ENGINES[engine_id]
        model_id = catalog.repo_id
        settings = getattr(asset, "settings", {}) or {}
        if not isinstance(settings, dict):
            return UNKNOWN, "invalid_local_engine_claim", None, None, None
        revision = settings.get("model_revision")
        # Old records lacking the pin can identify the engine family, but
        # never claim an exact weight revision they didn't record.
        if (claimed_model and claimed_model != model_id) or (
                revision is not None and revision != catalog.model_revision):
            return UNKNOWN, "conflicting_local_engine_claim", None, None, None
        return AI, "unverified_local_engine_claim", engine_id, model_id, (
            revision if isinstance(revision, str) else None)
    if engine_id in SOUND_ENGINES and SOUND_ENGINES[engine_id].kind == "model":
        catalog = SOUND_ENGINES[engine_id]
        if claimed_model and claimed_model != catalog.repo_id:
            return UNKNOWN, "conflicting_local_engine_claim", None, None, None
        return AI, "unverified_local_engine_claim", engine_id, catalog.repo_id, None
    return UNKNOWN, "unrecognized_local_engine", None, None, None


def project_origin_inventory(project, sound_library):
    """Return a bounded *internal* candidate inventory for future signing.

    Every rendered clip is represented, including duplicates and reused stems.
    Unknown or imported voice audio is never assumed to be a human recording.
    Only known on-disk Sound Library records with matching bytes are classified
    as locally asserted AI generation or procedural (non-AI) synthesis.

    All evidence is local and presently unsigned; consumers MUST NOT label this
    inventory as a verified C2PA credential. Internal source hashes and clip IDs
    are linkable and require separate privacy review before any public export.
    No source audio gets modified.
    """
    project.validate()
    ingredients = []
    for track in project.tracks:
        for clip in track.clips:
            origin, evidence, engine, model, model_revision = (
                UNKNOWN, "source_not_attested", None, None, None)
            media_sha256 = None
            if clip.asset_id:
                sound = _SOUND_ASSET.fullmatch(clip.asset_id)
                voice = _VOICE_ASSET.fullmatch(clip.asset_id)
                if sound:
                    asset = sound_library.get(sound.group(1))
                    if asset is None:
                        evidence = "local_asset_not_found"
                    else:
                        # Audio integrity must be checked before deriving claims.
                        # Source metadata is mutable even if the bytes match.
                        verified = bool(sound_library.verify(asset))
                        origin, evidence, engine, model, model_revision = _sound_origin(
                            asset, content_verified=verified)
                        if verified:
                            checksum = getattr(asset, "sha256", "")
                            if isinstance(checksum, str) and re.fullmatch(
                                    r"[a-f0-9]{64}", checksum):
                                media_sha256 = checksum
                elif voice:
                    # A content-addressed WAV is not proof of human authorship
                    # or AI provenance; generation-time attestation is missing.
                    evidence = "voice_origin_unrecorded"
                    # The asset ID carries a digest string, but this function
                    # has not read or verified the underlying WAV bytes.
                    media_sha256 = None
                else:
                    evidence = "unsupported_asset_id"
            else:
                evidence = "not_rendered"
            ingredients.append({
                "track_id": track.id,
                "clip_id": clip.id,
                "asset_id": clip.asset_id or None,
                "start_frame": clip.start_frame,
                "frame_count": clip.frame_count,
                "source_offset_frames": clip.source_offset_frames,
                "origin": origin,
                "evidence": evidence,
                "engine": engine,
                "model_id": model,
                "model_revision": model_revision,
                "media_sha256": media_sha256,
            })
    origins = {item["origin"] for item in ingredients}
    if AI in origins:
        overall = "mixed_ai_and_other" if len(origins) > 1 else AI
    elif UNKNOWN in origins or not origins:
        overall = UNKNOWN
    else:
        overall = NON_AI_SYNTHESIS
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": project.id,
        "project_revision": project.revision,
        "sample_rate": project.sample_rate,
        "classification": overall,
        "evidence_status": "unsigned_unverified_local_inventory",
        "contains_ai": AI in origins,
        "contains_unknown": UNKNOWN in origins,
        "model_ids": sorted({item["model_id"] for item in ingredients if item["model_id"]}),
        "ingredients": ingredients,
    }
