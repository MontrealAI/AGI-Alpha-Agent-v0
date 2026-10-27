# SPDX-License-Identifier: Apache-2.0
"""Two authorized verification replays; never append to primary histories."""
from pathlib import Path
import gzip
import hashlib
import json
import sys
import time

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'beyond_beta'
START=time.perf_counter();CPU_START=time.process_time()

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def semantic_hash(value):return hashlib.sha256(canonical(value)).hexdigest()

def verify_sources(record):
    assert record['sourceId']=='0c364c2e6fbc82a3112c9ef616e5d21b06b7792a24463de85cc3b9a6f5a42d20'
    for item in record['files']:
        path=ROOT/item['path']
        assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],'Frozen input changed: '+item['path']
    return len(record['files'])

def without_crypto(value):
    if isinstance(value,list):return [without_crypto(v) for v in value]
    if isinstance(value,dict):return {k:without_crypto(v) for k,v in value.items() if k not in {'permit','helperReceipt','completionReuseReceipts'}}
    return value

def sections(world):
    outcome_keys=('id','week','completionWeek','worker','buyer','factor','jobType','priceUSD','valueUSD','betaAtDispatch','actualBetaAtCompletion','finished','technicalAccepted','trueValid','usefulAccepted','costUSD','additionalRetentionUSD','repairs','usedAssets','billId','maximumCostUSD')
    asset_keys=('id','key','family','worker','originJobId','source','state','trueValid','trueEffect','observedEffect','admittedWeek','expiresWeek','lastMaintenanceWeek','realizedGrossSavingsUSD','useCount','programCostUSD','realizedDirectNetUSD','refusal')
    return dict(summary=world['summary'],cashAndAccounts=dict(cash=world['cash'],ledgerCostsMicros=world['summary']['ledgerCostsMicros'],costCategoriesMicros=world['costCategoriesMicros']),
        jobOutcomes=[{k:j.get(k) for k in outcome_keys} for j in world['jobs']],
        assetOutcomes=[{k:a.get(k) for k in asset_keys} for a in world['assets']],
        decisions=without_crypto(world['investmentDecisions']),candidateOutcomes=without_crypto(world['candidates']),
        resourceSchedules=world['resourceSchedules'],resourceConsumption=world['resourceConsumption'],
        offers=world['offers'],events=without_crypto(world['events']))

def differences(left,right,path='',limit=30):
    out=[]
    def visit(a,b,p):
        if len(out)>=limit:return
        if type(a)!=type(b):out.append(dict(path=p,original=a,replay=b));return
        if isinstance(a,dict):
            if set(a)!=set(b):out.append(dict(path=p,originalKeys=sorted(a),replayKeys=sorted(b)))
            for key in sorted(set(a)&set(b)):visit(a[key],b[key],p+'/'+str(key))
        elif isinstance(a,list):
            if len(a)!=len(b):out.append(dict(path=p,originalLength=len(a),replayLength=len(b)))
            for i,(x,y) in enumerate(zip(a,b)):visit(x,y,p+'/'+str(i))
        elif a!=b:out.append(dict(path=p,original=a,replay=b))
    visit(left,right,path);return out

