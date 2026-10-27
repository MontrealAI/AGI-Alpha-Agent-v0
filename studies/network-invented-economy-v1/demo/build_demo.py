# SPDX-License-Identifier: Apache-2.0
"""Embed retained research evidence in an offline bilingual HTML demonstration."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def project_samples(samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Keep every saved UI record while omitting bulky, separately supplied audits.

    Monetary totals, policies, every week, every event, cost books and lineage
    records retain their original values. Full ledgers and outcome duplicates
    remain in the input evidence companion; large paired-probe arrays remain in
    that companion rather than being copied into a browser presentation.
    """
    projected = []
    counts = {"ledger_rows_omitted": 0, "duplicate_outcome_rows_omitted": 0, "paired_probe_arrays_omitted": 0}

    def alpha_summary(value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if "paired_probes" in value:
            counts["paired_probe_arrays_omitted"] += 1
        return {key: item for key, item in value.items() if key not in {"paired_probes", "assumptions"}}

    for sample in samples:
        result = {key: value for key, value in sample.items() if key not in {"ledger", "outcomes"}}
        counts["ledger_rows_omitted"] += len(sample.get("ledger", []))
        counts["duplicate_outcome_rows_omitted"] += len(sample.get("outcomes", []))
        for collection in ("events", "skills"):
            if collection in sample:
                result[collection] = [
                    {key: alpha_summary(value) if key in {"alpha", "alpha_assessment"} else value
                     for key, value in record.items()}
                    for record in sample[collection]
                ]
        projected.append(result)
    return projected, {
        **counts,
        "records_truncated": False,
        "weekly_values_and_cost_totals_changed": False,
        "full_data_location": "results/demo_data.json and the complete evidence companion",
        "scope": "Presentation projection only; all saved weeks/events retained, no model rerun or outcome selection.",
    }


def project_sensitivity(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Retain all cases and only the aggregate fields displayed by the demo."""
    fields = ("profit", "accepted_useful", "retention_count", "investment_count")
    statistics = ("mean", "lower", "upper", "n")
    result = []
    for row in rows:
        record = {key: row[key] for key in ("case", "arm") if key in row}
        for key in fields:
            if isinstance(row.get(key), dict):
                record[key] = {stat: row[key][stat] for stat in statistics if stat in row[key]}
        result.append(record)
    return result, {
        "records_retained": len(result), "records_omitted": 0,
        "displayed_metrics": list(fields), "displayed_statistics": list(statistics),
        "values_changed": False,
        "other_metrics_location": "results/demo_data.json and the complete evidence companion",
    }


def build(data_path: Path, output: Path, commercial_path: Path | None = None) -> dict[str, Any]:
    """Use saved histories when supplied, otherwise show an honest witness-only edition."""
    root = Path(__file__).resolve().parents[1]
    provenance: dict[str, Any] = {"generated_at_utc": datetime.now(UTC).isoformat(), "inputs": {}}
    data: dict[str, Any] = {"summary": {}, "samples": [], "sensitivity": []}
    if data_path.is_file():
        raw = data_path.read_bytes()
        loaded = json.loads(raw)
        if not isinstance(loaded, dict) or not isinstance(loaded.get("samples", []), list):
            raise ValueError("demo data must be an object with an optional samples array")
        data.update(loaded)
        provenance["inputs"][str(data_path)] = hashlib.sha256(raw).hexdigest()
    if commercial_path is None and data_path.resolve() == (root / "results/demo_data.json").resolve():
        commercial_path = root / "results/commercial_core.json"
    if commercial_path is not None and commercial_path.is_file():
        commercial_raw = commercial_path.read_bytes()
        commercial = json.loads(commercial_raw)
        # An explicitly supplied register may accompany a reproduced confirmation.
        # Refuse stale reporting attached to a different scenario or result set.
        for name, scenario in commercial.get("scenarios", {}).items():
            baseline = data.get("summary", {}).get("scenarios", {}).get(name, {}).get("beta", {})
            for metric in ("profit", "collections", "accepted_useful", "available_cash"):
                reported = scenario.get("metrics", {}).get(metric, {}).get("mean")
                observed = baseline.get(metric, {}).get("mean")
                if not isinstance(reported, (float, int)) or not isinstance(observed, (float, int)):
                    raise ValueError(f"commercial register lacks matching saved summary: {name}/{metric}")
                if not math.isclose(reported, observed, rel_tol=1e-12, abs_tol=1e-7):
                    raise ValueError(f"commercial register differs from saved summary: {name}/{metric}")
        commercial["scenarios"] = {
            name: {key: value for key, value in scenario.items() if key != "world_values"}
            for name, scenario in commercial.get("scenarios", {}).items()
        }
        data["commercial_core"] = commercial
        commercial_reference = ("results/commercial_core.json" if commercial_path.resolve() ==
                                (root / "results/commercial_core.json").resolve() else str(commercial_path))
        provenance["inputs"][commercial_reference] = hashlib.sha256(commercial_raw).hexdigest()
        provenance["commercial_projection"] = {
            "all_scenarios_and_aggregate_values_retained": True,
            "per_world_values_omitted_from_display_copy": True,
            "full_register": commercial_reference,
        }
        provenance["reporting_amendment"] = {
            "kind": "editorial-priority-only",
            "priority": "Profitable work first; compounding capability when worthwhile.",
            "prior_edition": "evidence/editorial-priority-v1/demo/index.html",
            "prior_html_sha256": "9979955ef2e483ce2e92faf57cc1df110fe280a11f9f2487e1ccb10f58deb4d9",
            "scientific_results_changed": False,
            "new_economic_policy_selection": False,
        }
    for key, relative in (("mechanism", "evidence/mechanism_witness.json"), ("graph", "evidence/graph_demo.json")):
        if key not in data:
            source = root / relative
            if source.is_file():
                raw = source.read_bytes()
                data[key] = json.loads(raw)
                provenance["inputs"][relative] = hashlib.sha256(raw).hexdigest()
            else:
                data[key] = {}
    data["samples"], projection = project_samples(data.get("samples", []))
    provenance["presentation_projection"] = projection
    if isinstance(data.get("sensitivity"), list):
        data["sensitivity"], sensitivity_projection = project_sensitivity(data["sensitivity"])
        provenance["sensitivity_projection"] = sensitivity_projection
    # Only bind the official saved-data input to its adjacent protocol. Temporary
    # UI fixtures must not inherit the identity of the confirmation experiment.
    protocol_path = root / "results/protocol_freeze.json"
    if data_path.resolve() == (root / "results/demo_data.json").resolve() and protocol_path.is_file():
        raw_protocol = protocol_path.read_bytes()
        protocol = json.loads(raw_protocol)
        provenance["inputs"]["results/protocol_freeze.json"] = hashlib.sha256(raw_protocol).hexdigest()
        provenance["protocol"] = {
            key: protocol[key] for key in (
                "frozen_at_utc", "confirmation_seeds", "sensitivity_seeds",
                "sensitivity_policy", "statistics", "source_kind", "schema",
            ) if key in protocol
        }
        data["sensitivity_conditions"] = dict(protocol.get("sensitivity_cases", []))
    provenance["saved_simulation_histories"] = len(data.get("samples", []))
    data["demo_provenance"] = provenance
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    serialized = serialized.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    template = (root / "demo/template.html").read_text()
    if template.count("__STUDY_DATA__") != 1:
        raise ValueError("template requires exactly one evidence placeholder")
    html = template.replace("__STUDY_DATA__", serialized)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    return {
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "saved_histories": provenance["saved_simulation_histories"],
        "mode": "saved-simulation-and-local-witnesses" if data.get("samples") else "local-witnesses-economic-results-pending",
    }


def main() -> None:
    """Build without fetching resources or running an economic experiment."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=root / "results/demo_data.json")
    parser.add_argument("--commercial", type=Path,
                        help="Optional saved commercial register; must match the supplied Beta summary")
    parser.add_argument("--output", type=Path, default=root / "demo/index.html")
    args = parser.parse_args()
    if args.commercial is not None and not args.commercial.is_file():
        parser.error(f"commercial register does not exist: {args.commercial}")
    print(json.dumps(build(args.data, args.output, args.commercial), indent=2))


if __name__ == "__main__":
    main()
