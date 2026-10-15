// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {assess, bindParticipant, exampleContract, exportRecord, freezeContract, reportTemplate, restoreRecord,
    validateContract, validateFrozen, validateReport} from './engine.mjs';
const start = '2026-10-15T12:00:00.000Z', now = '2026-10-15T13:00:00.000Z';
const copy = value => JSON.parse(JSON.stringify(value));
async function fixture() {
    const frozen = await freezeContract(exampleContract(start)), report = await reportTemplate(frozen, start);
    report.state = 'complete'; report.finishedAt = now;
    report.rows.forEach(row => {
        row.trialCount = 1;
        row.metrics.forEach(m => { m.lower = m.upper = m.id === 'quality' && row.role === 'candidate' ? 20 : 10; m.evidenceDigest = 'a'.repeat(64); });
        row.constraints.forEach(c => { c.status = 'reported-pass'; c.evidenceDigest = 'b'.repeat(64); });
    });
    return {frozen, report};
}
test('supplied successful comparisons never issue independent verdict, designation or authority', async () => {
    const {frozen, report} = await fixture(), result = await assess(frozen, [report], now);
    assert.equal(result.status, 'reported-comparison-ready-for-review');
    assert.equal(result.independentVerdict, 'not-established'); assert.equal(result.designation, 'not-earned');
    assert.equal(result.admission, 'not-requested'); assert.equal(result.authority, 'none');
    assert.equal(result.verification, 'uncommissioned'); assert.equal(result.gaps.length, 3);
});
test('uncommissioned state and scaffold contain no test outcomes', async () => {
    const frozen = await freezeContract(exampleContract(start));
    assert.equal((await assess(frozen, [], now)).status, 'uncommissioned');
    const report = await reportTemplate(frozen, start);
    assert.equal((await assess(frozen, [report], now)).status, 'uncertain');
});
test('all exact bindings change contract identity and frozen objects cannot mutate', async () => {
    const original = exampleContract(start), frozen = await freezeContract(original);
    for (const key of ['sourceHash', 'configurationHash', 'toolsHash', 'knowledgeHash', 'interfacesHash']) {
        const changed = copy(original); changed.participants.candidate[key] = 'f'.repeat(64);
        assert.notEqual((await freezeContract(changed)).contractDigest, frozen.contractDigest);
    }
    assert.throws(() => { frozen.contract.mission = 'changed'; });
    const changed = copy(frozen); changed.contract.mission = 'changed';
    await assert.rejects(validateFrozen(changed), /CONTRACT_CHANGED/);
});
test('participant material binds actual supplied bytes without executing them', async () => {
    const material = {source: 'never execute()', configuration: {seed: 1}, tools: [], knowledge: [], interfaces: []};
    const a = await bindParticipant('candidate', material); material.configuration.seed++;
    const b = await bindParticipant('candidate', material);
    assert.notEqual(a.configurationHash, b.configurationHash); assert.equal(a.sourceHash, b.sourceHash);
});
test('same formation commitment, missing dimensions, duplicate comparator and identity conflict are rejected', () => {
    for (const change of [c => { c.evaluation.taskSetCommitment = c.evaluation.formationSetCommitment; },
        c => { c.metrics.pop(); }, c => { c.participants.alternative = {...c.participants.incumbent, id: 'alias'}; },
        c => { c.review.reviewerId = c.participants.candidate.id; }]) {
        const c = exampleContract(start); change(c); assert.throws(() => validateContract(c));
    }
});
test('changed candidate, contract, task, protocol or resource policy rejects report', async () => {
    const {frozen, report} = await fixture();
    for (const key of ['participantDigest', 'taskSetCommitment', 'protocolHash', 'resourcePolicyHash']) {
        const r = copy(report); r.rows[0][key] = 'f'.repeat(64); await assert.rejects(validateReport(r, frozen));
    }
    const r = copy(report); r.contractDigest = 'f'.repeat(64); await assert.rejects(validateReport(r, frozen), /WRONG_CONTRACT/);
});
test('uncertainty bounds and both comparators determine conservative reported gains', async () => {
    const {frozen, report} = await fixture(); report.rows[2].metrics[0].upper = 21;
    assert.equal((await assess(frozen, [report], now)).status, 'retain-incumbent');
    report.rows[2].metrics[0].upper = 20;
    assert.equal((await assess(frozen, [report], now)).status, 'retain-incumbent');
});
test('unknown cost or human burden never becomes zero or earned proof', async () => {
    for (const metric of ['cost', 'human']) {
        const {frozen, report} = await fixture();
        const m = report.rows[0].metrics.find(x => x.id === metric); m.lower = m.upper = null; m.evidenceDigest = null;
        assert.equal((await assess(frozen, [report], now)).status, 'evidence-needed');
    }
});
test('burden regressions, negative outcomes and tied comparisons keep incumbent', async () => {
    for (const dimension of ['cost', 'time', 'safety', 'human', 'proof']) {
        const {frozen, report} = await fixture(); const m = report.rows[0].metrics.find(x => x.id === dimension);
        m.lower = m.upper = 11; assert.equal((await assess(frozen, [report], now)).status, 'retain-incumbent');
    }
    const {frozen, report} = await fixture(); report.rows[0].metrics[0].lower = report.rows[0].metrics[0].upper = 10;
    assert.equal((await assess(frozen, [report], now)).status, 'retain-incumbent');
});
test('failed attempt cannot be hidden by successful retry; duplicates and reorder rejected', async () => {
    const {frozen, report} = await fixture(), failed = copy(report);
    failed.attemptId = 'failed'; failed.state = 'failed'; failed.failures = [{role: 'candidate', code: 'safety-failure', evidenceDigest: 'c'.repeat(64)}];
    const result = await assess(frozen, [failed, report], now);
    assert.equal(result.status, 'retain-incumbent'); assert(result.failures.some(f => f.code === 'safety-failure')); assert.equal(result.attempts, 2);
    await assert.rejects(assess(frozen, [report, report], now), /DUPLICATE/);
    failed.startedAt = now; await assert.rejects(assess(frozen, [failed, report], now), /ATTEMPT_ORDER/);
});
test('interrupted, stopped, uncertain and incomplete remain distinct and expired supersedes', async () => {
    const {frozen, report} = await fixture();
    for (const state of ['interrupted', 'stopped', 'uncertain', 'failed']) {
        const r = copy(report); r.state = state; assert.equal((await assess(frozen, [r], now)).status, state);
    }
    report.rows.pop(); assert.equal((await assess(frozen, [report], now)).status, 'reported-incomplete');
    assert.equal((await assess(frozen, [report], frozen.contract.expiresAt)).status, 'expired');
});
test('time validity, finite integers, unknown as a value and duplicate rows are strict', async () => {
    const {frozen, report} = await fixture();
    for (const mutate of [r => { r.startedAt = '2026-10-14T12:00:00.000Z'; },
        r => { r.rows[0].metrics[0].lower = NaN; }, r => { r.rows[0].metrics[0].upper = null; },
        r => { r.rows[0].metrics[0].evidenceDigest = null; }, r => { r.rows[1].role = 'candidate'; }]) {
        const r = copy(report); mutate(r); await assert.rejects(validateReport(r, frozen));
    }
    await assert.rejects(assess(frozen, [report], start), /FUTURE_RESULT/);
});
test('export restore verifies identity, preserves failures and returns only historical reports', async () => {
    const {frozen, report} = await fixture(), record = await exportRecord(frozen, [report]);
    const restored = await restoreRecord(JSON.stringify(record), now);
    assert.equal(restored.recovery, 'historical-reports-only'); assert.equal(restored.authority, 'none');
    assert.equal(restored.assessment.designation, 'not-earned');
    const changed = copy(record); changed.reports[0].evidenceDigest = 'c'.repeat(64);
    await assert.rejects(restoreRecord(JSON.stringify(changed), now), /RECORD_CHANGED/);
});
test('self-signed certification, hidden cases, executable paths and authority fields cannot enter schema', async () => {
    const {frozen, report} = await fixture();
    for (const [key, value] of [['independent', true], ['authority', 'execute'], ['signature', 'self-signed'],
        ['hiddenCases', ['secret']], ['executable', '/bin/sh']]) {
        const r = copy(report); r[key] = value; await assert.rejects(validateReport(r, frozen), /SCHEMA/);
    }
    const record = copy(await exportRecord(frozen, [report])); record.designation = 'earned';
    await assert.rejects(restoreRecord(JSON.stringify(record), now), /SCHEMA/);
    await assert.rejects(restoreRecord('{"schema":1,"schema":2}', now), /Duplicate/);
});
test('earlier complete metric regressions and uncertainty survive passing retries and recovery', async () => {
    for (const dimension of ['safety', 'cost', 'quality']) {
        const {frozen, report} = await fixture(), earlier = copy(report);
        earlier.attemptId = `earlier-${dimension}`;
        const metric = earlier.rows[0].metrics.find(m => m.id === dimension);
        metric.lower = dimension === 'quality' ? 9 : 11;
        metric.upper = dimension === 'quality' ? 21 : 12;
        const result = await assess(frozen, [earlier, report], now);
        assert.equal(result.status, 'retain-incumbent');
        assert.equal(result.attemptResults[0].status, 'retain-incumbent');
        assert.equal(result.attemptResults[1].status, 'reported-comparison-ready-for-review');
        assert(result.failures.some(f => f.attemptId === earlier.attemptId && f.metricId === dimension));
        const restored = await restoreRecord(JSON.stringify(await exportRecord(frozen, [earlier, report])), now);
        assert.equal(restored.assessment.status, 'retain-incumbent');
        assert.deepEqual(restored.assessment.attemptResults, result.attemptResults);
    }
});
test('earlier unknown and incomplete outcomes cannot disappear after passing retry', async () => {
    for (const mode of ['unknown', 'incomplete']) {
        const {frozen, report} = await fixture(), earlier = copy(report); earlier.attemptId = mode;
        if (mode === 'unknown') earlier.rows[0].metrics[0].lower = earlier.rows[0].metrics[0].upper = null;
        else earlier.rows.pop();
        const result = await assess(frozen, [earlier, report], now);
        assert.equal(result.status, 'evidence-needed'); assert.equal(result.attemptResults[0].unknown, true);
        assert(result.gaps.some(gap => gap.includes('retained attempt')));
    }
});
test('expiry contracts currency without erasing historical comparison or granting authority', async () => {
    const {frozen, report} = await fixture();
    const result = await assess(frozen, [report], frozen.contract.expiresAt);
    assert.equal(result.status, 'expired'); assert.equal(result.reportedComparison, 'reported-comparison-ready-for-review');
    assert.equal(result.authority, 'none'); assert.equal(result.independentVerdict, 'not-established');
});