def main():
    output=STUDY/'validation/semantic-reproduction.json';assert not output.exists(),'Refuse to overwrite verification evidence'
    results=STUDY/'results/primary';summary_path=results/'summary.json';summary=json.loads(summary_path.read_text());assert summary['status']=='COMPLETE'
    protocol_path=STUDY/'protocol.json';protocol=json.loads(protocol_path.read_text());freeze_path=STUDY/'protocol/source-freeze.json';freeze=json.loads(freeze_path.read_text())
    source_count=verify_sources(freeze)
    selection_path=results/'training-selection.json';selection=json.loads(selection_path.read_text())
    primary_paths=[summary_path,selection_path,results/'worlds.jsonl.gz',results/'training-worlds.jsonl.gz',results/'training-selection-freeze.json']
    primary_hashes={str(path.relative_to(ROOT)):sha(path) for path in primary_paths}
    first_alpha=next((dict(summaryIndex=i,**row) for i,row in enumerate(summary['rows']) if row['arm']=='network-alpha' and row['admittedAssets']>0),None)
    assert first_alpha is not None,'No recorded admitted Alpha history exists; do not substitute a scenario'
    identities=[('reference',1001,'trained-beta'),(first_alpha['scenario'],first_alpha['seed'],'network-alpha')]
    originals={}
    with gzip.open(results/'worlds.jsonl.gz','rb') as stream:
        for line_index,line in enumerate(stream,1):
            world=json.loads(line);s=world['summary'];key=(s['scenario'],s['seed'],s['arm'])
            if key in identities:
                assert key not in originals
                originals[key]=dict(world=world,line=line_index,rawLineSHA256=hashlib.sha256(line).hexdigest())
                if len(originals)==2:break
    assert len(originals)==2
    sys.path.insert(0,str(STUDY/'src'))
    from economy import run_world
    rows=[]
    for key in identities:
        saved=originals[key];original=saved['world'];s=original['summary']
        selected=selection['bestBeta' if key[2]=='trained-beta' else 'bestOptionalAlpha']['policy']
        assert selected==original['policy'],'Saved history policy differs from selected policy'
        wall=time.perf_counter();cpu=time.process_time()
        replay=run_world(protocol,selected,key[0],s['profile'],key[1],key[2])
        runtime=dict(wallSeconds=time.perf_counter()-wall,cpuSeconds=time.process_time()-cpu)
        original_sections=sections(original);replay_sections=sections(replay);comparisons={}
        for name in original_sections:
            a=original_sections[name];b=replay_sections[name]
            comparisons[name]=dict(equal=a==b,originalSHA256=semantic_hash(a),replaySHA256=semantic_hash(b),differences=differences(a,b))
        public_original={x['name']:x['publicKey'] for x in original['graph']['publicAuthorities']}
        public_replay={x['name']:x['publicKey'] for x in replay['graph']['publicAuthorities']}
        crypto=dict(sameFixtureIdentityNames=set(public_original)==set(public_replay),ephemeralPublicKeysDiffer=public_original!=public_replay,
            originalGraphRoot=original['graph']['audit']['root'],replayGraphRoot=replay['graph']['audit']['root'],graphRootsDiffer=original['graph']['audit']['root']!=replay['graph']['audit']['root'],
            exclusion='Ephemeral keys, signatures, ciphertext and dependent commitments are integrity artifacts, not seeded economic outputs. Empty graphs can have identical genesis roots.')
        assert original['actualModelCalls']==replay['actualModelCalls']==0
        rows.append(dict(identity={k:s[k] for k in ('scenario','seed','profile','arm','policyId')},originalConfirmationLine=saved['line'],originalRawLineSHA256=saved['rawLineSHA256'],
            selectedPolicy=selected,semanticMatch=all(x['equal'] for x in comparisons.values()),comparisons=comparisons,
            originalSummary=original['summary'],replaySummary=replay['summary'],
            originalJobOutcomes=original_sections['jobOutcomes'],replayJobOutcomes=replay_sections['jobOutcomes'],
            originalAssetOutcomes=original_sections['assetOutcomes'],replayAssetOutcomes=replay_sections['assetOutcomes'],
            cryptographicArtifacts=crypto,measuredReplay=runtime,actualModelCalls=0,actualCommercialRevenueUsd=0,actualCompleteVerificationCostUsd=None))
    assert verify_sources(freeze)==source_count
    final_hashes={str(path.relative_to(ROOT)):sha(path) for path in primary_paths};assert final_hashes==primary_hashes,'Primary results changed during verification'
    report=dict(schema='beyond-beta-semantic-reproduction/v1',status='PASS' if all(r['semanticMatch'] for r in rows) else 'FAIL',
        classification='POST_FREEZE_VERIFICATION_REPLAYS_OF_TWO_ALREADY_RECORDED_HISTORIES; NOT_ADDITIONAL_CONFIRMATION_SAMPLES',
        sourceFreezeId=freeze['sourceId'],frozenSourcesVerifiedBeforeAndAfter=source_count,protocolSHA256=sha(protocol_path),scriptSHA256=sha(Path(__file__)),
        originalPrimaryFilesSHA256=primary_hashes,primaryFilesUnchanged=True,
        selectionRule='reference/1001/trained-beta plus first network-alpha history with admittedAssets>0 in original prescribed confirmation order',
        alphaSelectionSummaryIndex=first_alpha['summaryIndex'],verificationReplayCount=2,additionalPrimaryHistories=0,replays=rows,
        totalMeasuredVerification=dict(wallSeconds=time.perf_counter()-START,cpuSeconds=time.process_time()-CPU_START,includes='source/file hashing, read-only extraction, two simulation replays, and comparison'),
        actualModelCalls=0,actualCommercialRevenueUsd=0,actualCompleteVerificationCostUsd=None,
        interpretation='Exact semantic reproduction tests that fresh ephemeral cryptographic randomness and relocation do not alter these two histories. It does not independently validate economic assumptions or generalize to every seed.')
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+chr(10))
    print(json.dumps(dict(status=report['status'],verificationReplayCount=2,primaryFilesUnchanged=True,frozenSources=source_count,
        histories=[dict(identity=r['identity'],semanticMatch=r['semanticMatch'],ephemeralPublicKeysDiffer=r['cryptographicArtifacts']['ephemeralPublicKeysDiffer'],graphRootsDiffer=r['cryptographicArtifacts']['graphRootsDiffer'],measuredReplay=r['measuredReplay']) for r in rows],output=str(output))))
    if report['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
