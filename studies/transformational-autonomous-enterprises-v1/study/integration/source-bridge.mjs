// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import {createHash, randomUUID} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL, fileURLToPath} from 'node:url';

const hash = value => createHash('sha256').update(value).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));
const need = (ok, code) => {if (!ok) throw Error(code);};
const PINS = Object.freeze({alpha:'9cb90e8c189f146eff7d166e249d9474792c4864', manager:'3153ac394d37eeecb03e825ecce37559427bc6c3', jobs:'ca6cfb74a36c233e5f04bd591a5e2179299774a1', fleet:'45759fb096faf8988f58ae5ea71248d0f35a97c7'});
const ENTRIES = Object.freeze({
  alpha:['examples/successor-project/engine.mjs','examples/successor-workbench/engine.mjs','examples/successor-workbench/mission-record.mjs','examples/alpha-discovery/engine.mjs'],
  manager:['site/assets/successor/alpha-project.mjs','scripts/successor/build.mjs'],
  jobs:['integrations/alpha-agent/project-transfer.mjs'],
  fleet:['local-runtime/project/transfer.mjs','local-runtime/worker.mjs']
});

function sourceClosure(directory, entries) {
  const files = new Map();
  function visit(relative) {
    if (files.has(relative)) return;
    need(!relative.startsWith('..') && !path.isAbsolute(relative), 'SOURCE_OUTSIDE_CHECKOUT');
    const location = path.join(directory, relative);
    need(fs.lstatSync(location).isFile() && fs.realpathSync(location) === location, 'SOURCE_NOT_REGULAR');
    const bytes = fs.readFileSync(location);
    const original = execFileSync('git',['show','HEAD:'+relative],{cwd:directory,maxBuffer:4_000_000});
    need(bytes.equals(original), 'SOURCE_CHANGED');
    files.set(relative, {path:relative, bytes:bytes.length, sha256:hash(bytes)});
    for (const match of bytes.toString('utf8').matchAll(/(?:^|;)\s*(?:import|export)\s+(?:[\w*{},\s]+?\s+from\s*)?['"](\.[^'"]+)['"]/gm)) {
      visit(path.posix.normalize(path.posix.join(path.posix.dirname(relative),match[1])));
    }
  }
  entries.forEach(visit);
  return [...files.values()].sort((a,b)=>a.path.localeCompare(b.path));
}

