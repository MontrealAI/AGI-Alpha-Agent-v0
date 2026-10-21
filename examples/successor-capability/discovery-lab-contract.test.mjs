// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {canonical,parseBounded,validateResources,validateBindings,validateWorkRequest,
    BINDING_KEYS,DISCOVERY_LAB_INSPECTION_CHECKS} from './discovery-lab-contract.mjs';

function withoutEncoder(operation) {
    const original = globalThis.TextEncoder;
    let calls = 0;
    globalThis.TextEncoder = class {
        constructor() { calls++; throw Error('Unexpected encoder allocation'); }
    };
    try { operation(); assert.equal(calls, 0); }
    finally { globalThis.TextEncoder = original; }
}

test('obviously oversized imported text is rejected before encoder allocation', () => {
    withoutEncoder(() => assert.throws(() => parseBounded(' '.repeat(2_000_001)), /Import exceeds 2 MB/));
});
test('direct oversized scalar is rejected before stringify or encoder allocation', () => {
    const value = 'x'.repeat(2_000_001), original = JSON.stringify;
    JSON.stringify = item => {
        assert.notEqual(item, value, 'Oversized scalar reached stringify');
        return original(item);
    };
    try { withoutEncoder(() => assert.throws(() => canonical(value), /Canonical JSON exceeds 2 MB/)); }
    finally { JSON.stringify = original; }
});
test('escaped and cumulative canonical output is bounded before encoder allocation', () => {
    for (const value of ['\u0000'.repeat(333_334), Array(3).fill('x'.repeat(800_000)),
        {['k'.repeat(2_000_001)]: 1}]) {
        withoutEncoder(() => assert.throws(() => canonical(value), /Canonical JSON exceeds 2 MB/));
    }
});
test('ASCII and escaped scalar JSON remain accepted at exactly two million bytes', () => {
    for (const value of ['x'.repeat(1_999_998), '\u0000'.repeat(333_333)]) {
        const text = canonical(value);
        assert.equal(Buffer.byteLength(text), 2_000_000);
        assert.equal(parseBounded(text), value);
    }
});
test('UTF-8 multibyte boundaries are measured even when code units fit', () => {
    for (const value of ['é'.repeat(999_999), '😀'.repeat(499_999) + 'é']) {
        const text = canonical(value);
        assert.equal(Buffer.byteLength(text), 2_000_000);
        assert.equal(parseBounded(text), value);
        assert.throws(() => canonical(value + 'x'), /Canonical JSON exceeds 2 MB/);
        assert.throws(() => parseBounded(JSON.stringify(value + 'x')), /Import exceeds 2 MB/);
    }
});
test('canonical bytes for admitted compound data retain sorted keys and Unicode scalars', () => {
    assert.equal(canonical({z: ['é', '😀', '\u0000', true, null, -2], a: {b: 0}}),
        '{"a":{"b":0},"z":["é","😀","\\u0000",true,null,-2]}');
    assert.throws(() => canonical('\ud800'), /Unicode scalars required/);
});
test('array node ceiling is checked before descriptor materialization without shrinking its boundary', () => {
    const oversized = Array(100_000).fill(null), original = Object.getOwnPropertyDescriptors;
    let inspected = false;
    Object.getOwnPropertyDescriptors = item => {
        if (item === oversized) inspected = true;
        return original(item);
    };
    try {
        withoutEncoder(() => assert.throws(() => canonical(oversized), /JSON complexity exceeds limit/));
        assert.equal(inspected, false);
    } finally { Object.getOwnPropertyDescriptors = original; }
    const boundary = Array(99_999).fill(null);
    assert.equal(canonical(boundary), JSON.stringify(boundary));
});

function withoutDescriptors(value, operation) {
    const bulk = Object.getOwnPropertyDescriptors, single = Object.getOwnPropertyDescriptor;
    let inspected = 0;
    Object.getOwnPropertyDescriptors = item => {
        if (item === value) inspected++;
        return bulk(item);
    };
    Object.getOwnPropertyDescriptor = (item, key) => {
        if (item === value) inspected++;
        return single(item, key);
    };
    try { operation(); assert.equal(inspected, 0, 'Over-limit value reached descriptor inspection'); }
    finally {
        Object.getOwnPropertyDescriptors = bulk;
        Object.getOwnPropertyDescriptor = single;
    }
}

test('wide object node ceiling precedes descriptors and preserves the admitted boundary', () => {
    const value = Object.fromEntries(Array.from({length: 100_000}, (_, i) => ['k' + i, 0]));
    withoutDescriptors(value, () => withoutEncoder(() =>
        assert.throws(() => canonical(value), /JSON complexity exceeds limit/)));
    delete value.k99999;
    assert.equal(Object.keys(JSON.parse(canonical(value))).length, 99_999);
});

test('wide non-enumerable object and array keys are bounded before descriptor inspection', () => {
    for (const value of [{}, []]) {
        for (let i = 0; i < 100_000; i++) Object.defineProperty(value, 'extra' + i, {value: 0});
        withoutDescriptors(value, () => withoutEncoder(() =>
            assert.throws(() => canonical(value), /JSON complexity exceeds limit/)));
    }
});

