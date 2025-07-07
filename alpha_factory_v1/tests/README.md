[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# 🧪 Test Suite · Alpha‑Factory v1 👁
*Reliable automation through deterministic tests*

This directory hosts the unit and smoke tests that keep the Alpha‑Factory stack stable across updates. Tests run with `pytest` but also fall back to Python's built‑in `unittest` so they execute even in minimal environments.

---

## Quick Start
1. **Install dependencies**
   ```bash
   python -m pip install -r alpha_factory_v1/backend/requirements.lock
   ```
   For a lightweight run you only need `pytest`:
   ```bash
   python -m pip install pytest
   ```
2. **Run all tests**
   ```bash
   python -m pytest -q alpha_factory_v1/tests
   ```
   The suite is also compatible with `unittest`:
   ```bash
   python -m unittest discover -s alpha_factory_v1/tests
   ```

## Docker Smoke Test
`test_smoke.py` verifies that the Docker image builds and the API responds. Execute it separately if Docker is available:
```bash
python -m pytest alpha_factory_v1/tests/test_smoke.py
```
The test is skipped automatically when Docker cannot be found.

## Environment Variables
- `AF_MEMORY_DIR` – path used by some tests for temporary state.
- `PYTEST_CPU_SOFT_SEC`, `PYTEST_MEM_MB`, `PYTEST_NET_OFF` – resource limits used by `backend/tools/local_pytest.py`.

## Local Pytest Tool
To run tests in a hardened sandbox, invoke:
```bash
python -m alpha_factory_v1.backend.tools.local_pytest
```
This wrapper executes `pytest` with CPU and memory caps and strips credentials from the environment.

## Test Files
| File | Purpose |
|------|---------|
| `test_cli.py` | Command‑line argument parser |
| `test_alpha_model.py` | Quant finance helpers |
| `test_finance_agent.py` | Finance agent guardrails |
| `test_genetic_tests.py` | Genetic optimisation utilities |
| `test_governance_sim.py` | AGI governance simulation |
| `test_memory.py` | Key‑value memory fabric |
| `test_vector_memory.py` | Vector memory fabric |
| `test_planner_agent.py` | Planner agent logic |
| `test_requests_shim.py` | HTTP requests shim (minimal `requests` clone) |
| `test_register_decorator.py` | Agent registration decorator |
| `test_smoke.py` | Container build and API health check |
| `redteam_prompts.json` | Prompts for security testing |

## Contribution Guidelines
- Keep new tests deterministic and under five seconds.
- Avoid network calls unless explicitly mocked.
- Prefer `unittest.TestCase` for compatibility.
- Run the full suite before submitting changes.

