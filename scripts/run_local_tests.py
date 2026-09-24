#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run offline tests with a clean credential environment and loopback-only Python sockets."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def main() -> int:
    """Preserve only execution settings, never ambient service credentials."""
    root = Path(__file__).resolve().parents[1]
    keep = {
        "PATH",
        "HOME",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "LANG",
        "LC_ALL",
        "VIRTUAL_ENV",
        "PLAYWRIGHT_BROWSERS_PATH",
    }
    env = {name: value for name, value in os.environ.items() if name in keep}
    # Resolve the compiler from the checked-in browser lockfile's installation,
    # rather than requiring an unrelated global TypeScript version.
    browser_bin = root / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/node_modules/.bin"
    env["PATH"] = str(browser_bin) + os.pathsep + env.get("PATH", "")
    env.update(
        {
            "ALPHA_TEST_OFFLINE": "1",
            "PYTEST_NET_OFF": "1",
            "OPENAI_AGENTS_DISABLE_TRACING": "true",
            "ALPHA_ASI_DISABLE_AGENT_THREADS": "1",
            "NO_PROXY": "*",
            "NO_DISCLAIMER": "1",
            "PYTHONPATH": os.pathsep.join((str(root / "scripts" / "test_support"), str(root))),
            "NEO4J_PASSWORD": "local-tests-only-strong-password",
            "API_TOKEN": "test-token",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    return subprocess.call([sys.executable, "-m", "pytest", *sys.argv[1:]], cwd=root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
