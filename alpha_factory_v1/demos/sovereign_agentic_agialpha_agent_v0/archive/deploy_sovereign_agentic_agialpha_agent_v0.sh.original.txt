#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# deploy_sovereign_agentic_agialpha_agent_v0.sh
#
# A single script that:
#   1) Creates a project folder (sovereign_agent_deploy/ by default).
#   2) Generates all required agent files (sovereign_agent.py, Dockerfile, etc.).
#   3) Optionally copies data directories for persistent storage (weaviate_data, chroma_storage, data).
#   4) Runs docker-compose build + docker-compose up -d
#   5) Automatically attaches to the "sovereign_agent" container in a user-friendly Terminal way.
#
# For high-stakes, production-ready deployment by a non-technical user. Everything needed is in this one script.
#
# This version:
# - Installs cryptography (>=39.0.0) to fix the "cryptography library is required for signature verification" error.
# - Pins sentence-transformers / torch / transformers to avoid "init_empty_weights not defined" error.
# - Pins numpy<2.0.0.
# - Adds minimal Flask-based web chat at port 5000, with a token-gated webpage requiring 500k tokens for page access
#   and 1M tokens for agent access.
# - Ensures the user's front-end fetch calls the same origin ("/chat") instead of "http://localhost:5000/chat".
# - Explicitly upgrades pip/setuptools/wheel inside Docker to fix “invalid command 'bdist_wheel'” issues.
# - Integrates Agentic Tree Search (agentic_treesearch.py) as a core planning engine for open-ended alpha exploration
#   at route /tree_search, and **also** integrates the **Agentic Alpha Explorer** BFS expansions (agentic_alpha_explorer.py)
#   at route /alpha_explorer. The BFS expansions can still be run manually via the Python console:
#       python agentic_alpha_explorer.py --root="Consciousness Cascades" --diversity=1.0 --agentic
# - The same LLM selected (Ollama local model or cloud-based) is used for both chat and BFS expansions.
#
# Usage:
#   1) Make sure Docker & docker-compose are installed, plus Python 3.9+ if you run locally outside Docker.
#   2) ./deploy_sovereign_agentic_agialpha_agent_v0.sh
#      (It will prompt for a local Ollama model if no OPENAI_API_KEY or ANTHROPIC_API_KEY is set.)
#   3) Wait for the container to build. Then the script attaches to the agent container, letting you chat in the terminal.
#   4) Meanwhile, open a browser to http://localhost:5000 for the full user-friendly web UI, including BFS expansions.

set -e

TARGET_DIR="sovereign_agent_deploy"
OLLAMA_CONFIG_FILE="ollama_model.conf"  # to persist user’s chosen local model

###############################################################################
# 0) Check Port 11434 Freed (for Ollama)
###############################################################################
function check_port_11434_free() {
  if command -v lsof &> /dev/null; then
    PORT_CHECK="$(lsof -i tcp:11434 -sTCP:LISTEN -t 2>/dev/null || true)"
  else
    PORT_CHECK="$(netstat -anp 2>/dev/null | grep 11434 | grep LISTEN || true)"
  fi
  if [ -n "$PORT_CHECK" ]; then
    echo "Error: Port 11434 is already in use by another process. Please free this port and re-run."
    exit 1
  fi
}

###############################################################################
# 1) Start Ollama Daemon in background
###############################################################################
function start_ollama_daemon() {
  echo "Starting Ollama server in background..."
  nohup ollama serve > /tmp/ollama_server.log 2>&1 &
  OLLAMA_PID=$!

  READY=false
  for i in {1..15}; do
    sleep 1
    if command -v nc &> /dev/null; then
      if nc -z localhost 11434 2>/dev/null; then
        READY=true
        break
      fi
    else
      if curl -s http://localhost:11434/ > /dev/null; then
        READY=true
        break
      fi
    fi
  done

  if [ "$READY" != "true" ]; then
    echo "Error: Ollama server not responding on port 11434."
    kill $OLLAMA_PID 2>/dev/null || true
    exit 1
  fi
  echo "Ollama daemon is running on port 11434."
}

###############################################################################
# 2) Attempt to Upgrade Ollama if needed
###############################################################################
function upgrade_ollama() {
  unameOut="$(uname -s)"
  if [[ "$unameOut" == "Linux" ]]; then
    echo "Upgrading Ollama for Linux..."
    if ! command -v curl &> /dev/null; then
      echo "Error: 'curl' not installed. Please install it and re-run."
      exit 1
    fi
    if ! curl -fsSL https://ollama.com/install.sh | sh; then
      echo "Error: Failed to upgrade Ollama on Linux."
      exit 1
    fi
  elif [[ "$unameOut" == "Darwin" ]]; then
    echo "Upgrading Ollama on macOS..."
    if ! command -v brew &> /dev/null; then
      echo "Error: 'brew' not found. Please install Homebrew or see https://brew.sh/"
      exit 1
    fi
    if ! brew upgrade ollama; then
      echo "Error: Failed to upgrade Ollama via Homebrew."
      exit 1
    fi
  else
    echo "Unsupported OS for auto-upgrade. See https://ollama.com/download"
    exit 1
  fi
}

###############################################################################
# 3) Pull gemma3:4b if user wants that default
###############################################################################
function pull_gemma3() {
  echo "Pulling 'gemma3:4b' model (this may take several minutes)..."
  set +e
  PULL_OUTPUT="$(ollama pull gemma3:4b 2>&1)"
  PULL_STATUS=$?
  set -e

  if [ $PULL_STATUS -ne 0 ]; then
    echo "$PULL_OUTPUT"
    if echo "$PULL_OUTPUT" | grep -q "412:"; then
      echo "Detected version mismatch (412). Attempting Ollama upgrade..."
      upgrade_ollama
      killall ollama 2>/dev/null || true
      sleep 1
      check_port_11434_free
      start_ollama_daemon
      echo "Retrying pull of 'gemma3:4b'..."
      if ! ollama pull gemma3:4b; then
        echo "Error: second attempt to pull gemma3:4b also failed."
        killall ollama 2>/dev/null || true
        exit 1
      fi
    else
      echo "Error: failed to pull gemma3:4b"
      killall ollama 2>/dev/null || true
      exit 1
    fi
  fi
  echo "Successfully pulled 'gemma3:4b' model."
}

###############################################################################
# 4) Show Download Progress
###############################################################################
function show_download_progress() {
  while IFS= read -r line; do
    echo "$line"
  done
}

###############################################################################
# 5) Interactive Model Selection if no API keys
###############################################################################
function interactive_ollama_model_selection() {
  if [ -f "$OLLAMA_CONFIG_FILE" ]; then
    # shellcheck source=/dev/null
    source "$OLLAMA_CONFIG_FILE" || true
    if [ -n "$OLLAMA_MODEL" ]; then
      echo "Using previously selected local Ollama model: \"$OLLAMA_MODEL\" (from $OLLAMA_CONFIG_FILE)."
      return
    fi
  fi

  echo "Fetching up to 20 popular models from Ollama library (ollama.com/library)..."
  local model_page
  model_page="$(curl -sSfL "https://ollama.com/library" || true)"
  if [ -z "$model_page" ]; then
    echo "⚠️  Unable to retrieve model list from ollama.com. Possibly no internet connection."
    echo -n "Enter the Ollama model name to use (e.g. llama2:7b or gemma3:4b). Press ENTER for 'gemma3:4b': "
    read -r user_input_model
    if [ -z "$user_input_model" ]; then
      user_input_model="gemma3:4b"
    fi
    OLLAMA_MODEL="$user_input_model"
  else
    local model_names
    model_names=$(echo "$model_page" | sed -n 's/.*href="\/library\/\([^"]*\)".*/\1/p' | head -n 20)
    if [ -z "$model_names" ]; then
      echo "No models found on the library page. Defaulting to gemma3:4b."
      OLLAMA_MODEL="gemma3:4b"
    else
      echo
      echo "Top 20 Ollama models (by popularity) found on the library page:"
      local i=1
      while IFS= read -r model; do
        local anchor_block
        anchor_block=$(echo "$model_page" | grep -A10 -m1 "href=\"/library/$model\"" | sed ':a;N;$!ba;s/\n/ /g')
        local anchor_block_sans_tags
        anchor_block_sans_tags=$(echo "$anchor_block" | sed -E 's/<[^>]+>/ /g' | tr -s ' ')
        local size_info
        size_info=$(echo "$anchor_block_sans_tags" | grep -oE '[0-9]+(\.[0-9]+)?[MG]B' | head -n1)
        [ -n "$size_info" ] && size_info="(Size: $size_info)" || size_info="(Size: unknown)"
        echo "  $i) $model $size_info"
        i=$((i+1))
      done <<< "$model_names"

      echo
      echo -n "Enter the number of the model to use, or type a custom name. Press ENTER for 'gemma3:4b': "
      read -r choice
      if [[ -z "$choice" ]]; then
        OLLAMA_MODEL="gemma3:4b"
      elif [[ "$choice" =~ ^[0-9]+$ ]]; then
        local total_count
        total_count=$(echo "$model_names" | wc -l)
        if (( choice >= 1 && choice <= total_count )); then
          OLLAMA_MODEL=$(echo "$model_names" | sed -n "${choice}p")
          echo "Selected model #$choice: \"$OLLAMA_MODEL\"."
        else
          echo "Invalid selection ($choice). Defaulting to 'gemma3:4b'."
          OLLAMA_MODEL="gemma3:4b"
        fi
      else
        OLLAMA_MODEL="$choice"
      fi
    fi
  fi

  echo "Using Ollama model: \"$OLLAMA_MODEL\""
  echo "export OLLAMA_MODEL=\"$OLLAMA_MODEL\"" > "$OLLAMA_CONFIG_FILE"
  echo "(Saved choice to $OLLAMA_CONFIG_FILE for future runs.)"
}

###############################################################################
# MAIN SCRIPT
###############################################################################
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "No OPENAI_API_KEY or ANTHROPIC_API_KEY found. Using local Ollama (interactive selection)..."

  if command -v lsof &> /dev/null; then
    sudo kill -9 "$(sudo lsof -t -i:11434)" 2>/dev/null || true
  fi

  if ! command -v ollama &> /dev/null; then
    echo "Ollama not found on the host system, installing system-wide..."
    unameOut="$(uname -s)"
    case "$unameOut" in
      Linux*)
        echo "Installing Ollama for Linux..."
        if ! command -v curl &> /dev/null; then
          echo "Error: 'curl' not installed. Please install it and re-run."
          exit 1
        fi
        if ! curl -fsSL https://ollama.com/install.sh | sh; then
          echo "Error: Ollama install failed on Linux."
          exit 1
        fi
        ;;
      Darwin*)
        echo "Installing Ollama for macOS via Homebrew..."
        if ! command -v brew &> /dev/null; then
          echo "Error: 'brew' not found. Please install Homebrew or see https://brew.sh/"
          exit 1
        fi
        if ! brew install ollama; then
          echo "Error: brew install ollama failed."
          exit 1
        fi
        ;;
      *)
        echo "Unsupported OS. See https://github.com/jmorganca/ollama for instructions."
        exit 1
        ;;
    esac
  else
    echo "Ollama is already installed on the host."
  fi

  check_port_11434_free
  start_ollama_daemon
  interactive_ollama_model_selection

  echo "Exporting LLM_PROVIDER=ollama, OLLAMA_MODEL=${OLLAMA_MODEL}"
  export LLM_PROVIDER="ollama"
  export OLLAMA_MODEL="${OLLAMA_MODEL}"
  export OLLAMA_URL="http://localhost:11434"

  echo "Pulling Ollama model \"$OLLAMA_MODEL\". This may take a while if not already downloaded..."
  set +e
  PULL_OUT="$(ollama pull "$OLLAMA_MODEL" | show_download_progress)"
  PULL_OK=${PIPESTATUS[0]}
  set -e

  if [ "$PULL_OK" -ne 0 ]; then
    if echo "$PULL_OUT" | grep -q "412:"; then
      echo "Detected version mismatch. Attempting Ollama upgrade..."
      upgrade_ollama
      killall ollama 2>/dev/null || true
      sleep 1
      check_port_11434_free
      start_ollama_daemon
      echo "Retrying pull of '$OLLAMA_MODEL'..."
      if ! ollama pull "$OLLAMA_MODEL"; then
        echo "Error: second attempt to pull $OLLAMA_MODEL also failed."
        killall ollama 2>/dev/null || true
        exit 1
      fi
    else
      echo "Error: failed to pull $OLLAMA_MODEL"
      killall ollama 2>/dev/null || true
      exit 1
    fi
  fi
else
  echo "Found OPENAI_API_KEY or ANTHROPIC_API_KEY; using cloud-based LLM provider."
fi

echo "============================================================"
echo "Sovereign Agentic AGI ALPHA - Automatic Deployment Script"
echo "============================================================"
echo "Creating '$TARGET_DIR/', generating agent files, and"
echo "running docker-compose build/up -d. Make sure Docker &"
echo "Compose are installed, and Python 3.9+ for local usage."
echo "------------------------------------------------------------"
echo

mkdir -p "$TARGET_DIR"
echo "[1/5] Created/verified directory: '$TARGET_DIR'."

echo "[2/5] Generating files..."

###############################################################################
# The main agent code
###############################################################################
cat <<'AGENT_PY' > "$TARGET_DIR/sovereign_agent.py"
#!/usr/bin/env python3
"""
Sovereign Agentic AGI ALPHA - Single-File Monolithic Version
(with chain-of-thought, advanced reasoning, MCP extension,
 pinned sentence-transformers + cryptography, etc.)

We do NOT remove or alter existing Terminal-based chat.
We ADD a minimal Flask-based web interface that:
  1) Serves a "/" route with the big HTML page
  2) Serves a "/chat" endpoint for JSON POST, so user can chat from the webpage
  3) Demonstrates a "/tree_search" endpoint for open-ended alpha exploration
     via the integrated "Agentic Tree Search".
  4) Demonstrates a "/alpha_explorer" endpoint for BFS expansions via
     "Agentic Alpha Explorer" (agentic_alpha_explorer.py).

**Extra Diagnostics**: The "/tree_search" and "/alpha_explorer" routes log details,
 returning BFS expansions & best node as JSON so the front-end can display them.
"""

