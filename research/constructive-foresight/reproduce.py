# SPDX-License-Identifier: Apache-2.0
"""Prepare a fresh isolated replication, preserving the original frozen evidence."""
from __future__ import annotations
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="A new directory; existing paths are refused")
    args = parser.parse_args()
    dest = args.destination.resolve()
    if dest.exists() or dest == ROOT or ROOT in dest.parents:
        raise ValueError("Use a new directory outside the archived research tree")
    dest.mkdir(parents=True, exist_ok=False)
    files = ["protocol.json", "decision_protocol.json", "numerics.py", "decision.py", "run_logged.py",
             "analyze.py", "analyze_decisions.py", "check_results.py", "check_decision.py", "requirements.txt"]
    for name in files:
        shutil.copy2(ROOT / name, dest / name)
    shutil.copytree(ROOT / "data", dest / "data")
    (dest / "REPLICATION.json").write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Fresh replication of the archived protocol; original outcomes and forecasts remain unchanged",
        "source_tree": str(ROOT), "credentials_required": False,
        "commands_in_order": ["python numerics.py development", "python numerics.py calibration",
                              "python numerics.py freeze", "python numerics.py confirmation", "python analyze.py"],
        "warning": "Run confirmation within the new freeze's launch window. Do not copy or edit the original freeze."
    }, indent=2) + "\n")
    print(f"Prepared {dest}; no experiment has been executed. See REPLICATION.json and README.md in the source archive.")


if __name__ == "__main__":
    main()
