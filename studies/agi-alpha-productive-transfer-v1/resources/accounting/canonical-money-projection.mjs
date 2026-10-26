// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {planMission} from '../../market/inherited/market/canonical/shadow-ledger.mjs';

const output=new URL('./canonical-money-ledger.json',import.meta.url);
if(existsSync(output))throw Error('Refusing to overwrite canonical accounting snapshot');
const source=new URL('../../market/inherited/market/canonical/shadow-ledger.mjs',import.meta.url);
const projection=planMission({missionId:'transfer-study-total',reference:'Actual study account; incomplete useful-deliverable acceptance and unexposed full charges. Process resource facts are held separately in resource-ledger.jsonl.',
 currency:'USD',acceptance:'unknown',totalCollectedCents:0,priceAssumptionCents:null,
 totalOperatingCostCents:null,operatingCostsComplete:false,capabilityCostCents:null,
 reserveCents:null,obligationCents:null,costBasis:'observed',reinvestmentBps:0,
 humanMinutes:null,humanHourlyCents:null,traditionalMinutes:null});
if(projection.summary.observed.fullCost!==null||projection.summary.observed.operatingMargin!==null||
 projection.summary.observed.availableSurplus!==null||projection.summary.observed.revenue!==0)throw Error('Unknown accounting boundary lost');
writeFileSync(output,JSON.stringify({schema:'agi-alpha-transfer-canonical-accounting/v1',
 canonicalSourceSHA256:createHash('sha256').update(readFileSync(source)).digest('hex'),
 canonicalSourceModified:false,projection,
 boundary:'The canonical API records money only. CPU/wall resources retain physical units in their separate ledger; they are not inserted as dollars or monetized without a tariff. This is one study account, not additive per-asset duplication.'},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({observedRevenueCents:0,fullCost:null,profit:null,availableSurplus:null}));
