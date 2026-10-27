# SPDX-License-Identifier: Apache-2.0
"""Read-only native reconciliation of 24 preselected completed histories.

Added after the source freeze as an extraction/audit utility. It never generates
or reruns a world, changes a frozen source, selects by outcome, or calls a model.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, ROUND_HALF_UP
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'beyond_beta'

def sha(path):
    result=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1048576),b''):result.update(block)
    return result.hexdigest()

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def digest(kind,value):
    return hashlib.sha256(b'BEYOND-BETA-V1\0'+kind.encode()+b'\0'+canonical(value)).hexdigest()

def round_scaled(amount,fraction):
    return int((Decimal(amount)*Decimal(str(fraction))).quantize(Decimal(1),rounding=ROUND_HALF_UP))

def cents(micros):return int((Decimal(micros)/10000).quantize(Decimal(1),rounding=ROUND_HALF_UP))

def verify_graph(audit):
    previous=digest('GENESIS',{})
    for index,event in enumerate(audit['events']):
        assert event['index']==index and event['previous']==previous,'Graph history continuity mismatch'
        assert event['hash']==digest('EVENT',{k:v for k,v in event.items() if k!='hash'}),'Graph event hash mismatch'
        previous=event['hash']
    nodes=[digest('MERKLE-LEAF',e) for e in audit['events']]
    if not nodes:root=digest('MERKLE-EMPTY',{})
    else:
        while len(nodes)>1:
            if len(nodes)%2:nodes.append(nodes[-1])
            nodes=[digest('MERKLE-NODE',dict(left=nodes[i],right=nodes[i+1])) for i in range(0,len(nodes),2)]
        root=nodes[0]
    assert root==audit['root'],'Graph root mismatch'
    return root

def verify_cash(world):
    book=world['cash'];funds=book['funds'];t=book['t']
    bills=[b for b in book['bills'] if b['t']<=t]
    accrued=sum(b['amountMicros'] for b in bills);paid=sum(b['amountMicros'] for b in bills if b['paid']);unpaid=accrued-paid
    invoices=[i for i in book['invoices'] if i['t']<=t]
    collected=sum(i['amountMicros'] for i in invoices if i['status']=='collected')
    cash=book['seedMicros']+collected-paid
    warranty=sum(round_scaled(i['amountMicros'],book['warrantyFraction']) for i in invoices if i['status']=='collected' and i['warrantyUntil']>=t and i['refundBillId'] is None)
    tax=round_scaled(max(0,collected-accrued),book['taxFraction']);reserve=book['baseReserveMicros']+warranty+tax
    liquid=cash-unpaid-reserve;earned=collected-accrued-reserve
    amounts=dict(cash=cash,collected=collected,accrued=accrued,paid=paid,unpaid=unpaid,
        receivable=sum(i['amountMicros'] for i in invoices if i['status']=='pending'),reserve=reserve,
        availableOperating=max(0,min(liquid,earned)),liquidAfterObligations=liquid,earnedAfterCosts=earned,
        baseReserve=book['baseReserveMicros'],warrantyReserve=warranty,taxReserve=tax)
    assert all(funds[key+'Micros']==value for key,value in amounts.items()),'Cash/fund ledger reconstruction mismatch'
    assert not world['unspentPublicCostHolds'] and not world['pendingEvents'],'Selected history has unresolved work or funding holds'
    assert book['actualCollectionsUsd']==0 and book['actualCompleteCostUsd'] is None
    projection=book['nativeProjectionInput']
    for arm in ('accrual','liquidity'):
        row=projection[arm]
        assert row['totalCollectedCents']==0 and row['costBasis']=='assumed' and row['operatingCostsComplete'] is True
        assert row['priceAssumptionCents']==cents(collected) and row['reserveCents']==cents(reserve)
        assert row['capabilityCostCents']==0 and row['reinvestmentBps']==0
        assert row['totalOperatingCostCents']==cents(accrued if arm=='accrual' else paid)
        assert row['obligationCents']==(0 if arm=='accrual' else cents(unpaid))
    assert projection['expectedEarnedMicros']==earned
    assert projection['expectedLiquidExcludingSeedMicros']==liquid-book['seedMicros']
    summary=world['summary']
    assert abs(summary['completeProfitUSD']-(collected-accrued)/1e6)<1e-6
    assert summary['accepted']==sum(j['usefulAccepted'] for j in world['jobs'])
    return dict(reconstructedFundMicros=amounts,seedMicros=book['seedMicros'],seedCountsAsRevenue=False,
                cashMatchesProjection=True,actualRevenueUsd=0,actualCompleteCostUsd=None)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--results',type=Path,default=STUDY/'results/primary');ap.add_argument('--run-native',action='store_true')
    args=ap.parse_args()
    if not args.run_native:
        print(json.dumps(dict(status='NOT_RUN',requires='Completed frozen campaign and explicit --run-native',selection='All six reference/seed1001 arms; network-alpha/seed1001 in every other declared scenario',expectedHistories=24)));return
    paths={name:STUDY/'validation'/name for name in ('native-confirmation-input.json','native-confirmation-results.json','native-confirmation-extraction.json')}
    assert all(not p.exists() for p in paths.values()),'Refuse to overwrite native confirmation evidence'
    summary_path=args.results/'summary.json';summary=json.loads(summary_path.read_text())
    assert summary['status']=='COMPLETE' and not (args.results/'failure.json').exists(),'Campaign is not complete'
    freeze_path=STUDY/'protocol/source-freeze.json';freeze=json.loads(freeze_path.read_text());p=json.loads((STUDY/'protocol.json').read_text())
    for item in freeze['files']:
        path=ROOT/item['path']
        assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],'Frozen source changed: '+item['path']
    assert summary['confirmationHistories']==p['experiment']['confirmationHistories']
    expected={('reference',1001,arm) for arm in p['experiment']['confirmationArms']}|{(s['id'],1001,'network-alpha') for s in p['scenarios']}
    assert len(expected)==24,'Prespecified selection size changed'
    summary_rows={(r['scenario'],r['seed'],r['arm']):r for r in summary['rows']}
    graph_source=next(x['sha256'] for x in freeze['files'] if x['path']=='beyond_beta/src/graph_lifecycle.py')
    ledger_path=args.results/'worlds.jsonl.gz';before_sha=sha(ledger_path);selected={};worlds=[];checks=[];line_count=0
    with gzip.open(ledger_path,'rb') as stream:
        for line_count,line in enumerate(stream,1):
            world=json.loads(line);row=world['summary'];key=(row['scenario'],row['seed'],row['arm'])
            if key not in expected:continue
            assert key not in selected,'Duplicate preselected history'
            assert row==summary_rows[key],'World differs from campaign summary'
            assert row['profile']=='reference' and world['actualModelCalls']==0
            graph_root=verify_graph(world['graph']['audit']);cash_check=verify_cash(world)
            identity=':'.join(map(str,key));selected[key]=identity
            worlds.append(dict(id=identity,projection=world['cash']['nativeProjectionInput'],graphAuditRoot=graph_root,graphSourceHash=graph_source,
                authorityChecks=[dict(fixture=f,week=row['settlementEndWeek']) for f in world['graph']['publicAuthorities']]))
            checks.append(dict(id=identity,scenario=key[0],seed=key[1],arm=key[2],compressedLedgerLine=line_count,
                rawLineSHA256=hashlib.sha256(line).hexdigest(),worldSHA256=hashlib.sha256(canonical(world)).hexdigest(),graphAuditRoot=graph_root,
                graphEvents=len(world['graph']['audit']['events']),projectionSHA256=hashlib.sha256(canonical(world['cash']['nativeProjectionInput'])).hexdigest(),cash=cash_check))
    assert set(selected)==expected,'Missing preselected histories'
    assert line_count==summary['confirmationHistories'],'Incomplete or duplicate confirmation stream'
    assert sha(ledger_path)==before_sha,'Ledger changed during extraction'
    worlds.sort(key=lambda w:w['id']);checks.sort(key=lambda c:c['id'])
    batch=dict(schema='beyond-beta-native-input/v1',sourceFreezeId=freeze['sourceId'],selectionRule='Prespecified before results: six reference seed1001 arms plus network-alpha seed1001 in every other scenario',
        confirmationLedgerSHA256=before_sha,summarySHA256=sha(summary_path),worlds=worlds)
    paths['native-confirmation-input.json'].write_text(json.dumps(batch,indent=2,allow_nan=False)+'\n')
    execution=subprocess.run(['node',str(STUDY/'src/native_bridge.mjs'),str(paths['native-confirmation-input.json']),str(paths['native-confirmation-results.json'])],capture_output=True,text=True,check=True)
    native=json.loads(paths['native-confirmation-results.json'].read_text())
    assert len(native['worlds'])==24 and native['measuredExecution']['nativePlanMissionCalls']==48
    for source,result in zip(worlds,native['worlds']):
        assert result['id']==source['id'] and result['graphAuditRoot']==source['graphAuditRoot']
        assert result['accounting']['reconciliation']['passed']
        assert all(r['result']['eligible'] for r in result['authorities']),'Declared terminal fixture authority unexpectedly unavailable'
    report=dict(schema='beyond-beta-native-confirmation-extraction/v1',status='PASS',classification='READ_ONLY_RECONCILIATION_OF_ACTUALLY_EXECUTED_SIMULATED_HISTORIES',
        selectedHistories=24,confirmationHistoriesScanned=line_count,sourceFreezeId=freeze['sourceId'],freezeSHA256=sha(freeze_path),
        extractionScriptSHA256=sha(Path(__file__)),confirmationLedgerSHA256=before_sha,summarySHA256=sha(summary_path),
        nativeInputSHA256=sha(paths['native-confirmation-input.json']),nativeResultsSHA256=sha(paths['native-confirmation-results.json']),
        measuredNativeExecution=native['measuredExecution'],checks=checks,stdout=execution.stdout.strip(),
        actualModelCalls=0,actualCommercialRevenueUsd=0,actualCompleteCostUsd=None,
        limit='Native financial reconciliation and fixture authority are checked; this creates no new market worlds, production work, live identity or causal evidence beyond the frozen simulation.')
    paths['native-confirmation-extraction.json'].write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status='PASS',selectedHistories=24,nativePlanMissionCalls=48,authorityCalls=native['measuredExecution']['authorityCalls'],sourceFreezeId=freeze['sourceId'])))

if __name__=='__main__':main()
