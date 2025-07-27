# SPDX-License-Identifier: Apache-2.0
"""Lightweight notebook execution tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Skip when nbformat, nbconvert or ipykernel is unavailable
missing = [name for name in ("nbformat", "nbconvert", "ipykernel") if importlib.util.find_spec(name) is None]
if missing:
    reason = ", ".join(missing) + " missing"
    pytest.skip(reason, allow_module_level=True)

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


def test_macro_sentinel_notebook(tmp_path: Path) -> None:
    """Execute the entire macro sentinel notebook headless."""
    nb_path = Path("alpha_factory_v1/demos/macro_sentinel/colab_macro_sentinel.ipynb")
    assert nb_path.exists(), nb_path

    nb = nbformat.read(nb_path, as_version=4)

    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        src = cell.source
        if src.startswith("%%bash"):
            cell.source = "print('skipping bash cell')"
        if "getpass.getpass" in src or "input(" in src:
            cell.source = (
                "import os, json\n"
                "os.environ.setdefault('OPENAI_API_KEY', '')\n"
                "os.environ.setdefault('FRED_API_KEY', '')\n"
                "os.environ.setdefault('TW_BEARER_TOKEN', '')\n"
                "os.environ.setdefault('LIVE_FEED', '0')\n"
                "os.environ['DEFAULT_PORTFOLIO_USD'] = '2000000'\n"
                "print(json.dumps({k: os.getenv(k, '') for k in ['OPENAI_API_KEY',"
                " 'FRED_API_KEY','TW_BEARER_TOKEN','LIVE_FEED']}, indent=2))"
            )
        if "agent_macro_entrypoint.py" in src:
            cell.source = (
                "import subprocess, sys\n"
                "proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                "print('stub process started')"
            )
        if "macro_event(" in src or "await cycle" in src:
            cell.source = "print('skip programmatic call')"
        if "AgentClient(" in src:
            cell.source = "print('skip AgentClient call')"

    ep = ExecutePreprocessor(timeout=120, kernel_name="python3", allow_errors=True)
    ep.preprocess(nb, {"metadata": {"path": str(tmp_path)}})

    errors = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        for out in cell.get("outputs", []):
            if out.output_type == "error":
                errors.append(f"Cell {i} failed: {out.evalue}\n{cell.source}")
    assert not errors, "Notebook execution errors:\n" + "\n\n".join(errors)
