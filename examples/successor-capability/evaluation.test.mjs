// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { apparatus } from './apparatus.mjs';
import { construct } from './constructor.mjs';
import { freezeCapability } from './capability-package.mjs';
import { evaluateFrozenReuse, compareCapability, buildSuccessor,
    evaluateConstructorGeneralization, sensingCorrectionBaseline, proveRecurringObstruction } from './evaluation.mjs';

let promise;
function example() {
    promise ||= (async () => {
        const app = apparatus('shielded');
        const result = construct(app);
        assert.equal(result.status, 'qualified');
        return freezeCapability(app, result);
    })();
    return promise;
}

async function sourceDigest() {
    const hash = createHash('sha256');
    for (const name of ['apparatus.mjs', 'typed-runtime.mjs', 'independent-checker.mjs',
        'constructor.mjs', 'capability-package.mjs', 'evaluation.mjs']) {
        hash.update(name).update(await readFile(new URL(name, import.meta.url)));
    }
    return hash.digest('hex');
}

test('frozen package executes three new task types without changing its bytes', async () => {
    const pkg = await example();
    const before = JSON.stringify(pkg);
    const report = await evaluateFrozenReuse(pkg, {seed: 100});
    assert.equal(report.status, 'PASS');
    assert.deepEqual(report.cases.map(item => item.kind),
        ['threshold-screening', 'inverse-design', 'constrained-selection']);
    assert.equal(report.packageDigestBefore, report.packageDigestAfter);
    assert.equal(JSON.stringify(pkg), before);
    assert.equal(report.measurements.length, 24);
    assert.ok(report.measurements.every(item => item.valid && item.actual === item.expected));
    assert.equal(report.freeze.order, 'package-frozen-before-seed-and-case-generation');
});

test('changing a valid candidate cannot relabel the same hidden tasks as fresh', async () => {
    const original = await example();
    const first = await evaluateFrozenReuse(original, {seed: 200});
    const changed = apparatus('shielded');
    changed.primitives[0].cost++;
    const other = await freezeCapability(changed, construct(changed));
    assert.notEqual(original.digest, other.digest);
    const second = await evaluateFrozenReuse(other, {seed: 200, exposedCaseIds: first.exposedCaseIds});
    assert.deepEqual(first.cases.map(item => item.id), second.cases.map(item => item.id));
    assert.ok(second.cases.every(item => item.exposure === 'previously-exposed-regression'));
});

test('all matched comparison costs and a competent sensing comparator remain visible', async () => {
    const pkg = await example();
    const report = await compareCapability(pkg);
    assert.equal(report.runs[1].status, 'qualified');
    assert.equal(report.relation, 'tie');
    assert.equal(report.costs.coldStart + report.costs.uses * report.costs.operationPerUse,
        report.costs.totalAtHorizon);
    const sensing = await sensingCorrectionBaseline(pkg, pkg.search.limits);
    assert.equal(sensing.status, 'qualified');
    assert.ok(sensing.best.ast.installations.some(id => id.startsWith('sense-')));
    assert.ok(sensing.ledger.installation > 0);
    assert.ok(sensing.tested > 1);
    await assert.rejects(compareCapability(pkg, {searchOptions: {maxStates: 1}}), /effective construction limits/);
});

test('reservoir successor retains the computed old-scope failure and accepts old plus new tasks', async () => {
    const pkg = await example();
    const report = await buildSuccessor(pkg, {seed: 300});
    assert.equal(report.oldScope.status, 'FAIL');
    assert.ok(report.oldScope.diagnostic.envelope.errorBound > 0);
    assert.equal(report.oldScope.diagnostic.independent.ok, false);
    assert.ok(report.oldScope.diagnostic.reservoirMeasurement.error > 0);
    assert.equal(report.status, 'PASS');
    assert.equal(report.obligations.preserved, true);
    assert.equal(report.newFunction.accepted, true);
    assert.equal(report.newFunction.operation, 'reservoir');
    assert.equal(report.reuse.cases.length, 6);
    assert.equal(report.costs.cumulative, report.costs.ancestor + report.costs.remaining);
    assert.ok(report.invalidated.includes('parent scope certificate'));
});

test('constructor final families require full source freeze and add an active structural reservoir', async () => {
    await assert.rejects(evaluateConstructorGeneralization({seed: 400}), /source-closure SHA-256/);
    const digest = await sourceDigest();
    const report = await evaluateConstructorGeneralization({seed: 400, constructorDigest: digest});
    assert.equal(report.freeze.constructorDigest, digest);
    assert.equal(report.order, 'constructor-frozen-before-structural-case-generation');
    assert.equal(report.cases.length, 3);
    for (const item of report.cases) {
        assert.equal(item.publicApparatus.channels.length, apparatus(item.topology).channels.length + 1);
        const relay = item.publicApparatus.channels.find(channel => channel.id.startsWith('relay-'));
        assert.ok(relay.initial > 0 && relay.drift > 0);
    }
    assert.equal(report.status, 'PASS');
});

test('budget exhaustion in a successor remains inconclusive with earlier scope failure retained', async () => {
    const report = await buildSuccessor(await example(), {seed: 500, searchOptions: {maxStates: 1}});
    assert.equal(report.status, 'INCONCLUSIVE');
    assert.equal(report.oldScope.status, 'FAIL');
    assert.equal(report.package, undefined);
    assert.match(report.reason, /No qualifying construction found within budget/);
});

test('a tolerance-qualified package can fail new task purposes; mixed outcomes aggregate FAIL', async () => {
    const app = apparatus('shielded');
    app.tolerance = 100;
    const pkg = await freezeCapability(app, construct(app));
    const report = await evaluateFrozenReuse(pkg, {seed: 1});
    assert.equal(report.status, 'FAIL');
    assert.ok(report.cases.some(item => item.status === 'FAIL'));
    assert.ok(report.cases.some(item => item.status === 'PASS'));
    assert.equal(report.packageDigestBefore, report.packageDigestAfter);
});


test('independent obstruction proof detects uncontrollable recurring coupling and never claims a package', async () => {
    const app = apparatus('referenced');
    assert.equal(proveRecurringObstruction(app), null);
    app.channels.find(channel => channel.id === 'local').drift = 1;
    const proof = proveRecurringObstruction(app);
    assert.equal(proof.channel, 'local');
    assert.ok(proof.strictLowerBound > app.tolerance);
    assert.equal(proof.modelOnly, true);
});
