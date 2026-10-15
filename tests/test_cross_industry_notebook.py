# SPDX-License-Identifier: Apache-2.0
"""Execute every trusted notebook Python cell offline and verify recovery semantics."""
import json
from pathlib import Path
import socket
import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = (
    ROOT / "alpha_factory_v1/demos/cross_industry_alpha_factory/colab_deploy_alpha_factory_cross_industry_demo.ipynb"
)


def cells():
    notebook = json.loads(NOTEBOOK.read_text())
    return ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]


def test_all_notebook_cells_execute_without_network_and_export_recover(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def denied(*args, **kwargs):
        raise AssertionError("Notebook attempted network access")

    monkeypatch.setattr(socket.socket, "connect", denied)
    namespace = {}
    for index, source in enumerate(cells()):
        exec(compile(source, f"notebook-cell-{index}", "exec"), namespace)
    assert namespace["report"]["mode"] == "synthetic-example"
    assert namespace["recomputed"]["input_sha256"] == namespace["report"]["input_sha256"]
    assert namespace["recomputed"]["ranking"] == namespace["report"]["ranking"]
    path = namespace["evidence_path"]
    original = path.read_bytes()
    old_weight = namespace["assessment"]["weights"]["benefit"]
    namespace["assessment"]["weights"]["benefit"] = old_weight + 1
    with pytest.raises(ValueError, match="rerun"):
        exec(compile(cells()[-2], "export-cell", "exec"), namespace)
    namespace["assessment"]["weights"]["benefit"] = old_weight
    assert path.read_bytes() == original
    with pytest.raises(FileExistsError):
        exec(compile(cells()[-2], "export-cell", "exec"), namespace)
    assert path.read_bytes() == original
    forged = json.loads(original)
    forged["report"] = {"selected_id": "invented", "productionApproved": True}
    path.write_text(json.dumps(forged))
    exec(compile(cells()[-1], "recovery-cell", "exec"), namespace)
    assert namespace["recomputed"]["selected_id"] != "invented"
    assert "productionApproved" not in namespace["recomputed"]
    path.write_bytes(b'{"schema":"x","schema":"y"}')
    with pytest.raises(ValueError, match="Duplicate"):
        exec(compile(cells()[-1], "recovery-cell", "exec"), namespace)
    path.write_bytes(b'{"input":"\xff"}')
    with pytest.raises(UnicodeDecodeError):
        exec(compile(cells()[-1], "recovery-cell", "exec"), namespace)


def test_notebook_has_no_shell_cells_or_retained_outputs():
    notebook = json.loads(NOTEBOOK.read_text())
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == [] and cell["execution_count"] is None
            compile("".join(cell["source"]), "notebook", "exec")
    assert all("ngrok" not in source and "subprocess" not in source for source in cells())
