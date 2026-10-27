// SPDX-License-Identifier: Apache-2.0
export const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
export function quantile(a,p){const x=a.filter(Number.isFinite).sort((a,b)=>a-b);return x.length?x[Math.floor((x.length-1)*p)]:null;}
export function distribution(a){
 const x=a.filter(Number.isFinite),m=mean(x),v=x.length>1?x.reduce((s,z)=>s+(z-m)**2,0)/(x.length-1):0;
 const se=x.length?Math.sqrt(v/x.length):null;
 return {n:x.length,mean:m,median:quantile(x,.5),p05:quantile(x,.05),p95:quantile(x,.95),min:x.length?Math.min(...x):null,
  max:x.length?Math.max(...x):null,meanMC95:x.length?[m-1.96*se,m+1.96*se]:null};
}
export function frequency(k,n){const z=1.959963984540054,p=n?k/n:0,d=1+z*z/Math.max(1,n),c=(p+z*z/(2*Math.max(1,n)))/d,
 h=z*Math.sqrt(p*(1-p)/Math.max(1,n)+z*z/(4*Math.max(1,n)**2))/d;
 return {count:k,n,rate:n?p:null,wilson95:n?[c-h,c+h]:null};}
export function summarize(rows){
 const keys=[...new Set(rows.flatMap(x=>Object.keys(x)))];const out={runs:rows.length};
 for(const k of keys){const v=rows.map(x=>x[k]);if(v.some(x=>typeof x==='number'))out[k]=distribution(v);
  else if(v.every(x=>typeof x==='boolean'))out[k]=frequency(v.filter(Boolean).length,v.length);}
 for(const [name,test]of Object.entries({profitable:r=>r.profitCents>0,invested:r=>r.investmentCampaigns>0,
  admittedAlpha:r=>r.successfulCampaigns>0,usedAlpha:r=>r.alphaUses>0,peerBenefitWork:r=>r.peerUsefulOutcomes>0,
  earnedFunded:r=>r.earnedFundedInvestmentCents>0,zeroUseful:r=>r.usefulAccepted===0}))out[name]=frequency(rows.filter(test).length,rows.length);
 return out;
}
export function paired(rows,a,b){
 const A=new Map(rows.filter(r=>r.arm===a).map(r=>[r.seed,r])),B=new Map(rows.filter(r=>r.arm===b).map(r=>[r.seed,r]));
 const diffs=[];for(const [seed,x]of A){const y=B.get(seed);if(!y)throw Error('Unmatched paired seed');const d={seed};
  for(const k of ['profitCents','discountedAccrualProfitCents','terminalCashCents','costsCents','usefulAccepted','accepted','capacityRefusals',
   'newlyFeasibleUseful','investmentCampaigns','earnedFundedInvestmentCents','retainedCapabilities','peerUsefulOutcomes'])d[k]=x[k]-y[k];
  diffs.push(d);}
 return {arms:[a,b],independentWorlds:diffs.length,differences:Object.fromEntries(Object.keys(diffs[0]??{}).filter(k=>k!=='seed').map(k=>[k,distribution(diffs.map(d=>d[k]))])),
  positiveProfitDifference:frequency(diffs.filter(d=>d.profitCents>0).length,diffs.length),rows:diffs};
}