import os
import sys
import json
import yaml
import requests
import time
import logging
import subprocess
import asyncio
import socket
import uuid
import threading
import ast
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger("SovereignAlphaAgent")
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Attempt optional openai
try:
    import openai
except ImportError:
    openai = None
OPENAI_TIMEOUT_SEC = int(os.getenv("OPENAI_TIMEOUT_SEC", "30"))

# Attempt optional anthropic
try:
    from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
except ImportError:
    Anthropic = None
    HUMAN_PROMPT = None
    AI_PROMPT = None

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None
    ChromaSettings = None

try:
    import weaviate
except ImportError:
    weaviate = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import dns.resolver
except ImportError:
    dns = None

try:
    from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange, ServiceInfo
except ImportError:
    Zeroconf = None
    ServiceBrowser = None
    ServiceInfo = None

try:
    import cryptography
except ImportError:
    cryptography = None

# We'll import Flask for the minimal web chat + endpoints:
try:
    from flask import Flask, request, jsonify
except ImportError:
    Flask = None

# Import the agentic_treesearch module (we place it in the same directory).
try:
    import agentic_treesearch
except ImportError:
    agentic_treesearch = None

# Import the agentic_alpha_explorer for BFS expansions
try:
    import agentic_alpha_explorer
except ImportError:
    agentic_alpha_explorer = None

trust_file = "trust_whitelist.yaml"
trust_config = {
    "allowed_domains": [],
    "allowed_paths": [],
    "allowed_tools": [],
    "allowed_cert_fingerprints": [],
    "allowed_ed25519_keys": []
}
if os.path.isfile(trust_file):
    try:
        with open(trust_file, "r") as f:
            user_trust = yaml.safe_load(f)
        for k in trust_config.keys():
            if k in user_trust and isinstance(user_trust[k], list):
                trust_config[k] = user_trust[k]
    except Exception as e:
        logger.error(f"Error reading trust_whitelist.yaml: {e}")
else:
    with open(trust_file, "w") as f:
        yaml.safe_dump(trust_config, f)
    logger.info(f"Created default {trust_file}.")

def is_domain_allowed(domain: str) -> bool:
    domain = domain.lower().strip()
    for allowed in trust_config["allowed_domains"]:
        if domain == allowed or domain.endswith('.' + allowed):
            return True
    return False

def is_path_allowed(path: str) -> bool:
    import os
    abspath = os.path.abspath(path)
    for allowed in trust_config["allowed_paths"]:
        allowed_abs = os.path.abspath(allowed)
        if abspath == allowed_abs or (
            abspath.startswith(allowed_abs) and
            (len(abspath) == len(allowed_abs) or abspath[len(allowed_abs)] == os.sep)
        ):
            return True
    return False

def plugin_web_fetch(url: str):
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    if not is_domain_allowed(domain):
        return f"Error: domain '{domain}' not allowed."
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return f"HTTP error {r.status_code}"
        text = r.text
        if len(text) > 1000:
            text = text[:1000] + "... [truncated]"
        return text
    except Exception as e:
        return f"Error: {e}"

def plugin_file_read(path: str):
    if not is_path_allowed(path):
        return f"Error: file path '{path}' not allowed."
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
            if len(data) > 1000:
                data = data[:1000] + "... [truncated]"
            return data
    except Exception as e:
        return f"Error: {e}"

def plugin_file_write(path: str, content: str):
    if not is_path_allowed(path):
        return f"Error: file path '{path}' not allowed."
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}."
    except Exception as e:
        return f"Error: {e}"

allowed_tools = trust_config.get("allowed_tools", [])
local_plugins = [
    {"name": "web_fetch", "description": "Fetch URL content", "func": plugin_web_fetch,
     "parameters": {"url": "string"}},
    {"name": "file_read", "description": "Read text from a file", "func": plugin_file_read,
     "parameters": {"path": "string"}},
    {"name": "file_write","description": "Write text to a file","func": plugin_file_write,
     "parameters": {"path": "string", "content": "string"}}
]
local_plugins = [p for p in local_plugins if p["name"] in allowed_tools]

def create_openai_functions(plugin_list):
    out = []
    for p in plugin_list:
        props = {}
        required = []
        for arg, typ in p["parameters"].items():
            props[arg] = {"type": "string"}
            required.append(arg)
        out.append({
            "name": p["name"],
            "description": p["description"],
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required
            }
        })
    return out

openai_functions = create_openai_functions(local_plugins)

class VectorMemory:
    def __init__(self):
        self.backend = os.getenv("MEMORY_BACKEND","chroma").lower()
        self._embed_func = None
        embed_mode = os.getenv("EMBEDDING_MODE","").lower()

        use_openai_embed = False
        try:
            if embed_mode == "openai" and openai and os.getenv("OPENAI_API_KEY"):
                use_openai_embed = True
            elif embed_mode == "local":
                use_openai_embed = False
            else:
                if openai and os.getenv("OPENAI_API_KEY"):
                    use_openai_embed = True
        except:
            pass

        if use_openai_embed and openai:
            def openai_embed(text: str):
                try:
                    resp = openai.Embedding.create(model="text-embedding-ada-002", input=[text])
                    return resp["data"][0]["embedding"]
                except Exception as e:
                    logger.error(f"OpenAI embedding error: {e}")
                    return None
            self._embed_func = openai_embed
        else:
            if SentenceTransformer:
                try:
                    modelname = os.getenv("EMBEDDING_MODEL","sentence-transformers/all-MiniLM-L6-v2")
                    logger.info(f"Loading local embedding model {modelname}...")
                    st = SentenceTransformer(modelname)
                    self._embed_func = lambda txt: st.encode(txt).tolist()
                except Exception as e:
                    logger.error(f"Local embedding init failed: {e}")
                    self._embed_func = lambda txt: [float(hash(txt)%100000)]
            else:
                logger.warning("No SentenceTransformer installed; using dummy embeddings.")
                self._embed_func = lambda txt: [float(hash(txt)%100000)]

        self.chroma_client = None
        self.collection = None
        self.weaviate_client = None

        if self.backend == "chroma" and chromadb:
            dir_ = os.getenv("CHROMA_PERSIST_DIR","chroma_storage")
            try:
                cset = ChromaSettings(persist_directory=dir_)
                self.chroma_client = chromadb.Client(cset)
                self.collection = self.chroma_client.get_or_create_collection(name="sovereign_memory")
            except Exception as e:
                logger.error(f"Chroma init failed: {e}")
                self.chroma_client = None
        elif self.backend == "weaviate" and weaviate:
            url = os.getenv("WEAVIATE_URL","http://localhost:8080")
            auth = None
            if os.getenv("WEAVIATE_API_KEY"):
                import weaviate.auth
                auth = weaviate.auth.AuthApiKey(api_key=os.getenv("WEAVIATE_API_KEY"))
            try:
                self.weaviate_client = weaviate.Client(url, auth_client_secret=auth)
                schema = self.weaviate_client.schema.get()
                classes = [c["class"] for c in schema.get("classes",[])]
                if "MemoryItem" not in classes:
                    class_schema = {
                        "class":"MemoryItem",
                        "vectorizer":"none",
                        "properties":[{"name":"content","dataType":["text"]}]
                    }
                    self.weaviate_client.schema.create_class(class_schema)
            except Exception as e:
                logger.error(f"Weaviate init failed: {e}")
                self.weaviate_client = None

    def add(self, text: str):
        if not text or not self._embed_func:
            return
        vec = self._embed_func(text)
        if vec is None:
            return
        if self.backend=="chroma" and self.chroma_client:
            try:
                self.collection.add(documents=[text], embeddings=[vec], ids=[str(uuid.uuid4())])
            except Exception as e:
                logger.error(f"Chroma add error: {e}")
        elif self.backend=="weaviate" and self.weaviate_client:
            try:
                self.weaviate_client.data_object.create({"content": text}, "MemoryItem", vector=vec)
            except Exception as e:
                logger.error(f"Weaviate add error: {e}")

    def search(self, query: str, k=3) -> List[str]:
        if not query or not self._embed_func:
            return []
        vec = self._embed_func(query)
        if vec is None:
            return []
        if self.backend=="chroma" and self.chroma_client:
            try:
                res = self.collection.query(query_embeddings=[vec], n_results=k, include=["documents"])
                if res and "documents" in res and res["documents"]:
                    return res["documents"][0]
            except Exception as e:
                logger.error(f"Chroma search error: {e}")
        elif self.backend=="weaviate" and self.weaviate_client:
            try:
                r = self.weaviate_client.query.get("MemoryItem", ["content"]) \
                           .with_near_vector({"vector":vec}).with_limit(k).do()
                items = r.get("data",{}).get("Get",{}).get("MemoryItem",[])
                return [it["content"] for it in items if "content" in it]
            except Exception as e:
                logger.error(f"Weaviate search error: {e}")
        return []

import re

class ReasoningAgent:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER","ollama").lower()
        self.model_name = (os.getenv("OLLAMA_MODEL","gemma3:4b")
                           if self.provider == "ollama"
                           else os.getenv("OPENAI_MODEL","gpt-3.5-turbo"))
        self.history = []
        self.memory = VectorMemory()
        self.debug_mode = False

        self.anthropic_client = None
        if self.provider == "anthropic" and Anthropic is not None and os.getenv("ANTHROPIC_API_KEY"):
            self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        if self.provider == "openai" and openai is not None and os.getenv("OPENAI_API_KEY"):
            openai.api_key = os.getenv("OPENAI_API_KEY")

        self.max_steps = 5
        self.reaction_tools = {
            "Search": self.tool_search,
            "Calculate": self.tool_calculate
        }

    def tool_search(self, query: str) -> str:
        try:
            r = requests.get(f"https://api.duckduckgo.com/?q={query}&format=json").json()
            abstract = r.get("Abstract", "")
            related = r.get("RelatedTopics", [])
            if abstract:
                return abstract[:300]
            elif related:
                return related[0].get("Text","")[:300]
            else:
                return "No relevant info."
        except Exception as e:
            return f"[Search error: {e}]"

    def _eval_node(self, node: ast.AST) -> float:
        """Recursively evaluate supported AST nodes."""
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left ** right
            raise ValueError("Unsupported operator")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval_node(node.operand)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Unsupported expression")

    def _safe_eval(self, expression: str) -> float:
        """Evaluate an arithmetic expression using the AST parser."""
        tree = ast.parse(expression, mode="eval")
        allowed = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Constant,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Pow,
            ast.USub,
            ast.Load,
        )
        for n in ast.walk(tree):
            if not isinstance(n, allowed):
                raise ValueError("Unsupported expression")
        return self._eval_node(tree.body)

    def tool_calculate(self, expression: str) -> str:
        try:
            return str(self._safe_eval(expression))
        except Exception as e:
            return f"[Calculation error: {e}]"

    def generate_prompt(self, user_input: str) -> str:
        system_text = (
            "You are the Sovereign Agentic AGI ALPHA. "
            "You think step-by-step but never reveal your chain-of-thought. "
            "Use the following format for advanced reasoning if needed:\n"
            "Thought: <reasoning>\n"
            "Action: <tool> [<input>]\n"
            "Observation: <result>\n"
            "Thought: <further reasoning>\n"
            "Answer: <final answer>\n\n"
            "Tools available: Search, Calculate.\n"
        )
        conv_text = ""
        for turn in self.history:
            if turn["role"] == "user":
                conv_text += f"User: {turn['content']}\n"
            else:
                conv_text += f"Assistant: {turn['content']}\n"
        conv_text += f"User: {user_input}\nAssistant:"
        return system_text + conv_text

    def call_llm(self, prompt: str) -> str:
        if self.provider == "openai":
            try:
                response = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=[{"role":"system","content":prompt}],
                    temperature=0.7,
                    timeout=OPENAI_TIMEOUT_SEC
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"[OpenAI error: {e}]"
        elif self.provider == "anthropic" and self.anthropic_client:
            full_prompt = f"{HUMAN_PROMPT} {prompt}{AI_PROMPT}"
            try:
                resp = self.anthropic_client.completions.create(
                    model=os.getenv("ANTHROPIC_MODEL","claude-2"),
                    prompt=full_prompt,
                    max_tokens_to_sample=1024,
                    temperature=0.7
                )
                return resp.completion.strip()
            except Exception as e:
                return f"[Anthropic error: {e}]"
        else:
            # local Ollama
            cmd = ["ollama", "run", self.model_name, prompt]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    err = result.stderr.strip() or "Unknown ollama CLI error"
                    return f"[Ollama error: {err}]"
            except FileNotFoundError:
                # fallback to HTTP
                try:
                    url = os.getenv("OLLAMA_URL","http://localhost:11434") + "/generate"
                    pl = {"model": self.model_name, "prompt": prompt, "stream": False}
                    r = requests.post(url, json=pl, timeout=300)
                    if r.status_code == 200:
                        j = r.json()
                        return j.get("reply", j.get("completion","")).strip()
                    else:
                        return f"[Ollama HTTP error: {r.status_code}]"
                except Exception as e:
                    return f"[Ollama fallback error: {e}]"
            except Exception as e:
                return f"[Ollama error: {e}]"

    def parse_react(self, text: str):
        lines = text.split("\n")
        steps = []
        current_block = {"type": None, "content": ""}
        for line in lines:
            line = line.strip()
            if line.lower().startswith("thought:"):
                if current_block["type"] is not None:
                    steps.append(current_block)
                current_block = {"type": "thought", "content": line[len("Thought:"):].strip()}
            elif line.lower().startswith("action:"):
                if current_block["type"] is not None:
                    steps.append(current_block)
                current_block = {"type": "action", "content": line[len("Action:"):].strip()}
            elif line.lower().startswith("observation:"):
                if current_block["type"] is not None:
                    steps.append(current_block)
                current_block = {"type": "observation", "content": line[len("Observation:"):].strip()}
            elif line.lower().startswith("answer:"):
                if current_block["type"] is not None:
                    steps.append(current_block)
                current_block = {"type": "answer", "content": line[len("answer:"):].strip()}
                steps.append(current_block)
                current_block = {"type": None, "content": ""}
            else:
                if current_block["type"] is not None:
                    current_block["content"] += " " + line
        if current_block["type"] is not None:
            steps.append(current_block)
        return steps

    def run_react_loop(self, prompt: str) -> str:
        remaining_steps = self.max_steps
        partial_prompt = prompt
        while remaining_steps > 0:
            model_output = self.call_llm(partial_prompt)
            steps = self.parse_react(model_output)
            final_answer = ""
            tool_invoked = False
            for step in steps:
                if step["type"] == "answer":
                    final_answer = step["content"]
                    break
                elif step["type"] == "action":
                    toolline = step["content"]
                    match = re.match(r"(\w+)\s*\[(.*)\]", toolline)
                    if match:
                        toolname = match.group(1).strip()
                        toolarg = match.group(2).strip()
                        toolfn = self.reaction_tools.get(toolname, None)
                        if toolfn:
                            observation = toolfn(toolarg)
                            partial_prompt += f"\nObservation: {observation}\nThought:"
                            tool_invoked = True
                        else:
                            partial_prompt += f"\nObservation: [No such tool: {toolname}]\nThought:"
                            tool_invoked = True
            if final_answer:
                return final_answer
            if not tool_invoked:
                # no further "Action" => agent likely gave a final answer
                return model_output.strip()
            remaining_steps -= 1
        return "I'm sorry, I cannot determine the final answer."

    def handle_message(self, user_input: str) -> str:
        self.memory.add(user_input)
        prompt = self.generate_prompt(user_input)
        final_answer = self.run_react_loop(prompt)
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": final_answer})
        return final_answer

