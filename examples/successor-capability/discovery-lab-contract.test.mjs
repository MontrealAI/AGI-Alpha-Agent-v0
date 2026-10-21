// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {canonical,parseBounded} from './discovery-lab-contract.mjs';

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
