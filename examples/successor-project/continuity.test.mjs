// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync,execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {canonical} from '../../docs/assets/successor/engine.mjs';
import * as native from '../successor-workbench/mission-record.mjs';
import {example,run} from '../successor-workbench/engine.mjs';
import {createBrief} from '../alpha-discovery/engine.mjs';
import * as project from './engine.mjs';
import {importManagerCycle,inspectContinuity,advanceContinuity,ALPHA_BASELINE,ALPHA_NATIVE_SOURCE,MANAGER_SOURCE} from './continuity.mjs';
const managerCheckout=process.env.CONTINUITY_MANAGER_SOURCE,alphaBaselineCheckout=process.env.CONTINUITY_ALPHA_BASELINE;
if(!managerCheckout||!alphaBaselineCheckout)throw Error('Both pinned clean source checkouts are required; integration tests do not skip');
const manager=await import(pathToFileURL(path.join(managerCheckout,'scripts/successor/alpha-project.mjs')));
const options={managerCheckout,alphaBaselineCheckout};
const manifest=JSON.parse(fs.readFileSync(path.join(alphaBaselineCheckout,'docs/successor/mission/sources.json')));
const source=p=>({repository:ALPHA_BASELINE.repository,commit:ALPHA_BASELINE.commit,path:p,sha256:manifest.sources[p]});
const sources={discovery:source('examples/alpha-discovery/engine.mjs'),mission:source('examples/successor-workbench/mission-record.mjs')};
const choices={family:'public-data',selection:'explicit-user-selection',duplicatePolicy:'sum-all-rows-no-deduplication',unitPolicy:'unchanged-integer-units',dataRights:'synthetic'};
async function fixture(language='en'){
  const spec=example('public-data');spec.language=language;
  let record=await native.createRecord({missionId:'old-mission',sourceHash:manifest.sourceHash,spec});
  let p=await project.createProject({projectId:'one-project',cycleId:'first-cycle',sourceHash:manifest.sourceHash,record,discoveryBytes:canonical(await createBrief(project.publicDataOpportunity(),manifest.sourceHash)),choices,sources});
  const append=r=>project.appendRecord(p,r,{expectedRevision:p.revision,sourceHash:manifest.sourceHash,sources});
  record=await native.startRun(record,{expectedRevision:0,runId:'original-run'});p=await append(record);
  record=await native.completeRun(record,await run(spec,{sourceHash:manifest.sourceHash}),{expectedRevision:record.revision,runId:'original-run'});p=await append(record);
  record=await native.reviewRecord(record,{expectedRevision:record.revision,decision:'rejected',note:'Supplied self-review: preserve rejection, no protected comparative evaluation.'});p=await append(record);
  let raw=await manager.importAlphaProject(canonical(p),{alphaCheckout:alphaBaselineCheckout,language,mappingAcknowledgement:'alpha-public-data-to-manager-rows/v1'});
  raw=await manager.advanceAlphaProject(raw,{alphaCheckout:alphaBaselineCheckout,action:'run'});
  raw=await manager.advanceAlphaProject(raw,{alphaCheckout:alphaBaselineCheckout,action:'select-and-draft',budget:'25'});
  return {raw,p};
}
function selection(language='en'){
  const spec=example('public-data');spec.language=language;spec.inputs.csv='group,amount\nNouveau,14\nNouveau,-4\nAutre,2\n';
  return {acknowledgement:'new-public-data-cycle',cycleId:'second-cycle',missionId:'second-mission',spec};
}
async function reseal(v){delete v.sha256;v.sha256=await project.exactDigest(canonical(v));return canonical(v);}
for(const language of ['en','fr'])test(language+': Alpha → actual Manager work/USDC proposal → fresh Alpha cycle and execution retain one history',async()=>{
  const {raw,p}=await fixture(language),imported=await importManagerCycle(raw,selection(language),options);
  let read=await inspectContinuity(imported,options);
  assert.equal(read.continuity.manager.raw,raw);assert.equal(read.project.projectId,'one-project');
  assert.deepEqual(read.project.cycles[0],p.cycles[0]);assert.equal(read.project.cycles.length,2);
  assert.notEqual(read.project.sourceHash,p.sourceHash);
  assert.equal(read.project.cycles.at(-1).records[0].source.commit,ALPHA_NATIVE_SOURCE.commit);
  const last=()=>JSON.parse(read.project.cycles.at(-1).records.at(-1).bytes);
  assert.equal(last().state,'draft');assert.equal(last().review,null);assert.equal(last().result,null);
  assert.equal(JSON.parse(read.project.cycles[0].records.at(-1).bytes).review.decision,'rejected');
  const executed=await advanceContinuity(imported,options);read=await inspectContinuity(executed,options);
  assert.equal(last().result.pack.result.summary.total,12);assert.equal(last().review,null);
  assert.equal(read.continuity.manager.raw,raw);
  assert.equal(read.continuity.history[0].projectRaw,JSON.parse(imported).history[0].projectRaw);
  const stored=JSON.parse(read.continuity.history.at(-1).projectRaw).cycles.at(-1).records.at(-1);
  const pack=JSON.parse(stored.bytes).result.pack;
  assert.equal(last().result.pack.createdAt,pack.createdAt);
  assert.equal(last().result.pack.economics.elapsedMilliseconds,pack.economics.elapsedMilliseconds);
  assert.equal(read.managerSummary.checkpoints,3);assert.equal(read.managerSummary.plans,1);
  assert.equal(read.continuity.authority,'none');assert.equal(read.continuity.qualification,'not-evaluated');assert.equal(read.continuity.settlement,'not-connected');
});
test('explicit new input, distinct mission/cycle IDs and trusted checkouts are required',async()=>{
  const {raw}=await fixture();
  await assert.rejects(importManagerCycle(raw,{...selection(),acknowledgement:'inferred'},options),/EXPLICIT_NEW_INPUT/);
  await assert.rejects(importManagerCycle(raw,{...selection(),missionId:'old-mission'},options),/NEW_MISSION_ID/);
  await assert.rejects(importManagerCycle(raw,{...selection(),cycleId:'first-cycle'},options),/DUPLICATE_CYCLE/);
  await assert.rejects(importManagerCycle(raw,selection(),{...options,managerCheckout:alphaBaselineCheckout}),/SOURCE_PIN/);
});
test('outer checksums cannot fabricate Manager execution, change history or grant authority',async()=>{
  const {raw}=await fixture(),base=JSON.parse(await importManagerCycle(raw,selection(),options));
  for(const change of [v=>v.authority='approved',v=>v.history[0].kind='local-alpha-run',v=>v.selection.spec.inputs.csv+='X,99\n',v=>v.sources.manager.commit='a'.repeat(40)]){
    const v=structuredClone(base);change(v);await assert.rejects(inspectContinuity(await reseal(v),options));
  }
  const v=structuredClone(base),m=JSON.parse(v.manager.raw);m.history.at(-1).kind='local-run';delete m.sha256;m.sha256=await project.exactDigest(canonical(m));v.manager.raw=canonical(m);v.manager.sha256=await project.exactDigest(v.manager.raw);
  await assert.rejects(inspectContinuity(await reseal(v),options),/MANAGER_NATIVE_INVALID/);
});
test('native project cannot be swapped even with every outer digest recomputed',async()=>{
  const {raw}=await fixture(),v=JSON.parse(await advanceContinuity(await importManagerCycle(raw,selection(),options),options));
  const p=JSON.parse(v.history.at(-1).projectRaw);p.projectId='another-project';delete p.projectDigest;
  const {digest}=await import('../../docs/assets/successor/engine.mjs');p.projectDigest=await digest('successor-project',p);
  v.history.at(-1).projectRaw=canonical(p);v.history.at(-1).sha256=await project.exactDigest(v.history.at(-1).projectRaw);
  await assert.rejects(inspectContinuity(await reseal(v),options),/CROSS_PROJECT|TRANSITION_CHANGED/);
});
test('CLI saves a reviewable single history, inspects it and refuses overwrite',async t=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'alpha-continuity-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const {raw}=await fixture(),transfer=path.join(root,'manager.json'),spec=path.join(root,'next.json'),output=path.join(root,'history.json');
  fs.writeFileSync(transfer,raw);fs.writeFileSync(spec,canonical(selection().spec));
  const cli=args=>spawnSync(process.execPath,[new URL('./continuity-cli.mjs',import.meta.url).pathname,...args],{encoding:'utf8',timeout:30000});
  const args=['import',transfer,managerCheckout,alphaBaselineCheckout,spec,'second-cycle','second-mission','--new-public-data-cycle',output];
  assert.equal(cli(args).status,0);const before=fs.readFileSync(output,'utf8');assert.equal(cli(args).status,1);assert.equal(fs.readFileSync(output,'utf8'),before);
  const inspected=cli(['inspect',output,managerCheckout,alphaBaselineCheckout]);assert.equal(inspected.status,0);assert.equal(JSON.parse(inspected.stdout).projectId,'one-project');
});

