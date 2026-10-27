#!/usr/bin/env python3
"""Operational continuation only; never changes scientific inputs or repeats a world.

Prepared before inspection of calibrated outcomes. Original runner, sources and
failure record stay unchanged. Complete gzip records define the authoritative
prefix (the cap-triggering record precedes its summary-list append). New gzip
members append to the same file; original byte-prefix hashes are preserved.
"""
from __future__ import annotations
import argparse
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
import run_experiment as original
from economy import policy_grid, run_world
from freeze_study import verify


def read_prefix(path, expected):
    rows = []
    if not path.exists():
        return rows
    # gzip CRC, complete JSON and exact expected event order must all verify.
    # An incomplete or corrupt tail is a hard failure, not silently truncated.
    with gzip.open(path, 'rt') as stream:
        for index, line in enumerate(stream):
            if index >= len(expected):
                raise ValueError('More records than prespecified')
            if not line.endswith('\n'):
                raise ValueError('Incomplete final record')
            world = json.loads(line)
            row = world['summary']
            policy, scenario, profile, seed, arm = expected[index]
            target = (policy['id'], scenario, profile, seed, arm)
            actual = tuple(row[k] for k in ('policyId', 'scenario', 'profile', 'seed', 'arm'))
            if actual != target:
                raise ValueError(f'Non-prefix record at index {index}: {actual} != {target}')
            rows.append(row)
    return rows


