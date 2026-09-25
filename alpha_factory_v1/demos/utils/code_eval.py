# SPDX-License-Identifier: Apache-2.0
"""Evaluate the built-in identity fixture; isolate every other program in Docker."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import tempfile

from alpha_factory_v1.core.utils.secure_run import secure_run


def evaluate(code: str, value: object, function: str = "main") -> tuple[str, str]:
    """Return JSON output and error without running generated code on the host.

    The exact identity fixture is evaluated as data for the offline tutorial.
    All other programs use the same Docker boundary as agent coding missions.
    """
    if function not in {"main", "agent"} or len(code) > 16000:
        return "", "Unsupported function or program size"
    try:
        payload = json.dumps(value)
        if len(payload) > 4096:
            return "", "Input exceeds 4096 characters"
        parsed = ast.parse(code)
        identity = ast.parse(f"def {function}(x):\n    return x")
        if ast.dump(parsed) == ast.dump(identity):
            return json.dumps(value, separators=(",", ":")), ""
        # repr embeds the JSON as a string, never as executable Python.
        wrapper = (
            code + f"\nimport json\nprint(json.dumps({function}(json.loads({payload!r})), separators=(',', ':')))\n"
        )
        with tempfile.TemporaryDirectory(prefix="alpha-demo-code-") as temp:
            script = Path(temp) / "candidate.py"
            script.write_text(wrapper, encoding="utf-8")
            result = secure_run([sys.executable, str(script)])
        error = result.stderr.strip()
        if result.returncode and not error:
            error = f"Sandbox exited with status {result.returncode}"
        return result.stdout.strip(), error
    except Exception as exc:
        return "", str(exc)
