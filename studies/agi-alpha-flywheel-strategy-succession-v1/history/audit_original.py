#!/usr/bin/env python3
"""Read-only audit of the recovered Strategy Laboratory archive.

Uses its generator only to recover exact SHA-committed inputs. Does not execute
candidate policies, import its judge/statistics/engine, or bypass its replay
runtime guard. Independently checks stored artifacts, arithmetic, and seeds.
"""
from __future__ import annotations
import hashlib
import heapq
import json
import math
import platform
import statistics
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE / "extracted/SUCCESSOR_Omega_Strategy_Lab_v0.1.0"
sys.path.insert(0, str(LAB))
from omega.tasks import generate  # Original generator; every output hash checked.


def read(path):
    return json.loads(path.read_text())


def digest(value):
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(blob).hexdigest()


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), (a, b)


def optimal_cost(data):
    """Separate flat-index Dijkstra, independent of original judge/search."""
    side, grid = data["n"], data["grid"]
    costs = [math.inf] * len(grid)
    costs[0] = 0
    queue = [(0, 0)]
    while queue:
        cost, cell = heapq.heappop(queue)
        if cost != costs[cell]:
            continue
        if cell == len(grid) - 1:
            return cost
        row, col = divmod(cell, side)
        options = []
        if col: options.append(cell - 1)
        if col + 1 < side: options.append(cell + 1)
        if row: options.append(cell - side)
        if row + 1 < side: options.append(cell + side)
        for nxt in options:
            if grid[nxt] <= 0: continue
            trial = cost + grid[nxt]
            if trial < costs[nxt]:
                costs[nxt] = trial
                heapq.heappush(queue, (trial, nxt))
    raise AssertionError("Unreachable committed task")


def check_artifact(domain, data, run, oracle):
    artifact, work, judgment = run["artifact"], run["work"], run["judgment"]
    assert type(work) is int and 0 <= work <= data["budget"]
    assert run["budget"] == data["budget"] and judgment["work"] == work
    assert isinstance(artifact, list)
    if domain == "route":
        if not artifact:
            close(judgment["quality"], 0)
            close(judgment["score"], 0)
            assert judgment["success"] is False
            return
        side, grid = data["n"], data["grid"]
        assert len(artifact) <= work and len(set(artifact)) == len(artifact)
        assert artifact[0] == 0 and artifact[-1] == side * side - 1
        assert all(type(x) is int and 0 <= x < len(grid) and grid[x] > 0 for x in artifact)
        for left, right in zip(artifact, artifact[1:]):
            lr, lc = divmod(left, side)
            rr, rc = divmod(right, side)
            assert abs(lr - rr) + abs(lc - rc) == 1
        cost = sum(grid[x] for x in artifact[1:])
        assert cost >= oracle > 0
        assert judgment["path_cost"] == cost and judgment["optimal_cost"] == oracle
        quality = oracle / cost
        score = .9 * quality + .1 * (1 - work / data["budget"])
        assert judgment["success"] is True
    elif domain == "evidence":
        assert len(set(artifact)) == len(artifact)
        assert all(type(x) is int and 0 <= x < len(data["sources"]) for x in artifact)
        selected = [data["sources"][x] for x in artifact]
        assert sum(x["cost"] for x in selected) == work
        covered = {fact for source in selected for fact in source["facts"]}
        quality = sum(data["weights"][x] for x in covered) / sum(data["weights"])
        score = quality
        assert judgment["success"] == (quality == 1)
    elif domain == "schedule":
        used, allocations, total_duration, value = set(), {}, 0, 0
        for assignment in artifact:
            assert set(assignment) == {"job", "worker", "start", "finish"}
            assert all(type(x) is int for x in assignment.values())
            j, w, start, finish = [assignment[k] for k in ("job", "worker", "start", "finish")]
            assert j not in used and 0 <= j < len(data["jobs"])
            assert 0 <= w < data["workers"]
            job = data["jobs"][j]
            assert start >= 0 and finish - start == job["times"][w]
            assert finish <= min(data["horizon"], job["deadline"])
            for a, b in allocations.setdefault(w, []):
                assert finish <= a or b <= start
            allocations[w].append((start, finish))
            used.add(j)
            total_duration += finish - start
            value += job["value"]
        assert total_duration == work and judgment["jobs"] == len(artifact)
        quality = value / sum(job["value"] for job in data["jobs"])
        score = quality
        assert judgment["success"] == (quality == 1)
    else:
        raise AssertionError(domain)
    close(judgment["quality"], quality)
    close(judgment["score"], score)
    assert math.isfinite(score) and 0 <= score <= 1


