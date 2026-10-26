"""Build the offline, self-contained bilingual study demonstration."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ACQ = ROOT / "independent" / "acquisition"


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path)
    parser.add_argument("--economics", type=Path)
    parser.add_argument("--market-analysis", type=Path)
    parser.add_argument("--market-completion", type=Path)
    parser.add_argument("--market-representative", type=Path)
    parser.add_argument("--market-protocol", type=Path)
    args = parser.parse_args()
    summary = read(ACQ / "comparison_summary.json")
    outcomes = read(ACQ / "panel" / "outcomes.json")
    costs = read(ACQ / "cost_records.json")
    protocol = read(ACQ / "protocol.json")
    freeze = read(ACQ / "source_freeze.json")
    contribution = read(ACQ / "contribution_manifest.json")
    chains = []
    for spec in protocol["chains"]:
        chain = dict(spec)
        chain["nodes"] = spec["profile"]["side"] ** 2
        chain["stages"] = {}
        for family in protocol["stages"]:
            pair = {}
            for method in protocol["method_execution_order"]:
                record = next(
                    r for r in outcomes["outcomes"]
                    if r["chain_id"] == spec["id"]
                    and r["family"] == family and r["method"] == method
                )
                pair[method] = record
            chain["stages"][family] = pair
        chain["complete_chain"] = {}
        for method in protocol["method_execution_order"]:
            records = [chain["stages"][family][method] for family in protocol["stages"]]
            first = min(datetime.fromisoformat(r["start_utc"]) for r in records)
            last = max(datetime.fromisoformat(r["end_utc"]) for r in records)
            chain["complete_chain"][method] = {
                "elapsed_wall_seconds": (last - first).total_seconds(),
                "sum_recorded_stage_wall_seconds": sum(r["stage_total_wall_seconds"] for r in records),
                "sum_solver_wall_seconds": sum(r["method_call_wall_seconds"] for r in records),
                "accepted_stages": sum(r["accepted"] for r in records),
            }
        chains.append(chain)
    sources = []
    for path in [
        ACQ / "comparison_summary.json", ACQ / "panel" / "outcomes.json",
        ACQ / "cost_records.json", ACQ / "protocol.json",
        ACQ / "amendment_001.json", ACQ / "source_freeze.json",
        ACQ / "contribution_manifest.json",
    ]:
        sources.append({
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    data = {
        "schema": "capability-advantage-offline-demo/v1",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "panel_scope": "preregistered-development-transfer",
        "chains": chains,
        "summary": summary,
        "costs": costs,
        "protocol": protocol,
        "freeze": freeze,
        "contribution": contribution,
        "sources": sources,
        "primary": {"status": "awaiting_registered_run", "data": None},
        "economics": {"status": "awaiting_registered_run", "data": None},
    }
    if args.primary:
        data["primary"] = {"status": "available", "data": read(args.primary)}
        data["sources"].append({
            "path": str(args.primary), "sha256": hashlib.sha256(args.primary.read_bytes()).hexdigest()
        })
    if args.economics:
        data["economics"] = {"status": "available", "data": read(args.economics)}
        data["sources"].append({
            "path": str(args.economics), "sha256": hashlib.sha256(args.economics.read_bytes()).hexdigest()
        })
    for key, path in [
        ("analysis", args.market_analysis), ("completion", args.market_completion),
        ("representative", args.market_representative), ("protocol", args.market_protocol),
    ]:
        if path:
            data["economics"][key] = read(path)
            data["sources"].append({
                "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
            })
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    template = (HERE / "demo_template.html").read_text()
    if template.count("__EMBEDDED_STUDY_DATA__") != 1:
        raise ValueError("Expected one embedded-data placeholder")
    result = template.replace("__EMBEDDED_STUDY_DATA__", encoded)
    target = HERE / "The_Capability_Advantage_EN_FR.html"
    target.write_text(result)
    receipt = {
        "output": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "bytes": target.stat().st_size, "built_utc": data["built_utc"],
        "input_sources": data["sources"],
        "primary_status": data["primary"]["status"], "economics_status": data["economics"]["status"],
        "external_assets": False, "network_required": False,
    }
    (HERE / "build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
