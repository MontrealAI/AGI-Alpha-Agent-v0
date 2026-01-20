# SPDX-License-Identifier: Apache-2.0
"""Execute the alpha_asi_world_model_colab notebook in --no-llm mode."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

nbformat = pytest.importorskip("nbformat")
pm = pytest.importorskip("papermill")


def test_notebook_runs(tmp_path: Path) -> None:
    nb_path = Path("alpha_factory_v1/demos/alpha_asi_world_model/alpha_asi_world_model_colab.ipynb")
    assert nb_path.exists(), nb_path
    nb = nbformat.read(nb_path, as_version=4)

    skip = {2, 4, 8, 15, 17, 19}
    skip_markers = (
        "alpha_asi_world_model_demo --demo",
        "get_ipython().system",
        "&",
    )
    for idx, cell in enumerate(nb.cells):
        if idx in skip or any(marker in cell.source for marker in skip_markers):
            cell.source = "print('skipped')"

    mod = tmp_path / "mod.ipynb"
    nbformat.write(nb, mod)

    os.environ["NO_LLM"] = "1"
    os.environ.setdefault("ALPHA_ASI_SILENT", "1")

    pm.execute_notebook(str(mod), str(tmp_path / "out.ipynb"), kernel_name="python3")
