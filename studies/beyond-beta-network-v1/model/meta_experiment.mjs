// SPDX-License-Identifier: Apache-2.0
// Prospective, simulated independent invention-campaign mechanism experiment.
// `register` writes assumptions/seeds/hashes only. `run` requires the root freeze.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {BASE,ASSETS} from './config.mjs';
import {DEFAULT_WORKFLOW_CONFIG,planJob,planCampaignReview,planConstruction,planAuxiliary} from './workflow.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const PROTOCOL=path.join(ROOT,'protocol/meta_protocol.json');
const sha=x=>createHash('sha256').update(x).digest('hex');
const cents=x=>Math.round(x*100);
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
const sum=a=>a.reduce((s,x)=>s+x,0);
const quantile=(a,p)=>{const b=[...a].sort((x,y)=>x-y);return b.length?b[Math.floor((b.length-1)*p)]:null;};
const rngFor=seed=>label=>{const b=createHash('sha256').update(`${seed}|${label}`).digest();return b.readUInt32BE(0)/4294967296;};
const MC_SEEDS=Array.from({length:256},(_,i)=>1040000+i);
const SOURCE_FILES=['model/config.mjs','model/workflow.mjs','model/alpha_gate.mjs','model/alpha_probe.mjs',
 'model/meta_experiment.mjs','evidence/frontier_model_recheck.json'];

function sourceHashes(){return Object.fromEntries(SOURCE_FILES.map(f=>[f,sha(fs.readFileSync(path.join(ROOT,f)))]));}
function distribution(a){
  const m=mean(a),variance=a.length>1?sum(a.map(x=>(x-m)**2))/(a.length-1):0,se=Math.sqrt(variance/a.length);
  return {n:a.length,mean:m,median:quantile(a,.5),p05:quantile(a,.05),p95:quantile(a,.95),min:Math.min(...a),max:Math.max(...a),meanMC95:[m-1.96*se,m+1.96*se]};
}
function wilson(k,n){const z=1.959963984540054,p=k/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [c-h,c+h];}
function aggregateResource(plans){
  return {input:sum(plans.map(p=>p.tokens.input)),output:sum(plans.map(p=>p.tokens.output)),
    cpu:sum(plans.map(p=>p.resources.cpuHours)),validation:sum(plans.map(p=>p.resources.validatorCpuHours)),
    service:sum(plans.map(p=>p.resources.serviceHours))};
}

export function buildMetaProtocol(){
  const config={...DEFAULT_WORKFLOW_CONFIG,...BASE,betaResourceFactor:1,betaBundleAbsorption:0,betaExperimentAbsorption:0};
  return {schema:'beyond-beta-meta-protocol/v1',registeredAt:new Date().toISOString(),evidence:'ASSUMED_OR_EXPLORED',
    scientificStatus:'Prospective modeled mechanism experiment; no scientific outcomes produced by registration',
    purpose:'Whether a retained family-specific experiment ordering reduces the complete cost of later independent capability construction at matched quality, beyond ordinary delivery reuse',
    seeds:MC_SEEDS,candidateCount:96,config,assetWorkUnits:ASSETS.experiment.researchWorkUnits,
    sourceCostLayer:'C_optional_research_without_prepaid_customer_origin',
    arms:['expert_baseline','retained_family_screen','zero_increment_control'],amortizationCampaignCounts:[1,4,16,64,256],
    sourceHashes:sourceHashes(),
    methods:{
      baseline:'Same current Beta: Astra Pro max, Terra max, known solver access, candidate draws and final validator. Ordinary mechanical screening is already available with sensitivity0.65 by default.',
      intervention:'Only a retained family-specific screen adds the declared familyScreenIncrement to sensitivity. Same default false-positive rate. No generic expert-use or quality multiplier.',
      campaign:'A fresh target and96 freshly generated candidate traces, maxRetries0; never descendant customer jobs. Candidate count and all generation costs remain identical across arms.',
      uncertainty:'Campaign-level shared interpretation errors correlate producer and final review. Mechanical defects, informative checks and improvement opportunities use stable keyed draws.',
      opportunity:'The latent opportunity variable means discoverability within the modeled bounded campaign; it is not a theorem that no human or stronger search can improve the problem.',
      finalReview:'A proposed improvement receives up to96 disjoint falsification cases. Early rejection consumes its actual review work; failures remain in the cost denominator.',
      assetCost:'Full optional-C tariff-backed construction, one automated investment evaluation, final asset review, maintenance across the registered useful lifetime and scheduled revalidation. No prepaid customer A is available to deduct; cheap B retention work units are not substituted for this independent research campaign. No unallocated allowance or contingency expense.',
      amortization:'Expected-workload projections from the completed fresh-campaign sample, not actual cash receipts or256 invented assets. Common fixed enterprise costs cancel in this incremental mechanism comparison.',
      null:'Retained flag with familyScreenIncrement0 must exactly reproduce baseline cost, resource use and outcome for every paired campaign, before adding the unrecovered asset cost. Full Beta experiment absorption is an additional synthetic exact-null control.',
      fullCostEndpoint:'Complete campaign cost per useful validated new method, with fixed asset lifecycle cost allocated over the stated future campaign count. Also report success, false admissions, missed proposals, latency and resource use.',
      capacity:'Amortization rows report a necessary resource-flow feasibility bound within the fixed useful lifetime, including construction and maintenance. Passing that bound does not prove schedulability or demand.',
      networkBoundary:'A local mechanism experiment conditional on a useful retained ordering, not a network-admission event. Its lifecycle includes local construction/evaluation/upkeep; actual network Alpha assessment/distribution/transfer are evaluated in the main finite ledger and are not claimed paid here.',
      betaPath:'Initial public Beta configuration. Future upgrade absorption is tested in the main paired network simulation; this experiment cannot attribute shared future model improvements to retained Alpha.',
      claimLimit:'Conditional modeled test-ordering value only. No live model call, actual autonomous invention, admitted graph asset, deployed validator, buyer purchase or change in authority occurs.',
    }};
}

