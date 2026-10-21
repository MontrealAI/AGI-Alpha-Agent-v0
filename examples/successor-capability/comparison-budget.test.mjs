// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {apparatus, expandApparatus, TOPOLOGIES} from './apparatus.mjs';
import {construct, advanceSearch, importSearchCheckpoint} from './constructor.mjs';
import {freezeCapability, importCapability, projectedFreezeCostCapability,
    verificationCostCapability} from './capability-package.mjs';
import {buildSuccessor, compareCapability, evaluateConstructorGeneralization, runEvaluation} from './evaluation.mjs';

let parentPromise;
function parent() {
    parentPromise ||= (async () => {
        const app = apparatus('shielded');
        return freezeCapability(app, construct(app));
    })();
    return parentPromise;
}

async function sourceDigest() {
    const hash = createHash('sha256');
    for (const name of ['apparatus.mjs', 'typed-runtime.mjs', 'independent-checker.mjs',
        'constructor.mjs', 'capability-package.mjs', 'evaluation.mjs']) {
        hash.update(name).update(await readFile(new URL(name, import.meta.url)));
    }
    return hash.digest('hex');
}

test('static freeze reservation reproduces actual replay ledgers for every topology and an inherited package', async () => {
    for (const topology of TOPOLOGIES) {
        const app = apparatus(topology), result = construct(app);
        const projected = projectedFreezeCostCapability(app, result);
        assert.deepEqual((await freezeCapability(app, result)).costLedger, projected);
    }
    const first = await parent(), app = expandApparatus(first.apparatus);
    const result = construct(app, {parent: first});
    assert.deepEqual((await freezeCapability(app, result, {parent: first})).costLedger,
        projectedFreezeCostCapability(app, result, {parent: first}));
});

test('an unfunded optional scratch freeze cannot discard an accepted successor or invent comparator savings', async () => {
    const first = await parent(), original = JSON.stringify(first);
    for (const maxCost of [1300, 1400, 1500, 1600]) {
        const report = await buildSuccessor(first, {seed: 123, searchOptions: {maxCost}});
        assert.equal(report.status, 'PASS');
        assert.equal(report.package.costLedger.total, 1157);
        assert.deepEqual(await importCapability(report.package), report.package);
        assert.equal(report.obligations.preserved, true);
        assert.equal(report.newFunction.accepted, true);
        assert.equal(report.scratch.status, 'exhausted');
        assert.equal(report.scratch.qualification.status, 'inconclusive');
        assert.equal(report.scratch.freeze.status, 'not-run');
        assert.equal(report.scratch.ledger.total, maxCost === 1300 ? 1298 : 1399);
        assert.ok(report.scratch.ledger.total <= maxCost);
        assert.equal(report.scratch.acceptanceLedger, null);
        assert.equal(report.costs.scratchQualified, false);
        assert.equal(report.costs.scratchConstructionWork, report.scratch.ledger.total);
        assert.equal(report.costs.scratchAfterAcceptance, report.scratch.ledger.total);
        assert.equal(report.scratchReuse, null);
        for (const key of ['constructionFromScratch', 'remainingSaving', 'cumulativeSaving']) {
            assert.equal(report.costs[key], null);
        }
        if (maxCost > 1300) {
            assert.equal(report.scratch.constructionStatus, 'qualified');
            assert.equal(report.scratch.freeze.requiredTotal, 2806);
            assert.equal(report.scratch.freeze.unperformedFreezeWork, 1407);
        }
    }
    assert.equal(JSON.stringify(first), original);
});

test('matched inherited-package comparison reports unfunded classical and scratch acceptance as inconclusive', async () => {
    const successor = await buildSuccessor(await parent(), {seed: 123, searchOptions: {maxCost: 1500}});
    const pkg = successor.package, before = JSON.stringify(pkg);
    const report = await compareCapability(pkg);
    assert.equal(report.status, 'INCONCLUSIVE');
    assert.equal(report.relation, 'baseline-inconclusive');
    assert.equal(report.runs[0].status, 'qualified');
    assert.equal(report.runs[0].ledger.total, 1157);
    for (const run of report.runs.slice(1)) {
        assert.equal(run.status, 'exhausted');
        assert.equal(run.constructionStatus, 'qualified');
        assert.equal(run.qualification.status, 'inconclusive');
        assert.equal(run.freeze.status, 'not-run');
        assert.equal(run.freeze.requiredTotal, 2806);
        assert.equal(run.ledger.total, 1399);
        assert.ok(run.ledger.total <= pkg.search.limits.maxCost);
    }
    assert.equal(JSON.stringify(pkg), before);
});

