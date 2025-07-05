#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

demo_dir="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
root_dir="${demo_dir%/*/*}"                       # → alpha_factory_v1
compose="$demo_dir/docker-compose.muzero.yml"

cd "$root_dir"
if [[ -f ../check_env.py ]]; then
  if ! AUTO_INSTALL_MISSING=1 python ../check_env.py --auto-install; then
    echo "🚨  Environment check failed" >&2
    exit 1
  fi
fi

# Install MuZero specific requirements when AUTO_INSTALL_MISSING is set
verify_muzero_deps() {
  python - <<'EOF'
import importlib, sys
missing = [pkg for pkg in ("torch", "gymnasium", "gradio") if importlib.util.find_spec(pkg) is None]
if missing:
    print("Missing: " + ", ".join(missing))
    sys.exit(1)
EOF
}

if ! verify_muzero_deps; then
  if [[ "${AUTO_INSTALL_MISSING:-0}" == "1" ]]; then
    pip_args=()
    if [[ -n "${WHEELHOUSE:-}" ]]; then
      pip_args+=(--no-index --find-links "$WHEELHOUSE")
    fi
    pip install "${pip_args[@]}" -r "$demo_dir/requirements.txt"
    verify_muzero_deps || { echo "🚨  Missing MuZero dependencies" >&2; exit 1; }
  else
    echo "🚨  Missing MuZero dependencies. Re-run with AUTO_INSTALL_MISSING=1" >&2
    exit 1
  fi
fi

command -v docker >/dev/null 2>&1 || {
  echo "🚨  Docker is required → https://docs.docker.com/get-docker/"; exit 1; }

[[ -f "$demo_dir/config.env" ]] || {
  echo "➕  Creating default config.env (edit to add OPENAI_API_KEY)"; 
  cp "$demo_dir/config.env.sample" "$demo_dir/config.env"; }

echo "🚢  Building & starting MuZero Planning demo …"
HOST_PORT=${HOST_PORT:-7861}

# Warn if the requested port is already in use (best-effort check)
if command -v lsof >/dev/null 2>&1 && lsof -i TCP:"${HOST_PORT}" -s TCP:LISTEN >/dev/null 2>&1; then
  echo "🚨  Port ${HOST_PORT} already in use. Set HOST_PORT to an open port." >&2
  exit 1
fi

docker compose --project-name alpha_muzero -f "$compose" up -d --build

printf '\n🎉  Open http://localhost:%s for the live MuZero dashboard.\n' "$HOST_PORT"
printf '🛑  Stop → docker compose -p alpha_muzero down\n'

# Automatically open the dashboard in a browser when possible
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:${HOST_PORT}" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then  # macOS
  open "http://localhost:${HOST_PORT}" >/dev/null 2>&1 &
fi
