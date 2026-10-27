[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

<a id="current-runnable-path-1360"></a>

<!-- CURRENT-DEMO:START -->
## Current runnable path — 1.46.1

**Mode:** Supplied-input comparison. Compare your own cross-industry assessments
using explicit priorities, review thresholds and evidence notes. This is a
bounded decision-support calculation, not discovery of verified market opportunities.

**Prerequisites:** Python 3.11–3.13 and installed project dependencies.

After [installation](../README.md#start-locally), run the explicitly synthetic
example, then replace its assessments with your own:

```bash
python -m alpha_factory_v1.demos check cross_industry_alpha_factory
python -m alpha_factory_v1.demos run cross_industry_alpha_factory
python -m alpha_factory_v1.demos.cross_industry_alpha_factory.opportunity_comparison --example
python -m alpha_factory_v1.demos.cross_industry_alpha_factory.opportunity_comparison --input my-opportunities.json > comparison.json
```

The module requires either `--input` or `--example`; it never manufactures
findings when no input is supplied. The catalog uses `--example` and labels the
report `synthetic-example`. Supplied files produce `supplied-input` reports.
No network, credentials, provider, persistent ledger or financial transaction is used.

### Input contract

Copy [opportunities.example.json](opportunities.example.json). The JSON must have
exactly these fields (unknown and duplicate keys are rejected):

- `schema_version`: `cross-industry-input-v1`
- `weights`: `benefit`, `confidence`, `effort`, `risk`, each an integer 0–100;
  at least one weight must be positive
- `constraints`: integer `max_risk` and `min_confidence`, each 0–100
- `opportunities`: 1–100 candidates, each with `id`, `sector`, `opportunity`,
  `benefit`, `confidence`, `effort`, `risk`, and `evidence`

Candidate ratings are integer assessment points 0–100. Larger benefit and
confidence are preferred; smaller effort and risk are preferred. These are
your judgments, not calibrated probabilities or money. Use consistent criteria
across sectors. IDs are unique, 1–64 ASCII letters/digits/underscores/hyphens,
starting with a letter or digit. Sector text is limited to 120 Unicode codepoints,
opportunity text to 500, and evidence to 1–10 references/notes of at most 500
codepoints each. All text must be nonempty and trimmed; control characters and
unpaired surrogates are rejected. Evidence URLs are retained as text, never fetched.
The CLI accepts strict UTF-8 JSON up to 1 MiB; invalid inputs exit 2 with no report.

### Calculation and evidence

Score = (benefit weight × benefit + confidence weight × confidence +
effort weight × (100 − effort) + risk weight × (100 − risk)) / sum of weights.

The report preserves all supplied candidates and evidence. It includes each
weighted contribution, normalized weights, constraints, exclusion reasons,
rank and Pareto status. Scores/contributions round exact nonnegative rational
values half-up to six decimal places; rounded contributions may not sum exactly
to the rounded score. Risk above the maximum or confidence below the minimum
excludes a candidate. Eligible candidates sort by rounded score descending,
then ASCII ID; excluded candidates follow in ID order with null ranks.
`selected_id` is the first eligible ID, or null when all are excluded.
A high score is only a review priority, not authorization to act.

The existing system `core.simulation.mats.pareto_front` computes non-dominated
eligible candidates over (−benefit, −confidence, effort, risk). Equal vectors
are both non-dominated; weights do not alter Pareto membership.
`core.runtime.store.digest` binds the complete input using SHA-256 over sorted,
compact, non-ASCII-escaped UTF-8 JSON. This identifies the assessed input, not
proof of truth. Same input gives the same report, with no timestamps/randomness.
The example ranks routing (74.5), maintenance (73.5), then excluded storage (52.5).
Changing weights or thresholds changes the actual result.

### Compatibility and review boundary

The historical helper retains `--list` and explicit `--sample --seed 42 --no-log`.
Legacy external generation requires explicit `--generate` plus configuration;
it never falls back to canned samples on provider failure. Those unverified
ideas are separate from the offline comparator.
The optional Agents bridge accepts the full input under `supplied`.
The marketplace helper accepts `--input FILE --dry-run` and only queues eligible
ranked candidates when invoked without `--dry-run`; actual queueing is a separate
external action requiring operator approval. Explicit `--sample` is retained.

Original research narratives, assets, flowcharts and deployment scripts below
are preserved as historical/advanced material. They do not expand this tested scope.
Nothing here verifies market data, promises revenue or implements superintelligence.
The linked notebook now runs only the supplied-input comparison and recoverable
unsigned evidence export. Its Python cells are tested locally with network access
blocked; actual hosted Colab deployment remains unqualified. The retained deployment
shell script is historical advanced material, not a recommended quick-start.

<!-- CURRENT-DEMO:END -->

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.

Current demo version: `1.0.0`.


# 👁️ Alpha-Factory v1 — Cross-Industry **AGENTIC α-AGI** Demo

*Out-learn • Out-think • Out-design • Out-strategise • Out-execute*
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/cross_industry_alpha_factory/colab_deploy_alpha_factory_cross_industry_demo.ipynb)

of a real general intelligence. Use at your own risk.

See [CONCEPTUAL_FRAMEWORK.md](CONCEPTUAL_FRAMEWORK.md) for an architecture overview.

> **⚠️ Disclaimer**: This demo is **for research and educational purposes only**. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

---

### 1 · Why we built this
Alpha-Factory stitches together **five flagship agents** (Finance, Biotech, Climate, Manufacturing, Policy) under a
zero-trust, policy-guarded orchestrator. 
It closes the full loop:

> **alpha discovery → uniform real-world execution → continuous self-improvement**

and ships with:

* **Automated curriculum** (Ray PPO trainer + reward rubric) 
* **Uniform adapters** (market data, PubMed, Carbon-API, OPC-UA, GovTrack) 
* **DevSecOps hardening** — SBOM + _cosign_, MCP guard-rails, ed25519 prompt signing 
* Runs **online (OpenAI)** or **offline** via bundled Mixtral-8×7B local-LLM 
* One-command Docker installer **_or_** one-click Colab notebook for non-technical users

The design follows the “AI-GAs” recipe for open-ended systems, 
embraces Sutton & Silver’s “Era of Experience” doctrine, and borrows
MuZero-style model-based search to stay sample-efficient.

---

### 2 · Two-click bootstrap

| Path | Audience | Time | Hardware |
|------|----------|------|----------|
| **Docker script**<br>`deploy_alpha_factory_cross_industry_demo.sh` | dev-ops / prod | 8 min | any Ubuntu with Docker 24 |
| **Colab notebook**<br>`colab_deploy_alpha_factory_cross_industry_demo.ipynb` | analysts / no install | 4 min | free Colab CPU |

The notebook installs dependencies from `../requirements-colab.lock` for a quick setup.

Both flows autodetect `OPENAI_API_KEY`; when absent they inject a **Mixtral 8×7B**
local LLM container so the demo works **fully offline**.

Install the extras from `requirements-demo.txt` if you plan to run
`cross_alpha_discovery_stub.py` or `openai_agents_bridge.py`.

> **Prerequisite**: Docker 24+ with the `docker compose` plugin (or the
> legacy `docker-compose` binary) must be installed.

### Quick Start
```bash
git clone https://github.com/MontrealAI/AGI-Alpha-Agent-v0.git
cd AGI-Alpha-Agent-v0/alpha_factory_v1/demos/cross_industry_alpha_factory
cp .env.example ../../.env  # optional customization
./deploy_alpha_factory_cross_industry_demo.sh
```
The installer writes a random `API_TOKEN` to `.env`; include it in the
`Authorization` header when calling the REST API.
Customize variables like `OPENAI_API_KEY`, `AGENTS_ENABLED`, `PROM_PORT` or
`RAY_PORT` by editing `../../.env` before deployment.

Example `.env` snippet:

```bash
OPENAI_API_KEY=sk-your-key
CROSS_ALPHA_MODEL=gpt-4o-mini
AGENTS_ENABLED="finance_agent biotech_agent climate_agent manufacturing_agent policy_agent"
PROM_PORT=9090
RAY_PORT=8265
AUTO_COMMIT=1
```

> **Run this check before launching** the deploy script or Colab notebook:
```bash
python scripts/check_python_deps.py
python check_env.py --auto-install  # add --wheelhouse <dir> when offline
```
See [docs/OFFLINE_SETUP.md](../../../docs/OFFLINE_SETUP.md) for wheelhouse
instructions.

#### Pre-download Mixtral weights
Pull the 8×7B model once and mount it during deployment:

```bash
docker run --rm -v "$PWD/models:/models" ollama/ollama:0.9.0 pull mixtral:8x7b-instruct
./deploy_alpha_factory_cross_industry_demo.sh --model-path "$PWD/models"
```
The script sets `OLLAMA_MODELS=/models` inside the container so no internet
access is required at runtime.

#### Colab Quick Start
Click the badge above or run:
```bash
open https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/cross_industry_alpha_factory/colab_deploy_alpha_factory_cross_industry_demo.ipynb
```

### Quick Alpha Discovery
Generate offline sample opportunities with:
```bash
python cross_alpha_discovery_stub.py --list
```
Use `--sample -n 3 --seed 42` to log three illustrative picks to
`~/.alpha_factory/cross_alpha_log.json`. External ideas require explicit `--generate`
and configured credentials; provider failure is an error. Use the comparator above for supplied evidence.


### Environment variables
| Variable | Default | Purpose |
|---------|---------|---------|
| `CROSS_ALPHA_LEDGER` | `cross_alpha_log.json` | Output ledger for `cross_alpha_discovery_stub`. |
| `CROSS_ALPHA_MODEL` | `gpt-4o-mini` | Remote model used only with explicit `--generate`. |
| `OPENAI_API_KEY` | _(empty)_ | Credentials for explicit `--generate` only; never used by the comparator. |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | API endpoint. Auto-set to `http://local-llm:11434/v1` when no API key. |
| `OPENAI_TIMEOUT_SEC` | `30` | Request timeout for the OpenAI client. |
| `AGENTS_ENABLED` | `"finance_agent biotech_agent climate_agent manufacturing_agent policy_agent"` | Agents launched by the deploy script. |
| `DASH_PORT` | `9000` | External Grafana port. |
| `PROM_PORT` | `9090` | Prometheus port. |
| `RAY_PORT` | `8265` | Ray dashboard port. |
| `API_TOKEN` | generated | Bearer token for the REST API. |
| `AUTO_COMMIT` | `0` | Set to `1` to auto‑commit generated assets when not in CI. |

Install `filelock` if multiple runs write to the same ledger to ensure atomic updates.

#### Optional libraries
Certain extras unlock additional capabilities:

- `openai` – live idea generation from a remote LLM when `OPENAI_API_KEY` is set.
- `openai_agents` – exposes the Agents SDK bridge via `openai_agents_bridge.py`.
- `filelock` – enables concurrent ledger writes.

Install them all at once with:

```bash
pip install -r requirements-demo.txt
```
The `requirements-demo.txt` file installs these extras, including
`openai>=1.82.0,<2.0` and `openai-agents>=0.0.17`.

or install the packages individually.

### Testing
Run the cross-industry discovery test to ensure the stub works:

```bash
pytest tests/test_cross_alpha_discovery.py tests/test_cross_industry_comparison.py
```

See [tests/README.md](../../../tests/README.md) for environment setup guidance.

### 🤖 OpenAI Agents bridge
Expose the discovery helper via the OpenAI Agents SDK:
```bash
python -m alpha_factory_v1.demos.cross_industry_alpha_factory.openai_agents_bridge
```
The agent registers the tools `list_samples`, `discover_alpha` and `recent_log`.
When Google ADK is installed the bridge auto-registers with the ADK gateway as well.


---

### 3 · Live endpoints after install

| Service | URL (default ports) |
|---------|---------------------|
| Grafana dashboards | `http://localhost:9000` `admin/admin` |
| Prometheus | `http://localhost:9090` |
| Trace-Graph (A2A spans) | `http://localhost:3000` |
| Ray dashboard | `http://localhost:8265` |
| REST orchestrator | `http://localhost:8000` (`GET /healthz`) |

All ports are configurable: set environment variables like `DASH_PORT` or `PROM_PORT` before running the installer. The installer maps `DASH_PORT` (default `9000`) to Grafana's internal port `3000`. The Colab notebook tunnels this external port via `ngrok.connect(DASH_PORT)` so you can view the dashboard remotely.

---

### 4 · Architecture at a glance
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ docker-compose (network: alpha_factory)                   │
│                                       │
│  Grafana ◄── Prometheus ◄── metrics ───────┐                │
│     ▲                 │                │
│ Trace-Graph ◄─ A2A spans ─ Orchestrator ──┴─► Knowledge-Hub (RAG + vec-DB) │
│           ▲      ▲                      │
│           │ ADK RPC  │ REST                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │      Five industry agents (side-car adapters in *italics*)    │ │
│  │ Finance   Biotech   Climate    Mfg.    Policy       │ │
│  │ broker,   *PubMed*   *Carbon*   *OPC-UA*  *GovTrack*     │ │
│  │ factor α  RAG-ranker  intensity   scheduler  bill watch    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```
_Edit the Visio diagram under `assets/diagram_architecture.vsdx`._

---

### 5 · The five flagship agents

| Agent | Core libraries | Live adapter | Reward | Key env vars |
|-------|---------------|--------------|--------|--------------|
| FinanceAgent | `pandas-ta`, `cvxpy` | broker / market-data | Δ P&L − λ·VaR | `BROKER_API_KEY` |
| BiotechAgent | `langchain`, `biopython` | *PubMed* mock | novelty-weighted citations | `PUBMED_EMAIL` |
| ClimateAgent | `prophet` | *carbon-api* mock | − tCO₂eq / $ | `CARBON_API_KEY` |
| ManufacturingAgent | `ortools` | *OPC-UA* bridge | cost-to-produce ↓ | `OPC_HOST` |
| PolicyAgent | `networkx`, `sentence-transformers` | *GovTrack* | sentiment × p(passage) | `GOVTRACK_KEY` |

All inherit `BaseAgent(plan, act, learn)` and register with the orchestrator
via ADK’s `AgentDescriptor`.

---

### 6 · Continuous-learning pipeline (15 min cadence)
1. **Ray RLlib PPO** trainer spins in its own container (`alpha-trainer`).
2. Rewards are computed by `continual/rubric.json` (edit live; hot-reload).
3. Best checkpoint is zipped and `POST /agent/<id>/update_model` → agents swap
  weights **with zero downtime**.
4. CI smoke-tests (`.github/workflows/ci.yml`) validate orchestration on every
  PR; failures block merge.

---

### 7 · Security, compliance & transparency

| Layer | Control | Verification |
|-------|---------|--------------|
| Software Bill of Materials | **Syft** emits SPDX JSON | attested with **cosign** and pushed to the **Rekor** transparency log |
| Policy enforcement | **MCP** side-car runs `redteam.json` deny-rules | unit test: `make test:policy` |
| Prompt integrity | ed25519 signature embedded in every request header | Grafana panel “Signed Prompts %” |
| Container hardening | read-only FS, dropped caps, seccomp | passes *Docker Bench* & *Trivy* |

---

### 8 · Performance & heavy-load benchmarking
A **k6** scenario (`bench/k6_load.js`) and a matching Grafana dashboard are
included. On a 4-core VM the stack sustains **🌩 550 req/s** across agents
with p95 latency < 180 ms.

---

### 9 · Extending & deploying at scale
* **New vertical** → subclass `BaseAgent`, add adapter container, append to
 `AGENTS_ENABLED` in `.env`.
* **Custom LLM** → point `OPENAI_API_BASE` to your endpoint.
* **Kubernetes** → `make helm && helm install alpha-factory chart/`.


### 10 · Troubleshooting
If the setup cell fails with `k6-python` errors, remove the package from `alpha_factory_v1/requirements-colab.txt` before running `pip install`. The load testing step is optional and works without this package.

---

### 11 · Roadmap
* Production Helm chart (HA Postgres + Redis event-bus) 
* Replace mock PubMed / Carbon adapters with real connectors 
* Grafana auto-generated dashboards from OpenTelemetry spans 

Community PRs welcome!

### 12 · Teardown & cleanup
Stop containers and wipe data volumes with:
```bash
docker compose -f alpha_factory_v1/docker-compose.yml down -v
```
To automate this step run `./teardown_alpha_factory_cross_industry_demo.sh`.

---

### References
Clune 2019 · Sutton & Silver 2024 · MuZero 2020 

© 2025 MONTREAL.AI — Apache‑2.0 License
