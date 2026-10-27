# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evaluation"))
from conventional import review
from legal_packet import check_packet, packet, render_html


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", choices=["development", "primary", "stress"], required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = ROOT / args.output
    if out.exists():
        raise ValueError("REFUSE_OVERWRITE_CAMPAIGN")
    out.mkdir(parents=True)
    records = []
    packaging = []
    arms = ["B", "C1", "C", "D", "T"]
    for i, path in enumerate(sorted((ROOT / "inputs" / args.cohort).glob("*.json"))):
        case = json.loads(path.read_text())
        for arm in arms[i % 5 :] + arms[: i % 5]:
            started, cpu = time.perf_counter(), time.process_time()
            result = review(case) if arm == "D" else packet(case, "C" if arm == "T" else arm)
            if arm != "D":
                errors = check_packet(case, result)
                if errors:
                    raise ValueError(";".join(errors))
            envelope = {"arm": arm, "request": case, "packet": result}
            destination = out / case["case_id"] / arm
            destination.mkdir(parents=True)
            encoded = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
            (destination / "produced.json").write_text(encoded)
            (destination / "review-packet.html").write_text(render_html(case, result))
            elapsed, cpu_used = time.perf_counter() - started, time.process_time() - cpu
            records.append(
                {
                    "case_id": case["case_id"],
                    "arm": arm,
                    "cohort": args.cohort,
                    "runtime_seconds": elapsed,
                    "cpu_seconds": cpu_used,
                    "attempts": 1,
                    "accepted_deterministic": None,
                    "professional_acceptance": "unknown",
                    "escalation_required": bool(result["escalations"]),
                    "measured_review_minutes": None,
                    "provider_cost": None,
                    "outcome_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
                    "output": str(destination.relative_to(ROOT)),
                    "observed_at": datetime.now(UTC).isoformat(),
                }
            )
            packaging.append(
                {
                    "input": str((destination / "produced.json").relative_to(ROOT)),
                    "output": str((destination / "workbench.json").relative_to(ROOT)),
                }
            )
    (out / "analysis-records.json").write_text(json.dumps(records, indent=2) + "\n")
    (out / "packaging-manifest.json").write_text(json.dumps(packaging, indent=2) + "\n")
    print(json.dumps({"cohort": args.cohort, "evaluations": len(records), "output": str(out)}))


if __name__ == "__main__":
    main()
