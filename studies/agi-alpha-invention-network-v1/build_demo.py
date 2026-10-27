# SPDX-License-Identifier: Apache-2.0
"""Build a self-contained bilingual companion from frozen measured evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from technical import Diffusion, Reduced

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(values: np.ndarray) -> list[float]:
    return [float(f"{value:.7g}") for value in values.ravel()]


def stats(rows: list[dict]) -> dict:
    return {
        "count": len(rows),
        "accepted": sum(x["accepted"] for x in rows),
        "complete_ms": float(np.mean([x["complete_s"] for x in rows])) * 1000,
        "iterations": float(np.mean([x.get("iterations", 0) for x in rows])),
        "raw_error": float(np.mean([x["raw_relative_error"] for x in rows]))
        if rows and rows[0].get("raw_relative_error") is not None
        else None,
        "raw_accepted": sum(x.get("raw_accepted", False) for x in rows),
    }


def build() -> None:
    result_path = HERE / "technical_confirm/results.json"
    result = json.loads(result_path.read_text())
    development = json.loads((HERE / "technical_dev_final/results.json").read_text())
    training = json.loads((HERE / "technical_dev_final/training.json").read_text())
    freeze = json.loads((HERE / "evidence/technical_freeze.json").read_text())
    protocol = json.loads((HERE / "economic_protocol.json").read_text())
    economy_path = HERE / "economy/results.json"
    economy = json.loads(economy_path.read_text()) if economy_path.exists() else None
    domain = Diffusion()
    models = {v: Reduced(domain, np.load(HERE / f"technical_dev_final/artifacts/{v}.npy")) for v in ["v1", "v2"]}
    fields = []
    for prefix in ["", "ood_"]:
        cases = json.loads((HERE / f"technical_confirm/{prefix}case_manifest.json").read_text())["cases"]
        saved = np.load(HERE / f"technical_confirm/{prefix}solutions.npz")
        seen: dict[str, int] = {}
        for case in cases:
            family = case["family"]
            seen[family] = seen.get(family, 0) + 1
            if seen[family] > 4:
                continue
            reference = saved[case["case_id"] + "__reference"]
            rhs = domain.source(case)
            raw = {v: models[v].raw(case, rhs) for v in models}
            fields.append(
                {
                    "case_id": case["case_id"],
                    "family": family,
                    "theta": case["theta"],
                    "source": case["source"],
                    "reference": compact(reference),
                    "v1_error": compact(np.abs(raw["v1"] - reference)),
                    "v2_error": compact(np.abs(raw["v2"] - reference)),
                    "v1_relative": float(np.linalg.norm(raw["v1"] - reference) / np.linalg.norm(reference)),
                    "v2_relative": float(np.linalg.norm(raw["v2"] - reference) / np.linalg.norm(reference)),
                    "error_scale": float(max(np.max(np.abs(raw[v] - reference)) for v in raw)),
                }
            )
    all_rows = result["records"] + result["ood_records"]
    methods = ["spectral_pcg", "direct", "ilu_gmres", "v1", "v2", "improved_generalist"]
    slices = {}
    rng = np.random.default_rng(854201)
    for family in ["all", "thermal", "transfer", "ood"]:
        chosen = [
            r
            for r in all_rows
            if (r["family"] in {"thermal", "transfer"} if family == "all" else r["family"] == family)
        ]
        summaries = {method: stats([r for r in chosen if r["method"] == method]) for method in methods}
        pairs = {}
        version = {r["case_id"]: r["complete_s"] for r in chosen if r["method"] == "v2"}
        for baseline in ["spectral_pcg", "direct", "ilu_gmres", "improved_generalist"]:
            rows = sorted([r for r in chosen if r["method"] == baseline], key=lambda r: r["case_id"])
            difference = np.array([r["complete_s"] - version[r["case_id"]] for r in rows]) * 1000
            samples = difference[rng.integers(0, len(rows), (10000, len(rows)))].mean(axis=1)
            pairs[baseline] = {
                "saving_ms": float(difference.mean()),
                "ci_ms": np.quantile(samples, [0.025, 0.975]).tolist(),
            }
        slices[family] = {"methods": summaries, "pairs": pairs}
    comp = {}
    for sensors in [2, 6]:
        subset = [r for r in result["composition"]["mission_records"] if r["sensor_count"] == sensors]
        comp[str(sensors)] = {
            m: stats([r for r in subset if r["method"] == m])
            for m in ["competent_generalist", "combination", "v1_combination", "fixed_sensor_ablation", "solver_only"]
        }
    identities = {
        "technical_source": result["source_sha256"],
        "technical_results": sha(result_path),
        "technical_freeze": sha(HERE / "evidence/technical_freeze.json"),
        "v1": result["selection"]["v1_sha256"],
        "v2": result["selection"]["v2_sha256"],
        "economics": sha(economy_path) if economy else None,
    }
    data = {
        "slices": slices,
        "composition": comp,
        "fields": fields,
        "n": domain.n,
        "identities": identities,
        "freeze": freeze,
        "economy": economy,
        "economic_protocol": protocol,
        "environment": result["environment"],
        "artifacts": {
            "r1": 12,
            "r2": result["selection"]["selected_rank"],
            "setup_s": result["artifact_build_by_version_s"],
        },
        "gym": [r["observation_residual"] for r in training["records"] if r["stage"] == "gym"],
        "development": {v: development["summary"][v] for v in ["v1", "v2"]},
        "selection": result["selection"],
        "case_count": len(result["records"]) // len(methods),
    }
    output = HERE / "demo"
    output.mkdir(exist_ok=True)
    payload = json.dumps(data, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    html = (output / "template.html").read_text().replace("__RESEARCH_DATA__", payload)
    (output / "index.html").write_text(html)
    manifest = {
        "generated_from": identities,
        "economics_ready": economy is not None,
        "display_fields": [x["case_id"] for x in fields],
        "field_selection": "First four cases of each family; no selection by outcome",
        "field_provenance": "Reference fields are retained confirmation arrays; raw errors re-evaluate the frozen checkpoint on those same inputs after confirmation for visualization only",
        "uncertainty": "Paired percentile bootstrap of mean latency differences over cases, 10000 resamples, seed854201; descriptive, no independent-machine inference",
        "self_contained": True,
        "index_sha256": sha(output / "index.html"),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "file": str(output / "index.html"),
                "bytes": (output / "index.html").stat().st_size,
                "economics_ready": economy is not None,
                "field_examples": len(fields),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        build()