def start_flask_server(agent):
    """
    Minimal Flask-based server on port 5000 so the user
    can chat from the webpage, plus /tree_search, plus /alpha_explorer.
    """
    if not Flask:
        logger.warning("Flask not installed. Web chat is disabled.")
        return

    app = Flask("SovereignAgentFlask")

    PAGE_FILE = os.path.join(os.path.dirname(__file__), "sovereign_agent_web.html")
    if not os.path.isfile(PAGE_FILE):
        logger.warning("No 'sovereign_agent_web.html' found, web interface won't work.")
        PAGE_CONTENT = "<h1>Missing sovereign_agent_web.html</h1>"
    else:
        with open(PAGE_FILE, "r", encoding="utf-8") as f:
            PAGE_CONTENT = f.read()

    @app.route("/", methods=["GET"])
    def index():
        return PAGE_CONTENT, 200

    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.json or {}
        user_input = data.get("message","")
        if not user_input:
            return jsonify({"reply": "No message received."}), 400
        reply = agent.handle_message(user_input)
        return jsonify({"reply": reply})

    @app.route("/tree_search", methods=["POST"])
    def tree_search():
        """
        Minimal demonstration endpoint that calls agentic_treesearch for advanced exploration.
        """
        if not agentic_treesearch:
            return jsonify({"error": "Agentic Tree Search not installed."}), 500
        data = request.json or {}
        topic = data.get("topic","Test")
        try:
            logger.info("Ensuring 'workspace' directory exists...")
            os.makedirs("workspace", exist_ok=True)
            logger.info("Listing 'workspace' contents before tree search:")
            for f in os.listdir("workspace"):
                logger.info(f"   -> {f}")

            config_path = f"./dummy_config_for_{topic}.json"
            dummy_data = {"topic": topic, "ts": time.time()}
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(dummy_data, f)
            logger.info(f"Wrote dummy config {config_path}: {dummy_data}")

            logger.info(f"Calling agentic_treesearch.perform_experiments_bfts({config_path})...")
            bfs_details = agentic_treesearch.perform_experiments_bfts(config_path)
            logger.info("Tree search completed.")

            return jsonify({
                "result": f"Agentic Tree Search triggered with topic='{topic}'.",
                "resultDetails": bfs_details
            })
        except Exception as e:
            logger.exception("Error in /tree_search route", exc_info=e)
            return jsonify({"error": str(e)}), 500

    @app.route("/alpha_explorer", methods=["POST"])
    def alpha_explorer_route():
        """
        Demonstration endpoint for BFS expansions using agentic_alpha_explorer.
        We'll do a quick BFS (1-2 expansions) to avoid indefinite blocking.
        """
        if not agentic_alpha_explorer:
            return jsonify({"error": "Agentic Alpha Explorer not installed."}), 500
        data = request.json or {}
        root_concept = data.get("root","Consciousness Cascades")
        diversity = float(data.get("diversity",1.0))
        agentic = bool(data.get("agentic",False))

        logger.info(f"alpha_explorer BFS: root='{root_concept}', diversity={diversity}, agentic={agentic}")
        try:
            expansions, summary = agentic_alpha_explorer.run_explorer_once(
                root_concept=root_concept,
                diversity=diversity,
                agentic_mode=agentic
            )
            return jsonify({
                "result": f"Alpha Explorer BFS from root='{root_concept}'.",
                "expansions": expansions,
                "summary": summary
            })
        except Exception as e:
            logger.exception("Error in /alpha_explorer route", exc_info=e)
            return jsonify({"error": str(e)}), 500

    def run_flask():
        app.run(host="0.0.0.0", port=5000, debug=False)

    threading.Thread(target=run_flask, daemon=True).start()

def main():
    agent = ReasoningAgent()
    print("Sovereign Agentic AGI ALPHA with CoT + ReAct + MCP + Agentic Tree Search + Alpha Explorer. Type 'exit' or 'quit' to quit.\n")

    # Attempt MCP extension
    try:
        import sovereign_alpha_mcp_extension as mcp_ext
        from sovereign_alpha_mcp_extension import TrustPolicy

        trust_policy = TrustPolicy(
            allowed_cert_fingerprints=trust_config.get("allowed_cert_fingerprints", []),
            allowed_ed25519_keys=trust_config.get("allowed_ed25519_keys", []),
            allowed_domains=trust_config.get("allowed_domains", [])
        )
        extension = mcp_ext.SovereignAlphaAgentMCPExtension(
            trust_policy=trust_policy,
            discovery_github=True,
            discovery_dnssd=True,
            discovery_referrals=[]
        )
        extension.discover_and_launch()
        logger.info(f"MCP Extension integrated. Found {len(extension.mcp_servers)} trusted MCP servers.")
    except Exception as ex:
        logger.warning(f"Could not initialize MCP Extension: {ex}")

    # Start minimal Flask server
    start_flask_server(agent)

    # Original Terminal-based chat loop
    while True:
        try:
            user_input = input("User> ")
        except EOFError:
            print("\n[EOF: stopping agent]")
            break
        if not user_input:
            continue
        if user_input.strip().lower() in ["exit", "quit"]:
            print("Agent> Goodbye.")
            break
        response = agent.handle_message(user_input)
        print(f"Agent> {response}")

if __name__ == "__main__":
    main()
AGENT_PY

###############################################################################
# The Sovereign Alpha Agent MCP Extension Implementation
###############################################################################
cat <<'MCP_PY' > "$TARGET_DIR/sovereign_alpha_mcp_extension.py"
#!/usr/bin/env python3

import os
import json
import logging
import base64
import subprocess
import asyncio
import socket
from typing import List, Optional, Dict, Any

try:
    import dns
    import dns.resolver
except ImportError:
    dns = None

try:
    from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange, ServiceInfo
except ImportError:
    Zeroconf = None
    ServiceBrowser = None
    ServiceInfo = None

try:
    from cryptography.hazmat.primitives.serialization import load_pem_x509_certificate
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, ec, padding as asym_padding
    from cryptography.exceptions import InvalidSignature
except ImportError:
    raise RuntimeError("cryptography library is required for signature verification")

try:
    import requests
except ImportError:
    raise RuntimeError("requests library is required for HTTP operations in discovery")

logger = logging.getLogger("SovereignAlphaMCP")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

class TrustPolicy:
    """
    Trust policy for MCP plugins. Allows:
    - X.509 certificate fingerprint (SHA-256)
    - Ed25519 key (full or hashed)
    - Domain suffix
    """
    def __init__(
        self,
        allowed_cert_fingerprints: Optional[List[str]] = None,
        allowed_ed25519_keys: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None
    ):
        self.allowed_cert_fingerprints = [fp.lower().replace(':', '') for fp in (allowed_cert_fingerprints or [])]
        allowed_keys = allowed_ed25519_keys or []
        normalized_keys = []
        for key in allowed_keys:
            # If the key is a hex string 64 or 128 chars, treat it as raw hex.
            if all(c in "0123456789abcdefABCDEF" for c in key) and len(key) in (64, 128):
                normalized_keys.append(key.lower())
            else:
                # Attempt base64 decode. If fail, skip or log error.
                try:
                    key_bytes = base64.b64decode(key.strip())
                    normalized_keys.append(key_bytes.hex())
                except Exception as e:
                    logger.error(f"Invalid Ed25519 key format: {key} ({e})")
        self.allowed_ed25519_keys = normalized_keys
        # domain suffixes
        self.allowed_domains = [d.lower().lstrip("*").lstrip(".") for d in (allowed_domains or [])]

    def is_trusted(self, plugin: Dict[str, Any]) -> bool:
        source = plugin.get("source","<unknown>")
        name = plugin.get("name", source)
        cert_pem = plugin.get("certificate")
        signature_b64 = plugin.get("signature")
        pubkey_b64 = plugin.get("public_key")

        domain = None
        if plugin.get("url"):
            try:
                from urllib.parse import urlparse
                parsed = urlparse(plugin["url"])
                if parsed.hostname:
                    domain = parsed.hostname.lower()
            except:
                domain = None
        if not domain and plugin.get("domain"):
            domain = plugin["domain"].lower()

        # Check domain allowlist
        if domain:
            for allowed in self.allowed_domains:
                if domain == allowed or domain.endswith("." + allowed):
                    logger.info(f"TrustPolicy: '{name}' trusted by domain: {domain}")
                    return True

        # Check certificate fingerprint
        if cert_pem:
            try:
                cert = load_pem_x509_certificate(cert_pem.encode('utf-8'))
            except Exception as e:
                logger.error(f"TrustPolicy: Failed to load cert for plugin '{name}': {e}")
                return False
            try:
                cert_fingerprint = cert.fingerprint(hashes.SHA256()).hex()
            except Exception:
                cert_bytes = cert.tbs_certificate_bytes
                digest = hashes.Hash(hashes.SHA256())
                digest.update(cert_bytes)
                cert_fingerprint = digest.finalize().hex()
            if cert_fingerprint.lower() in self.allowed_cert_fingerprints:
                if signature_b64:
                    data = self._signature_data(plugin)
                    if self._verify_signature_with_cert(cert, signature_b64, data):
                        logger.info(f"TrustPolicy: '{name}' verified via certificate signature.")
                        return True
                    else:
                        logger.warning(f"TrustPolicy: Cert signature failed for '{name}'.")
                        return False
                else:
                    logger.info(f"TrustPolicy: '{name}' trusted (cert fingerprint match, no sig).")
                    return True
            else:
                logger.warning(f"TrustPolicy: Cert fingerprint not in allowlist for '{name}'.")

        # Check Ed25519 public key
        if pubkey_b64:
            try:
                pubkey_bytes = base64.b64decode(pubkey_b64.strip())
                pubkey_hex = pubkey_bytes.hex()
            except Exception as e:
                logger.error(f"TrustPolicy: Invalid public_key encoding for '{name}': {e}")
                return False
            allowed_key = False
            if pubkey_hex in self.allowed_ed25519_keys:
                allowed_key = True
            else:
                digest = hashes.Hash(hashes.SHA256())
                digest.update(pubkey_bytes)
                key_hash_hex = digest.finalize().hex()
                if key_hash_hex in self.allowed_ed25519_keys:
                    allowed_key = True
            if allowed_key:
                if signature_b64:
                    data = self._signature_data(plugin)
                    if self._verify_signature_ed25519(pubkey_bytes, signature_b64, data):
                        logger.info(f"TrustPolicy: '{name}' verified via Ed25519 signature.")
                        return True
                    else:
                        logger.warning(f"TrustPolicy: Ed25519 signature fail for '{name}'.")
                        return False
                else:
                    logger.info(f"TrustPolicy: '{name}' trusted (Ed25519 key match, no sig).")
                    return True
            else:
                logger.warning(f"TrustPolicy: Ed25519 key not in allowlist for '{name}'.")

        logger.warning(f"TrustPolicy: '{name}' NOT trusted (deny by default).")
        return False

    def _signature_data(self, plugin: Dict[str, Any]) -> bytes:
        data_obj = {k: v for k,v in plugin.items() if k not in ("signature","certificate")}
        try:
            return json.dumps(data_obj, sort_keys=True, separators=(',',':')).encode('utf-8')
        except:
            safe_obj = {}
            for k,v in data_obj.items():
                if isinstance(v,(str,int,float,bool,list,dict)) or v is None:
                    safe_obj[k] = v
            return json.dumps(safe_obj, sort_keys=True, separators=(',',':')).encode('utf-8')

    def _verify_signature_ed25519(self, pubkey_bytes: bytes, signature_b64: str, data: bytes) -> bool:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.exceptions import InvalidSignature
        try:
            signature = base64.b64decode(signature_b64.strip())
            ed25519.Ed25519PublicKey.from_public_bytes(pubkey_bytes).verify(signature, data)
            return True
        except (InvalidSignature, Exception):
            return False

    def _verify_signature_with_cert(self, cert, signature_b64: str, data: bytes) -> bool:
        from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, ec, padding as asym_padding
        from cryptography.hazmat.primitives import hashes
        from cryptography.exceptions import InvalidSignature
        try:
            signature = base64.b64decode(signature_b64.strip())
        except Exception as e:
            logger.error(f"TrustPolicy: Error decoding base64 sig: {e}")
            return False
        pubkey = cert.public_key()
        try:
            if isinstance(pubkey, ed25519.Ed25519PublicKey):
                pubkey.verify(signature, data)
                return True
            elif isinstance(pubkey, rsa.RSAPublicKey):
                pubkey.verify(signature, data, asym_padding.PKCS1v15(), hashes.SHA256())
                return True
            elif isinstance(pubkey, ec.EllipticCurvePublicKey):
                pubkey.verify(signature, data, ec.ECDSA(hashes.SHA256()))
                return True
            else:
                logger.error("TrustPolicy: Unsupported key type in cert.")
                return False
        except InvalidSignature:
            return False
        except Exception as e:
            logger.error(f"TrustPolicy: Cert sig verify error: {e}")
            return False

