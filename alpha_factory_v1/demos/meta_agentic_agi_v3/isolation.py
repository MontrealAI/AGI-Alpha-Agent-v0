# SPDX-License-Identifier: Apache-2.0
"""Route all legacy generated Python through the repository's Docker boundary."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

from alpha_factory_v1.core.utils.secure_run import secure_run


def run_python(
    code: str, function: str | None = None, args: tuple[Any, ...] = (), kwargs: dict[str, Any] | None = None
) -> str:
    """Return bounded sandbox stdout; fail closed if Docker is unavailable."""
    if not isinstance(code, str) or not code.strip() or len(code.encode()) > 16000:
        raise ValueError("Python source must contain 1–16000 UTF-8 bytes")
    payload = json.dumps({"args": args, "kwargs": kwargs or {}}, allow_nan=False)
    if len(payload.encode()) > 4096:
        raise ValueError("Arguments exceed 4096 bytes")
    if function is not None:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", function):
            raise ValueError("Invalid function name")
        code += (
            f"\nimport json\n_payload=json.loads({payload!r})\n"
            f"print(json.dumps({function}(*_payload['args'], **_payload['kwargs']), allow_nan=False))\n"
        )
    with tempfile.TemporaryDirectory(prefix="metaagi-code-") as temp:
        script = Path(temp) / "candidate.py"
        script.write_text(code, encoding="utf-8")
        result = secure_run([sys.executable, str(script)])
    if result.returncode:
        raise RuntimeError(f"Isolated program failed ({result.returncode}): {result.stderr[:1000]}")
    return str(result.stdout).strip()
