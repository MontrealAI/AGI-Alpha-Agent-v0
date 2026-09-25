# SPDX-License-Identifier: Apache-2.0
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

LLM = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/src/utils/llm.ts")
TSX_LOADER = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/node_modules/tsx/dist/loader.mjs")
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
        return "Node.js 22+ required for tsx loader"
    if not TSX_LOADER.is_file():
        return "tsx loader not installed"
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
        'Object.defineProperty(globalThis, "navigator", {value: {gpu: {}}, configurable: true});\n'
        "const saved = new Map();\n"
        "globalThis.localStorage = { getItem: k => saved.get(k), setItem: (k,v) => saved.set(k,v), "
        "removeItem: k => saved.delete(k) };\n"
        f"const m = await import('{LLM.resolve().as_posix()}');\n"
        "m.setUseGpu(true);\n"
        "console.log(JSON.stringify({available:m.gpuAvailable, backend:await m.gpuBackend(), "
        "preference:saved.get('USE_GPU')}));\n"
    )
    res = subprocess.run(
        ["node", "--import", TSX_LOADER.resolve().as_posix(), script],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    # Hardware capability and the retained GPU preference must not falsely label
    # the pinned quantized model, which is actually executed through WASM.
    assert json.loads(res.stdout) == {"available": True, "backend": "wasm-simd", "preference": "1"}


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
def test_llm_no_gpu_backend(tmp_path: Path) -> None:
    reason = _skip_reason()
    if reason:
        pytest.skip(reason)
    script = tmp_path / "run.mjs"
    script.write_text(
        'Object.defineProperty(globalThis, "navigator", {value: {}, configurable: true});\n'
        f"globalThis.localStorage = {{ getItem: () => null }};\n"
        f"const m = await import('{LLM.resolve().as_posix()}');\n"
        "console.log(JSON.stringify({available:m.gpuAvailable, backend:await m.gpuBackend()}));\n"
    )
    res = subprocess.run(
        ["node", "--import", TSX_LOADER.resolve().as_posix(), script],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout) == {"available": False, "backend": "wasm-simd"}
