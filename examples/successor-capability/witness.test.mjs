// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import {
    WITNESS_VERSION, WITNESS_LIMITS, defaultExperiment, validateExperiment, construct, evaluateConstruction,
} from './witness.mjs';

const clone = value => JSON.parse(JSON.stringify(value));
const popcount = mask => mask.toString(2).replaceAll('0', '').length;
const masks = count => Array.from({ length: 2 ** count }, (_, mask) => mask);
const terms = config => masks(config.input_count).filter(mask => popcount(mask) <= config.world.degree);

function sparseExperiment() {
    const config = defaultExperiment();
    config.input_count = 4;
    config.world.degree = 3;
    config.world.coefficient_limit = 16;
    config.world.overrides = terms(config).map(mask => ({ mask, coefficient: 0 }));
    const wanted = new Map([[0, 5], [1, 2], [2, -3], [3, 7], [7, 11]]);
    for (const term of config.world.overrides) term.coefficient = wanted.get(term.mask) ?? 0;
    config.threshold = 15;
    return config;
}

test('exports a bounded, fresh JSON configuration and validates an independent clone', () => {
    assert.equal(WITNESS_VERSION, 'binary-interaction-instrument/v1');
    assert.equal(WITNESS_LIMITS.min_inputs, 4);
    assert.equal(WITNESS_LIMITS.max_inputs, 8);
    assert.equal(WITNESS_LIMITS.max_calibration_samples, 37);
    assert.equal(WITNESS_LIMITS.max_world_terms, 93);
    assert.ok(Object.isFrozen(WITNESS_LIMITS));
    const config = defaultExperiment();
    const validated = validateExperiment(config);
    assert.deepEqual(validated, config);
    validated.world.overrides.push({ mask: 0, coefficient: 1 });
    assert.deepEqual(config.world.overrides, []);
    assert.deepEqual(defaultExperiment(), config);
    assert.deepEqual(clone(config), config);
});

test('constructs actual observations and exact Möbius coefficients, including the constant term', () => {
    const config = sparseExperiment();
    const artifact = construct(config);
    assert.deepEqual(artifact.calibration.inputs, [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 12]);
    assert.equal(artifact.calibration.sample_count, 11);
    const observed = new Map(artifact.calibration.observations.map(row => [row.mask, row.response]));
    assert.equal(observed.get(0), 5);
    assert.equal(observed.get(1), 7);
    assert.equal(observed.get(2), 2);
    assert.equal(observed.get(3), 11);
    const coefficients = new Map(artifact.model.coefficients.map(row => [row.mask, row.coefficient]));
    assert.equal(coefficients.get(0), 5);
    assert.equal(coefficients.get(1), 2);
    assert.equal(coefficients.get(2), -3);
    assert.equal(coefficients.get(3), 7);
    assert.equal(coefficients.get(4), 0);
    assert.ok(!coefficients.has(7));
    assert.equal(artifact.costs.calibration_world_evaluations, 11);
    assert.equal(artifact.costs.coefficient_subtractions, 4 + 6 * 3);
    assert.deepEqual(artifact, clone(artifact));
    artifact.experiment.world.overrides[0].coefficient = 6;
    assert.equal(config.world.overrides[0].coefficient, 5);
});

test('default construction and both evaluation phases are deterministic successful JSON artifacts', () => {
    const config = defaultExperiment();
    const artifact = construct(config);
    assert.deepEqual(construct(config), artifact);
    const before = JSON.stringify(artifact);
    for (const phase of ['development', 'heldout']) {
        const report = evaluateConstruction(config, artifact, phase);
        assert.equal(report.verdict, 'pass');
        assert.deepEqual(report.failure_reasons, []);
        assert.equal(report.response_match_count, report.evaluation_masks.length);
        assert.ok(report.comparisons.every(comparison => comparison.pass));
        assert.deepEqual(evaluateConstruction(config, artifact, phase), report);
        assert.deepEqual(clone(report), report);
    }
    assert.equal(JSON.stringify(artifact), before);
});

test('quadratic construction succeeds across every bounded input size, seeds and valid model degrees', () => {
    for (let inputCount = 4; inputCount <= 8; inputCount += 1) {
        for (const modelDegree of [1, 2]) {
            for (const worldDegree of [1, 2]) {
                for (const seed of [0, 17, 4294967295]) {
                    const config = defaultExperiment();
                    config.input_count = inputCount;
                    config.model_degree = modelDegree;
                    config.world.degree = worldDegree;
                    config.seed = seed;
                    const artifact = construct(config);
                    for (const phase of ['development', 'heldout']) {
                        const report = evaluateConstruction(config, artifact, phase);
                        if (worldDegree <= modelDegree) assert.equal(report.verdict, 'pass');
                    }
                    if (worldDegree > modelDegree) {
                        assert.equal(evaluateConstruction(config, artifact, 'heldout').verdict, 'fail');
                    }
                }
            }
        }
    }
});

