# SPDX-License-Identifier: Apache-2.0
"""Register an additive A/B diagnostic. Never runs market outcomes or alters prior files."""
import hashlib, json, pathlib

base=pathlib.Path(__file__).resolve().parent
study=base.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(name,data):
    with (base/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')

bridge_path=study/'market/production-followup.json'
audit_path=study/'results/independent-followup-audit/summary.json'
asset_path=study/'protocol/asset-B.json'
bridge,audit,asset=map(read,[bridge_path,audit_path,asset_path])
assert sha(audit_path)==bridge['evidenceClosure']['independentAudit']
assert sha(asset_path)==bridge['arms']['B']['asset']['sha256']
assert bridge['missions']==['F01','F02','F03','F04']
assert bridge['completeAcceptanceEvidence']['status']=='FAIL'
assert audit['marketBridge']['fullFourJobEquivalentAcceptanceABC2'] is False
assert audit['marketBridge']['ABEquivalentAcceptedTaskIds']==bridge['missions']
assert audit['identitiesAccepted'] and audit['workbenchAccepted']
for arm in ['A','B']:
    rows=[r for r in audit['rows'] if r['arm']==arm]
    assert len(rows)==4 and all(r['completeHandoffAccepted'] for r in rows)
    assert bridge['arms'][arm]['acceptedMissionIds']==bridge['missions']
qualification=('Acceptance means complete customer handoff under the frozen independent checker. '
 'An auxiliary Workbench fullTask captured-source reference had one too few parent path components at trial time. '
 'The identical delivery/raw-task.json exists and customer-report references resolve. Any publication navigation aliases '
 'are post-outcome repairs, not successful trial links or semantic reruns; no quality, cost or effort premium is credited.')
production={'schema':'agi-alpha-accepted-ab-diagnostic-production/v1',
 'missions':bridge['missions'],'evidenceSHA256':bridge['evidenceSHA256'],
 'sourceThreeArmBridge':{'path':'market/production-followup.json','sha256':sha(bridge_path),
   'campaignStatus':'GATED_UNEXECUTED','completeAcceptanceStatus':'FAIL',
   'plannedCells':166,'reason':'C2 fails F03 complete acceptance; no common-subset narrowing or zero-runtime-model discount.'},
 'arms':{a:bridge['arms'][a] for a in ['A','B']},'acceptedAsset':bridge['arms']['B']['asset'],
 'independentAcceptance':{'path':'results/independent-followup-audit/summary.json','receiptSHA256':sha(audit_path),
   'verifierSHA256':audit['verifierSha256'],'scope':'complete-useful-deliverable','independentlyVerified':True,
   'identitiesAccepted':audit['identitiesAccepted'],'workbenchAccepted':audit['workbenchAccepted'],
   'rows':[{k:r[k] for k in ['task','arm','inventoryAccepted','completeHandoffAccepted','omittedCalls',
     'spuriousCalls','wrongTargetCalls','materialErrors','resultSha256','deliveryReceiptSha256','independentReviewSha256']}
    for r in audit['rows'] if r['arm'] in ['A','B']]},
 'acceptanceQualification':qualification,
 'excludedComparator':{'label':'C2','acceptedJobs':3,'attemptedJobs':4,'failedMissionIds':['F03'],
   'financialComparisonQualified':False,'reason':'Two out-of-scope NumPy data methods included in SciPy call scope.'},
 'observedCustomerCollectionsCents':0,'actualFinancialAction':False,
 'inference':'Internal acceptance supplies scope qualification and exact asset identity only. No lower complete monetary cost, customer effort, field reliability, capacity or demand effect is identified.'}
write('production-accepted-ab.json',production)

old_protocol=study/'market/transfer-protocol.json';old_scenarios=study/'market/transfer-scenarios.json'
original=read(old_scenarios)
selected=[s for s in original if s['class']=='primary-no-unmeasured-benefit']
assert len(original)==166 and len(selected)==24
scenarios=[]
for s in selected:
    scenarios.append({'id':s['id'].replace('primary-','accepted-ab-',1),
     'basis':s['basis'],'class':'exploratory-accepted-ab-no-benefit','financing':s['financing'],
     'shared':s['shared'],'costs':{a:s['costs'][a] for a in ['A','B']},
     'inheritedScenarioId':s['id'],'mechanism':'Equal assumed complete A/B nominal cost; no demonstrated monetized saving asserted.',
     'assumptions':{**s['assumptions'],'completeNominalAttemptCostCents':500,
       'allNominalComponents':'The common $5 is a hypothetical complete nominal charge including unknown model/curator work; it is not $5 plus a zero-imputed unknown charge.'}})
write('scenarios.json',scenarios)
protocol={'schema':'agi-alpha-accepted-ab-diagnostic-protocol/v1',
 'status':'PROSPECTIVE_BEFORE_AB_DIAGNOSTIC_OUTCOMES_AFTER_FOLLOWUP_PRODUCTION',
 'designation':'Exploratory production-qualified A/B financing and accounting diagnostic',
 'originalThreeArmCampaign':{'status':'GATED_UNEXECUTED','cells':166,
   'protocolPath':'market/transfer-protocol.json','protocolSHA256':sha(old_protocol),
   'scenarioPath':'market/transfer-scenarios.json','scenarioSHA256':sha(old_scenarios),
   'preservation':'All original bytes, failed comparator outcomes and stop rule remain unchanged.'},
 'rationale':'The four accepted A/B handoffs allow a separately labelled two-arm diagnostic. C2 failed complete scope and is excluded as an unqualified investment, not treated as a fair full-cost financial comparator.',
 'production':{'path':'market/accepted-ab-diagnostic/production-accepted-ab.json',
   'sha256':sha(base/'production-accepted-ab.json'),'fullRegisteredMissionIds':bridge['missions'],
   'independentAuditSHA256':sha(audit_path),'acceptedAsset':bridge['arms']['B']['asset'],
   'qualification':qualification},
 'seedFirst':3001,'seedCount':8,'scenarioCount':24,'pairedWorlds':192,'enterpriseHistories':384,
 'pairing':'Identical semantic random draws across A and B for every scenario and seed. Seeds were already prospective in the unexecuted three-arm campaign; no original or new scenario outcomes were selected.',
 'selection':'All 24 originally prospective no-benefit cells: twelve stresses by deterministic/logit choice. No selection on market outcomes, no post-outcome task narrowing.',
 'scenarioSHA256':sha(base/'scenarios.json'),
 'pricing':'Previously declared fixed target $20, with $10 and $5 stress targets. Retain the engine nominal-cost-plus-$1 floor; report actual offer prices separately.',
 'costs':{'basis':'EXPLICIT_CONDITIONAL_ASSUMPTIONS','commonNominalCostCents':500,
   'BCompleteIncrementalConstructionEnvelopeCents':10000,'BMaintenancePerWeekCents':50,
   'maintenanceStressPerWeekCents':2000,'actualCompleteRecurringCents':None,'actualCompleteConstructionCents':None,
   'constructionIncludes':['discovery','all authoring and inference','unsuccessful candidates','evaluation',
    'correction','integration','shared cost allocation'],
   'meaning':'Conditional full-cost envelopes, not estimates, measured totals, bounds or ceilings. Nominal delivery includes routine verification; the retained failure multiplier separately charges failed-delivery correction. All actual incomplete costs remain null.',
   'humanLabor':'Zero asserted A/B minute difference; no agent elapsed-time wage conversion.'},
 'commonInputs':'All quality, buyer effort, integration, switching, trust, demand, capacity and competitor assumptions are shared. Process-stage timings do not modify inherited capacity. No C2 monetary curve, benefit or no-runtime-model discount.',
 'financing':'Finite starting capital and reserves retained. Invest only if the unchanged policy identifies positive incremental repayment and currently collected operating surplus can cover the full exact-B construction envelope. Initial capital and receivables are not earned cash.',
 'sameAsset':'B identity is the exact complete tested manifest, including its frozen source closure and tested B entry point. No replacement or successor is supplied. No forced reconstruction or free initial activation.',
 'prospectivePrediction':'All B investment decisions should refuse: equal unit delivery costs imply zero incremental saving, while full construction, upkeep and possible service interruption are nonnegative. A and B operational cash/profit summaries should match under paired draws.',
 'scientificRole':'This is principally a structural negative control, not an empirical treatment-effect estimate. The zero-benefit financing prediction is algebraic; executing diverse markets checks that the implementation, competition, liquidity and accounting do not manufacture a benefit or finance an unjustified asset. It does not establish that real B savings equal zero.',
 'outcomes':['all paired enterprise histories','accepted and rejected delivery counts','gross invoices versus collections',
   'profit excluding starting capital','reserves and obligations','every investment decision and refusal reason',
   'exact source identity in proposals and investments','B minus A profit','direct repayment and next-asset decision'],
 'analysis':'Retain every cell and seed; report scenario distributions descriptively. Simulated seed variation does not identify real demand or cost uncertainty. No equilibrium, optimality, realized sales, or self-acceleration claim.',
 'stoppingRule':'Run once after root approves a concrete source/input freeze. No scenario tuning, source edits or new task subsets after outcomes. Preserve any unexpected result and investigate only as a separately labelled failure audit.',
 'executionGate':'Freeze must bind runner, pure adapter, independent arithmetic auditor, exact unchanged derived market engine and canonical ledgers, protocol/scenarios, original bridge, independent audit, exact B manifest and every manifest source. Root approval is an internal project freeze, not a new user-permission request.',
 'actualEconomicDecision':'IDENTIFICATION_HOLD','observedCustomerCollectionsCents':0,'actualFinancialAction':False}
write('protocol.json',protocol)
print(json.dumps({'registered':True,'scenarioCount':24,'marketOutcomesExecuted':False,
 'productionSHA256':sha(base/'production-accepted-ab.json'),'protocolSHA256':sha(base/'protocol.json'),
 'scenariosSHA256':sha(base/'scenarios.json')}))
