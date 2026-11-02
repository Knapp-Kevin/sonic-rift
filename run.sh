#!/usr/bin/env bash
# Bring the environment up to date, then start Sonic Rift.
set -euo pipefail
cd "$(dirname "$0")"

bash setup_env.sh

echo
echo "Launching main.py..."
exec .venv/bin/python main.py