test('calibration, development and heldout exactly partition inputs without overlap', () => {
    for (let inputCount = 4; inputCount <= 8; inputCount += 1) {
        for (const degree of [1, 2]) {
            const config = defaultExperiment();
            config.input_count = inputCount;
            config.model_degree = degree;
            const artifact = construct(config);
            const development = evaluateConstruction(config, artifact, 'development');
            const heldout = evaluateConstruction(config, artifact, 'heldout');
            assert.ok(development.evaluation_masks.length >= 2);
            assert.ok(heldout.evaluation_masks.length >= 3);
            const all = [...artifact.calibration.inputs, ...development.evaluation_masks, ...heldout.evaluation_masks];
            assert.equal(new Set(all).size, 2 ** inputCount);
            assert.equal(all.length, 2 ** inputCount);
            assert.deepEqual([...all].sort((left, right) => left - right), masks(inputCount));
            assert.ok(development.evaluation_masks.every(mask => popcount(mask) > degree));
            assert.ok(heldout.evaluation_masks.every(mask => popcount(mask) > degree));
            assert.deepEqual(development.task_types, ['response-reconstruction']);
            assert.deepEqual(heldout.task_types, ['threshold-classification', 'response-ranking']);
            assert.equal(development.calibration_overlap_count, 0);
            assert.equal(heldout.other_phase_overlap_count, 0);
            const rank = heldout.comparisons.at(-1);
            assert.deepEqual(rank.query.masks, heldout.evaluation_masks);
            assert.ok(rank.query.masks.length >= 3);
        }
    }
});

test('an explicit cubic interaction computes numerical and downstream decision failures', () => {
    const config = sparseExperiment();
    const artifact = construct(config);
    const report = evaluateConstruction(config, artifact, 'heldout');
    assert.equal(report.verdict, 'fail');
    const comparison = report.comparisons.find(row => row.query.mask === 7);
    assert.deepEqual(comparison.expected, { response: 22, at_or_above_threshold: true });
    assert.deepEqual(comparison.actual, { response: 11, at_or_above_threshold: false });
    assert.equal(comparison.pass, false);
    assert.ok(report.failure_reasons.some(reason => reason.code === 'response-mismatch' && reason.mask === 7));
    assert.ok(report.failure_reasons.some(reason => reason.code === 'threshold-decision-mismatch'));
    const development = evaluateConstruction(config, artifact, 'development');
    assert.equal(development.verdict, 'pass');
    assert.deepEqual(development.evaluation_masks, [11, 14]);
});

test('ordinary degree-three generators fail the degree-two heldout exactness gate', () => {
    for (const inputCount of [4, 5, 6, 7, 8]) {
        for (const seed of [0, 17, 4294967295]) {
            const config = defaultExperiment();
            config.input_count = inputCount;
            config.world.degree = 3;
            config.seed = seed;
            const report = evaluateConstruction(config, construct(config), 'heldout');
            assert.equal(report.verdict, 'fail');
            assert.ok(report.failure_reasons.some(reason => reason.code === 'response-mismatch' && reason.mask === 7));
        }
    }
});

test('correct threshold and ranking decisions cannot conceal inaccurate model responses', () => {
    const config = sparseExperiment();
    config.threshold = 2048;
    const report = evaluateConstruction(config, construct(config), 'heldout');
    assert.equal(report.verdict, 'fail');
    assert.ok(report.comparisons.filter(row => row.task_type === 'threshold-classification')
        .every(row => row.decision_match));
    assert.equal(report.comparisons.at(-1).pass, true);
    assert.ok(report.failure_reasons.every(reason => reason.code === 'response-mismatch'));
});

test('ties rank by mask and threshold equality uses greater-than-or-equal', () => {
    const config = defaultExperiment();
    config.input_count = 4;
    config.world.overrides = terms(config).map(mask => ({ mask, coefficient: mask === 0 ? 3 : 0 }));
    config.threshold = 3;
    const report = evaluateConstruction(config, construct(config), 'heldout');
    assert.equal(report.verdict, 'pass');
    assert.ok(report.comparisons.slice(0, -1).every(row => row.actual.at_or_above_threshold));
    assert.deepEqual(report.comparisons.at(-1).actual.ordered_masks, [...report.evaluation_masks]);
});

