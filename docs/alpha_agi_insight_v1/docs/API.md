[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)

# Insight Demo API

This page summarizes the Insight demo API surface and points to the runtime
implementation inside the Alpha-Factory v1 package. Refer to the service
entrypoints in `alpha_factory_v1/backend/services` for the authoritative
behavior.

## Quick overview

- The Insight API server is a FastAPI app exposed by the orchestrator service.
- Routes are mounted under the demo's base URL (see `BUSINESS_HOST` in the
  `.env`/environment configuration).
- Auth behavior and rate limits are controlled by environment variables
  documented in `alpha_factory_v1/.env.sample`.

## Key endpoints

- `/health` — Liveness/readiness checks used by the Insight UI.
- `/api/insight/*` — Insight demo routes consumed by the browser client.

## Related files

- `alpha_factory_v1/backend/services/api_server_service.py`
- `alpha_factory_v1/backend/services/insight_api.py`
