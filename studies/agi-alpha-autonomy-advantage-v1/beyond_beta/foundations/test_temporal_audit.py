# SPDX-License-Identifier: Apache-2.0
"""Independent temporal audit controls using fictional cash and local graph gates.

No economy sampler, calibration histories, real model calls or financial actions.
"""
from copy import deepcopy
from pathlib import Path
import json
import sys

from audit_economic_trace import audit_graph_uses, audit_cash_checkpoint, AuditFailure, digest, merkle_root
from test_economic_trace_audit import fixture
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from graph_lifecycle import BeyondBetaGraph, OfflinePrincipal, authority_fixture
from fixture_factory import make_fixture_environment, fixture_artifact, matched_evidence, bind_cost_ownership, qualify, mission_for


def check(name, condition):
    if not condition:raise AuditFailure(name)


def graph_fixture():
    world,_=fixture();base,people=make_fixture_environment()
    original=list(base.authorities.values())
    people['creator']=OfflinePrincipal('worker-0.agent.agi.eth')
    authorities=[a for a in original if a['name']!='creator.agent.agi.eth']+[authority_fixture(people['creator'],['creator','compose','execution','retrieve'])]
    graph=BeyondBetaGraph(base.policy,base.beta,[],authorities)
    key=graph.create(people['creator'],people['writer'],fixture_artifact(),epoch=1,skill_id='temporal-control')
    e=matched_evidence(graph,key,[100_000,100_000],[1_000_000,1_000_000],epoch=1,case_prefix='TEMPORAL-CONTROL')
    co=world['graph']['records'][0]['evidence']['costOwnership']
    # Expand the handwritten cost vector into the graph's complete cost schema.
    from graph_lifecycle import costs
    entries=deepcopy(co['retentionEntries']);entries[0]['costs']=costs(adaptation=200_000)
    e=bind_cost_ownership(e,origin_job_costs=co['originJobCosts'],retention_entries=entries)
    qualify(graph,people,key,e,1);graph.admit(people['admitter'],key,1)
    permit=graph.authorize_reuse(people['creator'],key,mission_for(graph),1)
    graph.resolve_reuse(people['creator'],permit,1)
    log=graph.audit_log();receipt={'key':key,'permit':permit,'epoch':1,'eventIndex':len(log['events'])-1,'logRoot':log['root']}
    world['jobs'][0].update(usedAssets=[key],completionReuseReceipts=[receipt])
    world['graph']={'records':[graph.record(key)],'audit':log,'publicAuthorities':list(graph.authorities.values())}
    return world


def cash_fixture():
    world,_=fixture();cash=world['cash'];a,b=cash['bills']
    cash.update(baseReserveMicros=100_000,taxFraction=0,warrantyFraction=0)
    cash['invoices'][0]['id']='invoice-0'
    cash['events']=[{'t':7,'type':'SIMULATED_COST_COMMITMENT','billId':a['id'],'amountMicros':a['amountMicros']},{'t':7,'type':'SIMULATED_EXPENSE_PAYMENT','billId':a['id'],'amountMicros':-a['amountMicros']},{'t':7,'type':'SIMULATED_COST_COMMITMENT','billId':b['id'],'amountMicros':b['amountMicros']},{'t':7,'type':'SIMULATED_EXPENSE_PAYMENT','billId':b['id'],'amountMicros':-b['amountMicros']},{'t':7,'type':'SIMULATED_COLLECTION','invoiceId':'invoice-0','amountMicros':3_000_000}]
    snapshot={**cash['funds'],'reserveMicros':100_000,'availableOperatingMicros':1_700_000,'liquidAfterObligationsMicros':11_700_000}
    decision={'week':1,'funding':'operating-only','fundsBefore':1.7,'reservedUSD':.1,'cashCheckpoint':{'week':1,'cashEventCount':5,'cashEventIndex':4,'funds':snapshot,'publicHoldsUSD':{}}}
    return world,decision


def main():
    results=[];w=graph_fixture();assert audit_graph_uses(w,check)==1
    results.append({'id':'executed-offline-admission-current-at-use','passed':True})
    for kind in ('RETIRED','BETA_ADVANCED'):
        bad=deepcopy(w);events=bad['graph']['audit']['events'];use=bad['jobs'][0]['completionReuseReceipts'][0]
        e={'index':len(events),'kind':kind,'key':use['key'] if kind=='RETIRED' else 'beta','epoch':2,'binding':'changed-beta' if kind=='BETA_ADVANCED' else bad['graph']['records'][0]['candidateHash'],'previous':events[-1]['hash']}
        events.append({**e,'hash':digest('EVENT',e)});root=merkle_root(events);bad['graph']['audit']['root']=root
        use.update(epoch=2,eventIndex=len(events)-1,logRoot=root)
        try:audit_graph_uses(bad,check)
        except AuditFailure as exc:
            expected='No revoked or retired history is revived' if kind=='RETIRED' else 'Reuse compares against the current Beta version'
            assert str(exc)==expected,(str(exc),expected);results.append({'id':kind.lower()+'-before-reuse-refused','passed':True,'refusal':str(exc)})
        else:raise AssertionError('Changed authority incorrectly accepted')
    cw,decision=cash_fixture();by_id={b['id']:b for b in cw['cash']['bills']}
    audit_cash_checkpoint(decision,cw,by_id,check);results.append({'id':'cash-prefix-replay-excludes-seed-from-earned-funds','passed':True})
    future=deepcopy(cw);future['cash']['events'][-1]['t']=21
    try:audit_cash_checkpoint(decision,future,by_id,check)
    except AuditFailure as exc:
        assert str(exc)=='Cash checkpoint excludes future events';results.append({'id':'future-collection-prefix-refused','passed':True,'refusal':str(exc)})
    else:raise AssertionError('Future collection incorrectly accepted')
    source=Path(__file__).with_name('temporal-auditor-controls.json')
    if source.exists():raise FileExistsError('Preserve prior control results')
    record={'schema':'beyond-beta-independent-temporal-audit-controls/v1','basis':'FICTIONAL_CASH_AND_EXECUTED_OFFLINE_GRAPH_NO_ECONOMIC_SAMPLER','status':'PASS','controls':results,'economicWorldsExecuted':0}
    source.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':'PASS','controls':len(results),'economicWorldsExecuted':0}))


if __name__=='__main__':main()
