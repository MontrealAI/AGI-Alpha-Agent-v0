# SPDX-License-Identifier: Apache-2.0
import argparse, collections, datetime, hashlib, json, pathlib

parser=argparse.ArgumentParser(description='Append a scoped resource/accounting snapshot without changing original receipts.')
parser.add_argument('--output',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent)
args=parser.parse_args()
here=pathlib.Path(__file__).resolve().parent
resources=here.parent
study=resources.parent
out=args.output.resolve()
out.mkdir(parents=True,exist_ok=True)
for name in ['cost-summary.json','asset-cost-register.json','resource-ledger.jsonl']:
    if (out/name).exists():parser.error('Existing accounting snapshot is immutable; use --output with a new directory')
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,value):
    with (out/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
records=[];identities=[];seen={};duplicates=[]
paths=sorted(p for p in resources.rglob('receipt.json') if here not in p.parents)
paths+=sorted(p for p in resources.glob('*construction*.json') if p.is_file())
for path in paths:
    raw=path.read_bytes();d=json.loads(raw);relative=str(path.relative_to(study))
    identities.append({'path':relative,'sha256':sha(raw),'bytes':len(raw)})
    events=d.get('commands',[d])
    for index,e in enumerate(events):
        if 'wallNs' not in e:continue
        key=sha(json.dumps([e.get('startedAt'),e.get('wallNs'),e.get('childCpuSeconds'),e.get('exitCode')],separators=(',',':')).encode())
        if key in seen:
            duplicates.append({'source':relative,'index':index,'sameResourceEventAs':seen[key]});continue
        event_id='resource-'+key[:24];seen[key]=event_id
        records.append({'id':event_id,'source':relative,'sourceSHA256':sha(raw),'sourceEventIndex':index,
            'phase':e.get('phase',d.get('phase','unclassified')),'startedAt':e.get('startedAt'),
            'wallNs':e['wallNs'],'childCpuSeconds':e.get('childCpuSeconds'),'meterParentCpuNs':e.get('meterParentCpuNs'),
            'exitCode':e.get('exitCode'),'timedOut':e.get('timedOut'),
            'moneyUsd':None,'modelInferenceUsd':None,'humanMinutes':None,
            'basis':'measured local command resource; not complete labor/inference cost',
            'scientificAcceptance':'NOT_INFERRED_FROM_PROCESS_EXIT','costAccountKey':event_id})
phase=collections.defaultdict(lambda:{'commands':0,'nonzeroExits':0,'wallNsSum':0,'knownChildCpuSecondsSum':0.0,'unknownChildCpuRecords':0})
for e in records:
    p=phase[e['phase']];p['commands']+=1;p['nonzeroExits']+=e['exitCode'] not in [None,0];p['wallNsSum']+=e['wallNs']
    if e['childCpuSeconds'] is None:p['unknownChildCpuRecords']+=1
    else:p['knownChildCpuSecondsSum']+=e['childCpuSeconds']
with (out/'resource-ledger.jsonl').open('x') as f:
    for e in records:f.write(json.dumps(e,separators=(',',':'))+'\n')
opening=[]
for name in ['account-opening.json','followup-account-opening.json']:
    path=resources/name
    if path.exists():
        raw=path.read_bytes();opening.append({'path':str(path.relative_to(study)),'sha256':sha(raw),'bytes':len(raw)})
components=[
 ('discovery','Prior-owner/source audit, literature and prior-market audit','shared-study','incurred; incomplete metering'),
 ('design','Offering, acceptance, protocol and comparator design','shared-study','incurred; model/time money unknown'),
 ('B-construction','Model extraction prompt/compiler and integration','asset-B','incurred; full source closure pending'),
 ('C-failed-construction','Original conventional comparator, development failures and primary unqualified result','asset-C2-ancestry','incurred; do not erase or charge twice'),
 ('C2-construction','Stronger conventional resolver after preserved primary failure','asset-C2','in progress; final identity/cost pending'),
 ('model-production','Actual A curator and B model-extraction stages','mission-attempt','actual model money and tokens not exposed; keep unknown'),
 ('execution','Local Workbench/consumer process execution','mission-attempt','partially metered, not complete workflow'),
 ('verification','Independent complete-deliverable and source-integrity checks','shared-or-mission','partially metered; allocation unknown'),
 ('correction','Failed controls, comparator fairness correction and complete package correction','asset-or-mission','incurred; retain failures'),
 ('integration','Existing core/Workbench/history/canonical ledger integration','shared-study','incurred; complete money unknown'),
 ('primary','All 18 primary executions and unqualified complete-package/comparator result','research-confirmation','incurred; no customer acceptance inferred'),
 ('followup','Separate fresh followup, package controls and independent acceptance','research-confirmation','in progress; final costs/acceptance pending'),
 ('market','Original-history audit, adapter, controls, prospective scenarios and later admitted run','research-analysis','partly incurred; scientific market campaign not yet executed'),
 ('publication','Analysis, figures, bilingual demo, LaTeX/PDF, packaging and delivery','research-publication','in progress; complete cost unknown'),
 ('upkeep','Future compatibility, model/schema drift, support and retained asset maintenance','recurring-asset','not observed; amount and cadence unknown'),
 ('residual-human','Actual operator/customer review, exception handling and corrections','human-residual','active human time unknown; no elapsed-agent conversion')
]
summary={'schema':'agi-alpha-transfer-complete-cost-register/v1','createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'PARTIAL_PROCESS_MEASUREMENT_FULL_COST_UNKNOWN','accountOpenings':opening,'originalReceiptsModified':False,
 'cutoffReceiptIdentities':identities,'resourceLedger':'resource-ledger.jsonl','uniqueRecordedCommandEvents':len(records),
 'duplicateResourceEventsNotAdded':duplicates,'phaseResourceSums':dict(phase),
 'resourceBoundary':'Sums describe recorded unique command activity, not elapsed project duration, full end-to-end latency, human labor, invoice value or a guaranteed total CPU bound; nested/parallel scope and unmetered activities remain explicit.',
 'monetaryViews':{'marginalPerAttemptUsd':None,'recurringPerEquivalentAcceptedDeliverableUsd':None,'fullyLoadedStudyUsd':None,
  'fullyLoadedBConstructionUsd':None,'fullyLoadedC2ConstructionUsd':None,'modelInferenceTotalUsd':None,'toolAndComputeBillsUsd':None,
  'remainingHumanMinutes':None,'customerReviewMinutes':None,'actualCustomerCollectionsUsd':0,'profitUsd':None,'availableSurplusUsd':None},
 'components':[{'id':i,'scope':s,'account':a,'status':v,'moneyUsd':None,'humanMinutes':None} for i,s,a,v in components],
 'knownFailures':['Failed development controls and integration attempts in original receipts','Primary C unresolved-target comparator failure','Primary incomplete useful packages','Any subsequent failed candidate, validation, correction or publication attempt must be appended, not written off'],
 'allocationRule':'Every receipt/resource event has one costAccountKey. Shared work is entered once in the study account; asset and per-mission tables are allocation views, not additional charges. Unknown shared allocation is not silently 100 percent in both B and C2.',
 'failureRule':'Include failed construction in asset cost; include failed production in cost per equivalent accepted output. Do not also amortize those same charges into both nominal delivery and investment.',
 'marketBoundary':'The m and I scenario values are transparent conditional envelopes, not these unknown actual bills or complete upper bounds.',
 'requiresFinalization':['Append final followup receipts and independent complete acceptance','Bind B and C2 exact final source identities','Append economic experiment/audit, figures, document, browser and packaging receipts','Reconcile any exposed provider billing','Resolve shared-cost allocation or retain its uncertainty','Record residual human effort if actually observed']}
write('cost-summary.json',summary)
old=json.loads((resources/'conventional-construction.json').read_text()) if (resources/'conventional-construction.json').exists() else {}
assets={'schema':'agi-alpha-transfer-asset-cost-register/v1','status':'IDENTITIES_AND_COMPLETE_MONEY_PENDING_FINALIZATION',
 'assets':[
  {'id':'B-model-extraction-and-exact-compiler','sourcePath':'src/intake.py','finalSourceSHA256':None,
   'primaryExecutionFreezeSHA256':'7f505b229212908d32f05b69d7016946a71356261ad88826e52ac5dccbc7493e',
   'includes':['discovery/design allocation','prompt and compiler authoring','all failed controls','native integration','independent verification','common complete-package correction allocation'],
   'completeConstructionUsd':None,'recurringInferenceUsd':None,'upkeepUsd':None,'economicAdmission':'HOLD'},
  {'id':'C2-conventional-source-intake','sourcePath':None,'finalSourceSHA256':None,
   'preservedOriginalConventionalSHA256':old.get('sourceSha256'),
   'includes':['discovery/design allocation','original failed C construction and controls','primary comparator/package failure','C2 resolver construction','common complete-package correction allocation','independent fresh acceptance'],
   'completeConstructionUsd':None,'runtimeModelStageCalls':None,'designRuntimeModelStageCalls':0,
   'runtimeModelStageBasis':'Unconfirmed design intent; require executed complete-scope confirmation before economic use.',
   'upkeepUsd':None,'economicAdmission':'HOLD'}],
 'sharedAllocation':{'B':None,'C2':None,'studyOnly':None,'constraint':'When valued, fractions allocate one common cost pool and sum to one. Per-asset views must not be added to the whole study account.'},
 'parentAndStudyCost':'Existing baseline assets retain historical identity; their acquisition/reuse costs are not assumed zero. Prior sunk-study history and this prospective reconstruction are distinct views.'}
write('asset-cost-register.json',assets)
print(json.dumps({'uniqueEvents':len(records),'nonzeroExitEvents':sum(e['exitCode'] not in [None,0] for e in records),'phaseGroups':len(phase),'actualFullCost':'UNKNOWN'}))
