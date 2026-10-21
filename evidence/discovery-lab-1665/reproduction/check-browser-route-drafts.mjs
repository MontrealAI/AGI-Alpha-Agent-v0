import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {capturePinnedAlpha,boundedSource,assertStrongerSuccessor} from '../manager-lab/scripts/integrations/discovery-lab-native-test.mjs';
import {receiveDiscoveryLabWorkRequest as manager} from '../manager-lab/scripts/integrations/discovery-lab-work-request.mjs';
import {receiveDiscoveryLabWorkRequest as jobs} from '../jobs-lab/integrations/alpha-agent/discovery-lab-work-request.mjs';
import {canonical,parseBounded,BINDING_KEYS,RESOURCE_KEYS} from '../manager-lab/scripts/integrations/discovery-lab-contract.mjs';
assert.ok(process.argv.length===6||process.argv.length===7,'Usage: node proof.mjs /absolute/alpha /workspace.json /manager-draft.json /jobs-draft.json [trusted-selected-campaign-digest]');
if(process.argv[6])assert.match(process.argv[6],/^[0-9a-f]{64}$/);
const sha=x=>createHash('sha256').update(x).digest('hex');
const workspaceBytes=boundedSource(path.resolve(process.argv[3]));
const pinManager=fs.readFileSync(new URL('../manager-lab/config/discovery-lab-alpha-source.json',import.meta.url));
assert.ok(pinManager.equals(fs.readFileSync(new URL('../jobs-lab/config/discovery-lab-alpha-source.json',import.meta.url))));
const installed=capturePinnedAlpha(process.argv[2]);
try{
 const load=name=>import(pathToFileURL(path.join(installed.directory,'examples/successor-capability/'+name+'.mjs')).href);
 const [workspace,history,{createInspector}]=await Promise.all([load('workspace'),load('discovery-lab-history'),load('discovery-lab-inspector')]);
 const saved=await workspace.parseWorkspace(workspaceBytes.toString('utf8'));
 const view=await workspace.inspectWorkspace(saved),campaigns=view.discovery.campaigns;
 const first=campaigns.find(record=>record.state==='accepted');
 const selected=process.argv[6]?campaigns.find(record=>record.state==='accepted'&&record.campaignDigest===process.argv[6]):campaigns.filter(record=>record.state==='accepted').at(-1);
 assert.ok(selected,'Independently selected accepted campaign must exist in the actual workspace');
 if(selected.campaignDigest!==first.campaignDigest)assertStrongerSuccessor(first,selected);
 const limits={acquisitions:0,search:0,checking:10000,memoryBytes:10000000,storageBytes:4000000,workerCapacity:4,installations:0,elapsedMs:120000};
 for(let record=selected;record;record=record.parent)for(const key of ['acquisitions','search','checking','installations'])limits[key]+=record.charter.budget[key];
 assert.ok(RESOURCE_KEYS.every(key=>Number.isSafeInteger(limits[key])));
 const inspectCampaign=createInspector(installed.sources),outcomes=[];
 for(const [route,receiver,file] of [['USDC',manager,process.argv[4]],['AGIALPHA',jobs,process.argv[5]]]){
  const original=boundedSource(path.resolve(file)).toString('utf8');
  const actual=parseBounded(original),expected=await history.workRequest(selected,route,limits);
  assert.equal(canonical(actual),canonical(expected),'Unmodified browser export must equal independently reconstructed installed context/envelope');
  const receipt=await receiver(original,{expectedBindings:Object.fromEntries(BINDING_KEYS.map(key=>[key,selected.bindings[key]])),
   expectedCommission:Object.fromEntries(['id','branch','route'].map(key=>[key,expected.commission[key]])),inspectCampaign});
  assert.equal(receipt.state,'local-checked');assert.equal(receipt.original,original);assert.equal(receipt.requestSha256,sha(original));
  assert.equal(receipt.authority,'none');assert.equal(receipt.lifecycle.commission,'DRAFT_NOT_SUBMITTED');assert.equal(receipt.commission.capBaseUnits,'0');
  outcomes.push({route,originalFileSha256:sha(original),originalUtf8Bytes:Buffer.byteLength(original),receipt});
 }
 assert.deepEqual(outcomes[0].receipt.bindings,outcomes[1].receipt.bindings);
 assert.equal(outcomes[0].receipt.commission.id,outcomes[1].receipt.commission.id);
 assert.notEqual(outcomes[0].receipt.commission.branch,outcomes[1].receipt.commission.branch);
 assert.notEqual(outcomes[0].receipt.commission.route,outcomes[1].receipt.commission.route);
 console.log(JSON.stringify({schema:'successor/discovery-lab-browser-route-proof/v1',scope:'Unmodified actual browser exports through current pinned native inspector and both actual receivers; zero-cap local inspection only.',
  alphaCommit:installed.pin.commit,alphaTree:installed.pin.tree,sourceHash:installed.pin.sourceHash,coldSourceCustody:installed.custody,
  inputWorkspaceFileSha256:sha(workspaceBytes),canonicalWorkspaceDigest:sha(canonical(saved)),selectedCampaignDigest:selected.campaignDigest,selectedContext:process.argv[6]?'explicit-independent-selection':'latest-accepted-stronger',
  historyStates:campaigns.map(record=>record.state),retainedWorkspace:saved,outcomes,authority:'none',externalExecution:'unprovisioned'},null,2));
}finally{installed.dispose();}
