#!/usr/bin/env python3
"""Fictional branch controls; not calibrated economic results or selected seeds."""
import json
from copy import deepcopy
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from economy import run_world,policy_grid


def fixture():
    p=json.loads((ROOT/'protocol.json').read_text())
    p['experiment']['weeks']=24
    for name in p['bundles']:
        p['bundles'][name]={k:0 for k in p['bundles'][name]}
        p['bundles'][name].update(astraInput=1000,requests=1,modelHours=.01,cpuHours=.01)
    p['bundles']['specify']['astraInput']=1000000
    p['company'].update(seedUsd=1000,reserveUsd=100,fixedOperatingUsdWeek=1,taxReserveFraction=0,warrantyReserveFraction=0)
    p['capacity'].update(modelHoursPerAgentWeek=10000,proofContainerHoursPerAgentWeek=10000,tokensPerMinuteTotal=100000000)
    p['buyers'].update(buyers=2,weeklyOpportunityProbability=1,valueUsdLow=100000,valueUsdHigh=100000,annualBudgetUsdLow=1000000,annualBudgetUsdHigh=1000000,qualityThresholdInterval=[0,0],switchingCostUsdInterval=[0,0],deadlineDaysInterval=[100,100],collectionProbability=1,collectionDelayWeeks=0,paymentFeeFraction=0,customerIntakeHours=[0,0,0],postDeliveryDefectDetection=1)
    p['humanReference'].update(hoursByProfile={'reference':1000000,'burdensome':1000000,'efficient':1000000},loadedHourlyProxy=100)
    p['profiles']['reference'].update(resourceMultiplier=1,firstAttemptValidProbability=1,repairProbability=1,validatorSensitivity=1,validatorSpecificity=1,commonErrorProbability=0,constructionSuccessProbability=1,effectStrengthInterval=[.55,.55],buyerTrust=1)
    p['engineDefaults'].update(initialPrecision=1,initialDelivery=1,unsupportedProbability=0,clarificationProbability=0,commonReferenceBlind=0,maxGraphEvidenceAgeWeeks=100)
    p['engineDesign'].update(paidJobCandidateProbability=1,rightsClearedProbability=1,paidCandidateUsefulPrior=1,optionalDeliberateResearchEnabled=False,qualificationContextFractionByProfile={'reference':.05,'burdensome':.05,'efficient':.05},postponeValueFraction=0)
    p['network'].update(admissionCasesProbabilityIfValid=1,commonBlindSpotProbability=0,adaptationSuccessProbability=1,adoptionProbabilityIfGapAndPositiveValue=1,assetLifetimeWeeks=40)
    for a in p['network']['agents']:a.update(initialEquivalentProbability=0,competenceOffset=0)
    p['betaVersions']=p['betaVersions'][:1]
    p['betaVersions'][0]['equivalentByFamily']={k:0 for k in p['skills']}
    p['jobTypes']={'boundedModule':{'share':1,'resourceMultiplier':1}}
    return p


def main():
    start=time.monotonic();p=fixture();policy=dict(id='FICTIONAL',priceUSD=20,pricing='fixed',investment='positiveExpectedNetValue',funding='seed-permitted')
    results=[]
    for scenario in ['reference','alpha-zero','alpha-harm']:
        world=run_world(p,policy,scenario,'reference',19001,'network-alpha');s=world['summary'];cash=world['cash']
        assert cash['funds']['cashMicros']==cash['seedMicros']+cash['funds']['collectedMicros']-cash['funds']['paidMicros']
        assert not world['pendingEvents'] and not world['unspentPublicCostHolds']
        assert s['accepted']==sum(j['usefulAccepted'] for j in world['jobs'])
        assert s['falsePasses']==0
        admitted=[a for a in world['assets'] if a['admittedWeek'] is not None]
        if scenario=='reference':
            assert admitted and s['assetUses']>0, 'Positive fixture must exercise retention and transfer.'
            for record in world['graph']['records']:
                if not record['evidence']:continue
                e=record['evidence'];origin=sum(x['costMicros'] for x in e['costOwnership']['originJobCosts'])
                assert origin>0
                fixed=sum(e['arms']['candidate']['lifecycleCosts'].values())
                assert fixed==sum(sum(x['costs'].values()) for x in e['costOwnership']['retentionEntries']+e['costOwnership']['researchEntries'])
        else: assert not admitted, 'Zero/harm cannot pass positive-net-Alpha admission.'
        results.append(dict(scenario=scenario,checks='PASS',summary=s))
    moving=fixture();moving['engineDefaults']['maxGraphEvidenceAgeWeeks']=4
    next_beta=deepcopy(moving['betaVersions'][0]);next_beta.update(id='FICTIONAL-beta-2',startWeek=12,modelResourceMultiplier=.9)
    moving['betaVersions'].append(next_beta)
    world=run_world(moving,policy,'reference','reference',19002,'network-alpha')
    assert any(b['category']=='freshRevalidation' for b in world['cash']['bills']), 'Fresh evidence must consume paid B resources.'
    assert not world['pendingEvents'] and not world['unspentPublicCostHolds']
    assert any(e['type']=='BETA_UPGRADE' for e in world['events'])
    for record in world['graph']['records']:
        if record['evidence'] and record['evidence']['phase']=='revalidation':assert record['evidence']['arms']['candidate']['lifecycleCosts']['construction']==0
    results.append(dict(scenario='FICTIONAL_MOVING_BETA_AND_EXPIRING_EVIDENCE',checks='PASS',summary=world['summary']))
    record=dict(basis='FICTIONAL_ENGINE_CONTROLS_NOT_CALIBRATED_OUTCOMES',status='PASS',worlds=len(results),results=results,wallSeconds=time.monotonic()-start)
    (ROOT/'validation/engine-controls-result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('basis','status','worlds','wallSeconds')}))


if __name__=='__main__':main()
