#!/usr/bin/env bash
# Sonic Rift environment bootstrap for macOS and Linux.
# Steps: check tools, make the Python 3.11 venv, refresh the lock, sync packages, install PyTorch.
# Each step is skipped when its stamp file is newer than its inputs.
# UV_APP_DRY=1 skips the PyTorch step. Any failed step stops the script with a non-zero exit.
set -euo pipefail
cd "$(dirname "$0")"

WANT_PY="3.11"
VENV=".venv"
VENV_PY="$VENV/bin/python"
REQ_IN="requirements.in"
REQ_LOCK="requirements.lock.txt"
REQ_RUNTIME="$VENV/.requirements.runtime.lock.txt"
STAMP_DEPS="$VENV/.deps_installed"
STAMP_TORCH="$VENV/.torch_checked"
TORCH_SCRIPT="scripts/install_torch.py"
DRY="${UV_APP_DRY:-0}"

# One log per run; install_torch.py appends to the same file.
mkdir -p logs
LOG_FILE="logs/installer_$(date +%Y%m%d_%H%M%S).log"
export CHATTERBOX_INSTALL_LOG="$PWD/$LOG_FILE"

note() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }
say() { echo "$*"; note "$*"; }
die() { say "ERROR: $*"; exit 1; }
quietly() { "$@" >> "$LOG_FILE" 2>&1; }

# stale TARGET SOURCE...: true when TARGET is missing or older than any existing SOURCE.
stale() {
    local target="$1" source
    shift
    [ -e "$target" ] || return 0
    for source in "$@"; do
        if [ -e "$source" ] && [ "$source" -nt "$target" ]; then
            return 0
        fi
    done
    return 1
}

runs_wanted_python() {
    "$1" -c "import sys; sys.exit('.'.join(map(str, sys.version_info[:2])) != '$WANT_PY')" >/dev/null 2>&1
}

find_python() {
    local candidate
    for candidate in "python$WANT_PY" python3; do
        if command -v "$candidate" >/dev/null 2>&1 && runs_wanted_python "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

step_tools() {
    BASE_PY="$(find_python)" || die "Python $WANT_PY was not found. Install Python $WANT_PY and run this again."
    note "Using Python interpreter: $BASE_PY"
    command -v uv >/dev/null 2>&1 \
        || die "uv was not found. See https://github.com/astral-sh/uv#getting-started/installation"
    note "python and uv are on PATH."
}

step_venv() {
    if [ -x "$VENV_PY" ] && runs_wanted_python "$VENV_PY"; then
        note "$VENV already runs Python $WANT_PY."
        return 0
    fi
    if [ -d "$VENV" ]; then
        say "$VENV does not run Python $WANT_PY; rebuilding it."
        rm -rf "$VENV"           # a new venv has no stamps, so every later step runs again
    fi
    say "Creating venv with Python $WANT_PY..."
    quietly uv venv "$VENV" --python "$BASE_PY" || die "Could not create the virtual environment."
}

step_lock() {
    if ! stale "$REQ_LOCK" "$REQ_IN"; then
        say "Lock file already up to date."
        return 0
    fi
    say "Compiling $REQ_LOCK from $REQ_IN..."
    quietly uv pip compile "$REQ_IN" -o "$REQ_LOCK" || die "Lock file generation failed."
}

step_packages() {
    # PyTorch comes from its own index in step_torch, so drop its pins here.
    grep -v -E '^torch(audio|vision)?==' "$REQ_LOCK" > "$REQ_RUNTIME" || die "Could not write $REQ_RUNTIME."
    if ! stale "$STAMP_DEPS" "$REQ_LOCK"; then
        say "Dependencies already installed. Skipping runtime dependency install."
        return 0
    fi
    say "Installing dependencies from lock file..."
    quietly uv pip install --python "$VENV_PY" -r "$REQ_RUNTIME" --strict \
        || die "Dependency installation from lock file failed."
    echo "Dependencies synced from $REQ_RUNTIME" > "$STAMP_DEPS"
}

step_torch() {
    local needed=0
    stale "$STAMP_TORCH" "$TORCH_SCRIPT" "$REQ_LOCK" && needed=1
    if ! "$VENV_PY" -c "import torch, torchaudio, torchvision" >/dev/null 2>&1; then
        note "PyTorch does not import; reinstalling it."
        needed=1
    fi
    if [ "$needed" = 0 ]; then
        say "PyTorch already checked. Skipping install_torch.py."
        return 0
    fi
    rm -f "$STAMP_TORCH"
    say "Installing PyTorch..."
    "$VENV_PY" "$TORCH_SCRIPT" || die "PyTorch install failed. App may lack GPU support."
    echo "PyTorch checked by install_torch.py" > "$STAMP_TORCH"
}

echo
say "=== Starting Sonic Rift Installer ==="
echo "Installer log: $LOG_FILE"
note "Dry Run Mode: $DRY"

step_tools
step_venv
step_lock
step_packages
if [ "$DRY" = "0" ]; then
    step_torch
else
    say "[Dry Run] Skipped PyTorch installation"
fi
say "Setup complete."
