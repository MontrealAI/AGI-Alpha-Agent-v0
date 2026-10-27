"""Post-freeze independent readout of saved results; never runs the simulator."""
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'results/meta'
OUT = ROOT / 'results/analysis'
EXPECTED_FREEZE = '850e6978a3946f8f9d01dd0c6920b49916e955d12b420a65c1241d3c5cd675f6'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text())

def close(a, b):
    assert abs(a-b) <= 1e-8 * max(1, abs(a), abs(b)), (a,b)

def interval(values):
    m = mean(values)
    se = stdev(values) / math.sqrt(len(values))
    return [m-1.96*se, m+1.96*se]

freeze = load(ROOT/'protocol/freeze.json')
assert digest(ROOT/'protocol/freeze.json') == EXPECTED_FREEZE
for name, expected in freeze['sourceHashes'].items():
    assert digest(ROOT/name) == expected, f'Frozen source mismatch: {name}'
protocol = load(ROOT/'protocol/meta_protocol.json')
summary = load(META/'summary.json')
manifest = load(META/'manifest.json')
for name, expected in manifest['files'].items():
    path = META/name
    assert path.stat().st_size == expected['bytes']
    assert digest(path) == expected['sha256'], f'Archive mismatch: {name}'
assert manifest['rootFreezeSha256'] == EXPECTED_FREEZE
assert manifest['protocolSha256'] == digest(ROOT/'protocol/meta_protocol.json')

with gzip.open(META/'campaigns.jsonl.gz', 'rt') as handle:
    records = [json.loads(line) for line in handle if line.strip()]
assert [r['seed'] for r in records] == protocol['seeds']
assert len({r['campaignId'] for r in records}) == len(records) == 256
assert set(protocol['seeds']).isdisjoint(load(ROOT/'protocol/protocol.json')['selection']['seeds'])
assert set(protocol['seeds']).isdisjoint(load(ROOT/'protocol/protocol.json')['confirmation']['seeds'])

names = protocol['arms']
plans_checked = 0
for record in records:
    for name in names:
        row = record['arms'][name]
        plans = [row['plan']] + ([row['review']] if row['review'] else [])
        assert row['costCents'] == sum(p['costCents'] for p in plans)
        assert row['candidates'] == protocol['candidateCount']
        for plan in plans:
            plans_checked += 1
            assert plan['costCents'] == sum(plan['costDetailsCents'].values())
            assert isinstance(plan['costCents'], int)
            tokens = plan['tokens']
            assert tokens['input'] == sum(tokens[k] for k in ['uncachedInput','cachedInput','cacheWrite'])
            assert plan['costCents'] <= plan['reservedCostCents']
            for key, value in plan['resources'].items():
                assert value <= plan['reservedResources'][key] + 1e-7
        assert row['useful'] == bool(row['accepted'] and row['plan']['status']['correct'] and row['plan']['status']['improved'])
        assert row['falseAdmission'] == bool(row['accepted'] and not row['useful'])
    a, z = record['arms']['expert_baseline'], record['arms']['zero_increment_control']
    for field in ['costCents','useful','proposed','accepted','falseAdmission','candidates','resources']:
        assert a[field] == z[field], (record['seed'], field)

