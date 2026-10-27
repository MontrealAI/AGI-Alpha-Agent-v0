// SPDX-License-Identifier: Apache-2.0
import {writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const {createPublicSkillRegistry} = await import(pathToFileURL(process.argv[2]).href);
const registry = createPublicSkillRegistry(), checks = [];
const refuse = (name, action) => { try { action(); } catch(error) { checks.push({name, refused:true, reason:error.message}); return; } throw Error(`${name}: accepted`); };
const candidate = {id:'scheduling-research-fixture', originatingMission:'synthetic-origin', scope:'synthetic-scheduling-fixture',
  implementation:'Control-plane conformance only; not scientific evidence or actual skill content', rights:'PUBLIC_EXAMPLE_APACHE_2.0'};
registry.create(candidate);
refuse('premature-admission', () => registry.admit(candidate.id));
registry.evidence(candidate.id, {kind:'PUBLIC_FRESH_FIXTURE',fresh:true,criteria:'synthetic paired conformance',
  taskFamily:'teaching-scheduling',benefit:121,incrementalCost:120});
registry.assess(candidate.id);
registry.validate(candidate.id, {freshPass:true,baseline:'frontier-beta/1',independentCheck:'synthetic-control-only'});
registry.admit(candidate.id);
if(registry.discover().length!==1) throw Error('discovery failed');
refuse('unauthorized-fixture', () => registry.reuse(candidate.id,{scope:candidate.scope}));
const reuse=registry.reuse(candidate.id,{scope:candidate.scope,fixtureEligible:true});
registry.baselineChanged('frontier-beta/2');
refuse('stale-beta', () => registry.reuse(candidate.id,{scope:candidate.scope,fixtureEligible:true}));
registry.revalidate(candidate.id, {baseline:'frontier-beta/2',outcome:'retains',benefit:121,incrementalCost:120,
  freshPass:true,independentCheck:'synthetic-control-only'});
registry.revoke(candidate.id);
refuse('revoked-capability', () => registry.reuse(candidate.id,{scope:candidate.scope,baseline:'frontier-beta/2',fixtureEligible:true}));
const result={schema:'next-advantage-public-lifecycle-controls/v1',mode:'PUBLIC_FIXTURE_ONLY',qualification:registry.qualification(),
  benefit_and_cost:'Arbitrary synthetic branch-coverage values 121/120, excluded from scientific and economic results.',
  history:registry.history(),checks,reuse,scientific_admission:false,live_identity:false,retained_capability_value_established:false};
writeFileSync(process.argv[3],JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({status:'PASS',negative_controls:checks.length,mode:result.mode}));
