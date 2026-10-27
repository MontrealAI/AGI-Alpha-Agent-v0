// SPDX-License-Identifier: Apache-2.0
// Transparent pre-confirmation amendment: strengthen Beta's pricing-policy comparator.
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
import {SCENARIOS,POLICIES,TRAIN_SEEDS} from './config.mjs';
import {orderedPool} from './pool.mjs';import {mean,summarize} from './statistics.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),sha=x=>createHash('sha256').update(x).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const write=(p,x)=>fs.writeFileSync(path.join(root,p),JSON.stringify(x,null,2)+'\n');
const pricePolicies=[...new Map(POLICIES.map(p=>{const id=`beta-p${p.priceRatio}-s${p.scarcity}-r${p.reserveFactor}`;
 return [id,{...p,id,allowInvestment:false,allowSeparateResearch:false,hurdle:1e9}];})).values()];
const score=rows=>{const x=rows.map(r=>r.discountedAccrualProfitCents).sort((a,b)=>a-b),tail=x.slice(0,Math.max(1,Math.ceil(x.length*.1))),risk=rows.filter(r=>r.insolvent).length/rows.length;
 return {scoreCents:mean(x)+.25*mean(tail),meanDiscountedProfitCents:mean(x),cvar10Cents:mean(tail),insolvencyRate:risk,eligible:risk<=.05};};
function choose(rows){const eligible=rows.filter(r=>r.eligible),pool=eligible.length?eligible:rows.filter(r=>r.insolvencyRate===Math.min(...rows.map(x=>x.insolvencyRate)));
 pool.sort((a,b)=>b.scoreCents-a.scoreCents||a.insolvencyRate-b.insolvencyRate||a.policy.id.localeCompare(b.policy.id));return {...pool[0],constraintSatisfied:eligible.length>0};}
if(process.argv[2]==='register'){
 if(fs.existsSync(path.join(root,'protocol/beta_symmetry_amendment.json')))throw Error('Amendment already registered');
 if(fs.existsSync(path.join(root,'results/confirmation.json'))||fs.existsSync(path.join(root,'results/confirmation_ledgers.jsonl.gz')))throw Error('Confirmation already started');
 fs.copyFileSync(path.join(root,'protocol/selected_policies.json'),path.join(root,'protocol/initial_selected_policies.json'));
 const amendment={schema:'paid-alpha-beta-symmetry-amendment/v1',registeredAt:new Date().toISOString(),
  baseFreezeSHA256:sha(fs.readFileSync(path.join(root,'protocol/freeze.json'))),
  originalTrainingSHA256:sha(fs.readFileSync(path.join(root,'results/training.json'))),
  originalSelectionSHA256:sha(fs.readFileSync(path.join(root,'protocol/initial_selected_policies.json'))),
  amendmentCodeSHA256:sha(fs.readFileSync(fileURLToPath(import.meta.url))),
  reason:'After the development screen and before any confirmation, Beta-only pricing had fewer freedoms. Add the same price, scarcity and reserve choices. Network winners and all numerical model assumptions remain unchanged.',
  betaPolicies:pricePolicies,trainingSeeds:TRAIN_SEEDS,uniqueFinalPolicies:POLICIES.length+pricePolicies.length,
  originalPolicyHistoriesPreserved:true,confirmationSeedsInspected:0,
  selection:'Best symmetric Beta versus unchanged network winner, using the identical downside-adjusted objective and risk rule.',
  noAdditionalAlphaTuning:true};
 write('protocol/beta_symmetry_amendment.json',amendment);console.log(JSON.stringify({amendmentSHA256:sha(fs.readFileSync(path.join(root,'protocol/beta_symmetry_amendment.json'))),betaPolicies:pricePolicies.length}));
}else if(process.argv[2]==='run'){
 const A=read('protocol/beta_symmetry_amendment.json');
 if(sha(fs.readFileSync(fileURLToPath(import.meta.url)))!==A.amendmentCodeSHA256)throw Error('Amendment source changed');
 const F=read('protocol/freeze.json');for(const [p,h]of Object.entries(F.sourceHashes))if(sha(fs.readFileSync(path.join(root,p)))!==h)throw Error(`Frozen source changed ${p}`);
 if(fs.existsSync(path.join(root,'results/beta_symmetry_training.json')))throw Error('Expanded training already exists');
 const scores={},rows=[],initial=read('protocol/initial_selected_policies.json');
 const tasks=SCENARIOS.flatMap(C=>pricePolicies.map(P=>({kind:'train',C,P,seeds:TRAIN_SEEDS})));
 await orderedPool(tasks,async(out,t,i)=>{rows.push(...out.rows);(scores[t.C.id]??=[]).push({policy:t.P,...score(out.rows),outcomes:summarize(out.rows)});
  if(i%15===0)console.log(JSON.stringify({symmetricBetaPolicy:i+1,total:tasks.length}));});
 const selected={};for(const C of SCENARIOS){const beta={...choose(scores[C.id]),selectionKind:'beta'},network=initial.selected[C.id].network;
  const enterprise={...choose([beta,network]),selectionKind:'enterprise'};selected[C.id]={beta,network,enterprise};}
 write('results/beta_symmetry_training.json',{amendmentSHA256:sha(fs.readFileSync(path.join(root,'protocol/beta_symmetry_amendment.json'))),rows,selected});
 write('protocol/selected_policies.json',{schema:'paid-alpha-symmetric-policy-selection/v1',selectedAt:new Date().toISOString(),
  protocolSHA256:A.baseFreezeSHA256,amendmentSHA256:sha(fs.readFileSync(path.join(root,'protocol/beta_symmetry_amendment.json'))),
  initialSelectionSHA256:A.originalSelectionSHA256,trainingSHA256:A.originalTrainingSHA256,
  expandedBetaTrainingSHA256:sha(fs.readFileSync(path.join(root,'results/beta_symmetry_training.json'))),selected,confirmationSeedsInspected:0});
 console.log(JSON.stringify({selected:Object.fromEntries(Object.entries(selected).map(([k,v])=>[k,Object.fromEntries(Object.entries(v).map(([a,b])=>[a,b.policy.id]))])),
  finalSelectionSHA256:sha(fs.readFileSync(path.join(root,'protocol/selected_policies.json')))}));
}else throw Error('Use register then run before confirmation');
