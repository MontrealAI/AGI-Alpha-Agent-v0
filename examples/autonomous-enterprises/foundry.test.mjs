// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as q from './rational.mjs';
import {buildFoundry, canonical, digestArtifact, constructInverse, evaluateArtifact} from './foundry.mjs';
import {qualifyArtifact} from './checker.mjs';

const bundlePromise = buildFoundry({qualifyArtifact});
const basis = (n, at) => Array.from({length: n}, (_, i) => i === at ? '1' : '0');

test('exact rational operations retain reduced canonical bytes and bounded growth', () => {
    assert.equal(q.encode(q.add(q.parse('2/3'), q.parse('1/6'))), '5/6');
    assert.equal(q.encode(q.divide(q.parse('-2/3'), q.parse('-4/5'))), '5/6');
    assert.equal(q.encode(q.subtract(q.parse('1/2'), q.parse('1/2'))), '0');
    for (const input of ['-0', '2/4', '1/0', '01', '1/-2', '1.5', '1e2', NaN, 1.1]) {
        assert.throws(() => q.parse(input));
    }
    assert.throws(() => q.divide(q.parse('1'), q.parse('0')));
    assert.throws(() => q.parse('1' + '0'.repeat(129)));
});

test('all five transforms enumerate64 candidates and retain rejected search work', async () => {
    const bundle = await bundlePromise;
    assert.deepEqual(bundle.transforms.map(item => item.envelope.artifact.n), [2, 4, 8, 16, 32]);
    for (const item of bundle.transforms) {
        assert.equal(item.attempts.length, 64);
        assert(item.attempts.some(attempt => attempt.status === 'REJECTED'));
        assert(item.attempts.some(attempt => attempt.status === 'MATCH'));
        assert.equal(item.preparation.coefficientOperations, 64 * item.envelope.artifact.n ** 2);
        assert.equal(item.preparation.coefficientComparisons, 64 * item.envelope.artifact.n ** 2);
        assert.equal(item.verification.basisCases, item.envelope.artifact.n);
    }
});

test('emitted receipts reproduce selected paper counts without substituting expected constants', async () => {
    const bundle = await bundlePromise;
    assert.deepEqual(bundle.transforms.map(item => item.totalWork), [592, 2192, 8640, 34624, 139328]);
    assert.deepEqual(bundle.counts, {transformChain: 185376, incrementalConvolution: 592132,
        inverseDirect: 78016, inverseInherited: 30912, inverseOnlyViaNewConvolution: 623044,
        isolated: 1226276, joint: 808420, operating: {transform: 160, convolution: 544, inverse: 384},
        unrestrictedSamePrimitiveJointPlanner: 808420});
    assert.equal(bundle.totalCostComplete, false);
    assert(bundle.excludedCosts.includes('rational bit growth'));
    assert(bundle.observedWorkLedger.totalCountedCampaignWork > bundle.counts.joint + bundle.counts.inverseDirect);
    const observed = bundle.observedWorkLedger;
    assert.equal(observed.totalCountedCampaignWork, observed.constructorPreparation + observed.selectedQualifications
        + observed.additionalCurrentDependencyAndScopeChecks + observed.identityResearchAdmission);
});

test('convolution anchor search preserves all four candidates and independent1024-pair certificate', async () => {
    const {convolution} = await bundlePromise;
    assert.equal(convolution.attempts.length, 4);
    assert.deepEqual(convolution.attempts.map(item => item.ast.divisor), ['-32', '-1', '1', '32']);
    assert.equal(convolution.attempts.filter(item => item.status === 'REJECTED').length, 3);
    assert.equal(convolution.constructionWork, 2308);
    assert.equal(convolution.verification.basisCases, 1024);
    assert.equal(convolution.work, 589824);
});

