// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {canonical} from './journey-codec.mjs';
import {exactDigest} from './engine.mjs';
import {fixture,freshCycle} from './journey-fixture.mjs';
import {createJourney,inspectJourney,appendJourney} from './journey.mjs';
import {receivers,managerImport,managerAdvance,jobsImport,jobsRun,fleetRequest} from './receivers.mjs';
const fleetCheckout=process.env.GUIDED_FLEET_SOURCE;
if(!fleetCheckout)throw Error('GUIDED_FLEET_SOURCE pinned source required; complete journey tests never skip');
const {fixture:fleetFixture}=await import(pathToFileURL(path.join(fleetCheckout,'local-runtime/tests/helpers.mjs')));
async function actualFleetReturn(request){
  // Actual bounded computation/grants/journal; fixture isolation is synthetic, not native Linux qualification.
  const f=fleetFixture();
  try{
    const imported=await f.runtime.dispatch('journey-import',{request,confirm:true},f.operator),agent=f.create(),node=f.create('node');
    let grant=await f.runtime.dispatch('journey-prepare',{journey:imported.journey,actor:agent.id},f.operator);f.authorize(grant);
    const execution=await f.run(agent,grant);
    grant=await f.runtime.dispatch('journey-review-prepare',{journey:imported.journey,execution:execution.run,actor:node.id},f.operator);f.authorize(grant);
    const review=await f.run(node,grant);
    const exported=await f.runtime.dispatch('journey-export',{journey:imported.journey,execution:execution.run,review:review.run,confirm:true},f.operator);
    return exported.returned;
  }finally{f.close();}
}
async function prepared(language,route){
  const native=await fixture(language,'guided-'+language+'-'+route),nativeRaw=canonical(native);
  let history=await createJourney(nativeRaw),manager=await managerImport(nativeRaw,language);
  manager=await managerAdvance(manager,'run');manager=await managerAdvance(manager,'select-and-draft','25');
  history=await appendJourney(history,'manager-transfer',manager,receivers);
  let upstream=manager;
  if(route==='agijobsv0-jobregistry-v2'){
    upstream=await jobsImport(manager,'7000000000000000000','2026-10-16T01:00:00.000Z');
    history=await appendJourney(history,'jobs-transfer',upstream,receivers);
    upstream=await jobsRun(upstream);history=await appendJourney(history,'jobs-transfer',upstream,receivers);
  }
  return {native,nativeRaw,history,upstream,manager};
}
for(const language of ['en','fr'])for(const route of ['manager-usdc','agijobsv0-jobregistry-v2'])test(`${language}/${route}: actual Alpha→separately priced Jobs→Fleet execution/internal check→changed Alpha cycle`,async()=>{
  const p=await prepared(language,route),request=await fleetRequest(p.upstream,{language,route}),returned=await actualFleetReturn(request);
  const completed=await appendJourney(p.history,'fleet-return',returned,receivers),read=await inspectJourney(completed,receivers);
  assert.equal(read.fleet.request.upstream.raw,p.upstream);
  assert.equal(read.fleet.reviewClass,'historical-internal');assert.equal(read.fleet.independentReview,false);assert.equal(read.fleet.productionQualified,false);
  const next=await freshCycle(p.native);
  const staleHistory=await appendJourney(p.history,'alpha-cycle',canonical(next),receivers);
  await assert.rejects(appendJourney(staleHistory,'fleet-return',returned,receivers),/FLEET_PROJECT/);
  const continued=await appendJourney(completed,'alpha-cycle',canonical(next),receivers),end=await inspectJourney(continued,receivers);
  assert.deepEqual(end.project.cycles[0],p.native.cycles[0]);assert.equal(end.project.projectId,p.native.projectId);
  assert.equal(JSON.parse(end.project.cycles[0].records.at(-1).bytes).review.decision,'rejected');
  const last=JSON.parse(end.project.cycles.at(-1).records.at(-1).bytes);
  assert.equal(last.result.pack.result.summary.total,12);assert.equal(last.review,null);
  assert.equal(end.fleet,null);assert.equal(end.latestTransfer,null);assert.equal(end.journey.authority,'none');assert.equal(end.journey.settlement,'not-connected');
  assert.equal(end.journey.history.at(-2).raw,returned);assert.equal(end.journey.history[0].raw,p.nativeRaw);
  await assert.rejects(appendJourney(continued,'fleet-return',returned,receivers),/DUPLICATE_EVENT|FLEET_PROJECT/);
});
async function reseal(v){delete v.sha256;return canonical({...v,sha256:await exactDigest(canonical(v))});}
test('outer resealing cannot rewrite route, native work, project or settlement authority',async()=>{
  const p=await prepared('en','agijobsv0-jobregistry-v2');
  for(const change of [v=>v.authority='approved',v=>v.projectId='unrelated',v=>v.history[0].raw+=' ',v=>v.history.at(-1).kind='manager-transfer']){
    const v=JSON.parse(p.history);change(v);if(v.history[0].raw!==p.nativeRaw)v.history[0].sha256=await exactDigest(v.history[0].raw);
    await assert.rejects(inspectJourney(await reseal(v),receivers));
  }
  const request=JSON.parse(await fleetRequest(p.upstream,{language:'en',route:'agijobsv0-jobregistry-v2'}));request.route={backend:'manager-usdc',asset:'USDC'};
  await assert.rejects(actualFleetReturn(await reseal(request)));
});
test('route switching cannot roll back retained checkpoints or silently reprice a proposal',async()=>{
  const p=await prepared('en','manager-usdc'),initialManager=await managerImport(p.nativeRaw,'en');
  let jobs=await jobsImport(p.nativeRaw,'7','2026-10-16T01:00:00.000Z');
  let history=await appendJourney(p.history,'jobs-transfer',jobs,receivers);
  await assert.rejects(appendJourney(history,'manager-transfer',initialManager,receivers),/TRANSFER_HISTORY_REWRITTEN/);
  const repriced=await jobsImport(p.nativeRaw,'8','2026-10-16T01:00:00.000Z');
  await assert.rejects(appendJourney(history,'jobs-transfer',repriced,receivers),/TRANSFER_REPLANNED/);
  const wrong=await fixture('en','another-project'),wrongJobs=await jobsImport(canonical(wrong),'7','2026-10-16T01:00:00.000Z');
  await assert.rejects(appendJourney(history,'jobs-transfer',wrongJobs,receivers),/JOBS_PROJECT/);
});
