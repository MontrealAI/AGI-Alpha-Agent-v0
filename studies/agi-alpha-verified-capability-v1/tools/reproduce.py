# SPDX-License-Identifier: Apache-2.0
"""Plan or execute a new isolated reproduction; never replace original outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from packaging.markers import default_environment
from verify_frozen import verify

ROOT = Path(__file__).resolve().parents[1]


def execute(command: list[str], root: Path, label: str, timeout: int) -> None:
    logs = root / "reproduction-logs"
    logs.mkdir(exist_ok=True)
    with (logs / f"{label}.stdout.txt").open("x") as out, (logs / f"{label}.stderr.txt").open("x") as err:
        result = subprocess.run(command, cwd=root, stdout=out, stderr=err, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit {result.returncode}; all partial evidence retained")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--run", action="store_true", help="Execute after all custody/environment checks")
    args = parser.parse_args()
    target = args.destination.resolve()
    if target.exists() or target.is_relative_to(ROOT) or ROOT.is_relative_to(target):
        raise ValueError("A fresh isolated destination outside the source tree is required")
    plan = {"classification": "NEW_REPRODUCTION_NOT_ORIGINAL_CONFIRMATION", "destination": str(target),
            "steps": ["Verify immutable production source and all47wheel hashes",
                      "Require exact frozen platform markers, Python/pip/packaging and Node versions",
                      "Copy only reproducibility inputs to a fresh directory; preserve original tree",
                      "Run the same18questions/four arms once; keep every partial failure",
                      "Bind new measured production bytes in a new market freeze",
                      "Run exactly the unchanged48cells/24seeds once; no tuning or retry"],
            "network_requests": 0, "credentials": 0, "model_calls": 0, "actual_transactions": 0}
    print(json.dumps(plan, indent=2))
    if not args.run:
        return
    verify(ROOT, "protocol/production-freeze.json")
    manifest = json.loads((ROOT / "inputs/missions-v1/manifest.json").read_text())
    expected = json.loads((ROOT / manifest["jobs"][0]["job"]).read_text())["target_environment"]
    if expected != default_environment():
        raise ValueError("Frozen environment differs; revalidation needs a separate protocol, not silent retargeting")
    import pip
    import packaging
    node = subprocess.check_output(["node", "--version"], text=True).strip()
    if sys.version_info[:3] != (3, 12, 14) or pip.__version__ != "26.2.2" or packaging.__version__ != "26.3" or node != "v24.22.1":
        raise ValueError("Exact recorded interpreter/tool versions required for this reproduction")

    def ignore(directory: str, names: list[str]) -> list[str]:
        relative = Path(directory).relative_to(ROOT)
        excluded = {"__pycache__", ".git", "selected-wheels", "browser-review"}
        if relative == Path("evidence"):
            excluded.update({"production-primary", "market-primary", "production-summary.json"})
        if relative == Path("demo"):
            excluded.add("index.html")
        if relative == Path("paper"):
            excluded.add("build")
        return [name for name in names if name in excluded]

    shutil.copytree(ROOT, target, ignore=ignore)
    (target / "REPRODUCTION.json").write_text(json.dumps({**plan,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_results_preserved_at": str(ROOT)}, indent=2) + "\n")
    execute(["node", "src/run_campaign.mjs", "--run", "--freeze", "protocol/production-freeze.json",
             "--output", "evidence/production-primary"], target, "production", 900)
    prior = json.loads((target / "protocol/market-freeze.json").read_text())
    rows = []
    for row in prior["files"]:
        data = (target / row["path"]).read_bytes()
        rows.append({"path": row["path"], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    fresh = {"schema": prior["schema"], "marketOutcomesInspected": False,
             "classification": "REPRODUCTION_WITH_NEW_TIMING_CALIBRATION",
             "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
             "original_market_freeze_sha256": hashlib.sha256((target / "protocol/market-freeze.json").read_bytes()).hexdigest(),
             "files": rows}
    with (target / "protocol/reproduction-market-freeze.json").open("x") as out:
        out.write(json.dumps(fresh, indent=2) + "\n")
    execute(["node", "market/run-campaign.mjs", "--run", "--freeze", "protocol/reproduction-market-freeze.json",
             "--output", "evidence/market-primary"], target, "market", 200)
    print(json.dumps({"status": "REPRODUCTION_COMPLETE", "path": str(target),
                      "warning": "This is a new reproduction, not another sample in the frozen original study."}))


if __name__ == "__main__":
    main()
