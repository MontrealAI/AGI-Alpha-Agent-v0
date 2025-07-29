#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
#
# Alpha-Factory Quickstart Launcher
# Professional production-ready script to bootstrap and run Alpha-Factory v1

set -Eeuo pipefail
trap 'echo -e "\n\u274c Error on line $LINENO" >&2' ERR

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PIP_LOG="pip-install.log"  # log pip output for troubleshooting
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  # always operate from repository root
export PYTHONPATH="${PWD}:${PYTHONPATH:-}"

# use local wheels when available
# shellcheck disable=SC2155
if [[ -z "${WHEELHOUSE:-}" && -d wheels ]]; then
  export WHEELHOUSE="$(pwd)/wheels"
fi
PIP_ARGS=()
[[ -n "${WHEELHOUSE:-}" ]] && PIP_ARGS=(--no-index --find-links "$WHEELHOUSE")

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
color() { printf '\033[1;%sm%s\033[0m\n' "$1" "$2"; }
info() { color 34 "$1"; }
warn() { color 33 "$1"; }

prompt() {
  if [[ $WIZARD -eq 1 ]]; then
    read -rp "$1 [Y/n] " answer
    [[ ${answer:-Y} =~ ^[Yy]$ ]]
  else
    return 0
  fi
}

check_dep() {
  if ! command -v "$1" >/dev/null 2>&1; then
    warn "Missing dependency: $1"
    warn "Install with: $2"
    return 1
  fi
}

check_deps() {
  local missing=0
  check_dep python3 "sudo apt install python3" || missing=1
  check_dep git "sudo apt install git" || missing=1
  check_dep docker "sudo apt install docker.io" || missing=1
  check_dep docker-compose "sudo apt install docker-compose" || missing=1
  if [[ $missing -eq 1 ]]; then
    warn "Please install the missing tools and rerun the script."
    prompt "Continue anyway?" || exit 1
  fi
}

check_python_version() {
  python3 - <<'PY'
import sys
req = (3, 11)
max_py = (3, 13)
if sys.version_info < req or sys.version_info >= max_py:
    print(f"❌ Python {req[0]}.{req[1]}+ and <{max_py[0]}.{max_py[1]} required", file=sys.stderr)
    sys.exit(1)
PY
}

create_venv() {
  if [[ ! -d $VENV_DIR ]]; then
    info "Creating virtual environment"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install "${PIP_ARGS[@]}" -U pip >"$PIP_LOG" 2>&1 || { warn "pip install failed"; exit 1; }
    local req="alpha_factory_v1/requirements.lock"
    [[ -f $req ]] || req="alpha_factory_v1/requirements.txt"
    "$VENV_DIR/bin/pip" install "${PIP_ARGS[@]}" -r "$req" >>"$PIP_LOG" 2>&1 || { warn "pip install failed"; exit 1; }
  fi
}

run_preflight() {
  python alpha_factory_v1/scripts/preflight.py
}

usage() {
  cat <<EOT
Usage: $0 [--preflight] [--skip-preflight] [--wizard] [orchestrator args...]

Bootstraps and launches Alpha-Factory in an isolated Python virtual environment.
  --preflight        Run environment checks and exit
  --skip-preflight   Skip automatic preflight checks before launching
  --wizard           Interactive mode guiding you through each step
  Pip install output logs to \$PIP_LOG and failures abort the script.
  Set WHEELHOUSE to install packages from a local wheel cache.
  See docs/OFFLINE_INSTALL.md#environment-variables for details.
  Any other options are passed directly to the orchestrator.
EOT
}

# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------
SKIP_PREFLIGHT=0
PRECHECK_ONLY=0
WIZARD=0
ORCH_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --preflight) PRECHECK_ONLY=1; shift ;;
    --skip-preflight) SKIP_PREFLIGHT=1; shift ;;
    --wizard) WIZARD=1; shift ;;
    *) ORCH_ARGS+=("$1"); shift ;;
  esac
done

# ---------------------------------------------------------------------------
# Main script
# ---------------------------------------------------------------------------
header() {
  echo "============================================"
  echo "         Alpha-Factory Quickstart 🚀"
  echo "============================================"
}

header
check_deps
info "Displaying disclaimer"
python3 - <<'PY'
from alpha_factory_v1.utils.disclaimer import print_disclaimer
print_disclaimer()
PY
check_python_version

VENV_DIR=".venv"
prompt "Create virtual environment at $VENV_DIR?" && create_venv

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

if [[ $PRECHECK_ONLY -eq 1 ]]; then
  run_preflight
  exit 0
fi

if [[ $SKIP_PREFLIGHT -eq 0 ]]; then
  if ! run_preflight; then
    warn "Preflight checks failed. Run 'python check_env.py --auto-install'"
    prompt "Continue anyway?" || exit 1
  else
    info "Preflight passed"
  fi
fi

info "Starting Orchestrator..."
exec python -m alpha_factory_v1.run "${ORCH_ARGS[@]}"
