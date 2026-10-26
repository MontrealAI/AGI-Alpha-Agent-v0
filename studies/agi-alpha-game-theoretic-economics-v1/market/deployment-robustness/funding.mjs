// SPDX-License-Identifier: Apache-2.0
// Pure read-only attribution view over the existing enterprise cash/cost history.
// No invoices, expenses, decisions, cash balances or accounting records are mutated.
export const FUNDING_VIEW_SCHEMA='agi-alpha-generated-funds-attribution/v1';
export const OPENING_RD_REFERENCE='upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing';
const assert=(condition,message)=>{if(!condition)throw Error(message);};
const integer=(value,name,nonnegative=true)=>{
  assert(Number.isSafeInteger(value)&&(!nonnegative||value>=0),`Explicit safe integer required: ${name}`);return value;
};
const sum=values=>values.reduce((a,b)=>a+b,0);

export function fundingView(run,{earmarks=[]}={}){
  assert(run&&run.config&&run.histories,'A complete existing enterprise run is required');
  const {config,histories}=run;
  assert(Array.isArray(histories.balances)&&histories.balances.length>0,'Existing weekly balances required');
  assert(Array.isArray(histories.bills)&&Array.isArray(histories.cash),'Existing bills and cash events required');
  assert(Array.isArray(earmarks),'Earmarks must be an explicit array');
  const opening=integer(config.initialCashCents,'opening cash'),reserve=integer(config.reserveCents,'reserve');
  const bills=new Map(histories.bills.map(b=>[b.id,b]));
  assert(bills.size===histories.bills.length,'Duplicate bill identities');
  const usedBills=new Set(),usedEarmarks=new Set();
  const commitments=earmarks.map(e=>{
    assert(e&&typeof e.id==='string'&&e.id&&!usedEarmarks.has(e.id),'Unique earmark identity required');usedEarmarks.add(e.id);
    assert(typeof e.evidenceRef==='string'&&e.evidenceRef.length>0,'Documented commitment evidence required');
    assert(typeof e.assetSHA256==='string'&&/^[a-f0-9]{64}$/.test(e.assetSHA256),'Actual asset identity required for an earmark');
    integer(e.amountCents,'earmark amount');integer(e.createdWeek,'earmark creation week');
    assert(Array.isArray(e.billIds),'Explicit linked bill identities required');
    for(const id of e.billIds){
      assert(typeof id==='string'&&!usedBills.has(id),'A bill cannot release multiple earmarks');usedBills.add(id);
      if(bills.has(id))assert(bills.get(id).reference===e.assetSHA256,'Linked bill must reference the earmarked asset');
    }
    if(e.cancelledWeek!==undefined&&e.cancelledWeek!==null){
      integer(e.cancelledWeek,'earmark cancellation week');assert(e.cancelledWeek>=e.createdWeek,'Earmark cannot cancel before creation');
    }
    return {...e,billIds:[...e.billIds]};
  });
  const eligibleHistorical=[];
  if(config.investmentCostBasis==='full-history'&&config.historicalCostTiming==='opening'){
    for(const bill of histories.bills){
      if(bill.category!=='capability'||bill.reference!==OPENING_RD_REFERENCE||bill.week!==0||
          !bill.paid||bill.paidWeek!==0)continue;
      const eventIndex=histories.cash.findIndex(e=>e.reference===bill.id&&e.type==='expense_payment'&&e.week===0&&e.amountCents===-bill.amountCents);
      if(eventIndex<0)continue;
      // Opening historical research must actually precede all customer collections.
      if(histories.cash.slice(0,eventIndex).some(e=>e.type==='simulated_collection'))continue;
      integer(bill.amountCents,'paid opening historical R&D');
      eligibleHistorical.push({billId:bill.id,amountCents:bill.amountCents,paidWeek:0,
        allocationBasis:'Explicit opening historical R&D paid before any collections; retained in original full profit and cash.'});
    }
  }
  assert(sum(eligibleHistorical.map(x=>x.amountCents))<=opening,'Historical seed allocation exceeds opening resources');
  const rows=histories.balances.map(balance=>{
    const week=integer(balance.week,'balance week'),cash=integer(balance.cashCents,'cash'),
      liabilities=integer(balance.obligationsCents,'unpaid obligations'),
      collections=integer(balance.cumulativeCollectionsCents,'collections'),
      accrued=integer(balance.accruedCostsCents,'accrued expenses'),
      strict=integer(balance.earnedAvailableCents,'original strict earned amount',false);
    assert(balance.reserveCents===reserve,'Reserve disagreement with existing balance');
    const historical=sum(eligibleHistorical.filter(x=>x.paidWeek<=week).map(x=>x.amountCents));
    assert(historical<=accrued,'Historical addback cannot exceed recorded accrued expenses');
    const unaccrued=sum(commitments.filter(e=>e.createdWeek<=week&&
      (e.cancelledWeek===undefined||e.cancelledWeek===null||e.cancelledWeek>week)).map(e=>{
        const released=sum(e.billIds.map(id=>bills.get(id)).filter(b=>b&&b.week<=week).map(b=>b.amountCents));
        return Math.max(0,e.amountCents-released);
      }));
    const cashCap=cash-liabilities-reserve,generatedBeforeEarmarks=collections-accrued+historical;
    assert(strict===Math.min(cashCap,collections-accrued-reserve),'Original strict metric disagrees with original balance fields');
    return {week,cashCents:cash,unpaidObligationsCents:liabilities,reserveCents:reserve,
      collectedCents:collections,allAccruedCostsCents:accrued,
      explicitlySeedPaidOpeningHistoricalRDCents:historical,
      prospectiveAccruedCostsToRecoverCents:accrued-historical,
      cashCapBeforeEarmarksCents:cashCap,generatedBeforeEarmarksCents:generatedBeforeEarmarks,
      outstandingUnaccruedEarmarksCents:unaccrued,
      cashCapAfterEarmarksCents:cashCap-unaccrued,
      generatedAfterEarmarksCents:generatedBeforeEarmarks-unaccrued,
      fundingCeilingBeforeUnpricedDiscoveryCents:Math.max(0,Math.min(cashCap,generatedBeforeEarmarks)-unaccrued),
      fullCostRecoveryCeilingBeforeUnpricedDiscoveryCents:Math.max(0,Math.min(cashCap,collections-accrued)-unaccrued),
      originalStrictEarnedAvailableCents:strict};
  });
  const duringService=rows.filter(x=>x.week<config.weeks),terminal=rows.at(-1);
  return {schema:FUNDING_VIEW_SCHEMA,basis:'SIMULATED_READ_ONLY_ATTRIBUTION',financialAuthority:'NONE',
    costBoundary:'BEFORE_UNPRICED_SECOND_ASSET_DISCOVERY',unpricedIncrementalDiscoveryCostCents:null,
    allInSpendableResourcesIdentified:false,
    afterDiscoveryQualification:'For nonnegative unpriced discovery cost D, subsequent spendable resources are at most max(0,reported ceiling-D); fixed-path profit is likewise reduced by any attributed D. No default D=0 or finite empirical cost bound is asserted.',
    sourceScenario:config.id,sourceArm:run.arm,sourceSeed:run.seed,
    sourceOfFundsConvention:'One reserve in liquidity; recover all prospective accrued costs; exclude only seed-paid opening historical R&D; subtract outstanding unaccrued earmarks from both bounds.',
    historicalBillsExcludedFromGeneratedRecovery:eligibleHistorical,
    historicalRDCentsExcluded:sum(eligibleHistorical.map(x=>x.amountCents)),
    actualSecondInvestmentCents:0,earmarks:commitments,weekly:rows,terminal,
    firstPositiveFundingCeilingWeek:rows.find(x=>x.fundingCeilingBeforeUnpricedDiscoveryCents>0)?.week??null,
    maximumFundingCeilingBeforeUnpricedDiscoveryCents:Math.max(...rows.map(x=>x.fundingCeilingBeforeUnpricedDiscoveryCents)),
    maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents:duringService.length?Math.max(...duringService.map(x=>x.fundingCeilingBeforeUnpricedDiscoveryCents)):0,
    firstPositiveDuringServiceFundingCeilingWeek:duringService.find(x=>x.fundingCeilingBeforeUnpricedDiscoveryCents>0)?.week??null,
    qualification:'Availability does not establish a qualified successor, an investment, repayment or capability growth.',
    originalCashAndProfitUnchanged:true};
}