export async function createBridge(repositories) {
  const roots = Object.fromEntries(Object.keys(PINS).map(key=>[key,fs.realpathSync(path.resolve(repositories[key]))]));
  const sources = Object.fromEntries(Object.keys(PINS).map(key=>{
    const commit = execFileSync('git',['rev-parse','HEAD'],{cwd:roots[key],encoding:'utf8'}).trim();
    need(commit===PINS[key], 'CHECKOUT_PIN_'+key);
    return [key,{commit,files:sourceClosure(roots[key],ENTRIES[key])}];
  }));
  const load = (repo, file) => import(pathToFileURL(path.join(roots[repo],file)).href);
  const [project, work, record, discovery, manager, builder, jobs, fleet, worker] = await Promise.all([
    load('alpha',ENTRIES.alpha[0]),load('alpha',ENTRIES.alpha[1]),load('alpha',ENTRIES.alpha[2]),load('alpha',ENTRIES.alpha[3]),
    load('manager',ENTRIES.manager[0]),load('manager',ENTRIES.manager[1]),load('jobs',ENTRIES.jobs[0]),
    load('fleet',ENTRIES.fleet[0]),load('fleet',ENTRIES.fleet[1])
  ]);
  const canonical = (await load('alpha','docs/assets/successor/engine.mjs')).canonical;
  const built = builder.builderArtifacts();
  const context = {...built,validateNative:manager.validateBrowserAlpha};
  const options = {managerInspector:{source:built.managerSource,inspect:raw=>manager.inspectAlphaProject(raw,context)}};
  const bridgeSource={sha256:hash(fs.readFileSync(fileURLToPath(import.meta.url))),
    fleetLockSha256:hash(fs.readFileSync(path.join(roots.fleet,'fleet/package-lock.json'))),
    nodeVersion:process.version,managerSourceManifest:built.sourceManifest};
  const sourceHash = hash(JSON.stringify({sources,bridgeSource}));
  const source = file => ({repository:'MontrealAI/AGI-Alpha-Agent-v0',commit:PINS.alpha,path:file,sha256:sources.alpha.files.find(entry=>entry.path===file).sha256});
  const alphaSources = {mission:source(ENTRIES.alpha[2]),discovery:source(ENTRIES.alpha[3])};
  async function run({csv,missionId,projectId='writer4-enterprise',cycleId=missionId,unit='declared integer units',language='en',parentProject=null}) {
    const started = performance.now(), cpuStart=process.cpuUsage(), timing=[];
    const timed = async (stage, action) => {const start=performance.now(); const result=await action();timing.push({stage,elapsedMs:performance.now()-start});return result;};
    const spec=work.example('public-data');Object.assign(spec,{name:'Writer 4 bounded mission',language});spec.inputs={csv,unit};
    spec.rights={dataClass:'synthetic',source:'Writer 4 finite synthetic compiler output; provenance retained separately',license:'Apache-2.0'};
    let native=await record.createRecord({missionId,sourceHash,spec});
    const choices={family:'public-data',selection:'explicit-user-selection',duplicatePolicy:'sum-all-rows-no-deduplication',unitPolicy:'unchanged-integer-units',dataRights:'synthetic'};
    let alpha = parentProject ? await project.nextCycle(parentProject,{cycleId,record:native,choices,sourceHash,sources:alphaSources,expectedRevision:(await project.validateProject(parentProject)).revision})
      : await project.createProject({projectId,cycleId,sourceHash,discoveryBytes:canonical(await discovery.createBrief(project.publicDataOpportunity(),sourceHash)),record:native,choices,sources:alphaSources});
    const initialProject=canonical(alpha);
    const runId=missionId+'-local-run';
    native=await record.startRun(native,{expectedRevision:native.revision,runId});
    alpha=await project.appendRecord(alpha,native,{expectedRevision:alpha.revision,sourceHash,sources:alphaSources});
    const pack=await timed('Alpha exact public-data execution',()=>work.run(spec,{sourceHash}));
    native=await record.completeRun(native,pack,{expectedRevision:native.revision,runId});
    alpha=await project.appendRecord(alpha,native,{expectedRevision:alpha.revision,sourceHash,sources:alphaSources});
    const alphaRaw=canonical(alpha);
    let managerRaw=await timed('Manager explicit same-row mapping',()=>manager.importAlphaProject(alphaRaw,{language,mappingAcknowledgement:manager.MAPPING},context));
    managerRaw=await timed('Manager local exact-arithmetic candidate',()=>manager.advanceAlphaProject(managerRaw,{action:'run'},context));
    managerRaw=await timed('Manager separate unsigned USDC plan',()=>manager.advanceAlphaProject(managerRaw,{action:'select-and-draft',budget:'1'},context));
    const managerInspection=await manager.inspectAlphaProject(managerRaw,context);
    let jobsRaw=await timed('Jobs unfunded AGIALPHA work compilation',()=>jobs.importAlphaProject(managerRaw,{...options,amountBaseUnits:'1000000000000000000',compiledAt:'2026-10-23T00:00:00.000Z'}));
    jobsRaw=await timed('Jobs local source adapter execution',()=>jobs.runProjectTransfer(jobsRaw,options));
    const jobsInspection=await jobs.inspectProjectTransfer(jobsRaw,options);
    const fleetRaw=await timed('Fleet exact inherited project mapping',()=>fleet.createProjectRequest(jobsRaw,{language}));
    const fleetInspection=await fleet.inspectProjectRequest(fleetRaw);
    const execution=await timed('Fleet bounded worker function',()=>worker.perform('agent',fleetInspection.request.task));
    const task=fleetInspection.request.task;
    const reviewTask={...clone(task),action:'successor-check',input:{...clone(task.input),files:execution.files},review:'internal',sourceActor:randomUUID(),sourceController:randomUUID()};
    const review=await timed('Fleet separate internal checker function',()=>worker.perform('node',reviewTask));
    need(execution.checker.passed && review.checker.passed,'FLEET_CHECK_FAILED');
    need(alpha.projectId===jobsInspection.project.projectId && alpha.projectDigest===fleetInspection.request.project.projectDigest,'PROJECT_IDENTITY_LOST');
    return {schema:'writer4-four-repository-source-composition/v1',missionId,projectId:alpha.projectId,cycleId,
      status:'local-source-composition-executed',sourceHash,sources,bridgeSource,managerSourceVerification:built.identityVerification,
      originalMissionIdPreserved:JSON.parse(alpha.cycles.at(-1).records.at(-1).bytes).missionId===missionId,
      ancestry:alpha.cycles.map(c=>({cycleId:c.cycleId,parentCycleDigest:c.parentCycleDigest})),
      elapsedMs:performance.now()-started,cpuMicroseconds:process.cpuUsage(cpuStart),peakRSSKiB:process.resourceUsage().maxRSS,timing,
      scope:{nativeHostAdmission:'NOT_RUN',processIsolation:'NOT_TESTED',independentEconomicReview:false,settlement:'not-connected',authority:'none',fundsMoved:'0',providerCalls:0},
      routes:{manager:{currency:'USDC',decimals:6,plan:managerInspection.state.plans.at(-1)},jobs:{currency:'AGIALPHA',decimals:18,planning:jobsInspection.transfer.planning}},
      artifacts:{initialProject,alpha:alphaRaw,manager:managerRaw,jobs:jobsRaw,fleet:fleetRaw,execution,review,nativeRecord:canonical(native)},
      result:JSON.parse(pack.result.artifacts.find(file=>file.name==='analysis.json').content)};
  }
  async function inspectRestore(nativeRaw) {
    const original=await record.restoreRecord(nativeRaw,{sourceHash});
    const swapped=await record.restoreRecord(nativeRaw,{sourceHash:hash(sourceHash+'different-model')});
    const child=await record.importRecord(nativeRaw,{missionId:'restored-'+randomUUID(),sourceHash});
    return {original,swapped,child};
  }
  return {run,inspectRestore,sources,bridgeSource,sourceHash,modules:{project,record,worker,fleet,jobs,manager},context,options};
}

export {PINS};
