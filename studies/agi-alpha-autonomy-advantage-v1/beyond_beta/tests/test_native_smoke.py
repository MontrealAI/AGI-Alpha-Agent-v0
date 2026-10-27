# SPDX-License-Identifier: Apache-2.0
"""Fictional end-to-end graph/cash/native planning smoke; no economic world run."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'beyond_beta/src'))
from graph_lifecycle import costs,digest
from fixture_factory import make_fixture_environment,fixture_artifact,matched_evidence,bind_cost_ownership,qualify,mission_for

spec=importlib.util.spec_from_file_location('unchanged_finance',ROOT/'venture_creation/src/finance_capacity.py')
finance=importlib.util.module_from_spec(spec);spec.loader.exec_module(finance)

def main():
    graph,people=make_fixture_environment()
    book=finance.CashBook(100,10,0,0)
    delivery=book.expense(0,20,'originalDeliveryA','paid-job-a');book.advance(0)
    book.invoice(0,'paid-job-a',100,1,True,0,1);book.advance(1)
    retention=book.expense(1,4,'incrementalRetentionB','retained-solver');book.advance(1)
    key=graph.create(people['creator'],people['writer'],fixture_artifact(),skill_id='paid-job-retention',epoch=1)
    evidence=matched_evidence(graph,key,[20000000,20000000],[100000000,100000000],epoch=1,case_prefix='fictional-fresh')
    commitment=lambda bill: digest('SMOKE-LEDGER',{k:bill[k] for k in ('id','ref','amountMicros','category')})
    evidence=bind_cost_ownership(evidence,
        origin_job_costs=[dict(jobId='paid-job-a',ledgerCommitment=commitment(delivery),costMicros=delivery['amountMicros'],ownership='DELIVERY_A_ALREADY_CHARGED')],
        retention_entries=[dict(chargeId=retention['id'],ledgerCommitment=commitment(retention),costs=costs(construction=retention['amountMicros']),ownership='INCREMENTAL_RETENTION_B')])
    assessment=qualify(graph,people,key,evidence,1);assert assessment['qualified']
    graph.admit(people['admitter'],key,1)
    permit=graph.authorize_reuse(people['executor'],key,mission_for(graph),1)
    invocation=graph.resolve_reuse(people['executor'],permit,1)
    assert invocation['artifact']==fixture_artifact()
    assert assessment['costOwnership']['originDeliveryCostMicros']==20000000
    assert assessment['costOwnership']['alphaLifecycleCostMicros']==4000000
    projection=book.native_projection_input()
    for field in ('accrual','liquidity'):
        projection[field]['missionId']='beyond-beta-fictional-smoke'
        projection[field]['reference']='Fictional offline paid-job A and incremental retention B boundary; actual receipts zero'
    fixture=graph.authorities[people['creator'].name]
    source_hash=hashlib.sha256((ROOT/'beyond_beta/src/graph_lifecycle.py').read_bytes()).hexdigest()
    batch=dict(schema='beyond-beta-native-input/v1',worlds=[dict(id='fictional-paid-job-retention',projection=projection,
        graphAuditRoot=graph.audit_log()['root'],graphSourceHash=source_hash,
        authorityChecks=[dict(fixture=fixture,week=1),dict(fixture={**fixture,'name':'child.'+fixture['name']},week=1),dict(fixture={**fixture,'revoked':True},week=1)])])
    with tempfile.TemporaryDirectory(prefix='beyond-beta-native-') as temporary:
        source=Path(temporary)/'input.json';target=Path(temporary)/'output.json'
        source.write_text(json.dumps(batch))
        run=subprocess.run(['node',str(ROOT/'beyond_beta/src/native_bridge.mjs'),str(source),str(target)],capture_output=True,text=True,check=True)
        native=json.loads(target.read_text())
    assert native['measuredExecution']['nativePlanMissionCalls']==2
    assert native['measuredExecution']['authorityCalls']==3
    assert native['measuredExecution']['admissionCalls']==0
    assert [x['result']['eligible'] for x in native['worlds'][0]['authorities']]==[True,False,False]
    accounting=native['worlds'][0]['accounting']
    assert accounting['reconciliation']['passed']
    assert accounting['accrual']['observed']['revenue']==0
    assert accounting['accrual']['observed']['fullCost'] is None
    assert native['boundaries']['actualModelCalls']==0
    result=dict(schema='beyond-beta-native-smoke/v1',classification='FICTIONAL_CONTROL_NOT_CALIBRATED_OUTCOME',passed=True,
        actualModelCalls=0,actualRevenueUsd=0,actualCompleteCostUsd=None,
        graphAssessment=assessment,graphAudit=graph.audit_log(),simulatedCash=book.serialize(),nativeInput=batch,nativeResult=native,
        stdout=run.stdout.strip(),sources=[dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in (Path(__file__),ROOT/'beyond_beta/src/graph_lifecycle.py',ROOT/'beyond_beta/src/fixture_factory.py',ROOT/'venture_creation/src/finance_capacity.py')])
    output=ROOT/'beyond_beta/validation/native-smoke.json';output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,nativePlanMissionCalls=2,authorityChecks=3,output=str(output.relative_to(ROOT)),calibratedEconomicWorlds=0)))

if __name__=='__main__':main()
