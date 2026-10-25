#!/usr/bin/env python3
"""Post-run independent audit of the registered main study.

Imports the separately authored reviewer checker only. No producer module is
imported, no candidate is re-executed, and no criterion is changed. Requires a
terminal confirmation record before reading protected outcomes.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from check import check


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(domain, value):
    # Public digest contract: a domain prefix plus canonical JSON of the
    # already-stringified payload. Receipt/strategy payloads contain integers.
    content = json.dumps(encoded(value).decode(), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(("successor-omega/v1:" + domain + "\0" + content).encode()).hexdigest()


def semantic(task):
    jobs = sorted(task["jobs"], key=lambda j: j["id"])
    obj = dict(kind=task["kind"], jobs=[dict(id=j["id"], duration=j["duration"], crew=j["crew"], deps=sorted(j["deps"])) for j in jobs],
               capacity=task["capacity"], release={j["id"]:task.get("release", {}).get(j["id"], 0) for j in task["jobs"]},
               locked=task.get("locked", {}), baseline=task.get("baseline"),
               deadline=task.get("deadline", len(task["capacity"])),
               movement_limit=task.get("movement_limit", 2304) if task["kind"] == "repair" else None)
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def bootstrap(values):
    # Reimplementation of the registered complete-stream percentile procedure.
    rng = random.Random(20261024)
    n = len(values)
    samples = []
    for _ in range(10000):
        total = 0
        for _ in range(n):
            total += values[rng.randrange(n)]
        samples.append(total/n)
    samples.sort()
    return dict(mean=statistics.fmean(values), percentile_95_interval=[samples[249], samples[9749]],
                independent_streams=n, resamples=10000, seed=20261024)


def assert_equal_numbers(left, right, context):
    if isinstance(left, dict):
        for key, value in left.items():
            assert_equal_numbers(value, right[key], context + "." + key)
    elif isinstance(left, list):
        assert len(left) == len(right), context
        for i, (a,b) in enumerate(zip(left, right)):
            assert_equal_numbers(a,b,context+f"[{i}]")
    elif isinstance(left, (int,float)) and not isinstance(left,bool):
        assert math.isclose(left,right,rel_tol=1e-12,abs_tol=1e-12),(context,left,right)
    else:
        assert left == right,(context,left,right)


def compact_checkpoint_identity(path, obj):
    # Keep JS's original numeric formatting instead of reserializing telemetry.
    text = path.read_text().strip()
    match = re.search(r',"integrity":"([0-9a-f]{64})"\}$', text)
    assert match is not None, "Expected the registered compact checkpoint framing"
    body_text = text[:match.start()] + "}"
    quoted = json.dumps(body_text,ensure_ascii=False,separators=(",", ":"))
    computed = hashlib.sha256(("successor-omega/v1:release-stream\0"+quoted).encode()).hexdigest()
    assert computed == obj["integrity"] == match.group(1), "Checkpoint integrity"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    terminal = run/"RUN_COMPLETE.json"
    if not terminal.exists():
        raise SystemExit("Refusing to audit protected outputs before terminal confirmation marker")
    start, complete = read(run/"RUN_START.json"), read(terminal)
    assert start.get("run_mode") == "CONFIRMATION", "Development smoke is not main confirmation"
    began = time.perf_counter()
    protocol = read(run/"protocol.json")
    frozen_path = PROJECT/"protocol/STUDY_FREEZE.json"
    frozen = read(frozen_path)
    assert start["top_freeze_sha256"] == sha(frozen_path)
    changed=[]
    for name, item in frozen["files"].items():
        path = PROJECT/name
        if not path.exists() or sha(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            changed.append(name)
    assert not changed, ("Frozen scientific source changed", changed)
    assert start["checker_sha256"] == sha(HERE.parent/"check.py")
    assert start["protocol_sha256"] == sha(PROJECT/"protocol/MAIN_PROTOCOL.json")
    source_manifest = read(PROJECT/"companion/SOURCE_MANIFEST.json")
    assert source_manifest["source_hash"] == start["source_hash"] == complete["source_hash"]
    assert hashlib.sha256(encoded(source_manifest["files"])).hexdigest() == start["source_hash"]
    for item in source_manifest["files"]:
        assert sha(PROJECT/"companion"/item["path"]) == item["sha256"], item["path"]

    inputs = {p.stem:read(p) for p in (run/"inputs").glob("*.json")}
    assert len(inputs) == 24
    task_lookup, groups, hashes, seed_keys = {}, [], set(), set()
    for stream,cfg in sorted(inputs.items()):
        roles=[("confirmation",cfg["tasks"])]
        for stage,data in cfg["qualification"].items():
            roles.extend([(stage+"-training",data["training"]),(stage+"-qualification",data["validation"])])
        for group,tasks in roles:
            for task in tasks:
                digest=semantic(task)
                seedkey=(task.get("fixture_seed"),task.get("scope"))
                assert digest not in hashes, ("Semantic overlap",stream,group,task["id"])
                assert seedkey not in seed_keys,("Seed/scope overlap",seedkey)
                hashes.add(digest);seed_keys.add(seedkey)
                task_lookup[(stream,task["id"])]=task
                groups.append((stream,group,task["id"],digest))
        if stream.startswith("stream-"):
            assert len(cfg["tasks"]) == 72
            for window in range(3):
                scopes=Counter(t["scope"] for t in cfg["tasks"][window*24:(window+1)*24])
                assert scopes == dict(ordinary=8,tight=8,repair=8),(stream,window,scopes)
    registry=read(run/"INPUT_REGISTRY.json")
    registry_rows={(r["stream"],r["group"],r["task_id"],r["semantic_sha256"]) for r in registry["records"]}
    assert registry_rows == set(groups)
    assert not registry["collisions"]
    # Public development comparison is recomputed from retained files; no
    # producer's scanner/digest helper is imported.
    exposed_hashes=set()
    def collect(obj):
        if isinstance(obj,dict):
            if obj.get("schema")=="release-plan/v1" and isinstance(obj.get("jobs"),list) and isinstance(obj.get("capacity"),list):
                try: exposed_hashes.add(semantic(obj))
                except (KeyError,TypeError,ValueError): pass
            else:
                for value in obj.values(): collect(value)
        elif isinstance(obj,list):
            for value in obj: collect(value)
    for folder in (PROJECT/"development",HERE.parent):
        for p in folder.rglob("*"):
            if "results" in p.relative_to(folder).parts or not p.is_file(): continue
            try:
                if p.suffix==".json": collect(read(p))
                elif p.suffix==".jsonl":
                    for line in p.read_text().splitlines():
                        if line.strip(): collect(json.loads(line))
            except (ValueError,UnicodeError): pass
    collect(read(PROJECT/"companion/schema-examples.json"))
    assert exposed_hashes.isdisjoint(hashes), "Exposed development semantic overlap"

    trials=[json.loads(line) for line in (run/"trials.jsonl").read_text().splitlines() if line.strip()]
    main_rows=[r for r in trials if r["category"]=="main"]
    diag=[r for r in trials if r["category"]=="diagnostic"]
    assert len(main_rows)==288 and len(diag)==48 and complete["trials"]==336
    identities={(r["category"],r["stream"],r["arm"],r["parent_treatment"],r["budget"]) for r in trials}
    assert len(identities)==336
    counts=Counter();checksums=[];trial_audits=[]
    discovery_classes=defaultdict(Counter)
    candidate_classes=defaultdict(Counter)
    for ordinal,trial in enumerate(trials):
        folder=run/trial["artifact_path"]
        assert read(folder/"summary.json")==trial
        checkpoint_path=folder/"checkpoint.json"
        state=read(checkpoint_path)
        compact_checkpoint_identity(checkpoint_path,state)
        assert state["source_hash"]==start["source_hash"] and state["proof"]==[] and state["authority"]==[]
        assert state["policy"]["totalWork"]==trial["budget"]
        assert state["work"]==trial["work"]<=trial["budget"]
        ledger_total=0;costs=Counter()
        for index,row in enumerate(state["ledger"]):
            assert row["entry"]==index and type(row["work"]) is int and row["work"]>=0
            ledger_total+=row["work"]
            assert row["total"]==ledger_total<=trial["budget"]
            costs[row["kind"]]+=row["work"]
        assert ledger_total==state["work"] and dict(costs)==trial["costs"]
        cfg=inputs[trial["stream"]]
        assert state["cursor"]==len(state["missions"])==trial["attempted"]
        assert [r["task_id"] for r in state["missions"]]==[t["id"] for t in cfg["tasks"][:state["cursor"]]]
        assert sum(m["qualified"] for m in state["missions"])==trial["qualified"]
        assert sum(m["valid"] for m in state["missions"])==trial["valid"]
        mission_checks=0
        for mission in state["missions"]:
            assert mission["proof"]==[] and mission["authority"]==[]
            receipt=dict(task_id=mission["task_id"])
            # JavaScript omits undefined fields in an unexecuted refusal.
            for field in ("result","checker"):
                if field in mission:receipt[field]=mission[field]
            receipt["source_hash"]=start["source_hash"]
            assert identity("release-stream",receipt)==mission["receipt_digest"]
            if mission["valid"]:
                verdict=check(dict(task=task_lookup[(trial["stream"],mission["task_id"])],result=mission["result"]))
                assert verdict["valid"] and verdict["qualified"]==mission["qualified"]
                mission_checks+=1
        rejected={r["digest"] for r in state["rejected"]}
        for asset in state["assets"]:
            assert asset["proof"]==[] and asset["authority"]==[]
            assert asset["source_hash"]==start["source_hash"]
            assert identity("release-strategy",asset["strategy"])==asset["digest"]
            assert not (asset["active"] and asset["digest"] in rejected)
        assert sum(a["active"] for a in state["assets"])<=state["policy"]["maxAssets"]
        for d in state["discoveries"]:
            class_key=f"{trial['category']}:{trial['budget']}:{trial['arm']}:{trial['parent_treatment']}"
            search=d.get("search") or {}
            for candidate in search.get("trials",[]):
                candidate_rows=candidate.get("rows",[])
                if not candidate_rows:
                    label="never_evaluated"
                elif any(r.get("truncated") or r.get("error") in ("WORK_LIMIT","CHECK_RESERVE") for r in candidate_rows):
                    label="budget_or_work_truncated"
                elif any(not r.get("valid") for r in candidate_rows):
                    label="invalid_candidate"
                elif candidate.get("complete"):
                    label="completed_valid_training"
                elif candidate.get("eliminated_after") is not None:
                    label="normal_valid_successive_halving_elimination"
                else:
                    label="unfinished_training_prefix"
                candidate_classes[class_key][label]+=1
            if not search.get("candidate"):
                label="no_complete_candidate_no_admission_test"
            elif not d.get("gate"):
                label="candidate_without_completed_gate"
            else:
                label=d["gate"]["decision"]
            discovery_classes[class_key][label]+=1
            q=d.get("qualification")
            if not q: continue
            allocation=q["registered_per_output_allocation"]
            fair=all(r.get("allocated_budget")==allocation for r in q["rows"]+q["reference"])
            assert fair==q["fair_allocation"]
            if d.get("gate",{}).get("accepted"):
                assert fair and all(r["valid"] and not r["truncated"] for r in q["rows"])
                assert d["gate"]["incumbent_maintenance"]==0
            assert [r["task_id"] for r in q["rows"]]==[r["task_id"] for r in q["reference"]]
        raw_count,semantic_count,refusals=0,0,0
        with gzip.open(folder/"raw.jsonl.gz","rt") as raw:
            for line in raw:
                if not line.strip():continue
                item=json.loads(line);raw_count+=1
                task,result=item["task"],item["row"].get("result")
                row=item["row"]
                assert semantic(task)==semantic(task_lookup[(trial["stream"],task["id"])] )
                assert row["work"]>=row["execution_work"]>=0
                assert row["work"]<=row["allocated_budget"],("per-output cap",trial["artifact_path"],task["id"],row["work"],row["allocated_budget"])
                if result is not None:
                    verdict=check(dict(task=task,result=result));semantic_count+=1
                    if row.get("checker") is not None:
                        assert verdict==row["checker"],("checker mismatch",trial["artifact_path"],task["id"])
                    if row["valid"]:
                        assert verdict["valid"] and verdict["qualified"]==row["qualified"]
                    elif verdict["valid"]:
                        assert row["error"] is not None
                        refusals+=1
                else:
                    assert not row["valid"] and not row["qualified"]
        counts.update(dict(raw_records=raw_count,independent_artifact_checks=semantic_count,accepted_receipt_rechecks=mission_checks,conservative_refusals=refusals))
        checksums.append(dict(path=trial["artifact_path"]+"/raw.jsonl.gz",sha256=sha(folder/"raw.jsonl.gz")))
        trial_audits.append(dict(path=trial["artifact_path"],status="PASS",raw_records=raw_count,ledger_work=ledger_total,qualified=trial["qualified"]))
        if (ordinal+1)%24==0:
            print(f"Audited {ordinal+1}/{len(trials)} trials; {counts['independent_artifact_checks']} stored outputs independently checked",flush=True)

    summary=read(run/"SUMMARY.json")
    by_arm=defaultdict(dict)
    for r in main_rows:
        if r["budget"]==1000000:by_arm[r["arm"]][r["stream"]]=r
    ids=sorted(by_arm["flywheel"])
    assert len(ids)==12
    differences={
        "coverage_difference_per_stream":[by_arm["flywheel"][s]["qualified"]-by_arm["workflow"][s]["qualified"] for s in ids],
        "coverage_percentage_point_difference":[(by_arm["flywheel"][s]["qualified"]-by_arm["workflow"][s]["qualified"])*100/72 for s in ids],
        "charged_work_difference":[by_arm["flywheel"][s]["work"]-by_arm["workflow"][s]["work"] for s in ids]}
    recomputed={name:bootstrap(values) for name,values in differences.items()}
    assert_equal_numbers(recomputed,summary["primary"],"registered-primary-bootstrap")
    for aggregate in summary["arms"]:
        batch=[r for r in main_rows if r["arm"]==aggregate["arm"] and r["budget"]==aggregate["budget"]]
        assert len(batch)==12
        for key in ("offered","attempted","valid","qualified"):
            assert sum(r[key] for r in batch)==aggregate[key]
        assert sum(r["work"] for r in batch)==aggregate["total_work"]
        assert_equal_numbers(aggregate["coverage_percent"],sum(r["qualified"] for r in batch)*100/864,"coverage")
    equivalence=[]
    for s in ids:
        fly,learner=by_arm["flywheel"][s],by_arm["learner"][s]
        equivalence.append(dict(stream=s,qualified_difference=fly["qualified"]-learner["qualified"],work_difference=fly["work"]-learner["work"],
                                same_mission_outcomes=fly["mission_results"]==learner["mission_results"],
                                same_asset_contents=[a["strategy"] for a in fly["assets"]]==[a["strategy"] for a in learner["assets"]]))
    assert equivalence==summary["conventional_equivalence"]
    native=read(run/"NATIVE_REFERENCE.json")
    assert len(native["rows"])==72
    for row in native["rows"]:
        candidate=(row.get("native") or {}).get("checked_schedule")
        if candidate is not None:
            verdict=check(dict(task=task_lookup[(row["stream"],row["task_id"])],result=candidate))
            assert verdict==row["checker"]
            assert verdict["valid"]==row["valid"] and verdict["qualified"]==row["qualified"]
            counts["native_artifact_checks"]+=1
        assert row["practical_workflow_valid"]==(row["valid"] or row["portfolio_valid"])
        assert row["practical_workflow_qualified"]==(row["qualified"] or row["portfolio_qualified"])
    result=dict(schema="independent-main-audit/v1",status="PASS",source_hash=start["source_hash"],
                top_freeze_sha256=start["top_freeze_sha256"],audit_source_sha256=sha(Path(__file__)),
                run=str(run),counts=dict(counts),main_trials=288,diagnostic_trials=48,
                input_disjointness=dict(registered_unique=len(hashes),preserved_exposed_unique=len(exposed_hashes),overlap=0,
                                        scope="Exact normalized constraints, not graph-isomorphism equivalence; reserved synthetic demo/load hashes additionally checked by frozen driver"),
                primary_recomputed=recomputed,conventional_equivalence=equivalence,
                discovery_outcome_classification={k:dict(v) for k,v in discovery_classes.items()},
                training_candidate_classification={k:dict(v) for k,v in candidate_classes.items()},
                trial_audits=trial_audits,raw_evidence_hashes=checksums,
                elapsed_seconds=time.perf_counter()-began,
                independence=dict(producer_imports=False,candidate_policies_reexecuted=False,
                                  separate_checker=True,same_project_commission=True,external_institutional_review=False),
                limitations=["Stored outputs rechecked; no fresh rerun of candidate search or main confirmation", "Frozen registered summaries recomputed; no replacement endpoint or selected exclusion", "Named operation ledger consistency does not price unknown authoring or monetary costs"])
    output=HERE/"MAIN_INDEPENDENT_AUDIT.json"
    output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",output=str(output),counts=dict(counts),primary=recomputed,elapsed_seconds=result["elapsed_seconds"]),indent=2),flush=True)


if __name__=="__main__":
    main()
