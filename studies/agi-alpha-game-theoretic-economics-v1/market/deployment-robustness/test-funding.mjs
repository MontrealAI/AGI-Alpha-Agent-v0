// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {fundingView,OPENING_RD_REFERENCE} from './funding.mjs';

const asset='a'.repeat(64);
function fixture({opening=1000,reserve=0,basis='full-history',balances,bills=[],cash=[]}){
  return {arm:'B',seed:0,config:{id:'synthetic-control',initialCashCents:opening,reserveCents:reserve,
    investmentCostBasis:basis,historicalCostTiming:'opening',weeks:3},histories:{bills,cash,
      balances:balances.map(b=>({week:b.week??0,cashCents:b.cash,obligationsCents:b.unpaid??0,
        reserveCents:reserve,cumulativeCollectionsCents:b.collections??0,accruedCostsCents:b.costs??0,
        earnedAvailableCents:Math.min(b.cash-(b.unpaid??0)-reserve,(b.collections??0)-(b.costs??0)-reserve)}))}};
}
const earmark=(amount=80)=>({id:'actual-candidate-commitment-synthetic',amountCents:amount,createdWeek:0,
  assetSHA256:asset,evidenceRef:'SYNTHETIC_COUNTEREXAMPLE_ONLY',billIds:['candidate-bill']});
const historical={id:'historical',category:'capability',reference:OPENING_RD_REFERENCE,week:0,
  dueWeek:0,amountCents:100,paid:true,paidWeek:0};

test('Seed alone is not generated money',()=>{
  const run=fixture({balances:[{cash:1000}]});assert.equal(fundingView(run).terminal.fundingCeilingBeforeUnpricedDiscoveryCents,0);
});
test('Unpaid historical R&D is never added back',()=>{
  const run=fixture({balances:[{cash:1100,collections:100,costs:100,unpaid:100}],bills:[{...historical,paid:false,paidWeek:undefined}]});
  const result=fundingView(run);assert.equal(result.historicalRDCentsExcluded,0);assert.equal(result.terminal.fundingCeilingBeforeUnpricedDiscoveryCents,0);
});
test('Only explicitly paid opening historical R&D is credited once',()=>{
  const run=fixture({balances:[{cash:1000,collections:100,costs:100}],bills:[historical],
    cash:[{week:0,type:'expense_payment',reference:'historical',amountCents:-100,cashAfterCents:900},
      {week:0,type:'simulated_collection',reference:'invoice',amountCents:100,cashAfterCents:1000}]});
  const before=JSON.stringify(run),result=fundingView(run);
  assert.equal(result.historicalRDCentsExcluded,100);assert.equal(result.terminal.fundingCeilingBeforeUnpricedDiscoveryCents,100);
  assert.equal(result.terminal.fullCostRecoveryCeilingBeforeUnpricedDiscoveryCents,0);assert.equal(JSON.stringify(run),before);
});
test('One reserve constrains cash and is not deducted twice from generated resources',()=>{
  const run=fixture({reserve:200,balances:[{cash:1000,collections:100}]});
  const result=fundingView(run).terminal;assert.equal(result.cashCapBeforeEarmarksCents,800);
  assert.equal(result.originalStrictEarnedAvailableCents,-100);assert.equal(result.fundingCeilingBeforeUnpricedDiscoveryCents,100);
});
test('Earmark reduces both bounds: cash100 generated500 earmark80 leaves20',()=>{
  const run=fixture({balances:[{cash:100,collections:500}]});
  assert.equal(fundingView(run,{earmarks:[earmark()]}).terminal.fundingCeilingBeforeUnpricedDiscoveryCents,20);
});
test('Earmark to accrual to payment preserves available funds without double charge',()=>{
  const bill={id:'candidate-bill',week:1,dueWeek:2,amountCents:80,category:'capability',reference:asset,paid:true,paidWeek:2};
  const run=fixture({balances:[{week:0,cash:100,collections:500},{week:1,cash:100,collections:500,costs:80,unpaid:80},
    {week:2,cash:20,collections:500,costs:80}],bills:[bill]});
  const result=fundingView(run,{earmarks:[earmark()]});
  assert.deepEqual(result.weekly.map(x=>x.fundingCeilingBeforeUnpricedDiscoveryCents),[20,20,20]);
  assert.deepEqual(result.weekly.map(x=>x.outstandingUnaccruedEarmarksCents),[80,0,0]);
});
test('Future collections cannot fund earlier weeks',()=>{
  const run=fixture({balances:[{week:0,cash:1000},{week:1,cash:1100,collections:100}]});
  const result=fundingView(run);assert.deepEqual(result.weekly.map(x=>x.fundingCeilingBeforeUnpricedDiscoveryCents),[0,100]);
  assert.equal(result.firstPositiveFundingCeilingWeek,1);
});
test('First adoption and setup are never mistaken for opening historical R&D',()=>{
  const run=fixture({balances:[{cash:1000,collections:200,costs:200}],bills:[
    {...historical,id:'adoption',reference:asset},{...historical,id:'setup',category:'business',reference:'setup'}],
    cash:[{week:0,type:'expense_payment',reference:'adoption',amountCents:-100},{week:0,type:'expense_payment',reference:'setup',amountCents:-100}]});
  const result=fundingView(run);assert.equal(result.historicalRDCentsExcluded,0);assert.equal(result.terminal.fundingCeilingBeforeUnpricedDiscoveryCents,0);
});
