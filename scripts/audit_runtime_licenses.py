#!/usr/bin/env python3
"""Inventory installed Python distribution licensing, without importing engines.

This is a review aid, not a license determination or a software bill of materials.
Each configured interpreter queries its own importlib.metadata in isolated mode.
No packages, model weights, or networks are touched by this program.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_INSPECTOR = r'''
import importlib.metadata as md
import json

def canonical(name):
    return ''.join('-' if ch in '._-' else ch.lower() for ch in name)

results = []
for dist in md.distributions():
    metadata = dist.metadata
    name = metadata.get('Name')
    if not name:
        continue
    classifiers = metadata.get_all('Classifier', [])
    license_field = (metadata.get('License') or '').strip()
    results.append({
        'name': name,
        'canonical_name': canonical(name),
        'version': dist.version,
        'license_expression': (metadata.get('License-Expression') or '').strip(),
        'license_field': license_field[:512],
        'license_field_truncated': len(license_field) > 512,
        'license_classifiers': [c for c in classifiers if c.startswith('License ::')],
    })
print(json.dumps(sorted(results, key=lambda d: (d['canonical_name'], d['version'])), ensure_ascii=False))
'''

# Review-only heuristics. Not declarations of actual current license status.
WATCHED_PACKAGES = {
    "kaldiio": "Historical VoxCPM environment included an evaluation-limited release; inspect the installed version's actual LICENSE.",
    "espeakng-loader": "May bundle GPL espeak-ng binaries; check component and redistribution rights.",
    "phonemizer-fork": "Historically reported GPL; verify the precise installed distribution.",
    "praat-parselmouth": "Historically reported GPL; check current license and dynamic use.",
    "pykakasi": "Historically reported GPL; check current license and runtime coupling.",
    "pyside6": "Qt LGPL/GPL licensing options require separate review for intended distribution.",
    "pyside6-addons": "Qt addons may have module-specific obligations; check used modules.",
    "shiboken6": "PySide6 component; verify current LGPL/GPL terms.",
}


def canonical_name(value):
    return "".join("-" if ch in "._-" else ch.lower() for ch in value)


def classify(package):
    """Return conservative review flags; do not label any dependency cleared."""
    flags = []
    name = canonical_name(package["name"])
    declared = " ".join((
        package.get("license_expression", ""),
        package.get("license_field", ""),
        " ".join(package.get("license_classifiers", [])),
    )).lower()
    if name in WATCHED_PACKAGES:
        flags.append("known_dependency_review")
    if not declared.strip():
        flags.append("no_license_metadata")
    if any(marker in declared for marker in ("non-commercial", "noncommercial", "evaluation", "research only")):
        flags.append("possible_use_restriction")
    if "gpl" in declared or "agpl" in declared or "lgpl" in declared:
        flags.append("copyleft_or_dual_license_review")
    if package.get("license_field_truncated"):
        flags.append("truncated_license_metadata")
    return flags


def review_environment(label, distributions):
    if not isinstance(distributions, list):
        raise ValueError("Expected a list of installed distributions")
    records = []
    seen = set()
    for record in distributions:
        if not isinstance(record, dict) or not isinstance(record.get("name"), str) or not isinstance(record.get("version"), str):
            raise ValueError("Invalid distribution record")
        name = canonical_name(record["name"])
        if name in seen:
            raise ValueError("Duplicate installed distribution name: " + name)
        seen.add(name)
        r = {key: record.get(key) for key in (
            "name", "version", "license_expression", "license_field",
            "license_field_truncated", "license_classifiers",
        )}
        r["review_flags"] = classify(record)
        if name in WATCHED_PACKAGES:
            r["manual_review_reason"] = WATCHED_PACKAGES[name]
        records.append(r)
    records.sort(key=lambda item: canonical_name(item["name"]))
    return {
        "environment": label,
        "distribution_count": len(records),
        "flagged_count": sum(bool(r["review_flags"]) for r in records),
        "distributions": records,
    }


def inspect_python(interpreter, *, timeout=90):
    try:
        completed = subprocess.run(
            [str(interpreter), "-I", "-c", _INSPECTOR],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Interpreter inventory failed: " + str(exc)) from exc
    try:
        distributions = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Interpreter returned invalid package inventory") from exc
    if not isinstance(distributions, list):
        raise RuntimeError("Interpreter returned invalid package inventory")
    return distributions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", dest="interpreters", action="append", metavar="LABEL=PYTHON_PATH",
                        help="Repeat for each installed engine environment; default is current Python")
    parser.add_argument("--output", type=Path, help="Optional explicit destination; otherwise print JSON only")
    args = parser.parse_args(argv)
    selected = args.interpreters or ["current=" + sys.executable]
    environments = []
    labels = set()
    for value in selected:
        label, sep, path = value.partition("=")
        if not sep or not label.strip() or not path.strip():
            parser.error("--python must be LABEL=PYTHON_PATH")
        if label in labels:
            parser.error("Environment labels must be unique")
        labels.add(label)
        environments.append(review_environment(label, inspect_python(path)))
    report = {
        "schema_version": 1,
        "method": "Python -I importlib.metadata, no imports of installed packages",
        "license_decision": "not_cleared_manual_review_required",
        "note": "Package metadata may be incomplete or misleading. Model weights, native DLLs and copyright clearance need separate inspection.",
        "environments": environments,
    }
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
