// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {compareCampaign} from './discovery-lab-baselines.mjs';
import {DEFAULT_CHARTER, runCampaign} from './discovery-lab.mjs';
import {checkStage} from './discovery-lab-checker.mjs';

const base = runCampaign(DEFAULT_CHARTER);
const byName = (records, name) => records.find(value => value.name === name);

test('finite controls execute independent enumeration and current checker acceptance', () => {
    const records = compareCampaign(DEFAULT_CHARTER, base.stages);
    assert.equal(records.length, 10);
    const reference = records[0];
    assert.equal(reference.status, 'accepted');
    assert.equal(reference.measurementCandidates, 18);
    assert.equal(reference.platformCandidates, 4);
    assert.ok(reference.policyCombinations > 0);
    assert.ok(reference.measuredWork.search > 0);
    assert.ok(reference.measuredWork.checking > 0);
    assert.equal(reference.measuredWork.acquisitions, 540);
    assert.match(reference.scope, /Not a global architecture optimum/);
    assert.equal(reference.completeCampaignCandidates, 54);
    assert.equal(reference.witness.length, 6);
    assert.equal(reference.relation, 'tie');
    assert.equal(byName(records, 'Full-state reasoning').labels, 8);
    assert.equal(byName(records, 'Separate service realization').status, 'rejected');
    assert.equal(byName(records, 'Separate service realization').vacancies, 0);
    assert.equal(byName(records, 'Fixed complete certificate').status, 'unsupported');
    assert.equal(byName(records, 'Fixed architecture with more search').measuredWork.acquisitions, 288);
    assert.deepEqual(byName(records, 'Full diagnosis').expectedCost, {numerator: 16, denominator: 4});
    assert.deepEqual(byName(records, 'No-diagnosis construction').expectedCost, {numerator: 20, denominator: 4});
});

test('unchanged complete certificates and compatible contracts retain measured work rather than a declared tie', () => {
    const records = compareCampaign(DEFAULT_CHARTER, base.stages, {parent: base});
    const full = byName(records, 'Full recomputation');
    const incremental = byName(records, 'Equally capable incremental contracts');
    assert.equal(full.status, 'accepted'); assert.equal(incremental.status, 'accepted');
    assert.ok(incremental.retainedContracts.length > 0);
    assert.ok(incremental.measuredWork.search < full.measuredWork.search);
    assert.deepEqual(incremental.completeBoundaryProfiles, full.completeBoundaryProfiles);
    assert.equal(byName(records, 'Fixed complete certificate').status, 'accepted');
    assert.ok(byName(records, 'Fixed complete certificate').measuredWork.checking > 0);
    const scratch = byName(records, 'Successor from scratch');
    assert.match(scratch.scope, /Complete independently constructed six-stage cold campaign/);
    assert.deepEqual(scratch.inheritedAssets, []);
    assert.deepEqual(scratch.sharedMeasuredWork, records[0].measuredWork);
    assert.equal(scratch.measuredWork.search, 0);
});

test('budget refusal retains actual partial work and never manufactures successful controls', () => {
    let charged = 0;
    const records = compareCampaign(DEFAULT_CHARTER, base.stages, {charge(kind, n) {
        if (kind === 'search' && charged + n > 5) throw Error('search budget exhausted');
        if (kind === 'search') charged += n;
    }});
    assert.equal(records.length, 1);
    assert.equal(records[0].status, 'inconclusive');
    assert.equal(records[0].measuredWork.search, charged);
    assert.equal(charged, 5);
    assert.ok(!records.some(value => value.status === 'accepted'));
});

test('current finite checkpoint and noisy programs remain independently checked', () => {
    for (const update of [{checkpoints: ['safety', 'sterile']}, {noise: 1, accuracy: 2}, {operations: []},
        {controls: 4, memory: 16, operations: ['flip-z', 'flip-w', 'mix']}]) {
        const charter = {...structuredClone(DEFAULT_CHARTER), ...update};
        const report = runCampaign(charter);
        const records = compareCampaign(charter, report.stages);
        assert.equal(records[0].status, 'accepted');
        assert.equal(byName(records, 'Full recomputation').status, 'accepted');
        assert.equal(byName(records, 'Full diagnosis').status, 'accepted');
    }
});

test('equal complete profiles retain continuation while the actual current route witness changes', () => {
    const oldCharter = {...structuredClone(DEFAULT_CHARTER), faultHypotheses: ['clear', 'left']};
    const nextCharter = {...structuredClone(DEFAULT_CHARTER), faultHypotheses: ['clear', 'right']};
    const previous = runCampaign(oldCharter), current = runCampaign(nextCharter, {parent: previous});
    assert.equal(previous.state, 'accepted'); assert.equal(current.state, 'accepted');
    const before = previous.stages[4].program, after = current.stages[4].program;
    assert.deepEqual(before.components.map(value => value.profiles.map(row => row.value)),
        after.components.map(value => value.profiles.map(row => row.value)));
    assert.deepEqual(before.routeWitness.leaves.map(value => value.route), ['R']);
    assert.deepEqual(after.routeWitness.leaves.map(value => value.route), ['L']);
    assert.equal(after.reuseContracts.find(value => value.component === 'routing').status, 'rebuilt');
    assert.ok(after.reuseContracts.every(value => value.completeProfileEqual && value.propagation === 'stopped'));
    const stale = structuredClone(after); stale.routeWitness = structuredClone(before.routeWitness);
    assert.equal(checkStage('execute', nextCharter, stale, current.stages.slice(0, 4)).accepted, false);
    assert.equal(current.comparisons.find(value => value.name === 'Equally capable incremental contracts').status, 'accepted');
});
