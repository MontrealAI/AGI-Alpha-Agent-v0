// SPDX-License-Identifier: Apache-2.0
// Engineering controls only. Seeds42/43 and deliberately synthetic performance
// parameters are disjoint from every registered scientific seed range.
import assert from 'node:assert/strict';
import {simulate} from './simulator.mjs';
import {BASE} from './config.mjs';
import {auditRun} from '../tests/economics_audit.mjs';
const C={...BASE,id:'synthetic-workflow-integration',weeks:12,runoffWeeks:24,
 prospectsMonthly:20,seedCapital:100000,copyHazardWeekly:0,marketSpread:0,
 buyerValueMedian:300000,buyerValueSpread:0,humanReference:100000,trustMax:0,switchingCost:0,
 initialPerceivedQuality:.98,reputationFeedback:0,humanQuality:.97,
 initialCompletionBelief:.98,humanCompletionBelief:.98,scopeSupport:1,commodityShare:0,
 improvableFraction:1,initialError:0,commonError:0,improvementProbability:1,
 customerErrorDetection:1,lateErrorDetection:1,badDebt:0,concurrency:12,
 inputQuotaWeekly:150000000,outputQuotaWeekly:30000000,cpuHoursWeekly:20000,
 validatorHoursWeekly:5000,earlyAbandonWeeks:1000,collectionDelayWeeks:0,betaUpgradeWeek:6};
const P={id:'synthetic-retain',priceRatio:.4,scarcity:0,hurdle:1.1,reserveFactor:1,
 allowInvestment:false,allowBundles:false,allowMeta:false,allowSharing:false};
const retain=simulate(C,P,42);assert.equal(auditRun(retain).passed,true);
assert.equal(retain.summary.betaVersionChanges,1);assert.ok(retain.histories.jobs.length>0);
assert.equal(retain.summary.actualJobs,0);assert.equal(retain.summary.actualCollectionsUSD,0);
for(const job of retain.histories.jobs){
 assert.equal(job.plan.accounting.betaVersion,job.betaVersion,'Workflow and booked Beta versions agree');
}
const campaign=simulate({...C,id:'synthetic-campaign-integration',weeks:52,
 prospectsMonthly:100,seedCapital:1000000,concurrency:4,inputQuotaWeekly:100000000,
 outputQuotaWeekly:20000000,cpuHoursWeekly:50000,betaUpgradeWeek:26,
 assetConstructionMultiplier:.1,assetMaintenanceWeekly:0,assetProductiveProbability:1,
 assetFalseAdmission:0,assetFalseRejection:0,meanAssetBelief:1,alphaProbeCount:6,
 alphaRevalidationProbeCount:6,alphaSystematicRiskReserveCentsPerUse:0},
 {...P,id:'synthetic-investment-control',allowInvestment:true,allowBundles:true,allowMeta:true,allowSharing:true},43);
assert.equal(auditRun(campaign).passed,true);
assert.ok(campaign.histories.campaigns.length>0,'Synthetic control exercises paid candidate assessment');
for(const row of campaign.histories.campaigns){
 assert.ok(row.review.costCents<=row.review.reservedCostCents);
 assert.ok(row.review.missionChecks.length>0);
 assert.equal(row.review.assessment.evaluationCostCents,row.review.costCents);
}
console.log('Synthetic workflow integration controls passed, including zero-delay collections, Beta change and paid candidate tests.');
