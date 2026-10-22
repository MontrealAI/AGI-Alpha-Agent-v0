// SPDX-License-Identifier: Apache-2.0
// Inert parse/resolver decisions only; input modules are never linked or evaluated.
import test from 'node:test';
import assert from 'node:assert/strict';
import {parseModuleSources, checkDependencyRecords, ownedTarget} from './fleet_module_boundary.mjs';

test('parse-only records include side-effect imports and both reexport forms', () => {
    const records = parseModuleSources([
        {name: 'entry.mjs', source: "import './a.mjs'; export {value} from './b.mjs'; export * from './c.mjs';"},
        ...['a', 'b', 'c'].map(name => ({name: name + '.mjs', source: 'export const value = 1;'}))
    ]);
    assert.deepEqual(records[0].requests, ['./a.mjs', './b.mjs', './c.mjs']);
    const names = new Set(records.map(row => row.name));
    assert.doesNotThrow(() => checkDependencyRecords(records, names));
    names.delete('c.mjs');
    assert.throws(() => checkDependencyRecords(records, names), /absent from the captured source map/);
});

test('static records do not claim to enumerate computed imports; resolver decisions remain closed', () => {
    const records = parseModuleSources([{name: 'entry.mjs', source:
        "const target = './missing.mjs'; const later = () => import(target);"}]);
    assert.deepEqual(records[0].requests, []);
    const names = new Set(['entry.mjs', 'owned.mjs']);
    assert.equal(ownedTarget('./owned.mjs', 'entry.mjs', names), 'owned.mjs');
    for (const target of ['./missing.mjs', '../outside.mjs', 'node:fs', 'file:///tmp/missing.mjs']) {
        assert.throws(() => ownedTarget(target, 'entry.mjs', names));
    }
    assert.equal(ownedTarget('node:crypto', 'entry.mjs', names, {'entry.mjs': ['node:crypto']}), 'node:crypto');
    assert.throws(() => ownedTarget('node:crypto', 'owned.mjs', names, {'entry.mjs': ['node:crypto']}));
});