export function evaluateFreshCampaign(config,seed,candidateCount=96){
  const rng=rngFor(seed),job={id:`independent-campaign-${seed}`,complexity:1,scopeSupported:true,candidateCount};
  const opportunity=rng('independent-opportunity')<(config.improvableFraction??0.65);
  const C={...config,maxRetries:0,improvementProbability:opportunity?config.improvementProbability:0};
  const arms={};
  for(const name of ['expert_baseline','retained_family_screen','zero_increment_control']){
    const assets={experiment:name!=='expert_baseline'};
    const c=name==='zero_increment_control'?{...C,familyScreenIncrement:0}:C;
    const plan=planJob(c,job,assets,rng);
    const proposed=['improved','invalid_pass'].includes(plan.status.code);
    let review=null;
    if(proposed){
      // The same mistaken interpretation can affect all model roles and review.
      const reviewRng=label=>label==='review-common-blindspot'?rng('common-specification-blindspot'):rng(`final-review-${label}`);
      review=planCampaignReview(c,{id:`${job.id}-final-review`,valid:plan.status.correct&&plan.status.improved,trials:96},{},reviewRng);
    }
    const accepted=Boolean(review?.status.accepted);
    const useful=accepted&&plan.status.correct&&plan.status.improved;
    const allPlans=[plan,...(review?[review]:[])];
    arms[name]={costCents:sum(allPlans.map(p=>p.costCents)),useful,proposed,accepted,
      falseAdmission:accepted&&!useful,resources:aggregateResource(allPlans),
      candidates:plan.diagnostics.candidates,observedCheapRejections:plan.diagnostics.observedCheapRejections,
      observedPostScreenMechanicalFailures:plan.diagnostics.observedPostScreenMechanicalFailures,
      plan,review};
  }
  const b=arms.expert_baseline,z=arms.zero_increment_control;
  for(const k of ['costCents','useful','proposed','accepted','falseAdmission','candidates'])if(b[k]!==z[k])throw Error(`Zero-increment mismatch ${seed}:${k}`);
  if(JSON.stringify(b.resources)!==JSON.stringify(z.resources))throw Error(`Zero-increment resource mismatch ${seed}`);
  return {seed,campaignId:job.id,opportunity,arms};
}

