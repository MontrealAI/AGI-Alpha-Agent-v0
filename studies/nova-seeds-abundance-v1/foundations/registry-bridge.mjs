import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {generateSigningIdentity, trustKey, signPayload, verifySignedPayload} from './vendor/jobs/packages/successor-core/src/signatures.mjs';
import {canonicalize} from './vendor/jobs/packages/successor-core/src/integrity.mjs';
import {OutcomeLedger, verifyLedger, summarizeOutcomes} from './vendor/fleet/fleet/successor/outcomes.mjs';

const digest = value => crypto.createHash('sha256').update(canonicalize(value)).digest('hex');
const stamp = ms => new Date(ms).toISOString();
export async function runRegistryBridge(payload, {missionId = 'nova-seeds-research-local-v1', now = Date.now()} = {}) {
  const context = {institutionId:'nova-seeds-research-fixture',missionId,environment:'local-synthetic-research',mode:'fixture'};
  const identity = generateSigningIdentity({keyId:'ephemeral-local-receipt-key',organizationId:'single-research-operator',custodyId:'same-process-fixture',fixture:true});
  const trust = trustKey(identity,{roles:['research-recorder'],context,notBefore:stamp(now-1000),expiresAt:stamp(now+60000),maxIndependence:'I0'});
  const trustStore = {schemaVersion:1,keys:[trust]}, purpose = 'nova-seeds-synthetic-execution-receipt/v1';
  const start = performance.now(), record = await signPayload(payload,{identity,purpose,context,issuedAt:stamp(now)}), signMs = performance.now()-start;
  const checkStart = performance.now();
  const checked = await verifySignedPayload(record,{trustStore,purpose,role:'research-recorder',context,now});
  const verifyMs = performance.now()-checkStart;
  assert.deepEqual(checked.payload,payload);
  const negatives = [];
  async function rejects(name, alteredRecord = record, alteredOptions = {}) {
    try {await verifySignedPayload(alteredRecord,{trustStore,purpose,role:'research-recorder',context,now,...alteredOptions});}
    catch(error) {negatives.push({case:name,rejected:true,code:error.code});return;}
    throw Error('Unexpected verification success: '+name);
  }
  await rejects('payload-tamper',{...record,payload:{...payload,adversarialAlteration:true}});
  await rejects('cross-mission-replay',record,{context:{...context,missionId:missionId+'-successor'}});
  await rejects('expired-key',record,{now:now+60001});
  await rejects('wrong-purpose',record,{purpose:'production-authority'});
  await rejects('untrusted-signer',record,{trustStore:{schemaVersion:1,keys:[]}});
  await rejects('revoked-key',record,{trustStore:{schemaVersion:1,keys:[{...trust,revokedAt:stamp(now-1)}]}});
  const falsePayload = {...payload,syntheticPhysicalTruth:false,claim:'An operator may sign a false assertion.'};
  const falseRecord = await signPayload(falsePayload,{identity,purpose,context,issuedAt:stamp(now)});
  const falseAccepted = await verifySignedPayload(falseRecord,{trustStore,purpose,role:'research-recorder',context,now});
  assert.deepEqual(falseAccepted.payload,falsePayload);
  const directory = fs.mkdtempSync(path.join(os.tmpdir(),'nova-seeds-ledger-'));
  let observations, summary, ledgerTamperRejected;
  try {
    const ledger = new OutcomeLedger(directory), attempt = digest({missionId,payload});
    const evidenceSha256 = digest(record), stateData = state => ({state,projectSha256:digest(context),method:'nova-seeds-research-local-v1',inputHashes:[digest(payload)],outputHashes:state==='completed'?[evidenceSha256]:[],runtimeSha256:digest({node:process.version})});
    ledger.append({attempt,type:'attempt',at:now,evidenceSha256,data:stateData('reserved')});
    ledger.append({attempt,type:'cost',at:now,evidenceSha256,data:{id:'attributable-human-and-provider-cost',category:'compute',basis:'unknown',currency:'USD',amountMicros:null,billingReferenceSha256:null}});
    ledger.append({attempt,type:'attempt',at:now+1,evidenceSha256,data:stateData('completed')});
    ledger.append({attempt,type:'review',at:now+1,evidenceSha256,data:{verdict:'accepted',control:'internal',deliverySha256:digest(payload),eligibilityEvidenceSha256:null}});
    observations = new OutcomeLedger(directory).read();
    summary = summarizeOutcomes(observations);
    const altered = structuredClone(observations); altered[0].event.data.method = 'tampered';
    try {verifyLedger(altered); ledgerTamperRejected=false;} catch {ledgerTamperRejected=true;}
    assert.equal(ledgerTamperRejected,true);
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
  identity.privateKey = null;
  return {schema:'nova-seeds-foundations-bridge/v1',scope:'Actual Jobs signature and Fleet ledger modules; local fixture, no external execution or authority.',context,record,trustStore,signMs,verifyMs,receiptBytes:Buffer.byteLength(canonicalize(record)),negativeTests:negatives,ledgerTamperRejected,falseSignedAssertionAccepted:true,physicalTruthEstablished:false,independence:'I0',persistentPrivateKeys:false,observations,summary};
}
if(process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
  const payload=process.argv[2]?JSON.parse(fs.readFileSync(process.argv[2],'utf8')):{schema:'nova-seeds-placeholder-fixture/v1',purpose:'Integration API exercise only; actual experiment payload must be separately supplied.'};
  console.log(JSON.stringify(await runRegistryBridge(payload),null,2));
}
