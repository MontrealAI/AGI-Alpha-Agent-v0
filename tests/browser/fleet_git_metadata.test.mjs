// SPDX-License-Identifier: Apache-2.0
// Inert metadata and ordinary Git configuration reads only; no executable fixtures.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {auditGitConfiguration} from './fleet_git_metadata.mjs';

const ordinary = '[core]\n repositoryformatversion = 0\n bare = false\n[gc]\n auto = 0\n';
const residue = '[core]\n sparseCheckout = false\n sparseCheckoutCone = false\n[index]\n sparse = false\n';

test('inactive bounded sparse-checkout residue is admitted without enabling it', () => {
    assert.deepEqual(auditGitConfiguration(ordinary, residue),
        {worktreeConfiguration: 'disabled', ignoredWorktreePresent: true});
    for (const value of ['false', 'NO', 'off', '0']) {
        assert.doesNotThrow(() => auditGitConfiguration(ordinary + '[EXTENSIONS]\n worktreeConfig = ' + value + ' # disabled\n', residue));
    }
});

for (const value of ['true', 'yes', 'on', '1', '', 'unknown', '"false"']) {
    test('ambiguous or active worktreeConfig value is refused: ' + JSON.stringify(value), () => {
        assert.throws(() => auditGitConfiguration(ordinary + '[extensions]\n worktreeConfig = ' + value + '\n', residue));
    });
}

for (const fragment of [
    '[gc]\n auto\n',
    '[gc]\n auto = 1\n',
    '[gc]\n auto = -1\n',
    '[gc]\n auto = "0"\n',
    '[gc]\n auto = unknown\n',
    '[gc]\n auto = 0\n auto = 1\n',
    '[gc]\n auto = 1\n auto = 0\n',
    '[gc]\n recentObjectsHook = unavailable-value\n',
    '[gc "other"]\n auto = 0\n',
    '[extensions]\n worktreeConfig\n',
    '[extensions]\n worktreeConfig = false\n worktreeConfig = true\n',
    '[extensions]\n worktreeConfig = true\n worktreeConfig = false\n',
    '[extensions]\n worktreeConfig = fal\\\nse\n',
    '[extensions]\n worktreeConfig = "false\n"\n',
    '[extensions "other"]\n worktreeConfig = false\n',
    '[extensions.worktreeConfig]\n value = false\n',
    '[core]\n bare = true\n',
    '[include]\n path = unavailable.cfg\n',
    '[includeIf "gitdir:other"]\n path = unavailable.cfg\n',
    '[filter "unavailable"]\n smudge = unavailable-value\n',
    '[protocol "file"]\n allow = always\n',
    '[core]\n fsmonitor = unavailable-value\n',
    '[core]\n worktree = other\n',
    '[remote "origin"]\n promisor = true\n',
    '[remote "origin"]\n uploadpack = unavailable-value\n',
    '[extensions]\n partialClone = origin\n'
]) {
    test('non-admitted metadata is refused as inert text: ' + JSON.stringify(fragment), () => {
        assert.throws(() => auditGitConfiguration(ordinary + fragment, residue));
    });
}

test('ignored file must still contain only benign disabled sparse metadata', () => {
    for (const value of ['[core]\n sparseCheckout = true\n', '[core]\n hooksPath = unavailable\n',
        '[include]\n path = unavailable.cfg\n', '[extensions]\n worktreeConfig = true\n', 'x'.repeat(128001)]) {
        assert.throws(() => auditGitConfiguration(ordinary, value));
    }
});

for (const fragment of [
    '[index]\n sparse\n', '[index]\n sparse = true\n', '[index]\n sparse = unknown\n',
    '[index]\n sparse = "false"\n', '[index]\n sparse = false\n sparse = true\n',
    '[index]\n sparse = true\n sparse = false\n', '[index]\n other = false\n',
    '[index "other"]\n sparse = false\n', '[index.sparse]\n value = false\n'
]) {
    test('active or ambiguous ignored sparse index is refused as inert text: ' + JSON.stringify(fragment), () => {
        assert.throws(() => auditGitConfiguration(ordinary, residue + fragment));
    });
}

