// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync,existsSync,appendFileSync,createReadStream} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync,createGunzip} from 'node:zlib';
import {createInterface} from 'node:readline';
import {pairedSimulation} from '../reporting/market-expose.mjs';
import {configurationsFor} from './design.mjs';
import {fundingView} from './funding.mjs';

const root=dirname(fileURLToPath(import.meta.url)),market=resolve(root,'..');
const args=process.argv.slice(2),get=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const registeredReplay=args.includes('--replay-registered');
const out=resolve(get('--output',resolve(root,'results-01'))),freezePath=resolve(root,'freeze.json');
const sha=value=>createHash('sha256').update(value).digest('hex');
const assert=(condition,message)=>{if(!condition)throw Error(message);};
const protocol=JSON.parse(readFileSync(resolve(root,'protocol.json'),'utf8'));
const configurations=configurationsFor(protocol),seeds=Array.from({length:protocol.seeds.count},(_,i)=>protocol.seeds.first+i);
assert(seeds.length===24&&seeds[0]===3001&&seeds.at(-1)===3024,'Fresh seed set changed');
if(args.includes('--validate-only')){
  process.stdout.write(JSON.stringify({validated:true,configurations:configurations.length,seeds:seeds.length,
    pairedWorlds:configurations.length*seeds.length,enterpriseRuns:configurations.length*seeds.length*3,
    freshOutcomesExecuted:0})+'\n');
  process.exit(0);
}
assert(existsSync(freezePath),'Reviewed pre-outcome freeze is required');
const freeze=JSON.parse(readFileSync(freezePath,'utf8'));
function verifyFreeze(){
  for(const f of freeze.files)assert(sha(readFileSync(resolve(market,f.path)))===f.sha256,`Frozen extension input changed: ${f.path}`);
}
verifyFreeze();
let originalCompletion=null,replayIterator=null,replayExactMatches=0;
if(registeredReplay){
  const originalDirectory=resolve(root,'results-01');
  assert(existsSync(resolve(originalDirectory,'completion.json')),'Registered replay requires the completed original archive');
  originalCompletion=JSON.parse(readFileSync(resolve(originalDirectory,'completion.json'),'utf8'));
  assert(originalCompletion.completed&&originalCompletion.configurations===128&&originalCompletion.seeds===24&&
    originalCompletion.pairedWorlds===3072&&originalCompletion.freezeSHA256===sha(readFileSync(freezePath)),
    'Original registered completion does not match the frozen design');
  const originalArchive=resolve(originalDirectory,'complete-runs.jsonl.gz');
  assert(sha(readFileSync(originalArchive))===originalCompletion.completeRunsSHA256,'Original registered archive hash mismatch');
  replayIterator=createInterface({input:createReadStream(originalArchive).pipe(createGunzip()),crlfDelay:Infinity})[Symbol.asyncIterator]();
}else assert(Date.now()<=Date.parse(protocol.research_cutoff_utc),'Research cutoff has passed; no fresh outcomes permitted');
assert(!existsSync(out),'Refusing to overwrite any prior extension output');mkdirSync(out,{recursive:true});
writeFileSync(resolve(out,'configurations.json'),JSON.stringify(configurations,null,2)+'\n');
const startWall=process.hrtime.bigint(),startCPU=process.cpuUsage();
function resources(){const cpu=process.cpuUsage(startCPU);return {wallSeconds:Number(process.hrtime.bigint()-startWall)/1e9,
  cpuSeconds:(cpu.user+cpu.system)/1e6};}
function checkBudget(){
  const r=resources();
  if(!registeredReplay){
    assert(r.wallSeconds<=protocol.maximum_execution_wall_seconds,'Declared wall budget reached');
    assert(r.cpuSeconds<=protocol.maximum_execution_cpu_seconds,'Declared CPU budget reached');
    assert(Date.now()<=Date.parse(protocol.research_cutoff_utc),'Declared scientific cutoff reached');
  }
  return r;
}
const stats=values=>{const mean=values.reduce((a,b)=>a+b,0)/values.length,
  sd=Math.sqrt(values.reduce((a,b)=>a+(b-mean)**2,0)/Math.max(1,values.length-1)),sorted=[...values].sort((a,b)=>a-b);
  return {n:values.length,mean,sd,meanInterval95:[mean-1.96*sd/Math.sqrt(values.length),mean+1.96*sd/Math.sqrt(values.length)],
    minimum:sorted[0],median:sorted[Math.floor((sorted.length-1)*.5)],maximum:sorted.at(-1)};};
