// SPDX-License-Identifier: Apache-2.0
// Repeated synchronous observations at operational CLI boundaries, not a filesystem lock.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { SOURCE_ROOT, assertOutsideCheckout } = require('./authority-paths');
const { reviewedRevision } = require('./authority-revision');
const policy = require('./mainnet-authority');
const same = (a, b) => policy.digest(a) === policy.digest(b);
function requireValue(ok) { if (!ok) throw Error('Pinned source, build or operator input changed; stop and review again'); }
function readBytes(filename) {
    const target = path.resolve(filename), resolved = fs.realpathSync(target);
    const fd = fs.openSync(target, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    try {
        const stat = fs.fstatSync(fd); requireValue(stat.isFile() && stat.size <= 64 * 1024 * 1024);
        const bytes = fs.readFileSync(fd); requireValue(bytes.length <= 64 * 1024 * 1024);
        return { target, resolved, mode: stat.mode & 0o777, bytes, hash: crypto.createHash('sha256').update(bytes).digest('hex') };
    } finally { fs.closeSync(fd); }
}
function createInputBoundary(revision) {
    requireValue(same(reviewedRevision(), revision));
    const compiled = policy.compiledContracts(), compiledHash = policy.digest(compiled), pins = new Map(), directories = new Map();
    function pin(filename) {
        const item = readBytes(filename), old = pins.get(item.target);
        if (old) requireValue(old.resolved === item.resolved && old.mode === item.mode && old.hash === item.hash);
        else pins.set(item.target, { resolved: item.resolved, mode: item.mode, hash: item.hash });
        return item.bytes;
    }
    for (const name of policy.NAMES) {
        const base = path.join(SOURCE_ROOT, `tests/contracts/artifacts/contracts/ascension/${name}.sol/${name}`);
        pin(`${base}.json`); const debug = JSON.parse(pin(`${base}.dbg.json`));
        pin(path.resolve(path.dirname(base), debug.buildInfo));
    }
    for (const build of Object.values(compiled.builds)) for (const source of Object.keys(build.input.sources))
        pin(path.join(SOURCE_ROOT, 'tests/contracts', source.startsWith('@') ? 'node_modules' : '', source));
    function pinDirectory(directory) {
        const target = assertOutsideCheckout(directory), stat = fs.lstatSync(target);
        requireValue(stat.isDirectory() && !stat.isSymbolicLink() && fs.realpathSync(target) === target);
        const identity = `${stat.dev}:${stat.ino}`, prior = directories.get(target);
        requireValue(prior === undefined || prior === identity); directories.set(target, identity);
    }
    function assertCurrent() {
        for (const directory of directories.keys()) pinDirectory(directory);
        requireValue(same(reviewedRevision(), revision));
        for (const [target, before] of pins) {
            const after = readBytes(target);
            requireValue(after.resolved === before.resolved && after.mode === before.mode && after.hash === before.hash);
        }
        requireValue(policy.digest(policy.compiledContracts()) === compiledHash);
    }
    assertCurrent();
    return { compiled, assertCurrent, pinDirectory, readJson: filename => { const bytes = pin(filename); requireValue(bytes.length <= 16 * 1024 * 1024); return JSON.parse(bytes); }, readRaw: filename => {
        const target = assertOutsideCheckout(filename); requireValue(fs.realpathSync(path.dirname(target)) === path.dirname(target));
        const bytes = pin(target); requireValue(bytes.length <= 200002); return bytes.toString('utf8').trim();
    } };
}
module.exports = { createInputBoundary };