test('changing seeds and bounded coefficients changes actual observations and reused outputs', () => {
    const original = defaultExperiment();
    const changedSeed = defaultExperiment();
    changedSeed.seed += 1;
    const first = construct(original);
    const second = construct(changedSeed);
    assert.notDeepEqual(first.calibration.observations, second.calibration.observations);
    assert.notDeepEqual(evaluateConstruction(original, first, 'heldout').comparisons,
        evaluateConstruction(changedSeed, second, 'heldout').comparisons);
    const changedCoefficient = defaultExperiment();
    const constant = first.model.coefficients.find(term => term.mask === 0).coefficient;
    changedCoefficient.world.overrides = [{ mask: 0, coefficient: constant === 8 ? 7 : constant + 1 }];
    const third = construct(changedCoefficient);
    assert.notDeepEqual(first.calibration.observations, third.calibration.observations);
    assert.equal(evaluateConstruction(changedCoefficient, third, 'heldout').verdict, 'pass');
});

test('reports construction, calibration revalidation, reference and reuse costs without physical-cost claims', () => {
    const config = defaultExperiment();
    const artifact = construct(config);
    const report = evaluateConstruction(config, artifact, 'heldout');
    const count = artifact.calibration.sample_count;
    const queries = report.evaluation_masks.length;
    assert.equal(count, 1 + 5 + 10);
    assert.deepEqual(report.costs.construction, artifact.costs);
    const costs = report.costs.this_evaluation;
    assert.equal(costs.artifact_validation_world_evaluations, count);
    assert.equal(costs.reference_world_evaluations, queries);
    assert.equal(costs.total_world_evaluations, count + queries);
    assert.equal(costs.reuse_model_evaluations, queries);
    assert.equal(costs.reuse_model_basis_checks, queries * count);
    assert.equal(costs.downstream_threshold_decisions, queries);
    assert.equal(costs.downstream_rankings, 1);
    for (const value of Object.values(costs)) assert.ok(Number.isSafeInteger(value));
    for (const object of [artifact, report]) {
        assert.equal(object.synthetic, true);
        assert.equal(object.protected_holdout, false);
        assert.equal(object.limitations.physical_validation, false);
        assert.equal(object.limitations.superiority_claim, false);
        assert.equal(object.limitations.revenue_claim, false);
        assert.equal(object.limitations.unrestricted_engineering_comparison, false);
    }
});

test('accepts schema boundary values and rejects malformed, unbounded and executable configurations', () => {
    for (const mutate of [
        config => { config.input_count = 3; },
        config => { config.input_count = 9; },
        config => { config.input_count = 4.5; },
        config => { config.input_count = '5'; },
        config => { config.model_degree = 0; },
        config => { config.model_degree = 3; },
        config => { config.seed = -1; },
        config => { config.seed = -0; },
        config => { config.seed = 4294967296; },
        config => { config.seed = NaN; },
        config => { config.seed = Infinity; },
        config => { config.threshold = 2049; },
        config => { config.threshold = -2049; },
        config => { config.world.degree = 4; },
        config => { config.world.coefficient_limit = 0; },
        config => { config.world.coefficient_limit = 17; },
        config => { config.version = 'wrong'; },
        config => { config.run = 'fetch("https://example.test")'; },
        config => { config.world.source = '() => 1'; },
        config => { config.world.overrides = [{ mask: 32, coefficient: 1 }]; },
        config => { config.world.overrides = [{ mask: 7, coefficient: 1 }]; },
        config => { config.world.overrides = [{ mask: 1, coefficient: 9 }]; },
        config => { config.world.overrides = [{ mask: 1, coefficient: 0.5 }]; },
        config => { config.world.overrides = [{ mask: 1, coefficient: 1, source: 'bad' }]; },
        config => { config.world.overrides = [{ mask: 1, coefficient: 1 }, { mask: 1, coefficient: 1 }]; },
        config => { config.world.overrides = [{ mask: 2, coefficient: 1 }, { mask: 1, coefficient: 1 }]; },
        config => { config.world.overrides = new Array(2); },
        config => { config.world.overrides = new (class extends Array {})(); },
        config => { config.world.overrides = new Array(94).fill({ mask: 0, coefficient: 0 }); },
        config => { config.world.overrides.extra = true; },
        config => { config.world.overrides[Symbol('extra')] = true; },
        config => { config[Symbol('extra')] = true; },
        config => { delete config.threshold; },
    ]) {
        const config = defaultExperiment();
        mutate(config);
        assert.throws(() => validateExperiment(config), TypeError);
        assert.throws(() => construct(config), TypeError);
    }
    for (const input of [null, [], () => 1, 'config', 5, Object.create(defaultExperiment())]) {
        assert.throws(() => validateExperiment(input), TypeError);
    }
    const boundary = defaultExperiment();
    Object.assign(boundary, { input_count: 8, model_degree: 1, seed: 4294967295, threshold: -2048 });
    boundary.world = { degree: 3, coefficient_limit: 16, overrides: [{ mask: 224, coefficient: -16 }] };
    assert.deepEqual(validateExperiment(boundary), boundary);
    assert.doesNotThrow(() => construct(boundary));
});

