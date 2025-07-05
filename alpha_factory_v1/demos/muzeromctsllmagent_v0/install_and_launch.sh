#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# install_and_launch.sh
#
# Final "One-Click" script to install and launch the
# SOVEREIGN AGENTIC AGI ALPHA AGENT (MuZero + MCTS + RAG + LLM + Solana gating).
#

set -e

USE_DOCKER=false  # If true, we'll use Docker instead of local venv

echo "[STEP 1] Checking system..."

if ! command -v python3 &>/dev/null; then
  echo "Python3 not found. Please install it."
  exit 1
fi

if [[ "$OSTYPE" == "darwin"* ]] && ! command -v brew &>/dev/null; then
  echo "Homebrew not found (macOS). Please install from https://brew.sh"
  exit 1
fi

if [ "$USE_DOCKER" = true ]; then
  if ! command -v docker &>/dev/null; then
    echo "Docker not found! Install Docker or set USE_DOCKER=false."
    exit 1
  fi
  echo "[DOCKER MODE] Creating Dockerfile..."

  cat <<'EOF' > Dockerfile.sovereign
FROM python:3.9-slim

RUN apt-get update && apt-get install -y git curl && apt-get clean

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py /app/
CMD ["python","agent.py"]
EOF

  # Minimal Python deps
  cat <<'EOF' > requirements.txt
numpy
torch
protobuf==3.20.*
deepseek-r1
text-embedding
solana
EOF

  # The entire agent code
  cat <<'EOF' > agent.py
import os
import sys
import random
import math
import subprocess
import torch
import torch.nn as nn
from solana.publickey import PublicKey
from solana.rpc.api import Client

# For demonstration, user can pass MOCK_SOLANA_PUBKEY to check real balance
TOKEN_MINT = "tWKHzXd5PRmxTF5cMfJkm2Ua3TcjwNNoSRUqx6Apump"
REQUIRED_BALANCE = 1000000
RPC_URL = "https://solana-mainnet.g.alchemy.com/v2/KT1RV46Eoje4kL-SC2pSANHTVm6-wgwF"

def ensure_token_holding():
    key = os.environ.get("MOCK_SOLANA_PUBKEY","")
    if not key:
        print("[INFO] No public key set => skipping real check. (Set MOCK_SOLANA_PUBKEY to do a real check.)")
        return
    client = Client(RPC_URL)
    resp = client.get_token_accounts_by_owner(
        PublicKey(key),
        {"mint":PublicKey(TOKEN_MINT)}
    )
    if "result" not in resp or not resp["result"]["value"]:
        print("[ERROR] No $AGIALPHA token found. Access Denied.")
        sys.exit(1)
    total = 0.0
    for acc in resp["result"]["value"]:
        info = acc["account"]["data"]["parsed"]["info"]["tokenAmount"]
        total += float(info["uiAmount"])
    if total < REQUIRED_BALANCE:
        print(f"[ERROR] You hold {total} $AGIALPHA (<1,000,000). Denied.")
        sys.exit(1)
    print(f"[OK] You hold {total} $AGIALPHA ≥ 1,000,000. Gate passed.")

# RAG
class RagSearcher:
    def __init__(self):
        pass
    def retrieve(self, query:str):
        return "some relevant info from deepseek-r1"

# LLM
class OllamaLLM:
    def __init__(self, model="llama2.13b", searcher=None):
        self.model = model
        self.searcher = searcher
    def generate_proposals(self, prompt, num_options=3):
        snippet = self.searcher.retrieve(prompt)
        combined = prompt + "\nContext:\n" + snippet
        try:
            out = subprocess.check_output([
                "ollama","-m", self.model,"-p", combined
            ]).decode("utf-8")
            # We'll just mock parse:
            return [f"Strategy {i+1} from LLM+RAG" for i in range(num_options)]
        except Exception as e:
            print("[WARN] ollama call failed:", e)
            return [f"Fallback Strategy {i+1}" for i in range(num_options)]

# MuZero
class RepresentationNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(512,256), nn.ReLU(), nn.Linear(256,128))
    def forward(self,x):
        return self.net(x)

class DynamicsNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(128+1,128), nn.ReLU(), nn.Linear(128,128))
        self.reward_head = nn.Linear(128,1)
    def forward(self, state, action):
        c = torch.cat([state, action], dim=-1)
        h = self.net(c)
        r = self.reward_head(h)
        return h, r

class PredictionNetwork(nn.Module):
    def __init__(self, action_size=3):
        super().__init__()
        self.policy = nn.Linear(128, action_size)
        self.value = nn.Linear(128,1)
    def forward(self, s):
        pol = self.policy(s)
        val = self.value(s)
        return pol,val

class MuZeroModel(nn.Module):
    def __init__(self, action_size=3):
        super().__init__()
        self.repr = RepresentationNetwork()
        self.dyn = DynamicsNetwork()
        self.pred = PredictionNetwork(action_size)
    def initial_inference(self, obs):
        s0 = self.repr(obs)
        p,v = self.pred(s0)
        return s0,p,v
    def recurrent_inference(self, state, action):
        sn,r = self.dyn(state, action)
        p,v = self.pred(sn)
        return sn,r,p,v

