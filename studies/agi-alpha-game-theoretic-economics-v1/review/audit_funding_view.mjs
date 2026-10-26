// SPDX-License-Identifier: Apache-2.0
// Independent synthetic funding checks. No market or fresh production is executed.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {fundingView,OPENING_RD_REFERENCE} from '../market/deployment-robustness/funding.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const out=process.argv[2]??resolve(root,'review/prefreeze-funding-view-audit.json');
if(existsSync(out))throw Error('Refusing to overwrite an earlier audit receipt.');
const tests=[],asset='a'.repeat(64);
function test(name,fn){try{fn();tests.push({name,passed:true});}catch(e){tests.push({name,passed:false,error:e.message});}}
function run({reserve=500,bills=[],cash=[],balances}){
  const result={arm:'B',seed:0,basis:'SYNTHETIC_CONTROL_ONLY',config:{id:'independent-funded-budget-control',weeks:3,
    initialCashCents:1000,reserveCents:reserve,investmentCostBasis:'full-history',historicalCostTiming:'opening'},
    histories:{bills,cash,balances:balances.map(x=>({week:x[0],cashCents:x[1],obligationsCents:x[2],
      cumulativeCollectionsCents:x[3],accruedCostsCents:x[4],reserveCents:reserve,
      earnedAvailableCents:Math.min(x[1]-x[2]-reserve,x[3]-x[4]-reserve)}))}};
  // These fixtures satisfy real cash conservation; liquidity is not fabricated independently.
  for(const b of result.histories.balances){
    const paid=bills.filter(x=>x.paid&&x.paidWeek<=b.week).reduce((n,x)=>n+x.amountCents,0);
    assert.equal(b.cashCents,1000+b.cumulativeCollectionsCents-paid);
    assert.equal(b.obligationsCents,b.accruedCostsCents-paid);
  }
  return result;
}
const history={id:'historical',category:'capability',reference:OPENING_RD_REFERENCE,week:0,dueWeek:0,amountCents:900,paid:true,paidWeek:0};
const paidHistory={week:0,type:'expense_payment',reference:'historical',amountCents:-900,cashAfterCents:100};
const receipt={week:0,type:'simulated_collection',reference:'synthetic-invoice',amountCents:500,cashAfterCents:600};
const earmark={id:'synthetic-commitment',createdWeek:0,amountCents:80,assetSHA256:asset,
  evidenceRef:'SYNTHETIC_TEST_NO_REAL_ASSET_OR_PURCHASE',billIds:['second-bill']};
const ceiling=v=>v.terminal.fundingCeilingBeforeUnpricedDiscoveryCents;
test('Finite seed alone cannot become generated funds',()=>assert.equal(ceiling(fundingView(run({balances:[[0,1000,0,0,0]]}))),0));
test('A physically consistent liquidity-bound earmark leaves 20, not 100',()=>{
  const r=run({bills:[history],cash:[paidHistory,receipt],balances:[[0,600,0,500,900]]});
  assert.equal(ceiling(fundingView(r)),100);
  assert.equal(ceiling(fundingView(r,{earmarks:[earmark]})),20);
});
test('Reservation, liability accrual and payment preserve the same available amount',()=>{
  const bill={id:'second-bill',week:1,dueWeek:2,amountCents:80,category:'capability',reference:asset,paid:true,paidWeek:2};
  const r=run({bills:[history,bill],cash:[paidHistory,receipt,{week:2,type:'expense_payment',reference:'second-bill',amountCents:-80,cashAfterCents:520}],
    balances:[[0,600,0,500,900],[1,600,80,500,980],[2,520,0,500,980]]});
  assert.deepEqual(fundingView(r,{earmarks:[earmark]}).weekly.map(x=>x.fundingCeilingBeforeUnpricedDiscoveryCents),[20,20,20]);
});
test('Historical addback requires a paid opening liability',()=>{
  const r=run({bills:[{...history,paid:false,paidWeek:undefined}],cash:[{...receipt,cashAfterCents:1500}],balances:[[0,1500,900,500,900]]});
  assert.equal(fundingView(r).historicalRDCentsExcluded,0);assert.equal(ceiling(fundingView(r)),0);
});
test('An opening historical bill paid after receipts is not certified seed provenance',()=>{
  const r=run({bills:[history],cash:[{...receipt,cashAfterCents:1500},{...paidHistory,cashAfterCents:600}],balances:[[0,600,0,500,900]]});
  assert.equal(fundingView(r).historicalRDCentsExcluded,0);assert.equal(ceiling(fundingView(r)),0);
});
test('Setup and first adoption remain recovered prospective costs',()=>{
  const bills=[{id:'setup',category:'business',reference:'setup',week:0,amountCents:100,paid:true,paidWeek:0},
    {id:'first-adoption',category:'capability',reference:asset,week:0,amountCents:80,paid:true,paidWeek:0}];
  const r=run({reserve:200,bills,balances:[[0,1320,0,500,180]]});
  assert.equal(fundingView(r).historicalRDCentsExcluded,0);assert.equal(ceiling(fundingView(r)),320);
});
test('Receipts after service cannot fund earlier in-horizon construction',()=>{
  const r=run({balances:[[0,1000,0,0,0],[1,1000,0,0,0],[2,1000,0,0,0],[3,1200,0,200,0]]});
  const v=fundingView(r);assert.equal(v.maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents,0);
  assert.equal(v.firstPositiveFundingCeilingWeek,3);assert.equal(v.firstPositiveDuringServiceFundingCeilingWeek,null);
});
test('Unpriced failed discovery stays unknown and no second investment is created',()=>{
  const r=run({balances:[[0,1100,0,100,0]]}),before=JSON.stringify(r),v=fundingView(r);
  assert.equal(v.unpricedIncrementalDiscoveryCostCents,null);assert.equal(v.allInSpendableResourcesIdentified,false);
  assert.equal(v.actualSecondInvestmentCents,0);assert.equal(JSON.stringify(r),before);
});
const report={schema:'agi-alpha-independent-funding-view-controls/v1',executedAt:new Date().toISOString(),
  passed:tests.every(t=>t.passed),failedAssertions:tests.filter(t=>!t.passed).length,
  firstFailures:tests.filter(t=>!t.passed),tests,
  fundingSourceSHA256:createHash('sha256').update(readFileSync(resolve(root,'market/deployment-robustness/funding.mjs'))).digest('hex'),
  newMarketWorldsExecuted:0,newProductionMissions:0,
  preservedCounterexample:'A draft earmark subtraction only in the generated bound overcommitted a liquidity-bound budget. This was corrected before any fresh campaign. The verified physically consistent control has cash600, reserve500, generated500 and earmark80; spendable amount20.',
  interpretation:'Checks the declared attribution convention and nonmutation; does not identify unknown discovery cost, validate buyer demand or qualify a second asset.'};
writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
process.exitCode=report.passed?0:1;
