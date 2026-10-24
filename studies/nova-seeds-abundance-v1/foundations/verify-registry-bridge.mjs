import fs from 'node:fs';
import assert from 'node:assert/strict';
import {verifySignedPayload} from './vendor/jobs/packages/successor-core/src/signatures.mjs';
import {verifyLedger, summarizeOutcomes} from './vendor/fleet/fleet/successor/outcomes.mjs';

const report = JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
assert.equal(report.schema,'nova-seeds-foundations-bridge/v1');
assert.equal(report.context.mode,'fixture');
const historicalTime=Date.parse(report.record.issuedAt);
const result=await verifySignedPayload(report.record,{trustStore:report.trustStore,purpose:'nova-seeds-synthetic-execution-receipt/v1',role:'research-recorder',context:report.context,now:historicalTime});
verifyLedger(report.observations);
assert.deepEqual(summarizeOutcomes(report.observations),report.summary);
console.log(JSON.stringify({validHistoricalSignature:true,verifiedAtHistoricalTime:report.record.issuedAt,currentAuthority:'none',trust:'Published local fixture key, not independently authenticated production custody.',recordDigest:result.digest,ledgerRecords:report.observations.length,physicalTruthEstablished:false},null,2));
