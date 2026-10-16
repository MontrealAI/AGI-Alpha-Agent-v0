// SPDX-License-Identifier: Apache-2.0
// V2-only offline source observer. Historical v1 helpers remain unchanged.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const cp = require('child_process');
const { SOURCE_ROOT } = require('./authority-paths');
function need(ok, message) { if (!ok) throw Error(message); }
function gitEnvironment() {
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.toUpperCase().startsWith('GIT_')));
    return { ...env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_SYSTEM: '/dev/null', GIT_CONFIG_GLOBAL: '/dev/null',
        GIT_NO_REPLACE_OBJECTS: '1', GIT_NO_LAZY_FETCH: '1', GIT_TERMINAL_PROMPT: '0', GIT_OPTIONAL_LOCKS: '0', GIT_ATTR_NOSYSTEM: '1' };
}
function gitRead(args, root = SOURCE_ROOT, input) {
    need(['rev-parse', 'ls-tree', 'ls-files', 'cat-file'].includes(args[0]), 'Only source-observation Git plumbing is supported');
    return cp.execFileSync('git', ['--no-replace-objects', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
        '-c', 'core.excludesFile=/dev/null', '-c', 'core.attributesFile=/dev/null', '-c', 'protocol.allow=never', ...args],
    { cwd: root, env: gitEnvironment(), encoding: 'utf8', input, timeout: 30000, maxBuffer: 16 * 1024 * 1024, stdio: ['pipe', 'pipe', 'pipe'] });
}
function reviewedRevision(directory = SOURCE_ROOT) {
    const root = fs.realpathSync(directory), metadata = path.join(root, '.git');
    // A standalone complete checkout is the supported operational boundary. Linked worktrees,
    // alternate object stores and repository config includes need a separate closure model.
    need(fs.lstatSync(metadata).isDirectory() && fs.realpathSync(metadata) === metadata, 'Standalone complete Git checkout required');
    for (const name of ['config', 'config.worktree']) {
        const file = path.join(metadata, name); if (!fs.existsSync(file)) continue;
        need(fs.lstatSync(file).isFile() && fs.realpathSync(file) === file && fs.statSync(file).size <= 65536, 'Ordinary bounded repository configuration required');
        need(!/^\s*\[\s*include(?:if)?(?:\s|"|\])/im.test(fs.readFileSync(file, 'utf8')), 'Repository configuration includes are unsupported');
    }
    for (const name of ['alternates', 'http-alternates']) need(!fs.existsSync(path.join(metadata, 'objects/info', name)), 'Alternate object stores are unsupported');
    const git = (args, input) => gitRead(args, root, input);
    need(fs.realpathSync(git(['rev-parse', '--show-toplevel']).trim()) === root, 'Observed Git toplevel differs from source root');
    need(git(['rev-parse', '--is-shallow-repository']).trim() === 'false', 'Complete non-shallow checkout required');
    need(git(['rev-parse', '--show-object-format']).trim() === 'sha1', 'SHA1 source object format required');
    const commit = git(['rev-parse', 'HEAD']).trim(), tree = git(['rev-parse', 'HEAD^{tree}']).trim();
    need(/^[0-9a-f]{40}$/.test(commit) && /^[0-9a-f]{40}$/.test(tree), 'Exact source commit/tree required');
    const entries = git(['ls-tree', '-r', '-z', '--full-tree', commit]).split('\0').filter(Boolean).map(entry => {
        const match = /^([0-7]{6}) blob ([a-f0-9]{40})\t([\s\S]+)$/.exec(entry);
        need(match && ['100644', '100755', '120000'].includes(match[1]), 'Unsupported tracked entry or submodule');
        return { mode: match[1], hash: match[2], name: match[3] };
    });
    need(entries.length > 0 && entries.length <= 20000, 'Bounded complete source tree required');
    const expected = new Map(entries.map(e => [e.name, `${e.mode}:${e.hash}`]));
    need(expected.size === entries.length, 'Duplicate source paths');
    // Require every HEAD blob to exist locally. Missing promised objects must fail without fetch.
    const objects = git(['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'], entries.map(e => e.hash).join('\n') + '\n').trimEnd().split('\n');
    need(objects.length === entries.length && objects.every((line, i) => new RegExp(`^${entries[i].hash} blob [0-9]+$`).test(line)), 'Missing local source objects; acquire a complete checkout separately');
    function checkIndex() {
        const flags = git(['ls-files', '-v', '-z']).split('\0').filter(Boolean);
        need(flags.every(s => s[0] !== 'S' && !/[a-z]/.test(s[0])), 'Assume-unchanged or skip-worktree flags are unsupported');
        const index = git(['ls-files', '--stage', '-z']).split('\0').filter(Boolean).map(s => /^([0-7]{6}) ([0-9a-f]{40}) 0\t([\s\S]+)$/.exec(s));
        need(index.length === expected.size && index.every(m => m && expected.get(m[3]) === `${m[1]}:${m[2]}`), 'Source index differs from reviewed HEAD');
        need(git(['ls-files', '--others', '--exclude-standard', '-z']) === '', 'Untracked source files are unsupported');
    }
    function checkBytes() {
        let total = 0;
        for (const entry of entries) {
            const file = path.resolve(root, entry.name);
            need(file.startsWith(root + path.sep) && fs.realpathSync(path.dirname(file)) === path.dirname(file), 'Tracked source parent escapes or aliases checkout');
            const stat = fs.lstatSync(file); let bytes;
            if (entry.mode === '120000') { need(stat.isSymbolicLink(), 'Tracked symlink type changed'); bytes = Buffer.from(fs.readlinkSync(file)); }
            else {
                need(stat.isFile() && !stat.isSymbolicLink() && Boolean(stat.mode & 0o100) === (entry.mode === '100755'), 'Tracked source type or executable mode changed');
                need(stat.size <= 64 * 1024 * 1024, 'Source file exceeds observation bound');
                const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
                try { bytes = fs.readFileSync(fd); } finally { fs.closeSync(fd); }
            }
            total += bytes.length; need(total <= 512 * 1024 * 1024, 'Source tree exceeds observation bound');
            need(crypto.createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex') === entry.hash, 'Raw tracked source bytes differ from reviewed HEAD');
        }
    }
    checkIndex(); checkBytes();
    const lock = path.join(root, 'tests/contracts/package-lock.json');
    need(expected.has('tests/contracts/package-lock.json'), 'Tracked contract lockfile required');
    const lockSha256 = crypto.createHash('sha256').update(fs.readFileSync(lock)).digest('hex');
    need(git(['rev-parse', 'HEAD']).trim() === commit && git(['rev-parse', 'HEAD^{tree}']).trim() === tree, 'Source changed during observation');
    checkIndex(); checkBytes();
    return { commit, tree, lockSha256 };
}
module.exports = { reviewedRevision, gitEnvironment, gitRead };
