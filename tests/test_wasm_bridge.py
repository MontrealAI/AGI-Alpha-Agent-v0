# SPDX-License-Identifier: Apache-2.0
"""Test WASM bridge error handling."""

import shutil
import subprocess
from pathlib import Path

import pytest

BRIDGE = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/src/wasm/bridge.js")
LIB = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/lib/pyodide.js")


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
def test_pyodide_load_failure(tmp_path: Path) -> None:
    if not BRIDGE.exists():
        pytest.skip("bridge.js not built")
    bridge_copy = tmp_path / "bridge.mjs"
    text = BRIDGE.read_text().replace("../lib/pyodide.js", LIB.resolve().as_posix())
    bridge_copy.write_text(text)

    script = tmp_path / "run.mjs"
    script.write_text(
        "globalThis.window = {\n"
        "  toast: (m) => console.log(m),\n"
        "  loadPyodide: () => { throw new Error('boom'); }\n"
        "};\n"
        "globalThis.toast = globalThis.window.toast;\n"
        f"const m = await import('{bridge_copy.as_posix()}');\n"
        "try { await m.run(); } catch (e) {}\n"
    )
    result = subprocess.run(["node", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "Pyodide failed to load" in result.stdout
