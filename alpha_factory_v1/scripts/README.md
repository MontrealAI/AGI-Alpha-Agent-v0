[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# `alpha_factory_v1/scripts` — Zero‑to‑Alpha in *One* Command ⚡️

> **Module of [Alpha‑Factory v1 👁️✨](../README.md)** — the multi‑agent, cross‑industry α‑AGI that
> *Out‑learns · Out‑thinks · Out‑designs · Out‑strategises · Out‑executes*

This folder contains the **turn‑key installer** that transforms any Docker‑enabled
machine into a fully running **Alpha‑Factory** — with self‑tests, live trace‑graph
and offline fallback — **in ≈ 60 seconds.**

---

## 🚀 Quick start (default profile)

For an all‑in‑one setup run:

```bash
./scripts/one_click_install.sh
```

This performs the preflight checks and deploys the full stack.

If you prefer to execute the steps manually:

```bash
# 0 · validate prerequisites (Docker, Docker Compose, Git)
python3 scripts/preflight.py

# 1 · make the installer executable
chmod +x scripts/install_alpha_factory_pro.sh

# 2 · launch the stack (clone + build + run + smoke‑test)
./scripts/install_alpha_factory_pro.sh --bootstrap --deploy --open

# 3 · open the UI (auto with --open)
open http://localhost:8088        # Trace‑graph
open http://localhost:8000/docs   # Interactive API
```

> **Cloud‑free?** If `OPENAI_API_KEY` is missing, the installer automatically pulls the
> **Φ‑2** model from Ollama and sets `LLM_PROVIDER=ollama` for you.

---

## 🔑 Installer flags (superset of the legacy builder)

| Flag | Effect | Default |
|------|--------|---------|
| `--all` | Enable UI, trace‑graph and tests | off |
| `--ui / --no-ui` | Force include / exclude React UI | auto (on if TTY) |
| `--trace` | Bundle live WebSocket trace hub | off |
| `--tests` | Copy tests & dev tools into image | off |
| `--no-cache` | Pass `--no-cache` to `docker build` | off |
| `--bootstrap` | Clone repo if `alpha_factory_v1/` absent | off |
| `--deploy` | Build **and** run docker‑compose stack + pytest | off (build‑only) |
| `--alpha <name>` | Pre‑enable finance strategy (e.g. `btc_gld`) | none |
| `--open` | Launch web UI in browser after deploy | off |

**TL;DR:** `--deploy` turns a static image build into a live, self‑tested stack.

---

## 🧐 What the script actually does (Deploy path)

1. **Bootstrap** – shallow‑clones repo when requested.
2. **Hot‑fix** – patches the one failing test until upstream merge lands.
3. **Secrets** – copies `.env.sample` → `.env`; appends local model fallback if no key.
4. **Strategy toggle** – uses `yq` (or `sed`) to switch `config/alpha_factory.yml`.
5. **Compose build** – honours optional `cuda` profile for GPU nodes.
6. **Health check** – runs `pytest -q /app/tests` inside the orchestrator container.
7. **Success banner** with clickable URLs.

All steps are idempotent; re‑running the script is safe.

---

## 🔧 Common Workflows

| Goal | Command |
|------|---------|
| Rebuild backend after code change | `docker compose build backend && docker compose up -d backend` |
| Import latest Grafana dashboard | `python scripts/import_dashboard.py alpha_factory_v1/dashboards/alpha_factory_overview.json` |
| Switch to GPU runtime | `PROFILE=cuda ./scripts/install_alpha_factory_pro.sh --deploy` |
| Follow live logs | `docker compose logs -f orchestrator ui` |
| Clean up containers & volumes | `docker compose down -v --remove-orphans` |

The ``import_dashboard.py`` helper requires ``GRAFANA_TOKEN`` and verifies the
given JSON file exists before uploading.

Run ``python scripts/fetch_assets.py`` to download the Insight browser assets.
When any checksum in ``scripts/fetch_assets.py`` changes, execute
``python scripts/generate_build_manifest.py`` so
``build_assets.json`` stays in sync.

### Updating Browser Assets

When upgrading the Pyodide runtime run the helper then verify the
downloads:

```bash
python scripts/update_pyodide.py 0.28.0
npm --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1 run fetch-assets
python scripts/fetch_assets.py --verify-only
```

This refreshes the checksum values in ``scripts/fetch_assets.py`` and
regenerates ``build_assets.json``. Run ``pre-commit`` and commit the
updated ``fetch_assets.py`` and manifest so the browser demo continues to
build reproducibly.

---

## Offline Setup

When working on an air‑gapped machine build wheels ahead of time and tell
``check_env.py`` where to find them.

1. **Build wheels** from the lock file:
   ```bash
   mkdir -p /media/wheels
   pip wheel -r requirements.lock -w /media/wheels
   pip wheel -r requirements-dev.txt -w /media/wheels
   ```

2. **Run the environment check** using your wheelhouse:
   ```bash
   WHEELHOUSE=/media/wheels AUTO_INSTALL_MISSING=1 \
     python check_env.py --auto-install --wheelhouse /media/wheels
   ```
   When a ``wheels/`` directory exists in the repository root, the setup
   scripts automatically set ``WHEELHOUSE`` for you.

---

## 🛡️ Security & Compliance

* **Secrets stay secret** — `.env` is `.gitignore`‑d; Kubernetes `Secret` template provided.
* **Signed images** — every image pushed by CI is Cosign‑signed and SBOM‑tagged.
* **Health‑checks** — Docker `HEALTHCHECK` keeps orchestrator & UI under watchdog.
* **Governance** — every critical planner step emits an OpenTelemetry span *and* a
  W3C Verifiable Credential (see `backend/governance.py`).

---

## 🤖 CI / GitHub Actions usage

```yaml
      - name: Verify environment
        run: python check_env.py --auto-install --wheelhouse /path/to/wheels
      - name: Build & smoke‑test α‑Factory
        run: |
          chmod +x alpha_factory_v1/scripts/install_alpha_factory_pro.sh
          alpha_factory_v1/scripts/install_alpha_factory_pro.sh --deploy --no-ui
      - name: Run tests
        run: |
          WHEELHOUSE=/path/to/wheels pytest -q
```

*The `--no-ui` flag speeds up CI by skipping the React build.*

---

## 📝 License

MIT — © 2025 [MONTREAL.AI](https://montreal.ai)

> **Run the script, watch the trace‑graph, and out‑think the future.**