test('rejects accessors without invoking them', () => {
    let called = false;
    const config = defaultExperiment();
    Object.defineProperty(config, 'seed', { enumerable: true, get() { called = true; return 1; } });
    assert.throws(() => validateExperiment(config), /ordinary JSON data field/);
    assert.equal(called, false);
    const configArray = defaultExperiment();
    configArray.world.overrides.length = 1;
    Object.defineProperty(configArray.world.overrides, '0', {
        enumerable: true, get() { called = true; return { mask: 0, coefficient: 1 }; },
    });
    assert.throws(() => validateExperiment(configArray), /ordinary JSON array entry/);
    assert.equal(called, false);
});

test('rejects invented coefficients, observations, costs, dimensions and extra artifact fields', () => {
    const config = defaultExperiment();
    const original = construct(config);
    for (const mutate of [
        artifact => { artifact.model.coefficients[0].coefficient += 1; },
        artifact => { artifact.calibration.observations[0].response += 1; },
        artifact => { artifact.calibration.inputs[0] = 1; },
        artifact => { artifact.calibration.sample_count -= 1; },
        artifact => { artifact.model.coefficient_count += 1; },
        artifact => { artifact.costs.calibration_world_evaluations = 0; },
        artifact => { artifact.experiment.seed += 1; },
        artifact => { artifact.generator = 'another-generator'; },
        artifact => { artifact.synthetic = false; },
        artifact => { artifact.protected_holdout = true; },
        artifact => { artifact.limitations.physical_validation = true; },
        artifact => { artifact.source = '() => 42'; },
        artifact => { artifact.model.source = '() => 42'; },
        artifact => { artifact.model.coefficients[0].extra = true; },
        artifact => { artifact.model.coefficients.pop(); },
        artifact => { artifact.model.coefficients.push({ mask: 7, coefficient: 1 }); },
        artifact => { delete artifact.model.coefficients[0]; },
        artifact => { artifact.model.coefficients.extra = true; },
        artifact => { artifact.calibration.observations[0].response = NaN; },
        artifact => { artifact.calibration.observations[0].response = Infinity; },
        artifact => { artifact.model.coefficients = new Array(1000000); },
    ]) {
        const artifact = clone(original);
        mutate(artifact);
        assert.throws(() => evaluateConstruction(config, artifact, 'heldout'), TypeError);
    }
    assert.throws(() => evaluateConstruction(config, {}, 'heldout'), TypeError);
    assert.throws(() => evaluateConstruction(config, original, 'production'), /phase/);
    assert.throws(() => evaluateConstruction(config, original), /phase/);
});

test('artifact field order does not matter, frozen artifacts work and validation does not invoke accessors', () => {
    const config = defaultExperiment();
    const original = construct(config);
    const reversed = Object.fromEntries(Object.entries(original).reverse());
    Object.freeze(reversed);
    Object.freeze(reversed.model);
    assert.equal(evaluateConstruction(config, reversed, 'heldout').verdict, 'pass');
    let called = false;
    const artifact = construct(config);
    Object.defineProperty(artifact.model.coefficients[0], 'coefficient', {
        enumerable: true, get() { called = true; return 1; },
    });
    assert.throws(() => evaluateConstruction(config, artifact, 'heldout'), /ordinary JSON data field/);
    assert.equal(called, false);
});

test('the largest construction respects exposed calibration and world bounds', () => {
    const config = defaultExperiment();
    config.input_count = 8;
    config.world.degree = 3;
    config.world.coefficient_limit = 16;
    const artifact = construct(config);
    assert.equal(artifact.calibration.sample_count, WITNESS_LIMITS.max_calibration_samples);
    assert.equal(terms(config).length, WITNESS_LIMITS.max_world_terms);
    assert.equal(artifact.costs.calibration_world_basis_checks,
        WITNESS_LIMITS.max_calibration_samples * WITNESS_LIMITS.max_world_terms);
    for (const row of artifact.calibration.observations) assert.ok(Number.isSafeInteger(row.response));
    const report = evaluateConstruction(config, artifact, 'heldout');
    for (const row of report.comparisons.slice(0, -1)) {
        assert.ok(Number.isSafeInteger(row.expected.response));
        assert.ok(Number.isSafeInteger(row.actual.response));
        assert.ok(Math.abs(row.expected.response) <= 16 * WITNESS_LIMITS.max_world_terms);
    }
});
