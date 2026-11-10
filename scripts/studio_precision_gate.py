"""Offline, exact-commit Studio precision qualification with auditable receipts.

Runs only locally selected unit tests. No model installs, network calls, CI or
release operations. Successful tests are NOT an owner playback acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
FOCUSED = (
    "tests.test_audio_precision_clip_edit",
    "tests.test_audio_clipboard",
    "tests.test_editor_precision_controls",
    "tests.test_editor_clipboard_controls",
    "tests.test_timeline_multiselect",
    "tests.test_audio_project_session",
    "tests.test_project_timeline",
    "tests.test_timeline_drag_trim",
    "tests.test_studio_page",
)


def git(*args):
    completed = subprocess.run(
        ("git", *args), cwd=ROOT, text=True,
        capture_output=True, timeout=20, check=True)
    return completed.stdout.strip()


def execute(label, command, folder, env):
    log = folder / (label + ".log")
    start = time.monotonic()
    exit_code = None
    error = None
    with log.open("wb") as output:
        try:
            completed = subprocess.run(
                command, cwd=ROOT, env=env, stdout=output,
                stderr=subprocess.STDOUT, timeout=1200, check=False)
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            error = "test process exceeded 20-minute limit"
        except OSError as exc:
            error = type(exc).__name__
    return {
        "name": label, "command": command, "exit_code": exit_code,
        "error": error, "duration_seconds": round(time.monotonic() - start, 2),
        "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "log_filename": log.name,
        "pass": exit_code == 0 and error is None,
    }


def isolated_test_env(run_dir):
    """Redirect test profile/cache writes away from a real Windows identity.

    Python packages and executable paths remain unchanged. This is an
    environment-level safeguard, NOT a filesystem/network sandbox. Inspect
    individual tests before running if they invoke untrusted native software.
    """
    home = run_dir / "isolated-profile"
    directories = {
        "USERPROFILE": home,
        "HOME": home,
        "APPDATA": home / "AppData" / "Roaming",
        "LOCALAPPDATA": home / "AppData" / "Local",
        "XDG_CONFIG_HOME": home / ".config",
        "XDG_DATA_HOME": home / ".local" / "share",
        "XDG_CACHE_HOME": home / ".cache",
        "HF_HOME": home / ".cache" / "huggingface",
        "TORCH_HOME": home / ".cache" / "torch",
        "MPLCONFIGDIR": home / ".cache" / "matplotlib",
        "TEMP": run_dir / "temp",
        "TMP": run_dir / "temp",
        "TMPDIR": run_dir / "temp",
    }
    env = os.environ.copy()
    for name, destination in directories.items():
        destination.mkdir(parents=True, exist_ok=True)
        env[name] = str(destination)
    # Avoid *expected* model fetches; these flags do not block arbitrary network
    # access. No test may be treated as sandboxed merely because they are set.
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PIP_NO_INDEX": "1",
        "WANDB_MODE": "offline",
    })
    return env


def main():
    parser = argparse.ArgumentParser(
        description="Run offline Sonic Rift Studio qualification on an exact Windows commit")
    parser.add_argument("--expected-head", required=True, help="Full expected 40-hex Git commit")
    parser.add_argument("--receipt-dir", required=True, type=Path,
                        help="Existing or new folder outside the source tree")
    parser.add_argument("--full", action="store_true",
                        help="Also run the entire unittest discovery suite")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-fA-F0-9]{40}", args.expected_head):
        parser.error("--expected-head must be a full 40-character Git SHA")
    folder = args.receipt_dir.resolve()
    if folder == ROOT or ROOT in folder.parents:
        parser.error("--receipt-dir must be outside the source checkout")
    folder.mkdir(parents=True, exist_ok=True)
    # Every invocation owns a unique evidence directory. Reusing a
    # common receipt root must never overwrite logs cited by an older receipt.
    run_dir = folder / ("studio-precision-" + uuid.uuid4().hex)
    run_dir.mkdir(mode=0o700)

    receipt = {
        "contract": "sonic-rift-studio-precision-acceptance-v1",
        "run_id": run_dir.name,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "expected_head": args.expected_head.lower(),
        "actual_head": None,
        "worktree_clean_before": False,
        "worktree_clean_after": None,
        "full_suite_requested": bool(args.full),
        "stages": [],
        "status": "NO_GO",
        "owner_gui_audio_acceptance": "NOT_RUN",
        "note": "No test outcome alone proves owner listening, installer or live workflow.",
    }
    try:
        receipt["actual_head"] = git("rev-parse", "HEAD").lower()
        receipt["worktree_clean_before"] = not bool(
            git("status", "--porcelain", "--untracked-files=normal"))
        if (os.name == "nt" and receipt["worktree_clean_before"]
                and receipt["actual_head"] == receipt["expected_head"]):
            env = isolated_test_env(run_dir)
            command = [sys.executable, "-m", "unittest", "-v", *FOCUSED]
            focused = execute("focused", command, run_dir, env)
            receipt["stages"].append(focused)
            if focused["pass"] and args.full:
                full = execute("full", [
                    sys.executable, "-m", "unittest", "discover", "-s", "tests",
                ], run_dir, env)
                receipt["stages"].append(full)
            receipt["worktree_clean_after"] = not bool(
                git("status", "--porcelain", "--untracked-files=normal"))
            if (receipt["worktree_clean_after"]
                    and all(stage["pass"] for stage in receipt["stages"])):
                receipt["status"] = (
                    "CODE_GATES_PASSED_PENDING_OWNER_ACCEPTANCE"
                    if args.full else "FOCUSED_TESTS_PASSED_FULL_NOT_RUN")
        else:
            receipt["preflight_blocker"] = (
                "Requires Windows, clean checkout, and exact expected HEAD")
    except (subprocess.SubprocessError, OSError) as exc:
        receipt["preflight_blocker"] = type(exc).__name__

    path = run_dir / "receipt.json"
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")
    print(receipt["status"])
    print("Receipt:", path)
    for stage in receipt["stages"]:
        print(stage["name"], "pass" if stage["pass"] else "FAIL",
              "log:", run_dir / stage["log_filename"])
    return 0 if receipt["status"] != "NO_GO" else 2


if __name__ == "__main__":
    sys.exit(main())
