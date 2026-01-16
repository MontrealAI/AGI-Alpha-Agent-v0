# SPDX-License-Identifier: Apache-2.0
"""Tests for the JavaScript state serializer."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SERIALIZER_TS = Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/src/state/serializer.ts")


def _compile_serializer(tmp_path: Path) -> Path:
    (tmp_path / "package.json").write_text('{"type":"module"}', encoding="utf-8")
    js_out = tmp_path / SERIALIZER_TS.with_suffix(".js")
    subprocess.run(
        [
            "tsc",
            "--target",
            "es2020",
            "--module",
            "es2020",
            "--outDir",
            str(tmp_path),
            "--rootDir",
            ".",
            SERIALIZER_TS,
        ],
        check=True,
    )
    return js_out


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
def test_js_serializer_roundtrip(tmp_path: Path) -> None:
    js_out = _compile_serializer(tmp_path)
    script = tmp_path / "run.mjs"
    script.write_text(
        f"import {{save, load}} from '{js_out.resolve().as_posix()}';\n"
        "const data = JSON.parse(process.argv[2]);\n"
        "const pop = data.pop;\n"
        "if (data.gen !== undefined) pop.gen = data.gen;\n"
        "const out = load(save(pop, data.rngState));\n"
        "console.log(JSON.stringify(out));\n"
    )

    sample = {
        "pop": [
            {"logic": 1.1, "feasible": 0.2, "front": 0, "strategy": "s"},
            {"logic": 2.3, "feasible": 0.4, "front": 1, "strategy": "t"},
        ],
        "gen": 5,
        "rngState": [1, 2, 3, 4],
    }

    result = subprocess.run(["node", script, json.dumps(sample)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    loaded = json.loads(result.stdout)
    assert loaded == sample


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
@pytest.mark.parametrize(
    "payload",
    [
        {"pop": [{"logic": "a", "feasible": 1}]},
        {"pop": [{"logic": 1, "feasible": "b"}]},
        {"pop": [{"logic": 1, "feasible": 2, "extra": True}]},
        {"pop": [], "extra": 1},
    ],
)
def test_js_serializer_rejects_invalid(tmp_path: Path, payload: dict) -> None:
    js_out = _compile_serializer(tmp_path)
    script = tmp_path / "run.mjs"
    script.write_text(
        f"import {{load}} from '{js_out.resolve().as_posix()}';\n"
        "try {\n"
        "  const out = load(process.argv[2]);\n"
        "  console.log(JSON.stringify(out));\n"
        "} catch (err) {\n"
        "  console.error(err.message);\n"
        "  process.exit(1);\n"
        "}\n"
    )
    result = subprocess.run(["node", script, json.dumps(payload)], capture_output=True, text=True)
    assert result.returncode == 1


@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
def test_js_serializer_malformed_json(tmp_path: Path) -> None:
    js_out = _compile_serializer(tmp_path)
    script = tmp_path / "run.mjs"
    script.write_text(
        f"import {{load}} from '{js_out.resolve().as_posix()}';\n"
        "try {\n"
        "  load(process.argv[2]);\n"
        "} catch (err) {\n"
        "  console.error(err.message);\n"
        "  process.exit(1);\n"
        "}\n"
    )
    result = subprocess.run(["node", script, "{invalid"], capture_output=True, text=True)
    assert result.returncode == 1
