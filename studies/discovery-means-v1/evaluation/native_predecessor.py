# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any
import alpha_factory_v1.core.runtime.successor.flywheel_probe as native
from alpha_factory_v1.core.runtime.successor.protocol import digest


def run() -> None:
    folder = Path(__file__).parent
    manifest = json.loads((folder / "task_manifest.json").read_text())
    rows = []
    cases = [case for case in manifest["cases"] if case["family"] == "permission_constraints"]
    for case in cases:
        hs = sorted(case["hypotheses"])
        labels = dict(zip(hs, ("not-applied", "applied", "partially-applied")))
        experiments = {e["id"]: e for e in case["experiments"] if e["allowed"]}
        epoch = digest("confirmation-epoch", {"case": case["case_id"]})
        sources = {eid: digest("confirmation-synthetic-probe", e) for eid, e in experiments.items()}
        problem = native.ProbeProblem(
            mission_digest=digest("confirmation-mission", case),
            purpose_digest=digest("confirmation-purpose", {"purpose": "Identify supplied synthetic hypothesis"}),
            input_semantics="Author-generated singleton finite model, not observations of a physical system",
            required_output_semantics="Bijective three-result label mapped to exact hypothesis identity",
            observation_epoch=epoch,
            coverage_basis="Exhaustive replay of every hypothesis in the supplied three-hypothesis model only",
            probes=[native.ReadOnlyProbe(probe_id=eid, observation_contract="Synthetic singleton outcome",
                                        source_digest=sources[eid], query_units=e["cost"])
                    for eid, e in experiments.items()],
            hypotheses=[native.EffectHypothesis(hypothesis_id=h, result=labels[h],
                                               observations={eid: e["outcomes"][h][0] for eid, e in experiments.items()})
                        for h in hs], query_budget=case["max_cost"])
        worlds = []
        for h in hs:
            observations: list[Any] = []
            trace = []
            start, cpu = time.perf_counter(), time.process_time()
            while True:
                report = native.inspect_information(problem, observations)
                independently_remaining = sorted(x for x in hs if all(experiments[o.probe_id]["outcomes"][x] == [o.value] for o in observations))
                check = (report["remaining_hypotheses"] == independently_remaining
                         and report["query_units_spent"] == sum(experiments[o.probe_id]["cost"] for o in observations)
                         and report["query_units_spent"] <= case["max_cost"]
                         and report["authority_granted"] is False and report["retry_permitted"] is False)
                trace.append({"report": report, "independent_state_check": check})
                if report["result"] is not None or report["next_probe"] is None or len(observations) >= case["max_experiments"]:
                    break
                eid = report["next_probe"]
                if eid not in experiments or eid in {o.probe_id for o in observations}:
                    raise AssertionError("native requested forbidden, unknown, or repeated probe")
                observations.append(native.ProbeObservation(probe_id=eid, value=experiments[eid]["outcomes"][h][0],
                                                            observation_epoch=epoch, source_digest=sources[eid]))
            worlds.append({"true_hypothesis": h, "correct": report["result"] == labels[h] and all(t["independent_state_check"] for t in trace),
                           "depth": len(observations), "cost": report["query_units_spent"], "trace": trace,
                           "wall_seconds": time.perf_counter() - start, "cpu_seconds": time.process_time() - cpu})
        rows.append({"case_id": case["case_id"], "hypothesis_to_result": labels, "input": problem.model_dump(),
                     "excluded_forbidden_experiments": [e["id"] for e in case["experiments"] if not e["allowed"]],
                     "worlds": worlds, "all_worlds_correct": all(w["correct"] for w in worlds),
                     "worst_cost": max(w["cost"] for w in worlds), "worst_depth": max(w["depth"] for w in worlds)})
    path = Path(native.__file__).resolve()
    result = {"scope": "Four matched singleton three-result cases from frozen24-case manifest; all12worlds replayed. Native depth enforced by external same-cap wrapper because native contract has no depth field. Other20cases outside native schema, not failures. No physical observation, installed release qualification, or production authority.",
              "manifest_sha256": hashlib.sha256((folder / "task_manifest.json").read_bytes()).hexdigest(),
              "loaded_native_path": str(path), "loaded_native_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "rows": rows, "summary": {"cases": len(rows), "correct_cases": sum(r["all_worlds_correct"] for r in rows),
                                        "worlds": sum(len(r["worlds"]) for r in rows),
                                        "correct_worlds": sum(w["correct"] for r in rows for w in r["worlds"])}}
    destination = folder / "native_predecessor_results.json"
    if destination.exists():
        raise SystemExit("refusing to overwrite native predecessor evidence")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    run()
