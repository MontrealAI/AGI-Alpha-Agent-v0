# SPDX-License-Identifier: Apache-2.0
"""Append a finalized release view without rewriting the initial snapshot or receipts."""
import argparse,collections,datetime,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
subprocess.run([sys.executable,str(HERE/'build-accounting.py'),'--output',str(out)],check=True,capture_output=True)
s=read(out/'cost-summary.json');events=[json.loads(x) for x in (out/'resource-ledger.jsonl').read_text().splitlines()]
keys={e['id'] for e in events}
for receipt in sorted((ROOT/'reviews').rglob('receipt.json')):
 d=read(receipt)
 if d.get('schema')!='agi-alpha-command-resource/v1':continue
 key=hashlib.sha256(json.dumps([d.get('startedAt'),d.get('wallNs'),d.get('childCpuSeconds'),d.get('exitCode')],separators=(',',':')).encode()).hexdigest()
 identity='resource-'+key[:24]
 if identity in keys:continue
 keys.add(identity);relative=str(receipt.relative_to(ROOT))
 events.append({'id':identity,'costAccountKey':identity,'source':relative,'sourceSHA256':sha(receipt),'phase':d.get('phase'),'startedAt':d.get('startedAt'),'wallNs':d['wallNs'],'childCpuSeconds':d.get('childCpuSeconds'),'meterParentCpuNs':d.get('meterParentCpuNs'),'exitCode':d.get('exitCode'),'timedOut':d.get('timedOut'),'moneyUsd':None,'modelInferenceUsd':None,'humanMinutes':None,'basis':'Recorded local review/replay process only; not a fresh job or human wage bill.'})
 s['cutoffReceiptIdentities'].append({'path':relative,'sha256':sha(receipt),'bytes':receipt.stat().st_size})
phase=collections.defaultdict(lambda:{'commands':0,'nonzeroExits':0,'wallNsSum':0,'knownChildCpuSecondsSum':0,'unknownChildCpuRecords':0})
for e in events:
 d=phase[e['phase']];d['commands']+=1;d['nonzeroExits']+=e['exitCode'] not in [None,0];d['wallNsSum']+=e['wallNs']
 if e['childCpuSeconds'] is None:d['unknownChildCpuRecords']+=1
 else:d['knownChildCpuSecondsSum']+=e['childCpuSeconds']
(out/'resource-ledger.jsonl').write_text(''.join(json.dumps(e,separators=(',',':'))+'\n' for e in events))
s['uniqueRecordedCommandEvents']=len(events);s['phaseResourceSums']=dict(phase)
s['releaseCutoffUTC']=datetime.datetime.now(datetime.UTC).isoformat()
s['initialSnapshotPreserved']=True
s['finalAssetBindings']={'path':'resources/accounting/final-asset-bindings.json','sha256':sha(HERE/'final-asset-bindings.json')}
status={'B-construction':'Constructed, frozen and tested; four fresh customer reports accepted. Complete money unknown.','C2-construction':'Constructed and tested; three of four fresh handoffs accepted. Original C failures retained; full money unknown.','followup':'Complete: twelve scheduled executions on four new jobs; A4/B4/C2=3 frozen report acceptance, auxiliary navigation qualification retained.','market':'Complete: prior19,440 histories audited; original166new three-arm cells gated; separately registered384A/B histories audited; one separate cash-eligible software control.','publication':'PDF16pages and EN/FR offline demo complete and visually verified; assembly/upload/PR work after this cutoff remains unpriced, not free.'}
for c in s['components']:
 if c['id'] in status:c['status']=status[c['id']]
s['unmeteredActivities']=['Current-session model authoring/reasoning and extraction bills/token totals','Discovery tools and source acquisition not represented by command receipts','Browser/PDF attempts whose separate QA histories lack comparable process counters','Remaining artifact transfer and draft-PR publication after cutoff','Future upkeep and residual human/customer review']
s['requiresFinalization']=['Reconcile actual provider/tool bills if exposed','Measure matched active customer/operator effort','Resolve shared allocation without duplicate charges','Record future upkeep when incurred']
s['recordedNonzeroExitEvents']=sum(e['exitCode'] not in [None,0] for e in events)
write(out/'cost-summary.json',s)
bindings=read(HERE/'final-asset-bindings.json');assets=read(out/'asset-cost-register.json');assets['status']='TESTED_IDENTITIES_BOUND_COMPLETE_MONEY_UNKNOWN'
for arm,row in zip(['B','C'],assets['assets']):
 actual=bindings['assets'][arm];row.update({'testedAssetId':actual['id'],'sourcePath':actual['path'],'finalSourceSHA256':actual['sha256'],'completeConstructionUsd':None,'economicAdmission':'IDENTIFICATION_HOLD' if arm=='B' else 'HOLD_INCOMPLETE_EQUIVALENCE'})
 if arm=='C':row.update({'runtimeModelStageCalls':0,'runtimeModelStageBasis':'Observed no runtime model stage; complete equivalent scope failed on F03, so no economic discount is admitted.'})
write(out/'asset-cost-register.json',assets)
write(out/'FINALIZATION.json',{'schema':'agi-alpha-accounting-finalization/v1','releaseCutoffUTC':s['releaseCutoffUTC'],'initialBuilderSha256':sha(HERE/'build-accounting.py'),'finalizerSha256':sha(Path(__file__)),'resourceEvents':len(events),'nonzeroExits':s['recordedNonzeroExitEvents'],'completeCostKnown':False,'canonicalMoneyProjection':'../canonical-money-ledger.json','actualCollectionsUsd':0,'publicationsAfterCutoffUnpriced':True})
print(json.dumps({'releaseCutoffUTC':s['releaseCutoffUTC'],'resourceEvents':len(events),'nonzeroExits':s['recordedNonzeroExitEvents'],'actualFullCost':'UNKNOWN'}))
