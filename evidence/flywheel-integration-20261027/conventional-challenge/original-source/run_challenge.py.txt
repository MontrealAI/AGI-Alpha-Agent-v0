# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy, hashlib, json, resource, sys, time
from pathlib import Path
from conventional import witness

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

def identity(path):
    b=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),git_blob=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest())

def main():
    resource.setrlimit(resource.RLIMIT_CPU,(90,90))
    freeze=ROOT/"FROZEN_CASES.json"
    ref_path=ROOT/"REFERENCE_RESULTS.json"
    if (ROOT/"RESULTS.json").exists(): raise SystemExit("primary result exists; no automatic rerun")
    f=json.loads(freeze.read_text())
    refs=json.loads(ref_path.read_text())
    assert hashlib.sha256(freeze.read_bytes()).hexdigest()==refs["freeze_sha256"]
    assert identity(ROOT/"conventional.py")["sha256"]==refs["reference_source_sha256"]
    source=identity(ROOT/"upstream/flywheel_access_path.py")
    protocol=identity(ROOT/"upstream/protocol.py")
    assert source["git_blob"]==f["target_git_blob"]
    assert protocol["git_blob"]=="a027036c91951a2beb65e490cd8fc28507c73309"
    from upstream.flywheel_access_path import AccessProblem, check_access, construct_access
    start=time.perf_counter(); cpu=time.process_time()
    results=[]
    probes=[]
    for case,reference in zip(f["cases"],refs["results"],strict=True):
        assert case["mission_id"]==reference["mission_id"]
        t=time.perf_counter(); c=time.process_time()
        p=AccessProblem.model_validate(case)
        out=construct_access(p)
        measured=dict(wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-c)
        completed=out["status"]!="incomplete" and reference["result"]["status"]!="incomplete"
        rank=[len(out["pending_permissions"]),out["estimated_cost_micro_usd"],out["duration_seconds"],[s["step_id"] for s in out["steps"]]] if out["status"] in {"declared-plan","conditional-plan"} else None
        exact=completed and out["status"]==reference["result"]["status"] and rank==reference["result"]["rank"]
        accepted=out["status"] in {"declared-plan","conditional-plan"}
        checked=witness(case,out) if accepted else None
        native_checked=check_access(p,out)
        if accepted:
            bad=copy.deepcopy(out);bad["authority_granted"]=True
            probes.append(dict(mission_id=case["mission_id"],probe="invent-authority",refused=not check_access(p,bad)))
            bad=copy.deepcopy(out);bad["estimated_cost_micro_usd"]+=1
            probes.append(dict(mission_id=case["mission_id"],probe="cost-tamper",refused=not check_access(p,bad)))
            bad=copy.deepcopy(out);bad["preserved_obligations"]=case["obligations"][:1]
            probes.append(dict(mission_id=case["mission_id"],probe="erase-obligation",refused=not check_access(p,bad)))
        results.append(dict(mission_id=case["mission_id"],reference=reference["result"],target=out,target_measurements=measured,
                            complete_pair=completed,exact_agreement=exact if completed else None,
                            independent_witness_valid=checked,native_checker_accepted=native_checked))
    report=dict(schema="fresh-conventional-challenge-results/v1",freeze_sha256=hashlib.sha256(freeze.read_bytes()).hexdigest(),
        reference_results_sha256=hashlib.sha256(ref_path.read_bytes()).hexdigest(),sources=[source,protocol,identity(ROOT/"conventional.py"),identity(ROOT/"run_challenge.py")],
        cases=len(results),complete_pairs=sum(r["complete_pair"] for r in results),
        exact_agreements=sum(r["exact_agreement"] is True for r in results),
        target_incomplete=sum(r["target"]["status"]=="incomplete" for r in results),
        reference_incomplete=sum(r["reference"]["status"]=="incomplete" for r in results),
        accepted_plans=sum(r["independent_witness_valid"] is True for r in results),
        witness_failures=sum(r["independent_witness_valid"] is False for r in results),
        negative_probes=len(probes),negative_probes_refused=sum(p["refused"] for p in probes),
        wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        complete_actual_cost_usd=None,actual_customer_collections_usd=0,controlled_frontier_calls=0,
        conclusion="Competent ordinary parity stops this scoped technical-breakthrough claim; discovery advantage and commercial success remain unmeasured",
        results=results,negative_controls=probes)
    (ROOT/"RESULTS.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in {"results","negative_controls","sources"}},sort_keys=True))
    assert report["exact_agreements"]==report["complete_pairs"]
    assert report["witness_failures"]==0
    assert report["negative_probes"]==report["negative_probes_refused"]

if __name__=="__main__": main()
