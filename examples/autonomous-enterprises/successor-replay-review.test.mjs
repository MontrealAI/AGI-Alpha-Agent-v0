// SPDX-License-Identifier: Apache-2.0
// Ordinary incorrect numeric receipts must retain known or unknown checker work without changing saved history.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as controller from './controller.mjs';
import * as workspace from '../successor-capability/workspace.mjs';
import {constructInverse} from './foundry.mjs';
import {qualifyArtifact} from './checker.mjs';
import {defaultCharter, digest, copy, auditSnapshot} from './protocol.mjs';

const source = {constructor: '1'.repeat(64), checker: '2'.repeat(64), closure: '3'.repeat(64)};
async function reservedSuccessor() {
    const charter = {...defaultCharter(source), maxN: 2, constructionLimit: 100_000,
        perTaskLimit: 100_000, taskLimit: 1};
    let value = await controller.start(await workspace.createWorkspace(), charter);
    for (let i = 0; i < 4; i++) value = await controller.next(value, {expectedSource: source, seed: 20261021});
    value = await controller.invokeReserved(value, source);
    for (let i = 0; i < 2; i++) value = await controller.next(value, {expectedSource: source});
    const persisted = await workspace.parseWorkspace(workspace.canonical(value));
    const {current} = await controller.state(persisted);
    assert.equal(current.state, 'SUCCESSOR_RESERVED');
    const construction = await constructInverse(current.bundle.transforms.at(-1).envelope,
        current.bundle.envelopes, qualifyArtifact, {reference: 'inherited',
            convolutionDigest: current.bundle.convolution.envelope.digest, kernel: ['5', '1']});
    assert.equal(construction.state, 'ACCEPTED');
    assert.deepEqual(construction.envelope.artifact.ast.spectrum, ['6', '4']);
    return {workspace: persisted, current, construction};
}
async function rejectAndPreserve(context, changed, expectedError) {
    changed.envelope.digest = await digest(changed.envelope.artifact);
    const beforeHistory = workspace.canonical(context.workspace);
    const before = auditSnapshot();
    await assert.rejects(workspace.recordEnterpriseEvent(context.workspace, 'enterprise-successor', {
        attempt: context.current.attempt, construction: changed, parentFreezeDigest: context.current.freeze.digest
    }), expectedError);
    const after = auditSnapshot();
    assert.equal(workspace.canonical(context.workspace), beforeHistory);
    const retained = (await controller.state(context.workspace)).current;
    assert.equal(retained.state, 'SUCCESSOR_RESERVED');
    assert.equal(retained.successorSpent, 'unknown-reservation-retained');
    assert.equal(retained.successor, undefined);
    return {before, after};
}

test('incorrect nonzero spectrum returns a fully counted negative certificate without erasing history', async () => {
    const context = await reservedSuccessor(), changed = copy(context.construction);
    changed.envelope.artifact.ast.spectrum[0] = '7';
    const {before, after} = await rejectAndPreserve(context, changed, /qualification|receipts/i);
    assert.ok(after.successorReplayWork > before.successorReplayWork);
    assert.equal(after.rejectedReplaysWithUnknownPartialWork, before.rejectedReplaysWithUnknownPartialWork);
});

test('stale successor operating bound retains partial checker work when current qualification throws', async () => {
    const context = await reservedSuccessor(), changed = copy(context.construction);
    changed.envelope.artifact.operatingWork += 1;
    const {before, after} = await rejectAndPreserve(context, changed, /operating-work bound/i);
    assert.equal(after.rejectedReplaysWithUnknownPartialWork, before.rejectedReplaysWithUnknownPartialWork + 1);
    assert.equal(after.failedReplayWork, 'UNKNOWN_PARTIAL_WORK_RETAINED');
    assert.equal(after.successorReplayWork, before.successorReplayWork);
});

test('a conservative known-zero construction refusal releases its unused reservation for same-mission reentry', async () => {
    const charter = {...defaultCharter(source), maxN: 2, constructionLimit: 0, perTaskLimit: 100_000};
    const started = await controller.start(await workspace.createWorkspace(), charter);
    const refused = await controller.next(started, {expectedSource: source});
    const row = (await controller.state(refused)).history.at(-1);
    assert.equal(row.state, 'INCONCLUSIVE');
    assert.equal(row.actualConstructionWork, 0); assert.equal(row.unknownSpent, false);
    assert.equal(row.unresolvedReservation, false); assert.equal(row.bundle, undefined);
    const resumed = await controller.start(refused, {...charter, constructionLimit: 100_000});
    assert.equal((await controller.state(resumed)).current.state, 'RESERVED');
    assert.equal(workspace.canonical(resumed.events.slice(0, refused.events.length)), workspace.canonical(refused.events));
});
