[Project notice](../DISCLAIMER_SNIPPET.md)

# Repository guide — 1.23.2

Choose a working path before installing dependencies. The maintained private operator, browser workspaces,
native learning labs and historical service stack have different requirements. Their source, research,
flowcharts, media and prior release notes remain available together in this repository.

## Start with a result

| Goal | Entry point | First result |
|---|---|---|
| Try the project immediately | [Public workspace](../index.html) | Editable scenarios, computed results and downloadable evidence |
| Work privately with your own records | [Start here](START_HERE.md) | Install matching release assets, run an allocation, inspect and review it |
| Explore a particular experiment | [Complete demo walkthrough](DEMOS.md) | All 26 catalog entries, prerequisites and launch commands |
| Train a small planning model | [MuZero guide](MUZERO.md) or [Evidence & Planning Lab](../demos/muzeromctsllmagent_v0.md) | Native training, measured baselines and retained reports |
| Operate and recover the agent | [Operator guide](OPERATIONS.md) | Private state, authentication, pause, backup, restore and upgrades |
| Reproduce the contract reference | [Ascension protocol](ASCENSION_PROTOCOL.md) | Local-EVM lifecycle with explicit fixture boundaries |
| Contribute to the repository | [Contributor guide](../../AGENTS.md) | Locked development setup, hooks, types and tests |
| Understand the research vision | [Manuscript alignment](MANUSCRIPT_ALIGNMENT.md) | The original manuscript mapped to implementations and remaining research obligations |

The browser examples need no account or API key. The native allocation example needs Python 3.11–3.13;
Docker, Node and a model are optional for that path. Use separate environments for operator releases,
development and the heavier labs. [Release readiness](RELEASE_READINESS.md) defines the supported scope.

## Find the right source

| Repository area | Purpose | Validation and operating guidance |
|---|---|---|
| `alpha_factory_v1/core/runtime`, `examples/missions` | Signed missions, review, recovery, inference and operator API | Runtime matrix, real model, browser and isolated-code acceptance |
| `alpha_factory_v1/demos` | Complete catalog, native labs and preserved experiments | Catalog preflight, 17 finite wheel launches and separate lab gates |
| `docs`, packaged demo `web` directories | Public workspaces, guides, mirrors and offline assets | Strict documentation builds, browser workflows, exact-source distribution and public HTTPS checks |
| `contracts`, `tests/contracts`, `truffle` | Canonical contracts, local protocol harness and historical deployment configuration | Shipped/test source consistency, Solidity tests and real local-EVM acceptance; deployment needs separate qualification |
| `alpha_factory_v1/backend`, `src`, `af_requests`, `openai_agents`, `stubs` | Preserved orchestrator, compatibility layers and optional integrations | Full regression, typing, service-container and integration checks; optional credentials and extras have explicit boundaries |
| `docker`, `infrastructure`, Compose and Helm files | Local images and deployment configurations | Supported containers and shared Compose consumers are exercised; production infrastructure needs operator-specific configuration |
| `scripts`, `tools`, `codex`, `.github` | Setup, checks, packaging, CI and publication | Hooks, exact-commit release gates, verified installation and re-downloaded release checksums |
| `benchmarks`, `experiments`, `data`, `policies`, `internal_docs`, `wheels` | Research fixtures, policies, background material and offline setup guidance | Retained in source; a fixture or design document does not establish a live integration |

## Docker quickstart for the preserved research API

The root `run_quickstart.sh` is the **research API** launcher. For the maintained private agent and its
operator console, use [Start here](START_HERE.md) or the operator container in [Operations](OPERATIONS.md).

```bash
./run_quickstart.sh --help
./run_quickstart.sh --build-only
./run_quickstart.sh
```

The first launch creates a private root `.env` from the sample and stops. Set `API_TOKEN` and
`NEO4J_PASSWORD`, then run it again. Existing configuration is never overwritten. Keep the file private;
Docker receives its values through `--env-file`, so the non-root process can use a mode-600 host file.
The application normalizes documented dotenv quotes and inline comments without expanding variables.

The image builds from the repository root, uses hashed historical dependencies, includes the compatibility
package and runs the API instead of exiting with help. Its default enabled agent is `ping`; set
`ALPHA_ENABLED_AGENTS` for optional integrations only after configuring their requirements.
Open **http://127.0.0.1:8000/docs** and authenticate with your configured API token. The host port is
loopback-only; this helper fixes the internal port at 8000 and memory at `/data/memory`.
The named Docker volume `alpha-factory-quickstart-data` retains memory when the container stops.
Use **Ctrl+C** to stop. Do not remove the volume when you want to retain its data.

This small image does not start the companion UI or database. Use the documented Compose profile for
the broader historical stack. Older README command examples and image tags remain as historical material;
the maintained operator path uses the matching release wheel and lock, not an unverified `latest` image.

## Verify an install before changing anything

Download the installer, wheel, lock and `SHA256SUMS` from the same release into a new folder:

```bash
python3 install_agent.py --release-dir . --venv .venv-agent --check-only
python3 install_agent.py --release-dir . --venv .venv-agent
```

Use `python` on Windows. The check-only command validates checksums, required files and destination paths
without network calls, installs or file writes. With `--wheelhouse`, it also checks that the directory
exists and contains wheel files; dependency completeness and platform compatibility are checked by the
subsequent hashed installation. Invalid inputs fail before environment creation. An interrupted install
retains its partial new environment for inspection and tells you which phase failed; retry at a new path.
Keep the existing agent and its backup when upgrading.

## What the release establishes

Repo-Healer repair workspaces omit dependency caches and Python virtual environments, including custom
names identified by `pyvenv.cfg`. Candidate generation and file comparison share that selection, avoiding
large dependency copies and spurious deletion proposals. This does not change the original environment
or provide a general sandbox for untrusted validation commands.

The publication workflow requires the complete offline regression, strict type profiles, dependency
advisory checks, runtime and wheel matrices, native labs, real browser/model/container workflows,
contract tests, preservation checks and exact-main integration CI. Packaging exercises the installer,
then public-site acceptance and re-downloaded asset checksums precede publication. Inspect the matching
release manifest and validation archive for measured results and any explicit skips.

The supported profile remains bounded demos and a private single-operator deployment. Mainnet authority,
public multi-tenant operation, universal intelligence, independent economic guarantees and unconfigured
external services require separate evidence. The [manuscript map](MANUSCRIPT_ALIGNMENT.md) keeps those
research obligations visible while preserving the full vision.
