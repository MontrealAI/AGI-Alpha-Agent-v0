# SPDX-License-Identifier: Apache-2.0
import csv, json, time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from lyapunov_study import ROOT, system, exact, load_basis, certified
from prototype_study import certify_solve


def run():
    out = ROOT / "results_validated"
    manifest = json.loads((out / "validation_freeze.json").read_text())
    bases = {
        "adaptive_fallback": None,
        "work48_fallback": load_basis(out / "work_pod48.npy", manifest["bases"]["work_pod48"]),
        "gym48_fallback": load_basis(out / "gym_pod48.npy", manifest["bases"]["gym_pod48"]),
    }
    rows = []
    summaries = {}
    for split in ["confirmation", "shift"]:
        ps = json.loads((out / f"{split}_parameters.json").read_text())
        for i, p in enumerate(ps):
            A, B, alpha = system(p)
            truth = exact(A, B)
            for name, V in bases.items():
                t = time.perf_counter()
                A, B, alpha = system(p)
                X, c, counts = certify_solve(A, B, alpha, name, V)
                seconds = time.perf_counter() - t
                err = abs(float(np.trace(X - truth))) / float(np.trace(truth))
                rows.append(
                    {
                        "split": split,
                        "case": i,
                        "method": name,
                        "seconds": seconds,
                        "accepted": bool(certified(c) and err <= 0.01),
                        "relative_trace_error": err,
                        **counts,
                    }
                )
        summaries[split] = {}
        for name in bases:
            rs = [r for r in rows if r["split"] == split and r["method"] == name]
            summaries[split][name] = {
                "n": len(rs),
                "accepted": sum(r["accepted"] for r in rs),
                "seconds_total": sum(r["seconds"] for r in rs),
                "batch32_seconds_observed": [sum(r["seconds"] for r in rs[j : j + 32]) for j in range(0, len(rs), 32)],
                "specialist_calls": sum(r["specialist_calls"] for r in rs),
                "adaptive_calls": sum(r["adaptive_calls"] for r in rs),
                "schur_calls": sum(r["schur_calls"] for r in rs),
                "rejected_certificates": sum(r["rejected_certificates"] for r in rs),
            }
    with (out / "fallback_validation.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    (out / "fallback_results.json").write_text(
        json.dumps(
            {
                "status": "scoped_revalidation_of_exposed_instances_not_fresh_confirmation",
                "timing": "Measured full composition including assembly, failed certificates and fallback; independent reference audit excluded",
                "summary": summaries,
            },
            indent=2,
        )
    )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        run()