function lifecycle(config,assetWorkUnits){
  const construction=planConstruction(config,{workUnits:assetWorkUnits,keys:['experiment']});
  const evaluation=planAuxiliary(config,'investment_evaluation');
  // The asset's conditional full passing review is charged at actual tariffs;
  // its larger blind capacity reservation remains separate from expenditure.
  const review=planCampaignReview(config,{id:'experiment-asset-admission',valid:true,trials:96},{},()=>0.99);
  const reviewCostCents=review.costCents;
  const maintenance=planAuxiliary(config,'maintenance'),revalidation=planAuxiliary(config,'revalidation');
  const weeks=config.assetLifetimeWeeks,revalidations=Math.max(0,Math.floor((weeks-1)/config.assetRevalidationWeeks));
  const fixedMaintenanceCents=cents(config.assetMaintenanceWeekly)*weeks;
  const costCents=construction.costCents+evaluation.costCents+reviewCostCents+weeks*maintenance.costCents+revalidations*revalidation.costCents+fixedMaintenanceCents;
  const resources=aggregateResource([construction,evaluation,{...review,tokens:review.reservedTokens,resources:review.reservedResources}]);
  const m=aggregateResource([maintenance]),r=aggregateResource([revalidation]);
  for(const k of Object.keys(resources))resources[k]+=weeks*m[k]+revalidations*r[k];
  return {costCents,construction,evaluation,reviewCostCents,reviewReservedCostCents:review.reservedCostCents,maintenancePlan:maintenance,revalidationPlan:revalidation,
    fixedMaintenanceAllowanceCents:fixedMaintenanceCents,weeks,revalidations,resources,
    conditionalAssetAssumption:'A scope-matched useful retained test ordering is available after the fully charged construction campaign; its autonomous discovery is not observed. Zero-increment arm tests no added information.'};
}

export function summarizeMeta(protocol,records){
  const C=protocol.config,life=lifecycle(C,protocol.assetWorkUnits),names=protocol.arms;
  const arms=Object.fromEntries(names.map(name=>{
    const rows=records.map(r=>r.arms[name]),useful=sum(rows.map(r=>Number(r.useful)));
    return [name,{campaigns:rows.length,usefulValidated:useful,usefulRate:useful/rows.length,usefulRateWilson95:wilson(useful,rows.length),
      accepted:sum(rows.map(r=>Number(r.accepted))),falseAdmissions:sum(rows.map(r=>Number(r.falseAdmission))),
      proposed:sum(rows.map(r=>Number(r.proposed))),costCents:distribution(rows.map(r=>r.costCents)),
      variableCostPerUsefulCents:useful?sum(rows.map(r=>r.costCents))/useful:null,
      meanResources:Object.fromEntries(Object.keys(life.resources).map(k=>[k,mean(rows.map(r=>r.resources[k]))]))}];
  }));
  const savings=records.map(r=>r.arms.expert_baseline.costCents-r.arms.retained_family_screen.costCents);
  const qualityDiff=records.map(r=>Number(r.arms.retained_family_screen.useful)-Number(r.arms.expert_baseline.useful));
  const limits={input:C.inputQuotaWeekly,output:C.outputQuotaWeekly,cpu:C.cpuHoursWeekly,validation:C.validatorHoursWeekly,service:C.concurrency*C.hoursWeekly};
  const amortization=protocol.amortizationCampaignCounts.map(n=>{
    const a=arms.retained_family_screen,b=arms.expert_baseline;
    const demand={};for(const k of Object.keys(limits))demand[k]=(life.resources[k]+n*a.meanResources[k])/(life.weeks*limits[k]);
    const expectedUseful=n*a.usefulRate,total=a.costCents.mean*n+life.costCents;
    return {futureCampaigns:n,expectedUsefulValidated:expectedUseful,
      baselineCompleteCostPerUsefulCents:b.usefulRate?b.costCents.mean/b.usefulRate:null,
      retainedCompleteCostPerUsefulCents:expectedUseful?total/expectedUseful:null,
      zeroIncrementCompleteCostPerUsefulCents:b.usefulRate?(b.costCents.mean*n+life.costCents)/(n*b.usefulRate):null,
      fullAssetLifecycleCostCents:life.costCents,expectedVariableSavingCents:mean(savings)*n,
      expectedNetResourceSavingCents:mean(savings)*n-life.costCents,
      maximumFractionOfLifetimeCapacity:demand,necessaryCapacityBoundSatisfied:Object.values(demand).every(x=>x<=1),
      interpretation:'Projection over independent future construction campaigns; no revenue, actual purchase, or guaranteed campaign demand'};
  });
  const costSaving=distribution(savings),quality=distribution(qualityDiff);
  return {schema:'beyond-beta-meta-results/v1',completedAt:new Date().toISOString(),evidence:'ASSUMED_OR_EXPLORED',
    campaigns:records.length,candidatesPerCampaign:protocol.candidateCount,seeds:protocol.seeds,arms,
    pairedVariableCostSavingCents:costSaving,pairedUsefulValidatedDifference:quality,
    exactZeroIncrementControlPassed:true,assetLifecycle:life,amortization,
    projectedBreakEvenCampaigns:costSaving.mean>0?Math.ceil(life.costCents/costSaving.mean):null,
    interpretation:{
      conditionalVariableCostReduction:costSaving.meanMC95[0]>0,
      zeroIncrementNull:true,
      selfFinancingNotEstablishedByThisExperiment:true,
      economicMeaning:'A cheaper future campaign is different from an investment that repays its full lifecycle cost. Use the amortization and capacity rows; the macro cash ledger tests financing separately.',
      intervals:'Monte Carlo uncertainty within the assumed model; excludes uncertainty about real frontier task performance, discovery rates or buyer demand.',
      actualModelCalls:0,actualInventions:0,actualTransactions:0,
    }};
}