# MCTS
class MCTSNode:
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = {}
        self.N=0; self.W=0; self.Q=0
        self.P={}
class MCTSPlanner:
    def __init__(self, model, c_puct=1.0):
        self.model=model
        self.c_puct=c_puct
    def search(self, root_state, actions, steps=30):
        root = MCTSNode(root_state)
        prior_prob = 1/len(actions)
        for a in actions:
            root.P[a] = prior_prob
        for _ in range(steps):
            leaf = self._select(root)
            if leaf is None: break
            val = self._simulate(leaf)
            self._backprop(leaf, val)
        best_a = max(actions, key=lambda a: root.children.get(a,MCTSNode(None)).N)
        return best_a
    def _select(self,node):
        best_a, best_score = None, -999
        for a, p in node.P.items():
            if a not in node.children:
                return node
            c = node.children[a]
            U = self.c_puct*p*math.sqrt(node.N+1)/(1+c.N)
            score = c.Q+U
            if score>best_score:
                best_score=score; best_a=a
        return node.children[best_a]
    def _simulate(self,node):
        # Real code would do MuZero inference
        return random.random()
    def _backprop(self,node,val):
        cur=node
        while cur:
            cur.N+=1; cur.W+=val
            cur.Q = cur.W/cur.N
            cur=cur.parent

def main():
    print("=== SOVEREIGN AGENTIC AGI ALPHA AGENT ===")
    ensure_token_holding()

    # RAG + LLM
    searcher = RagSearcher()
    llm = OllamaLLM(searcher=searcher)
    # MuZero + MCTS
    mu = MuZeroModel(action_size=3)
    planner = MCTSPlanner(mu)

    goal = input("Enter your goal: ").strip() or "Default goal"
    print(f"[AGENT] Goal: {goal}")

    # LLM proposals
    proposals = llm.generate_proposals("Goal: "+goal, 3)
    print("[AGENT] Proposed strategies:")
    for i,p in enumerate(proposals):
        print(f"  {i+1}. {p}")

    # MCTS
    obs = torch.rand(1,512)
    acts = list(range(len(proposals)))
    best_act = planner.search(obs, acts, steps=30)
    chosen = proposals[best_act]
    print(f"[AGENT] MCTS best plan => {chosen}")

    confirm = input("Execute plan? (y/n): ")
    if confirm.lower().startswith('y'):
        print("[AGENT] Executing (mock) ... Done!")
    else:
        print("[AGENT] Cancelled.")
    print("=== COMPLETE ===")

if __name__=="__main__":
    main()
EOF

  echo "[*] Building Docker image 'sovereign_agi_alpha'..."
  docker build -f Dockerfile.sovereign -t sovereign_agi_alpha .
  echo "[*] Launching container..."
  docker run -it --rm sovereign_agi_alpha

  exit 0

else
  # LOCAL VENV approach
  echo "[STEP 2] Creating local python venv..."

  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
  fi
  # shellcheck source=/dev/null
  source .venv/bin/activate

  cat <<'EOF' > requirements.txt
numpy
torch
protobuf==3.20.*
deepseek-r1
text-embedding
solana
EOF

  pip install --upgrade pip
  pip install -r requirements.txt

  # On macOS, install ollama if missing:
  if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v ollama &>/dev/null; then
      echo "[MacOS] Installing ollama..."
      brew tap jmorganca/ollama
      brew install ollama
    fi
  fi

  echo "[STEP 3] Generating agent code..."

  cat <<'EOF' > agent.py
import os
import sys
import random
import math
import subprocess
import torch
import torch.nn as nn

from solana.publickey import PublicKey
from solana.rpc.api import Client

TOKEN_MINT = "tWKHzXd5PRmxTF5cMfJkm2Ua3TcjwNNoSRUqx6Apump"
REQUIRED_BALANCE = 1000000
RPC_URL = "https://solana-mainnet.g.alchemy.com/v2/KT1RV46Eoje4kL-SC2pSANHTVm6-wgwF"

def ensure_token_holding():
    user_key = os.environ.get("MOCK_SOLANA_PUBKEY","")
    if not user_key:
        print("[INFO] No user pubkey => skipping real check. (Set MOCK_SOLANA_PUBKEY to do real gating.)")
        return
    client = Client(RPC_URL)
    resp = client.get_token_accounts_by_owner(
        PublicKey(user_key),
        {"mint": PublicKey(TOKEN_MINT)}
    )
    if "result" not in resp or not resp["result"]["value"]:
        print("[ERROR] No $AGIALPHA found. Access Denied.")
        sys.exit(1)
    total=0
    for val in resp["result"]["value"]:
        info = val["account"]["data"]["parsed"]["info"]["tokenAmount"]
        total += float(info["uiAmount"])
    if total<REQUIRED_BALANCE:
        print(f"[ERROR] Only {total} $AGIALPHA (<1,000,000). Denied.")
        sys.exit(1)
    print(f"[OK] Gating passed. You hold {total} $AGIALPHA≥1,000,000.")