arm_readout = {}
fallback_audit = {}
for name in names:
    rows = [r['arms'][name] for r in records]
    s = summary['arms'][name]
    useful = sum(r['useful'] for r in rows)
    accepted = sum(r['accepted'] for r in rows)
    false_pass = sum(r['falseAdmission'] for r in rows)
    fallbacks = [(record['seed'],record['arms'][name]) for record in records
                 if record['arms'][name]['plan']['status']['code']=='invalid_pass'
                 and record['arms'][name]['plan']['diagnostics'].get('selected') is None]
    fallback_passes=sum(r['accepted'] for _,r in fallbacks)
    fallback_audit[name]={'nonInventiveFallbacksMisclassifiedAsProposed':len(fallbacks),
                         'falseAcceptedFallbacks':fallback_passes,
                         'unnecessaryReviewCostCents':sum(r['review']['costCents'] for _,r in fallbacks),
                         'seeds':[seed for seed,_ in fallbacks]}
    close(mean(r['costCents'] for r in rows), s['costCents']['mean'])
    assert useful == s['usefulValidated'] and accepted == s['accepted'] and false_pass == s['falseAdmissions']
    arm_readout[name] = {
        'campaigns':len(rows), 'usefulMethods':useful,
        'locallyAcceptedOutputsIncludingMisclassifiedFallbacks':accepted,
        'locallyAcceptedActualMethodProposals':accepted-fallback_passes,
        'localFalsePasses':false_pass, 'falsePassFractionOfLocalAcceptance':false_pass/accepted if accepted else None,
        'falseAcceptedActualMethodProposals':false_pass-fallback_passes,
        'falseAcceptedNonInventiveFallbacks':fallback_passes,
        'meanVariableCampaignCostUSD':s['costCents']['mean']/100,
        'variableCostPerUsefulMethodUSD':sum(r['costCents'] for r in rows)/useful/100 if useful else None,
        'meanResources':s['meanResources'],
    }

savings = [r['arms']['expert_baseline']['costCents']-r['arms']['retained_family_screen']['costCents'] for r in records]
for record,delta in zip(records,savings):
    adjusted=[]
    for name in ['expert_baseline','retained_family_screen']:
        row=record['arms'][name]
        fallback=row['plan']['status']['code']=='invalid_pass' and row['plan']['diagnostics'].get('selected') is None
        adjusted.append(row['costCents']-(row['review']['costCents'] if fallback else 0))
    assert adjusted[0]-adjusted[1]==delta, 'Endpoint caveat changes a paired cash saving'
quality = [int(r['arms']['retained_family_screen']['useful'])-int(r['arms']['expert_baseline']['useful']) for r in records]
for a,b in zip(interval(savings),summary['pairedVariableCostSavingCents']['meanMC95']): close(a,b)
for a,b in zip(interval(quality),summary['pairedUsefulValidatedDifference']['meanMC95']): close(a,b)
life = summary['assetLifecycle']
C = protocol['config']
limits = {'input':C['inputQuotaWeekly'],'output':C['outputQuotaWeekly'],
          'cpu':C['cpuHoursWeekly'],'validation':C['validatorHoursWeekly'],
          'service':C['concurrency']*C['hoursWeekly']}
