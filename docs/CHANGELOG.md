# Changelog

This demo is a conceptual research prototype. References to "AGI" and
"superintelligence" describe aspirational goals and do not indicate the
presence of a real general intelligence. Use at your own risk.

All notable changes to this project are documented in this file.

## [Unreleased]
- Synced `openai`, `openai-agents` and `uvicorn` pins across requirements files
  and clarified why `requests` and `rich` differ between layers.
- Documented `API_RATE_LIMIT`, `AGI_ISLAND_BACKENDS` and `ALERT_WEBHOOK_URL`
  environment variables.
- Added [`src/tools/analyse_backtrack.py`](../src/tools/analyse_backtrack.py) for visualising archive backtracks.
- Documented how to build a wheelhouse for offline installs and updated
  `tests/README.md` with the instructions.
- Added CI workflow running lint, type checks, tests and Docker build with
  automated image deployment on tags and rollback on failure. Metrics are
  exported via OpenTelemetry and can be viewed in Grafana or the Streamlit
  dashboard.
- Documented `ALPHA_ASI_*` demo variables in README and AGENTS.md.
- Removed outdated `alpha_asi_world_model_demo_v1.py` script.
- `_set_seed` in `alpha_asi_world_model_demo.py` now sets CUDA seeds when
  a GPU is available.

## [1.1.0] - 2025-07-15
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

## [v1.0] - 2025-07-01
- CLI commands `simulate`, `show-results`, `agents-status` and `replay` for running and inspecting forecasts.
- Web dashboard served when `RUN_MODE=web` or via `streamlit run src/interface/web_app.py`.
- Security features include API token authentication, optional TLS for the gRPC bus and REST API, ED25519-signed agent wheels and HashiCorp Vault integration for secrets.

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
