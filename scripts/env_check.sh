#!/usr/bin/env bash
set -euo pipefail
python scripts/check_python_deps.py
python check_env.py --auto-install