def remaining_worlds(p, tasks, workers):
    """Bounded independent execution; yield in the unchanged prescribed order."""
    if workers == 1:
        for policy,scenario,profile,seed,arm in tasks:
            yield run_world(p,policy,scenario,profile,seed,arm)
        return
    iterator=iter(tasks)
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        pending=deque()
        for _ in range(workers):
            task=next(iterator,None)
            if task is not None:pending.append(pool.submit(run_world,p,*task))
        while pending:
            future=pending.popleft()
            world=future.result()
            yield world
            task=next(iterator,None)
            if task is not None:pending.append(pool.submit(run_world,p,*task))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--resume-prespecified', action='store_true')
    ap.add_argument('--output', type=Path, default=ROOT/'results/primary')
    ap.add_argument('--max-seconds', type=float, default=5400)
    ap.add_argument('--workers', type=int, choices=(1,2,3,4), default=4)
    args = ap.parse_args()
    if not args.resume_prespecified:
        print(json.dumps({'status':'NOT_RUN','requires':'Original preserved wall-time-cap failure; explicit root continuation'}))
        return
    verify(ROOT/'protocol/source-freeze.json')
    out=args.output
    if (out/'summary.json').exists():
        raise SystemExit('Refusing continuation after a final summary')
    failure=json.loads((out/'failure.json').read_text())
    if failure['message'] not in ('Declared campaign wall-time envelope exceeded; partial evidence preserved, no automatic rerun.', 'Explicit storage-capacity interruption; original bytes preserved; recovered complete ordered records only.'):
        raise SystemExit('Unsupported interruption or recovery record')
    if (out/'continuation-start.json').exists():
        raise SystemExit('No automatic repeated continuation')
    p=json.loads((ROOT/'protocol.json').read_text())
    policies=policy_grid(p); exp=p['experiment']
    expected_train=[(policy,scenario,profile,seed,'network-alpha')
        for policy in policies for profile in exp['trainingProfiles']
        for scenario in exp['trainingScenarios'] for seed in exp['trainingSeeds']]
    train_path=out/'training-worlds.jsonl.gz'; confirm_path=out/'worlds.jsonl.gz'
    train=read_prefix(train_path,expected_train)
    if len(train)<len(expected_train) and confirm_path.exists():
        raise SystemExit('Confirmation exists before training was complete')
    prefixes={path.name:{'bytes':path.stat().st_size,'sha256':original.file_sha256(path)}
        for path in (train_path,confirm_path) if path.exists()}
    start=time.monotonic();cpu=time.process_time();new_count=0
    original.write_json(out/'continuation-start.json',dict(
        schema='operational-prefix-continuation/v1',startedAtUtc=datetime.now(timezone.utc).isoformat(),
        originalFailure=failure,originalPrefixes=prefixes,
        continuationSourceSHA256=original.file_sha256(Path(__file__)),
        amendmentSHA256=original.file_sha256(ROOT/'publication/RUNTIME_CONTINUATION_AMENDMENT.md'),
        additionalWallTimeLimitSeconds=args.max_seconds,
        independentWorkers=args.workers,prescribedOutputOrderUnchanged=True,
        scientificInputsChanged=False,completedHistoriesReplaced=False))

    def record(world,stream):
        nonlocal new_count
        stream.write(json.dumps(world,separators=(',',':'),allow_nan=False)+'\n')
        new_count+=1
        if new_count%64==0:
            print(json.dumps(dict(continuationCompleted=new_count,elapsedSeconds=round(time.monotonic()-start,2))),flush=True)
        if time.monotonic()-start>args.max_seconds:
            raise RuntimeError('Additional operational envelope exhausted; evidence preserved')

    confirmed=[]
    try:
        if len(train)<len(expected_train):
            with gzip.open(train_path,'at',compresslevel=3) as stream:
                for world in remaining_worlds(p,expected_train[len(train):],args.workers):
                    record(world,stream);train.append(world['summary'])
        chosen=original.select(train,policies,p)
        selection_path=out/'training-selection.json'
        freeze_path=out/'training-selection-freeze.json'
        if freeze_path.exists():
            frozen=json.loads(freeze_path.read_text())
            if json.loads(selection_path.read_text()) != chosen:
                raise ValueError('Existing training selection does not match immutable training prefix')
            for key,path in [('trainingWorldsSha256',train_path),('trainingSelectionSha256',selection_path),('protocolSha256',ROOT/'protocol.json')]:
                if frozen[key]!=original.file_sha256(path):
                    raise ValueError('Existing training commitment mismatch: '+key)
        else:
            if confirm_path.exists():
                raise ValueError('No training freeze before existing confirmation')
            original.write_json(selection_path,chosen)
            original.write_json(out/'training-summaries.json',train)
            hashes=json.loads((out/'run-inputs.json').read_text())['sourceHashes']
            closure=hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            original.write_json(freeze_path,dict(schema='beyond-beta-training-selection-freeze/v1',
                frozenAtUtc=datetime.now(timezone.utc).isoformat(),confirmationHistoriesAlreadyRun=0,
                selectedRuleIds={k:chosen[k]['policy']['id'] if chosen[k] else None for k in ('bestBeta','bestOptionalAlpha','overallWinner')},
                selectedRules={k:chosen[k]['policy'] if chosen[k] else None for k in ('bestBeta','bestOptionalAlpha','overallWinner')},
                trainingWorldsSha256=original.file_sha256(train_path),trainingSelectionSha256=original.file_sha256(selection_path),
                protocolSha256=original.file_sha256(ROOT/'protocol.json'),runtimeSourceClosureId=closure,sourceHashes=hashes,
                rule='Same original selection code after all prespecified training and before any confirmation; operational continuation only.'))
        if chosen['bestBeta'] is None or chosen['bestOptionalAlpha'] is None:
            original.write_json(out/'summary.json',dict(status='UNQUALIFIED_TRAINING_SUBSET',trainingCompleted=len(train),confirmationCompleted=0,selection=chosen))
            return
        expected_confirmation=[]
        for scenario in p['scenarios']:
            for seed in exp['confirmationSeeds']:
                profile=exp['trainingProfiles'][(seed-1001)%3]
                for arm in exp['confirmationArms']:
                    selected=chosen['bestBeta'] if arm=='trained-beta' else chosen['bestOptionalAlpha']
                    expected_confirmation.append((selected['policy'],scenario['id'],profile,seed,arm))
        confirmed=read_prefix(confirm_path,expected_confirmation)
        with gzip.open(confirm_path,'at',compresslevel=3) as stream:
            for world in remaining_worlds(p,expected_confirmation[len(confirmed):],args.workers):
                scenario=world['summary']['scenario'];seed=world['summary']['seed'];arm=world['summary']['arm']
                record(world,stream);confirmed.append(world['summary'])
                if scenario=='reference' and seed==1001:
                    target=out/f'demonstration-{arm}.json'
                    if target.exists():raise ValueError('Would overwrite a completed demonstration history')
                    original.write_json(target,world)
        # A wall-cap may have written a demonstration before its separate export;
        # reconstruct only an absent export from its already recorded full world.
        missing={arm for arm in exp['confirmationArms'] if not (out/f'demonstration-{arm}.json').exists()}
        if missing:
            with gzip.open(confirm_path,'rt') as stream:
                for line in stream:
                    world=json.loads(line);row=world['summary']
                    if row['scenario']=='reference' and row['seed']==1001 and row['arm'] in missing:
                        original.write_json(out/f"demonstration-{row['arm']}.json",world);missing.remove(row['arm'])
                    if not missing:break
        if missing:raise ValueError('Missing prespecified demonstration histories')
        for name,meta in prefixes.items():
            digest=hashlib.sha256();remaining=meta['bytes']
            with (out/name).open('rb') as stream:
                while remaining:
                    block=stream.read(min(1048576,remaining))
                    if not block:raise ValueError('Original recorded prefix was shortened')
                    digest.update(block);remaining-=len(block)
            if digest.hexdigest()!=meta['sha256']:
                raise ValueError('Original recorded compressed prefix changed')
        verify(ROOT/'protocol/source-freeze.json')
        result=original.summaries(confirmed)
        result.update(schema='beyond-beta-campaign/v1',status='COMPLETE',trainingHistories=len(train),confirmationHistories=len(confirmed),selection=chosen,
            wallSeconds=failure['wallSeconds']+time.monotonic()-start,
            cpuSeconds=None,continuationCpuSeconds=time.process_time()-cpu,
            actualModelCalls=0,actualRevenueUSD=0,actualCompleteCostUSD=None,
            operationalContinuation=True,originalFailurePreserved='failure.json',
            originalCpuTimeUnavailable=True)
        original.write_json(out/'summary.json',result)
        original.write_json(out/'continuation-completion.json',dict(status='COMPLETE',newHistories=new_count,
            continuationWallSeconds=time.monotonic()-start,continuationCpuSeconds=time.process_time()-cpu,
            originalPrefixesPreserved=True,trainingHistories=len(train),confirmationHistories=len(confirmed)))
        print(json.dumps({k:result[k] for k in ('status','trainingHistories','confirmationHistories','wallSeconds')}),flush=True)
    except Exception as exc:
        original.write_json(out/'continuation-failure.json',dict(status='FAILED_PRESERVED',type=type(exc).__name__,message=str(exc),
            newHistoriesWritten=new_count,wallSeconds=time.monotonic()-start))
        raise

if __name__=='__main__':main()