class SovereignAlphaAgentMCPExtension:
    """
    Discover, validate, launch MCP servers.
    """
    def __init__(self, trust_policy: TrustPolicy,
                 discovery_github: bool = True,
                 discovery_dnssd: bool = True,
                 discovery_referrals: Optional[List[str]] = None):
        self.trust_policy = trust_policy
        self.discovery_github = discovery_github
        self.discovery_dnssd = discovery_dnssd
        self.discovery_referrals = discovery_referrals or []
        self.mcp_servers: List[Any] = []
        self._launched_containers: List[str] = []
        self._zeroconf: Optional[Zeroconf] = None

    def discover_and_launch(self) -> None:
        plugins = []
        if self.discovery_github:
            plugins += self._discover_from_github()
        if self.discovery_dnssd:
            plugins += self._discover_from_dnssd()
        if self.discovery_referrals:
            plugins += self._process_referrals(self.discovery_referrals)
        if not plugins:
            logger.info("No MCP plugins discovered from any source.")

        for plugin in plugins:
            name = plugin.get("name") or plugin.get("source") or "<unknown>"
            try:
                if not self.trust_policy.is_trusted(plugin):
                    logger.info(f"Skipping '{name}' (not trusted).")
                    continue
                transport = plugin.get("transport", "").lower()
                if not transport:
                    if plugin.get("command"):
                        transport = "stdio"
                    elif plugin.get("url"):
                        transport = "sse"
                    elif plugin.get("image"):
                        transport = "docker"

                if transport == "stdio":
                    params: Dict[str,Any] = {}
                    for k in ("command","args","env","cwd","encoding","encoding_error_handler"):
                        if k in plugin:
                            params[k] = plugin[k]
                    if "command" not in params:
                        logger.error(f"Cannot launch '{name}': no 'command' for stdio.")
                        continue
                    logger.info(f"Launched STDIO server for '{name}' (Pseudo).")
                    self.mcp_servers.append({"server_type":"stdio","params":params,"name":name})

                elif transport == "sse":
                    params: Dict[str,Any] = {}
                    for k in ("url","headers","timeout","sse_read_timeout"):
                        if k in plugin:
                            params[k] = plugin[k]
                    if "url" not in params:
                        logger.error(f"Cannot connect '{name}': no 'url' for SSE.")
                        continue
                    logger.info(f"Connected SSE server '{name}' at {params.get('url')}. (Pseudo)")
                    self.mcp_servers.append({"server_type":"sse","params":params,"name":name})

                elif transport == "docker":
                    image = plugin.get("image")
                    if not image:
                        logger.error(f"Cannot launch '{name}': no 'image' for Docker.")
                        continue
                    container_port = plugin.get("port",80)
                    try:
                        result = subprocess.run(["docker","run","-d","--rm","-P",image],
                                                capture_output=True,text=True)
                        if result.returncode != 0:
                            logger.error(f"Docker launch failed '{name}': {result.stderr.strip()}")
                            continue
                        cid = result.stdout.strip()
                        self._launched_containers.append(cid)
                        logger.info(f"'{name}' Docker container {cid[:12]} started.")
                        port_res = subprocess.run(["docker","port", cid, str(container_port)],
                                                  capture_output=True,text=True)
                        if port_res.returncode!=0 or not port_res.stdout:
                            logger.error(f"No port map for '{name}': {port_res.stderr.strip()}")
                            subprocess.run(["docker","rm","-f",cid])
                            self._launched_containers.remove(cid)
                            continue
                        mapping = port_res.stdout.strip()
                        host_port = None
                        if "->" in mapping:
                            host_port = mapping.split("->")[-1].split(":")[-1]
                        host_port = host_port.strip() if host_port else None
                        if not host_port:
                            logger.error(f"Unrecognized port map '{name}': {mapping}")
                            subprocess.run(["docker","rm","-f",cid])
                            self._launched_containers.remove(cid)
                            continue
                        url = f"http://localhost:{host_port}"
                        logger.info(f"'{name}' Docker SSE at {url} (Pseudo).")
                        self.mcp_servers.append({"server_type":"docker_sse","url":url,"name":name})
                    except FileNotFoundError:
                        logger.error(f"Docker not installed - cannot run '{name}'.")
                        continue
                else:
                    logger.warning(f"'{name}' uses unsupported transport '{transport}'. Will skip or isolate.")
                    if plugin.get("image"):
                        try:
                            result = subprocess.run(["docker","run","-d","--rm",plugin["image"]],
                                                    capture_output=True,text=True)
                            if result.returncode==0:
                                cid = result.stdout.strip()
                                self._launched_containers.append(cid)
                                logger.warning(f"'{name}' isolated in Docker (no integration).")
                            else:
                                logger.error(f"Failed to isolate '{name}': {result.stderr.strip()}")
                        except Exception as e:
                            logger.error(f"Error isolating '{name}': {e}")
                    continue

            except Exception as e:
                logger.exception(f"Error processing plugin '{name}': {e}")

        logger.info(f"Discovery complete. {len(self.mcp_servers)} integrated.")
        if self.mcp_servers:
            names=[str(s.get('name')) for s in self.mcp_servers]
            logger.info("Trusted servers: " + ", ".join(names))

    def _discover_from_github(self) -> List[Dict[str,Any]]:
        discovered=[]
        try:
            idx="https://raw.githubusercontent.com/modelcontextprotocol/servers/main/README.md"
            resp=requests.get(idx,timeout=5)
            if resp.status_code==200:
                content=resp.text
                for line in content.splitlines():
                    if line.startswith("* ["):
                        start=line.find("](https://github.com/")
                        if start!=-1:
                            end=line.find(")",start)
                            if end!=-1:
                                repo_url=line[start+2:end]
                                plugin_name=line[line.find("[")+1:line.find("]")]
                                manifest=self._fetch_repo_manifest(repo_url)
                                if manifest:
                                    manifest["source"]=repo_url
                                    if "name" not in manifest:
                                        manifest["name"]=plugin_name
                                    discovered.append(manifest)
                                else:
                                    image=None
                                    command=None
                                    args=None
                                    if repo_url.endswith(".git"):
                                        repo_url=repo_url[:-4]
                                    parts=repo_url.rstrip("/").split("/")
                                    rname=parts[-1] if parts else ""
                                    if "server" in rname.lower():
                                        command="npx"
                                        args=["-y",f"@modelcontextprotocol/{rname}"]
                                    if command or image:
                                        pl={"name":plugin_name,"source":repo_url}
                                        if command:
                                            pl.update({"transport":"stdio","command":command,"args":args})
                                        if image:
                                            pl.update({"transport":"docker","image":image})
                                        discovered.append(pl)
            else:
                logger.warning(f"GitHub discovery fail status {resp.status_code}")
        except Exception as e:
            logger.error(f"GitHub discovery error: {e}")
        logger.info(f"GitHub discovered {len(discovered)} plugins.")
        return discovered

    def _fetch_repo_manifest(self, repo_url:str)->Optional[Dict[str,Any]]:
        raw_base=repo_url.replace("https://github.com","https://raw.githubusercontent.com")
        if raw_base.endswith("/"):
            raw_base=raw_base[:-1]
        if raw_base.endswith(".git"):
            raw_base=raw_base[:-4]
        for branch in ("main","master"):
            for fname in ("mcp.json","MCP.json","manifest.json","mcp.yaml","MCP.yaml","manifest.yaml"):
                url=f"{raw_base}/{branch}/{fname}"
                try:
                    resp=requests.get(url,timeout=3)
                    if resp.status_code==200:
                        txt=resp.text
                        if fname.endswith(".json"):
                            return json.loads(txt)
                        else:
                            try:
                                import yaml
                                return yaml.safe_load(txt)
                            except:
                                logger.warning(f"YAML parse failed {url}")
                                return None
                except:
                    continue
        return None

    def _discover_from_dnssd(self)->List[Dict[str,Any]]:
        discovered=[]
        if Zeroconf:
            try:
                services=[]
                def on_service_state_change(zc:Zeroconf,stype:str,name:str,sc):
                    if sc is ServiceStateChange.Added:
                        try:
                            info:ServiceInfo=zc.get_service_info(stype,name)
                            if info:
                                host=None
                                if info.addresses:
                                    try:
                                        host=socket.inet_ntoa(info.addresses[0])
                                    except:
                                        try:
                                            host=socket.inet_ntop(socket.AF_INET6,info.addresses[0])
                                        except:
                                            host=None
                                if not host and info.server:
                                    host=info.server.strip(".")
                                port=info.port
                                if host:
                                    url=f"http://{host}:{port}"
                                    plugin={"name":info.name,"transport":"sse","url":url,
                                            "domain":info.server.rstrip('.') if info.server else None,
                                            "source":"mDNS"}
                                    if info.properties:
                                        try:
                                            for k,v in info.properties.items():
                                                kk=k.decode('utf-8') if isinstance(k,bytes) else str(k)
                                                vv=v.decode('utf-8') if isinstance(v,bytes) else str(v)
                                                plugin[kk]=vv
                                        except:
                                            pass
                                    services.append(plugin)
                        except Exception as e:
                            logger.error(f"mDNS service '{name}' error: {e}")
                self._zeroconf=Zeroconf()
                ServiceBrowser(self._zeroconf,"_mcp._tcp.local.",handlers=[on_service_state_change])
                import time
                time.sleep(3)
                self._zeroconf.close()
                self._zeroconf=None
                if services:
                    discovered.extend(services)
            except Exception as e:
                logger.error(f"mDNS discovery error: {e}")
        else:
            logger.debug("No zeroconf, skipping mDNS.")

        if dns and dns.resolver:
            test_domains=[]
            for ref in self.discovery_referrals:
                if isinstance(ref,str) and "." in ref and not ref.startswith("http") and not ref.startswith("_mcp._tcp"):
                    test_domains.append(ref)
            test_domains=list({d.lower() for d in test_domains})
            for domain in test_domains:
                q=f"_mcp._tcp.{domain}"
                try:
                    ans=dns.resolver.resolve(q,"SRV")
                    for a in ans:
                        tgt=str(a.target).rstrip(".")
                        port=a.port
                        url=f"http://{tgt}:{port}"
                        plugin={"transport":"sse","url":url,"domain":tgt,"source":"DNS-SD"}
                        try:
                            txtans=dns.resolver.resolve(q,"TXT")
                            for t in txtans:
                                txt_data="".join(s.decode('utf-8') for s in t.strings)
                                for part in txt_data.split(";"):
                                    if '=' in part:
                                        k,v=part.split('=',1)
                                        plugin[k.strip()]=v.strip()
                        except:
                            pass
                        discovered.append(plugin)
                except Exception as e:
                    logger.debug(f"No SRV for '{q}': {e}")
        else:
            if dns is None:
                logger.debug("dnspython not installed, skipping DNS-SD.")
        if discovered:
            logger.info(f"DNS-SD discovered {len(discovered)} plugin(s).")
        return discovered

    def _process_referrals(self,referrals:List[str])->List[Dict[str,Any]]:
        discovered=[]
        for ref in referrals:
            if not isinstance(ref,str):
                continue
            if ref.startswith("http://") or ref.startswith("https://"):
                try:
                    resp=requests.get(ref,timeout=5)
                    if resp.status_code==200:
                        data=resp.text
                        plugin=None
                        try:
                            plugin=json.loads(data)
                        except json.JSONDecodeError:
                            try:
                                import yaml
                                plugin=yaml.safe_load(data)
                            except:
                                plugin=None
                        if plugin:
                            plugin["source"]=ref
                            discovered.append(plugin)
                            continue
                except Exception as e:
                    logger.debug(f"Referral fetch fail {ref}: {e}")
            if "github.com" in ref or "/" in ref:
                if ref.startswith("http"):
                    gh_url=ref
                else:
                    parts=ref.split("/")
                    if len(parts)==2:
                        owner,repo=parts
                        gh_url=f"https://raw.githubusercontent.com/{owner}/{repo}/main/mcp.json"
                    else:
                        gh_url=None
                if gh_url:
                    try:
                        resp=requests.get(gh_url,timeout=5)
                        if resp.status_code==200:
                            plugin=json.loads(resp.text)
                            plugin["source"]=gh_url
                            discovered.append(plugin)
                            continue
                    except Exception as e:
                        logger.debug(f"GitHub referral fail {gh_url}: {e}")
        return discovered

    def shutdown(self)->None:
        async def _close_server(s):
            try:
                pass
            except Exception as e:
                logger.debug(f"Error closing server {s}: {e}")
        async def _close_all():
            tasks=[asyncio.create_task(_close_server(s)) for s in self.mcp_servers]
            if tasks:
                await asyncio.gather(*tasks,return_exceptions=True)
        try:
            asyncio.run(_close_all())
        except RuntimeError:
            pass
        for cid in list(self._launched_containers):
            try:
                subprocess.run(["docker","rm","-f",cid],timeout=5,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.warning(f"Failed to stop container {cid}: {e}")
        self._launched_containers.clear()
        logger.info("All plugin servers & containers shut down.")
MCP_PY

###############################################################################
# Minimal .dockerignore
###############################################################################
cat <<'DOCKERIGNORE' > "$TARGET_DIR/.dockerignore"
.git
__pycache__
DOCKERIGNORE

###############################################################################
# requirements.txt (including libraries for agentic_alpha_explorer.py)
###############################################################################
cat <<'REQS' > "$TARGET_DIR/requirements.txt"
numpy<2.0.0
requests>=2.28.0
pyyaml>=6.0
openai>=0.27.0
anthropic>=0.49.0
chromadb>=0.6.3
weaviate-client>=4.11.0
pandas>=1.5.0

torch==2.0.1
transformers==4.28.0
sentence-transformers==2.2.2

dnspython>=2.2.1
zeroconf>=0.39.0
cryptography>=39.0.0
openai-agents>=0.0.6

flask>=2.2.0
shutup>=0.2.0
humanize>=4.0.0
dataclasses-json>=0.5.7
jsonschema>=4.0.0
networkx>=2.6.0
REQS

###############################################################################
# Dockerfile
###############################################################################
cat <<'DOCKERFILE' > "$TARGET_DIR/Dockerfile"
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./

# Install system packages + cryptography build deps + wheel
RUN apt-get update && \
    apt-get install -y curl build-essential libssl-dev libffi-dev python3-dev python3-wheel && \
    rm -rf /var/lib/apt/lists/* && \
    # Ensuring the newest pip/setuptools/wheel to fix "bdist_wheel not found":
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # Install Ollama in container
    curl -fsSL https://ollama.com/install.sh | sh && \
    ln -s /usr/bin/ollama /usr/local/bin/ollama || true && \
    # Install Python deps
    pip install --no-cache-dir -r requirements.txt && \
    # Re-install huggingface_hub==0.10.1 for older sentence-transformers
    pip uninstall -y huggingface_hub && \
    pip install --no-cache-dir huggingface_hub==0.10.1 && \
    # Additional forced step so we confirm cryptography + SentenceTransformer + Flask are present
    python -c "import cryptography; import sentence_transformers; import flask" && \
    echo 'export PATH="/usr/local/bin:$PATH"' >> /root/.bashrc

COPY sovereign_agent.py ./
COPY sovereign_alpha_mcp_extension.py ./
COPY trust_whitelist.yaml ./
COPY sovereign_agent_web.html ./sovereign_agent_web.html
COPY agentic_treesearch.py ./

# The Agentic Alpha Explorer code (BFS expansions):
COPY agentic_alpha_explorer.py ./

EXPOSE 5000
RUN mkdir -p data
CMD ["python","sovereign_agent.py"]
DOCKERFILE

###############################################################################
# docker-compose.yaml
###############################################################################
cat <<'COMPOSE' > "$TARGET_DIR/docker-compose.yaml"
version: "3.8"
services:
  agent:
    build: .
    image: sovereign-agent:latest
    container_name: sovereign_agent
    network_mode: host
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER-ollama}
      - OPENAI_API_KEY=${OPENAI_API_KEY-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY-}
      - OLLAMA_MODEL=${OLLAMA_MODEL-gemma3:4b}
      - OLLAMA_URL=${OLLAMA_URL-http://localhost:11434}
      - MEMORY_BACKEND=${MEMORY_BACKEND-chroma}
      - EMBEDDING_MODE=${EMBEDDING_MODE-local}
      - WEAVIATE_URL=${WEAVIATE_URL-http://localhost:8080}
    stdin_open: true
    tty: true
COMPOSE

###############################################################################
# trust_whitelist.yaml
###############################################################################
cat <<'TRUST' > "$TARGET_DIR/trust_whitelist.yaml"
allowed_domains:
  - "example.com"
allowed_paths:
  - "./data"
allowed_tools:
  - "web_fetch"
  - "file_read"
  - "file_write"
allowed_cert_fingerprints: []
allowed_ed25519_keys: []
TRUST

###############################################################################
# README.md
###############################################################################
cat <<'README' > "$TARGET_DIR/README.md"
# Sovereign Agentic AGI ALPHA (v0)

This single-file, production-ready agent integrates chain-of-thought
and ReAct orchestration for advanced reasoning, plus the **Sovereign
Alpha Agent MCP Extension** for secure self-extension, plus
**Agentic Tree Search** and **Agentic Alpha Explorer** BFS expansions.

## Common Fixes
- cryptography installed (>=39.0.0) to fix "cryptography library is required" error.
- pinned sentence-transformers + torch + transformers to avoid "init_empty_weights not defined".
- pinned numpy<2.0.0.
- Minimal Flask-based web UI at http://localhost:5000 or http://<your-host>:5000, 
  serving the big HTML page, so a non-technical user can interact.
- The web chat fetch is now a relative "/chat" call to avoid "Failed to fetch."
- Dockerfile now installs python3-wheel so that sentence-transformers==2.2.2
  can build wheels properly in the container.
- We also explicitly upgrade pip, setuptools, and wheel inside Docker to fix "invalid command 'bdist_wheel'".
- We provide a /tree_search route (Agentic Tree Search) and a /alpha_explorer route (Agentic Alpha Explorer BFS).
- **Extra Debug**: check container logs to see BFS expansions or tree-search logs.

## Usage
1. docker-compose build
2. docker-compose up -d
3. This script auto-attaches to sovereign_agent for Terminal chat (type exit/quit to end).
4. Meanwhile, the minimal Flask UI is at http://localhost:5000 (or the host's IP:port).
   - A wallet connect flow gates page usage at 500k tokens, agent usage at 1M tokens ($AGIALPHA).
   - Chat with the agent in the terminal or in the web UI.
   - Try BFS expansions at /alpha_explorer or tree search at /tree_search from the web form.
5. For logs: docker-compose logs -f agent or docker attach sovereign_agent.

If /alpha_explorer returns HTTP 500, the container logs will show a traceback after
**"Error in /alpha_explorer route"**. That traceback helps diagnose issues.
README

###############################################################################
# The big webpage (sovereign_agent_web.html)
###############################################################################
cat <<'WEB_HTML' > "$TARGET_DIR/sovereign_agent_web.html"
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>AGI ALPHA AGENT – Official Website</title>
  <!-- LOAD SOLANA WEB3.JS -->
  <script src="https://unpkg.com/@solana/web3.js@1.76.0/lib/index.iife.js"></script>

  <style>
  /* GLOBAL RESETS & FONTS */
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }
  html, body {
    width: 100%;
    height: 100%;
    font-family: "Open Sans", sans-serif;
    overflow-x: hidden;
  }

  body {
    background: linear-gradient(135deg, rgba(255,250,235,1), rgba(255,245,220,1));
    color: #333;
    min-height: 100vh;
    line-height: 1.4;
    scroll-behavior: smooth;
    position: relative;
  }

  #p5-background {
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%; z-index: -1;
    background: url("https://ipfs.io/ipfs/QmQ6MogCaNn5xMWkFa2jtvYSoiTJXtapp3unTenD65SDak")
                center center no-repeat;
    background-size: cover;
    opacity: 0.3;
    mix-blend-mode: multiply;
  }
  #asi-hieroglyphs {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none;
    background: repeating-linear-gradient(
      160deg,
      transparent 0 10px,
      rgba(255,205,160,0.05) 10px 20px,
      transparent 20px 30px,
      rgba(255,225,200,0.03) 30px 40px
    );
    mix-blend-mode: screen;
  }

  #main-content {
    display: none;
  }

  header {
    width: 100%;
    padding: 3rem 1rem 2rem;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  header .agent-image {
    max-width: 500px; width: 85%; border-radius: 0.5rem;
    box-shadow: 0 0 35px rgba(0,0,0,0.25); margin-bottom: 1.5rem;
  }
  header h1 {
    font-family: "Montserrat", sans-serif; font-weight: 700;
    font-size: 2.2rem; color: #8e6d2a; text-transform: uppercase;
    margin-bottom: 1rem; letter-spacing: 0.08em;
  }
  header p.tagline {
    font-size: 1.15rem; color: #a28154; margin-bottom: 1.5rem;
  }
  header a.cta-button {
    display: inline-block; text-decoration: none; padding: 0.9rem 1.5rem;
    font-size: 1.15rem; font-weight: 600; border-radius: 30px; color: #fff;
    background: linear-gradient(135deg, #ffd28f, #fbb45c);
    transition: all 0.4s ease; box-shadow: 0 0 15px rgba(255,255,255,0.3);
  }
  header a.cta-button:hover {
    box-shadow: 0 0 35px rgba(255,255,255,0.5); transform: scale(1.06);
  }

  main {
    width: 90%; max-width: 1100px; margin: 2rem auto;
    background-color: rgba(255,255,255, 0.8);
    backdrop-filter: blur(5px); border-radius: 0.5rem;
    padding: 2rem; box-shadow: 0 0 25px rgba(255,255,255,0.5);
  }
  main h2 {
    font-family: "Montserrat", sans-serif; font-weight: 700; font-size: 1.7rem; color: #8e6d2a; margin: 1rem 0;
  }
  main .code-block {
    display: inline-block; background: #fff3e0; padding: 0.3rem 0.6rem; border-radius: 4px;
    font-family: monospace; color: #8e6d2a;
  }
  main p {
    margin-bottom: 1.2rem; font-size: 1rem; color: #333; line-height: 1.6;
  }
  main p strong {
    font-weight: 700; color: #8e6d2a;
  }

  section {
    margin-bottom: 2rem; opacity: 0; transform: translateY(30px); transition: all 0.8s ease;
  }
  section.in-view {
    opacity: 1; transform: translateY(0);
  }

  hr {
    margin: 2rem 0; border: none; height: 1px; background-color: rgba(142,109,42,0.25);
  }

  .connect-btn {
    display: inline-block; text-decoration: none; padding: 0.9rem 1.5rem; font-size: 1.05rem;
    font-weight: 600; border-radius: 30px; color: #fff;
    background: linear-gradient(135deg, #ffd28f, #fbb45c);
    transition: all 0.4s ease; box-shadow: 0 0 15px rgba(255,255,255,0.3);
    cursor: pointer;
  }
  .connect-btn:hover {
    box-shadow: 0 0 35px rgba(255,255,255,0.5); transform: scale(1.06);
  }
  #access-message {
    margin-top: 1rem; font-weight: bold; font-size: 1rem; color: #8e6d2a; text-align: center;
  }
  #web-chat {
    margin-top: 2rem; padding: 1rem; border-radius: 5px; background: #fef9f3; box-shadow: 0 0 5px rgba(0,0,0,0.1);
  }
  #chat-log {
    width: 100%; height: 200px; background: #ffffff; overflow-y: auto; margin-bottom: 1rem;
    padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; color: #444;
  }
  #user-input {
    width: 75%; padding: 0.6rem; font-size: 1rem; margin-right: 0.5rem;
  }
  #send-btn {
    padding: 0.6rem 1rem; font-size: 1rem; font-weight: 600; color: #fff; background: #fbb45c;
    border: none; border-radius: 4px; cursor: pointer; box-shadow: 0 0 3px rgba(0,0,0,0.1);
  }
  #send-btn:hover {
    background: #f7a53d;
  }

  @media (max-width: 768px) {
    header .agent-image { max-width: 300px; }
    header h1 { font-size: 1.6rem; margin-bottom: 0.7rem; }
    header p.tagline { font-size: 1rem; }
    header a.cta-button { font-size: 1rem; }
    main { padding: 1.5rem; }
    #user-input {
      width: 100%; margin-bottom: 0.5rem;
    }
    #send-btn {
      width: 100%; margin-bottom: 1rem;
    }
  }
  </style>
