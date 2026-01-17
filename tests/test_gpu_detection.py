# SPDX-License-Identifier: Apache-2.0
import re
import shutil
import subprocess
from pathlib import Path

import pytest

LLM = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/src/utils/llm.ts")
TS_NODE_LOADER = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/node_modules/ts-node/esm.mjs")
ONNX_RUNTIME = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/node_modules/onnxruntime-web")
NODE_MAJOR_RE = re.compile(r"v?(\d+)")


def _node_major() -> int | None:
    if not shutil.which("node"):
        return None
    try:
        version = subprocess.check_output(["node", "--version"], text=True).strip()
    except subprocess.SubprocessError:
        return None
    match = NODE_MAJOR_RE.match(version)
    if not match:
        return None
    return int(match.group(1))


def _skip_reason() -> str | None:
    node_major = _node_major()
    if node_major is None:
        return "node not available"
    if node_major < 22:
        return "Node.js 22+ required for ts-node loader"
    if not TS_NODE_LOADER.is_file():
        return "ts-node loader not installed"
    ort_pkg = LLM.parents[2] / "node_modules" / "onnxruntime-web"
    if not ort_pkg.exists():
        return "onnxruntime-web not installed"
    ort_probe = subprocess.run(
        ["node", "-e", "import('onnxruntime-web')"],
        capture_output=True,
        text=True,
    )
    if ort_probe.returncode != 0:
        return "onnxruntime-web not importable"
    if not ONNX_RUNTIME.exists():
        return "onnxruntime-web not installed"
    if not LLM.is_file():
        return "llm.ts missing"
    return None


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
def test_llm_gpu_backend(tmp_path: Path) -> None:
    reason = _skip_reason()
    if reason:
        pytest.skip(reason)
    script = tmp_path / "run.mjs"
    script.write_text(
        f"globalThis.navigator = {{ gpu: {{}} }};\n"
        f"globalThis.localStorage = {{ getItem: () => null }};\n"
        f"const m = await import('{LLM.resolve().as_posix()}');\n"
        "console.log(await m.gpuBackend());\n"
    )
    res = subprocess.run(
        ["node", "--loader", TS_NODE_LOADER.resolve().as_posix(), script],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "webgpu"


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
def test_llm_no_gpu_backend(tmp_path: Path) -> None:
    reason = _skip_reason()
    if reason:
        pytest.skip(reason)
    script = tmp_path / "run.mjs"
    script.write_text(
        f"globalThis.navigator = {{}};\n"
        f"globalThis.localStorage = {{ getItem: () => null }};\n"
        f"const m = await import('{LLM.resolve().as_posix()}');\n"
        "console.log(await m.gpuBackend());\n"
    )
    res = subprocess.run(
        ["node", "--loader", TS_NODE_LOADER.resolve().as_posix(), script],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "wasm-simd"
