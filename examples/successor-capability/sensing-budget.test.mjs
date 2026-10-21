// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {apparatus} from './apparatus.mjs';
import {sensingCorrectionBaseline} from './evaluation.mjs';

const example = (topology = 'shielded') => {
    const app = apparatus(topology);
    return {apparatus: app, ast: {scope: [...app.scope]}};
};
const total = ledger => ['synthesis', 'qualification', 'installation', 'calibration', 'tuning', 'operation', 'maintenance']
    .reduce((value, key) => value + ledger[key], 0);

test('sensing total budget covers every attempted candidate and all independent acceptance work', async () => {
    for (const topology of ['shielded', 'routed', 'referenced']) for (let maxCost = 1; maxCost <= 100; maxCost++) {
        const report = await sensingCorrectionBaseline(example(topology), {maxCost});
        assert.ok(report.ledger.total <= maxCost, `${topology} exceeded ${maxCost}`);
        assert.equal(total(report.ledger), report.ledger.total);
        assert.ok(report.ledger.unsuccessfulCandidates <= report.tested);
        assert.ok(report.attempts.every(attempt => attempt.workToDate <= report.ledger.total));
        if (report.status === 'qualified') {
            assert.equal(report.qualification.status, 'qualified');
            assert.equal(report.independent.ok, true);
            assert.equal(report.replay.length, 2);
            assert.ok(report.replay.every(fixture => fixture.accepted));
        }
        if (report.status === 'not-qualified-within-supplied-sensing-language') {
            assert.equal(report.search.complete, true);
            assert.equal(report.search.status, 'completed');
            assert.equal(report.independent.ok, false);
        }
    }
});

test('terminal qualification reservation preserves a funded incumbent without pretending enumeration finished', async () => {
    const unfunded = await sensingCorrectionBaseline(example(), {maxCost: 31});
    assert.equal(unfunded.status, 'exhausted');
    assert.equal(unfunded.diagnosticBest.ok, true);
    assert.equal(unfunded.qualification.status, 'inconclusive');
    const incumbent = await sensingCorrectionBaseline(example(), {maxCost: 32});
    assert.equal(incumbent.status, 'qualified');
    assert.equal(incumbent.ledger.total, 32);
    assert.equal(incumbent.search.status, 'exhausted');
    assert.equal(incumbent.search.enumerationComplete, false);
    const complete = await sensingCorrectionBaseline(example(), {maxCost: 42});
    assert.equal(complete.status, 'qualified');
    assert.equal(complete.ledger.total, 42);
    assert.equal(complete.search.status, 'completed');
});

test('the common-reference 20-unit sensing attempt is a completed negative, never a cheaper qualified alternative', async () => {
    const negative = await sensingCorrectionBaseline(example('referenced'), {maxCost: 20});
    assert.equal(negative.ledger.total, 20);
    assert.equal(negative.status, 'not-qualified-within-supplied-sensing-language');
    assert.equal(negative.qualification.status, 'not-qualified');
    assert.equal(negative.search.complete, true);
    assert.equal(negative.best.errorBound, 0.5);
    assert.equal(negative.best.ok, false);
    assert.equal(negative.independent.ok, false);
    assert.equal(negative.replay.length, 0);
    const exhausted = await sensingCorrectionBaseline(example('referenced'), {maxCost: 19});
    assert.equal(exhausted.status, 'exhausted');
    assert.equal(exhausted.search.complete, false);
    assert.equal(exhausted.qualification.status, 'inconclusive');
});

test('state, program-size and retained-memory cuts remain explicit incomplete comparisons', async () => {
    const state = await sensingCorrectionBaseline(example('referenced'), {maxStates: 1});
    assert.equal(state.status, 'exhausted');
    assert.equal(state.search.enumerationComplete, false);
    assert.match(state.search.stopReason, /state limit/);
    const program = await sensingCorrectionBaseline(example(), {maxProgramSize: 1});
    assert.equal(program.status, 'truncated');
    assert.equal(program.search.enumerationComplete, true);
    assert.equal(program.search.complete, false);
    assert.ok(program.search.excludedByProgramSize > 0);
    const memory = await sensingCorrectionBaseline(example(), {maxMemoryStates: 4});
    assert.equal(memory.status, 'qualified');
    assert.equal(memory.search.status, 'exhausted');
    assert.match(memory.search.stopReason, /memory-state limit/);
    assert.ok(memory.attempts.length + memory.replay.length <= 4);
});

test('expired execution does no modeled work and partial replay cannot qualify', async () => {
    const expired = await sensingCorrectionBaseline(example(), {}, {timeLimitMs: 0});
    assert.equal(expired.status, 'exhausted');
    assert.equal(expired.ledger.total, 0);
    assert.equal(expired.tested, 0);
    const original = Date.now;
    let ticks = 0;
    try {
        Date.now = () => ticks++;
        const partial = await sensingCorrectionBaseline(example(), {}, {timeLimitMs: 7});
        assert.equal(partial.status, 'exhausted');
        assert.equal(partial.independent.ok, true);
        assert.equal(partial.replay.length, 1);
        assert.equal(partial.qualification.status, 'inconclusive');
        assert.match(partial.search.stopReason, /timeout during acceptance replay/);
    } finally { Date.now = original; }
});

test('sensor guards are ordered semantically rather than by their catalogue positions', async () => {
    const pkg = example();
    pkg.apparatus.primitives.find(primitive => primitive.id === 'sense-residual').requires = ['sense-reservoir'];
    const report = await sensingCorrectionBaseline(pkg);
    assert.equal(report.status, 'qualified');
    assert.deepEqual(report.best.ast.installations, ['sense-reservoir', 'sense-residual']);
});

test('large sensor catalogues use distinct BigInt subsets and report truncated coverage', async () => {
    const pkg = example();
    const sensor = pkg.apparatus.primitives.find(primitive => primitive.id === 'sense-residual');
    for (let index = 0; index < 35; index++) pkg.apparatus.primitives.push({...sensor, id: `extra-sensor-${index}`});
    const report = await sensingCorrectionBaseline(pkg, {maxStates: 2});
    assert.equal(report.status, 'qualified');
    assert.equal(report.search.status, 'exhausted');
    assert.equal(report.search.totalSubsets, (1n << 37n).toString());
    assert.deepEqual(report.best.ast.installations, ['sense-residual']);
});

test('invalid limits and accessor inputs are rejected before executing their getters', async () => {
    for (const key of ['maxCost', 'maxStates', 'maxMemoryStates', 'maxProgramSize']) {
        for (const value of [0, -1, NaN, Infinity, 1.5]) {
            await assert.rejects(sensingCorrectionBaseline(example(), {[key]: value}), /Invalid sensing/);
        }
    }
    await assert.rejects(sensingCorrectionBaseline(example(), {unknownLimit: 1}), /Unsupported sensing/);
    let reads = 0;
    const limits = Object.defineProperty({}, 'maxCost', {enumerable: true, get: () => { reads++; return 100; }});
    await assert.rejects(sensingCorrectionBaseline(example(), limits), /Invalid sensing/);
    const pkg = Object.defineProperty({}, 'apparatus', {enumerable: true, get: () => { reads++; return apparatus(); }});
    await assert.rejects(sensingCorrectionBaseline(pkg), /accessors/);
    const badScope = example();
    Object.defineProperty(badScope.ast.scope, '0', {get: () => { reads++; return 'standard'; }});
    await assert.rejects(sensingCorrectionBaseline(badScope), /accessors/);
    assert.equal(reads, 0);
});