const priceRange=values=>values.length?{minimumCents:Math.min(...values),maximumCents:Math.max(...values)}:null;
const summaries=[];let completedWorlds=0;
try{
  for(const config of configurations){
    const rows=[];
    for(const seed of seeds){
      checkBudget();
      const paired=pairedSimulation(config,seed),fundingByArm=Object.fromEntries(['A','B','C'].map(arm=>[arm,fundingView(paired.arms[arm])]));
      const capital=paired.arms.B.histories.bills.filter(x=>x.category==='capability').reduce((n,x)=>n+x.amountCents,0);
      paired.successionAvailability={schema:'agi-alpha-fresh-deployment-succession-availability/v1',
        status:'FRESH_SEED_BOUNDED_EXTENSION',costBoundary:'BEFORE_UNPRICED_SECOND_ASSET_DISCOVERY',
        unpricedIncrementalDiscoveryCostCents:null,allInSpendableResourcesIdentified:false,
        qualification:'Reported G is an upper funding ceiling before unknown nonnegative discovery cost D. After attributed search cost, resources are at most max(0,G-D); modeled profit is reduced by D. No default D=0.',
        fundingByArm,secondAssetGate:{status:'NO_GO',recordSHA256:protocol.successor_gate.no_go_record_sha256,
          candidate:null,earmarkedGeneratedFundsCents:0,actualSecondInvestmentCents:0},
        B_oneoffCapabilityIncurredCents:capital,
        B_fixedRealizedPathMaximumOneoffCostBeforeUnpricedDiscoveryCents:paired.causal.B_minus_A_profitCents+capital,
        B_minus_A_terminalFundingCeilingCents:fundingByArm.B.terminal.fundingCeilingBeforeUnpricedDiscoveryCents-
          fundingByArm.A.terminal.fundingCeilingBeforeUnpricedDiscoveryCents};
      const serialized=JSON.stringify(paired);
      if(registeredReplay){
        const archived=await replayIterator.next();
        if(archived.done||archived.value!==serialized){
          writeFileSync(resolve(out,'first-replay-mismatch.json'),JSON.stringify({scenario:config.id,seed,
            archivedSHA256:archived.done?null:sha(archived.value),reproducedSHA256:sha(serialized)},null,2)+'\n');
          throw Error('Registered replay differs from the original paired JSON');
        }
        replayExactMatches++;
      }
      appendFileSync(resolve(out,'complete-runs.jsonl.gz'),gzipSync(serialized+'\n',{level:6,mtime:0}));
      rows.push(paired);completedWorlds++;
      for(const [arm,run]of Object.entries(paired.arms)){
        const funding=fundingByArm[arm];
        appendFileSync(resolve(out,'outcomes.jsonl'),JSON.stringify({scenario:config.id,seed,arm,...run.summary,causal:paired.causal,
          funding:{costBoundary:funding.costBoundary,historicalRDCentsExcluded:funding.historicalRDCentsExcluded,
            terminal:funding.terminal,firstPositiveFundingCeilingWeek:funding.firstPositiveFundingCeilingWeek,
            maximumFundingCeilingBeforeUnpricedDiscoveryCents:funding.maximumFundingCeilingBeforeUnpricedDiscoveryCents,
            maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents:funding.maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents},
          unpricedIncrementalDiscoveryCostCents:null,actualSecondInvestmentCents:0})+'\n');
      }
      checkBudget();
    }
    const arms=Object.fromEntries(['A','B','C'].map(arm=>[arm,{
      profitBeforeUnpricedDiscoveryCents:stats(rows.map(x=>x.arms[arm].summary.profitCents)),
      accepted:stats(rows.map(x=>x.arms[arm].summary.enterpriseAccepted)),
      collectionsCents:stats(rows.map(x=>x.arms[arm].summary.grossCollectionsCents)),
      finalCashCents:stats(rows.map(x=>x.arms[arm].summary.finalCashCents)),
      terminalFundingCeilingBeforeUnpricedDiscoveryCents:stats(rows.map(x=>x.successionAvailability.fundingByArm[arm].terminal.fundingCeilingBeforeUnpricedDiscoveryCents)),
      terminalFullCostRecoveryCeilingBeforeUnpricedDiscoveryCents:stats(rows.map(x=>x.successionAvailability.fundingByArm[arm].terminal.fullCostRecoveryCeilingBeforeUnpricedDiscoveryCents)),
      maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents:stats(rows.map(x=>x.successionAvailability.fundingByArm[arm].maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents)),
      originalStrictTerminalEarnedCents:stats(rows.map(x=>x.successionAvailability.fundingByArm[arm].terminal.originalStrictEarnedAvailableCents)),
      investmentRate:rows.filter(x=>x.arms[arm].summary.investmentWeek!==null).length/rows.length,
      failedInvestmentRate:rows.filter(x=>x.arms[arm].summary.failedInvestment).length/rows.length,
      insolvencyRate:rows.filter(x=>x.arms[arm].summary.insolvent).length/rows.length,
      positiveModeledProfitBeforeUnpricedDiscoveryRate:rows.filter(x=>x.arms[arm].summary.profitCents>0&&
        !x.arms[arm].summary.insolvent&&x.arms[arm].summary.obligationsCents===0).length/rows.length,
      positiveTerminalFundingCeilingRate:rows.filter(x=>x.successionAvailability.fundingByArm[arm].terminal.fundingCeilingBeforeUnpricedDiscoveryCents>0).length/rows.length,
      positiveDuringServiceFundingCeilingRate:rows.filter(x=>x.successionAvailability.fundingByArm[arm].maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents>0).length/rows.length,
      directRepaymentRate:rows.filter(x=>x.arms[arm].summary.directCostPayback).length/rows.length,
      computedWeeklyQuoteRange:priceRange(rows.flatMap(x=>x.arms[arm].histories.prices.map(p=>p.enterpriseCents))),
      actuallyOfferedQuoteRange:priceRange(rows.flatMap(x=>x.arms[arm].histories.prices.filter(p=>p.offersSeen>0).map(p=>p.enterpriseCents))),
      acceptedDeliveryPriceRange:priceRange(rows.flatMap(x=>x.arms[arm].histories.jobs.filter(p=>p.provider==='enterprise'&&p.accepted).map(p=>p.priceCents)))
    }]));
    summaries.push({scenario:config.id,config,arms,costBoundary:'BEFORE_UNPRICED_SECOND_ASSET_DISCOVERY',
      causalBeforeUnpricedDiscovery:Object.fromEntries(['B_minus_A_profitCents','C_minus_A_profitCents','B_minus_C_profitCents'].map(k=>[k,stats(rows.map(x=>x.causal[k]))])),
      incrementalTerminalFundingCeilingCents:stats(rows.map(x=>x.successionAvailability.B_minus_A_terminalFundingCeilingCents)),
      pathFixedMaximumOneoffCostBeforeUnpricedDiscoveryCents:stats(rows.map(x=>x.successionAvailability.B_fixedRealizedPathMaximumOneoffCostBeforeUnpricedDiscoveryCents)),
      B_C_exact_ties:rows.every(x=>x.causal.B_C_behaviorallyIdentical),
      B_positive_incremental_rate:rows.filter(x=>x.causal.B_minus_A_profitCents>0).length/rows.length,
      B_negative_incremental_rate:rows.filter(x=>x.causal.B_minus_A_profitCents<0).length/rows.length,
      actualSecondInvestments:0});
    process.stdout.write(JSON.stringify({scenario:config.id,finished:rows.length,totalCompletedWorlds:completedWorlds,...resources()})+'\n');
  }
  if(registeredReplay)assert((await replayIterator.next()).done,'Original archive has unexpected extra worlds');
  checkBudget();verifyFreeze();
  writeFileSync(resolve(out,'summary.json'),JSON.stringify({schema:'agi-alpha-bounded-deployment-robustness-summary/v1',
    status:'FRESH_SEED_USER_AUTHORIZED_EXTENSION',freezeSHA256:sha(readFileSync(freezePath)),seeds,scenarios:summaries,
    costBoundary:'BEFORE_UNPRICED_SECOND_ASSET_DISCOVERY',unpricedIncrementalDiscoveryCostCents:null,
    qualification:'G and profit are conditional ceilings before unknown incremental discovery cost D; there is no all-in funding identification, no second asset, no successor investment and no real collection.',
    allPreviousCampaignsPreserved:true,actualSecondInvestments:0,
    intervals:'Unadjusted conditional Monte Carlo mean intervals across24 fresh seeds per condition; exclude unidentified parameter and authoring-cost uncertainty.'},null,2)+'\n');
  const completeRunsSHA256=sha(readFileSync(resolve(out,'complete-runs.jsonl.gz'))),
    summarySHA256=sha(readFileSync(resolve(out,'summary.json'))),measured=checkBudget();
  if(registeredReplay)assert(completeRunsSHA256===originalCompletion.completeRunsSHA256&&
    summarySHA256===originalCompletion.summarySHA256,'Registered aggregate archive/summary identity mismatch');
  writeFileSync(resolve(out,'completion.json'),JSON.stringify({completed:true,configurations:configurations.length,seeds:seeds.length,
    mode:registeredReplay?'REGISTERED_REPLAY_ZERO_NEW_EVIDENCE':'ORIGINAL_BOUNDED_RESEARCH',
    freezeSHA256:sha(readFileSync(freezePath)),replayExactMatches,newEconomicScenarios:registeredReplay?0:configurations.length,
    pairedWorlds:completedWorlds,enterpriseRuns:completedWorlds*3,competitorFirmAccounts:completedWorlds*6,
    completeRunsSHA256,summarySHA256,
    originalCoreSHA256:sha(readFileSync(resolve(market,'src/market.mjs'))),
    outputOnlyExposureSHA256:sha(readFileSync(resolve(market,'reporting/market-expose.mjs'))),
    resources:measured,budgetsSatisfied:registeredReplay?null:true,cutoffSatisfied:registeredReplay?null:true,actualSecondInvestments:0,
    unpricedIncrementalDiscoveryCostCents:null,observedCollectionsCents:0,actualTransactions:0},null,2)+'\n');
}catch(error){
  writeFileSync(resolve(out,'failure.json'),JSON.stringify({completed:false,message:error.message,stack:error.stack,
    completedWorlds,completedConfigurations:summaries.length,resources:resources(),utc:new Date().toISOString(),
    partialOutputsPreserved:true,actualSecondInvestments:0},null,2)+'\n');
  throw error;
}
