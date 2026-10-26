// SPDX-License-Identifier: Apache-2.0
import {writeFileSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';

const stress=[
 {id:'reference'},
 {id:'zero-demand',arrivalProbability:0},
 {id:'low-demand',arrivalProbability:0.10},
 {id:'target-10-dollars',initialPriceCents:1000},
 {id:'target-5-dollars',initialPriceCents:500},
 {id:'strong-cheap-ai',aiInitialPriceCents:500,aiCostCents:100,aiQuality:0.97,aiReviewMinutes:8},
 {id:'cheap-human',humanHourlyCents:2000,humanMarkup:1.02},
 {id:'price-war',competitorStrategy:'undercut',competitorCostReduction:0.75,competitorImitationCostCents:1000},
 {id:'slow-collections',paymentDelayWeeks:13,paymentProbability:0.85},
 {id:'quality-failures',successProbability:0.80,refundProbability:1,churnProbability:0.75},
 {id:'maintenance-shock',assetMaintenanceCentsPerWeek:2000},
 {id:'cash-and-capacity',initialCashCents:30000,paymentDelayWeeks:13,weeklyOverheadCents:1000,enterpriseSlotsPerWeek:1}
];
const out=[];
function make(id,kind,modelStageCents,constructionCents,choice,integration,arrival,shock={}){
 const {id:stressId,...alterations}=shock;
 const common={pricingPolicy:'fixed',initialPriceCents:2000,choiceModel:choice,
  integrationCents:integration,arrivalProbability:arrival,...alterations};
 const upkeep=alterations.assetMaintenanceCentsPerWeek??50;
 const costs=Object.fromEntries(['A','B','C'].map(a=>[a,{
  completeRecurringCostCents:500+(kind==='primary-no-unmeasured-benefit'?0:a==='C'?0:modelStageCents),
  completeConstructionCostCents:a==='A'?0:constructionCents,
  maintenancePerWeekCents:a==='A'?0:upkeep,assumedIntakeMinutes:0
 }]));
 return {id,basis:'EXPLICIT_CONDITIONAL_ASSUMPTIONS',class:kind,financing:'operating-surplus',shared:common,costs,
  mechanism:kind==='primary-no-unmeasured-benefit'?'Common complete nominal cost; no demonstrated monetized saving asserted.':
   'A and B require a source-intake model/curator stage; C has no runtime model stage only after independent full-scope equivalence. The total stage charge is unknown and swept symmetrically for A/B.',
  assumptions:{commonNonmodelNominalCents:500,totalUnknownModelStageCents:kind==='primary-no-unmeasured-benefit'?null:modelStageCents,
   completeIncrementalReconstructionEnvelopeCents:constructionCents,
   envelopeBasis:'Transparent counterfactual values, not measured totals, estimates, empirically established bounds or guaranteed complete cost ceilings.',
   constructionIncludes:['discovery','all authoring and inference','unsuccessful candidates','evaluation','correction','integration','shared-cost allocation'],
   nominalCostBoundary:'Nominal attempt includes routine verification; failed-delivery correction is separately charged by the retained multiplier.',
   actualFinancialAction:false,stress:stressId??null}};
}
for(const s of stress)for(const choice of ['deterministic','logit'])
 out.push(make(`primary-${s.id}-${choice}`,'primary-no-unmeasured-benefit',0,10000,choice,1000,0.25,s));
for(const m of [0,25,100,500,1500])for(const investment of [2500,10000,50000])
 for(const integration of [0,1000])for(const arrival of [0.25,0.5])for(const choice of ['deterministic','logit'])
  out.push(make(`conditional-m${m}-I${investment}-i${integration}-a${arrival}-${choice}`,
   'conditional-model-cost-sensitivity',m,investment,choice,integration,arrival));
for(const s of stress.filter(s=>s.id!=='reference'))for(const choice of ['deterministic','logit'])
 out.push(make(`conditional-stress-${s.id}-${choice}`,'conditional-model-cost-sensitivity',500,10000,choice,0,0.5,s));
if(out.length!==166||new Set(out.map(s=>s.id)).size!==166)throw Error('Unexpected preregistered scenario cardinality');
const path=fileURLToPath(new URL('./transfer-scenarios.json',import.meta.url));
if(existsSync(path))throw Error('Refusing to overwrite previously registered scenarios');
writeFileSync(path,JSON.stringify(out,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({scenarios:out.length,primary:24,conditionalGrid:120,conditionalStress:22,marketOutcomesRun:false}));
