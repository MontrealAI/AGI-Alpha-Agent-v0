#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

# ── flags ────────────────────────────────────────────────────────
NO_CACHE=0
for a in "$@"; do [[ $a == "--no-cache" ]] && NO_CACHE=1; done

# ── prerequisites ───────────────────────────────────────────────
need(){ command -v "$1" &>/dev/null || { echo "$1 required"; exit 1; }; }
for c in docker git curl unzip; do need "$c"; done
SCAN=$(command -v ss || command -v lsof) || { echo "ss or lsof required"; exit 1; }
docker compose version &>/dev/null || { echo "Docker Compose v2 required"; exit 1; }

# ── repo checkout / fallback ────────────────────────────────────
URL=https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
DIR=alpha_factory_v1
[[ -d $DIR ]] || { echo "Cloning α‑Factory…";
  git clone --depth=1 "$URL" "$DIR" || {
    curl -sL "$URL/archive/refs/heads/main.zip" -o repo.zip
    unzip -q repo.zip && rm repo.zip
    mv AGI-Alpha-Agent-v0-main "$DIR"; }; }
cd "$DIR"

# ── free‑port helper ────────────────────────────────────────────
free_port(){ for p in $(seq "$1" "$2"); do
  ([[ $SCAN == *ss ]] && ss -ltn | grep -q ":$p ") ||
  ([[ $SCAN == *lsof ]] && lsof -i :"$p" -sTCP:LISTEN &>/dev/null) && continue
  echo "$p"; return; done; echo 0; }

BACKEND_PORT=$(free_port 8080 8090)
PROXY_PORT=$(free_port 7000 7009)
MESH_PORT=$(free_port 7010 7019)
UI_PORT=$(free_port 3000 3009)
for v in BACKEND_PORT PROXY_PORT MESH_PORT UI_PORT; do [[ ${!v} -eq 0 ]] && { echo "Port scan failed for $v"; exit 1; }; done
echo "ℹ️  Ports — backend:${BACKEND_PORT} proxy:${PROXY_PORT} mesh:${MESH_PORT} UI:${UI_PORT}"

# ── scaffold services if missing ────────────────────────────────
mk_service(){ dir=$1 entry=$2 port=$3
  mkdir -p "$dir"/{static,tests}
  [[ -f $dir/$entry ]] || cat >"$dir/$entry" <<'PY'
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import pathlib, uvicorn, os, sys
BASE = pathlib.Path(__file__).parent
app  = FastAPI()

@app.get("/", include_in_schema=False)
async def health():
    idx = BASE/"static"/"index.html"
    return FileResponse(idx) if idx.exists() else JSONResponse({"status":"ok"})

if __name__ == "__main__":
    uvicorn.run(f"{pathlib.Path(__file__).stem}:app",
                host="0.0.0.0",
                port=int(os.getenv("PORT", sys.argv[1] if len(sys.argv)>1 else 3000)))
PY
  [[ -f $dir/static/index.html ]] || echo "<h1>${dir} ✔</h1>" >"$dir"/static/index.html
  if [[ $dir == backend ]]; then
    [[ -f $dir/tests/test_health.py ]] || cat >"$dir"/tests/test_health.py <<'PY'
import os, requests
def test_health():
    port=os.getenv("PORT","8080")
    assert requests.get(f"http://localhost:{port}/").status_code==200
PY
  fi
  [[ -f $dir/Dockerfile ]] || cat >"$dir"/Dockerfile <<EOF
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic numpy pandas pytest requests
HEALTHCHECK CMD curl -f http://localhost:${port}/ || exit 1
ENV PORT=${port}
EXPOSE ${port}
CMD ["python","${entry}","${port}"]
EOF
}
mk_service backend              orchestrator.py "${BACKEND_PORT}"
mk_service infra/agentsdk_proxy proxy.py        "${PROXY_PORT}"
mk_service infra/adk_mesh       mesh.py         "${MESH_PORT}"
mk_service ui                   server.py       3000   # UI stays on 3000 inside container

# ── .env prompt ─────────────────────────────────────────────────
echo -e "\n### α‑Factory quick‑config ###"
read -rp "OpenAI API key (ENTER to skip): " OPENAI
echo "OPENAI_API_KEY=${OPENAI}" > .env

# ── docker‑compose.yml ─────────────────────────────────────────
cat > docker-compose.yaml <<YML
services:
  orchestrator:
    build: { context: ./backend }
    env_file: .env
    ports: ["${BACKEND_PORT}:${BACKEND_PORT}"]
  agentsdk_proxy:
    build: { context: ./infra/agentsdk_proxy }
    env_file: .env
    ports: ["${PROXY_PORT}:${PROXY_PORT}"]
  adk_mesh:
    build: { context: ./infra/adk_mesh }
    env_file: .env
    ports: ["${MESH_PORT}:${MESH_PORT}"]
  ui:
    build: { context: ./ui }
    env_file: .env
    ports: ["${UI_PORT}:3000"]
  ollama_fallback:
    image: ollama/ollama:latest
    environment: ["OLLAMA_MODEL=phi3"]
    profiles: ["noapi"]
YML

PROJECT=alpha_factory

# ── build & up ──────────────────────────────────────────────────
echo -e "\n🔨  Building images …"
docker compose -p "$PROJECT" build "$( [[ $NO_CACHE -eq 1 ]] && echo "--no-cache" )"
echo -e "\n🚀  Launching stack …"
docker compose -p $PROJECT up -d

cat <<TXT

✅  Backend : http://localhost:${BACKEND_PORT}
✅  UI      : http://localhost:${UI_PORT}

Logs : docker compose -p ${PROJECT} logs -f orchestrator ui
Tests: docker compose -p ${PROJECT} exec orchestrator pytest -q /app/tests

TXT
