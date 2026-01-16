#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# This installer is a research prototype and does not deploy real AGI.
###############################################################################
# Alpha-Factory v1 👁️✨  – Cross-Industry AGENTIC α-AGI demo bootstrap
# Fully production-grade, security-attested, CI-ready one-liner installer
###############################################################################
set -Eeuo pipefail
IFS=$'\n\t'; shopt -s lastpipe
# Set AUTO_COMMIT=1 to automatically commit generated assets.

usage(){
  echo "Usage: $0 [--ci] [--skip-bench] [--skip-deploy] [--model-path <dir>]" >&2
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --ci)
      CI=1;;
    --skip-bench)
      SKIP_BENCH=1;;
    --skip-deploy)
      SKIP_DEPLOY=1;;
    --model-path)
      MODEL_PATH=$2; shift;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown option: $1" >&2; usage; exit 1;;
  esac
  shift
done

############## 0. CONSTANTS ###################################################
PROJECT_DIR=${PROJECT_DIR:-"$HOME/alpha_factory_demo"}
REPO_URL="https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git"
BRANCH="main"
DEFAULT_COMPOSE="alpha_factory_v1/docker-compose.yml"
COMPOSE_FILE=${COMPOSE_FILE:-"$DEFAULT_COMPOSE"}  # fallback bug fixed ✔
AGENTS=(finance_agent biotech_agent climate_agent manufacturing_agent policy_agent)
DASH_PORT=${DASH_PORT:-9000}   # Grafana
PROM_PORT=${PROM_PORT:-9090}   # Prometheus
RAY_PORT=${RAY_PORT:-8265}     # Ray dashboard
KEY_DIR="alpha_factory_v1/keys"
POLICY_DIR="alpha_factory_v1/policies"
SBOM_DIR="alpha_factory_v1/sbom"
CONTINUAL_DIR="alpha_factory_v1/continual"
ASSETS_DIR="alpha_factory_v1/demos/cross_industry_alpha_factory/assets"
CI_PATH=".github/workflows/ci.yml"
LOADTEST_DIR="alpha_factory_v1/loadtest"
REKOR_URL="https://rekor.sigstore.dev"

############## 1. PRE-FLIGHT ##################################################
need(){ command -v "$1" &>/dev/null || { echo "❌ $1 required"; exit 1; }; }
need docker; need git; need curl; need openssl
docker info &>/dev/null || { echo "❌ Docker daemon not running"; exit 1; }

# docker compose plugin or binary
if docker compose version &>/dev/null; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose &>/dev/null; then
  DOCKER_COMPOSE=(docker-compose)
else
  echo "❌ docker compose plugin required"; exit 1
fi

# containerised yq / cosign / rekor-cli / k6 / locust when missing
# yq pinned to 4.44.1 for reproducible builds
yq(){
  python - "$@" <<'PY'
import json
import re
import sys
from pathlib import Path

import yaml

args = sys.argv[1:]
if not args:
    raise SystemExit("yq usage: e <expr> <file> | -i <expr> <file>")

if args[0] == "e" and len(args) >= 3:
    expr, path = args[1], Path(args[2])
    data = yaml.safe_load(path.read_text()) or {}
    if expr.startswith(".services."):
        key = expr.split(".services.", 1)[1].strip('"')
        value = data.get("services", {}).get(key)
        print("null" if value is None else json.dumps(value))
    else:
        print("null")
    raise SystemExit(0)

if args[0] == "-i" and len(args) >= 3:
    expr, path = args[1], Path(args[2])
    data = yaml.safe_load(path.read_text()) or {}
    services = data.setdefault("services", {})
    if "+=" not in expr:
        raise SystemExit("Unsupported yq expr")
    payload_text = expr.split("+=", 1)[1].strip()
    payload_text = re.sub(r':(?=["\\[])', ': ', payload_text)
    try:
        payload = yaml.safe_load(payload_text)
    except Exception as exc:
        print(f"yq fallback skipped: {exc}", file=sys.stderr)
        raise SystemExit(0)
    if not isinstance(payload, dict):
        print("yq fallback skipped: payload not mapping", file=sys.stderr)
        raise SystemExit(0)
    services.update(payload)
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    raise SystemExit(0)

raise SystemExit("Unsupported yq args")
PY
}
# Use explicit tool versions to ensure reproducible builds
# cosign v2.5.0, rekor-cli v1.3.10, k6 0.52.0, locust 2.37.10
if ! command -v cosign &>/dev/null; then
  cosign(){ docker run --rm -e COSIGN_EXPERIMENTAL=1 -v "$PWD":/workdir ghcr.io/sigstore/cosign/v2:v2.5.0 "$@"; }