test('optional scratch acceptance requires the complete freeze budget and retains its raw replayable constructor result', async () => {
    const first = await parent();
    const below = await buildSuccessor(first, {seed: 123, searchOptions: {maxCost: 2805}});
    assert.equal(below.costs.scratchQualified, false);
    assert.equal(below.scratch.freeze.status, 'not-run');
    const exact = await buildSuccessor(first, {seed: 123, searchOptions: {maxCost: 2806}});
    assert.equal(exact.status, 'PASS');
    assert.equal(exact.scratch.status, 'qualified');
    assert.equal(exact.scratch.ledger.total, 1399);
    assert.equal(exact.scratch.acceptanceLedger.total, 2806);
    assert.equal(exact.scratch.freeze.status, 'completed');
    assert.equal(exact.costs.scratchQualified, true);
    assert.equal(exact.costs.constructionFromScratch, 2806);
    assert.equal(exact.costs.scratchConstructionWork, 2806);
    assert.equal(exact.costs.scratchAfterAcceptance, 2806 + exact.scratchReuse.ledger.total);
    const replayed = await freezeCapability(exact.package.apparatus, exact.scratch);
    assert.deepEqual(replayed.costLedger, exact.scratch.acceptanceLedger);
});

test('vertical aggregate includes actual scratch search spend even when its package acceptance is unfunded', async () => {
    const report = await runEvaluation({seed: 42, searchOptions: {maxCost: 1500},
        constructorDigest: await sourceDigest()});
    assert.equal(report.successor.status, 'PASS');
    assert.equal(report.successor.costs.scratchQualified, false);
    assert.equal(report.successor.scratch.ledger.total, 1399);
    assert.equal(report.costAccounting.successorAndMatchedColdStart,
        report.successor.costs.remainingAfterAcceptance + 1399);
    assert.equal(report.aggregateCost, report.costAccounting.topologyJourneys.reduce((a, b) => a + b, 0)
        + report.costAccounting.unseenFamilies.reduce((a, b) => a + b, 0)
        + report.costAccounting.successorAndMatchedColdStart);
});

test('an infeasible inherited search still reports an accepted scratch baseline with its complete freeze ledger', async () => {
    const app = apparatus('shielded');
    app.channels.push({...app.channels[0], id: 'relay', initial: 0, drift: 0});
    for (const edge of app.edges) edge.to = 'relay';
    app.edges.push({id: 'relay-readout', from: 'relay', to: 'readout', gain: 1});
    app.primitives.push({...structuredClone(app.primitives.find(item => item.id === 'route-residual')),
        id: 'route-shared', target: 'relay-readout', cost: 10});
    const first = await freezeCapability(app, construct(app));
    const report = await buildSuccessor(first, {seed: 123, searchOptions: {maxProgramSize: 1}});
    assert.equal(report.status, 'INCONCLUSIVE');
    assert.equal(report.result.status, 'infeasible');
    assert.equal(report.package, undefined);
    assert.equal(report.scratch.status, 'qualified');
    assert.equal(report.scratch.ledger.total, 49);
    assert.equal(report.scratch.acceptanceLedger.total, 98);
    assert.equal(report.costs.scratchQualified, true);
    assert.equal(report.costs.scratchConstructionWork, 98);
    assert.equal(report.costs.constructionFromScratch, 98);
});

test('an unfunded primary successor retains its qualified candidate and actual work without claiming acceptance', async () => {
    const app = apparatus('shielded');
    const first = await freezeCapability(app, construct(app, {maxCost: 600}));
    const original = JSON.stringify(first), expanded = expandApparatus(app);
    assert.equal(first.costLedger.total, 591);
    for (const maxCost of [600, 1156]) {
        const raw = construct(expanded, {parent: first, maxCost});
        const projected = projectedFreezeCostCapability(expanded, raw, {parent: first});
        const report = await buildSuccessor(first, {seed: 123, searchOptions: {maxCost}});
        assert.equal(report.status, 'INCONCLUSIVE');
        assert.equal(report.oldScope.status, 'FAIL');
        assert.equal(report.result.status, 'exhausted');
        assert.equal(report.result.constructionStatus, 'qualified');
        assert.equal(report.result.qualification.status, 'inconclusive');
        assert.deepEqual(report.result.ledger, raw.ledger);
        assert.equal(report.result.ledger.total, 424);
        assert.deepEqual(report.result.checkpoint, raw.checkpoint);
        const resumed = advanceSearch(importSearchCheckpoint(report.result.checkpoint), {steps: 0});
        assert.equal(resumed.status, 'qualified');
        assert.deepEqual(resumed.ledger, raw.ledger);
        assert.equal(report.result.acceptanceLedger, null);
        assert.equal(report.result.freeze.status, 'not-run');
        assert.equal(report.result.freeze.requiredTotal, 1157);
        assert.equal(report.result.freeze.unperformedFreezeWork, 733);
        assert.deepEqual(report.result.freeze.projectedLedger, projected);
        assert.equal(report.package, undefined);
        assert.equal(report.reuse, undefined);
        assert.equal(report.newFunction, undefined);
        assert.match(report.reason, /Candidate found; package acceptance could not be funded/);
        assert.equal(report.costs.ancestor, 591);
        assert.equal(report.costs.remaining, raw.ledger.total + verificationCostCapability(first) + 5);
        assert.equal(report.costs.remaining, 726);
        assert.equal(report.costs.cumulative, 1317);
        assert.equal(report.costs.scratchConstructionWork, report.scratch.ledger.total);
        assert.ok(report.costs.scratchConstructionWork <= maxCost);
        assert.equal(report.costs.remainingSaving, null);
        assert.equal(report.costs.cumulativeSaving, null);
    }
    assert.equal(JSON.stringify(first), original);
});

