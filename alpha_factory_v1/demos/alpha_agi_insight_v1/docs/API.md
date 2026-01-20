[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)
# API Overview

This demo exposes a minimal REST and WebSocket interface implemented in `src.interface.api_server`. All requests must include `Authorization: Bearer $API_TOKEN`.

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

| Endpoint | Query/Path Params | Payload | Example Response |
|---------|------------------|---------|-----------------|
| **POST `/simulate`** | – | `{ "horizon": 5, "pop_size": 6, "generations": 3 }` | `{ "id": "d4e5f6a7" }` |
| **GET `/results/{sim_id}`** | `sim_id` (path) | – | `{ "id": "d4e5f6a7", "forecast": [{"year": 1, "capability": 0.1}], "population": [] }` |
| **GET `/population/{sim_id}`** | `sim_id` (path) | – | `{ "id": "d4e5f6a7", "population": [] }` |
| **GET `/runs`** | – | – | `{ "ids": ["d4e5f6a7"] }` |
| **POST `/insight`** | – | `{ "ids": ["d4e5f6a7"] }` | `{ "forecast": [{"year": 1, "capability": 0.1}] }` |
| **WS `/ws/progress`** | – | N/A | `{"id": "d4e5f6a7", "year": 1, "capability": 0.1}` |

### `GET /population/{sim_id}`

Retrieve only the final population for a completed run.

```bash
curl -H "Authorization: Bearer $API_TOKEN" \
  http://localhost:8000/population/<sim_id>
```

Example response:

```json
{
  "id": "<sim_id>",
  "population": [
    {"effectiveness": 0.5, "risk": 0.2, "complexity": 0.3, "rank": 0}
  ]
}
```

### `POST /insight`

Compute aggregated forecast data across stored runs. Optionally pass a JSON
payload with a list of run identifiers under `ids`. When omitted, all available
runs are included.

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

