[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Changelog


All notable changes to this project are documented in this file.

## Breaking Changes Policy
Incompatible updates are announced in advance whenever possible and remain deprecated for at least one minor release.
Each release includes a dedicated `### Breaking Changes` section describing removed features or behavioural differences.
Consult that section when upgrading.

## Breaking Changes
Any incompatible API updates will be clearly listed under this heading for each release.
Downstream users should consult this section when upgrading.

- **1.1.0** – `GraphMemory._fallback_query` now returns stub data when both
  Neo4j and NetworkX are missing.
- **1.0.3**
  - `check_env.py` exits with an error if `numpy` or `pandas` are missing unless
    `--allow-basic-fallback` is used.
  - Removed `alpha_asi_world_model_demo_v1.py`.
  - Removed `insight_browser_v1/dist/` from version control; run `npm run build` to regenerate the assets.
## [Unreleased]
### Breaking Changes
- Core modules previously under `src/` now live in `alpha_factory_v1.core`.
- Update imports accordingly.
- Monitoring, governance and archive helpers moved under `alpha_factory_v1.core`.
- `alpha-factory` and `edge_runner.py` now print a short warning before startup.
- Synced `openai`, `openai-agents` and `uvicorn` pins across requirements files
  and clarified why `requests` and `rich` differ between layers.
- `build_gallery_site.sh` and `deploy_gallery_pages.sh` now run
  `scripts/mirror_demo_pages.py` so the GitHub Pages subdirectory mirror stays
  current.
- Documented `API_RATE_LIMIT`, `AGI_ISLAND_BACKENDS` and `ALERT_WEBHOOK_URL`
  environment variables.
- Added [`alpha_factory_v1/core/tools/analyse_backtrack.py`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/core/tools/analyse_backtrack.py) for visualising archive backtracks.
- Documented how to build a wheelhouse for offline installs and updated
  `tests/README.md` with the instructions.
- Added `scripts/build_offline_wheels.sh` to gather wheels for all lock files.
- Added `requests` to `requirements-dev.txt` for parity with other examples.
- Updated `@vitejs/plugin-vue` to version 6 so the Docs workflow builds with Vite 7.
- Removed outdated `OPENAI_CONTEXT_WINDOW` reference from the self-healing repo demo.
- Documented how to add new policies in `POLICY_RUNBOOK.md`.
- Each demo README now clarifies that `__version__` denotes the demo revision, not the overall project release.
- Clarified that `transfer_test.evaluate_agent` is a placeholder returning the archived
  score. Added a simple heuristic in `MetaRefinementAgent` that proposes a longer
  cycle period when logs show slow agent cycles.
- Service worker cache version is now generated dynamically to ensure updates are
  picked up by browsers.
- `scripts/fetch_assets.py` now downloads the Pyodide runtime from the official
  CDN and retrieves GPT-2 weights directly from Hugging Face.
- Added `FETCH_ASSETS_ATTEMPTS` environment variable to control download retries.
- Added `FETCH_ASSETS_BACKOFF` environment variable to adjust retry delay.
- The browser bundle now defaults to the official Web3 Storage CDN. IPFS
  fallback has been removed.
- Fixed internal documentation links so MkDocs builds without warnings.
- The **📦 Browser Size** workflow now caches pip and npm dependencies using
  the built-in features of `actions/setup-python` and `actions/setup-node` so
  repeated runs skip redundant downloads.
- The workflow preinstalls `numpy`, `pandas`, `pytest` and `PyYAML` so the
  environment check passes reliably before running pre-commit.
- Fixed the **Build & Test** GitHub Actions workflow so Docker tags always use
  lowercase repository names. The job now runs only when triggered manually by
  the repository owner.
- Upgraded the Insight demo to **streamlit 1.46** so NumPy 2.x installs cleanly.
 - The Docker image now installs **rustc** and **cargo** to build crates like
   `blake3` on Python 3.13.
 - The workflow pushes version-specific Docker tags `py311`, `py312`, `py313` and
   `py314` for each build and signs all images with cosign.
- `ci.yml` now caches Node dependencies using `cache-dependency-path` so the
  "Dependencies lock file is not found" warning no longer appears.
## [0.1.0-alpha] - 2024-05-01
- Initial alpha release.
- Git tag `v0.1.0-alpha`.
- This tag points at commit `0ff79a4f`.
 - If cloning from a snapshot without tags, recreate it using:
    ```bash
    # Verify the release tag
    git tag -l v0.1.0-alpha
    # Recreate the tag when missing
    ./scripts/create_release_tag.sh HEAD
    git push origin v0.1.0-alpha
    ```
- The package exposes `alpha_factory_v1.__version__ = "0.1.0-alpha"` at this release.

### Breaking Changes
- None.

## [1.1.1] - 2025-08-01
- CI workflow now runs via workflow_dispatch. The pipeline executes lint,
  mypy, the full Pytest matrix, Windows/macOS smoke tests, an offline docs
  build, the Docker build and pushes images on tags.
- Lock files must be regenerated with `pip-compile --allow-unsafe`.
- Requires **Python 3.11–3.13 (<3.14)** and **Node.js 22.17.1**.


## [1.0.3] - 2025-07-10
### Breaking Changes
- `check_env.py` exits with an error if `numpy` or `pandas` are missing unless `--allow-basic-fallback` is used.
- Removed `alpha_asi_world_model_demo_v1.py`.
- Removed `insight_browser_v1/dist/` from version control; run `npm run build` to regenerate the assets.
- Added CI workflow running lint, type checks, tests and Docker build with
  automated image deployment on tags and rollback on failure. Metrics are
  exported via OpenTelemetry and can be viewed in Grafana or the Streamlit
  dashboard.
- Clarified that `numpy` and `pandas` are required for realistic results and
  `check_env.py` now errors if they are missing unless `--allow-basic-fallback`
  is provided.
- Documented `ALPHA_ASI_*` demo variables in README and AGENTS.md.
  and [README](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/cross_industry_alpha_factory/README.md)
  (introduced in commit `d0e1e2ed`).

## [1.1.0] - 2025-07-15
### Breaking Changes
- `GraphMemory._fallback_query` now returns stub data when both Neo4j and NetworkX are missing.
### Added
- CLI commands `agents-status` and `replay` for monitoring agents and replaying ledger events.
- ADK and MCP adapters bridging the Alpha Data Kernel and Multi‑Chain Proxy.
- Detailed design overview for the α‑AGI Insight demo under `alpha_factory_v1/demos/alpha_agi_insight_v1/docs`.
- Expanded API documentation with `curl` and WebSocket examples.
- Additional CLI notes and help command reference.
- Documented `AGI_INSIGHT_MEMORY_PATH` for persistent storage configuration.
- Optional CPU and memory caps for the CodeGen sandbox via
  `SANDBOX_CPU_SEC` and `SANDBOX_MEM_MB`.
- Optional `firejail` sandboxing when the binary is available.
- Configurable secret backend for HashiCorp Vault and cloud managers via `AGI_INSIGHT_SECRET_BACKEND`.
- Protobuf dataclasses generated via `make proto` (uses the `betterproto` plugin when installed).
- Optional JSON console logging and DuckDB ledger support.
- Aggregated forecast endpoint `/insight` and OpenAPI schema exposure.
- Baseline load test metrics: p95 latency below 180 ms with 20 VUs.
- Prometheus metrics available at `/metrics`.
- Lightweight `/status` endpoint listing agent names, heartbeats and restarts.
- `GraphMemory._fallback_query` now returns stub data when both Neo4j and NetworkX are missing.
- Property-based tests verify `SafetyGuardianAgent` blocks malicious code.
- Added optional e2e test broadcasting Merkle roots to the Solana devnet.
- Example Helm values file for the Insight chart.
- `simulate` command now accepts `--energy` and `--entropy` to set initial
  sector values. The React dashboard exposes matching input fields.
- Version constant ``__version__`` defined in ``alpha_factory_v1.demos.alpha_agi_insight_v1.__init__``.
- Version constant ``__version__`` defined in ``alpha_factory_v1.demos.cross_industry_alpha_factory.__init__``.

## [v1.0] - 2025-07-01
- CLI commands `simulate`, `show-results`, `agents-status` and `replay` for running and inspecting forecasts.
- Web dashboard served when `RUN_MODE=web` or via `streamlit run src/interface/web_app.py`.
- Security features include API token authentication, optional TLS for the gRPC bus and REST API, ED25519-signed agent
  wheels and HashiCorp Vault integration for secrets.

## [1.0.2] - 2025-06-30
- Documented CLI and FastAPI usage with example commands.
- Added agent architecture diagrams and algorithm explanations for MATS and forecasting.
- Provided a Streamlit dashboard for interactive demos.
- Maintained versioned changelog for project history.

## [1.0.1] - 2025-05-25
- Packaged the React web client and served static assets from the API server.
- Added asynchronous API tests and new CLI flags.
- Improved container orchestration scripts and default Docker compose files.

## [1.0.0] - 2025-05-15
- Initial release with an offline-friendly CLI and REST API for running simulations.
- Included a minimal web interface served when `RUN_MODE=web`.
- Shipped Meta-Agentic Tree Search and forecasting modules with Docker deployment scripts.

## [0.2.0] - 2024-06-01
- Expanded design document with data flow, interface and deployment notes.
- Documented API endpoints in greater detail.
- Added infrastructure templates for Docker, Helm and Terraform with environment variables.