class RagSearcher:
    def retrieve(self, query):
        return "some relevant deepseek-r1 snippet"

class OllamaLLM:
    def __init__(self, model="llama2.13b",searcher=None):
        self.model=model
        self.searcher=searcher
    def generate_proposals(self,prompt,num_options=3):
        snippet = self.searcher.retrieve(prompt)
        combined = prompt+"\nContext:\n"+snippet
        try:
            out = subprocess.check_output(["ollama","-m",self.model,"-p",combined]).decode("utf-8")
            return [f"Strategy {i+1} from LLM+RAG" for i in range(num_options)]
        except Exception as e:
            print("[WARN] ollama call fail:", e)
            return [f"Fallback {i+1}" for i in range(num_options)]

class RepresentationNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(512,256), nn.ReLU(), nn.Linear(256,128))
    def forward(self,x):
        return self.net(x)

class DynamicsNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(128+1,128),nn.ReLU(),nn.Linear(128,128))
        self.reward_head = nn.Linear(128,1)
    def forward(self, s, a):
        c = torch.cat([s,a], dim=-1)
        h = self.net(c)
        r = self.reward_head(h)
        return h,r

class PredictionNetwork(nn.Module):
    def __init__(self, action_size=3):
        super().__init__()
        self.policy = nn.Linear(128, action_size)
        self.value  = nn.Linear(128,1)
    def forward(self,x):
        p = self.policy(x)
        v = self.value(x)
        return p,v

class MuZeroModel(nn.Module):
    def __init__(self, action_size=3):
        super().__init__()
        self.repr = RepresentationNetwork()
        self.dyn = DynamicsNetwork()
        self.pred = PredictionNetwork(action_size)
    def initial_inference(self,obs):
        s0 = self.repr(obs)
        p,v = self.pred(s0)
        return s0,p,v
    def recurrent_inference(self, state, action):
        sn,r = self.dyn(state, action)
        p,v = self.pred(sn)
        return sn,r,p,v

class MCTSNode:
    def __init__(self, state, parent=None):
        self.state=state
        self.parent=parent
        self.children={}
        self.N=0; self.W=0; self.Q=0
        self.P={}

class MCTSPlanner:
    def __init__(self, model, c_puct=1.0):
        self.model=model
        self.c_puct=c_puct
    def search(self, root_state, possible_actions, steps=30):
        root=MCTSNode(root_state)
        prior=1/len(possible_actions)
        for a in possible_actions:
            root.P[a]=prior
        for _ in range(steps):
            leaf = self._select(root)
            if leaf is None: break
            val = self._simulate(leaf)
            self._backprop(leaf,val)
        best_a = max(possible_actions, key=lambda a: root.children.get(a,MCTSNode(None)).N)
        return best_a
    def _select(self,node):
        best_a,best_score=None,-999
        for a,p in node.P.items():
            if a not in node.children:
                return node
            c=node.children[a]
            U=self.c_puct*p*( (node.N+1)**0.5 )/(1+c.N)
            score=c.Q+U
            if score>best_score:
                best_score=score; best_a=a
        return node.children[best_a]
    def _simulate(self,node):
        # Real code would do MuZero rollouts
        return random.random()
    def _backprop(self,node,value):
        cur=node
        while cur:
            cur.N+=1; cur.W+=value
            cur.Q=cur.W/cur.N
            cur=cur.parent

def main():
    print("=== SOVEREIGN AGENTIC AGI ALPHA AGENT (Local) ===")
    ensure_token_holding()

    searcher = RagSearcher()
    llm = OllamaLLM(searcher=searcher)
    mu = MuZeroModel(action_size=3)
    planner = MCTSPlanner(mu)

    goal = input("Enter your goal: ").strip() or "Default synergy"
    print(f"[AGENT] Goal: {goal}")

    proposals = llm.generate_proposals("Goal: "+goal,3)
    print("[AGENT] Proposed strategies:")
    for i,p in enumerate(proposals):
        print(f"  {i+1}. {p}")

    obs=torch.rand(1,512)
    acts=list(range(len(proposals)))
    best = planner.search(obs, acts, steps=30)
    chosen = proposals[best]
    print(f"[AGENT] => MCTS best plan: '{chosen}'")

    c=input("Execute plan? (y/n): ")
    if c.lower().startswith('y'):
        print("[AGENT] Executing (mock) ... done!")
    else:
        print("[AGENT] Cancelled.")
    print("=== COMPLETE ===")

if __name__=="__main__":
    main()
EOF

  echo "[STEP 4] Launching the agent now..."
  python agent.py
  echo "[DONE] SOVEREIGN AGENTIC AGI ALPHA has completed."
fi

