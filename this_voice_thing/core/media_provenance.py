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
    source_event = getattr(asset, "source_event", {})
    if source_event:
        expected_fields = {"origin", "engine", "model_id", "model_revision",
                           "media_sha256", "evidence_status"}
        checksum = getattr(asset, "sha256", None)
        if (type(source_event) is not dict or set(source_event) != expected_fields
                or source_event["engine"] != engine_id
                or source_event["media_sha256"] != checksum
                or source_event["evidence_status"] != "unsigned_local_generation_event"):
            return UNKNOWN, "invalid_local_generation_event", None, None, None
        if (engine_id == "procedural"
                and source_event["origin"] == NON_AI_SYNTHESIS
                and source_event["model_id"] == ""
                and source_event["model_revision"] == ""
                and not claimed_model):
            return NON_AI_SYNTHESIS, "unsigned_local_generation_event", engine_id, None, None
        known = MUSIC_ENGINES.get(engine_id) or SOUND_ENGINES.get(engine_id)
        if (known is None or engine_id == "procedural"
                or source_event["origin"] != AI
                or source_event["model_id"] != known.repo_id
                or (claimed_model and claimed_model != known.repo_id)
                or type(source_event["model_revision"]) is not str
                or len(source_event["model_revision"]) > 200):
            return UNKNOWN, "conflicting_local_generation_event", None, None, None
        return AI, "unsigned_local_generation_event", engine_id, known.repo_id, (
            source_event["model_revision"] or None)
    # Legacy labels may originate from prior Sonic Rift builds, imports or
    # manual edits. No generation-time event was captured, so the current
    # categorical disclosure must remain unknown rather than infer AI/human.
    if engine_id in MUSIC_ENGINES or engine_id in SOUND_ENGINES:
        return UNKNOWN, "legacy_engine_label_without_event", None, None, None
    return UNKNOWN, "unrecognized_local_engine", None, None, None


def _summarize_origin_items(ingredients):
    """Deterministic summary shared by whole-mix and per-stem disclosures."""
    origins = {item["origin"] for item in ingredients}
    if AI in origins:
        overall = "mixed_ai_and_other" if len(origins) > 1 else AI
    elif UNKNOWN in origins or not origins:
        overall = UNKNOWN
    else:
        overall = NON_AI_SYNTHESIS
    return {
        "classification": overall,
        "contains_ai": AI in origins,
        "contains_unknown": UNKNOWN in origins or not origins,
        "model_ids": sorted({item["model_id"] for item in ingredients if item["model_id"]}),
    }


def project_origin_inventory(project, sound_library, *, voice_media=None):
    """Return a bounded *internal* candidate inventory for future signing.

    Every rendered clip is represented, including duplicates and reused stems.
    Unknown or imported voice audio is never assumed to be a human recording.
    Only generation-time origin events bound to verified Sound Library media
    are classified as locally asserted AI/procedural sources. Legacy labels
    remain unknown even when their catalog engine name looks convincing.

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
                    # A content-addressed WAV alone proves neither human
                    # recording nor AI generation; only the app's own successful
                    # TTS path writes a bound, unsigned local origin event.
                    evidence = "voice_origin_unrecorded"
                    if voice_media is not None:
                        record = voice_media.read_voice_origin(clip.asset_id)
                        if record is not None:
                            origin = AI
                            evidence = record["evidence_status"]
                            engine = record["engine"]
                            media_sha256 = record["media_sha256"]
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
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": project.id,
        "project_revision": project.revision,
        "sample_rate": project.sample_rate,
        "evidence_status": "unsigned_unverified_local_inventory",
        **_summarize_origin_items(ingredients),
        "ingredients": ingredients,
    }


def public_origin_disclosure(inventory):
    """Privacy-minimized summary suitable for an *unsigned export sidecar*.

    Never include project IDs, source hashes, paths, speech text, prompts, seeds,
    voice references, personal identifiers or per-clip time locations. This is
    explicit disclosure, not cryptographic origin verification.
    """
    if (type(inventory) is not dict
            or inventory.get("evidence_status") != "unsigned_unverified_local_inventory"):
        raise ValueError("Expected an unsigned local source inventory")
    ingredients = inventory["ingredients"]
    counts = {
        "ai_generated": sum(item["origin"] == AI for item in ingredients),
        "non_ai_synthesis": sum(item["origin"] == NON_AI_SYNTHESIS for item in ingredients),
        "unknown": sum(item["origin"] == UNKNOWN for item in ingredients),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "disclosure_status": "unsigned_local_claims_not_c2pa",
        "c2pa_signed": False,
        "c2pa_embedded": False,
        "classification": inventory["classification"],
        "contains_ai": inventory["contains_ai"],
        "contains_unknown": inventory["contains_unknown"],
        "model_ids": list(inventory["model_ids"]),
        "clip_source_counts": counts,
    }


def public_stem_disclosures(inventory, stem_files):
    """Per-exported-stem AI/unknown summaries, without private asset references.

    This is unsigned JSON and cannot be validated as C2PA. Stems are indexed
    by their already-exported relative filenames, never by public source IDs.
    A silent or empty track is unknown, not an assertion of human authorship.
    """
    if (type(inventory) is not dict
            or inventory.get("evidence_status") != "unsigned_unverified_local_inventory"
            or type(stem_files) is not dict):
        raise ValueError("Expected the inventory and export stem mapping")
    output = {}
    for track_id, filename in stem_files.items():
        if type(track_id) is not str or type(filename) is not str:
            raise ValueError("Invalid stem identifiers")
        items = [item for item in inventory["ingredients"] if item["track_id"] == track_id]
        subinventory = {
            "evidence_status": "unsigned_unverified_local_inventory",
            **_summarize_origin_items(items),
            "ingredients": items,
        }
        output[filename] = public_origin_disclosure(subinventory)
    return output
