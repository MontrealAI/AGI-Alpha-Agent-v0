[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)
# API Overview

This demo exposes a minimal REST and WebSocket interface implemented in `src.interface.api_server`. All requests must
include `Authorization: Bearer $API_TOKEN`.

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational
goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes
financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

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