test('oversized or ambiguous imports reject before any execution or history mutation',async()=>{
  await assert.rejects(inspectContinuity(' '.repeat(2_000_001),options),/2 MB/);
  await assert.rejects(inspectContinuity('{"schema":"x","schema":"y"}',options));
});

test('hidden validator edits in either checkout are rejected against pinned Git bytes', {timeout:120000},async()=>{
  const {raw}=await fixture();
  for(const [checkout,pin,key,relative] of [
    [managerCheckout,MANAGER_SOURCE,'managerCheckout','scripts/successor/alpha-project.mjs'],
    [alphaBaselineCheckout,ALPHA_BASELINE,'alphaBaselineCheckout','examples/successor-project/engine.mjs'],
  ]){
    const directory=fs.mkdtempSync(path.join(os.tmpdir(),'continuity-validator-'));
    try{
      execFileSync('git',['-C',checkout,'worktree','add','--detach',directory,pin.commit],{timeout:60000,stdio:'pipe'});
      const file=path.join(directory,relative),before=fs.readFileSync(file);
      for(const flag of ['skip-worktree','assume-unchanged']){
        execFileSync('git',['-C',directory,'update-index','--'+flag,'--',relative]);
        try{
          fs.writeFileSync(file,Buffer.concat([before,Buffer.from('\n/* hidden validator edit */\n')]));
          assert.equal(execFileSync('git',['-C',directory,'status','--porcelain','--untracked-files=no'],{encoding:'utf8'}).trim(),'');
          await assert.rejects(importManagerCycle(raw,selection(),{...options,[key]:directory}),/CONTINUITY_SOURCE_BYTES/);
        }finally{
          fs.writeFileSync(file,before);execFileSync('git',['-C',directory,'update-index','--no-'+flag,'--',relative]);
        }
      }
    }finally{
      execFileSync('git',['-C',checkout,'worktree','remove','--force',directory],{timeout:30000,stdio:'pipe'});
      fs.rmSync(directory,{recursive:true,force:true});
    }
  }
});

