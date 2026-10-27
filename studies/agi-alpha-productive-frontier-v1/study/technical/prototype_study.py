# SPDX-License-Identifier: Apache-2.0
import argparse, csv, hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from lyapunov_study import system, parameters, exact, certificate, project, adaptive, certified, load_basis, ROOT

PP = json.loads((ROOT / "prototype_protocol.json").read_text())


def certify_solve(A, B, alpha, method, V=None):
    counts = {"specialist_calls": 0, "adaptive_calls": 0, "schur_calls": 0, "rejected_certificates": 0}
    if method == "schur":
        X = exact(A, B)
        c = certificate(A, B, X, alpha)
        counts["schur_calls"] += 1
    elif V is not None:
        X = project(A, B, V)
        c = certificate(A, B, X, alpha)
        counts["specialist_calls"] += 1
    else:
        X, rank, c = adaptive(A, B, alpha)
        counts["adaptive_calls"] += 1
    if not certified(c) and V is not None:
        counts["rejected_certificates"] += 1
        X, rank, c = adaptive(A, B, alpha)
        counts["adaptive_calls"] += 1
    if not certified(c):
        counts["rejected_certificates"] += 1
        X = exact(A, B)
        c = certificate(A, B, X, alpha)
        counts["schur_calls"] += 1
    return X, c, counts


def one_case(p, method, V=None):
    start = time.perf_counter()
    records = []
    counts = {
        "specialist_calls": 0,
        "adaptive_calls": 0,
        "schur_calls": 0,
        "rejected_certificates": 0,
        "selection_refinements": 0,
    }
    for g in PP["gain_grid"]:
        A, B, alpha = system(p)
        A -= g * np.eye(len(A))
        alpha += g
        X, c, cs = certify_solve(A, B, alpha, method, V)
        for k, v in cs.items():
            counts[k] += v
        val = c["trace"] + 0.15 * g * g
        delta = np.sqrt(len(A)) * c["absolute_fro_bound"]
        records.append(
            {
                "g": g,
                "objective": val,
                "delta": delta,
                "lower": val - delta,
                "upper": val + delta,
                "certificate": c["relative_trace_certificate"],
            }
        )
    upper = min(r["upper"] for r in records)
    survivors = [i for i, r in enumerate(records) if r["lower"] <= upper]
    if len(survivors) > 1:
        for i in survivors:
            r = records[i]
            g = r["g"]
            A, B, alpha = system(p)
            A -= g * np.eye(len(A))
            alpha += g
            X = exact(A, B)
            c = certificate(A, B, X, alpha)
            counts["schur_calls"] += 1
            counts["selection_refinements"] += 1
            val = c["trace"] + 0.15 * g * g
            delta = np.sqrt(len(A)) * c["absolute_fro_bound"]
            records[i] = {
                "g": g,
                "objective": val,
                "delta": delta,
                "lower": val - delta,
                "upper": val + delta,
                "certificate": c["relative_trace_certificate"],
            }
    best = min(range(len(records)), key=lambda i: records[i]["upper"])
    separated = all(records[best]["upper"] < r["lower"] for i, r in enumerate(records) if i != best)
    return {
        "seconds": time.perf_counter() - start,
        "gain": records[best]["g"],
        "objective": records[best]["objective"],
        "separated": separated,
        "abstained": not separated,
        **counts,
    }, records


def run(out, validation_rerun=False, seed=None, proposals=None):
    out.mkdir(exist_ok=True, parents=True)
    seed = PP["seed"] if seed is None else seed
    protocol = {**PP, "seed": seed}
    ps = parameters(seed, PP["cases"])
    (out / f"prototype{seed}_freeze.json").write_text(
        json.dumps(
            {
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "seed": seed,
                "technical_implementation_sha256": hashlib.sha256(
                    (ROOT / "lyapunov_study.py").read_bytes()
                ).hexdigest(),
                "proposals_sha256": hashlib.sha256(Path(proposals).read_bytes()).hexdigest() if proposals else None,
                "protocol_sha256": hashlib.sha256((ROOT / "prototype_protocol.json").read_bytes()).hexdigest(),
                "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "parameters": ps.tolist(),
                "run_status": "scoped_revalidation_of_exposed_cases"
                if validation_rerun
                else "fresh_confirmation_after_input_guard_correction"
                if seed == 7401
                else "preconfirmation",
            },
            indent=2,
        )
    )
    if proposals:
        (out / "frozen_opportunity_proposals.json").write_bytes(Path(proposals).read_bytes())
    manifest = json.loads((ROOT / "results_validated/validation_freeze.json").read_text())
    bases = {
        "schur": None,
        "adaptive_fallback": None,
        "work48_fallback": load_basis(ROOT / "results_validated/work_pod48.npy", manifest["bases"]["work_pod48"]),
        "gym48_fallback": load_basis(ROOT / "results_validated/gym_pod48.npy", manifest["bases"]["gym_pod48"]),
    }
    rows = []
    detail = []
    for i, p in enumerate(ps):
        oracle = []
        for g in PP["gain_grid"]:
            A, B, alpha = system(p)
            A -= g * np.eye(len(A))
            oracle.append(float(np.trace(exact(A, B))) + 0.15 * g * g)
        for name, V in bases.items():
            result, recs = one_case(p, name, V)
            bestoracle = min(oracle)
            chosenidx = PP["gain_grid"].index(result["gain"])
            result.update(
                {
                    "case": i,
                    "method": name,
                    "oracle_gain": PP["gain_grid"][int(np.argmin(oracle))],
                    "objective_regret": float(oracle[chosenidx] - bestoracle),
                    "accepted": bool(
                        result["separated"]
                        and oracle[chosenidx] - bestoracle <= PP["acceptance"]["maximum_objective_regret"]
                    ),
                }
            )
            rows.append(result)
            detail.append({"case": i, "method": name, "candidates": recs})
    with (out / "selection_prototype.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    summary = {}
    for name in bases:
        rs = [r for r in rows if r["method"] == name]
        summary[name] = {
            "n": len(rs),
            "accepted": sum(r["accepted"] for r in rs),
            "seconds_total": sum(r["seconds"] for r in rs),
            "max_objective_regret": max(r["objective_regret"] for r in rs),
            "abstained": sum(r["abstained"] for r in rs),
            "specialist_calls": sum(r["specialist_calls"] for r in rs),
            "adaptive_calls": sum(r["adaptive_calls"] for r in rs),
            "schur_calls": sum(r["schur_calls"] for r in rs),
            "selection_refinements": sum(r["selection_refinements"] for r in rs),
            "qualifies_frozen_service": all(r["accepted"] for r in rs) and sum(r["seconds"] for r in rs) <= 2.0,
        }
    (out / "selection_details.json").write_text(json.dumps(detail, indent=2))
    (out / "selection_results.json").write_text(json.dumps({"protocol": protocol, "summary": summary}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--validation-rerun", action="store_true")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--proposals")
    args = ap.parse_args()
    with threadpool_limits(limits=1):
        run(Path(args.out), args.validation_rerun, args.seed, args.proposals)
