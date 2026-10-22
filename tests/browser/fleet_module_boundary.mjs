// SPDX-License-Identifier: Apache-2.0
// Parse-only dependency extraction and an owned-byte ESM resolver boundary.
// SourceTextModule is constructed but is never linked or evaluated here.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';
import * as nodeModule from 'node:module';
import {types} from 'node:util';
import {fileURLToPath, pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';

const MAX_SOURCE_BYTES = 16_000_000, MAX_RECORDS = 256;
const namespaces = new Map();
let hooks = null;
const safeName = name => typeof name === 'string' && name.length > 0 && name.length <= 4096
    && !/[\u0000-\u0020\u007f?#%\\]/.test(name) && !path.posix.isAbsolute(name)
    && path.posix.normalize(name) === name && !name.split('/').some(item => !item || item === '.' || item === '..');

/** Node's parser reports all static imports and reexports without running them. */
export function staticDependencyRecords(records) {
    assert.ok(Array.isArray(records) && records.length <= MAX_RECORDS);
    const names = new Set(); let total = 0;
    const result = records.map(({name, source}) => {
        assert.ok(typeof name === 'string' && name.length <= 4096 && !names.has(name)); names.add(name);
        assert.ok(typeof source === 'string' && source.length <= 2_000_000);
        total += Buffer.byteLength(source); assert.ok(total <= MAX_SOURCE_BYTES);
        const module = new vm.SourceTextModule(source, {identifier: name});
        const requests = [...module.dependencySpecifiers];
        assert.ok(requests.length <= 4096 && requests.every(item => item.length <= 4096));
        return {name, requests};
    });
    assert.ok(Buffer.byteLength(JSON.stringify(result)) <= 1_000_000);
    return result;
}

/** A bounded parser process enables vm modules; it never links/evaluates input. */
export function parseModuleSources(records, helperSource = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8')) {
    const input = JSON.stringify(records); assert.ok(Buffer.byteLength(input) <= 32_000_000);
    const output = execFileSync(process.execPath, ['--no-warnings', '--max-old-space-size=128',
        '--experimental-vm-modules', '--input-type=module', '--eval', helperSource, '--', '--parse-module-map'],
    {input, encoding: 'utf8', timeout: 5000, killSignal: 'SIGKILL', maxBuffer: 1_000_000,
        env: {...process.env, NODE_OPTIONS: '', NODE_PATH: ''}});
    return JSON.parse(output);
}

export function ownedTarget(specifier, parentName, names, builtins = {}) {
    assert.ok(safeName(parentName) && typeof specifier === 'string' && specifier.length <= 4096
        && !/[\u0000-\u0020\u007f?#%\\]/.test(specifier), 'Unsupported import name or URL alias');
    if ((builtins[parentName] ?? []).includes(specifier)) return specifier;
    assert.ok(specifier.startsWith('./') || specifier.startsWith('../'), 'Only owned relative imports or approved builtins are admitted');
    const target = path.posix.normalize(path.posix.join(path.posix.dirname(parentName), specifier));
    assert.ok(!target.startsWith('../') && !path.posix.isAbsolute(target) && names.has(target),
        'Import is absent from the captured source map');
    return target;
}

/** Check parser records without resolving, loading or executing a dependency. */
export function checkDependencyRecords(records, names, builtins = {}) {
    for (const {name, requests} of records) for (const specifier of requests) ownedTarget(specifier, name, names, builtins);
}

function ownerOf(url) {
    if (typeof url !== 'string') return null;
    for (const record of namespaces.values()) if (url.startsWith(record.prefix)) return record;
    return null;
}

/** Synchronous hooks constrain literal and computed imports for the whole process lifetime. */
export function createModuleBoundary(directory, files, entries, builtins = {}) {
    assert.ok(typeof nodeModule.registerHooks === 'function', 'This runtime does not support the owned module boundary');
    assert.ok(namespaces.size < 16, 'Use a fresh bounded reviewer process after sixteen invocations');
    const prefix = pathToFileURL(path.resolve(directory) + path.sep).href;
    assert.ok(!namespaces.has(prefix));
    assert.ok(files instanceof Map && !types.isProxy(files) && files.size > 0 && files.size <= MAX_RECORDS);
    const capturedFiles = new Map(); let total = 0;
    for (const [name, bytes] of Map.prototype.entries.call(files)) {
        assert.ok(safeName(name) && Buffer.isBuffer(bytes) && !types.isProxy(bytes) && bytes.length <= 2_000_000);
        total += bytes.length; assert.ok(total <= MAX_SOURCE_BYTES); capturedFiles.set(name, Buffer.from(bytes));
    }
    assert.ok(Array.isArray(entries) && !types.isProxy(entries) && entries.length <= MAX_RECORDS
        && entries.every(name => safeName(name) && capturedFiles.has(name)));
    assert.ok(builtins && [Object.prototype, null].includes(Object.getPrototypeOf(builtins)) && !types.isProxy(builtins));
    const capturedBuiltins = Object.create(null);
    for (const name of Reflect.ownKeys(builtins)) {
        const descriptor = Object.getOwnPropertyDescriptor(builtins, name);
        assert.ok(safeName(name) && capturedFiles.has(name) && descriptor && Object.hasOwn(descriptor, 'value'));
        const values = descriptor.value;
        assert.ok(Array.isArray(values) && !types.isProxy(values) && values.length <= 2
            && Reflect.ownKeys(values).length === values.length + 1);
        capturedBuiltins[name] = [];
        for (let index = 0; index < values.length; index++) {
            const item = Object.getOwnPropertyDescriptor(values, String(index));
            assert.ok(item && Object.hasOwn(item, 'value') && ['node:crypto', 'node:perf_hooks'].includes(item.value));
            capturedBuiltins[name].push(item.value);
        }
        Object.freeze(capturedBuiltins[name]);
    }
    Object.freeze(capturedBuiltins);
    const record = {prefix, files: capturedFiles, names: new Set(capturedFiles.keys()), entries: new Set(entries),
        importerURL: import.meta.url, builtins: capturedBuiltins, active: true};
    namespaces.set(prefix, record);
    const relativeName = (url, owner) => {
        assert.ok(url.startsWith(owner.prefix));
        const name = path.relative(fileURLToPath(owner.prefix), fileURLToPath(url)).split(path.sep).join('/');
        assert.ok(owner.names.has(name), 'Module is outside the captured source map'); return name;
    };
    if (!hooks) hooks = nodeModule.registerHooks({
        resolve(specifier, context, nextResolve) {
            const parent = ownerOf(context.parentURL);
            if (parent) {
                assert.ok(parent.active, 'The captured invocation is closed');
                const parentName = relativeName(context.parentURL, parent);
                const target = ownedTarget(specifier, parentName, parent.names, parent.builtins);
                if (target.startsWith('node:')) return nextResolve(target, context);
                return {url: pathToFileURL(path.join(fileURLToPath(parent.prefix), target)).href,
                    format: 'module', shortCircuit: true};
            }
            const targetOwner = ownerOf(specifier);
            if (targetOwner) {
                assert.ok(targetOwner.active && context.parentURL === targetOwner.importerURL,
                    'Only the fixed reviewer may enter a captured namespace');
                const name = relativeName(specifier, targetOwner);
                assert.ok(targetOwner.entries.has(name), 'Unsupported captured entry module');
                return {url: specifier, format: 'module', shortCircuit: true};
            }
            return nextResolve(specifier, context);
        },
        load(url, context, nextLoad) {
            const owner = ownerOf(url);
            if (!owner) return nextLoad(url, context);
            assert.ok(owner.active, 'The captured invocation is closed');
            return {format: 'module', source: owner.files.get(relativeName(url, owner)), shortCircuit: true};
        }
    });
    return {
        async importModule(name) {
            assert.ok(record.active && record.entries.has(name), 'Unsupported or closed captured entry');
            return import(pathToFileURL(path.join(fileURLToPath(prefix), name)).href);
        },
        close() {
            record.active = false; record.files.clear();
            // Keep a small denying tombstone. Never expose a namespace to the default loader later.
            record.names.clear(); record.entries.clear();
        }
    };
}

if (process.argv.includes('--parse-module-map')) {
    const chunks = []; let size = 0;
    for await (const chunk of process.stdin) {
        size += chunk.length; assert.ok(size <= 32_000_000); chunks.push(chunk);
    }
    process.stdout.write(JSON.stringify(staticDependencyRecords(JSON.parse(Buffer.concat(chunks).toString()))));
}
