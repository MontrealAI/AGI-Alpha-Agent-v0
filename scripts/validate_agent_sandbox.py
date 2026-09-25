#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require Docker and validate code missions against real isolated execution."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission, RuntimeConfig
from alpha_factory_v1.core.runtime.store import Journal, digest
from alpha_factory_v1.core.utils.secure_run import secure_run
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not shutil.which("docker"):
        raise RuntimeError("Docker is a required release gate, not an optional skip")
    with tempfile.TemporaryDirectory(prefix="alpha-code-validation-") as temp:
        journal = Journal.initialize(Path(temp) / "agent", RuntimeConfig(allow_code_execution=True))
        root = Path(__file__).resolve().parents[1]
        mission = Mission.model_validate_json((root / "examples/missions/code.json").read_bytes())
        engine = Engine(journal)
        record = engine.execute(journal.submit(mission)["id"])
        assert record["result"]["accuracy"] == 1.0
        engine.review(record["id"], record["revision"], digest(record["result"]), True, "Verified held-out cases")
        assert engine.export(record["id"])["receipt"]["body"]["document"]["state"] == "completed"
        bad = mission.model_dump()
        bad["work"]["candidate"] = "def solve(values): return 0"
        ident = journal.submit(Mission.model_validate(bad))["id"]
        try:
            engine.execute(ident)
            raise AssertionError("incorrect candidate accepted")
        except ValueError:
            pass
        assert journal.latest(ident)["state"] == "failed"
        assert journal.latest(ident)["failed_result"]["accuracy"] < 1
        result = secure_run(["python3", "-c", 'import os; print(os.getuid()); print(os.path.exists("/work/.env"))'])
        assert result.returncode == 0 and result.stdout.strip() == "65534\nFalse"
        readonly = secure_run(["python3", "-c", 'open("/host-write-probe", "w").write("blocked")'])
        assert readonly.returncode != 0
        network = secure_run(["python3", "-c", 'import socket; socket.create_connection(("1.1.1.1",443),timeout=2)'])
        assert network.returncode != 0
        try:
            secure_run(["python3", "-c", 'print("x" * (2 * 1024 * 1024))'])
            raise AssertionError("unbounded output accepted")
        except ValueError:
            pass
        evidence = {
            "passed": True,
            "backend": "Docker",
            "checks": [
                "correct code approved and exported",
                "incorrect code rejected with retained evidence",
                "non-root uid",
                "host files absent",
                "root filesystem read-only",
                "outbound network denied",
                "output limited to 1 MiB",
            ],
            "journal": journal.verify(),
        }
        args.output.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence))


if __name__ == "__main__":
    main()
