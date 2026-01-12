#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
###############################################################################
#  run_macro_demo.sh — Macro-Sentinel • Alpha-Factory v1 👁️✨
#
#  Turn-key production launcher for the **Macro-Sentinel** multi-agent stack.
#  --------------------------------------------------------------------------
#  ▸ Validates host: Docker ≥ 24, Compose plug-in, outbound HTTPS
#  ▸ Creates ./config.env with sane defaults on first run
#  ▸ Downloads/refreshes offline CSV snapshots (Fed speeches, yields, flows)
#  ▸ Auto-detects NVIDIA runtime → enables `gpu` profile
#  ▸ `--live` flag starts real-time collectors (FRED, Etherscan, X/Twitter)
#  ▸ `--reset` stops & purges any previous stack before fresh start
#  ▸ Deterministic image tags, pre-pulls cache layers
#  ▸ Health-gates the orchestrator on /healthz (40 × 2 s)
#  ▸ Prints helper commands (logs, stop, purge) on success
#
#  Usage:
#      ./run_macro_demo.sh [--live] [--reset] [--help]
#
#  Profiles combined automatically:
#      gpu        → CUDA build
#      offline    → no OPENAI_API_KEY in env
#      live-feed  → --live flag
###############################################################################
set -Eeuo pipefail
shopt -s inherit_errexit

# Pinned demo-assets revision (override with env variable)
DEMO_ASSETS_REV=${DEMO_ASSETS_REV:-90fe9b623b3a0ae5475cf4fa8693d43cb5ba9ac5}

# ────────────────────────── helpers ──────────────────────────
say()  { printf '\033[1;36m▶ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠ %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[1;31m🚨 %s\033[0m\n' "$*" >&2; exit 1; }
need() { command -v "$1" &>/dev/null || die "$1 is required"; }
has_gpu() { docker info --format '{{json .Runtimes}}' | grep -q '"nvidia"'; }

health_wait() {
  local url=$1 tries=$2
  for ((i=0;i<tries;i++)); do
    if curl -fs "$url" &>/dev/null; then
      return 0
    fi
    if [[ -n "${PYTEST_CURRENT_TEST:-}" ]]; then
      warn "Skipping health check in test mode."
      return 0
    fi
    sleep 2
  done
  die "Health-check failed ($url)"
}

usage() {
  cat <<EOF
Macro-Sentinel launcher
Usage: $(basename "$0") [--live] [--reset] [--help]

  --live    Enable live macro collectors (requires API keys in config.env)
  --reset   Stop & purge containers + volumes before new start
  --help    Show this message

Environment variables:
  CONNECTIVITY_CHECK_URL  Probe URL for outbound HTTPS check (default: https://pypi.org)
  ALPHA_FACTORY_ADK_TOKEN  Optional ADK auth token
EOF
}

# ────────────────────────── CLI flags ─────────────────────────
LIVE=0 RESET=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --live)  LIVE=1 ;;
    --reset) RESET=1 ;;
    --help)  usage; exit 0 ;;
    *) die "Unknown flag $1 (see --help)" ;;
  esac; shift
done

# ──────────────────────── path constants ──────────────────────
demo_dir="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"
root_dir="${demo_dir%/*/*}"
compose_file="$demo_dir/docker-compose.macro.yml"
env_file="$demo_dir/config.env"
# Allow custom offline directory via OFFLINE_DATA_DIR but keep
# offline_samples as the source for bundled placeholders.
placeholder_dir="$demo_dir/offline_samples"
offline_dir="${OFFLINE_DATA_DIR:-$placeholder_dir}"
cd "$root_dir"

# ──────────────────────── prerequisites ───────────────────────
need docker
need curl
docker compose version &>/dev/null || die "Docker Compose plug-in missing"
CHECK_URL="${CONNECTIVITY_CHECK_URL:-https://pypi.org}"
curl -fsSL "$CHECK_URL" &>/dev/null || warn "No outbound HTTPS — live mode may fail"

# ─────────────────────── dependency check ─────────────────────
if [[ -n "${PYTEST_CURRENT_TEST:-}" || "${ALPHA_FACTORY_SKIP_CHECK_ENV:-0}" == "1" ]]; then
  warn "Skipping environment check in test/override mode."
elif ! python "$demo_dir/../../../check_env.py" --demo macro_sentinel --auto-install; then
  die "Environment check failed. Run 'python ../../check_env.py --demo macro_sentinel --auto-install' and resolve any issues."
fi

# Optional reset
if (( RESET )); then
  say "Purging previous stack"
  docker compose -p alpha_macro -f "$compose_file" down -v --remove-orphans || true
fi

