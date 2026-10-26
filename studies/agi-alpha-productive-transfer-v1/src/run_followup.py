# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    destination = ROOT / "results/followup"
    destination.mkdir(exist_ok=False)
    freeze_path = ROOT / "protocol/followup-candidate-freeze.json"
    freeze = json.loads(freeze_path.read_text())
    inputs = json.loads((ROOT / "protocol/followup-input-freeze.json").read_text())
    protocol = json.loads((ROOT / "protocol/followup-protocol.json").read_text())
    start = dt.datetime.now(dt.UTC).isoformat()
    attempts = []
    for index, task in enumerate(inputs["tasks"]):
        if sha(ROOT / task["path"]) != task["sha256"]:
            raise ValueError("frozen input changed")
        (destination / task["id"]).mkdir()
        for arm in protocol["execution"]["order"][index].split(","):
            for row in freeze["files"]:
                if sha(ROOT / row["path"]) != row["sha256"]:
                    raise ValueError("frozen candidate changed")
            out = destination / task["id"] / arm
            command = ["node", str(ROOT / "src/workbench_v2.mjs"), str(ROOT / task["path"]), arm, str(out)]
            proposal = None
            if arm != "C":
                suffix = "request" if arm == "A" else "response"
                proposal = ROOT / f"transcripts/followup/{arm}/{task['id']}.{suffix}.json"
                command.append(str(proposal))
            resource = ROOT / f"resources/followup-{task['id']}-{arm}"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "src/meter.py"),
                    "--phase",
                    "fresh-followup-confirmation",
                    "--out",
                    str(resource),
                    "--timeout",
                    "45",
                    "--",
                    *command,
                ],
                capture_output=True,
                timeout=50,
                check=False,
            )
            (destination / task["id"] / f"{arm}-meter-stdout.txt").write_bytes(completed.stdout)
            (destination / task["id"] / f"{arm}-meter-stderr.txt").write_bytes(completed.stderr)
            result_path = out / "delivery/result.json"
            attempts.append(
                {
                    "mission": task["id"],
                    "arm": arm,
                    "exitCode": completed.returncode,
                    "resourceReceipt": str((resource / "receipt.json").relative_to(ROOT)),
                    "inputSha256": task["sha256"],
                    "proposalSha256": sha(proposal) if proposal else None,
                    "resultSha256": sha(result_path) if result_path.exists() else None,
                    "attempt": 1,
                    "retried": False,
                }
            )
            print(
                json.dumps({"mission": task["id"], "arm": arm, "exitCode": completed.returncode}), flush=True
            )
    entries = [
        {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)}
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    ]
    campaign = {
        "schema": "agi-alpha-fresh-transfer-campaign/v1",
        "startedAt": start,
        "sealedAt": dt.datetime.now(dt.UTC).isoformat(),
        "candidateFreezeSha256": sha(freeze_path),
        "inputFreezeSha256": sha(ROOT / "protocol/followup-input-freeze.json"),
        "attempts": attempts,
        "payloads": entries,
        "oracleViewed": False,
        "scope": "Separately registered fresh historical source work packages, three arms; local model-backed curator/extraction plus actual Workbench execution. Not customers or field-reliability trials.",
    }
    (destination / "campaign.json").write_text(json.dumps(campaign, indent=2) + "\n")
    print(
        json.dumps(
            {
                "campaignSha256": sha(destination / "campaign.json"),
                "attempts": len(attempts),
                "failedExecutions": sum(x["exitCode"] != 0 for x in attempts),
            }
        )
    )


if __name__ == "__main__":
    main()