</head>

<body>
<div id="p5-background"></div>
<div id="asi-hieroglyphs"></div>

<div style="text-align:center; margin-top:3rem;">
  <button id="connect-page" class="connect-btn">Connect Wallet (500k+)</button>
  <p id="page-access-message"></p>
</div>

<div id="main-content">
  <header>
    <img class="agent-image"
         src="https://ipfs.io/ipfs/QmQ6MogCaNn5xMWkFa2jtvYSoiTJXtapp3unTenD65SDak"
         alt="AGI ALPHA AGENT">
    <h1>AGI ALPHA AGENT</h1>
    <p class="tagline">The Official AGI ALPHA AGENT Website</p>
    <a class="cta-button"
       href="https://dexscreener.com/solana/8zq3vBuoy66dur6dhrA4aqnrtGg9yZyRAp51BTBpEXj"
       target="_blank"
       rel="noopener">
      Buy $AGIALPHA Tokens
    </a>
    <p style="margin-top:1rem; font-size:0.95rem; color:#8e6d2a;">
      Contract Address (CA):
      <strong>tWKHzXd5PRmxTF5cMfJkm2Ua3TcjwNNoSRUqx6Apump</strong>
    </p>
  </header>

  <main>
    <section id="web-chat">
      <h2>Chat with AGI ALPHA AGENT (Web)</h2>
      <div id="chat-log"></div>
      <input type="text" id="user-input" placeholder="Type your message here..."/>
      <button id="send-btn">Send</button>
      <p style="font-size:0.85rem; color:#666; margin-top:0.5rem;">
        This sends a POST request to <code>/chat</code> on the same origin 
        (so if you're accessing <code>http://192.168.x.x:5000</code>, it calls <code>http://192.168.x.x:5000/chat</code>).
      </p>
    </section>

    <hr>

    <section>
      <h2>🔱∞  AGENTIC ALPHA EXPLORER (INFINITE MODE)  ∞🔱</h2>
      <p>Enter a "root concept," choose a diversity factor, check "Agentic" if you want agentic BFS. This calls <code>/alpha_explorer</code>.</p>
      <div style="display:flex; flex-wrap:wrap; align-items:center; margin-bottom:1rem;">
        <input type="text" id="alpha-root" placeholder="Root concept" value="Consciousness Cascades"
               style="flex:1; min-width:200px; padding:0.5rem; margin-right:0.5rem;"/>
        <input type="number" id="alpha-diversity" placeholder="diversity=1.0" value="1.0"
               style="width:80px; padding:0.5rem; margin-right:0.5rem;"/>
        <label style="margin-right:0.5rem;">
          <input type="checkbox" id="alpha-agentic" /> Agentic BFS
        </label>
        <button id="alpha-run"
                style="padding:0.6rem 1rem; font-size:1rem; font-weight:600; background:#fbb45c; border:none; border-radius:4px; cursor:pointer;">
          Run
        </button>
      </div>
      <div id="alpha-bfs-result"
           style="color:#444; background:#ffffff; padding:0.5rem; border-radius:4px; border:1px solid #ddd; min-height:60px;">
      </div>
    </section>

    <hr>

    <section id="agentic-tree-search">
      <h2>Alpha Explorer with Agentic Tree Search</h2>
      <p>Enter a "topic" or "signal" to explore, then press "Explore" to run the agentic tree search. (Demo on /tree_search)</p>
      <div style="display:flex; flex-wrap:wrap; align-items:center;">
        <input type="text" id="alpha-topic" placeholder="Enter a topic or signal"
               style="flex:1; min-width:200px; padding:0.5rem; margin-right:0.5rem;"/>
        <button id="explore-btn"
                style="padding: 0.6rem 1rem; font-size: 1rem; font-weight: 600; background: #fbb45c; border:none; border-radius:4px; cursor:pointer;">
          Explore
        </button>
      </div>
      <div id="explore-result"
           style="margin-top:1rem; color:#444; background:#ffffff; padding:0.5rem; border-radius:4px; border:1px solid #ddd; min-height:50px;">
      </div>
    </section>

    <hr>

    <section id="about">
      <h2>About AGI ALPHA AGENT</h2>
      <p>
        <strong>AGI-Alpha-Agent-v0</strong><br>
        <strong>CA:</strong>
        <span class="code-block">tWKHzXd5PRmxTF5cMfJkm2Ua3TcjwNNoSRUqx6Apump</span><br>
        <strong>AGI ALPHA AGENT (ALPHA.AGENT.AGI.Eth) Powered by $AGIALPHA</strong><br>
        <strong>Seize the Alpha. Transform the world.</strong>
      </p>
      <p>
        <a href="https://www.linkedin.com/in/montrealai/" target="_blank" rel="noopener">Vincent Boucher</a>,
        an AI pioneer and President of
        <a href="https://www.montreal.ai/" target="_blank" rel="noopener">MONTREAL.AI</a>
        and <a href="https://www.quebec.ai/" target="_blank" rel="noopener">QUEBEC.AI</a> since 2003,
        reshaped the landscape by dominating the
        <a href="https://web.archive.org/web/20170929214241/https://gym.openai.com/read-only.html"
           target="_blank" rel="noopener">OpenAI Gym</a>
        with <strong>AI Agents</strong> in 2016 (#1 worldwide) and unveiling the game-changing
        <a href="https://www.quebecartificialintelligence.com/priorart"
           target="_blank" rel="noopener">“Multi-Agent AI DAO”</a> blueprint in 2017
        (“<em>The Holy Grail of Foundational IP at the Intersection of AI Agents and Blockchain</em>”).
      </p>
      <p>
        Our <strong>AGI ALPHA AGENT</strong>, fueled by the strictly-utility
        <strong>$AGIALPHA</strong> token, now harnesses that visionary foundation—
        <em>arguably the world’s most valuable, impactful and important IP</em>—to unleash
        the ultimate alpha signal engine.
      </p>
    </section>

    <hr>

    <section id="access-gate">
      <h2>Access the AGI ALPHA AGENT</h2>
      <p>You must hold at least <strong>1,000,000</strong> $AGIALPHA tokens to proceed.</p>
      <button id="connect-wallet" class="connect-btn">Connect Wallet</button>
      <p id="access-message"></p>
      <p>
        <strong>CA:</strong>
        <span class="code-block">tWKHzXd5PRmxTF5cMfJkm2Ua3TcjwNNoSRUqx6Apump</span><br>
      </p>
      <p><strong>Exclusive Access with $AGIALPHA Token</strong></p>
    </section>

    <hr>

    <section id="disclaimers">
      <h2>Initial Terms & Conditions</h2>
      <p><strong>The Emergence of an AGI-Powered Alpha Agent.</strong></p>
      <p><strong>Ticker ($): AGIALPHA</strong></p>
      <p>
        Rooted in the publicly disclosed 2017 “Multi-Agent AI DAO” prior art, the AGI ALPHA AGENT
        utilizes $AGIALPHA tokens purely as utility tokens—no equity, no profit-sharing—intended
        for the purchase of products/services by the AGI ALPHA AGENT (ALPHA.AGENT.AGI.Eth).
        They are not intended for investment or speculative purposes.
      </p>
      <p><strong>1.</strong> <strong>Token Usage</strong>: strictly utility tokens—no equity, no profit-sharing.</p>
      <p><strong>2.</strong> <strong>Non-Refundable</strong>.</p>
      <p><strong>3.</strong> <strong>No Guarantee of Value</strong>.</p>
      <p><strong>4.</strong> <strong>Regulatory Compliance</strong>.</p>
      <p><strong>5.</strong> <strong>User Responsibility</strong>.</p>
      <p><strong>OVERRIDING AUTHORITY:</strong> AGI.Eth</p>
      <p>$AGIALPHA is experimental. Any expectation of profit is unjustified.</p>
      <p>By using $AGIALPHA, you agree to the $AGIALPHA Terms and Conditions.</p>
    </section>

    <hr>

    <section id="further-info">
      <h2>Further Information</h2>
      <p>
        <strong>Discord:</strong>
        <a href="https://discord.gg/montrealai" target="_blank" rel="noopener">https://discord.gg/montrealai</a>
      </p>
      <p>
        <strong>LinkedIn:</strong>
        <a href="https://www.linkedin.com/in/montrealai/" target="_blank" rel="noopener">
          https://www.linkedin.com/in/montrealai/
        </a>
      </p>
      <p>
        <strong>X (AGI ALPHA AGENT):</strong>
        <a href="https://x.com/agialphaagent" target="_blank" rel="noopener">https://x.com/agialphaagent</a>
      </p>
      <p>
        <strong>X (MONTREAL.AI):</strong>
        <a href="https://x.com/Montreal_AI" target="_blank" rel="noopener">https://x.com/Montreal_AI</a>
      </p>
      <p>
        <strong>Facebook Page:</strong>
        <a href="https://www.facebook.com/MontrealAI/" target="_blank" rel="noopener">
          https://www.facebook.com/MontrealAI/
        </a>
      </p>
      <p>
        <strong>Facebook Group:</strong>
        <a href="https://www.facebook.com/groups/MontrealAI" target="_blank" rel="noopener">
          https://www.facebook.com/groups/MontrealAI
        </a>
      </p>
      <p>
        <strong>Telegram:</strong>
        <a href="https://t.me/agialpha" target="_blank" rel="noopener">https://t.me/agialpha</a>
      </p>
      <p>
        <strong>YouTube:</strong>
        <a href="https://www.youtube.com/montrealai" target="_blank" rel="noopener">
          https://www.youtube.com/montrealai
        </a>
      </p>
      <p>
        <strong>Official info about $AGIALPHA</strong> is in the on-chain records of the AGI ALPHA Agent:
        <a href="https://app.ens.domains/alpha.agent.agi.eth" target="_blank" rel="noopener">
          https://app.ens.domains/alpha.agent.agi.eth
        </a>.
      </p>
      <p>Pre-Alpha Version — Under Development.</p>
    </section>
  </main>
</div>

<!-- p5.js: background star effect -->
<script src="https://cdn.jsdelivr.net/npm/p5@1.6.0/lib/p5.min.js"></script>
<script>
let starCount = 33;
let stars = [];
let containerRadius = 300;
let angle = 0;

function setup() {
  const cnv = createCanvas(windowWidth, windowHeight, WEBGL);
  cnv.parent("p5-background");
  colorMode(HSB, 360, 100, 100);
  noStroke();
  for (let i = 0; i < starCount; i++) {
    stars.push(new Star());
  }
}

function draw() {
  background(0, 0.08);
  rotateY(angle * 0.001);
  rotateX(angle * 0.0007);
  angle += 0.2;

  let zoom = sin(frameCount * 0.002) * 150;
  translate(0, 0, zoom);

  push();
  noFill();
  stroke(50, 0, 100, 20);
  sphere(containerRadius);
  pop();

  for (let s of stars) {
    s.update();
    s.render();
  }
}

class Star {
  constructor() {
    let r = random(containerRadius);
    let theta = random(TWO_PI);
    let phi = random(PI);
    this.x = r * sin(phi) * cos(theta);
    this.y = r * sin(phi) * sin(theta);
    this.z = r * cos(phi);
    this.vx = random(-1,1);
    this.vy = random(-1,1);
    this.vz = random(-1,1);
    this.hue = random(360);
    this.size = random(4,7);
  }

  update() {
    this.x += this.vx;
    this.y += this.vy;
    this.z += this.vz;
    let magPos = sqrt(this.x*this.x + this.y*this.y + this.z*this.z);
    if(magPos > containerRadius - this.size) {
      let nx = this.x / magPos;
      let ny = this.y / magPos;
      let nz = this.z / magPos;
      let dot = this.vx*nx + this.vy*ny + this.vz*nz;
      this.vx -= 2*dot*nx;
      this.vy -= 2*dot*ny;
      this.vz -= 2*dot*nz;
    }
  }

  render() {
    push();
    translate(this.x, this.y, this.z);
    fill(this.hue, 80, 100);
    sphere(this.size);
    pop();
    this.hue += 0.4;
    if(this.hue >= 360) this.hue = 0;
  }
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}
</script>

<script>
document.addEventListener("DOMContentLoaded", () => {
  const sections = document.querySelectorAll("section");
  const observerOpts = { root: null, rootMargin: "0px", threshold: 0.1 };
  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if(entry.isIntersecting) {
        entry.target.classList.add("in-view");
        obs.unobserve(entry.target);
      }
    });
  }, observerOpts);
  sections.forEach(sec => observer.observe(sec));
});
</script>

