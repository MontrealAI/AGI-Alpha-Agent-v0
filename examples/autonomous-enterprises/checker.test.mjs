// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {qualifyArtifact, hashArtifact, interpretArtifact, evaluateEnvelope,
    specificationApplication, verifyBundle} from './checker.mjs';
import {buildFoundry} from './foundry.mjs';

const clone = value => JSON.parse(JSON.stringify(value));
const basis = (n, index) => Array.from({length: n}, (_, i) => i === index ? '1' : '0');
const frame = (kind, n, dependencies, ast, operatingWork, certificate = {}) => ({
    schema: 'autonomous-enterprise-artifact/v1', kind, n, dependencies, ast, operatingWork, certificate});
async function envelope(artifact) { return {digest: await hashArtifact(artifact), artifact}; }
async function specialist(n) {
    const all = [await envelope(frame('identity', 1, [], {op: 'identity'}, 0, {matrix: [['1']]}))];
    for (let size = 2; size <= n; size *= 2) {
        const child = all.at(-1), matrix = [];
        for (let row = 0; row < size; row++) {
            matrix.push(Array.from({length: size}, (_, col) => {
                let bits = row & col, parity = 0;
                while (bits) { parity ^= bits & 1; bits >>= 1; }
                return parity ? '-1' : '1';
            }));
        }
        all.push(await envelope(frame('walsh', size, [child.digest], {op: 'split-mix', child: child.digest,
            inputLayout: 'halves', outputLayout: 'blocks', mix: [1, 1, 1, -1]}, size * Math.log2(size), {matrix})));
    }
    const transform = all.at(-1);
    const convolution = await envelope(frame('xor-convolution', n, [transform.digest],
        {op: 'xor-convolution', transform: transform.digest, divisor: String(n)}, 3 * n * Math.log2(n) + 2 * n));
    const inverse = await envelope(frame('inverse', n, [transform.digest], {op: 'spectral-inverse',
        transform: transform.digest, divisor: String(n),
        kernel: Array.from({length: n}, (_, i) => String(i === 0 ? n + 1 : 1)),
        spectrum: Array.from({length: n}, (_, i) => String(i === 0 ? 2 * n : n))}, 2 * n * Math.log2(n) + 2 * n));
    return {all, transform, convolution, inverse};
}
const fixed = await specialist(32), small = await specialist(4);

test('separately authored specialist transform receives every linear basis check', async () => {
    const receipt = await qualifyArtifact(fixed.transform.artifact, fixed.all.slice(0, -1));
    assert.equal(receipt.accepted, true); assert.equal(receipt.semantics, 'linear-over-rationals');
    assert.equal(receipt.basisCases, 32); assert.equal(receipt.arithmetic, 5120);
    assert.equal(receipt.comparisons, 1024); assert.equal(receipt.matrixComparisons, 1024);
    assert.equal(receipt.operatingWork, 160);
    assert.equal(receipt.cases.length, 32);
});

test('bilinear convolution covers all1024ordered basis pairs and differentiates XOR from cyclic', async () => {
    const receipt = await qualifyArtifact(fixed.convolution.artifact, fixed.all);
    assert.equal(receipt.accepted, true); assert.equal(receipt.semantics, 'bilinear-over-rationals');
    assert.equal(receipt.basisCases, 1024); assert.equal(receipt.totalWork, 589824);
    const difference = receipt.cases.find(item => item.basis[0] === 3 && item.basis[1] === 1);
    assert.deepEqual(difference.output, basis(32, 2)); assert.notDeepEqual(difference.output, basis(32, 4));
});

test('direct and inherited inverse check every basis under their different actual arithmetic paths', async () => {
    const dependencies = [...fixed.all, fixed.convolution];
    const direct = await qualifyArtifact(fixed.inverse.artifact, dependencies);
    const inherited = await qualifyArtifact(fixed.inverse.artifact, dependencies,
        {reference: 'inherited', convolutionDigest: fixed.convolution.digest});
    assert.equal(direct.accepted, true); assert.equal(inherited.accepted, true);
    assert.equal(direct.basisCases, 32); assert.equal(inherited.basisCases, 32);
    assert.equal(direct.totalWork, 77824); assert.equal(inherited.totalWork, 30720);
    assert.equal(inherited.dependencyChecks.qualifiedNow.includes(fixed.convolution.digest), true);
    assert.equal(direct.scopeChecks.arithmetic, 992);
    assert.equal(direct.scopeChecks.comparisons, 32);
});