test('the exact inherited primary freeze budget accepts the same candidate with its complete verified ledger', async () => {
    const app = apparatus('shielded'), first = await freezeCapability(app, construct(app, {maxCost: 600}));
    const report = await buildSuccessor(first, {seed: 123, searchOptions: {maxCost: 1157}});
    assert.equal(report.status, 'PASS');
    assert.equal(report.result.ledger.total, 424);
    assert.equal(report.result.freeze.status, 'completed');
    assert.equal(report.result.freeze.requiredTotal, 1157);
    assert.equal(report.result.qualification.status, 'qualified');
    assert.equal(report.package.costLedger.total, 1157);
    assert.deepEqual(report.result.freeze.projectedLedger, report.package.costLedger);
    assert.deepEqual(report.result.acceptanceLedger, report.package.costLedger);
    assert.deepEqual(await importCapability(report.package), report.package);
    assert.equal(report.obligations.preserved, true);
    assert.equal(report.newFunction.accepted, true);
    assert.equal(report.costs.remaining, 1157 + verificationCostCapability(first) + 5);
});

test('unfunded primary topology and successor acceptance retain only actual work in the vertical aggregate', async () => {
    const report = await runEvaluation({seed: 42, searchOptions: {maxCost: 500},
        constructorDigest: await sourceDigest()});
    assert.equal(report.status, 'INCONCLUSIVE');
    const shielded = report.topologies.find(item => item.topology === 'shielded');
    assert.equal(shielded.status, 'INCONCLUSIVE');
    assert.equal(shielded.result.constructionStatus, 'qualified');
    assert.equal(shielded.result.qualification.status, 'inconclusive');
    assert.equal(shielded.result.freeze.status, 'not-run');
    assert.equal(shielded.result.freeze.requiredTotal, 591);
    assert.equal(shielded.result.ledger.total, 294);
    assert.equal(shielded.package, undefined);
    assert.equal(report.costAccounting.topologyJourneys[0], 294);
    assert.equal(report.successor.status, 'INCONCLUSIVE');
    assert.equal(report.successor.package, undefined);
    assert.equal(report.costAccounting.successorAndMatchedColdStart,
        report.successor.costs.remaining + report.successor.costs.scratchConstructionWork);
    assert.equal(report.aggregateCost, report.costAccounting.topologyJourneys.reduce((a, b) => a + b, 0)
        + report.costAccounting.unseenFamilies.reduce((a, b) => a + b, 0)
        + report.costAccounting.successorAndMatchedColdStart);
});

test('generalization keeps an unfunded runtime-qualified family distinct from its independently proved negative', async () => {
    const report = await evaluateConstructorGeneralization({seed: 42, searchOptions: {maxCost: 1000},
        constructorDigest: await sourceDigest()});
    const routed = report.cases.find(item => item.topology === 'routed');
    assert.equal(routed.status, 'INCONCLUSIVE');
    assert.equal(routed.constructionStatus, 'qualified');
    assert.equal(routed.result.qualification.status, 'inconclusive');
    assert.equal(routed.result.ledger.total, 553);
    assert.equal(routed.result.freeze.status, 'not-run');
    assert.equal(routed.result.freeze.requiredTotal, 1105);
    assert.equal(routed.result.acceptanceLedger, null);
    assert.equal(routed.package, null);
    assert.equal(routed.reuse, null);
    assert.equal(routed.acceptedOutcome, 'unfinished');
    const negative = report.cases.find(item => item.topology === 'referenced');
    assert.equal(negative.status, 'PASS');
    assert.equal(negative.acceptedOutcome, 'independently-proved-negative-case');
    assert.equal(negative.package, null);
    assert.equal(report.status, 'INCONCLUSIVE');
});
