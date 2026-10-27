// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {evaluateFreshCampaign,buildMetaProtocol} from './meta_experiment.mjs';
import {DEFAULT_WORKFLOW_CONFIG} from './workflow.mjs';
const config={...DEFAULT_WORKFLOW_CONFIG,improvableFraction:1,improvementProbability:1,
 commonError:0,initialError:.4,maxRetries:0,betaBundleAbsorption:0,betaExperimentAbsorption:0};
// Two tiny synthetic campaigns, disjoint from all registered outcome seeds.
const sample=evaluateFreshCampaign(config,42,4);
assert.equal(sample.arms.expert_baseline.costCents,sample.arms.zero_increment_control.costCents);
assert.equal(sample.arms.expert_baseline.candidates,4);
assert.equal(sample.arms.retained_family_screen.candidates,4);
const absorbed=evaluateFreshCampaign({...config,betaExperimentAbsorption:1},43,4);
assert.equal(absorbed.arms.expert_baseline.costCents,absorbed.arms.retained_family_screen.costCents);
assert.deepEqual(absorbed.arms.expert_baseline.resources,absorbed.arms.retained_family_screen.resources);
assert.equal(absorbed.arms.expert_baseline.useful,absorbed.arms.retained_family_screen.useful);
const protocol=buildMetaProtocol();
assert.equal(protocol.config.betaExperimentAbsorption,0);
assert.equal(protocol.seeds[0],1040000);assert.equal(protocol.seeds.at(-1),1040255);
assert.ok(protocol.methods.networkBoundary.includes('not a network-admission'));
assert.equal(protocol.assetWorkUnits,2600,'Optional independent research is not reclassified as cheap retention');
assert.equal(protocol.sourceCostLayer,'C_optional_research_without_prepaid_customer_origin');
console.log('Meta controls passed: fresh campaign unit, no descendant-job proxy and absorbed/null equality.');
