# SPDX-License-Identifier: Apache-2.0
"""Post-freeze diagnostic replay: correct only the frozen auditor's epoch count.

This imports no simulator and executes no economic worlds. The frozen source,
original audit failures, histories and training choice are never modified.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/'foundations/audit_economic_trace.py'
EXPECTED='bbb845ffbfba640a9597265a283ab5e984b18ba793879ada71e7200c36ce4c17'
OLD="current_epoch=sum(e['kind']=='CANONICAL_ADMISSION' and records[e['key']]['descriptor']['function']==function for e in prefix)"
NEW="current_epoch=reconstructed_epoch(prefix,records,function)"


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def reconstructed_epoch(prefix, records, function):
    # The frozen graph starts each declared function at zero. Every successful
    # relevant canonical admission, Beta update and policy update increments it.
    # Inventory updates can be function-specific; a hash alone cannot identify
    # the affected functions, so this diagnostic refuses rather than guesses.
    if any(e['kind']=='INVENTORY_ADVANCED' for e in prefix):
        raise ValueError('Diagnostic scope refuses inventory update without full historical snapshots')
    return sum(e['kind'] in ('BETA_ADVANCED','POLICY_ADVANCED') or
               (e['kind']=='CANONICAL_ADMISSION' and records[e['key']]['descriptor']['function']==function)
               for e in prefix)


def controls():
    records={'a':{'descriptor':{'function':'contracts'}},'b':{'descriptor':{'function':'composition'}},'c':{'descriptor':{'function':'contracts'}}}
    admission=lambda key:{'kind':'CANONICAL_ADMISSION','key':key}
    beta={'kind':'BETA_ADVANCED','key':'beta'};policy={'kind':'POLICY_ADVANCED','key':'policy'}
    tests=[]
    def check(name,condition):
        tests.append({'name':name,'passed':bool(condition)})
        if not condition:raise AssertionError(name)
    check('Initial relevant admission contributes one',reconstructed_epoch([admission('a')],records,'contracts')==1)
    check('Beta update and fresh admission contribute two',reconstructed_epoch([beta,admission('a')],records,'contracts')==2)
    check('Old epoch cannot survive a later Beta update',reconstructed_epoch([admission('a'),beta],records,'contracts')!=1)
    check('New relevant admission invalidates prior epoch',reconstructed_epoch([beta,admission('a'),admission('c')],records,'contracts')!=2)
    check('Unrelated function admission does not increment this function',reconstructed_epoch([beta,admission('a'),admission('b')],records,'contracts')==2)
    check('Policy update increments every declared function',reconstructed_epoch([policy,admission('a')],records,'contracts')==2)
    check('Revocation does not erase historical increments',reconstructed_epoch([admission('a'),{'kind':'REVOKED','key':'a'}],records,'contracts')==1)
    refused=False
    try:reconstructed_epoch([{'kind':'INVENTORY_ADVANCED','key':'inventory'}],records,'contracts')
    except ValueError:refused=True
    check('Ambiguous inventory update is refused',refused)
    return tests


def main():
    parser=argparse.ArgumentParser();parser.add_argument('worlds',type=Path);parser.add_argument('--original-audit',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Preserve prior diagnostic output; choose a new path')
    if sha(FROZEN)!=EXPECTED:raise ValueError('Frozen auditor source changed')
    raw=FROZEN.read_text()
    if raw.count(OLD)!=1:raise ValueError('Diagnostic must replace exactly one arithmetic expression')
    ns={'__name__':'preserved_frozen_auditor_diagnostic','__file__':str(FROZEN),'reconstructed_epoch':reconstructed_epoch}
    exec(compile(raw.replace(OLD,NEW),str(FROZEN)+'[one-expression-diagnostic]','exec'),ns)
    protocol_path=ROOT/'protocol.json';protocol=json.loads(protocol_path.read_text());prior=json.loads(args.original_audit.read_text())
    if prior['inputSha256']!=sha(args.worlds) or prior['auditorSha256']!=EXPECTED:raise ValueError('Original audit/input identity mismatch')
    result={'schema':'beyond-beta-epoch-diagnostic-replay/v1','classification':'POST_FREEZE_AUDITOR_INSTRUMENTATION_DIAGNOSIS_NOT_NEW_PRODUCTION','originalAuditStatus':prior['status'],'originalAuditFailures':len(prior['failures']),'originalAuditSha256':sha(args.original_audit),'frozenAuditorSha256':EXPECTED,'diagnosticSha256':sha(__file__),'inputSha256':prior['inputSha256'],'protocolSha256':sha(protocol_path),'controls':controls(),'worlds':0,'checks':0,'worldsWithCompleteStageWorkerTrace':0,'historicalReuseReceiptsAudited':0,'failures':[],'epochMismatchWorlds':[],'epochMismatchUses':0,'graphEventCounts':{},'economicWorldsExecuted':0,'economicHistoriesModified':0,'selectionModified':False,'correction':{'oldExpression':OLD,'newExpression':NEW,'rule':'Relevant canonical admissions plus all preceding Beta and policy advances. Function-specific inventory changes without historical snapshots are refused.'}}
    event_counts=Counter()
    for index,world in enumerate(ns['read_worlds'](args.worlds)):
        result['worlds']+=1;s=world['summary'];identity={k:s.get(k) for k in ('policyId','scenario','profile','seed','arm')};graph=world.get('graph',{});events=graph.get('audit',{}).get('events',[]);records={r['descriptor']['key']:r for r in graph.get('records',[])}
        event_counts.update(e['kind'] for e in events)
        uses=[(u,j['id']) for j in world['jobs'] for u in j.get('completionReuseReceipts',[])]
        uses +=[(r['helperReceipt'],'revalidation:'+a['id']) for a in world.get('assets',[]) for r in a.get('revalidationHistory',[]) if r.get('helperReceipt')]
        mismatches=[]
        for use,origin in uses:
            p=use['permit']['payload'];prefix=events[:use['eventIndex']+1];function=records[use['key']]['descriptor']['function']
            old=sum(e['kind']=='CANONICAL_ADMISSION' and records[e['key']]['descriptor']['function']==function for e in prefix)
            if old!=p['comparisonEpoch']:
                corrected=reconstructed_epoch(prefix,records,function)
                mismatches.append({'origin':origin,'key':use['key'],'epoch':use['epoch'],'eventIndex':use['eventIndex'],'oldAdmissionOnlyCount':old,'recordedPermitEpoch':p['comparisonEpoch'],'correctedEpoch':corrected,'betaAdvances':sum(e['kind']=='BETA_ADVANCED' for e in prefix),'policyAdvances':sum(e['kind']=='POLICY_ADVANCED' for e in prefix),'exactCorrection':corrected==p['comparisonEpoch'],'checkpointRoot':use['logRoot']})
        if mismatches:
            result['epochMismatchWorlds'].append({'recordIndex':index,'identity':identity,'uses':mismatches});result['epochMismatchUses']+=len(mismatches)
        try:
            audited=ns['audit_world'](world,protocol)
            result['checks']+=audited['checks'];result['worldsWithCompleteStageWorkerTrace']+=audited['actualStageWorkerTraceComplete'];result['historicalReuseReceiptsAudited']+=audited['historicalReuseReceiptsAudited']
        except (ValueError,KeyError,TypeError) as exc:result['failures'].append({'recordIndex':index,'identity':identity,'error':str(exc)})
    result['graphEventCounts']=dict(event_counts)
    result['originalEpochFailureCount']=sum(x['error']=='New relevant admission cannot be bypassed' for x in prior['failures'])
    result['allOriginalFailuresExplainedExactly']=len(result['epochMismatchWorlds'])==len(prior['failures'])==result['originalEpochFailureCount'] and all(u['exactCorrection'] for w in result['epochMismatchWorlds'] for u in w['uses'])
    result['status']='PASS' if not result['failures'] and result['allOriginalFailuresExplainedExactly'] else 'FAIL'
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','worlds','checks','originalAuditStatus','originalAuditFailures','epochMismatchUses','historicalReuseReceiptsAudited','allOriginalFailuresExplainedExactly','economicWorldsExecuted')}))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