resources = summary['arms']['retained_family_screen']['meanResources']
max_campaigns_by_resource = {
    k:max(0, math.floor((life['weeks']*limits[k]-life['resources'][k])/resources[k]))
    for k in limits
}
max_campaigns = min(max_campaigns_by_resource.values())
average_saving = mean(savings)
break_even = math.ceil(life['costCents']/average_saving) if average_saving>0 else None
assert break_even == summary['projectedBreakEvenCampaigns']
recovered_at_capacity = max_campaigns*average_saving
result = {
    'schema':'beyond-beta-independent-meta-readout/v1',
    'analysisStatus':'Post-freeze read-only analysis of all registered saved outcomes; no simulator rerun or source change',
    'rootFreezeSHA256':EXPECTED_FREEZE,
    'metaProtocolSHA256':digest(ROOT/'protocol/meta_protocol.json'),
    'inputs':{name:{'bytes':(META/name).stat().st_size,'sha256':digest(META/name)}
              for name in ['summary.json','campaigns.jsonl.gz','manifest.json']},
    'audit':{'passed':True,'frozenSourceFilesVerified':len(freeze['sourceHashes']),
             'independentCampaigns':len(records),'plansReconciled':plans_checked,
             'exactZeroIncrementPairs':len(records),'registeredSeedsDisjointFromTrainingAndConfirmation':True},
    'arms':arm_readout,
    'postFreezeEndpointCaveat':{
        'frozenSourceAndResultsChanged':False,
        'issue':'The optional meta runner treats invalid_pass with selected=null as a proposed improvement, unlike the correctly bounded main engine and Alpha probe.',
        'classification':fallback_audit,
        'pairedCashSavingUnchangedForEveryCampaignAfterRemovingIdenticalUnneededReviewCharges':True,
        'usefulMethodCountsUnchanged':True,
        'resourceSavingBreakEvenUnchanged':True,
        'mainCommercialAndAlphaAcceptanceUnaffected':True,
        'reporting':'Of the21 local false passes in each arm,16 are invalid actual method proposals and5 are non-inventive fallbacks. Six fallback outputs were unnecessarily reviewed in each arm, costing81.35USD per arm in total. These are not graph admissions.',
        'status':'Post-freeze diagnostic classification of saved traces, not a replacement experiment or a rerun.'
    },
    'paired':{
        'meanVariableSavingUSD':average_saving/100,
        'meanVariableSavingMC95USD':[x/100 for x in interval(savings)],
        'relativeMeanVariableCostReduction':average_saving/summary['arms']['expert_baseline']['costCents']['mean'],
        'campaignsWithPositiveSaving':sum(x>0 for x in savings),
        'campaignsWithNegativeSaving':sum(x<0 for x in savings),
        'campaignsWithNoSaving':sum(x==0 for x in savings),
        'minimumSavingUSD':min(savings)/100,'maximumSavingUSD':max(savings)/100,
        'usefulMethodDifference':sum(quality),'usefulRateDifference':mean(quality),
        'usefulRateDifferenceMC95':interval(quality),
    },
    'completeCostAndCapacity':{
        'fullOptionalResearchLifecycleUSD':life['costCents']/100,
        'fixedMaintenanceAloneUSD':life['fixedMaintenanceAllowanceCents']/100,
        'usefulLifetimeWeeks':life['weeks'],
        'pointBreakEvenFreshCampaigns':break_even,
        'breakEvenUsingLowerMonteCarloMeanSaving':math.ceil(life['costCents']/interval(savings)[0]),
        'maximumCampaignsByNecessaryResourceBound':max_campaigns_by_resource,
        'maximumCampaignsBeforeOrdinaryCustomerWork':max_campaigns,
        'limitingResource':min(max_campaigns_by_resource,key=max_campaigns_by_resource.get),
        'maximumGrossSavingAtThatBoundUSD':recovered_at_capacity/100,
        'netSavingAtThatBoundUSD':(recovered_at_capacity-life['costCents'])/100,
        'maximumAffordableCompleteLifecycleAtThatBoundUSD':recovered_at_capacity/100,
        'fractionOfLifecycleCostRecoverableAtThatBound':recovered_at_capacity/life['costCents'],
        'capacityAtBreakEvenAsFractionOfLifetime':{
            k:(life['resources'][k]+break_even*resources[k])/(life['weeks']*limits[k]) for k in limits},
        'necessaryBoundIsNotASchedulabilityGuarantee':True,
    },
    'interpretation':{
        'modeledVariableEvaluationCostReduction':True,
        'qualityImprovementEstablished':False,
        'lifecycleRecoveryWithinRegisteredCapacityEstablished':False,
        'selfFinancingAccelerationEstablished':False,
        'networkAlphaAdmissionEstablishedByThisExperiment':False,
        'actualFrontierCalls':0,'actualNewAlgorithms':0,'actualCommercialTransactions':0,
        'limits':[
            'Intervals describe Monte Carlo variation inside assumptions, not real frontier performance uncertainty.',
            'The useful retained ordering is conditional; autonomous discovery of that ordering was not observed.',
            'The local falseAdmissions field includes misclassified non-inventive fallbacks:16 invalid method proposals plus5 fallback false passes per arm, not graph Alpha admission.',
            'A projected future campaign count is neither guaranteed demand nor collected revenue.',
            'The resource upper bound allocates capacity solely to this experiment; ordinary service work would reduce it.',
            'The experiment charges optional C research, not retention of learning already paid in customer A.'
        ]
    }
}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'meta_readout.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'audit':result['audit'],'paired':result['paired'],
                  'completeCostAndCapacity':result['completeCostAndCapacity']},indent=2))
