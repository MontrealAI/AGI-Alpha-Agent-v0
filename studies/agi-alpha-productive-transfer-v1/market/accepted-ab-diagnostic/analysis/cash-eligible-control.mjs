// SPDX-License-Identifier: Apache-2.0
// One post-campaign software control. No seed search or changes to frozen files.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {conditionalAB} from '../accepted-ab.mjs';
const at=name=>new URL(name,import.meta.url);
const hash=name=>createHash('sha256').update(readFileSync(at(name))).digest('hex');
const read=name=>JSON.parse(readFileSync(at(name),'utf8'));
const output=at('./cash-eligible-control.result.json');
if(existsSync(output))throw Error('Single execution only: refusing to overwrite or search further');
const input=read('./cash-eligible-control.input.json');
for(const [file,key] of [['../accepted-ab.mjs','frozenAdapterSHA256'],['../../market-transfer-core.mjs','frozenCoreSHA256'],
 ['../production-accepted-ab.json','productionSHA256'],['../scenarios.json','registeredScenarioSHA256'],['../freeze.json','approvedCampaignFreezeSHA256']]){
 if(hash(file)!==input.source[key])throw Error(`Preserved input changed: ${file}`);
}
if(input.seed!==3001)throw Error('Only the declared single seed is allowed');
const wall=performance.now(),cpu=process.cpuUsage();
const pair=conditionalAB(read('../production-accepted-ab.json'),input.scenario,input.seed);
const decisions=pair.arms.B.histories.investmentDecisions;
const eligible=decisions.filter(d=>d.availableCashCents>=d.fullCostCents);
const result={schema:'agi-alpha-post-campaign-cash-eligibility-software-control/v1',
 inputSHA256:hash('./cash-eligible-control.input.json'),sourceSHA256:hash('./cash-eligible-control.mjs'),
 source:input.source,seed:input.seed,classification:'POST_CAMPAIGN_SOFTWARE_CONTROL_NOT_REGISTERED_MARKET_OUTCOME',
 status:eligible.length?(pair.arms.B.histories.investments.length===0?'PASS_CASH_ELIGIBLE_ZERO_SAVING_REFUSED':'FAIL_UNJUSTIFIED_BUILD'):
  'INCONCLUSIVE_NO_CASH_ELIGIBLE_DECISION',
 decisions:decisions.length,cashEligibleDecisions:eligible.length,
 firstCashEligibleDecision:eligible[0]||null,
 maximumAvailableEarnedCashCents:decisions.length?Math.max(...decisions.map(d=>d.availableCashCents)):null,
 BInvestments:pair.arms.B.histories.investments.length,B_minus_A_profitCents:pair.differences.B_minus_A_profitCents,
 allEligibleDecisionsRefused:eligible.length>0&&eligible.every(d=>d.action==='retain-incumbent'&&d.expectedIncrementalSavingPerUseCents===0&&d.expectedNetBenefitCents<=0),
 noAdditionalTuning:true,registeredCampaignNotRerun:true,pair,
 resources:{processWallSeconds:(performance.now()-wall)/1000,processCpuSeconds:null,
  executionMonetaryCostCents:null,authoringInferenceCostCents:null,humanMinutes:null,
  boundary:'Measured command resources only; incomplete monetary cost remains unknown. Agent elapsed time is not a human wage bill.'},
 observedCustomerCollectionsCents:0,actualFinancialAction:false};
const end=process.cpuUsage(cpu);result.resources.processCpuSeconds=(end.user+end.system)/1e6;
writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({status:result.status,decisions:result.decisions,cashEligibleDecisions:result.cashEligibleDecisions,
 maxAvailableEarnedCashCents:result.maximumAvailableEarnedCashCents,BInvestments:result.BInvestments,
 AProfitCents:pair.arms.A.summary.profitCents,BProfitCents:pair.arms.B.summary.profitCents,
 firstCashEligibleDecision:result.firstCashEligibleDecision,resultSHA256:hash('./cash-eligible-control.result.json')})+'\n');
