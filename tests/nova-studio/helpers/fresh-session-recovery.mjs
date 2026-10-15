// SPDX-License-Identifier: Apache-2.0
// A separate Node process models loss of all in-process verification tokens.
// It does not model a physical device, a browser crash, RPC finality or live funds.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { WalletSession } from '../../../docs/assets/ascension-wallet/session.mjs';
import { NovaWorkflow } from '../../../docs/assets/nova-studio/workflow.mjs';
import { projectCycleState } from '../../../docs/assets/nova-studio/cycle.mjs';

const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const values = new Map(), calls = [];
const storage = { getItem:key=>values.get(key)??null, setItem:(key,value)=>values.set(key,value) };
const locks = { request:async(_name,_options,callback)=>callback({}) };
const session = new WalletSession(input.profile, storage, locks);
const flow = new NovaWorkflow(session, {
  publish:async()=>{ throw Error('Recovery must not upload.'); },
  retrieve:async()=>{ throw Error('Recovery must not silently refresh an external service.'); },
});
globalThis.fetch = async()=>{ throw Error('Recovery must not access the network.'); };
assert.equal(session.client.provider, null);
await flow.restoreProject(input.kit, input.passphrase);
assert.equal(session.client.provider, null);
assert.equal(session.client.account, null);
assert.equal(flow.project.projectId, input.project.projectId);
assert.deepEqual(flow.project, input.project);
assert.equal(flow.preview, null);
assert.equal(flow.observation, null);
for (const key of ['runtimeResult','runtimeTrust','runtimeSettlement','runtimeEvaluation','runtimeReuse','nativeDelivery'])
  assert.equal(flow[key], null, `${key} must not survive as current authority.`);
assert.equal(flow.runtimeTerms.size, 0);
assert.equal(flow.verifiedRoutes.size, 0);
const state = projectCycleState(flow.project);
assert.equal(state.fresh, false);
assert.equal(state.runtime, 'requires-current-authorization');
assert.equal(state.settlement, 'not-observed');
assert.equal(state.improvement, 'not-adopted');
for (const cycle of flow.project.cycles) {
  for (const record of cycle.signedRecords) assert.equal(record.trust, 'historical-unverified');
  for (const mission of cycle.missions) assert.equal(mission.authority, 'requires-new-grant');
}
if (input.pending) {
  assert.equal(session.client.pending.status, 'submission-unknown');
  assert.equal(session.client.pending.effectVerified, false);
  await assert.rejects(flow.prepare('reclaim', {}), /outstanding/);
  await assert.rejects(flow.create(input.draft, input.passphrase), /outstanding/);
  await assert.rejects(flow.nextCycle(input.draft, input.passphrase), /outstanding/);
}
// A provider is never attached or consulted. A restored export alone cannot send.
assert.equal(calls.length, 0);
process.stdout.write(JSON.stringify({point:input.point,restored:true,pending:input.pending,
  currentAuthority:false,providerAttached:false,networkRequests:0,automaticEffects:0}));
