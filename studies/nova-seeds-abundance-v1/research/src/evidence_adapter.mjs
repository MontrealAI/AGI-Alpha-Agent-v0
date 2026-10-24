// SPDX-License-Identifier: Apache-2.0
import {createHash} from 'node:crypto';
import {generateSigningIdentity,trustKey,signPayload,verifySignedPayload} from '../vendor/jobs/packages/successor-core/src/signatures.mjs';
import {OutcomeLedger,verifyLedger} from '../vendor/fleet/fleet/successor/outcomes.mjs';

const digest=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const stamp=n=>new Date(n).toISOString();
export function missionRecorder(directory,mission) {
  const identity=generateSigningIdentity({keyId:'research-local-recorder',organizationId:'nova-seeds-research',custodyId:'same-process-fixture',fixture:true});
  const context={institutionId:'nova-seeds-research',missionId:mission.id,environment:'local-synthetic-allocation',mode:'fixture'};
  const now=Date.now(),trustStore={schemaVersion:1,keys:[trustKey(identity,{roles:['recorder'],context,notBefore:stamp(now-1000),expiresAt:stamp(now+3600000),maxIndependence:'I0'})]};
  const purpose='nova-seeds-execution-evidence/v1',ledger=new OutcomeLedger(directory);
  return {publicTrust:trustStore,
    async append(method,result,outcome){
      const started=performance.now(),cpuBefore=process.cpuUsage();
      const payload={schema:'nova-seeds-execution-evidence/v1',missionDigest:digest(mission),method,plan:result.plan,
        artifactType:result.completionHash?'native-finite-model-completion':'finite-schedule-and-replay',
        artifactHash:result.completionHash||digest({mission,plan:result.plan,objective:result.objective}),outcomeDigest:digest(outcome),authority:'fixture-only',physicalTruthEstablished:false};
      const signed=await signPayload(payload,{identity,purpose,context,issuedAt:stamp(now)});
      await verifySignedPayload(signed,{trustStore,purpose,role:'recorder',context,now});
      const attempt=digest({mission:mission.id,method}),evidenceSha256=digest(signed),data={state:'completed',projectSha256:digest(mission),method,inputHashes:[digest(mission)],outputHashes:[evidenceSha256],runtimeSha256:digest({node:process.version})};
      ledger.append({attempt,type:'attempt',at:now,evidenceSha256,data});
      ledger.append({attempt,type:'cost',at:now,evidenceSha256,data:{id:'monetary-and-human-cost',category:'compute',basis:'unknown',currency:'USD',amountMicros:null,billingReferenceSha256:null}});
      const records=ledger.read();verifyLedger(records);
      return {signed,publicTrust:trustStore,ledgerHead:records.at(-1).sha256,ledgerRecords:records.length,receiptBytes:Buffer.byteLength(JSON.stringify(signed)),wallMs:performance.now()-started,cpuMicros:process.cpuUsage(cpuBefore)};
    },close(){identity.privateKey=null;return ledger.read();}};
}