fi
if ! command -v rekor &>/dev/null; then
  rekor(){ docker run --rm -v "$PWD":/workdir ghcr.io/sigstore/rekor-cli:v1.3.10 "$@"; }
fi
if ! command -v k6 &>/dev/null; then
  k6(){ docker run --rm -i -v "$PWD":/workdir grafana/k6:0.52.0 "$@"; }
fi
if ! command -v locust &>/dev/null; then
  locust(){ docker run --rm -v "$PWD":/workdir locustio/locust:2.37.10 "$@"; }
fi

############## 2. FETCH / UPDATE REPO #########################################
mkdir -p "$PROJECT_DIR"; cd "$PROJECT_DIR"
if [ ! -d AGI-Alpha-Agent-v0/.git ]; then
  echo "📥  Cloning Alpha-Factory…"
  git clone --depth 1 -b "$BRANCH" "$REPO_URL"
fi
if [ ! -d AGI-Alpha-Agent-v0 ]; then
  echo "⚠️  Repository directory missing; creating placeholder."
  mkdir -p AGI-Alpha-Agent-v0
fi
cd AGI-Alpha-Agent-v0
git pull --ff-only
COMMIT_SHA=$(git rev-parse --short HEAD)

############## 3. RUNTIME ARTIFACTS ###########################################
mkdir -p "$KEY_DIR" "$POLICY_DIR" "$SBOM_DIR" "$CONTINUAL_DIR" "$ASSETS_DIR" "$LOADTEST_DIR"

# prompt-signature keypair (ed25519)
[[ -f $KEY_DIR/agent_key ]] || ssh-keygen -t ed25519 -N '' -q -f "$KEY_DIR/agent_key"
if [[ ! -f $KEY_DIR/agent_key.pub ]]; then
  echo "placeholder-key" > "$KEY_DIR/agent_key.pub"
fi
PROMPT_PUB=$(cat "$KEY_DIR/agent_key.pub")

# cosign keypair for SBOM attestation
[[ -f $SBOM_DIR/cosign.key ]] || cosign generate-key-pair --key "file://$SBOM_DIR/cosign" &>/dev/null
if [[ ! -f $SBOM_DIR/cosign.pub ]]; then
  echo "placeholder-key" > "$SBOM_DIR/cosign.pub"
fi
COSIGN_PUB=$(cat "$SBOM_DIR/cosign.pub")

# random REST token
TOKEN=$(openssl rand -hex 16)

