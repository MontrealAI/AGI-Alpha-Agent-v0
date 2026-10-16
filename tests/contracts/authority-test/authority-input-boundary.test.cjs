// SPDX-License-Identifier: Apache-2.0
// Tiny input fixtures exercise revalidation; they do not bypass or qualify operational source anchoring.
const { test } = require('node:test');
const assert = require('assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');
const filename = path.resolve(__dirname, '../scripts/authority-input-boundary.js');
function fixture(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-input-boundary-')); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const artifact = path.join(root, 'tests/contracts/artifacts/contracts/ascension/Fixture.sol/Fixture.json'); fs.mkdirSync(path.dirname(artifact), { recursive: true });
    fs.writeFileSync(artifact, '{}'); fs.writeFileSync(artifact.replace('.json', '.dbg.json'), JSON.stringify({ buildInfo: '../../../build-info/fixture.json' }));
    const build = path.resolve(path.dirname(artifact), '../../../build-info/fixture.json'); fs.mkdirSync(path.dirname(build), { recursive: true }); fs.writeFileSync(build, '{}');
    const source = path.join(root, 'tests/contracts/contracts/Fixture.sol'); fs.mkdirSync(path.dirname(source), { recursive: true }); fs.writeFileSync(source, '// fixture');
    const input = path.join(root, 'command.json'); fs.writeFileSync(input, '{"nonce":1}\n');
    const revision = { commit: 'a'.repeat(40), tree: 'b'.repeat(40), lockSha256: 'c'.repeat(64) };
    const compiled = { builds: { test: { input: { sources: { 'contracts/Fixture.sol': { content: '// fixture' } } } } } };
    const state = { revision, compiled }, module = { exports: {} };
    vm.runInNewContext(fs.readFileSync(filename, 'utf8'), { module, exports: module.exports, Buffer, require: name => {
        if (name === './authority-paths') return { SOURCE_ROOT: root, assertOutsideCheckout: value => {
            const target = path.resolve(value), resolved = fs.realpathSync(target);
            if ([target, resolved].some(p => p === root || p.startsWith(root + path.sep))) throw Error('Outside checkout required'); return target;
        } };
        if (name === './authority-revision') return { reviewedRevision: () => state.revision };
        if (name === './mainnet-authority') return { NAMES: ['Fixture'], digest: x => crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex'), compiledContracts: () => state.compiled };
        return require(name);
    } }, { filename });
    const boundary = module.exports.createInputBoundary(revision); boundary.readJson(input);
    return { root, artifact, build, source, input, state, boundary };
}
test('pinned boundary accepts unchanged validated bytes after an asynchronous read', async t => {
    const f = fixture(t); await Promise.resolve(); f.boundary.assertCurrent(); assert.equal(f.boundary.readJson(f.input).nonce, 1);
});
for (const kind of ['artifact', 'build', 'source', 'input']) test(`pinned boundary rejects late ${kind} bytes before a capability is written`, async t => {
    const f = fixture(t); let capability = false;
    await Promise.resolve().then(() => fs.appendFileSync(f[kind], '\n'));
    assert.throws(() => { f.boundary.assertCurrent(); capability = true; }, /Pinned source/); assert.equal(capability, false);
});
test('pinned boundary rejects late source revision and reconstructed compiler drift', t => {
    const f = fixture(t), original = f.state.revision; f.state.revision = { ...original, tree: 'd'.repeat(40) };
    assert.throws(f.boundary.assertCurrent, /Pinned source/); f.state.revision = original;
    f.state.compiled = { ...f.state.compiled, injected: true }; assert.throws(f.boundary.assertCurrent, /Pinned source/);
});
test('operational CLIs require post-await input checks without a production bypass switch', () => {
    for (const name of ['mainnet-authority.js', 'authority-cli.js', 'authority-session.js', 'authority-verification-package.js']) {
        const text = fs.readFileSync(path.resolve(__dirname, '../scripts', name), 'utf8');
        assert.match(text, /createInputBoundary\(revision\)/); assert.match(text, /boundary\.assertCurrent\(\)/);
        assert.doesNotMatch(text, /process\.env\.[A-Z_]*(?:SKIP_SOURCE|TRUST_SOURCE|BYPASS)/);
    }
    const text = fs.readFileSync(path.resolve(__dirname, '../scripts/authority-session.js'), 'utf8');
    assert.match(text, /next => \{ assertSession\(\); durable = append/); assert.match(text, /assertSession\(\);\s*const returned = await relay\(raw\)/);
    assert.match(text, /same\(loadSession\(target, plan, revision\), durable/);
});

test('signed raw inputs reject reviewed-source paths and outside symlink aliases', t => {
    const f = fixture(t); assert.throws(() => f.boundary.readRaw(f.input), /Outside checkout/);
    const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-raw-outside-')); t.after(() => fs.rmSync(outside, { recursive: true, force: true }));
    fs.symlinkSync(f.root, path.join(outside, 'alias'), 'dir');
    assert.throws(() => f.boundary.readRaw(path.join(outside, 'alias/command.json')), /Outside checkout/);
    const raw = path.join(outside, 'signed.txt'); fs.writeFileSync(raw, '0x02abcd\n'); assert.equal(f.boundary.readRaw(raw), '0x02abcd');
});
test('pinned mutable directories reject symlink replacement and changed real-directory identity', t => {
    const f = fixture(t), outside = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-directory-pin-'));
    t.after(() => fs.rmSync(outside, { recursive: true, force: true }));
    const directory = path.join(outside, 'session'), displaced = path.join(outside, 'saved'); fs.mkdirSync(directory); f.boundary.pinDirectory(directory);
    fs.renameSync(directory, displaced); fs.mkdirSync(directory); assert.throws(f.boundary.assertCurrent, /Pinned source/);
    fs.rmdirSync(directory); fs.symlinkSync(displaced, directory, 'dir'); assert.throws(f.boundary.assertCurrent, /Pinned source/);
});
test('all operational CLI error handlers redact malformed private JSON', async t => {
    const { createRequire } = require('module'), outside = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-json-redaction-'));
    t.after(() => fs.rmSync(outside, { recursive: true, force: true }));
    for (const [name, args] of [['authority-cli.js', ['preflight', 'plan', 'input', path.join(outside, 'report')]],
        ['authority-session.js', ['prepare', 'input', path.join(outside, 'session-report')]],
        ['authority-verification-package.js', ['plan', 'plan', path.join(outside, 'package')]],
        ['mainnet-authority.js', ['plan', 'input', path.join(outside, 'plan')]]]) {
        const file = path.resolve(__dirname, '../scripts', name), actualRequire = createRequire(file), module = { exports: {} }, messages = [];
        const localRequire = dep => dep === './authority-revision' ? { reviewedRevision: () => ({}) } : dep === './authority-input-boundary' ?
            { createInputBoundary: () => ({ pinDirectory() {}, readJson() { return JSON.parse('ALPHA_PRIVATE_JSON_SENTINEL'); } }) } : actualRequire(dep);
        localRequire.main = module;
        const processFixture = { argv: ['node', file, ...args], env: {}, stdout: { write: text => messages.push(text) }, exitCode: 0 };
        vm.runInNewContext(fs.readFileSync(file, 'utf8'), { module, exports: module.exports, require: localRequire, __dirname: path.dirname(file),
            process: processFixture, console: { error: value => messages.push(String(value)), log: value => messages.push(String(value)) }, Buffer }, { filename: file });
        await new Promise(resolve => setImmediate(resolve));
        assert.equal(processFixture.exitCode, 1); assert.ok(messages.length > 0); assert.ok(!messages.join('\n').includes('ALPHA_PRIVATE_JSON_SENTINEL'));
    }
});
