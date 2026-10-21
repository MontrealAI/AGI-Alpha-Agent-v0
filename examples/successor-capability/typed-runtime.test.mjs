// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {apparatus, expandApparatus, TOPOLOGIES} from './apparatus.mjs';
import {qualify, compile, measure, validateApparatus} from './typed-runtime.mjs';
import {verify} from './independent-checker.mjs';

const ast = (installations = [], steps = [], scope = ['standard']) => ({schema: 'out-evolve-ast/v1',
    installations, prepare: {op: 'sequence', steps: steps.map(id => ({op: 'primitive', id}))}, scope});

test('runtime/checker independently agree across exhaustive short preparation words and topologies', () => {
    for (const name of TOPOLOGIES) {
        const a = apparatus(name), installs = a.primitives.filter(p => p.phase === 'install').slice(0, 3);
        const operations = a.primitives.filter(p => p.phase === 'prepare');
        for (let mask = 0; mask < 1 << installs.length; mask++) {
            const selected = installs.filter((p, index) => mask & 1 << index).map(p => p.id);
            for (const first of [null, ...operations]) for (const second of [null, ...operations]) {
                const program = ast(selected, [first, second].filter(Boolean).map(p => p.id));
                let runtime, reference, runtimeError, checkerError;
                try { runtime = qualify(a, program); } catch (error) { runtimeError = error; }
                try { reference = verify(a, program); } catch (error) { checkerError = error; }
                assert.equal(Boolean(runtimeError), Boolean(checkerError));
                if (!runtimeError) assert.deepEqual(reference, runtime);
            }
        }
    }
});

test('conservative recurrence bounds all repeated numerical measurements', () => {
    for (const initial of [0, 1, 6, 16]) for (const drift of [0, 1, 3]) for (let halves = 0; halves < 8; halves++) {
        const a = apparatus(); a.channels[0].initial = initial; a.channels[0].drift = drift;
        const program = ast([], Array(halves).fill('halve-residual'));
        const report = qualify(a, program);
        assert.deepEqual(verify(a, program), report);
        for (const cycle of [0, 1, 2, 8, 128, 1024]) {
            for (const sign of [-1, 1]) assert.ok(Math.abs(measure(a, program, 7, {cycle, sign}).error)
                <= report.errorBound);
        }
    }
});

test('exact rational ceiling remains conservative after many tiny dyadic contractions', () => {
    const a = apparatus(); a.channels[0].initial = 0; a.channels[0].drift = 1;
    a.limits.maxInstructions = 64;
    const report = qualify(a, ast([], Array(64).fill('halve-residual')));
    assert.equal(report.certificate.recurrence.residual.invariant, 2);
    assert.deepEqual(verify(a, ast([], Array(64).fill('halve-residual'))), report);
});

test('bounded repetition compiles and unbounded/oversized repetitions fail both interpreters', () => {
    const a = apparatus(), program = ast(['protect-residual']);
    program.prepare.steps.push({op: 'repeat', count: 2,
        body: {op: 'sequence', steps: [{op: 'primitive', id: 'halve-residual'}]}});
    assert.equal(compile(a, program).steps.length, 2);
    assert.deepEqual(verify(a, program), qualify(a, program));
    for (const count of [0, Infinity, 1.5, 33]) {
        program.prepare.steps[0].count = count;
        assert.throws(() => qualify(a, program)); assert.throws(() => verify(a, program));
    }
});

test('untrusted getters do not execute during runtime or independent validation', () => {
    let invoked = false;
    const a = apparatus();
    Object.defineProperty(a, 'scope', {enumerable: true, get() { invoked = true; throw Error('getter'); }});
    assert.throws(() => validateApparatus(a), /Accessor/);
    assert.throws(() => verify(a, ast()), /accessor/);
    assert.equal(invoked, false);
});

test('invalid effects, resource overflow and dormant reservoir exposure fail closed', () => {
    const a = apparatus();
    const winning = ast(['protect-residual'], ['flush-residual']);
    assert.equal(qualify(a, winning).ok, true);
    assert.equal(qualify(expandApparatus(a), winning).ok, false);
    assert.throws(() => measure(a, winning, 3, {operation: 'reservoir'}), /scope/);
    const wrong = structuredClone(a); wrong.primitives[0].effects = ['productive'];
    assert.throws(() => qualify(wrong, winning)); assert.throws(() => verify(wrong, winning));
    const costly = structuredClone(a); costly.limits.maxCost = 4;
    assert.throws(() => qualify(costly, winning), /overflow/); assert.throws(() => verify(costly, winning), /overflow/);
    assert.throws(() => measure(a, winning, 3, {cycle: 1025}), /bound/);
    const tampered = structuredClone(qualify(a, winning).certificate); tampered.productiveGain = 0;
    assert.throws(() => verify(a, winning, tampered), /certificate/);
});