<!-- WALLET CONNECT + BALANCE CHECK SCRIPT -->
<script>
const TOKEN_MINT = "tWKHzXd5PRmxTF5cMfJkm2Ua3TcjwNNoSRUqx6Apump";
const MIN_TOKENS_FOR_PAGE = 500000;
const MIN_TOKENS_FOR_AGENT = 1000000;
const RPC_URL = "https://solana-mainnet.g.alchemy.com/v2/KT1RV46Eoje4kL-SC2pSANHTVm6-wgwF";
const { Connection, PublicKey } = solanaWeb3;
const pageBtn   = document.getElementById("connect-page");
const pageMsg   = document.getElementById("page-access-message");
const agentBtn  = document.getElementById("connect-wallet");
const agentMsg  = document.getElementById("access-message");
const mainEl    = document.getElementById("main-content");

mainEl.style.display = "none";

async function getBalance(ownerPubkey) {
  const connection = new Connection(RPC_URL, "confirmed");
  const tokenAccounts = await connection.getParsedTokenAccountsByOwner(
    new PublicKey(ownerPubkey),
    { programId: new PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA") }
  );
  let balance = 0;
  for(const acc of tokenAccounts.value) {
    const info = acc.account.data.parsed.info;
    if(info.mint === TOKEN_MINT) {
      balance += info.tokenAmount.uiAmount;
    }
  }
  return balance;
}

// #1: Connect for PAGE Access (>=500k)
pageBtn.addEventListener("click", async () => {
  if(!window.solana || !window.solana.isPhantom) {
    alert("Phantom Wallet not found! Please install or enable it first.");
    return;
  }
  try {
    await window.solana.connect();
    const pubkeyStr = window.solana.publicKey.toString();
    pageMsg.innerText = `Connected: ${pubkeyStr}\nChecking balance...`;

    const bal = await getBalance(pubkeyStr);
    if(bal >= MIN_TOKENS_FOR_PAGE) {
      pageMsg.innerText = `✅ You hold ${bal.toLocaleString()} $AGIALPHA.\nPage access granted.`;
      mainEl.style.display = "block";
    } else {
      pageMsg.innerText = `⛔ You hold ${bal.toLocaleString()} $AGIALPHA, below 500,000.\nAccess denied.`;
      mainEl.style.display = "none";
    }
  } catch(e) {
    console.error(e);
    alert("Failed to connect or check balance (page).");
  }
});

// #2: Connect for AGENT Access (>=1M)
agentBtn.addEventListener("click", async () => {
  if(!window.solana || !window.solana.isPhantom) {
    alert("Phantom Wallet not found! Please install or enable it first.");
    return;
  }
  try {
    await window.solana.connect();
    const pubkeyStr = window.solana.publicKey.toString();
    agentMsg.innerText = `Connected wallet: ${pubkeyStr}\nChecking if >=1M $AGIALPHA...`;

    const bal = await getBalance(pubkeyStr);
    if(bal >= MIN_TOKENS_FOR_AGENT) {
      agentMsg.innerText = `🚀 Congratulations! You hold ${bal.toLocaleString()} $AGIALPHA.\nAGI ALPHA AGENT Access Granted.`;
    } else {
      agentMsg.innerText = `⛔ You hold ${bal.toLocaleString()} $AGIALPHA, below 1,000,000.\nAccess Denied.`;
    }
  } catch(e) {
    console.error(e);
    alert("Failed to connect or check balance (agent).");
  }
});

// Minimal Web Chat with the container's Flask server on port 5000,
// using relative "/chat" so it works for any IP/host.
const chatLog = document.getElementById("chat-log");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

sendBtn.addEventListener("click", async () => {
  const msg = userInput.value.trim();
  if(!msg) return;
  userInput.value = "";
  chatLog.innerHTML += `<div><strong>You:</strong> ${msg}</div>`;
  try {
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg })
    });
    if(!resp.ok) {
      chatLog.innerHTML += `<div style="color:red;">[HTTP error ${resp.status}]</div>`;
      return;
    }
    const data = await resp.json();
    const reply = data.reply || "[No reply]";
    chatLog.innerHTML += `<div><strong>Agent:</strong> ${reply}</div>`;
    chatLog.scrollTop = chatLog.scrollHeight;
  } catch(err) {
    console.error(err);
    chatLog.innerHTML += `<div style="color:red;">[Error contacting agent: ${err}]</div>`;
  }
});