test('untracked editable-source metadata cannot override the pinned Manager commit', {timeout:120000},async()=>{
  const {raw}=await fixture(),directory=fs.mkdtempSync(path.join(os.tmpdir(),'continuity-metadata-'));
  try{
    execFileSync('git',['-C',managerCheckout,'worktree','add','--detach',directory,MANAGER_SOURCE.commit],{timeout:60000,stdio:'pipe'});
    fs.writeFileSync(path.join(directory,'SOURCE.json'),JSON.stringify({commit:'0'.repeat(40),version:'1.17.0'}));
    await assert.rejects(importManagerCycle(raw,selection(),{...options,managerCheckout:directory}),/CONTINUITY_SOURCE_BYTES/);
  }finally{
    execFileSync('git',['-C',managerCheckout,'worktree','remove','--force',directory],{timeout:30000,stdio:'pipe'});
    fs.rmSync(directory,{recursive:true,force:true});
  }
});

test('fully resealed Manager capsule provenance cannot enter an Alpha return history',async()=>{
  const {raw}=await fixture(),transfer=JSON.parse(raw),capsule=JSON.parse(transfer.history[0].capsule);
  capsule.payload.sourceManifest.commit='0'.repeat(40);
  capsule.sha256=await project.exactDigest(canonical(capsule.payload));
  transfer.history[0].capsule=canonical(capsule);transfer.history[0].sha256=await project.exactDigest(transfer.history[0].capsule);
  await assert.rejects(importManagerCycle(await reseal(transfer),selection(),options),/MANAGER_NATIVE_INVALID/);
});
