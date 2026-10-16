// SPDX-License-Identifier: Apache-2.0
// Tiny disposable Git repositories test observation only, never candidate CLI qualification.
const { test } = require('node:test');
const assert = require('assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');
const cp = require('child_process');
const crypto = require('crypto');
const source = require('../scripts/authority-revision');
function repo(t, label = 'source') {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-source-observer-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const git = (...args) => cp.execFileSync('git', args, { cwd: root, env: source.gitEnvironment(), encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
    git('init', '--quiet'); fs.mkdirSync(path.join(root, 'tests/contracts'), { recursive: true });
    fs.writeFileSync(path.join(root, 'tests/contracts/package-lock.json'), '{}\n'); fs.writeFileSync(path.join(root, 'tracked.txt'), label + '\n');
    const commit = () => { git('add', '.'); git('-c', 'user.name=Disposable Alpha Test', '-c', 'user.email=test@example.invalid', 'commit', '--quiet', '-m', 'Source observer fixture only'); };
    commit(); return { root, git, commit };
}
function withEnv(values, fn) {
    const old = Object.fromEntries(Object.keys(values).map(k => [k, process.env[k]])); Object.assign(process.env, values);
    try { return fn(); } finally { for (const [k, v] of Object.entries(old)) if (v === undefined) delete process.env[k]; else process.env[k] = v; }
}
test('v2 observer binds actual clean raw source and tracked lock without changing legacy helper', t => {
    const r = repo(t), observed = source.reviewedRevision(r.root);
    assert.equal(observed.commit, r.git('rev-parse', 'HEAD')); assert.equal(observed.tree, r.git('rev-parse', 'HEAD^{tree}'));
    assert.equal(observed.lockSha256, crypto.createHash('sha256').update('{}\n').digest('hex'));
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.resolve(__dirname, '../scripts/mainnet.js'))).digest('hex'), 'd5f69f8e6f2e8869ae351b623d935674596442628a666d8f6819c31bf5550360');
});
test('v2 observer removes inherited repository/index/config/object overrides and forces no lazy fetch', t => {
    const r = repo(t), other = repo(t, 'unrelated'), original = cp.execFileSync; let calls = 0;
    cp.execFileSync = function(command, args, options) {
        if (command === 'git') { calls++; assert.equal(options.env.GIT_NO_LAZY_FETCH, '1'); assert.equal(options.env.GIT_NO_REPLACE_OBJECTS, '1');
            for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_KEY_0', 'GIT_CONFIG_VALUE_0']) assert.equal(options.env[key], undefined); }
        return original.call(this, command, args, options);
    };
    try {
        const actual = withEnv({ GIT_DIR: path.join(other.root, '.git'), GIT_WORK_TREE: other.root, GIT_INDEX_FILE: path.join(other.root, '.git/index'),
            GIT_OBJECT_DIRECTORY: path.join(other.root, '.git/objects'), GIT_ALTERNATE_OBJECT_DIRECTORIES: path.join(other.root, '.git/objects'),
            GIT_CONFIG_COUNT: '1', GIT_CONFIG_KEY_0: 'core.worktree', GIT_CONFIG_VALUE_0: other.root, GIT_NO_LAZY_FETCH: '0' }, () => source.reviewedRevision(r.root));
        assert.ok(calls > 0); assert.equal(actual.commit, r.git('rev-parse', 'HEAD'));
    } finally { cp.execFileSync = original; }
});
for (const flag of ['--assume-unchanged', '--skip-worktree']) test(`v2 observer rejects hidden index flag ${flag}`, t => {
    const r = repo(t); r.git('update-index', flag, 'tracked.txt'); fs.writeFileSync(path.join(r.root, 'tracked.txt'), 'hidden change\n');
    assert.throws(() => source.reviewedRevision(r.root), /Assume-unchanged or skip-worktree/);
});
test('v2 observer rejects raw line-ending changes despite Git normalization', t => {
    const r = repo(t); fs.writeFileSync(path.join(r.root, '.gitattributes'), 'tracked.txt text eol=lf\n'); r.commit();
    fs.writeFileSync(path.join(r.root, 'tracked.txt'), 'source\r\n'); r.git('add', 'tracked.txt');
    assert.throws(() => source.reviewedRevision(r.root), /Raw tracked source bytes/);
});
test('v2 observer rejects executable mode drift even when core.filemode is false', t => {
    const r = repo(t); r.git('config', 'core.filemode', 'false'); fs.chmodSync(path.join(r.root, 'tracked.txt'), 0o755);
    assert.throws(() => source.reviewedRevision(r.root), /executable mode/);
});
test('v2 observer never executes local clean filters or fsmonitor while rejecting dirty bytes', t => {
    const r = repo(t), sentinel = path.join(r.root, '.git', 'FILTER_EXECUTED');
    fs.writeFileSync(path.join(r.root, '.gitattributes'), 'tracked.txt filter=sentinel\n'); r.commit();
    r.git('config', 'filter.sentinel.clean', `touch '${sentinel}'; cat`); r.git('config', 'core.fsmonitor', `touch '${sentinel}'`);
    assert.equal(source.reviewedRevision(r.root).commit.length, 40); assert.equal(fs.existsSync(sentinel), false);
    fs.writeFileSync(path.join(r.root, 'tracked.txt'), 'changed\n');
    assert.throws(() => source.reviewedRevision(r.root), /Raw tracked source bytes/); assert.equal(fs.existsSync(sentinel), false);
});
test('v2 observer rejects staged and untracked changes', t => {
    const a = repo(t); fs.writeFileSync(path.join(a.root, 'tracked.txt'), 'staged\n'); a.git('add', 'tracked.txt');
    assert.throws(() => source.reviewedRevision(a.root), /index differs/);
    const b = repo(t); fs.writeFileSync(path.join(b.root, 'new.txt'), 'untracked'); assert.throws(() => source.reviewedRevision(b.root), /Untracked/);
});
test('v2 observer refuses a missing promised tree without invoking a local fetch transport', t => {
    const r = repo(t), tree = r.git('rev-parse', 'HEAD^{tree}'), sentinel = path.join(r.root, '.git', 'FETCH_ATTEMPTED'), upload = path.join(r.root, '.git', 'local-upload-pack');
    fs.writeFileSync(upload, `#!/bin/sh\nprintf attempted > '${sentinel}'\nexit 1\n`, { mode: 0o700 });
    r.git('config', 'extensions.partialClone', 'origin'); r.git('config', 'remote.origin.promisor', 'true');
    r.git('config', 'remote.origin.url', r.root); r.git('config', 'remote.origin.uploadpack', upload); r.git('config', 'protocol.file.allow', 'always');
    fs.unlinkSync(path.join(r.root, '.git/objects', tree.slice(0, 2), tree.slice(2)));
    assert.throws(() => withEnv({ GIT_NO_LAZY_FETCH: '0' }, () => source.reviewedRevision(r.root))); assert.equal(fs.existsSync(sentinel), false);
});
test('v2 observer requires local HEAD blobs even when matching working bytes exist', t => {
    const r = repo(t), blob = r.git('rev-parse', 'HEAD:tracked.txt');
    fs.unlinkSync(path.join(r.root, '.git/objects', blob.slice(0, 2), blob.slice(2)));
    assert.throws(() => source.reviewedRevision(r.root), /Missing local source objects/);
});
test('v2 observer rejects shallow checkout, config includes and alternate object stores', t => {
    const a = repo(t); fs.writeFileSync(path.join(a.root, '.git/shallow'), a.git('rev-parse', 'HEAD') + '\n'); assert.throws(() => source.reviewedRevision(a.root), /non-shallow/);
    const b = repo(t); fs.appendFileSync(path.join(b.root, '.git/config'), '\n[include]\npath = /nonexistent-unused-fixture-config\n'); assert.throws(() => source.reviewedRevision(b.root), /configuration includes/);
    const c = repo(t); fs.writeFileSync(path.join(c.root, '.git/objects/info/alternates'), '/nonexistent-unused-fixture-objects\n'); assert.throws(() => source.reviewedRevision(c.root), /Alternate object/);
});
test('v2 observer rejects linked roots and symlinked tracked parent directories', t => {
    const r = repo(t); assert.throws(() => source.reviewedRevision(path.join(r.root, 'tests')), /ENOENT|Standalone/);
    fs.renameSync(path.join(r.root, 'tests/contracts'), path.join(r.root, '.git/saved-contracts'));
    fs.symlinkSync(path.join(r.root, '.git/saved-contracts'), path.join(r.root, 'tests/contracts'), 'dir');
    fs.appendFileSync(path.join(r.root, '.git/info/exclude'), '\ntests/contracts\n');
    assert.throws(() => source.reviewedRevision(r.root), /parent escapes or aliases/);
});
test('all v2 operational and native source checks route through the offline observer', () => {
    for (const name of ['mainnet-authority.js', 'authority-cli.js', 'authority-session.js', 'authority-verification-package.js']) {
        const text = fs.readFileSync(path.resolve(__dirname, '../scripts', name), 'utf8');
        assert.match(text, /require\('\.\/authority-revision'\)\.reviewedRevision\(\)/); assert.doesNotMatch(text, /legacy\.reviewedRevision/);
    }
    for (const name of ['clean-checkout-cli.cjs', 'native-ci-evidence.cjs']) {
        const text = fs.readFileSync(path.join(__dirname, name), 'utf8');
        assert.match(text, /require\('\.\.\/scripts\/authority-revision'\)/); assert.doesNotMatch(text, /execFileSync\('git'|legacy\.reviewedRevision/);
    }
    const workflow = fs.readFileSync(path.resolve(__dirname, '../../../.github/workflows/alpha-authority-v2.yml'), 'utf8');
    assert.match(workflow, /scripts\/authority-revision'\)\.reviewedRevision\(\)/); assert.doesNotMatch(workflow, /git status|git diff/);
});
