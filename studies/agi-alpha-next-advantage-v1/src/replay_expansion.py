# SPDX-License-Identifier: Apache-2.0
"""Replay the frozen supplement with its original, content-verified source."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def stage(destination: Path) -> None:
    protocol_path = ROOT / "config/expansion_frontier_protocol.json"
    protocol = json.loads(protocol_path.read_text())
    substitutions = {
        "src/economics.py": "evidence/expansion_source_snapshot/economics.py",
        "config/economics.json": "evidence/expansion_source_snapshot/economics.json",
        "config/economic_protocol.json": "evidence/expansion_source_snapshot/economic_protocol.json",
    }
    for relative, expected in protocol["inputs"].items():
        source = ROOT / substitutions.get(relative, relative)
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen supplement dependency changed: " + relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    shutil.copyfile(protocol_path, destination / "config/expansion_frontier_protocol.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="next-advantage-supplement-") as folder:
        destination = Path(folder)
        stage(destination)
        if args.verify_only:
            print(json.dumps({"status": "PASS", "frozen_inputs_verified": True}))
        else:
            subprocess.run(
                [sys.executable, str(destination / "src/expansion_frontier.py"),
                 "--output", str(args.output.resolve())],
                check=True,
            )


if __name__ == "__main__":
    main()