test('object key output lower bound precedes descriptors and observes the remaining output budget', () => {
    const value = Object.fromEntries(Array.from({length: 3_000}, (_, i) => ['k'.repeat(700) + i, 0]));
    withoutDescriptors(value, () => withoutEncoder(() =>
        assert.throws(() => canonical(value), /Canonical JSON exceeds 2 MB/)));
    const nested = {['k'.repeat(40)]: 0};
    withoutDescriptors(nested, () => withoutEncoder(() =>
        assert.throws(() => canonical(['x'.repeat(1_999_960), nested]), /Canonical JSON exceeds 2 MB/)));
});

test('remaining node budget bounds nested object width before descriptor inspection', () => {
    const value = Object.fromEntries(Array.from({length: 99_999}, (_, i) => ['k' + i, 0]));
    withoutDescriptors(value, () => withoutEncoder(() =>
        assert.throws(() => canonical({nested: value}), /JSON complexity exceeds limit/)));
});

test('shared declared inspection charge composes with a distinct receiver allowance in the exact vector', () => {
    assert.equal(DISCOVERY_LAB_INSPECTION_CHECKS, 10000);
    const receiverChecks = 10000, replayChecks = 1000000;
    const committed = validateResources({acquisitions: 0, search: 0,
        checking: replayChecks + receiverChecks + DISCOVERY_LAB_INSPECTION_CHECKS,
        memoryBytes: 0, storageBytes: 0, workerCapacity: 0, installations: 0, elapsedMs: 0});
    assert.equal(committed.checking - receiverChecks - DISCOVERY_LAB_INSPECTION_CHECKS, replayChecks);
    assert.throws(() => validateResources({...committed, inspectionApproved: true}), /resource vector/);
});

const requestFixture = () => JSON.parse(readFileSync(new URL('./fixtures/discovery-lab-request.json', import.meta.url)));
test('canonical data comes from captured descriptors without property or array-method reads', () => {
    for (const [value, expected] of [[{count: 7}, '{"count":7}'], [[1, 2], '[1,2]']]) {
        let reads = 0;
        const view = new Proxy(value, {get() { reads++; throw Error('Caller property was read'); }});
        assert.equal(canonical(view), expected);
        assert.equal(reads, 0);
    }
});
test('captured array length must itself be a bounded nonnegative integer', () => {
    for (const length of [NaN, Infinity, -1, -0, 0.5, '0', false]) {
        const view = new Proxy([], {
            get: (target, key) => Reflect.get(target, key),
            getOwnPropertyDescriptor(target, key) {
                const descriptor = Reflect.getOwnPropertyDescriptor(target, key);
                return key === 'length' ? {...descriptor, value: length} : descriptor;
            }
        });
        assert.throws(() => canonical(view), /array length|complexity/i);
    }
});
test('resource and binding validation returns the same inert snapshot it checked', () => {
    const fixture = requestFixture();
    for (const [value, key, validate] of [
        [fixture.resourceLimits, 'checking', validateResources],
        [Object.fromEntries(BINDING_KEYS.map(key => [key, fixture[key]])), 'revision', validateBindings]
    ]) {
        value[key] = 0; let passes = 0;
        const view = new Proxy(value, {
            ownKeys(target) { passes++; return Reflect.ownKeys(target); },
            get(target, name) { return name === key && passes >= 3 ? -1 : Reflect.get(target, name); },
            getOwnPropertyDescriptor(target, name) {
                const descriptor = Reflect.getOwnPropertyDescriptor(target, name);
                return name === key && passes >= 3 ? {...descriptor, value: -1} : descriptor;
            }
        });
        assert.equal(validate(view)[key], 0);
        assert.equal(passes, 1);
    }
});
test('complete request validation keeps extra keys from its first captured frame', async () => {
    const fixture = {...requestFixture(), extra: true}; let passes = 0;
    const view = new Proxy(fixture, {
        ownKeys(target) {
            const keys = Reflect.ownKeys(target); passes++;
            return passes === 1 ? keys : keys.filter(key => key !== 'extra');
        }
    });
    await assert.rejects(validateWorkRequest(view), /request schema/);
});
test('complete request validation uses captured mode data rather than a later property value', async () => {
    const fixture = {...requestFixture(), executionMode: 'external'};
    const view = new Proxy(fixture, {
        get(target, key) { return key === 'executionMode' ? 'synthetic-local' : Reflect.get(target, key); }
    });
    await assert.rejects(validateWorkRequest(view), /not provisioned/);
});
test('complete request validation owns all data before awaiting its payload hash', async () => {
    const fixture = requestFixture(), original = structuredClone(fixture);
    const pending = validateWorkRequest(fixture);
    fixture.executionMode = 'external'; fixture.commission.capBaseUnits = '1';
    fixture.commission.status = 'SUBMITTED'; fixture.resourceLimits.checking = -1;
    fixture.payload.notice = 'Changed after validation started';
    assert.deepEqual(await pending, original);
});
