#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the frozen training/confirmation campaign only with explicit --run.

Ordinary invocation reports campaign size without producing any economic worlds.
Every simulated history is retained, including failures and selected-policy losses.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from economy import policy_grid,run_world


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def file_sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def select(rows,policies,p):
    profiles=p['experiment']['trainingProfileWeights']; scenarios=p['experiment']['trainingScenarioWeights']; scored=[]
    for index,policy in enumerate(policies):
        samples=[r for r in rows if r['policyId']==policy['id']]
        weights=[profiles[r['profile']]*scenarios[r['scenario']]/len(p['experiment']['trainingSeeds']) for r in samples]
        score=sum(w*r['completeProfitUSD'] for w,r in zip(weights,samples))
        accepted=sum(w*r['technicalAccepted'] for w,r in zip(weights,samples)); false=sum(w*r['falsePasses'] for w,r in zip(weights,samples))
        rate=false/accepted if accepted else 0
        scored.append(dict(policy=policy,index=index,weightedCompleteProfitUSD=score,weightedTechnicalAccepted=accepted,weightedFalsePasses=false,falsePassFraction=rate,cashValid=all(r['cashValid'] for r in samples),eligible=all(r['cashValid'] for r in samples) and rate<=p['engineDefaults']['qualityEligibilityFalsePassMax'],histories=len(samples)))
    def best(rules):
        eligible=[r for r in scored if r['eligible'] and r['policy']['investment'] in rules]
        return max(eligible,key=lambda r:(r['weightedCompleteProfitUSD'],-r['index'])) if eligible else None
    return dict(schema='beyond-beta-training-selection/v1',allPolicies=scored,bestBeta=best(['never']),bestOptionalAlpha=best(['positiveExpectedNetValue','riskAdjustedPositiveNetValue']),overallWinner=best(p['policies']['investmentRules']),selectionBasis='TRAINING_ONLY; exact ties use declared policy-grid order; no held-out outcome has been read')


