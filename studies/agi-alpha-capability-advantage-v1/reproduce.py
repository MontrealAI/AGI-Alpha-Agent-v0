# SPDX-License-Identifier: Apache-2.0
"""Verify or replay the frozen Capability Advantage research companion.

Default operation checks identities and reconciles preserved primary evidence.
It does not execute a solver, spend money, authenticate an ENS identity, or rerun
the market. An explicitly requested replay is an archival reproducibility check,
never an additional independent observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def verify_manifest(path: Path, base: Path) -> dict:
    document = json.loads(path.read_text())
    failures = []
    for item in document["files"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe manifest path: {relative}")
        source = base / relative
        if not source.is_file():
            failures.append({"path": str(relative), "reason": "missing"})
            continue
        data = source.read_bytes()
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            failures.append({"path": str(relative), "reason": "identity mismatch"})
    return {"manifest": str(path.relative_to(ROOT)), "files": len(document["files"]), "failures": failures}


def command(arguments: list[str]) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(arguments, cwd=ROOT, env=environment, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reverify-vectors", action="store_true", help="Run the frozen independent verifier on preserved numerical vectors; no solver rerun")
    parser.add_argument("--audit-market", action="store_true", help="Reconcile every saved financial history without executing the market model")
    parser.add_argument("--execute-primary", metavar="NEW_OUTPUT", type=Path, help="Replay all 144 archived arm-stage evaluations into a new directory beneath this study")
    parser.add_argument("--execute-market", metavar="NEW_OUTPUT", type=Path, help="Replay the frozen 2,304 simulated worlds into a new directory beneath this study")
    args = parser.parse_args()
    checks = [verify_manifest(ROOT / "protocol/production-freeze.json", ROOT)]
    market = ROOT / "economics/market-freeze.json"
    if market.exists():
        checks.append(verify_manifest(market, market.parent))
    print(json.dumps({"source_identity_checks": checks}, indent=2))
    if any(check["failures"] for check in checks):
        raise SystemExit("Frozen identity verification failed; do not execute changed research code as the registered study.")
    audit_output = ROOT / "replays" / ("audit-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    audit = [sys.executable, "audit-final/reconcile_primary.py", "--output-dir", str(audit_output)]
    if args.reverify_vectors:
        audit.append("--reverify-preserved-vectors")
    command(audit)
    if market.exists():
        command(["node", "economics/run_market.mjs", "--validate-only", "--protocol=economics/market-protocol.json", "--freeze=economics/market-freeze.json"])
        if args.audit_market:
            command([sys.executable, "audit-final/reconcile_market.py", "--output-dir", str(audit_output)])
    for selected, kind in [(args.execute_primary, "primary"), (args.execute_market, "market")]:
        if selected is None:
            continue
        output = (ROOT / selected).resolve()
        if not output.is_relative_to(ROOT) or output == ROOT or output.exists():
            raise SystemExit("Replay output must be a new directory beneath this extracted study.")
        output.parent.mkdir(parents=True, exist_ok=True)
        if kind == "primary":
            command([sys.executable, "production/run_campaign.py", "--cohort", "primary", "--arms", "ABCD", "--catalog", "--replay", "--limit", "2700", "--output", str(output)])
        else:
            command(["node", "economics/run_market.mjs", "--protocol=economics/market-protocol.json", "--freeze=economics/market-freeze.json", "--output=" + str(output)])
    print("Verification complete. Replays, if requested, are archival checks and do not enlarge the original sample.")


if __name__ == "__main__":
    main()