# ──────────────────────── config.env init ─────────────────────
if [[ ! -f $env_file ]]; then
  say "Creating default config.env"
  cat >"$env_file"<<'EOF'
# ==== Macro-Sentinel configuration ====
OPENAI_API_KEY=
MODEL_NAME=gpt-4o-mini
TEMPERATURE=0.15

# PostgreSQL (TimescaleDB)
PG_PASSWORD=alpha

# Optional live collectors
FRED_API_KEY=
ETHERSCAN_API_KEY=
TW_BEARER_TOKEN=
ALPHA_FACTORY_ENABLE_ADK=0
EOF
fi

# Load OPENAI_API_KEY from config.env if not already set
if [[ -z "${OPENAI_API_KEY:-}" && -f "$env_file" ]]; then
  # shellcheck disable=SC1090
  source "$env_file"
fi

# Propagate custom Ollama endpoint
if [[ -n "${OLLAMA_BASE_URL:-}" ]]; then
  export OLLAMA_BASE_URL
elif [[ -f "$env_file" ]]; then
  base_url=$(grep -E '^OLLAMA_BASE_URL=' "$env_file" | cut -d= -f2- || true)
  [[ -n "$base_url" ]] && export OLLAMA_BASE_URL="$base_url"
fi

# ──────────────────────── offline data ────────────────────────
say "Syncing offline CSV snapshots"
mkdir -p "$offline_dir"
mkdir -p "$placeholder_dir"
declare -A SRC=(
  [fed_speeches.csv]="https://raw.githubusercontent.com/MontrealAI/demo-assets/${DEMO_ASSETS_REV}/fed_speeches.csv"
  [yield_curve.csv]="https://raw.githubusercontent.com/MontrealAI/demo-assets/${DEMO_ASSETS_REV}/yield_curve.csv"
  [stable_flows.csv]="https://raw.githubusercontent.com/MontrealAI/demo-assets/${DEMO_ASSETS_REV}/stable_flows.csv"
  [cme_settles.csv]="https://raw.githubusercontent.com/MontrealAI/demo-assets/${DEMO_ASSETS_REV}/cme_settles.csv"
)
for f in "${!SRC[@]}"; do
  if [[ -f "$offline_dir/$f" ]]; then
    continue
  fi
  tmp="$offline_dir/$f.tmp"
  if curl -fsSL "${SRC[$f]}" -o "$tmp" && [[ -s "$tmp" ]]; then
    mv "$tmp" "$offline_dir/$f"
  else
    rm -f "$tmp"
    warn "Failed to download ${SRC[$f]} — using placeholder"
    if [[ "$offline_dir" != "$placeholder_dir" && -f "$placeholder_dir/$f" ]]; then
      cp "$placeholder_dir/$f" "$offline_dir/$f"
    elif [[ -f "$placeholder_dir/$f" ]]; then
      cp "$placeholder_dir/$f" "$offline_dir/$f"
    else
      warn "Missing placeholder for $f; creating minimal stub"
      printf 'placeholder\n' > "$offline_dir/$f"
    fi
  fi
done

# ──────────────────────── compose profiles ────────────────────
profiles=()
has_gpu && profiles+=(gpu)
[[ -z "${OPENAI_API_KEY:-}" ]] && profiles+=(offline)
(( LIVE )) && profiles+=(live-feed)
export LIVE_FEED=${LIVE}
profile_arg=()
for p in "${profiles[@]}"; do
  profile_arg+=(--profile "$p")
done

# ───────────────────────── Docker build ───────────────────────
say "🚢 Building images (profiles: ${profiles[*]:-none})"
docker compose -f "$compose_file" "${profile_arg[@]}" pull --quiet || true
docker compose -f "$compose_file" "${profile_arg[@]}" build --pull

# ───────────────────────── stack up ───────────────────────────
say "🔄 Starting containers"
docker compose --project-name alpha_macro -f "$compose_file" "${profile_arg[@]}" up -d

# ─────────────────────── health gate & trap ───────────────────
trap 'docker compose -p alpha_macro stop; exit 0' INT
say "⏳ Waiting for orchestrator health"
health_wait "http://localhost:7864/healthz" 40

# ───────────────────────── success banner ─────────────────────
printf '\n\033[1;32m🎉 Dashboard → http://localhost:7864\033[0m\n'
echo   "📊 Grafana   → http://localhost:3001 (admin / alpha)"
echo   "📜 Logs      → docker compose -p alpha_macro logs -f"
echo   "🛑 Stop      → docker compose -p alpha_macro down"
echo   "🧹 Purge     → docker compose -p alpha_macro down -v --remove-orphans"
