// SPDX-License-Identifier: Apache-2.0
// Exact replay of one ALREADY REGISTERED development world. Not new evidence.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {simulate} from '../../model/simulator.mjs';
import {auditRun,auditPaired} from '../../tests/economics_audit.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const read=f=>JSON.parse(fs.readFileSync(path.join(ROOT,f),'utf8'));
const hash=f=>createHash('sha256').update(fs.readFileSync(path.join(ROOT,f))).digest('hex');
const frozen='850e6978a3946f8f9d01dd0c6920b49916e955d12b420a65c1241d3c5cd675f6';
assert.equal(hash('protocol/freeze.json'),frozen);
const F=read('protocol/freeze.json');for(const [f,h] of Object.entries(F.sourceHashes))assert.equal(hash(f),h,`Frozen source ${f}`);
const scale=read('results/scale.json'),selection=read('protocol/selected_policies.json');
const caseId='L144C8Q4',seed=1035001,c=scale.cases.find(x=>x.id===caseId),P=selection.selected.favorable.network.policy;
const runs={},audits={};
for(const [arm,ablation] of [['network','none'],['same-price-beta','beta-only']]){
 const run=simulate(c.C,P,seed,{ablation});run.arm=arm;run.summary.arm=arm;run.case=caseId;
 Object.assign(run.summary,{case:caseId,parameter:c.parameter,value:c.value});
 const original=scale.rows.find(r=>r.case===caseId&&r.seed===seed&&r.arm===arm);
 assert.ok(original);assert.deepEqual(run.summary,original,'Replay must match EVERY originally recorded summary field');
 audits[arm]=auditRun(run);runs[arm]=run;
}
auditPaired(runs.network,runs['same-price-beta']);
const n=runs.network,b=runs['same-price-beta'],h=n.histories;
const sum=a=>a.reduce((x,y)=>x+y,0);
const campaigns=h.campaigns.map(campaign=>{
 const a=n.assets.find(a=>a.id===campaign.id),raw=h.paidCandidates.find(r=>r.id===campaign.forecast.rawCandidateId);
 const source=h.jobs.find(j=>j.id===campaign.originJobId),invoice=h.invoices.find(i=>i.id===campaign.originInvoiceId);
 assert.ok(source.accepted&&invoice.collectedWeek<=campaign.week);assert.equal(campaign.jobCostRechargedCents,0);
 const networkEvents=h.network.filter(e=>e.id===a.id),assessments=h.alphaAssessments.filter(e=>e.assetId===a.id);
 const uses=h.jobs.filter(j=>j.appliedAssetIds.includes(a.id)).map(j=>({id:j.id,classId:j.classId,agent:j.agent,
   offerWeek:j.offerWeek,startWeek:j.startWeek,finishWeek:j.finishWeek,betaVersion:j.betaVersion,
   accepted:j.accepted,useful:j.useful,falsePass:j.falsePass,observedError:j.observedError,newlyFeasible:j.newlyFeasible,
   modeledCollected:h.invoices.some(i=>i.jobId===j.id&&i.collectedWeek!==null),
   priceCents:j.priceCents,humanPriceCents:j.humanPriceCents,costCents:j.costCents,
   workflowCostCents:j.plan.costCents,sameSeedWorkflowWithoutNewlyAcquiredAssetsCents:j.baselineCostCents,
   pairedWorkflowResourceSavingCents:j.baselineCostCents-j.plan.costCents,
   incrementalAccessCostCents:Math.round(n.config.alphaAccessCostPerUse*100),
   providerHumanHours:0,appliedAssetIds:j.appliedAssetIds,
   peer:j.agent!==source.agent,
   matchedBetaJob:b.histories.jobs.find(x=>x.id===j.id)?(()=>{const x=b.histories.jobs.find(x=>x.id===j.id);return {
      accepted:x.accepted,useful:x.useful,finishWeek:x.finishWeek,costCents:x.costCents,priceCents:x.priceCents};})():null}));
 const attributedBills=h.bills.filter(x=>x.lane==='B_retention_reuse'&&x.reference.includes(a.id));
 const grossWorkflowSaving=sum(uses.map(j=>j.pairedWorkflowResourceSavingCents));
 assert.equal(grossWorkflowSaving,a.actualSavingsCents);
 const review=campaign.review.assessment;
 return {asset:a,candidate:raw,sourcePaidJob:{id:source.id,agent:source.agent,classId:source.classId,
    startWeek:source.startWeek,finishWeek:source.finishWeek,accepted:source.accepted,useful:source.useful,
    falsePass:source.falsePass,priceCents:source.priceCents,humanPriceCents:source.humanPriceCents,costCents:source.costCents,
    paidJobComponents:source.paidJobComponents,invoice},
   paidRetention:{sourceKind:campaign.sourceKind,week:campaign.week,readyWeek:campaign.booking.finish,
    jobDevelopmentAlreadyChargedCents:campaign.jobDevelopmentAlreadyChargedCents,jobCostRechargedCents:campaign.jobCostRechargedCents,
    constructionCents:campaign.construction.costCents,assessmentActualCents:campaign.review.costCents,
    completeInitialConstructionAndAssessmentCents:campaign.constructionCents,
    earnedFundedCents:campaign.earnedFundedCents,seedFundedCents:campaign.seedFundedCents,
    capacityBooking:campaign.booking,
    forecast:{...Object.fromEntries(['forecastBenefitCents','forecastGrossBenefitCents','forecastDisplacementCostCents','forecastNetCents',
       'forecastLifeWeeks','forecastEligibleUses','completeCostCents','upkeepCents','revalidationReserveCents','transferReserveCents',
       'publicationReserveCents','availableBeforeCents','earnedAvailableBeforeCents','affordable','capacityAvailable'].map(k=>[k,campaign.forecast[k]]))}},
   observedAssessment:review,allAssessments:assessments,
   independentMechanicalReview:campaign.review.review,
   networkEvents,transfers:h.transfers.filter(t=>t.asset===a.id),
   executedFreshUses:uses,
   attribution:{grossWorkflowResourceSavingCents:grossWorkflowSaving,
     incrementalAccessCostCents:sum(uses.map(j=>j.incrementalAccessCostCents)),
     assetReferencedBExpensesCents:sum(attributedBills.map(x=>x.amountCents)),assetReferencedBills:attributedBills,
     grossWorkflowSavingMinusAccessAndReferencedBExpensesCents:grossWorkflowSaving-sum(uses.map(j=>j.incrementalAccessCostCents))-sum(attributedBills.map(x=>x.amountCents)),
     usefulPeerUseJobs:uses.filter(j=>j.peer&&j.useful).length,
     note:'Resource savings are paired same-seed workflow costs, not causal revenue or complete enterprise gain. Asset-reference bills exclude shared discovery; all B is separately reported. New revenue, queue displacement, pricing, reputation, and lost jobs require whole-policy contrast.'}};
});
const allB=h.bills.filter(x=>x.lane==='B_retention_reuse');
const output={schema:'beyond-beta-selected-development-witness/v1',evidence:'MODELED SELECTED DEVELOPMENT ILLUSTRATION; NOT CONFIRMATION',
 case:caseId,seed,independentWorlds:1,sourceHashes:{freeze:frozen,scale:hash('results/scale.json'),selection:hash('protocol/selected_policies.json')},
 exactReplay:{allRecordedSummaryFieldsEqual:true,bothArmsAudited:true,audits},
 summaries:{network:n.summary,samePriceBeta:b.summary},
 fullSignedEnterpriseDifference:{profitCents:n.summary.profitCents-b.summary.profitCents,
   usefulOutcomes:n.summary.usefulAccepted-b.summary.usefulAccepted,attemptedJobs:n.summary.attemptedJobs-b.summary.attemptedJobs,
   collectionsCents:n.summary.collectionsCents-b.summary.collectionsCents,refundsCents:n.summary.refundsCents-b.summary.refundsCents,
   fullCostsCents:n.summary.costsCents-b.summary.costsCents},
 stages:{paidCandidates:h.paidCandidates.length,rightsCleared:h.paidCandidates.filter(r=>r.rightsCleared).length,
   retentionCampaigns:campaigns.filter(c=>c.paidRetention.sourceKind==='B_paid_job_retention').length,
   actualPaidOriginAdmissions:n.summary.paidOriginAdmissions,productiveAdmissions:n.assets.filter(a=>a.admitted&&a.productive).length,
   falseAdmissions:n.summary.alphaFalseAdmissions,peerUsefulOutcomes:n.summary.peerUsefulOutcomes},
 campaigns,allBCosts:{sumCents:sum(allB.map(x=>x.amountCents)),bills:allB},
 limitations:[
   'Selected after observing the development grid; one independent world. C8Q1 and C8Q4 reuse the same seed and are not two independent replications.',
   'The 36 fresh capacity holdouts have zero admissions and zero peer-use outcomes; this illustration does not replace them.',
   'All jobs, receipts, capability gains and transfers are simulated, with assumed scope, quality, demand and resource effects.',
   'A positive Alpha probe or useful peer-use job is not proof of positive realized complete asset or network return.',
   'Whole-policy contrast includes queue displacement, changes in acquisition/price/reputation, failed work and all costs; do not clip its negative sign.',
   'The optional research/retention policy grid is bounded and lacks a separately optimized B-only enterprise.'
 ]};
for(const [f,x] of [['development_witness.json',output]])fs.writeFileSync(path.join(ROOT,'results/analysis',f),JSON.stringify(x,null,2)+'\n');
for(const [f,h] of Object.entries(F.sourceHashes))assert.equal(hash(f),h,`Frozen source ${f}`);
console.log(JSON.stringify({case:caseId,seed,exactReplay:true,audits,stages:output.stages,difference:output.fullSignedEnterpriseDifference,
 assetSummaries:campaigns.map(c=>({id:c.asset.id,productive:c.asset.productive,admitted:c.asset.admitted,retirement:c.asset.retirementReason,
   source:c.sourcePaidJob,retention:c.paidRetention,gate:{verdict:c.observedAssessment.verdict,lowerDeltaCents:c.observedAssessment.lowerDeltaCents,
   lowerLifetimeNetCents:c.observedAssessment.assessedLowerBoundNetCents,forecastUses:c.observedAssessment.forecastEligibleUses},
   useCount:c.executedFreshUses.length,peerUseful:c.attribution.usefulPeerUseJobs,attribution:{...c.attribution,assetReferencedBills:undefined},
   networkEvents:c.networkEvents,transfers:c.transfers})),allBCostCents:output.allBCosts.sumCents},null,2));