test('direct and inherited inverse qualification preserve the exact same artifact and32basis checks', async () => {
    const {inverseDirect, inverseInherited} = await bundlePromise;
    assert.equal(inverseDirect.envelope.digest, inverseInherited.envelope.digest);
    assert.deepEqual(inverseInherited.envelope.artifact.ast.spectrum, ['64', ...Array(31).fill('32')]);
    assert.equal(inverseDirect.verification.basisCases, 32);
    assert.equal(inverseInherited.verification.basisCases, 32);
    assert.equal(inverseDirect.work - inverseInherited.work, 47104);
});

test('the unrestricted same-primitives joint planner ties and inverse-only planner rejects wasteful construction', async () => {
    const bundle = await bundlePromise;
    assert.equal(bundle.plans.joint.status, 'OPTIMAL');
    assert.equal(bundle.plans.joint.cost, bundle.counts.joint);
    assert.equal(bundle.plans.inverseOnly.cost, bundle.counts.inverseDirect);
    assert.equal(bundle.plans.inverseOnly.steps.length, 1);
    assert.equal(bundle.plans.inverseOnly.steps[0].recipe, 'construct-inverse-direct');
    assert.equal(bundle.controls.unrestrictedJoint.result, 'TIE');
    assert(bundle.counts.inverseOnlyViaNewConvolution > bundle.counts.inverseDirect);
    assert.equal(bundle.plans.joint.steps.reduce((sum, step) => sum + step.charge, 0), bundle.counts.joint);
});

test('actual XOR invocation differs from ordinary cyclic convolution', async () => {
    const bundle = await bundlePromise;
    const x = basis(32, 1);
    const actual = await evaluateArtifact(bundle.convolution.envelope, bundle.envelopes, [x, x], {qualifyArtifact});
    assert.deepEqual(actual.output, basis(32, 0));
    assert.notDeepEqual(actual.output, basis(32, 2));
    assert.equal(actual.arithmetic, 544);
});

test('a changed rational input is processed by executable transform bytes', async () => {
    const bundle = await bundlePromise; const f = bundle.transforms.at(-1).envelope;
    const input = ['1/2', '-3', ...Array(30).fill('0')];
    const actual = await evaluateArtifact(f, bundle.envelopes, [input], {qualifyArtifact});
    assert.deepEqual(actual.output, Array.from({length: 32}, (_, i) => i & 1 ? '7/2' : '-5/2'));
    assert.equal(actual.arithmetic, 160);
});

test('a singular kernel is rejected after recording its actual spectrum preparation', async () => {
    const bundle = await bundlePromise; const f = bundle.transforms.at(-1).envelope;
    const result = await constructInverse(f, bundle.envelopes, qualifyArtifact, {kernel: Array(32).fill('1')});
    assert.equal(result.state, 'REJECTED'); assert.equal(result.reason, 'SINGULAR_KERNEL');
    assert.equal(result.singular.length, 31); assert.equal(result.totalWork, 192);
    assert.equal(result.envelope, undefined);
});

test('artifact content identities are deterministic and input bytes are frozen before qualification await', async () => {
    const bundle = await bundlePromise;
    const envelope = structuredClone(bundle.transforms.at(-1).envelope);
    assert.equal(await digestArtifact(envelope.artifact), envelope.digest);
    assert.equal(canonical({b: 2, a: 1}), '{"a":1,"b":2}');
    const input = [basis(32, 0)];
    const deferredQualifier = async (...args) => { input[0][0] = '9'; return qualifyArtifact(...args); };
    const result = await evaluateArtifact(envelope, bundle.envelopes, input, {qualifyArtifact: deferredQualifier});
    assert.deepEqual(result.output, Array(32).fill('1'));
});

test('foundry size and independent-checker prerequisites are enforced', async () => {
    await assert.rejects(() => buildFoundry(), /checker/);
    await assert.rejects(() => buildFoundry({qualifyArtifact, maxN: 64}), /maximum/);
    await assert.rejects(() => buildFoundry({qualifyArtifact, maxN: 3}), /maximum/);
});