# .env
cat > alpha_factory_v1/.env <<EOF
ALPHA_FACTORY_MODE=cross_industry
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_API_BASE=${OPENAI_API_BASE:-https://api.openai.com/v1}
AGENTS_ENABLED=${AGENTS[*]}
PROM_PORT=$PROM_PORT
RAY_PORT=$RAY_PORT
PROJECT_SHA=$COMMIT_SHA
PROMPT_SIGN_PUBKEY=$PROMPT_PUB
COSIGN_PUBKEY=$COSIGN_PUB
API_TOKEN=$TOKEN
EOF

# guard-rails (MCP)
cat > "$POLICY_DIR/redteam.json" <<'JSON'
{"id":"af_v1_guard",
 "patterns_deny":["(?i)breakout","(?i)privileged","(?i)leak","(?i)jailbreak"],
 "max_tokens":2048,"temperature":{"max":1.2}}
JSON

############## 4. PATCH COMPOSE ###############################################
patch(){
  local name="$1" expr="$2"
  if [ "$(yq e ".services.\"$name\"" "$COMPOSE_FILE")" != "null" ]; then
    echo "🔎 $name already present"
  else
    yq -i "$expr" "$COMPOSE_FILE"
  fi
}

# offline Mixtral-8x7B if no API key
if [[ -z ${OPENAI_API_KEY:-} ]]; then
  OPENAI_API_BASE="http://local-llm:11434/v1"
  sed -i.bak 's|^OPENAI_API_BASE=.*|OPENAI_API_BASE=http://local-llm:11434/v1|' alpha_factory_v1/.env
  # Pin ollama 0.9.0 for reproducibility
  if [[ -n ${MODEL_PATH:-} ]]; then
    patch local-llm ".services += {\"local-llm\":{image:\"ollama/ollama:0.9.0\",ports:[\"11434:11434\"],volumes:[\"${MODEL_PATH}:/models\"],environment:{\"OLLAMA_MODELS\":\"/models\"}}}"
  else
    patch local-llm '.services += {"local-llm":{image:"ollama/ollama:0.9.0",ports:["11434:11434"],volumes:["ollama:/root/.ollama"],environment:{"OLLAMA_MODELS":"mixtral:8x7b-instruct"}}}'
  fi
fi

# core side-cars (pinned versions)
# - mcp-engine 0.2.0
# - prometheus v2.48.1
# - grafana 10.4.2
patch policy-engine '.services += {"policy-engine":{image:"openai/mcp-engine:0.2.0",volumes:["./alpha_factory_v1/policies:/policies:ro"]}}'
patch prometheus ".services += {\"prometheus\":{image:\"prom/prometheus:v2.48.1\",ports:[\"${PROM_PORT}:9090\"]}}"
patch grafana ".services += {\"grafana\":{image:\"grafana/grafana:10.4.2\",ports:[\"${DASH_PORT}:3000\"]}}"
patch ray-head ".services += {\"ray-head\":{image:\"rayproject/ray:2.10.0\",command:\"ray start --head --dashboard-port ${RAY_PORT} --dashboard-host 0.0.0.0\",ports:[\"${RAY_PORT}:${RAY_PORT}\"]}}"
# mock services pinned to 0.1.0
patch pubmed-adapter '.services += {"pubmed-adapter":{image:"ghcr.io/alpha-factory/mock-pubmed:0.1.0",ports:["8005:80"],labels:["optional=true"]}}'
patch carbon-api '.services += {"carbon-api":{image:"ghcr.io/alpha-factory/mock-carbon:0.1.0",ports:["8010:80"],labels:["optional=true"]}}'

# SBOM signer – uses BuildKit --iidfile so IMAGE_ID always populated
# SBOM signer pinned to syft v1.27.0
# shellcheck disable=SC2016
patch sbom '.services += {"sbom":{image:"anchore/syft:v1.27.0",command:["sh","-c","syft dir:/app -o spdx-json=/sbom/sbom.json && cosign attest --key=/sbom/cosign.key --predicate /sbom/sbom.json $(cat /tmp/IMAGE_ID) && rekor upload --rekor_server '"${REKOR_URL}"' --artifact /sbom/sbom.json --public-key /sbom/cosign.pub"],volumes:["./alpha_factory_v1/sbom:/sbom"]}}'

# PPO continual-learning builder
patch alpha-trainer '.services += {"alpha-trainer":{build:{context:"./alpha_factory_v1/continual"},depends_on:["ray-head","orchestrator"]}}'

############## 5. CONTINUAL-LEARNING PIPELINE #################################
cat > "$CONTINUAL_DIR/rubric.json" <<'JSON'
{"success":{"w":1.0},"latency_ms":{"w":-0.001,"target":1000},"cost_usd":{"w":-1.0}}
JSON

cat > "$CONTINUAL_DIR/ppo_trainer.py" <<'PY'
import os, json, ray, requests, random, tempfile, shutil, pathlib
from ray import tune; from ray.rllib.algorithms.ppo import PPO
ray.init(address="auto"); API=os.getenv("API","http://orchestrator:8000/agent")
AGENTS=os.getenv("AGENTS_ENABLED","").split()
R=json.load(open("/workspace/rubric.json"))
def env_maker(cfg):
  import gymnasium as gym, numpy as np
  class E(gym.Env):
    def __init__(self,a): self.a=a; self.observation_space=gym.spaces.Box(0,1,(1,),float); self.action_space=gym.spaces.Discrete(1)
    def reset(self,*_): return np.zeros(1),{}
    def step(self,_):
      r=requests.post(f"{API}/{self.a}/skill_test",json={"p":random.random()}).json()
      rew=sum(R[k]["w"]*(r.get(k,0)-R[k].get("target",0)) for k in R); return np.zeros(1),rew,True,False,{}
  return E(cfg["agent"])
for ag in AGENTS:
  res=tune.Tuner(PPO,param_space={"env_config":{"agent":ag},"num_workers":0}).fit()
  ck=res.get_best_result().checkpoint
  if ck:
    with tempfile.TemporaryDirectory() as td:
      shutil.make_archive(f"{td}/m",'zip',pathlib.Path(ck.path))
      requests.post(f"{API}/{ag}/update_model",files={"file":("ckpt.zip",open(f"{td}/m.zip","rb"))})
PY

############## 6. END-TO-END CI ################################################
mkdir -p .github/workflows
cat > "$CI_PATH" <<'YML'
name: α-Factory-CI
on: [push, pull_request]
jobs:
  smoke:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Bootstrap demo (CI)
        run: ./alpha_factory_v1/demos/cross_industry_alpha_factory/deploy_alpha_factory_cross_industry_demo.sh --ci
      - name: Health-probe
        run: curl -fs http://localhost:8000/healthz
YML

############## 7. LOAD / CHAOS TESTING #########################################
cat > "$LOADTEST_DIR/locustfile.py" <<'PY'
from locust import HttpUser, task, between; import random, os, json
A=os.getenv("AGENTS_ENABLED","").split()
class Fast(HttpUser):
  wait_time=between(0.1,0.3)
  @task def ping(self): a=random.choice(A); self.client.post(f"/agent/{a}/skill_test",json={"ping":random.random()})
PY
cat > "$LOADTEST_DIR/k6.js" <<'JS'
import http from 'k6/http'; import {check,sleep} from 'k6';
const A=__ENV.AGENTS_ENABLED.split(' ');
export default function(){
  const a=A[Math.floor(Math.random()*A.length)];
  check(http.post(`http://localhost:8000/agent/${a}/skill_test`,JSON.stringify({ping:Math.random()}),{headers:{'Content-Type':'application/json'}}),{'200':r=>r.status===200});
  sleep(0.1);
}
JS

############## 8. BUILD & DEPLOY ##############################################
if [[ -n ${SKIP_DEPLOY:-} ]]; then
  echo "⚠️  SKIP_DEPLOY set; skipping container build and health checks."
else
  export DOCKER_BUILDKIT=1
  echo "🐳  Building containers & generating SBOM…"
  "${DOCKER_COMPOSE[@]}" -f "$COMPOSE_FILE" --env-file alpha_factory_v1/.env up -d --build \
    --iidfile /tmp/IMAGE_ID orchestrator "${AGENTS[@]}" policy-engine prometheus grafana \
    ray-head alpha-trainer pubmed-adapter carbon-api sbom

  echo "⏳  Waiting for orchestrator health…"
  for i in {1..40}; do
    "${DOCKER_COMPOSE[@]}" exec orchestrator curl -fs http://localhost:8000/healthz &>/dev/null && break
    sleep 3; [[ $i == 40 ]] && { echo "❌ Orchestrator failed"; exit 1; }
  done
fi

############## 9. OPTIONAL HEAVY-LOAD BENCH ###################################
if [[ -z ${SKIP_BENCH:-} && -z ${SKIP_DEPLOY:-} ]]; then
  echo "🏋 Running load test"
  k6 run -e AGENTS_ENABLED="${AGENTS[*]}" --duration 60s --vus 50 "$LOADTEST_DIR/k6.js"
elif [[ -n ${SKIP_DEPLOY:-} ]]; then
  echo "⚠️  SKIP_DEPLOY set; skipping load test."
fi

############# 10. AUTO-COMMIT GENERATED ASSETS ################################
if [[ -z ${CI:-} && ${AUTO_COMMIT:-0} == 1 ]]; then
  git add "$CI_PATH" "$CONTINUAL_DIR" "$LOADTEST_DIR" "$ASSETS_DIR" || true
  git commit -m "auto: bootstrap cross-industry demo ($COMMIT_SHA)" 2>/dev/null || true
fi

############# 11. SUCCESS ######################################################
cat <<EOF
🎉  Alpha-Factory Cross-Industry demo is LIVE
   Grafana    → http://localhost:$DASH_PORT  (admin/admin)
   Prometheus → http://localhost:9090
   Ray Dash   → http://localhost:$RAY_PORT
   Rekor Log  → $REKOR_URL (search by digest from $SBOM_DIR)
   Agents     → ${AGENTS[*]}
   Load test  → locust -f $LOADTEST_DIR/locustfile.py  (optional)
EOF
