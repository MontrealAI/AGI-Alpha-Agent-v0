// SPDX-License-Identifier: Apache-2.0
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const original = readFileSync(resolve(root, 'upstream/src/market.mjs'), 'utf8');
const sha = value => createHash('sha256').update(value).digest('hex');
const expected = '52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27';
if (sha(original) !== expected) throw Error('Frozen upstream source identity mismatch');
const replacements = [
  ["from '../canonical/shadow-ledger.mjs'", "from './upstream/canonical/shadow-ledger.mjs'"],
  ['  const c=validateConfig(supplied),buyers=Array.from({length:c.buyers},(_,i)=>buyerState(seed,i,c));',
    '  let c=validateConfig(supplied);\n  const baseConfig=c, buyers=Array.from({length:c.buyers},(_,i)=>buyerState(seed,i,c));'],
  ['  const decisions=[],jobs=[],buyerChoices=[],competition=[],prices=[],priceStats={},weeklySales=[],feedback=[];',
    '  const decisions=[],jobs=[],buyerChoices=[],competition=[],prices=[],priceStats={},weeklySales=[],feedback=[];\n' +
    '  const hooks=options.continuationHooks??null;\n  hooks?.initialize({config:baseConfig,firm:f,seed});'],
  ['    if(f.assetPending&&week>=f.assetAvailableWeek&&!f.insolvent){f.assetPending=false;f.assetActive=true;}',
    '    if(f.assetPending&&week>=f.assetAvailableWeek&&!f.insolvent){f.assetPending=false;f.assetActive=true;}\n' +
    '    hooks?.activate({firm:f,week});\n    c=hooks?hooks.effectiveConfig(baseConfig):baseConfig;'],
  ['      invest(f,week,c,seed,arm,priorAccepted,decisions);',
    '      invest(f,week,c,seed,arm,priorAccepted,decisions);\n' +
    '      hooks?.beforeMarket({config:baseConfig,firm:f,week,seed,priorAccepted,expense,payBills,unitCost});\n' +
    '      c=hooks?hooks.effectiveConfig(baseConfig):baseConfig;'],
  ['  if(!enterprise.insolvent&&!enterprise.assetPending&&used.enterprise<c.enterpriseSlotsPerWeek&&',
    '  if(!enterprise.insolvent&&!enterprise.assetPending&&!enterprise.secondAssetPending&&used.enterprise<c.enterpriseSlotsPerWeek&&'],
  ['      if(!priceStats[price])priceStats[price]={seen:0,won:0};',
    '      hooks?.afterProduction({firm:f,week,jobs});\n      if(!priceStats[price])priceStats[price]={seen:0,won:0};'],
  ['  const canonical=canonicalProjection(f,c),profit=canonical.economic.summary.scenario.operatingMargin;',
    '  c=baseConfig;\n  const canonical=canonicalProjection(f,c),profit=canonical.economic.summary.scenario.operatingMargin;'],
  ["    productionEvidence:'Inherited6/6 and new joint-tuple4/4 scoped assessments each arm; no field-reliability estimate inferred.',",
    "    productionEvidence:'Inherited6/6 and new joint-tuple4/4 scoped assessments each arm; no field-reliability estimate inferred.',\n" +
    '    ...(hooks?{secondInvestment:hooks.finalize({firm:f,jobs,config:baseConfig})}:{}),']
];
let patched = original;
for (const [before, after] of replacements) {
  if (patched.split(before).length !== 2) throw Error('Ambiguous or missing continuation patch anchor');
  patched = patched.replace(before, after);
}
writeFileSync(resolve(root, 'continuation-core.mjs'), patched);
writeFileSync(resolve(root, 'core-transformation.json'), JSON.stringify({
  schema: 'agi-alpha-second-investment-core-transformation/v1',
  originalSHA256: expected, resultSHA256: sha(patched),
  method: 'Exact single-occurrence insertions; original source preserved separately.',
  patches: replacements.map(([before, after]) => ({ before, after })),
  neutralContract: 'With continuationHooks absent, the JSON result must equal the frozen core for the same arguments.'
}, null, 2) + '\n');
console.log(JSON.stringify({ originalSHA256: expected, resultSHA256: sha(patched), patches: replacements.length }));