function register(){
  if(fs.existsSync(path.join(ROOT,'protocol/freeze.json')))throw Error('Root freeze already exists; do not overwrite a prospective protocol');
  const protocol=buildMetaProtocol(),bytes=Buffer.from(JSON.stringify(protocol,null,2)+'\n');
  fs.mkdirSync(path.dirname(PROTOCOL),{recursive:true});fs.writeFileSync(PROTOCOL,bytes);
  console.log(JSON.stringify({registered:PROTOCOL,sha256:sha(bytes),campaignCount:protocol.seeds.length,candidateCount:protocol.candidateCount,seedRange:[protocol.seeds[0],protocol.seeds.at(-1)],scientificRuns:0}));
}
function run(args){
  const expected=args[args.indexOf('--freeze-sha')+1],freezeFile=path.join(ROOT,'protocol/freeze.json');
  if(!args.includes('--freeze-sha')||!fs.existsSync(freezeFile)||sha(fs.readFileSync(freezeFile))!==expected)throw Error('A matching root freeze SHA is required before scientific execution');
  const bytes=fs.readFileSync(PROTOCOL),protocol=JSON.parse(bytes),current=sourceHashes();
  for(const [f,h]of Object.entries(protocol.sourceHashes))if(current[f]!==h)throw Error(`Source changed after meta registration: ${f}`);
  const out=path.join(ROOT,'results/meta');if(fs.existsSync(path.join(out,'summary.json')))throw Error('Existing meta results preserved; refusing overwrite');
  fs.mkdirSync(out,{recursive:true});
  fs.writeFileSync(path.join(out,'run-start.json'),JSON.stringify({startedAt:new Date().toISOString(),protocolSha256:sha(bytes),rootFreezeSha256:expected,seeds:protocol.seeds},null,2)+'\n');
  const records=protocol.seeds.map(seed=>evaluateFreshCampaign(protocol.config,seed,protocol.candidateCount));
  const result=summarizeMeta(protocol,records),raw=Buffer.from(records.map(r=>JSON.stringify(r)).join('\n')+'\n'),gz=gzipSync(raw);
  fs.writeFileSync(path.join(out,'campaigns.jsonl.gz'),gz);
  fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify(result,null,2)+'\n');
  fs.writeFileSync(path.join(out,'campaigns.csv'),['seed,baseline_cost_cents,asset_cost_cents,baseline_useful,asset_useful,baseline_false_admission,asset_false_admission',
    ...records.map(r=>[r.seed,r.arms.expert_baseline.costCents,r.arms.retained_family_screen.costCents,Number(r.arms.expert_baseline.useful),Number(r.arms.retained_family_screen.useful),Number(r.arms.expert_baseline.falseAdmission),Number(r.arms.retained_family_screen.falseAdmission)].join(','))].join('\n')+'\n');
  const files=['run-start.json','campaigns.jsonl.gz','summary.json','campaigns.csv'];
  const manifest={completedAt:new Date().toISOString(),protocolSha256:sha(bytes),rootFreezeSha256:expected,campaigns:records.length,
    rawArchiveUncompressedBytes:raw.length,files:Object.fromEntries(files.map(f=>{const b=fs.readFileSync(path.join(out,f));return [f,{bytes:b.length,sha256:sha(b)}];}))};
  fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
  console.log(JSON.stringify({complete:true,campaigns:records.length,summary:path.join(out,'summary.json'),manifest:path.join(out,'manifest.json')}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const [command,...args]=process.argv.slice(2);
  if(command==='register')register();else if(command==='run')run(args);else throw Error('Use register, or run --freeze-sha <sha256>; registration never runs outcomes');
}