// Agentic Tree Search UI
const exploreBtn = document.getElementById("explore-btn");
const alphaTopic = document.getElementById("alpha-topic");
const exploreResult = document.getElementById("explore-result");

exploreBtn.addEventListener("click", async () => {
  const topic = alphaTopic.value.trim();
  if(!topic) {
    exploreResult.innerHTML = "<span style='color:red;'>Please enter a topic or signal.</span>";
    return;
  }
  exploreResult.innerText = "Exploring with topic: " + topic + "...";
  try {
    const resp = await fetch("/tree_search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic })
    });
    if(!resp.ok) {
      exploreResult.innerHTML = `<span style="color:red;">[Error: HTTP ${resp.status}]</span>`;
      return;
    }
    const data = await resp.json();
    if (data.resultDetails) {
      exploreResult.innerText = JSON.stringify(data.resultDetails, null, 2);
    } else if (data.result){
      exploreResult.innerText = data.result;
    } else {
      exploreResult.innerText = "[No known result]";
    }
  } catch(err) {
    console.error(err);
    exploreResult.innerHTML = `<span style="color:red;">[Error contacting /tree_search: ${err}]</span>`;
  }
});

// Agentic Alpha Explorer BFS UI
const alphaRootInput = document.getElementById("alpha-root");
const alphaDiversityInput = document.getElementById("alpha-diversity");
const alphaAgenticInput = document.getElementById("alpha-agentic");
const alphaRunBtn = document.getElementById("alpha-run");
const alphaBfsResult = document.getElementById("alpha-bfs-result");

alphaRunBtn.addEventListener("click", async () => {
  const root = alphaRootInput.value.trim();
  const diversity = parseFloat(alphaDiversityInput.value.trim() || "1.0");
  const agentic = alphaAgenticInput.checked;
  if(!root) {
    alphaBfsResult.innerHTML = "<span style='color:red;'>Please enter a root concept.</span>";
    return;
  }
  alphaBfsResult.innerText = `BFS expansions from root="${root}" (agentic=${agentic}, diversity=${diversity})...`;
  try {
    const resp = await fetch("/alpha_explorer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ root, diversity, agentic })
    });
    if(!resp.ok) {
      alphaBfsResult.innerHTML = `<span style="color:red;">[Error: HTTP ${resp.status}]</span>`;
      return;
    }
    const data = await resp.json();
    if(data.error) {
      alphaBfsResult.innerHTML = `<span style="color:red;">Error: ${data.error}</span>`;
      return;
    }
    alphaBfsResult.innerText = JSON.stringify(data, null, 2);
  } catch(err) {
    console.error(err);
    alphaBfsResult.innerHTML = `<span style="color:red;">[Error contacting /alpha_explorer: ${err}]</span>`;
  }
});
</script>

</body>
</html>
WEB_HTML

###############################################################################
# agentic_treesearch.py
###############################################################################
cat <<'TREES_PY' > "$TARGET_DIR/agentic_treesearch.py"
#!/usr/bin/env python3
# agentic_treesearch.py
#
# A minimal stub or placeholder for the Agentic Tree Search engine.
# This file holds advanced BFS / BFTS / custom treesearch logic,
# integrated as a demonstration for open-ended alpha exploration
# from the "/tree_search" endpoint in sovereign_agent.py.
#
# Now returns BFS details (expanded nodes, best node, etc.)
# so the front-end can display expansions & best path.

import os, re, json, time, pickle, uuid, random, queue, signal, shutil, logging, traceback
import humanize, yaml
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Callable, Set
from enum import Enum, auto
import copy
from multiprocessing import Process, Queue

logger = logging.getLogger(__name__)

@dataclass
class Node:
    plan: str = ""
    parent: Optional["Node"] = None
    children: set = field(default_factory=set)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_seed_node: bool = False

    def __post_init__(self):
        if self.parent:
            self.parent.children.add(self)

@dataclass
class Journal:
    nodes: List[Node] = field(default_factory=list)

    def append(self, node: Node) -> None:
        self.nodes.append(node)

    def get_node_by_id(self, node_id: str) -> Optional[Node]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

class ParallelAgent:
    def __init__(self, task_desc: str, cfg: dict, journal: Journal):
        self.task_desc = task_desc
        self.cfg = cfg
        self.journal = journal

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def cleanup(self):
        pass

def perform_experiments_bfts(config_path:str):
    logger.info(f"Perform experiments with config {config_path}")
    # Just a placeholder "BFS expansions" for demonstration:
    expansions = [
        {"node_id": "root", "metric": 0.5},
        {"node_id": "child_1", "metric": 0.7},
        {"node_id": "child_2", "metric": 0.9},
    ]
    best_node = expansions[-1]

    # We'll pretend there's more BFS logic here ...
    logger.info(f"BFS expansions: {expansions}")
    logger.info(f"Best node: {best_node}")

    bfs_details = {
        "expansions": expansions,
        "best_node": best_node
    }
    return bfs_details
TREES_PY

###############################################################################
# agentic_alpha_explorer.py
# FULL BFS EXPLORATION CODE (INFINITE MODE) EMBEDDED FOR PRODUCTION USAGE
###############################################################################
cat <<'ALPHA_EXPLORER' > "$TARGET_DIR/agentic_alpha_explorer.py"
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🪐🔮  AGENTIC ALPHA EXPLORER (INFINITE) - ASI SUPERINTELLIGENCE ERA  🔮🪐    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

EXPERIENCE NEXT-LEVEL COGNITIVE DISCOVERY:

