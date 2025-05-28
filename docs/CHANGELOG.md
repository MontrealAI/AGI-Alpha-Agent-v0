# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]
### Added
- Detailed design overview for the α‑AGI Insight demo under `alpha_factory_v1/demos/alpha_agi_insight_v1/docs`.
- Expanded API documentation with `curl` and WebSocket examples.
- Additional CLI notes and help command reference.
- Documented `AGI_INSIGHT_MEMORY_PATH` for persistent storage configuration.
- Optional CPU and memory caps for the CodeGen sandbox via
  `SANDBOX_CPU_SEC` and `SANDBOX_MEM_MB`.
- Optional `firejail` sandboxing when the binary is available.
- Configurable secret backend for HashiCorp Vault and cloud managers via `AGI_INSIGHT_SECRET_BACKEND`.
- Optional JSON console logging and DuckDB ledger support.
- Aggregated forecast endpoint `/insight` and OpenAPI schema exposure.
- Baseline load test metrics: p95 latency below 180 ms with 20 VUs.
- Prometheus metrics available at `/metrics`.
- Automated benchmark feedback posted on pull requests.

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
