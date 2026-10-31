#!/usr/bin/env python3
"""Offline Git-object inventory of Sonic Rift's historical source ancestry.

This tool compares tracked blob identities, not authorship. Different object
hashes cannot prove independent implementation or license clearance. It does
not fetch, install, mutate files, use a GPU, or call a network service.
"""
import argparse
import json
import subprocess
from pathlib import Path

UPSTREAM_COMMIT = "22460fd99ceb78c309f879b93878240241a0dc9b"

# These are review targets, NOT proven copyrights or claims of verbatim copies.
MOVED_REVIEW = {
    "model_backends.py": ("this_voice_thing/engines/chatterbox_backend.py",),
    "main.py": (
        "main.py",
        "this_voice_thing/ui/threads.py",
        "this_voice_thing/ui/common.py",
        "this_voice_thing/ui/main_window.py",
        "this_voice_thing/ui/pages/generation.py",
        "this_voice_thing/ui/pages/player.py",
        "this_voice_thing/ui/pages/model_loading.py",
        "this_voice_thing/ui/pages/generate.py",
    ),
    "launch_app.py": ("this_voice_thing/app.py",),
    "install_torch.py": ("scripts/install_torch.py",),
    "run.bat": ("run.bat",),
    "run.sh": ("run.sh",),
    "setup_env.bat": ("setup_env.bat",),
    "setup_env.sh": ("setup_env.sh",),
    "requirements.in": ("requirements.in",),
    "requirements.lock.txt": ("requirements.lock.txt",),
    "LICENSE": ("LICENSES/MIT-Chatterbox-TTS-UI.txt",),
}

REVIEW_AREAS = {
    "model_workers": ("this_voice_thing/ui/threads.py", "this_voice_thing/core/engine_loading.py"),
    "bootstrap_and_global_state": ("this_voice_thing/ui/common.py",),
    "application_shell": ("this_voice_thing/ui/main_window.py", "this_voice_thing/ui/widgets.py"),
    "chatterbox_adapter": (
        "this_voice_thing/engines/chatterbox_backend.py",
        "this_voice_thing/engines/chatterbox_provider.py",
    ),
    "launch_and_environment": (
        "run.bat", "run.sh", "setup_env.bat", "setup_env.sh",
        "scripts/install_torch.py",
    ),
    "source_license_and_notices": ("LICENSE", "NOTICE", "LICENSES/MIT-Chatterbox-TTS-UI.txt", "THIRD_PARTY_NOTICES.md"),
}


def parse_tree(raw):
    """Read git ls-tree -rz records, preserving spaces and Unicode in paths."""
    output = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            header, name = record.split(b"\t", 1)
            mode, kind, sha = header.decode("ascii").split(" ")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Malformed git ls-tree entry") from exc
        if kind == "blob":
            output[name.decode("utf-8", "surrogateescape")] = sha
    return output


def git_output(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def git_tree(root, revision):
    # Revision must resolve to a Git commit; no remote lookup or network.
    git_output(root, "rev-parse", "--verify", revision + "^{commit}")
    return parse_tree(git_output(root, "ls-tree", "-r", "-z", revision))


def build_report(current, upstream, *, current_revision, upstream_revision):
    """Only exact blob equality is verified; moved-path similarities are unknown."""
    upstream_by_blob = {}
    for path, blob in upstream.items():
        upstream_by_blob.setdefault(blob, []).append(path)
    exact = []
    for path, blob in sorted(current.items()):
        if blob in upstream_by_blob:
            exact.append({
                "current_path": path, "blob": blob,
                "upstream_paths": sorted(upstream_by_blob[blob]),
            })

    mapped = []
    for source, destinations in MOVED_REVIEW.items():
        for destination in destinations:
            src_blob = upstream.get(source)
            dst_blob = current.get(destination)
            mapped.append({
                "upstream_path": source,
                "current_path": destination,
                "upstream_blob": src_blob,
                "current_blob": dst_blob,
                "evidence": (
                    "exact_same_blob" if src_blob is not None and src_blob == dst_blob
                    else "changed_blob_review_required" if src_blob and dst_blob
                    else "path_missing_or_unavailable"
                ),
            })

    areas = {
        area: [{"path": path, "current_blob": current.get(path)}
               for path in paths]
        for area, paths in REVIEW_AREAS.items()
    }
    return {
        "schema_version": 1,
        "comparison": {"current_ref": current_revision, "upstream_ref": upstream_revision},
        "counts": {
            "current_tracked_blobs": len(current),
            "upstream_tracked_blobs": len(upstream),
            "current_paths_with_exact_upstream_blob": len(exact),
        },
        "exact_blob_matches": exact,
        "mapped_review_candidates": mapped,
        "manual_review_areas": areas,
        "interpretation": (
            "An exact blob match proves byte-identical Git object contents at these two "
            "revisions only. Changed or absent blobs do not prove independent authorship, "
            "absence of adapted code, legal clearance, or engine/model licensing rights."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--current", default="HEAD", help="Existing local Git commit/ref")
    parser.add_argument("--upstream", default=UPSTREAM_COMMIT,
                        help="Existing local upstream commit (historical default)")
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    try:
        current = git_tree(root, args.current)
        upstream = git_tree(root, args.upstream)
    except (OSError, subprocess.CalledProcessError) as exc:
        parser.error(
            "Cannot read the requested local Git revisions. Ensure the historical "
            "upstream commit is present locally; no network fetch is performed. "
            f"Detail: {exc}"
        )
    report = build_report(
        current, upstream, current_revision=args.current,
        upstream_revision=args.upstream,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