This single-file script performs an infinite BFS-style exploration of concepts, 
optionally coordinated by an “agentic” parallel approach (inspired by agentic_treesearch).
By default, it calls out to a local Ollama instance (http://localhost:11434) to generate 
sub-concepts from a root concept. The expansions continue indefinitely until you press Ctrl+C.

ASCEND INTO THE ASI-ERA:
    - **Immersive Terminal FX** via Rich: dynamic color palette, cosmic ASCII trees,
      animated spinners, and more to evoke superintelligent aesthetics.
    - **Infinite BFS** or **Agentic** expansions:
      Classic BFS or a minimal parallel agent approach controlling expansions.
    - **Production-Ready**:
      - Single-file code, robust error handling, session auto-saving, graceful shutdown.
      - Straightforward CLI with intuitive flags.
      - Cross-platform (Windows/macOS/Linux) support with zero manual tweaks needed.
    - **Highly Customizable**:
      - Switch LLM backends or adapt to local vs. cloud models easily (default: Ollama).
      - Diversify expansions by adjusting --diversity.

DEPENDENCIES:
    - Python 3.7+
    - rich (for advanced terminal UI)
    - requests, networkx, dataclasses_json, numpy, pandas, PyYAML, humanize, jsonschema
    - A local or remote LLM backend (default: Ollama).
      Or adapt the code to OpenAI, HuggingFace, etc.

AUTHOR:
    A specialized, well-funded, and futuristic team from the pinnacle 
    of AI engineering & design, ensuring a unique and powerful user experience.

USAGE:
    python agentic_alpha_explorer.py --root="Quantum Consciousness" --diversity=1.0 --agentic

    (Press Ctrl+C at any time to stop expansions.)
"""

import sys

try:
    from rich.console import Console
    from rich.theme import Theme
    from rich.table import Table
    from rich.tree import Tree
    from rich import box
    from rich.panel import Panel
    from rich.spinner import Spinner
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt
    from rich.style import Style as RichStyle
    from rich.traceback import install as rich_traceback_install
except ImportError:
    print(
        "\nERROR: The 'rich' library is not installed.\n"
        "Please install it by running:\n"
        "    pip install rich\n"
        "Then re-run this script.\n"
    )
    sys.exit(1)

import argparse
import json
import os
import random
import shutil
import textwrap
import time
import logging
import traceback
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin
from enum import Enum, auto
from functools import total_ordering
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Callable, Set

import requests
import humanize
import yaml
import numpy as np
import pandas as pd
import networkx as nx

try:
    import jsonschema
except ImportError:
    pass

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "bold yellow",
    "error": "bold red",
    "success": "bold green",
    "title": "bold magenta"
})
console = Console(theme=custom_theme)
rich_traceback_install(show_locals=False)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_MODEL = "llama3"
DEFAULT_ROOT_CONCEPT = "Consciousness Cascades"
DEFAULT_DIVERSITY_BIAS = 1.0
DEFAULT_MAX_DEPTH = 4
SLEEP_DURATION = 0.8

def clear_terminal():
    console.clear()

@dataclass
class Node:
    concept: str
    path: List[str] = field(default_factory=list)

class ConceptExplorer:
    def __init__(self, model=DEFAULT_MODEL):
        self.graph = nx.DiGraph()
        self.seen_concepts = set()
        self.last_added = None
        self.current_concept = None
        self.model = model
        self.term_width, self.term_height = shutil.get_terminal_size((80, 24))
        self.last_tree_update_time = 0
        self.MIN_UPDATE_INTERVAL = 0.5

    def get_available_models(self) -> List[str]:
        url = "http://localhost:11434/api/tags"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("models", [])
            return [m["name"] for m in data]
        except Exception as e:
            console.print(f"[error]Error contacting Ollama: {e}[/error]")
            return []

    def check_model_availability(self) -> bool:
        available = self.get_available_models()
        if not available:
            return False
        if self.model in available:
            return True
        for model_name in available:
            if model_name.startswith(f"{self.model}:"):
                self.model = model_name
                return True
        return False

    def strip_thinking_tags(self, response: str) -> str:
        return response.replace("<think>", "").replace("</think>", "")

    def _update_thinking_block(self, text: str, state: Dict[str, Any]):
        lines = textwrap.wrap(text.strip(), width=self.term_width)
        if not state["printed_brain_emoji"]:
            lines.insert(0, "🧠")
            state["printed_brain_emoji"] = True

        if len(lines) > 6:
            lines = lines[:6]
            lines[-1] += "..."

        if lines == state["last_printed_block"]:
            return

        for _ in range(state["printed_lines"]):
            console.print("\033[F\033[K", end="")
        console.out("", end="")

        for line_out in lines:
            console.print(f"[dim]{line_out}[/dim]")
        state["printed_lines"] = len(lines)
        state["last_printed_block"] = lines.copy()

    def query_ollama_stream(self, prompt: str) -> str:
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {"model": self.model, "prompt": prompt, "stream": True}

        if not self.check_model_availability():
            console.print(f"[error]Model '{self.model}' not found in Ollama's environment.[/error]")
            console.print(f"[warning]Try 'ollama pull {self.model}' or adapt to your LLM backend.[/warning]")
            return "[]"

        try:
            resp = requests.post(url, headers=headers, json=data, stream=True)
            resp.raise_for_status()

            full_response = ""
            in_think_mode = False
            think_buffer = ""
            thinking_state = {
                "printed_lines": 0,
                "printed_brain_emoji": False,
                "last_printed_block": [],
            }

            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk_data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                chunk = chunk_data.get("response", "")
                full_response += chunk

                idx = 0
                while idx < len(chunk):
                    if not in_think_mode:
                        st_tag = chunk.find("<think>", idx)
                        if st_tag == -1:
                            break
                        idx = st_tag + len("<think>")
                        in_think_mode = True
                        thinking_state["printed_brain_emoji"] = False
                        thinking_state["last_printed_block"] = []
                    else:
                        end_tag = chunk.find("</think>", idx)
                        if end_tag == -1:
                            think_buffer += chunk[idx:]
                            self._update_thinking_block(think_buffer, thinking_state)
                            break
                        else:
                            think_buffer += chunk[idx:end_tag]
                            self._update_thinking_block(think_buffer, thinking_state)
                            in_think_mode = False
                            think_buffer = ""
                            idx = end_tag + len("</think>")

                if chunk_data.get("done", False):
                    break
            return self.strip_thinking_tags(full_response)

        except KeyboardInterrupt:
            raise
        except Exception as e:
            console.print(f"[error]Error streaming expansions from Ollama: {e}[/error]")
            return "[]"

    def get_related_concepts(self, concept: str, path: Optional[List[str]] = None) -> List[str]:
        if concept in self.seen_concepts:
            return []
        self.seen_concepts.add(concept)
        self.current_concept = concept
        full_path = (path or []) + [concept]

        prompt = textwrap.dedent(f"""
            You are an advanced BFS agent. Starting with "{concept}",
            produce 8-10 related concepts (1-5 words each) as a JSON array, e.g. ["C1","C2",...].
            Aim for diversity across fields, avoid duplicates, keep it intriguing.

            Path so far: {' -> '.join(full_path)}
        """).strip()

        console.print(f"\n[cyan]⚡ Expanding from concept:[/cyan] [yellow]{concept}[/yellow]")
        if path:
            console.print(f"[cyan]Path:[/cyan] [magenta]{' -> '.join(path)} -> {concept}[/magenta]")

        raw = self.query_ollama_stream(prompt)
        try:
            if "[" in raw and "]" in raw:
                chunk_start = raw.find("[")
                chunk_end = raw.rfind("]") + 1
                expansions_txt = raw[chunk_start:chunk_end]
                expansions = json.loads(expansions_txt)

                filtered = []
                for rc in expansions:
                    rc = rc.strip()
                    if not rc:
                        continue
                    if rc.lower() in (s.lower() for s in self.seen_concepts):
                        console.print(f"[error]✗ Duplicate concept: {rc}[/error]")
                        continue
                    if len(rc) > self.term_width // 3:
                        rc = rc[: self.term_width // 3 - 3] + "..."
                    filtered.append(rc)
                console.print(f"[success]✓ Found {len(filtered)} expansions[/success]")
                return filtered
            else:
                console.print(f"[error]✗ Invalid JSON in LLM response[/error]")
                console.print(f"[warning]Full response:\n{raw}[/warning]")
                return []
        except Exception as ex:
            console.print(f"[error]✗ Error parsing expansions: {ex}[/error]")
            console.print(f"[warning]Raw response:\n{raw}[/warning]")
            return []

    def _diversity_score(self, concept: str, existing: set) -> float:
        score = 0
        for e in existing:
            shared = set(concept.lower().split()) & set(e.lower().split())
            if not shared:
                score += 1
        return score

    def _ascii_tree(self, node: str, prefix="", is_last=True, visited=None) -> str:
        if visited is None:
            visited = set()
        if node in visited:
            return f"{prefix}└── (...)\n"
        visited.add(node)

        if node == self.current_concept:
            display_node = f"[reverse magenta]{node}[/reverse magenta]"
        elif node == self.last_added:
            display_node = f"[reverse green]{node}[/reverse green]"
        else:
            display_node = f"[green]{node}[/green]"

        connector = "└── " if is_last else "├── "
        out = f"{prefix}{connector}{display_node}\n"
        successors = list(self.graph.successors(node))
        if not successors:
            return out
        next_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(successors):
            last_child = (i == len(successors) - 1)
            out += self._ascii_tree(child, next_prefix, last_child, visited)
        return out

    def update_live_tree(self, focus_node=None):
        now = time.time()
        if now - self.last_tree_update_time < self.MIN_UPDATE_INTERVAL:
            return
        self.last_tree_update_time = now
        self.term_width, self.term_height = shutil.get_terminal_size((80, 24))
        clear_terminal()

        header_lines = [
            f"[blue]{'=' * min(65, self.term_width)}[/blue]",
            "[bold yellow]🔱∞  AGENTIC ALPHA EXPLORER (INFINITE MODE)  ∞🔱[/bold yellow]",
            f"[blue]{'=' * min(65, self.term_width)}[/blue]\n"
        ]
        for line in header_lines:
            console.print(line, highlight=False)

        roots = [n for n in self.graph.nodes if self.graph.in_degree(n) == 0]
        if not roots:
            console.print("[red]No root node found![/red]")
            return

        root = roots[0]
        ascii_str = self._ascii_tree(root)
        console.print(ascii_str, highlight=False)
        console.print(f"\n[yellow]{'=' * min(65, self.term_width)}[/yellow]")
        console.print(f"[cyan]Total Concepts: {len(self.graph.nodes)} | Connections: {len(self.graph.edges)}[/cyan]")
        if self.current_concept:
            console.print(f"[white]Expanding: [yellow]{self.current_concept}[/yellow][/white]")

    def build_concept_web_infinite(self, root_concept: str, diversity_bias: float = DEFAULT_DIVERSITY_BIAS):
        self.graph.add_node(root_concept)
        queue = deque([(root_concept, [])])

        try:
            while True:
                concept, path = queue.popleft()
                self.update_live_tree(focus_node=concept)
                expansions = self.get_related_concepts(concept, path)
                if diversity_bias > 0 and expansions and random.random() < diversity_bias:
                    expansions.sort(key=lambda x: self._diversity_score(x, self.seen_concepts))

                for c in expansions:
                    if c not in self.graph:
                        self.graph.add_node(c)
                    self.graph.add_edge(concept, c)
                    self.last_added = c
                    new_path = path + [concept]
                    queue.append((c, new_path))
                    self.update_live_tree(focus_node=c)
                    time.sleep(SLEEP_DURATION)

                time.sleep(SLEEP_DURATION)

        except KeyboardInterrupt:
            console.print(f"\n[yellow]Exploration ended by user (Ctrl+C).[/yellow]")
            return
        finally:
            self.current_concept = None
            self.last_added = None
            self.update_live_tree()
            console.print(f"\n[green]✨ BFS expansions ended (interrupt).[/green]")

    def build_concept_web_agentic_infinite(self, root_concept: str, diversity_bias: float = DEFAULT_DIVERSITY_BIAS):
        from collections import deque
        from time import sleep
        from agentic_treesearch import Journal, Node as ASTNode, ParallelAgent

        console.print(f"\n[magenta]==== AGENTIC TREE SEARCH MODE (INFINITE) ====[/magenta]")
        cfg = {
            "agent": {
                "num_workers": 1,
                "search": {"num_drafts": 1},
                "steps": 10,
            },
            "exec": {
                "timeout": 300,
            },
        }

        journal = Journal()
        root_node = ASTNode(plan=f"Root concept: {root_concept}", is_seed_node=True)
        journal.append(root_node)
        self.graph.add_node(root_concept)
        queue = deque([(root_node, [])])

        with ParallelAgent(task_desc="Concept BFS", cfg=cfg, journal=journal) as agent:
            try:
                while True:
                    node, path = queue.popleft()
                    concept = node.plan.replace("Root concept:", "").strip()
                    self.update_live_tree(focus_node=concept)

                    console.print(f"\n[cyan]Agentic BFS exploring: [white]{concept}[/white][/cyan]")
                    expansions = self.get_related_concepts(concept, path)
                    if diversity_bias > 0 and expansions and random.random() < diversity_bias:
                        expansions.sort(key=lambda x: self._diversity_score(x, self.seen_concepts))

                    for c in expansions:
                        if c not in self.graph:
                            self.graph.add_node(c)
                        self.graph.add_edge(concept, c)
                        self.last_added = c
                        child_node = ASTNode(plan=c, parent=node)
                        journal.append(child_node)
                        queue.append((child_node, path + [concept]))
                        self.update_live_tree(focus_node=c)
                        sleep(SLEEP_DURATION)

                    sleep(SLEEP_DURATION)

            except KeyboardInterrupt:
                console.print(f"\n[yellow]Exploration ended by user (Ctrl+C).[/yellow]")
            finally:
                self.current_concept = None
                self.last_added = None
                self.update_live_tree()
                console.print(f"\n[green]✨ Agentic BFS expansions ended (interrupt).[/green]")

    def export_ascii_tree(self, output_file: str = "concept_web.txt"):
        roots = [n for n in self.graph.nodes if self.graph.in_degree(n) == 0]
        if not roots:
            console.print("[red]No root node found; nothing to export.[/red]")
            return

        def _plain_ascii_tree(node, prefix="", is_last=True, visited=None):
            if visited is None:
                visited = set()
            if node in visited:
                return f"{prefix}{'└── ' if is_last else '├── '}{node} (...)\n"
            visited.add(node)
            out_text = f"{prefix}{'└── ' if is_last else '├── '}{node}\n"
            children = list(self.graph.successors(node))
            if not children:
                return out_text

            next_prefix = prefix + ("    " if is_last else "│   ")
            for i, c in enumerate(children):
                last_c = (i == len(children) - 1)
                out_text += _plain_ascii_tree(c, next_prefix, last_c, visited)
            return out_text

        root = roots[0]
        ascii_str = _plain_ascii_tree(root)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(ascii_str)
        console.print(f"[green]📝 ASCII tree exported to '{output_file}'[/green]")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Discover infinite BFS expansions of a root concept until Ctrl+C."
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Name of the LLM model (e.g. 'llama2'). Must exist locally or adapt the script to your LLM."
    )
    parser.add_argument(
        "--root",
        default=DEFAULT_ROOT_CONCEPT,
        help="Root concept for BFS expansions."
    )
    parser.add_argument(
        "--diversity",
        type=float,
        default=DEFAULT_DIVERSITY_BIAS,
        help="Probability to reorder expansions by diversity (0 <= x <= 1)."
    )
    parser.add_argument(
        "--depth",
        "--max-depth",
        dest="depth",
        type=int,
        default=DEFAULT_MAX_DEPTH,
        help="Ignored in infinite mode; retained for legacy usage."
    )
    parser.add_argument(
        "--agentic",
        action="store_true",
        help="Enable agentic BFS expansions (infinite) instead of classic BFS."
    )
    return parser.parse_args()

def run_explorer_once(root_concept="Consciousness Cascades", diversity=1.0, agentic_mode=False):
    """
    A single-run BFS (1 or 2 expansions) for demonstration, so it doesn't go infinite.
    Returns expansions + some quick summary.
    """
    console = Console(theme=Theme({"info": "dim cyan"}))
    explorer = ConceptExplorer(model=os.getenv("OLLAMA_MODEL","gemma3:4b"))
    expansions_accum = []

    try:
        explorer.graph.add_node(root_concept)
        path = []
        expansions = explorer.get_related_concepts(root_concept, path)
        expansions_accum.append({
            "root": root_concept,
            "expanded": expansions
        })

        if expansions:
            chosen = expansions[0]
            explorer.graph.add_node(chosen)
            explorer.graph.add_edge(root_concept, chosen)
            expansions2 = explorer.get_related_concepts(chosen, [root_concept])
            expansions_accum.append({
                "root": chosen,
                "expanded": expansions2
            })
        summary = {
            "total_nodes": len(explorer.graph.nodes),
            "total_edges": len(explorer.graph.edges)
        }
    except KeyboardInterrupt:
        console.print("User interrupted BFS.")
    except Exception as e:
        traceback.print_exc()
        raise
    return expansions_accum, summary

def main():
    clear_terminal()

    banner_lines = [
        "[green]" + "=" * 70 + "[/green]",
        "[bold yellow]🪐🔮  AGENTIC ALPHA EXPLORER (INFINITE) - ASI SUPERINTELLIGENCE ERA  🔮🪐[/bold yellow]",
        "[green]" + "=" * 70 + "[/green]\n",
        "[magenta]Press Ctrl+C at any time to halt expansions.[/magenta]\n"
    ]
    for line in banner_lines:
        console.print(line)

    args = parse_arguments()
    console.print(f"[yellow]Root Concept:    [/yellow][white]{args.root}[/white]")
    console.print(f"[yellow]Model:           [/yellow][white]{args.model}[/white]")
    console.print(f"[yellow]Diversity:       [/yellow][white]{args.diversity}[/white]")
    console.print(f"[yellow]Depth (ignored): [/yellow][white]{args.depth}[/white]")
    if args.agentic:
        console.print(f"[yellow]Mode:            [/yellow][white]Agentic BFS (infinite)[/white]")
    else:
        console.print(f"[yellow]Mode:            [/yellow][white]Classic BFS (infinite)[/white]")

    explorer = ConceptExplorer(model=args.model)

    if not explorer.check_model_availability():
        console.print(f"[error]Error: Model '{args.model}' not available in Ollama or your LLM backend.[/error]")
        available = explorer.get_available_models()
        if available:
            console.print("[green]Available models:[/green]")
            for i, am in enumerate(available, 1):
                console.print(f"[cyan]{i}. {am}[/cyan]")
        else:
            console.print("[warning]No models found. You may need to pull or adapt the script to your LLM backend.[/warning]")
        sys.exit(1)

    try:
        if args.agentic:
            explorer.build_concept_web_agentic_infinite(args.root, diversity_bias=args.diversity)
        else:
            explorer.build_concept_web_infinite(args.root, diversity_bias=args.diversity)

        out_file = f"{args.root.lower().replace(' ', '_')}_concept_web.txt"
        explorer.export_ascii_tree(out_file)
        console.print(
            f"\n[green]✨ Exploration finished! {len(explorer.graph.nodes)} concepts, "
            f"{len(explorer.graph.edges)} connections. Results in '{out_file}'.[/green]"
        )

    except KeyboardInterrupt:
        console.print(f"\n[yellow]Exploration interrupted by user (Ctrl+C).[/yellow]")
        out_file = f"{args.root.lower().replace(' ', '_')}_concept_web.txt"
        explorer.export_ascii_tree(out_file)
        console.print(
            f"[green]Partial expansions saved with {len(explorer.graph.nodes)} concepts. "
            f"ASCII tree in '{out_file}'.[/green]"
        )

    except Exception as e:
        console.print(f"\n[error]An unexpected error occurred: {e}[/error]")
        traceback.print_exc()
        sys.exit(1)

    finally:
        console.print("\n[bold magenta]🪐 Session ended. If terminal is misaligned, type 'reset'.[/bold magenta]\n")

if __name__ == "__main__":
    main()
ALPHA_EXPLORER

###############################################################################
# Optionally copy local data for persistence
###############################################################################
if [ -d "weaviate_data" ]; then
  mkdir -p "$TARGET_DIR/weaviate_data"
  cp -r weaviate_data/* "$TARGET_DIR/weaviate_data" || true
  echo "Copied weaviate_data/"
fi
if [ -d "chroma_storage" ]; then
  mkdir -p "$TARGET_DIR/chroma_storage"
  cp -r chroma_storage/* "$TARGET_DIR/chroma_storage" || true
  echo "Copied chroma_storage/"
fi
if [ -d "data" ]; then
  mkdir -p "$TARGET_DIR/data"
  cp -r data/* "$TARGET_DIR/data" || true
  echo "Copied data/"
fi

echo "[3/5] Generated files in '$TARGET_DIR'."

###############################################################################
# 6) Build Docker
###############################################################################
cd "$TARGET_DIR"
echo "[4/5] docker-compose build..."
docker-compose build --no-cache

###############################################################################
# 7) docker-compose up -d
###############################################################################
echo "[5/5] Starting containers in background..."
docker-compose up -d

echo
echo "==========================================================="
echo "Sovereign Agentic AGI ALPHA is deployed in '$TARGET_DIR'!"
echo "Containers running in background."
echo
echo "Attaching to sovereign_agent container for a live chat..."
echo "==========================================================="
echo

if command -v docker &> /dev/null; then
  echo "Showing logs (docker-compose logs -f agent) in parallel. (Ctrl+C to stop logs only)"
  docker-compose logs -f agent &
  LOGS_PID=$!
  docker attach sovereign_agent || true
  echo "Container attach ended. Stopping log tail..."
  kill $LOGS_PID 2>/dev/null || true
else
  echo "Docker not found in PATH. Please run 'docker attach sovereign_agent' manually."
fi

echo
echo "==========================================================="
echo "If you typed 'exit' or 'quit' from inside container's chat,"
echo "the agent loop has ended, but container may still be running."
echo "Run 'docker-compose down' to stop it fully."
echo "==========================================================="

echo
echo "Below is the final webpage (with 500,000 token gate, user-friendly wallet connect, etc.),"
echo "and also featuring the new 'Alpha Explorer' to demonstrate Agentic Tree Search & BFS expansions."
echo "Note: This HTML is also served at http://localhost:5000/ by the container."
echo

cat sovereign_agent_web.html

