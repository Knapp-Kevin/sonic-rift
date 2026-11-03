"""Write MANIFEST.md for the review cut: every delivered file with its SHA-256, size and provenance."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
NAME = "sonic-rift-world-in-sound-v091-review"
ROLE = {
    f"{NAME}.mp4": "Review cut, sound on (H.264 1920x1080 30 fps, AAC 48 kHz stereo)",
    f"{NAME}-silent-captioned.mp4": "Silent cut with burned-in beat titles and speaker-labelled captions",
    f"{NAME}.en.vtt": "WebVTT captions, speaker-tagged",
    f"{NAME}-poster.jpg": "Poster frame: the balanced Studio after Check balance (real app grab)",
    "transcript.md": "Full transcript with on-screen actions",
    "soundtrack.wav": "Final soundtrack (normalized -16 LUFS, limited to -1 dBFS)",
    "stems/narration.wav": "Stem: Guide narration and brand tagline (approved WAVs, unchanged sources)",
    "stems/dialogue.wav": "Stem: character takes heard on Speech (generated on camera by v0.9.1)",
    "stems/music.wav": "Stem: the two music auditions (new ACE-Step take; kept take D)",
    "stems/effects.wav": "Stem: the ocean audition (procedural, seed 53)",
    "stems/scene-mix.wav": "Stem: the Studio's own Play mix as heard in the film",
    "timeline.json": "Edit decision list: events, levels, dead-air trims, playback re-timing, captions",
    "qa_transcription.json": "Transcription QA with Sonic Rift's own transcriber",
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def describe(rel):
    if rel in ROLE:
        return ROLE[rel]
    if rel.startswith("app-export/"):
        return "Sonic Rift's own Export mix output (master, per-track stems, manifest) and saved project"
    if rel.startswith("source-audio/vo-"):
        return "Approved Guide/brand narration, byte-identical to docs/marketing/audio"
    if rel.startswith("source-audio/"):
        return "Audio the app produced during the session (copied unchanged)"
    if rel.startswith("screenshots/"):
        return "Real app grab (2400x1350) from the filmed session"
    if rel.startswith("tools/"):
        return "Production script (capture, assembly, QA)"
    if rel.startswith("build/"):
        return "Assembly input (frame list, overlay text, opener, end card)"
    return ""


rows = []
for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
    rel = path.relative_to(OUT).as_posix()
    if rel in ("MANIFEST.md",) or rel.startswith("build/overlay/"):
        continue
    rows.append((rel, path.stat().st_size, sha(path), describe(rel)))
lines = ["# Media manifest: v0.9.1 review cut 1", "",
         "Every delivered file, its size and SHA-256. Paths are relative to this folder. "
         "Build overlay text files are omitted. See QA_REPORT.md for application and release identification.", "",
         "| File | Bytes | SHA-256 | What it is |", "|---|---:|---|---|"]
lines += [f"| `{rel}` | {size} | `{digest}` | {what} |" for rel, size, digest, what in rows]
(OUT / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(len(rows), "files")
