// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_CHARTER, runCampaign} from './discovery-lab.mjs';
import {payloadDigest, canonical} from './discovery-lab-contract.mjs';
import {FUTURE_PROTOCOL, freezeCapability, commitFutureTasks, publicFutureBank,
    evaluateFutureTasks, verifyFutureEvaluation} from './discovery-lab-future.mjs';
const charter = structuredClone(DEFAULT_CHARTER), campaign = runCampaign(charter);
const bindings = {missionId: 'capability-00000000-0000-0000-0000-000000000000', revision: 1,
    purposeDigest: await payloadDigest({purpose: charter.purpose}), charterDigest: await payloadDigest(charter),
    modelDigest: 'a'.repeat(64), sourceDigest: 'b'.repeat(64), evaluatorDigest: 'c'.repeat(64)};
const input = () => ({bindings: structuredClone(bindings), charter: structuredClone(charter),
    result: structuredClone(campaign), ancestors: []});
const capsule = await freezeCapability(input()), bank = await publicFutureBank(capsule, 18);
const evaluation = await evaluateFutureTasks(capsule, bank);
const sum = costs => Object.values(costs).reduce((total, amount) => total + amount, 0);
const task = changes => ({id: 'new-task', kind: 'screen', parameter: 7, maxActiveControls: 2, regime: 'linear', ...changes});

test('construction freezes actual accepted executable and sources before later future task commitment', async () => {
    assert.equal(capsule.status, 'frozen');
    assert.deepEqual(capsule.executable, campaign.stages[5].program);
    assert.equal(capsule.bindings.sourceDigest, bindings.sourceDigest);
    assert.equal(bank.freezeDigest, capsule.digest);
    assert.equal(bank.tasks.length, 6);
    assert.equal(bank.protocolDigest, await payloadDigest(FUTURE_PROTOCOL));
    assert.ok(Object.isFrozen(capsule.executable.responseTable));
    await assert.rejects(commitFutureTasks(structuredClone(capsule), [task({})]), /Freeze and verify/);
    await assert.rejects(commitFutureTasks(capsule, [task({expected: [1]})]), /expected answers/);
    assert.ok(Object.isFrozen(FUTURE_PROTOCOL.treatments));
    assert.throws(() => FUTURE_PROTOCOL.treatments.splice(1));
    let reads = 0;
    const unknown = structuredClone(capsule);
    Object.defineProperty(unknown, 'digest', {get() { reads++; return reads === 1 ? undefined : 'f'.repeat(64); }});
    await assert.rejects(commitFutureTasks(unknown, [task({})]), /Freeze and verify/);
    await assert.rejects(publicFutureBank(unknown), /Freeze and verify/);
    await assert.rejects(evaluateFutureTasks(unknown, {}), /custody/);
    assert.equal(reads, 0);
});

test('freeze owns one caller snapshot before digest await and rejects tampered evidence/source bindings', async () => {
    const mutable = input(), pending = freezeCapability(mutable);
    mutable.result.stages[5].program.responseTable[0] = 999;
    mutable.bindings.sourceDigest = 'd'.repeat(64);
    assert.deepEqual(await pending, capsule);
    const poisoned = input(); poisoned.result.stages[5].program.responseTable[0]++;
    await assert.rejects(freezeCapability(poisoned), /reconstruct/);
    const mismatch = input(); mismatch.bindings.charterDigest = '0'.repeat(64);
    await assert.rejects(freezeCapability(mismatch), /bindings/);
});

test('committed bank is captured before async digest and forbids duplicates, extra fields and unsafe values', async () => {
    const supplied = [task({})], pending = commitFutureTasks(capsule, supplied);
    supplied[0].parameter = 99;
    assert.equal((await pending).tasks[0].parameter, 7);
    for (const tasks of [[task({}), task({})], [task({parameter: -1})], [task({maxActiveControls: 4})],
        [task({regime: 'unknown'})], [task({kind: 'oracle'})]]) await assert.rejects(commitFutureTasks(capsule, tasks));
    let invoked = false;
    const accessor = task({}); Object.defineProperty(accessor, 'parameter', {enumerable: true, get() { invoked = true; return 8; }});
    await assert.rejects(commitFutureTasks(capsule, [accessor]), /Accessor/); assert.equal(invoked, false);
});

test('future runs invoke actual frozen table and removal changes actual path, acquisitions and work', () => {
    for (const t of bank.tasks.slice(0, 5)) {
        const frozen = evaluation.runs.find(run => run.taskId === t.id && run.treatment === 'frozen-capability');
        const removed = evaluation.runs.find(run => run.taskId === t.id && run.treatment === 'capability-removed');
        assert.equal(frozen.status, 'accepted'); assert.deepEqual(frozen.output, removed.output);
        assert.equal(frozen.invocations[0].action, 'invoke-frozen-response-table');
        assert.equal(removed.invocations[0].retainedTable, false);
        assert.equal(frozen.costs.acquisitions, 0); assert.equal(removed.costs.acquisitions, 8);
        assert.ok(sum(frozen.costs) < sum(removed.costs));
    }
});

