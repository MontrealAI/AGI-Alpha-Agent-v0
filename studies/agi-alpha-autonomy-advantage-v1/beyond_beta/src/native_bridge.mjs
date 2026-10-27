// SPDX-License-Identifier: Apache-2.0
// Thin inert projection adapter; no new runtime, model call or settlement path.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {projectBatch, SCHEMA as NATIVE_BATCH_SCHEMA} from '../../venture_creation/src/native_integration.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const sha=value=>createHash('sha256').update(value).digest('hex');
const canonical=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
const requireCondition=(condition,message)=>{if(!condition)throw Error(message);};
export const SCHEMA='beyond-beta-native-input/v1';

export function projectBeyondBeta(batch){
  requireCondition(batch?.schema===SCHEMA&&Array.isArray(batch.worlds),'Explicit BeyondBeta native input required');
  const worlds=batch.worlds.map(world=>{
    requireCondition(typeof world.id==='string'&&world.id.length,'World identity required');
    requireCondition(/^[a-f0-9]{64}$/.test(world.graphAuditRoot),'Executed graph audit commitment required');
    requireCondition(world.projection&&Array.isArray(world.authorityChecks),'Projection and explicit fixture authority checks required');
    // No historical study qualification rules are invoked: BeyondBeta admission
    // has already executed in graph_lifecycle.py against its own frozen contract.
    return {id:world.id,projection:world.projection,authorityChecks:world.authorityChecks};
  });
  const native=projectBatch({schema:NATIVE_BATCH_SCHEMA,worlds});
  const ownSource={path:'beyond_beta/src/native_bridge.mjs',sha256:sha(fs.readFileSync(path.join(ROOT,'beyond_beta/src/native_bridge.mjs')))};
  return {schema:'beyond-beta-native-results/v1',inputSha256:sha(canonical(batch)),sources:[ownSource,...native.sources],
    worlds:native.worlds.map((world,i)=>({...world,graphAuditRoot:batch.worlds[i].graphAuditRoot,graphSourceHash:batch.worlds[i].graphSourceHash??null})),
    measuredExecution:native.measuredExecution,
    boundaries:{actualCollectionsUsd:0,actualCompleteCostUsd:null,actualModelCalls:0,liveIdentityAuthenticated:false,livePermissions:false,
      nativeModule:'Unchanged native_snapshot/canonical/shadow-ledger.mjs planMission',
      authorityModule:'Unchanged direct-agent fixture authorityStatus; no live ENS or EIP-712 verification',
      existingClubValidation:'UNCHANGED; no club settlement path invoked',
      scope:'Executed inert native cash/accrual reconciliation and fixture eligibility only. BeyondBeta graph gates execute separately. This is not actual model production or commercial acceptance.',
      historicalQualificationRulesInvoked:false}};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const [inputFile,outputFile]=process.argv.slice(2);
  requireCondition(inputFile&&outputFile&&process.argv.length===4,'Usage: node beyond_beta/src/native_bridge.mjs INPUT.json NEW_OUTPUT.json');
  requireCondition(!fs.existsSync(outputFile),'Refuse to overwrite native evidence');
  const input=fs.readFileSync(inputFile),output=projectBeyondBeta(JSON.parse(input));
  output.inputFileSha256=sha(input);
  fs.writeFileSync(outputFile,JSON.stringify(output,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({outputFile,...output.measuredExecution}));
}
