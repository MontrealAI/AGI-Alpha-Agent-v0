// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as workspace from './workspace.mjs';
import * as history from './discovery-lab-history.mjs';
import * as evidence from './discovery-lab-evidence-history.mjs';
import * as future from './discovery-lab-future.mjs';
import * as runtime from './discovery-lab.mjs';
import {canonical} from './discovery-lab-contract.mjs';
const sources = {modelDigest: '1'.repeat(64), sourceDigest: '2'.repeat(64), evaluatorDigest: '3'.repeat(64)};
async function initial() {
    let value = await workspace.createWorkspace();
    const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sources);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const result = runtime.runCampaign(start.charter);
    const verification = runtime.verifyCampaign(start.charter, result);
    value = await workspace.recordDiscoveryEvent(value, 'lab-completed',
        await history.completedPayload(start.attempt, result, 1, verification.verificationResources));
    const record = (await workspace.inspectWorkspace(value)).discovery.campaigns[0];
    return {value, record};
}
const append = (value, campaign, kind, record) => evidence.evidencePayload(campaign.campaignDigest, kind, record)
    .then(payload => workspace.recordDiscoveryEvent(value, 'lab-evidence-attached', payload));
test('freeze, separate bank and actual invocation persist in the same replayed mission chain', async () => {
    let {value, record} = await initial();
    const original = canonical(value), capsule = await evidence.freezeRecord(record);
    value = await append(value, record, 'future-freeze', evidence.freezeReference(capsule));
    const bank = await future.publicFutureBank(capsule, 7);
    value = await append(value, record, 'future-task-bank', bank);
    value = await append(value, record, 'future-run-reserved', {schema: 'discovery-lab-future-reservation/v1',
        taskBankDigest: bank.digest, perTaskWorkLimit: 50, attempt: 'future-' + crypto.randomUUID()});
    const report = await future.evaluateFutureTasks(capsule, bank, {perTaskWorkLimit: 50});
    value = await append(value, record, 'future-evaluation', report);
    const reopened = await workspace.parseWorkspace(canonical(value));
    const checked = await workspace.inspectWorkspace(reopened);
    assert.deepEqual(checked.discovery.attachments.map(item => item.kind),
        ['future-freeze', 'future-task-bank', 'future-run-reserved', 'future-evaluation']);
    assert.equal(canonical({...value, revision: 2, events: value.events.slice(0, 3)}), original);
    assert.equal(checked.discovery.attachments.at(-1).authority, false);
    assert.ok(report.runs.some(run => run.status === 'inconclusive'));
    assert.ok(report.runs.some(run => run.invocations?.some(item => item.action === 'invoke-frozen-response-table')));
    await assert.rejects(append(value, record, 'future-evaluation', report), /Duplicate|completed protocol/);
});
test('out-of-order, swapped source and altered future outcomes cannot enter the chain', async () => {
    let {value, record} = await initial();
    const capsule = await evidence.freezeRecord(record), bank = await future.publicFutureBank(capsule, 1);
    await assert.rejects(append(value, record, 'future-task-bank', bank), /Freeze must/);
    const reference = evidence.freezeReference(capsule);
    await assert.rejects(append(value, record, 'future-freeze', {...reference, freezeDigest: '0'.repeat(64)}), /Frozen executable/);
    value = await append(value, record, 'future-freeze', reference);
    value = await append(value, record, 'future-task-bank', bank);
    value = await append(value, record, 'future-run-reserved', {schema: 'discovery-lab-future-reservation/v1',
        taskBankDigest: bank.digest, perTaskWorkLimit: 50, attempt: 'future-' + crypto.randomUUID()});
    const report = structuredClone(await future.evaluateFutureTasks(capsule, bank, {perTaskWorkLimit: 50}));
    report.runs[0].status = 'forged';
    await assert.rejects(append(value, record, 'future-evaluation', report), /do not replay/);
    await assert.rejects(append(value, {...record, campaignDigest: '0'.repeat(64)}, 'future-freeze', reference), /accepted completed/);
});
test('workspace inspection and append capture caller data before their asynchronous boundary', async () => {
    const {value} = await initial(), mutable = structuredClone(value);
    const pending = workspace.inspectWorkspace(mutable);
    mutable.events[0].payload.reason = 'Changed after validation began';
    const checked = await pending;
    assert.equal(checked.latest.reason, 'Initial frozen proposal');
    assert.equal(checked.head, value.events.at(-1).digest);
    await assert.rejects(workspace.inspectWorkspace(mutable), /binding mismatch/);
});

test('event snapshot capture rejects caller accessors without invoking them', async () => {
    const {value, record} = await initial();
    let calls = 0;
    const hostile = structuredClone(value);
    Object.defineProperty(hostile, 'missionId', {enumerable: true, get() { calls++; return value.missionId; }});
    await assert.rejects(workspace.recordDiscoveryEvent(hostile, 'lab-evidence-attached', {}), /Accessor/);
    const payload = {campaignDigest: record.campaignDigest, kind: 'future-freeze'};
    Object.defineProperty(payload, 'record', {enumerable: true, get() { calls++; return {}; }});
    await assert.rejects(workspace.recordDiscoveryEvent(value, 'lab-evidence-attached', payload), /Accessor/);
    assert.equal(calls, 0);
});

test('campaign start owns source and workspace frames before awaiting commitments', async () => {
    const value = structuredClone(await workspace.createWorkspace());
    const original = structuredClone(value), mutableSources = {...sources};
    const pending = history.startPayload(value, runtime.DEFAULT_CHARTER, mutableSources);
    mutableSources.sourceDigest = '4'.repeat(64);
    value.missionId = 'changed-after-start';
    value.events[0].payload.number = 99;
    const start = await pending;
    assert.equal(start.bindings.missionId, original.missionId);
    assert.equal(start.version, 1);
    assert.deepEqual(Object.fromEntries(Object.keys(sources).map(key => [key, start.bindings[key]])), sources);
    await workspace.recordDiscoveryEvent(original, 'lab-started', start);
});

test('campaign start rejects source and workspace accessors without executing them', async () => {
    const value = await workspace.createWorkspace();
    let calls = 0;
    const hostileSources = {...sources};
    Object.defineProperty(hostileSources, 'sourceDigest', {enumerable: true, get() { calls++; return sources.sourceDigest; }});
    await assert.rejects(history.startPayload(value, runtime.DEFAULT_CHARTER, hostileSources), /Accessor/);
    const hostileWorkspace = structuredClone(value);
    Object.defineProperty(hostileWorkspace, 'events', {enumerable: true, get() { calls++; return value.events; }});
    await assert.rejects(history.startPayload(hostileWorkspace, runtime.DEFAULT_CHARTER, sources), /Accessor/);
    assert.equal(calls, 0);
});

test('successor arguments retain the brief captured before history inspection', async () => {
    const value = await workspace.createWorkspace();
    const brief = {...workspace.DEFAULT_BRIEF, title: 'Captured successor proposal'};
    const pending = workspace.addSuccessor(value, brief, null, 'A separate frozen proposal');
    brief.title = 'Changed after inspection began';
    const next = await pending;
    assert.equal((await workspace.inspectWorkspace(next)).latest.brief.title, 'Captured successor proposal');
    let calls = 0;
    const hostile = {...brief};
    Object.defineProperty(hostile, 'title', {enumerable: true, get() { calls++; return brief.title; }});
    await assert.rejects(workspace.addSuccessor(value, hostile, null, 'Rejected accessor'), /Accessor/);
    assert.equal(calls, 0);
});
