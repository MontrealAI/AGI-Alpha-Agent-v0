[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Design Overview

[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

This document outlines the architecture of the Alpha Factory demo included in this repository. It also explains the individual agent roles and the Meta-Agentic Tree Search (MATS) algorithm used for evolutionary optimisation.

## Architecture

The demo consists of a lightweight orchestrator and a handful of specialised agents.  All
components communicate through a simple in-memory message bus using envelope objects.
The orchestrator exposes both a command line interface and a small REST API so the
simulation can run headless or with a web frontend.

### Simulation engine

Two tiny modules implement the core of the simulation:

- `forecast.py` – generates a capability forecast and triggers thermodynamic disruption.
- `mats.py` – performs a zero‑data evolutionary search to refine potential innovations.

Both modules are intentionally concise and easy to extend.

### Orchestrator

The orchestrator manages message routing between agents and persists every
interaction in a ledger. This ledger can be replayed to analyse decision steps or
to visualise the overall run. Agents are invoked sequentially in short cycles so
the system remains deterministic and easy to debug.


### Message bus

Messages are dispatched in short deterministic cycles.  Agents read an envelope,
mutate its contents and pass it back to the orchestrator which then forwards it
to the next participant.  Each interaction is stored in a ledger so that runs
can be replayed or inspected later.

## Agent roles

Seven agents are bootstrapped by the orchestrator:

1. **PlanningAgent** – builds a high level execution plan.
2. **ResearchAgent** – gathers background information and assumptions.
3. **StrategyAgent** – decides which sectors or ideas to pursue.
4. **MarketAgent** – evaluates potential economic impact.
5. **CodeGenAgent** – produces runnable code snippets when needed.
6. **SafetyGuardianAgent** – performs lightweight policy and safety checks.
7. **MemoryAgent** – persists ledger events for later replay.

Each agent implements short cycles of work which the orchestrator invokes sequentially. The ledger records every envelope processed so the entire run can be replayed for inspection.

## The MATS algorithm

MATS (Meta-Agentic Tree Search) is an NSGA-II style evolutionary loop that evolves a population of candidate solutions in two objective dimensions. Each individual has a numeric genome and is evaluated by a custom fitness function. Non-dominated sorting and crowding distance ensure that the search explores the trade‑off surface effectively. The resulting Pareto front highlights the best compromises discovered so far.

The demo uses MATS with a toy function `(x^2, y^2)` but the optimiser can be repurposed for arbitrary metrics. Results are visualised either in the Streamlit dashboard or through the REST API.

The helper function `run_evolution` initialises the population and executes the
NSGA‑II loop for a configurable number of generations. The population size,
mutation rate and generation count can be adjusted and a random ``seed`` enables
deterministic runs which is useful for testing and reproducibility.

## Data flow

Messages traverse the orchestrator in discrete cycles. Each cycle begins with the PlanningAgent emitting a high level goal. Subsequent agents enrich this envelope with research, strategy and market data before the CodeGenAgent proposes executable actions. The SafetyGuardianAgent performs a final policy check and, if approved, the MemoryAgent records the action to the ledger. This deterministic loop makes it easy to trace how a decision emerged from the collective agent swarm.

## Interfaces

The system exposes both a command line interface and a REST/WS API. The CLI is suitable for quick local experiments and supports subcommands for running simulations, replaying ledger events and inspecting agent status. The API server wraps the same orchestrator in a FastAPI application. Clients start a simulation via `POST /simulate`, fetch results with `GET /results/{id}` and stream logs through `WS /ws/{id}`. A lightweight web dashboard consumes these endpoints to visualise progress.

## Deployment model

The repository includes container and infrastructure templates for Docker Compose, Helm and Terraform. Each mode deploys the orchestrator together with optional agents and the web UI. Environment variables configured in `.env` control credentials, ports and runtime options. When running in Kubernetes, the Helm chart maps these variables to pod environment settings. The Terraform examples show how to provision equivalent services on AWS Fargate or Google Cloud Run.

## Evolution worker

`src/evolution_worker.py` provides a tiny FastAPI service that performs a single
NSGA‑II mutation step. It accepts either an uploaded tarball or a repository URL
and returns the resulting child genome.

### Endpoints

- `POST /mutate` – upload a `tar` file or send `repo_url` form data. All archive
  members are validated and extracted to a temporary directory before running
  the mutation step. The JSON response contains the new genome.
- `GET /healthz` – simple liveness probe returning `"ok"`.

Typical usage is to run the container and POST agent source code to `/mutate`.
The returned genome can seed another agent or be stored for analysis. A
`_safe_extract` validates each archive member before extraction. Symlinks and
hard links are rejected and paths are normalised so absolute or parent
directories cannot be written outside the target directory. Verified members are
then extracted individually to avoid surprises.

## Security considerations

The demo runs with minimal privileges and avoids hard-coded secrets. All credentials are loaded from `.env` or the host environment. Tests disable network access via `PYTEST_NET_OFF=true` to ensure deterministic behaviour.

Agent wheels in `alpha_factory_v1/backend/agents` must be signed with an ED25519 key. The public key is provided in `AGENT_WHEEL_PUBKEY` and each wheel includes a `.whl.sig` file. Unsigned wheels are ignored at runtime.

When exposing the API server, use TLS termination and restrict access behind a proxy. The default configuration binds to localhost only.
