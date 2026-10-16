// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import {canonical} from '../../docs/assets/successor/engine.mjs';
import * as native from '../successor-workbench/mission-record.mjs';
import {example,run} from '../successor-workbench/engine.mjs';
import {createBrief} from '../alpha-discovery/engine.mjs';
import * as projects from './engine.mjs';
const manifest=JSON.parse(fs.readFileSync(new URL('../../docs/successor/mission/sources.json',import.meta.url),'utf8'));
export const sourceHash=manifest.sourceHash;
const source=path=>({repository:'MontrealAI/AGI-Alpha-Agent-v0',commit:'021b3337de07e9a0cdd105fac967a0dc650de122',path,sha256:manifest.sources[path]});
export const sources={discovery:source('examples/alpha-discovery/engine.mjs'),mission:source('examples/successor-workbench/mission-record.mjs')};
const choices={family:'public-data',selection:'explicit-user-selection',duplicatePolicy:'sum-all-rows-no-deduplication',unitPolicy:'unchanged-integer-units',dataRights:'synthetic'};
export async function fixture(language='en',id='guided-project'){
  const spec=example('public-data');spec.language=language;
  let record=await native.createRecord({missionId:id+'-mission',sourceHash,spec});
  let project=await projects.createProject({projectId:id,cycleId:id+'-first-cycle',sourceHash,record,discoveryBytes:canonical(await createBrief(projects.publicDataOpportunity(),sourceHash)),choices,sources});
  const append=r=>projects.appendRecord(project,r,{expectedRevision:project.revision,sourceHash,sources});
  record=await native.startRun(record,{expectedRevision:0,runId:id+'-first-run'});project=await append(record);
  record=await native.completeRun(record,await run(spec,{sourceHash}),{expectedRevision:record.revision,runId:record.run.runId});project=await append(record);
  record=await native.reviewRecord(record,{expectedRevision:record.revision,decision:'rejected',note:'Retain rejected comparison: no independent qualification or measured economic advantage.'});project=await append(record);
  return project;
}
export async function freshCycle(project){
  const spec=example('public-data');spec.inputs.csv='group,amount\nChanged,14\nChanged,-4\nOther,2\n';
  const previous=JSON.parse(project.cycles.at(-1).records.at(-1).bytes);spec.language=previous.spec.language;
  const record=await native.createRecord({missionId:project.projectId+'-next-mission',sourceHash,spec});
  let next=await projects.nextCycle(project,{cycleId:project.projectId+'-next-cycle',record,choices,sourceHash,sources,recovered:true,expectedRevision:project.revision});
  const running=await native.startRun(record,{expectedRevision:0,runId:project.projectId+'-next-run'});
  next=await projects.appendRecord(next,running,{expectedRevision:next.revision,sourceHash,sources});
  const result=await native.completeRun(running,await run(spec,{sourceHash}),{expectedRevision:running.revision,runId:running.run.runId});
  return projects.appendRecord(next,result,{expectedRevision:next.revision,sourceHash,sources});
}
