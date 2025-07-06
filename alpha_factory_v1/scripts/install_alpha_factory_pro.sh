#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# install_alpha_factory_pro.sh  —  one‑stop builder *and* optional deployer
# ─────────────────────────────────────────────────────────────────────────
#   Original flags (still supported)
#     --all  --ui  --trace  --tests  --no-ui  --no-cache  -h|--help
#
#   Extra production flags (added, fully backward‑compatible)
#     --deploy       build + docker‑compose up + smoke tests
#     --bootstrap    clone repo if alpha_factory_v1/ is absent
#     --alpha NAME   pre‑enable a strategy in config/alpha_factory.yml
#     --open         launch default browser after deploy
#
#   Examples
#     ./install_alpha_factory_pro.sh --all --deploy           # full stack
#     ./install_alpha_factory_pro.sh --no-ui                  # image only
#     ./install_alpha_factory_pro.sh --bootstrap --deploy \
#           --alpha btc_gld --open                            # live alpha
# -----------------------------------------------------------------------
set -euo pipefail

VER="v1.3.3"
REPO="MontrealAI/AGI-Alpha-Agent-v0"
BRANCH="main"
PROFILE="${PROFILE:-full}"
IMAGE_TAG="alphafactory_pro:latest"
ALPHA_TOGGLE=""

# ─── defaults (original behaviour) ──────────────────────────────────────
tty=${CI:-}; want_ui=${tty:-1}; want_trace=0; want_tests=0; want_open=0
nocache_arg=""; do_deploy=0; do_bootstrap=0

open_url(){
  url="$1"
  if command -v xdg-open >/dev/null; then
    xdg-open "$url" >/dev/null 2>&1 &
  elif command -v open >/dev/null; then
    open "$url" >/dev/null 2>&1 &
  elif command -v start >/dev/null; then
    start "$url"
  else
    echo "→ open $url"
  fi
}

usage() { grep -E '^#( |$)' "$0" | sed 's/^# ?//' ; exit 0; }

fail(){
  echo "❌ Error on line $1" >&2
  exit 1
}
trap 'fail $LINENO' ERR

# ─── CLI parsing (keeps original flags) ─────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --all)        want_ui=1; want_trace=1; want_tests=1 ;;
    --ui)         want_ui=1 ;;
    --trace)      want_trace=1 ;;
    --tests)      want_tests=1 ;;
    --no-ui)      want_ui=0 ;;
    --no-cache)   nocache_arg="--no-cache" ;;
    --deploy)     do_deploy=1 ;;
    --open)       want_open=1 ;;
    --bootstrap)  do_bootstrap=1 ;;
    --alpha)      ALPHA_TOGGLE="$2"; shift ;;
    -h|--help)    usage ;;
    *)            echo "Unknown flag: $1" >&2; exit 1 ;;
  esac; shift
done

echo "╭──────── Alpha‑Factory $VER ────────"
printf "│ UI:%s Trace:%s Tests:%s Deploy:%s Alpha:%s\n" \
       "$([[ $want_ui == 1 ]] && echo ON || echo off)" \
       "$([[ $want_trace == 1 ]] && echo ON || echo off)" \
       "$([[ $want_tests == 1 ]] && echo ON || echo off)" \
       "$([[ $do_deploy == 1 ]] && echo YES || echo no)" \
       "${ALPHA_TOGGLE:-none}"
echo "╰────────────────────────────────────"

command -v docker        >/dev/null || { echo "❌ docker not found"; exit 1; }
command -v docker compose>/dev/null || { echo "❌ docker compose missing"; exit 1; }

# ─── bootstrap clone (opt‑in) ──────────────────────────────────────────
if [[ $do_bootstrap == 1 && ! -d alpha_factory_v1 ]]; then
  echo "→ cloning source tree…"
  git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" factory_tmp
  mv factory_tmp/alpha_factory_v1 . && rm -rf factory_tmp
fi

cd alpha_factory_v1 2>/dev/null ||:

# ─── build‑only path (original behaviour) ──────────────────────────────
if [[ $do_deploy == 0 ]]; then
  build_args=(
    --build-arg "ENABLE_UI=$want_ui"
    --build-arg "ENABLE_TRACE=$want_trace"
    --build-arg "INCLUDE_TESTS=$want_tests"
  )
  [[ -n $nocache_arg ]] && build_args+=("$nocache_arg")

  docker build "${build_args[@]}" -t "$IMAGE_TAG" .
  echo "✅ Image built: $IMAGE_TAG"
  echo "   Run it with:"
  echo "     docker run --rm -p 33000:3000 $IMAGE_TAG"
  exit 0
fi

# ─── deploy path ───────────────────────────────────────────────────────
echo "🚀  Deploying full stack (profile: $PROFILE)"

# 1. hot‑fix outdated test import (until upstream PR merged)
PATCH_SIG=".patched_ci_v${VER}"
if [[ ! -f $PATCH_SIG ]]; then
  sed -i 's/risk\.ACCOUNT_EQUITY/portfolio.equity/' tests/test_finance_agent.py || true
  touch "$PATCH_SIG"
fi

# 2. generate .env if missing
if [[ ! -f .env ]]; then
  echo "→ creating .env (edit credentials later)"
  cp .env.sample .env
  chmod 600 .env
fi

# 3. local model fallback
if grep -q '^OPENAI_API_KEY=$' .env || ! grep -q '^OPENAI_API_KEY=' .env; then
  echo "→ no OpenAI key detected; pulling ollama/phi‑2"
  docker pull ollama/phi-2:latest
  grep -q '^LLM_PROVIDER=' .env || echo "LLM_PROVIDER=ollama" >> .env
fi

# 4. auto‑enable strategy toggle (requires yq, fallback to sed)
if [[ -n $ALPHA_TOGGLE ]]; then
  if command -v yq >/dev/null; then
    yq -i ".finance.strategy = \"$ALPHA_TOGGLE\"" config/alpha_factory.yml
  else
    echo "Warning: yq not found; falling back to sed"
    sed -i "s/^strategy: .*$/strategy: $ALPHA_TOGGLE/" config/alpha_factory.yml
  fi
fi

# 5. build & start stack
docker compose --profile "$PROFILE" build
docker compose --profile "$PROFILE" up -d

# 6. smoke tests
docker compose exec orchestrator pytest -q /app/tests

echo "✅  α‑Factory healthy — open http://localhost:8088"
[[ $want_open == 1 ]] && open_url "http://localhost:8088"