test('disabled sparse index is admitted only in the ignored worktree file', () => {
    for (const value of ['false', 'NO', 'off', '0']) {
        assert.doesNotThrow(() => auditGitConfiguration(ordinary, residue + '[index]\n sparse = ' + value + '\n'));
    }
    assert.throws(() => auditGitConfiguration(ordinary + '[index]\n sparse = false\n', residue));
});

test('ordinary sparse-checkout disable residue passes without editing its bytes', () => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fleet-inert-sparse-disable-'));
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
    Object.assign(env, {GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_SYSTEM: os.devNull,
        GIT_CONFIG_GLOBAL: os.devNull, GIT_CONFIG_COUNT: '0', GIT_TERMINAL_PROMPT: '0'});
    const git = (...args) => spawnSync('git', ['-c', 'core.hooksPath=' + os.devNull, '-C', directory, ...args],
        {env, encoding: 'utf8', timeout: 10000});
    try {
        assert.equal(git('init', '--quiet').status, 0);
        fs.writeFileSync(path.join(directory, 'fixture.txt'), 'ordinary inert checkout fixture\n');
        assert.equal(git('add', 'fixture.txt').status, 0);
        assert.equal(git('-c', 'user.name=Inert fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '--quiet', '-m', 'ordinary fixture').status, 0);
        assert.equal(git('config', '--local', 'gc.auto', '0').status, 0);
        assert.equal(git('sparse-checkout', 'disable').status, 0);
        assert.equal(git('config', '--local', '--unset-all', 'extensions.worktreeConfig').status, 0);
        const config = fs.readFileSync(path.join(directory, '.git/config'), 'utf8');
        const ignored = fs.readFileSync(path.join(directory, '.git/config.worktree'), 'utf8');
        assert.match(ignored, /\[index\]\s+sparse = false/);
        assert.doesNotThrow(() => auditGitConfiguration(config, ignored));
        assert.equal(git('config', '--get', 'index.sparse').status, 1);
        assert.equal(fs.readFileSync(path.join(directory, '.git/config.worktree'), 'utf8'), ignored);
    } finally { fs.rmSync(directory, {recursive: true, force: true}); }
});

test('ordinary Git fixture confirms disabled config.worktree is ignored, with an inert enabled control', () => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fleet-inert-git-config-'));
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
    Object.assign(env, {GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_SYSTEM: os.devNull,
        GIT_CONFIG_GLOBAL: os.devNull, GIT_CONFIG_COUNT: '0', GIT_TERMINAL_PROMPT: '0'});
    const git = (...args) => spawnSync('git', ['-c', 'core.hooksPath=' + os.devNull, '-C', directory, ...args],
        {env, encoding: 'utf8', timeout: 10000});
    try {
        assert.equal(git('init', '--quiet').status, 0);
        assert.equal(git('config', '--local', 'gc.auto', '0').status, 0);
        const configPath = path.join(directory, '.git/config');
        const original = fs.readFileSync(configPath, 'utf8');
        fs.writeFileSync(path.join(directory, '.git/config.worktree'), residue);
        assert.doesNotThrow(() => auditGitConfiguration(original, residue));
        assert.equal(git('config', '--get', 'core.sparseCheckout').status, 1);
        fs.writeFileSync(configPath, original + '[extensions]\n worktreeConfig = false\n');
        assert.doesNotThrow(() => auditGitConfiguration(fs.readFileSync(configPath, 'utf8'), residue));
        assert.equal(git('config', '--get', 'core.sparseCheckout').status, 1);
        fs.writeFileSync(configPath, original + '[extensions]\n worktreeConfig = true\n');
        assert.throws(() => auditGitConfiguration(fs.readFileSync(configPath, 'utf8'), residue));
        const enabled = git('config', '--get', 'core.sparseCheckout');
        assert.equal(enabled.status, 0); assert.equal(enabled.stdout.trim(), 'false');
    } finally { fs.rmSync(directory, {recursive: true, force: true}); }
});