test('same finite tasks retain tied unrestricted reuse and a cheaper competent static total', () => {
    const normal = evaluation.relations.slice(0, 5);
    assert.ok(normal.every(row => row.comparisons.find(item => item.treatment === 'unrestricted-same-primitive').relation === 'warm-tie'));
    const frozen = evaluation.summaries.find(row => row.treatment === 'frozen-capability');
    const fixed = evaluation.summaries.find(row => row.treatment === 'competent-static');
    assert.ok(sum(fixed.total) < sum(frozen.total));
    assert.ok(sum(frozen.cold) > sum(frozen.recurring));
    assert.deepEqual(frozen.amortizedWork, {numerator: sum(frozen.total), denominator: 6});
});

test('changed regime refuses stale admission and deliberately bypassed stale control fails independent semantics', () => {
    const shifted = bank.tasks.at(-1).id;
    const record = name => evaluation.runs.find(run => run.taskId === shifted && run.treatment === name);
    assert.equal(record('frozen-capability').status, 'rejected');
    assert.equal(record('frozen-capability').output, null);
    assert.equal(record('stale-capability-control').status, 'rejected');
    assert.equal(record('stale-capability-control').checker.accepted, false);
    assert.equal(record('stale-capability-control').invocations[0].admissionBypassed, true);
    assert.equal(record('competent-static').status, 'accepted');
    assert.equal(record('construction-from-scratch').status, 'rejected');
    assert.ok(sum(record('construction-from-scratch').costs) > 0);
    assert.ok(evaluation.runs.filter(run => run.treatment === 'poisoned-capability-control')
        .every(run => run.status === 'rejected' && run.output === null && run.invocations[0].action === 'refuse-replacement'));
});

test('matched budget exhaustion retains partial work and outputs without falsely reporting a negative answer', async () => {
    const limited = await evaluateFutureTasks(capsule, bank, {perTaskWorkLimit: 20});
    assert.ok(limited.runs.some(run => run.status === 'inconclusive' && sum(run.costs) > 0));
    assert.ok(limited.runs.every(run => sum(run.costs) <= 20));
    const scratch = limited.runs.filter(run => run.treatment === 'construction-from-scratch');
    assert.ok(scratch.every(run => run.status === 'inconclusive' && run.output === null && run.costs.checking === 1));
    const empty = await evaluateFutureTasks(capsule, bank, {perTaskWorkLimit: 0});
    assert.ok(empty.runs.every(run => run.status === 'inconclusive' && sum(run.costs) === 0));
});

test('from-scratch pays real campaign construction for each task, not free reconstruction', () => {
    const row = evaluation.runs.find(run => run.treatment === 'construction-from-scratch' && run.taskId === bank.tasks[0].id);
    assert.equal(row.status, 'accepted');
    assert.equal(row.invocations[0].action, 'construct-from-scratch');
    for (const key of ['acquisitions', 'checking', 'search', 'installations']) assert.ok(row.costs[key] >= campaign.resources[key]);
});

test('three-generation freeze retains every ancestor construction and admission replay without inherited cost disappearance', async () => {
    const second = runCampaign(charter, {parent: campaign}), third = runCampaign(charter, {parent: second});
    const thirdCapsule = await freezeCapability({bindings, charter, result: third,
        ancestors: [{charter, result: campaign}, {charter, result: second}]});
    for (const key of ['acquisitions', 'checking', 'search', 'installations']) {
        assert.equal(thirdCapsule.construction[key], campaign.resources[key] + second.resources[key] + third.resources[key]);
        assert.equal(thirdCapsule.admissionReplay[key], thirdCapsule.construction[key]);
    }
});

test('rejected successor is a charged refusal and cannot replace the accepted predecessor capsule', async () => {
    const changed = {...charter, hiddenCoupling: true}, rejected = runCampaign(changed, {parent: campaign});
    const refused = await freezeCapability({bindings: {...bindings, charterDigest: await payloadDigest(changed)},
        charter: changed, result: rejected, ancestors: [{charter, result: campaign}]});
    assert.equal(refused.status, 'rejected'); assert.equal(refused.authority, false);
    assert.ok(sum(refused.construction) > sum(capsule.construction));
    await assert.rejects(commitFutureTasks(refused, [task({})]));
    assert.equal((await evaluateFutureTasks(capsule, bank)).digest, evaluation.digest);
});

test('independent replay accepts detached evidence but rejects outcome, cost, source, omission and task swaps', async () => {
    const detached = structuredClone(evaluation);
    assert.equal((await verifyFutureEvaluation(structuredClone(capsule), structuredClone(bank), detached)).verified, true);
    for (const mutate of [result => result.runs.pop(), result => result.runs[0].costs.checking--,
        result => result.runs[0].output.rows[0].value++, result => result.authority = true]) {
        const poisoned = structuredClone(evaluation); mutate(poisoned);
        await assert.rejects(verifyFutureEvaluation(capsule, bank, poisoned), error => {
            assert.match(error.message, /do not replay/); assert.ok(sum(error.verificationResources) > 0); return true;
        });
    }
    const source = structuredClone(capsule); source.bindings.sourceDigest = 'd'.repeat(64);
    await assert.rejects(verifyFutureEvaluation(source, bank, evaluation), /do not replay/);
    const swapped = structuredClone(bank); swapped.tasks.reverse();
    await assert.rejects(verifyFutureEvaluation(capsule, swapped, evaluation), /does not replay/);
    assert.equal(canonical(evaluation), canonical(await evaluateFutureTasks(capsule, bank)));
});