test('wrong normalization remains rejected after rehashing the candidate', async () => {
    const wrong = clone(small.convolution.artifact); wrong.ast.divisor = '1';
    assert.notEqual(await hashArtifact(wrong), small.convolution.digest);
    const receipt = await qualifyArtifact(wrong, small.all);
    assert.equal(receipt.accepted, false); assert.equal(receipt.basisCases, 16);
    assert.equal(receipt.cases.filter(item => !item.accepted).length, 16);
});

test('dependency content identity is checked before it is reused', async () => {
    const deps = clone(small.all); deps.at(-1).artifact.certificate.matrix[0][0] = '-1';
    await assert.rejects(qualifyArtifact(small.convolution.artifact, deps), /content hash mismatch/);
});

test('newly hashed incorrect predecessor still needs semantic basis admission', async () => {
    const deps = clone(small.all); deps.at(-1).artifact.certificate.matrix[0][0] = '-1';
    deps.at(-1).digest = await hashArtifact(deps.at(-1).artifact);
    const candidate = clone(small.convolution.artifact);
    candidate.dependencies = [deps.at(-1).digest]; candidate.ast.transform = deps.at(-1).digest;
    await assert.rejects(qualifyArtifact(candidate, deps), /valid complete-domain certificate/);
});

test('an artifact cannot invent a cheaper operating-work bound', async () => {
    const wrong = clone(fixed.transform.artifact); wrong.operatingWork = 159;
    await assert.rejects(qualifyArtifact(wrong, fixed.all.slice(0, -1)), /operating-work bound/);
});

test('singular and falsely stated spectra are separate semantic failures', async () => {
    const singular = clone(small.inverse.artifact);
    singular.ast.kernel = ['1', '1', '1', '1']; singular.ast.spectrum = ['4', '0', '0', '0'];
    await assert.rejects(qualifyArtifact(singular, small.all), /Singular/);
    const falseSpectrum = clone(small.inverse.artifact); falseSpectrum.ast.spectrum[0] = '4';
    assert.equal((await qualifyArtifact(falseSpectrum, small.all)).accepted, false);
});

test('unsupported executable grammar and mismatched dependency dimensions are refused', async () => {
    const wrong = clone(small.transform.artifact); wrong.ast.op = 'arbitrary-program';
    await assert.rejects(qualifyArtifact(wrong, small.all.slice(0, -1)), /grammar/);
    const badSize = clone(small.convolution.artifact); badSize.n = 8;
    await assert.rejects(qualifyArtifact(badSize, small.all), /dimension mismatch/);
});

test('fresh calls always execute current dependency admission, independently of earlier treatments', async () => {
    const a = await qualifyArtifact(small.convolution.artifact, small.all);
    const b = await qualifyArtifact(small.convolution.artifact, [...small.all].reverse());
    assert.deepEqual(a.dependencyChecks.qualifiedNow, b.dependencyChecks.qualifiedNow);
    assert.ok(a.dependencyChecks.arithmetic > 0); assert.equal(a.dependencyChecks.arithmetic, b.dependencyChecks.arithmetic);
});

test('an invocation uses captured executable bytes on exact rational vectors', async () => {
    const input = ['1/2', '2', '-3', '7/4'];
    const actual = await evaluateEnvelope(small.transform, small.all, [input]);
    const expected = specificationApplication('walsh', [input]);
    assert.deepEqual(actual.output, expected.output); assert.equal(actual.arithmetic, 8);
    const wrong = clone(small.transform); wrong.artifact.operatingWork = 7;
    await assert.rejects(evaluateEnvelope(wrong, small.all, [input]), /content hash/);
});

test('independent inverse application solves the known kernel with no generated-interpreter import', async () => {
    const input = ['1/2', '2', '-3', '7/4'], kernel = small.inverse.artifact.ast.kernel;
    const output = await interpretArtifact(small.inverse.artifact, small.all, [input]);
    const expected = specificationApplication('inverse', [input], {kernel});
    assert.deepEqual(output.output, expected.output); assert.equal(expected.arithmetic, 12);
    const roundtrip = specificationApplication('xor-convolution', [kernel, output.output]);
    assert.deepEqual(roundtrip.output, input);
});

test('ordinary incomplete topology and noncanonical rational inputs do not execute', async () => {
    await assert.rejects(qualifyArtifact(small.convolution.artifact, [small.transform]), /bytes are missing/);
    await assert.rejects(interpretArtifact(small.transform.artifact, small.all.slice(0, -1),
        [['2/4', '0', '0', '0']]), /reduced/);
});

