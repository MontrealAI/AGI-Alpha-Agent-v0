# SPDX-License-Identifier: Apache-2.0
# 🧪 Root Test Suite

These integration tests expect the `alpha_factory_v1` package to be importable. When running from the repository root without installation, set `PYTHONPATH` so Python can locate the source tree:

Run `python check_env.py --auto-install` first to confirm all dependencies are available.

```bash
export PYTHONPATH=$(pwd)
python -m pytest -q tests
```

Alternatively install the package in editable mode first:

```bash
pip install -e .
pytest -q
```
- Playwright test `test_umap_fallback.py` ensures the simulator uses random UMAP coordinates when Pyodide is blocked.