def bounds(values, baseline, alpha):
    deltas = [x - y for x, y in zip(values, baseline)]
    n = len(deltas)
    mean = statistics.fmean(deltas)
    variance = sum((x - mean)**2 for x in deltas) / (n - 1)
    radius = math.sqrt(2 * variance * math.log(2 / alpha) / n) + 14 * math.log(2 / alpha) / (3 * (n - 1))
    return {"n": n, "candidate_mean": statistics.fmean(values),
            "baseline_mean": statistics.fmean(baseline), "mean_gain": mean,
            "lower_bound": max(-1., mean - radius), "radius": radius,
            "wins": sum(x > 1e-12 for x in deltas),
            "ties": sum(abs(x) <= 1e-12 for x in deltas),
            "losses": sum(x < -1e-12 for x in deltas)}


def nodes(expr):
    return 1 + nodes(expr[1]) + nodes(expr[2]) if isinstance(expr, list) else 1


def main():
    begin = time.perf_counter()
    manifest = read(LAB / "evidence/example/manifest.json")
    config = manifest["config"]
    result = {"audit_version": 1, "status": "PASS", "runtime": platform.python_version(),
              "historical_runtime": manifest["runtime"]["python"],
              "candidate_execution_replayed": False,
              "method": "Original task generator with exact stored task hashes; new separate semantic checker and statistical recomputation; no original judge, engine, or statistics import",
              "attempts": [], "seed_checks": {}, "source_comparison": {},
              "limits": ["Not external institutional review", "Inputs regenerated with original generator and accepted only after exact hash match", "No re-execution of historical candidate policies", "Self-reported work counters cannot be fully reconstructed from final artifacts", "Recorded solver times exclude full enterprise costs"]}
    confirmation_seeds, development_seeds, incumbent_by_domain = set(), set(), {}
    total_cases, total_runs, total_dev, evolutions, randoms = 0, 0, 0, 0, 0
    for i in range(1, 7):
        root = LAB / "evidence/example/attempts" / f"{i:04d}"
        freeze, summary, development, seeds, records = [read(root / (f + ".json")) for f in ("freeze", "summary", "development", "seeds", "records")]
        cases = records["cases"]
        domain = freeze["domain"]
        programs = freeze["programs"]
        assert set(programs) == {"candidate", "incumbent", "reference", "strong_reference", "random_search", "sham", "broken"}
        assert programs["incumbent"] == incumbent_by_domain.get(domain, programs["reference"])
        assert programs["sham"] == programs["incumbent"]
        assert digest(programs["candidate"]) == summary["candidate_sha256"] == development["candidate_sha256"]
        assert digest(development) == freeze["development_sha256"]
        assert digest(freeze) == summary["freeze_sha256"]
        assert digest(seeds) == summary["seeds_sha256"]
        assert digest(cases) == summary["records_sha256"]
        alpha = config["total_alpha"] / (2 * i * (i + 1))
        close(alpha, freeze["alpha_per_test"])
        assert len(development["development"]) == len(development["random_control"]["development"]) == 72
        assert len(development["validation"]) == len(development["random_control"]["validation"]) == 7
        assert len(development["train_seeds"]) == len(development["validation_seeds"]) == 40
        expected_dev = 2 * 72 * 40 + 2 * 7 * 40
        assert development["development_task_executions"] == expected_dev
        dev_set = set(development["train_seeds"] + development["validation_seeds"])
        assert len(dev_set) == 80 and development_seeds.isdisjoint(dev_set)
        development_seeds.update(dev_set)
        flat_seeds = seeds["nominal"] + seeds["shifted"]
        assert len(set(flat_seeds)) == 4608 and confirmation_seeds.isdisjoint(flat_seeds)
        confirmation_seeds.update(flat_seeds)
        assert len(cases) == 4608
        by_stage = {stage: {name: [] for name in programs} for stage in seeds}
        for case in cases:
            stage = case["stage"]
            assert seeds[stage][case["index"]] == case["seed"]
            task = generate(domain, case["seed"], shift=(stage == "shifted"))
            assert digest({"domain": domain, "seed": task.seed, "shift": task.shift, "data": task.data}) == case["task_sha256"]
            oracle = optimal_cost(task.data) if domain == "route" else None
            assert set(case["runs"]) == set(programs)
            for name, run in case["runs"].items():
                check_artifact(domain, task.data, run, oracle)
                by_stage[stage][name].append(run["judgment"]["score"])
                total_runs += 1
            total_cases += 1
        recalculated = {}
        for stage in seeds:
            assert len(by_stage[stage]["candidate"]) == len(seeds[stage])
            for name in programs:
                close(statistics.fmean(by_stage[stage][name]), summary["means"][stage][name])
                close(statistics.fmean(c["runs"][name]["work"] for c in cases if c["stage"] == stage), summary["mean_work"][stage][name])
                close(statistics.fmean(c["runs"][name]["observations"]["score_calls"] for c in cases if c["stage"] == stage), summary["mean_score_calls"][stage][name])
            stats = bounds(by_stage[stage]["candidate"], by_stage[stage]["incumbent"], alpha)
            for k, v in stats.items(): close(v, summary[stage][k])
            recalculated[stage] = stats
        promote = (programs["candidate"] != programs["incumbent"] and
                   recalculated["nominal"]["lower_bound"] > freeze["min_gain"] and
                   recalculated["shifted"]["lower_bound"] >= -freeze["shift_tolerance"])
        assert promote == summary["decision"]["promote"]
        for control in ("sham", "broken"):
            n = bounds(by_stage["nominal"][control], by_stage["nominal"]["incumbent"], alpha)
            s = bounds(by_stage["shifted"][control], by_stage["shifted"]["incumbent"], alpha)
            passes = control != "sham" and n["lower_bound"] > freeze["min_gain"] and s["lower_bound"] >= -freeze["shift_tolerance"]
            assert not passes and not summary["controls"][control]["promote"]
        if promote: incumbent_by_domain[domain] = programs["candidate"]
        else: incumbent_by_domain[domain] = programs["incumbent"]
        result["attempts"].append({"attempt": i, "domain": domain, "decision": "PROMOTED" if promote else "HELD", "candidate_sha256": summary["candidate_sha256"],
            "incumbent_sha256": digest(programs["incumbent"]), "alpha_per_test": alpha,
            "recalculated": recalculated, "means": summary["means"], "mean_work": summary["mean_work"],
            "mean_score_calls": summary["mean_score_calls"], "ast_nodes": {name: nodes(p["expression"]) for name,p in programs.items()},
            "recorded_solver_execution_seconds": summary["execution_seconds"],
            "recorded_development_seconds": development["development_seconds"], "development_task_executions": expected_dev})
        total_dev += expected_dev
        evolutions += len(development["development"])
        randoms += len(development["random_control"]["development"])
        print(f"Attempt {i}: {domain}, all {len(cases)} committed inputs and {len(cases)*7} artifacts checked; {result['attempts'][-1]['decision']}", flush=True)
    assert development_seeds.isdisjoint(confirmation_seeds)
    prior_seeds = set()
    with zipfile.ZipFile(LAB / "evidence/prior_experiment.zip") as archive:
        for path in archive.namelist():
            if path.endswith("/seeds.json"):
                obj = json.loads(archive.read(path))
                for values in obj.values(): prior_seeds.update(values)
            if path.startswith("prior_experiment/omega/") and path.endswith(".py"):
                name = Path(path).name
                prior_bytes, current_bytes = archive.read(path), (LAB / "omega" / name).read_bytes()
                result["source_comparison"][name] = {"same": prior_bytes == current_bytes, "prior_sha256": hashlib.sha256(prior_bytes).hexdigest(), "final_sha256": hashlib.sha256(current_bytes).hexdigest()}
    assert len(prior_seeds) == 13824 and prior_seeds.isdisjoint(confirmation_seeds)
    assert prior_seeds.isdisjoint(development_seeds)
    result["seed_checks"] = {"final_confirmation_unique": len(confirmation_seeds), "final_development_unique": len(development_seeds), "prior_confirmation_unique": len(prior_seeds), "prior_final_confirmation_overlap": len(prior_seeds & confirmation_seeds), "development_confirmation_overlap": len(development_seeds & confirmation_seeds), "prior_confirmation_final_development_overlap": len(prior_seeds & development_seeds)}
    result["totals"] = {"committed_tasks_regenerated": total_cases, "stored_artifacts_semantically_checked": total_runs, "development_task_executions_in_original": total_dev, "evolutionary_candidates_in_original": evolutions, "random_candidates_in_original": randoms, "promotions": sum(a["decision"] == "PROMOTED" for a in result["attempts"]), "holds": sum(a["decision"] == "HELD" for a in result["attempts"])}
    result["fresh_audit_elapsed_seconds"] = time.perf_counter() - begin
    result["audit_source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out = HERE / "HISTORICAL_VERIFICATION.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "result": str(out), **result["totals"], "seconds": result["fresh_audit_elapsed_seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
