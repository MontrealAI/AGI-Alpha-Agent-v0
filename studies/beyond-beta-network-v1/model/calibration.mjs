// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {BASE,SCENARIOS,ASSETS,JOB_CLASSES,AGENTS,SENSITIVITIES} from './config.mjs';
import {DEFAULT_WORKFLOW_CONFIG,ROLE_BUDGETS,AUXILIARY_BUDGETS} from './workflow.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sources={
 OAI_PRICE:{url:'https://developers.openai.com/api/docs/pricing',date:'2026-10-26',type:'Reported by external sources',kind:'Official vendor tariff; not performance evidence'},
 OAI_MODELS:{url:'https://developers.openai.com/api/docs/guides/latest-model',date:'2026-10-26',type:'Reported by external sources',kind:'Official model/access/workflow guidance; not task acceptance calibration'},
 OAI_TERRA:{url:'https://openai.com/index/introducing-gpt-6-1-terra/',date:'2026-10-26',type:'Reported by external sources',kind:'Vendor capability evaluation; not independent foundry performance'},
 AWS:{url:'https://aws.amazon.com/fargate/pricing/',date:'2026-10-26',type:'Reported by external sources',kind:'US East N Virginia Linux x86 requested CPU and memory tariff'},
 SIMS:{url:'https://www.gsaadvantage.gov/ref_text/GS07F0011V/GS07F0011V_GSAMass_Supply_Schedule_TC_05062026.pdf',date:'2026-10-26',type:'Reported by external sources',kind:'Published US service-rate schedule; effective2026-10-01 through2027-09-30; not an accepted-outcome quote'},
 ALPHAEVOLVE:{url:'https://arxiv.org/abs/2506.13131',date:'2026-10-26',type:'Reported by external sources',kind:'Vendor-authored algorithm-discovery report; different models/workloads'},
 FUNSEARCH:{url:'https://www.nature.com/articles/s41586-023-06924-6',date:'2026-10-26',type:'Reported by external sources',kind:'Primary research; executable evaluators and held-out generalization, not this autonomous service'},
 ORTOOLS:{url:'https://developers.google.com/optimization',date:'2026-10-26',type:'Reported by external sources',kind:'Strong ordinary-tool baseline is available to every arm'},
 EOH:{url:'https://proceedings.mlr.press/v235/liu24bs.html',date:'2026-10-26',type:'Reported by external sources',kind:'Independent primary method research; external-validity limitation retained'},
 TRANSFORMATION:{url:'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/docs/Transformational_Intelligence.pdf',date:'2026-10-26',type:'Reported by external sources',kind:'Conceptual research foundation; not an empirical capability calibration'},
 GYM_OMEGA:{url:'https://github.com/MontrealAI/MontrealAI.github.io/blob/a9cc143bc05495405ac63b0e2645c425d66410b8/GoalOS_Gym_Specialist_ASI_Successor_Omega_v2_1_0_US_LETTER.pdf',date:'2026-10-26',type:'Reported by external sources',kind:'Conceptual mission/proof/authority/lifecycle foundation; synthetic examples excluded from numerical calibration'},
 USER_CHARTER:{url:'../USER_CHARTER.md',date:'2026-10-26',type:'Assumed or explored',kind:'Authorized study design and scope, including A/B/C and automated target'},
 LOCAL_TESTS:{url:'../results/graph_qualification.json',date:'2026-10-26',type:'Observed in our own work',kind:'Executed local research-code controls; no operational model/customer observations'},
};
const factual={webSearchPrice:['OAI_PRICE','Reported by external sources'],fileSearchPrice:['OAI_PRICE','Reported by external sources'],
 containerBlockPrice:['OAI_PRICE','Reported by external sources'],storagePricePerGbDay:['OAI_PRICE','Reported by external sources'],
 cpuPricePerHour:['AWS','Calibrated from sources'],humanReference:['SIMS','Calibrated from sources']};
const parameters=[];
for(const [namespace,obj]of [['enterprise',BASE],['workflow',DEFAULT_WORKFLOW_CONFIG]])for(const [name,value]of Object.entries(obj)){
 const anchor=factual[name],range=SENSITIVITIES.find(([k])=>k===name)?.[1]??null;
 parameters.push({namespace,name,value,evidenceCategory:anchor?.[1]??'Assumed or explored',sourceIds:anchor?[anchor[0]]:['USER_CHARTER'],sensitivityValues:range,
  note:name==='humanReference'?'Rates reported; team hours and failed-search allocation assumed. The product is a matched-scope reference estimate, not a quote.':
   name==='cpuPricePerHour'?'1 vCPU plus2GB x86 memory:3600*(0.000011244+2*0.000001235). Not a claim of runtime/latency.':
   anchor?'Current nominal tariff; quantity, applicability and future persistence remain assumptions.':
   'Not empirically calibrated for this venture. Declared policy, resource count, probability, demand, value, capacity or lifecycle assumption; vary rather than infer from a benchmark score.'});
}
const register={schema:'paid-work-alpha-calibration/v1',evidenceDate:'2026-10-26',sources,parameters,
 categories:['Observed in our own work','Reported by external sources','Calibrated from sources','Assumed or explored'],
 observedBoundary:{observed:['Source retrieval and arithmetic','Executable local simulator/test runs when separately receipted','Graph lifecycle/crypto software controls'],
  notObserved:['Live frontier delivery','Actual customer demand or purchases','Human-team elapsed effort','Operational Alpha admission','Production network scale','Real financial transactions']},
 modelTariffs:JSON.parse(fs.readFileSync(path.join(root,'evidence/frontier_model_recheck.json'),'utf8')),
 roleBudgets:{evidenceCategory:'Assumed or explored',values:ROLE_BUDGETS,interpretation:'Full billed internal Pro work and reasoning output are included, not multiplied by an arbitrary expertise factor.'},
 auxiliaryBudgets:{evidenceCategory:'Assumed or explored',values:AUXILIARY_BUDGETS},
 scenarios:SCENARIOS,jobClasses:JOB_CLASSES,agents:AGENTS,assets:ASSETS,
 A_B_C:{A:'All resource work producing the accepted customer artifact, including learning/search/correction. A stays in job and consolidated expense.',
  B:'Only additional retention, rights/sanitization, generalization, fresh paired assessment, distribution, integration, revalidation and upkeep. No source-job A is recharged.',
  C:'Optional separate research beyond the paid scope. Its complete additional cost is retained in the investment and Alpha hurdle when chosen.',
  valuationsAreNotExpenses:'Probe counterfactual utility and source-job references do not create duplicate cash bills. Reserves are unavailable cash, not expenses. Customer savings are not revenue.'},
 strategicLimits:['Buyer private value, trust, recurrence, human completion and contingent billing are unmeasured.',
  'Skill emergence and transfer effects are hypotheses, not field-estimated frequencies.',
  'Alpha intervals reflect conditional simulation noise and do not bound shared semantic bias.',
  'Physical deployment, professional signoff and unsupported semantics are outside the automated contract.',
  'Access restriction is not proof of scarcity or a durable economic moat.']};
fs.writeFileSync(path.join(root,'evidence/calibration_register.json'),JSON.stringify(register,null,2)+'\n');
console.log(JSON.stringify({registeredParameters:parameters.length,sourceCount:Object.keys(sources).length,scientificOutcomesRun:false}));
