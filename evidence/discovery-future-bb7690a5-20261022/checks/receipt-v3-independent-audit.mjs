import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import * as contract from '../alpha/examples/successor-capability/discovery-lab-contract.mjs';
import * as workspace from '../alpha/examples/successor-capability/workspace.mjs';
import * as history from '../alpha/examples/successor-capability/discovery-lab-history.mjs';
import * as evidence from '../alpha/examples/successor-capability/discovery-lab-evidence-history.mjs';
import * as receipts from '../alpha/examples/successor-capability/discovery-lab-receipts.mjs';
import * as docket from '../alpha/examples/successor-capability/discovery-lab-docket.mjs';
import {createInspector} from '../alpha/examples/successor-capability/discovery-lab-inspector.mjs';
import * as manager from '../manager-review/current/scripts/integrations/discovery-lab-work-request.mjs';
const root='/workspace/scratch/32717074a7f1';
const sourcePath=root+'/alpha/examples/successor-capability/discovery-lab-receipts.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const expected='dcff0519c680fac180d24ade5a02eb415a9ee950220c09d693bb2145d47de521';
assert.equal(sha(fs.readFileSync(sourcePath)),expected);
const wrapper=JSON.parse(fs.readFileSync('/dev/shm/discovery-native-receipt-current6/manager-wrapper.json','utf8'));
const saved=await workspace.parseWorkspace(fs.readFileSync('/dev/shm/discovery-continuation-current6/browser-workspace.json','utf8'));
const inspected=await workspace.inspectWorkspace(saved), retained=JSON.parse(wrapper.raw);
const campaign=inspected.discovery.campaigns.find(c=>contract.canonical(c.bindings)===contract.canonical(retained.bindings));
const context=receipts.makeReceiverContext(campaign), original=await receipts.inspectReceiverReceipt(wrapper,context);
const settle=receipt=>{
  for(let index=0;index<16;index++) {
    receipt.resources.receiverUsed.storageBytes=Buffer.byteLength(JSON.stringify(receipt));
    for(const key of contract.RESOURCE_KEYS.filter(key=>key!=='elapsedMs')) receipt.resources.totalUsed[key]
      =receipt.resources.receiverUsed[key]+receipt.resources.checkerUsed[key];
  }
  return {raw:JSON.stringify(receipt),source:wrapper.source};
};
const changes=[
  ['units-equal-bytes',r=>{r.resources.units='x'+r.resources.units.slice(1);}],
  ['native-accepted-false-after-complete-prefix',r=>{r.checker.report.accepted=false;r.checker.report.reasons=['ELAPSED_REPLAY_CHECK_INCOMPLETE'];r.state='inconclusive';}],
  ['permissive-native-memory',r=>{r.checker.report.resourceUsed.memoryBytes++;r.resources.checkerUsed.memoryBytes++;}],
  ['elapsed-free-change',r=>{r.resources.receiverUsed.elapsedMs+=10;r.resources.checkerUsed.elapsedMs+=10;r.checker.report.resourceUsed.elapsedMs+=10;r.resources.totalUsed.elapsedMs=r.resources.receiverUsed.elapsedMs+r.resources.checkerUsed.elapsedMs;}],
  ['receiver-search-reservation',r=>{r.resources.receiverReservation.search++;r.resources.nativeLimits.search--;}],
  ['derived-outcome-flipped-by-receiver-memory',r=>{r.resources.receiverUsed.memoryBytes=JSON.parse(r.original).resourceLimits.memoryBytes+1;r.checker.withinResourceEnvelope=false;r.state='inconclusive';}]
];
const withOriginal=await workspace.recordDiscoveryEvent(saved,'lab-evidence-attached',await evidence.evidencePayload(campaign.campaignDigest,'receiver-receipt',wrapper));
const variants=[];
for(const [name,change] of changes) {
  const altered=JSON.parse(wrapper.raw);change(altered);const input=settle(altered);
  const checked=await receipts.inspectReceiverReceipt(input,context);
  assert.equal(checked.receiptId,original.receiptId,name);assert.notEqual(checked.receiptDigest,original.receiptDigest,name);
  await assert.rejects(workspace.recordDiscoveryEvent(withOriginal,'lab-evidence-attached',await evidence.evidencePayload(campaign.campaignDigest,'receiver-receipt',input)),/Duplicate semantic receipt/);
  const external=await docket.emptyDocketAttachments(saved);external.receipts=[wrapper,input];
  await assert.rejects(docket.createDiscoveryDocket(saved,external),/repeats a semantic receipt/);
  const combined=await docket.emptyDocketAttachments(withOriginal);combined.receipts=[input];
  await assert.rejects(docket.createDiscoveryDocket(withOriginal,combined),/repeats a semantic receipt/);
  variants.push({name,admittedIndividually:true,state:checked.state,semanticReceiptId:checked.receiptId,rawDigest:checked.receiptDigest,checking:checked.resources.checking,historyDuplicateRefused:true,externalDuplicateRefused:true,combinedDuplicateRefused:true});
}
const sources=Object.fromEntries(['modelDigest','sourceDigest','evaluatorDigest'].map(key=>[key,campaign.bindings[key]]));
const inspect=createInspector(sources);
const expectedBindings=Object.fromEntries(contract.BINDING_KEYS.map(key=>[key,campaign.bindings[key]]));
const limits=JSON.parse(retained.original).resourceLimits;
async function receive(stage,preflight=false) {
  const request=await history.workRequest(campaign,'USDC',limits);
  request.stage=stage;request.inputArtifacts=campaign.artifacts.slice(0,contract.STAGES.indexOf(stage)).map(artifact=>artifact.digest);
  const receipt=await manager.receiveDiscoveryLabWorkRequest(contract.canonical(request),{expectedBindings,
    expectedCommission:Object.fromEntries(['id','branch','route'].map(key=>[key,request.commission[key]])),
    inspectCampaign:preflight?(payload,options)=>inspect(payload,{...options,limits:{...options.limits,checking:9999}}):inspect});
  return {raw:JSON.stringify(receipt),source:wrapper.source};
}
const executed=[await receive('evolve',true),await receive('evolve'),await receive('learn')];
let retainedExecutions=saved;const executions=[];
for(const input of executed) {
  const checked=await receipts.inspectReceiverReceipt(input,context);
  retainedExecutions=await workspace.recordDiscoveryEvent(retainedExecutions,'lab-evidence-attached',await evidence.evidencePayload(campaign.campaignDigest,'receiver-receipt',input));
  executions.push({state:checked.state,stage:JSON.parse(input.raw).stage,semanticReceiptId:checked.receiptId,checking:checked.resources.checking});
}
assert.deepEqual(executions.map(item=>item.state),['inconclusive','local-checked','local-checked']);
assert.equal(new Set(executions.map(item=>item.semanticReceiptId)).size,3);
const exported=await docket.createDiscoveryDocket(retainedExecutions);
const costs=JSON.parse(exported.files['08_cost_ledgers/costs.json']);
assert.equal(costs.receiverInspectionByRoute['manager-usdc'].checking,254030);
assert.equal(costs.commissions[0].alternatives[0].inspectionReceiptIds.length,3);
assert.equal((await docket.verifyDiscoveryDocket(exported,{expectedWorkspaceHead:(await workspace.inspectWorkspace(retainedExecutions)).head,expectedReceiverSources:[wrapper.source]})).verified,true);
assert.equal(sha(fs.readFileSync(sourcePath)),expected);
const result={schema:'discovery-lab/independent-v3-receipt-identity-audit/v1',node:process.version,moduleSha256:expected,
  scope:'Six adversarial variants of retained actual current6 native evidence; three new actual local Manager adapter plus Alpha inspector calls. No fresh complete Git custody, installed-package, hosted, external institutional or operational qualification. Unknown invocation multiplicity is not repaired by these identities.',
  original:{semanticReceiptId:original.receiptId,rawDigest:original.receiptDigest},variants,
  actualNativeExecutions:{executions,distinctIds:3,ledgerChecking:254030,trustedHeadAndSourceDocketVerification:true},
  authority:'none'};
fs.writeFileSync(root+'/review-tools/receipt-v3-independent-audit.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
