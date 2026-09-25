# SPDX-License-Identifier: Apache-2.0
"""Persistent non-root container entry point; publish ports on host loopback only."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from .api import create_app
from .store import Journal


def main() -> None:
    """Initialize a new mounted home once, then serve its authenticated console."""
    root = Path(os.getenv("ALPHA_AGENT_HOME", "/data/agent"))
    journal = Journal(root) if root.is_dir() and any(root.iterdir()) else Journal.initialize(root, allow_empty=True)
    journal.verify()
    print(f'AGIALPHA operator token file: {root / "api.token"}', flush=True)
    uvicorn.run(create_app(journal), host="0.0.0.0", port=8000, access_log=False)


if __name__ == "__main__":
    main()
