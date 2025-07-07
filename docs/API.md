[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# API and CLI Usage

This page documents the REST endpoints provided by the demo API server and the available command line commands.

## REST endpoints

The API is implemented with FastAPI in `src.interface.api_server`. The
orchestrator boots in the background when the server starts and is gracefully
shut down on exit. Available endpoints are:

- `POST /simulate` – start a new simulation.
- `GET /results` – most recent simulation data.
- `GET /results/{sim_id}` – fetch final forecast data.
- `GET /population/{sim_id}` – retrieve only the population list.
- `POST /insight` – aggregate existing forecasts.
- `GET /status` – current agent heartbeats and restart counts.
- `WS  /ws/progress` – stream progress logs while the simulation runs.
- `GET /openapi.json` – FastAPI auto-generated schema.
- `GET /metrics` – Prometheus metrics for monitoring.

### Error Responses

Errors follow the [RFC&nbsp;7807](https://datatracker.ietf.org/doc/html/rfc7807)
`application/problem+json` format:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Optional human readable message"
}
```

## Authentication

All requests must include an `Authorization: Bearer $API_TOKEN` header so the
server can verify the caller. Define `API_TOKEN` in your `.env` file:

```bash
API_TOKEN=mysecret
```

or pass the variable when launching Docker:

```bash
docker run -e API_TOKEN=mysecret <image>
```

Rate limiting is controlled via `API_RATE_LIMIT` (default `60` requests per
minute per IP).

Start the server with:

```bash
python -m src.interface.api_server --host 0.0.0.0 --port 8000
```

Once the server is running you can trigger a forecast using `curl`:

```bash
curl -X POST http://localhost:8000/simulate \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"horizon": 5, "pop_size": 6, "generations": 3, "curve": "linear", "energy": 1.0, "entropy": 1.0}'
```

Retrieve the results when the run finishes:

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/results/<sim_id>
```

## Command line interface

The CLI lives in `alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/cli.py`. It groups several commands under
one entry point:

```bash
python cli.py [COMMAND] [OPTIONS]
```

Display all available commands and options:

```bash
python cli.py --help
```

For example, to run a three‑generation simulation with six sectors and a
population size of six for a five‑year horizon:

```bash
python cli.py simulate --horizon 5 --sectors 6 --pop-size 6 --generations 3
```

The orchestrator starts automatically and persists a ledger under `./ledger/`.
Use the `show-results` command to display the latest forecast:

```bash
python cli.py show-results
```

Available commands are:

- `simulate` – run a forecast and launch the orchestrator. Key options include `--horizon`, `--curve`, `--k`, `--x0`,
  `--sectors`, `--pop-size` and `--generations`.
- `show-results` – display the latest ledger entries recorded by the orchestrator.
- `agents-status` – list currently registered agents.
- `replay` – replay ledger entries with a small delay for analysis.


### Endpoint Details

**POST `/simulate`**

Start a new simulation. Send a JSON payload with the following fields:

- `horizon` – forecast horizon in years
- `pop_size` – number of individuals per generation
- `generations` – number of evolutionary steps
- `mut_rate` – probability of mutating a gene
- `xover_rate` – probability of performing crossover
- `curve` – capability growth curve (`logistic`, `linear`, `exponential`)
- `k` – optional growth curve steepness
- `x0` – optional growth curve midpoint
- `energy` – initial energy level for generated sectors
- `entropy` – initial entropy level for generated sectors
- `sectors` – optional list of sector objects with `name`, `energy`, `entropy` and `growth`

`energy` and `entropy` apply when no custom `sectors` list is provided and map
to the `--energy` and `--entropy` CLI options.

```json
{
  "horizon": 5,
  "pop_size": 6,
  "generations": 3,
  "mut_rate": 0.1,
  "xover_rate": 0.5,
  "curve": "logistic",
  "k": 10.0,
  "x0": 0.0,
  "energy": 1.0,
  "entropy": 1.0,
  "sectors": [{"name": "s00", "energy": 1.0, "entropy": 1.0, "growth": 0.05}]
}
```

The response contains the generated simulation identifier:

```json
{"id": "<sim_id>"}
```

**GET `/results`**

Return the most recent simulation results. The payload matches
``GET /results/{sim_id}``.

```json
{
  "id": "<sim_id>",
  "forecast": [{"year": 1, "capability": 0.1}],
  "population": [{"effectiveness": 0.5, "risk": 0.2, "complexity": 0.3, "rank": 0}]
}
```

**GET `/results/{sim_id}`**

Return the final forecast for an earlier run. The returned list contains one
object per simulated year with the capability value reached by the model.

Example response:

```json
{
  "id": "<sim_id>",
  "forecast": [{"year": 1, "capability": 0.1}],
  "population": [
    {"effectiveness": 0.5, "risk": 0.2, "complexity": 0.3, "rank": 0}
  ]
}
```

**GET `/population/{sim_id}`** – returns only the ``population`` array if required.

**POST `/insight`**

Compute aggregated forecast data across stored runs. Optionally pass a JSON
payload with a list of run identifiers under ``ids``. When omitted, all
available runs are included.

Example request body:

```json
{
  "ids": ["abc123", "def789"]
}
```

The response contains the average capability value per year:

```json
{
  "forecast": [{"year": 1, "capability": 0.5}]
}
```

**GET `/status`**

List all running agents with their last heartbeat and restart count.

```json
{
  "agents": {
    "planning": {"last_beat": 0.0, "restarts": 0}
  }
}
```

**WebSocket `/ws/progress`**

Streams progress messages during a running simulation. Messages are plain text lines
such as `"Year 1: 0 affected"` or `"Generation 2"`. Close the socket once all
messages have been received.

```bash
wscat -c "ws://localhost:8000/ws/progress" \
  -H "Authorization: Bearer $API_TOKEN"
```

The server honours environment variables defined in `.env` such as `PORT` (HTTP port) and `OPENAI_API_KEY`. When a
prebuilt React dashboard exists under `src/interface/web_client/dist`, it is automatically served at the root path
(`/`). CORS headers are configured via `API_CORS_ORIGINS` (default `"*"`).
Sandbox CPU and memory limits can be set via `SANDBOX_CPU_SEC` and `SANDBOX_MEM_MB`.
Alert notifications can be forwarded when `ALERT_WEBHOOK_URL` is set. Islands may
target different backends by defining `AGI_ISLAND_BACKENDS`, for example
`default=gpt-4o,eval=mistral-small`.
The OpenAPI specification can be fetched from `/openapi.json` when the server is
running.

### Metrics

Prometheus scrapes `/metrics` on the same port as the API. The endpoint exposes
counters and histograms such as `api_requests_total` and
`api_request_duration_seconds`.

### Message Bus Protocol

Agents communicate over a lightweight gRPC bus. On connection clients must
perform a simple handshake by sending the literal string `proto_schema=1` to the
`/bus.Bus/Send` method. The server replies with the same string. After the
handshake, JSON encoded envelopes defined by `a2a.proto` may be transmitted.

## Offline usage

When network access is unavailable, install optional packages from a wheelhouse:

```bash
python check_env.py --auto-install --wheelhouse <dir>
```

Refer to [docs/OFFLINE_INSTALL.md](OFFLINE_INSTALL.md) for step‑by‑step
instructions.
