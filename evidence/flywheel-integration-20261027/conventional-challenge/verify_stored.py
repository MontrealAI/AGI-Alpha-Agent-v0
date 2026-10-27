# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy, hashlib, json, sys
from pathlib import Path
from conventional import witness

ROOT=Path(__file__).resolve().parent

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    frozen=ROOT/"FROZEN_CASES.json"
    original=ROOT/"RESULTS.json"
    f=json.loads(frozen.read_text())
    r=json.loads(original.read_text())
    assert sha(frozen)==r["freeze_sha256"]
    checks=[]
    families={}
    for case,row in zip(f["cases"],r["results"],strict=True):
        assert case["mission_id"]==row["mission_id"]
        normalized=copy.deepcopy(case)
        for step in normalized["steps"]:
            assert "schema_version" not in step
            step["schema_version"]=1
        report=row["target"]
        accepted=report["status"] in {"declared-plan","conditional-plan"}
        valid=witness(normalized,report) if accepted else None
        checks.append(dict(mission_id=case["mission_id"],status=report["status"],
            independent_witness_valid=valid,complete_pair=row["complete_pair"],exact_agreement=row["exact_agreement"]))
        family=case["mission_id"].rsplit("-",1)[0].removeprefix("fresh-")
        item=families.setdefault(family,dict(cases=0,complete_pairs=0,exact_agreements=0,
            declared_plans=0,conditional_plans=0,no_plans=0,incomplete=0,independent_witnesses=0))
        item["cases"]+=1
        item["complete_pairs"]+=row["complete_pair"]
        item["exact_agreements"]+=row["exact_agreement"] is True
        item[{"declared-plan":"declared_plans","conditional-plan":"conditional_plans","no-plan":"no_plans","incomplete":"incomplete"}[report["status"]]]+=1
        item["independent_witnesses"]+=valid is True
    assert all(x["independent_witness_valid"] is not False for x in checks)
    result=dict(schema="stored-output-verification/v1",freeze_sha256=sha(frozen),
        original_failed_receipt_sha256=sha(original),verifier_sha256=sha(Path(__file__)),
        correction="The independent harness compared serialized steps to inputs that omitted the StrictModel schema_version=1 default; this read-only checker adds that explicit known default to an isolated input copy before equality checking",
        target_executed=False,original_outputs_modified=False,requirements_or_cases_modified=False,
        accepted_plans=sum(x["independent_witness_valid"] is True for x in checks),witness_failures=0,
        complete_pairs=r["complete_pairs"],exact_agreements=r["exact_agreements"],
        target_incomplete=r["target_incomplete"],reference_incomplete=r["reference_incomplete"],
        families=families,checks=checks,
        incremental_cost_boundary=dict(observed=["reference wall/CPU seconds and max RSS", "target plus native negative/witness-check wall/CPU seconds and max RSS", "artifact byte sizes"],
            complete_actual_usd=None,unknown=["session model/tool effort", "authoring", "independent verification", "failed harness analysis and correction", "packaging and integration", "future maintenance"],
            actual_customer_collections_usd=0,buyer_acceptance=False,frontier_api_calls=0,
            no_additional_retention_or_gym_cost_claim=True),
        scope="Eight authored finite scenario families; no customer brief, live approval, actual scientific experiment, deployed canary, discovery advantage or retained Alpha")
    out=ROOT/"CORRECTED_VERIFICATION.json"
    if out.exists(): raise SystemExit("verification receipt exists")
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in {"checks","families"}},sort_keys=True))

if __name__=="__main__": main()