test('actual foundry receipts, all rejected candidates and planner costs independently replay', async () => {
    const bundle = await buildFoundry({qualifyArtifact});
    const replay = await verifyBundle(bundle);
    assert.equal(replay.verified, true); assert.equal(replay.counts.joint, 808420);
    assert.equal(replay.counts.unrestrictedSamePrimitiveJointPlanner, replay.counts.joint);
    assert.ok(replay.currentReplayWork > replay.counts.joint);
    const corruptFailure = clone(bundle); corruptFailure.transforms[0].attempts[0].receipts.coefficientOperations--;
    await assert.rejects(verifyBundle(corruptFailure), /candidate or failure charge/);
    const corruptLedger = clone(bundle); corruptLedger.counts.joint--;
    await assert.rejects(verifyBundle(corruptLedger), /costs or planner optimum/);
    const corruptPath = clone(bundle); corruptPath.plans.joint.steps[0].after = 0;
    await assert.rejects(verifyBundle(corruptPath), /witness stock or paid charge/);
    const corruptObserved = clone(bundle); corruptObserved.observedWorkLedger.totalCountedCampaignWork--;
    await assert.rejects(verifyBundle(corruptObserved), /campaign work ledger/);
});

test('declared foundry size and invocation inventory cannot disguise different executable bytes', async () => {
    const bundle = await buildFoundry({qualifyArtifact, maxN: 4});
    bundle.transforms[1] = clone(bundle.transforms[0]);
    await assert.rejects(verifyBundle(bundle), /stage kinds or dimensions/);
    const redefined = clone(small.transform); redefined.artifact.operatingWork = 1;
    await assert.rejects(evaluateEnvelope(small.transform, [...small.all.slice(0, -1), redefined],
        [basis(4, 0)]), /redefines/);
});

const disclosureFixture = buildFoundry({qualifyArtifact, maxN: 4});
for (const [name, change] of [
    ['metric units', bundle => { bundle.metric = 'complete-financial-cost/v1'; }],
    ['excluded unmeasured costs', bundle => { bundle.excludedCosts = []; }],
    ['isolated comparison scope', bundle => { bundle.isolatedComparisonScope = 'Every isolated architecture was freshly measured.'; }],
    ['scientific claims', bundle => { bundle.claims = ['Externally validated superiority and revenue.']; }],
    ['extra top-level authority', bundle => { bundle.executionApproved = true; }],
    ['identity charge scope', bundle => { bundle.identity.chargeScope = 'Included and institutionally approved.'; }],
    ['extra identity metadata', bundle => { bundle.identity.approved = true; }],
    ['joint comparison scope', bundle => { bundle.controls.unrestrictedJoint.scope = 'Benchmark victory over unrestricted compilers.'; }],
    ['extra joint comparison metadata', bundle => { bundle.controls.unrestrictedJoint.pilotComplete = true; }],
    ['extra inverse-only metadata', bundle => { bundle.controls.inverseOnly.pilotComplete = true; }],
    ['extra control branch', bundle => { bundle.controls.operational = {validated: true}; }],
    ['extra plan container metadata', bundle => { bundle.plans.admittedBy = 'independent institution'; }],
    ['extra transform record metadata', bundle => { bundle.transforms[0].approved = true; }],
    ['extra convolution record metadata', bundle => { bundle.convolution.externalAcceptance = true; }],
    ['inverse admission state', bundle => { bundle.inverseDirect.state = 'OPERATIONALLY_VALIDATED'; }],
    ['extra inverse record metadata', bundle => { bundle.inverseInherited.realizedProfit = 1; }],
    ['extra stage envelope metadata', bundle => { bundle.transforms[0].envelope.approved = true; }],
    ['extra identity envelope metadata', bundle => { bundle.identity.envelope.approved = true; }],
    ['extra selected verification metadata', bundle => { bundle.convolution.verification.approved = true; }],
    ['extra identity verification metadata', bundle => { bundle.identity.verification.approved = true; }],
    ['extra nested certificate metadata', bundle => { bundle.transforms[0].verification.cases[0].approved = true; }]
]) {
    test(`foundry admission rejects changed ${name} while preserving valid receipts`, async () => {
        const bundle = clone(await disclosureFixture); change(bundle);
        await assert.rejects(verifyBundle(bundle));
    });
}

test('closed-disclosure admission preserves the complete original scientific bytes', async () => {
    const bundle = await disclosureFixture, before = JSON.stringify(bundle);
    const result = await verifyBundle(bundle);
    assert.equal(result.verified, true); assert.equal(JSON.stringify(bundle), before);
    assert.deepEqual(result.counts, bundle.counts);
    assert.deepEqual(result.observedWorkLedger, bundle.observedWorkLedger);
});
