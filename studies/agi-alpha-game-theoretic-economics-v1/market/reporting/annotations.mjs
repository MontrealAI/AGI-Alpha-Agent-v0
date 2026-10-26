// Generated exact postprocessing blocks from frozen runners; no market decisions here.
const priceRange=values=>values.length?{minimumCents:Math.min(...values),maximumCents:Math.max(...values)}:null;
export function annotateExploratory(paired){
    const capital=paired.arms.B.histories.bills.filter(x=>x.category==='capability').reduce((n,x)=>n+x.amountCents,0);
    paired.exploratory={status:'POSTPRIMARY_EXPLORATORY',B_oneoffCapabilityIncurredCents:capital,
      B_fixedPathMaximumOneoffCostCents:paired.causal.B_minus_A_profitCents+capital,
      thresholdScope:'Fixed realized path only; K changes can change policy, funding, timing and demand. Not a global break-even bound.'};
}
export function annotatePolicy(paired,config,seed,priorId,prior){
    const capital=paired.arms.B.histories.bills.filter(x=>x.category==='capability').reduce((n,x)=>n+x.amountCents,0);
    const comparison=Object.fromEntries(['A','B','C'].map(arm=>{
      const baseline=prior.get(`${priorId}|${seed}|${arm}`);if(!baseline)throw Error('Matching heuristic world missing');
      if(baseline.opportunities!==paired.arms[arm].summary.opportunities||
        baseline.supportedOpportunities!==paired.arms[arm].summary.supportedOpportunities)throw Error('External common draws differ');
      return [arm,paired.arms[arm].summary.profitCents-baseline.profitCents];}));
    const posted=Object.fromEntries(['A','B','C'].map(arm=>[arm,{
      computedWeeklyQuotes:priceRange(paired.arms[arm].histories.prices.map(x=>x.enterpriseCents)),
      offeredQuotes:priceRange(paired.arms[arm].histories.prices.filter(x=>x.offersSeen>0).map(x=>x.enterpriseCents)),
      offeredBeforeAdoption:priceRange(paired.arms[arm].histories.prices.filter(x=>x.offersSeen>0&&!x.assetActive).map(x=>x.enterpriseCents)),
      offeredAfterAdoption:priceRange(paired.arms[arm].histories.prices.filter(x=>x.offersSeen>0&&x.assetActive).map(x=>x.enterpriseCents)),
      acceptedDeliveryPrices:priceRange(paired.arms[arm].histories.jobs.filter(x=>x.provider==='enterprise'&&x.accepted).map(x=>x.priceCents)),
      acceptedBeforeAdoption:priceRange(paired.arms[arm].histories.jobs.filter(x=>x.provider==='enterprise'&&x.accepted&&!x.assetUsed).map(x=>x.priceCents)),
      acceptedAfterAdoption:priceRange(paired.arms[arm].histories.jobs.filter(x=>x.provider==='enterprise'&&x.accepted&&x.assetUsed).map(x=>x.priceCents))}]));
    paired.policyDiagnostic={status:'POST_EXPLORATORY_NOT_CONFIRMATION',priorHeuristicScenario:priorId,
      targetPriceCents:config.initialPriceCents,priceRanges:posted,
      priceRangeScope:'All simulated: computed quotes may be unseen; offered quotes require offersSeen>0; accepted-delivery prices require accepted enterprise jobs.',
      policyMinusHeuristicProfitCents:comparison,
      B_oneoffCapabilityIncurredCents:capital,B_fixedPathMaximumOneoffCostCents:paired.causal.B_minus_A_profitCents+capital};
}
