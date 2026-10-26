// SPDX-License-Identifier: Apache-2.0
import {defaultConfig,scenarios} from './market.mjs';
import {writeFileSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const measured={measuredMechanicalWallSeconds:'Maximum arm mean across inherited and fresh joint-tuple measurements; no production capacity qualification.',
  measuredMechanicalCpuSeconds:'Maximum arm mean local CPU across inherited/fresh measurements; no measured dollar tariff.'};
const sourced={hourlyProviderCents:'S01 wage-derived USD65.375/hour rounded; treating it as provider cost is an assumption.',
  hourlyBuyerCents:'S01 and S03 alternative wage/contract anchors; mixture and relevance are assumptions.',
  humanHourlyCents:'S03 worldwide historical Python contracts USD20–40/hour, default30; no exact-job quote.',
  constructionHourlyCents:'S01 wage anchor; engineering hours and authoring bills remain unknown.'};
const ranges={ordinaryFinalizationMinutes:[0,2,10,30],constructionHours:[0.5,4,16,40],adoptionHours:[0.5,4,16,40],
  arrivalProbability:[0,.10,.25],paymentDelayWeeks:[0,2,13],choiceModel:['deterministic','logit'],
  investmentCostBasis:['full-history','adoption-only'],historicalCostTiming:['opening','at-adoption']};
const technical=new Set(['id','weeks','buyers','investmentFunding','stopAfterInsolvency','nextAsset','allMoneyIsAssumed']);
const parameters=Object.fromEntries(Object.entries(defaultConfig).map(([k,v])=>[k,{default:v,
  basis:measured[k]?'measured-within-tested-scope':sourced[k]?'sourced-anchor-with-assumed-transport':technical.has(k)?'declared-design':'scenario-assumption',
  explanation:measured[k]||sourced[k]||'Not identified by existing production or market evidence; conditional input only.',
  range:ranges[k]||null,affects:k.toLowerCase().includes('quality')||k.toLowerCase().includes('trust')?
    'choice, realized outcomes and repeat purchase':'choice, costs, cash, timing, capacity or investment; see MODEL.md and source'}]));
writeFileSync(resolve(root,'protocol/parameter-manifest.json'),JSON.stringify({schema:'agi-alpha-market-parameters/v1',
  warning:'Sensitivity ranges are not empirical bounds; unknown full costs may exceed every displayed value.',parameters,
  stressScenarios:scenarios},null,2)+'\n');
const files=['shadow-ledger.mjs','automated-costs.mjs'].map(path=>({path,
  sha256:createHash('sha256').update(readFileSync(resolve(root,'canonical',path))).digest('hex'),copiedByteIdentically:true,
  source:'Existing AGI ALPHA canonical modules carried through Useful Work v2/commercial-engine-v1 companion'}));
writeFileSync(resolve(root,'canonical/PROVENANCE.json'),JSON.stringify({schema:'agi-alpha-canonical-copy/v1',files,
  modifications:[],authority:'Inert arithmetic only. No transaction or authority API; simulated market history is not observed accounting.'},null,2)+'\n');