def summaries(rows):
    cells=[]
    for scenario in sorted({r['scenario'] for r in rows}):
        for arm in dict.fromkeys(r['arm'] for r in rows):
            sample=[r for r in rows if r['scenario']==scenario and r['arm']==arm]; values=[r['completeProfitUSD'] for r in sample]
            cells.append(dict(scenario=scenario,arm=arm,n=len(sample),meanCompleteProfitUSD=statistics.mean(values),minimumProfitUSD=min(values),maximumProfitUSD=max(values),sdProfitUSD=statistics.stdev(values) if len(values)>1 else 0,
                positiveProfitWorlds=sum(x>0 for x in values),totalAccepted=sum(r['accepted'] for r in sample),totalAdmittedAssets=sum(r['admittedAssets'] for r in sample),totalAssetUses=sum(r['assetUses'] for r in sample),meanProgramNetResourcesUSD=statistics.mean(r['retentionResearchProgramNetResourcesUSD'] for r in sample)))
    pairs=[]; lookup={(r['scenario'],r['seed'],r['arm']):r for r in rows}
    for scenario,seed in sorted({(r['scenario'],r['seed']) for r in rows}):
        get=lambda arm:lookup[scenario,seed,arm]['completeProfitUSD']
        pairs.append(dict(scenario=scenario,seed=seed,profile=lookup[scenario,seed,'network-alpha']['profile'],
            incrementalAlphaMovingUSD=get('network-alpha')-get('moving-beta-only'),incrementalAlphaFrozenUSD=get('network-alpha-frozen-beta')-get('frozen-beta-only'),
            sharingVersusPrivateUSD=get('network-alpha')-get('private-alpha-availability-ablation'),trainedWholePolicyUSD=get('network-alpha')-get('trained-beta'),
            erosionInteractionUSD=(get('network-alpha')-get('moving-beta-only'))-(get('network-alpha-frozen-beta')-get('frozen-beta-only'))))
    return dict(rows=rows,cells=cells,pairedComparisons=pairs)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,default=ROOT/'protocol.json');ap.add_argument('--output',type=Path,default=ROOT/'results/primary');ap.add_argument('--run',action='store_true');ap.add_argument('--max-seconds',type=float,default=1800)
    args=ap.parse_args();p=json.loads(args.protocol.read_text());policies=policy_grid(p);exp=p['experiment']
    expected_train=len(policies)*len(exp['trainingSeeds'])*len(exp['trainingProfiles'])*len(exp['trainingScenarios'])
    expected_confirmation=len(exp['confirmationSeeds'])*len(p['scenarios'])*len(exp['confirmationArms'])
    assert expected_train==exp['trainingHistories'] and expected_confirmation==exp['confirmationHistories']
    if not args.run:
        print(json.dumps(dict(status='NOT_RUN',trainingHistories=expected_train,confirmationHistories=expected_confirmation,requires='Root freeze before explicit --run.')));return
    if p['status']!='FROZEN_BEFORE_OUTCOMES':raise SystemExit('Refusing calibrated execution before the protocol is frozen.')
    out=args.output
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite an existing result directory.')
    out.mkdir(parents=True,exist_ok=True);start=time.monotonic();cpu=time.process_time();counter=0;train=[];confirmed=[]
    sources=[args.protocol,ROOT/'src/economy.py',ROOT/'src/graph_lifecycle.py',ROOT/'src/fixture_factory.py',Path(__file__).resolve(),ROOT.parent/'venture_creation/src/finance_capacity.py']
    frontier=ROOT/'calibration/frontier-configuration.json'
    if frontier.exists():sources.append(frontier)
    hashes={str(path.resolve().relative_to(ROOT.parent)):file_sha256(path) for path in sources}
    source_closure=hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    write_json(out/'run-inputs.json',dict(sourceHashes=hashes,protocolStatus=p['status'],actualModelCalls=0,actualRevenueUSD=0,actualCompleteCostUSD=None,wallTimeLimitSeconds=args.max_seconds))
    def record(world,stream):
        nonlocal counter
        stream.write(json.dumps(world,separators=(',',':'),allow_nan=False)+'\n');counter+=1
        if counter%64==0:print(json.dumps(dict(completed=counter,elapsedSeconds=round(time.monotonic()-start,2))),flush=True)
        if time.monotonic()-start>args.max_seconds:raise RuntimeError('Declared campaign wall-time envelope exceeded; partial evidence preserved, no automatic rerun.')
    try:
        with gzip.open(out/'training-worlds.jsonl.gz','wt',compresslevel=3) as stream:
            for policy in policies:
                for profile in exp['trainingProfiles']:
                    for scenario in exp['trainingScenarios']:
                        for seed in exp['trainingSeeds']:
                            world=run_world(p,policy,scenario,profile,seed,'network-alpha');record(world,stream);train.append(world['summary'])
        chosen=select(train,policies,p);write_json(out/'training-selection.json',chosen);write_json(out/'training-summaries.json',train)
        write_json(out/'training-selection-freeze.json',dict(schema='beyond-beta-training-selection-freeze/v1',frozenAtUtc=datetime.now(timezone.utc).isoformat(),confirmationHistoriesAlreadyRun=0,
            selectedRuleIds={k:chosen[k]['policy']['id'] if chosen[k] else None for k in ('bestBeta','bestOptionalAlpha','overallWinner')},
            selectedRules={k:chosen[k]['policy'] if chosen[k] else None for k in ('bestBeta','bestOptionalAlpha','overallWinner')},
            trainingWorldsSha256=file_sha256(out/'training-worlds.jsonl.gz'),trainingSelectionSha256=file_sha256(out/'training-selection.json'),protocolSha256=file_sha256(args.protocol),runtimeSourceClosureId=source_closure,sourceHashes=hashes,
            rule='Automatic sequential commitment after all training and before any confirmation. No policy or calibration changes are permitted after this record.'))
        if chosen['bestBeta'] is None or chosen['bestOptionalAlpha'] is None:
            write_json(out/'summary.json',dict(status='UNQUALIFIED_TRAINING_SUBSET',trainingCompleted=len(train),confirmationCompleted=0,selection=chosen));return
        with gzip.open(out/'worlds.jsonl.gz','wt',compresslevel=3) as stream:
            for scenario in p['scenarios']:
                for seed in exp['confirmationSeeds']:
                    profile=exp['trainingProfiles'][(seed-1001)%3]
                    for arm in exp['confirmationArms']:
                        selected=chosen['bestBeta'] if arm=='trained-beta' else chosen['bestOptionalAlpha']
                        world=run_world(p,selected['policy'],scenario['id'],profile,seed,arm);record(world,stream);confirmed.append(world['summary'])
                        if scenario['id']=='reference' and seed==1001:write_json(out/f'demonstration-{arm}.json',world)
        result=summaries(confirmed);result.update(schema='beyond-beta-campaign/v1',status='COMPLETE',trainingHistories=len(train),confirmationHistories=len(confirmed),selection=chosen,
            wallSeconds=time.monotonic()-start,cpuSeconds=time.process_time()-cpu,actualModelCalls=0,actualRevenueUSD=0,actualCompleteCostUSD=None)
        write_json(out/'summary.json',result)
        print(json.dumps({k:result[k] for k in ('status','trainingHistories','confirmationHistories','wallSeconds','cpuSeconds')}),flush=True)
    except Exception as exc:
        write_json(out/'failure.json',dict(status='FAILED_PRESERVED',errorType=type(exc).__name__,message=str(exc),historiesWritten=counter,trainingCompleted=len(train),confirmationCompleted=len(confirmed),wallSeconds=time.monotonic()-start))
        raise


if __name__=='__main__':main()
