// SPDX-License-Identifier: Apache-2.0
/**
 * A bounded, transparent synthetic measurement witness, not a physical experiment.
 *
 * Config schema (all keys required; no additional keys accepted):
 * {
 *   version: WITNESS_VERSION,
 *   input_count: integer in [4, 8],
 *   model_degree: 1 | 2,
 *   seed: unsigned 32-bit integer,
 *   world: {
 *     degree: 1 | 2 | 3,
 *     coefficient_limit: integer in [1, 16],
 *     overrides: ascending unique [{mask, coefficient}] within the world's degree
 *   },
 *   threshold: integer in [-2048, 2048]
 * }
 *
 * A mask encodes a binary input, with bit zero denoting the first input. The
 * response is sum(c[S] for S subset of mask). The fixed generator assigns each
 * allowed S a nonzero bounded integer; explicit overrides may include zero.
 * Calibration measures exactly the masks of popcount <= model_degree. Subset
 * Möbius inversion constructs a reusable coefficient vector from those actual
 * observations, without reading the generator's coefficients into the model.
 *
 * All remaining masks, in ascending order, alternate heldout/development,
 * starting with heldout. Both phases are nonempty and exclude calibration.
 * These public synthetic partitions are NOT protected holdouts. The parent
 * workspace is responsible for freezing its candidate before evaluation.
 */

export const WITNESS_VERSION = 'binary-interaction-instrument/v1';

export const WITNESS_LIMITS = Object.freeze({
    min_inputs: 4,
    max_inputs: 8,
    min_model_degree: 1,
    max_model_degree: 2,
    max_world_degree: 3,
    max_coefficient: 16,
    max_threshold_abs: 2048,
    max_seed: 4294967295,
    max_input_masks: 256,
    max_calibration_samples: 37,
    max_world_terms: 93,
});

const CONFIG_KEYS = ['version', 'input_count', 'model_degree', 'seed', 'world', 'threshold'];
const WORLD_KEYS = ['degree', 'coefficient_limit', 'overrides'];
const TERM_KEYS = ['mask', 'coefficient'];
const GENERATOR_VERSION = 'fixed-binary-polynomial/v1';

function fail(message) {
    throw new TypeError(message);
}

function record(value, keys, label) {
    if (!value || typeof value !== 'object' || Array.isArray(value)
        || Object.getPrototypeOf(value) !== Object.prototype) {
        fail(`${label} must be a plain JSON object.`);
    }
    const ownKeys = Reflect.ownKeys(value);
    if (ownKeys.length !== keys.length || !keys.every(key => ownKeys.includes(key))) {
        fail(`${label} must have exactly these fields: ${keys.join(', ')}.`);
    }
    for (const key of keys) {
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        if (!Object.hasOwn(descriptor, 'value') || !descriptor.enumerable) {
            fail(`${label}.${key} must be an ordinary JSON data field.`);
        }
    }
}

function denseArray(value, maximum, label) {
    if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype || value.length > maximum) {
        fail(`${label} must be an array with at most ${maximum} entries.`);
    }
    if (Reflect.ownKeys(value).length !== value.length + 1) {
        fail(`${label} must be dense and have no additional fields.`);
    }
    for (let index = 0; index < value.length; index += 1) {
        const descriptor = Object.getOwnPropertyDescriptor(value, String(index));
        if (!descriptor || !Object.hasOwn(descriptor, 'value') || !descriptor.enumerable) {
            fail(`${label}[${index}] must be an ordinary JSON array entry.`);
        }
    }
}

function integer(value, minimum, maximum, label) {
    if (!Number.isSafeInteger(value) || Object.is(value, -0) || value < minimum || value > maximum) {
        fail(`${label} must be an integer from ${minimum} to ${maximum}.`);
    }
    return value;
}

function popcount(mask) {
    let count = 0;
    for (let remaining = mask; remaining !== 0; remaining &= remaining - 1) count += 1;
    return count;
}

function masksForDegree(inputCount, degree) {
    const masks = [];
    for (let mask = 0; mask < 2 ** inputCount; mask += 1) {
        if (popcount(mask) <= degree) masks.push(mask);
    }
    return masks;
}

function limitations() {
    return {
        synthetic: true,
        protected_holdout: false,
        physical_validation: false,
        superiority_claim: false,
        revenue_claim: false,
        unrestricted_engineering_comparison: false,
        scope: 'Exact tests in a fixed integer polynomial world, not evidence of general discovery or business value.',
        cost_scope: 'Call counts and selected arithmetic only; not physical cost, wall-clock savings, or superiority.',
        holdout_scope: 'Public deterministic synthetic partitions, not secret or independently protected tests.',
    };
}

/** Return a fresh, successful quadratic experiment. All responses are computed. */
export function defaultExperiment() {
    return {
        version: WITNESS_VERSION,
        input_count: 5,
        model_degree: 2,
        seed: 17,
        world: { degree: 2, coefficient_limit: 8, overrides: [] },
        threshold: 12,
    };
}

/** Validate the closed bounded JSON schema, returning an independent clone. */
export function validateExperiment(config) {
    record(config, CONFIG_KEYS, 'experiment');
    if (config.version !== WITNESS_VERSION) fail(`experiment.version must be ${WITNESS_VERSION}.`);
    const inputCount = integer(config.input_count, 4, 8, 'experiment.input_count');
    const modelDegree = integer(config.model_degree, 1, 2, 'experiment.model_degree');
    const seed = integer(config.seed, 0, WITNESS_LIMITS.max_seed, 'experiment.seed');
    const threshold = integer(config.threshold, -2048, 2048, 'experiment.threshold');
    record(config.world, WORLD_KEYS, 'experiment.world');
    const worldDegree = integer(config.world.degree, 1, 3, 'experiment.world.degree');
    const coefficientLimit = integer(config.world.coefficient_limit, 1, 16, 'experiment.world.coefficient_limit');
    denseArray(config.world.overrides, WITNESS_LIMITS.max_world_terms, 'experiment.world.overrides');
    let previousMask = -1;
    const overrides = config.world.overrides.map((entry, index) => {
        const label = `experiment.world.overrides[${index}]`;
        record(entry, TERM_KEYS, label);
        const mask = integer(entry.mask, 0, 2 ** inputCount - 1, `${label}.mask`);
        const coefficient = integer(entry.coefficient, -coefficientLimit, coefficientLimit, `${label}.coefficient`);
        if (mask <= previousMask) fail('experiment.world.overrides masks must be unique and strictly ascending.');
        if (popcount(mask) > worldDegree) fail(`${label}.mask exceeds the declared world degree.`);
        previousMask = mask;
        return { mask, coefficient };
    });
    return {
        version: WITNESS_VERSION,
        input_count: inputCount,
        model_degree: modelDegree,
        seed,
        world: { degree: worldDegree, coefficient_limit: coefficientLimit, overrides },
        threshold,
    };
}

// Fixed integer mixing, not randomness, cryptography, source evaluation, or a service call.
function generatedCoefficient(seed, mask, limit) {
    let state = (seed ^ Math.imul(mask + 1, 0x9e3779b1)) >>> 0;
    state = Math.imul(state ^ (state >>> 16), 0x85ebca6b) >>> 0;
    state = Math.imul(state ^ (state >>> 13), 0xc2b2ae35) >>> 0;
    state = (state ^ (state >>> 16)) >>> 0;
    const residue = state % (2 * limit);
    return residue < limit ? residue - limit : residue - limit + 1;
}

function worldTerms(config) {
    const overrides = new Map(config.world.overrides.map(term => [term.mask, term.coefficient]));
    return masksForDegree(config.input_count, config.world.degree).map(mask => ({
        mask,
        coefficient: overrides.has(mask)
            ? overrides.get(mask)
            : generatedCoefficient(config.seed, mask, config.world.coefficient_limit),
    }));
}

function response(coefficients, inputMask) {
    let total = 0;
    for (const term of coefficients) {
        if ((inputMask & term.mask) === term.mask) total += term.coefficient;
    }
    return total;
}

function constructValidated(config) {
    const inputs = masksForDegree(config.input_count, config.model_degree);
    const sourceTerms = worldTerms(config);
    const observations = inputs.map(mask => ({ mask, response: response(sourceTerms, mask) }));
    const coefficients = [];
    let coefficientSubtractions = 0;
    for (const observation of observations) {
        let coefficient = observation.response;
        for (const term of coefficients) {
            if ((observation.mask & term.mask) === term.mask) {
                coefficient -= term.coefficient;
                coefficientSubtractions += 1;
            }
        }
        coefficients.push({ mask: observation.mask, coefficient });
    }
    return {
        version: WITNESS_VERSION,
        kind: 'mobius-response-model',
        synthetic: true,
        protected_holdout: false,
        experiment: config,
        generator: GENERATOR_VERSION,
        calibration: {
            method: 'subset-mobius-inversion',
            inputs,
            observations,
            sample_count: inputs.length,
        },
        model: {
            basis: 'boolean-subset-products',
            coefficients,
            coefficient_count: coefficients.length,
        },
        costs: {
            calibration_world_evaluations: inputs.length,
            calibration_world_basis_checks: inputs.length * sourceTerms.length,
            coefficient_subtractions: coefficientSubtractions,
            model_terms_stored: coefficients.length,
        },
        limitations: limitations(),
    };
}

/** Construct a deterministic JSON model artifact by measuring and inverting. */
export function construct(config) {
    return constructValidated(validateExperiment(config));
}

// Compare against a recomputed construction. Schema and values must both match;
// property order is irrelevant, but missing, extra, sparse, or accessor data fail.
function assertConsistent(actual, expected, path = 'artifact') {
    if (Array.isArray(expected)) {
        denseArray(actual, expected.length, path);
        if (actual.length !== expected.length) fail(`${path} has an inconsistent array size.`);
        for (let index = 0; index < expected.length; index += 1) {
            assertConsistent(actual[index], expected[index], `${path}[${index}]`);
        }
    } else if (expected && typeof expected === 'object') {
        record(actual, Object.keys(expected), path);
        for (const key of Object.keys(expected)) assertConsistent(actual[key], expected[key], `${path}.${key}`);
    } else if (!Object.is(actual, expected)) {
        fail(`${path} does not match the computed construction.`);
    }
}

function evaluationPartitions(config) {
    const development = [];
    const heldout = [];
    let index = 0;
    for (let mask = 0; mask < 2 ** config.input_count; mask += 1) {
        if (popcount(mask) <= config.model_degree) continue;
        (index % 2 === 0 ? heldout : development).push(mask);
        index += 1;
    }
    return { development, heldout };
}

function ranking(rows, field) {
    return [...rows].sort((left, right) => right[field] - left[field] || left.mask - right.mask)
        .map(row => row.mask);
}

/**
 * Check a frozen candidate's exact responses and phase-specific reuse tasks.
 * Consistency checking itself remeasures calibration and is explicitly costed.
 * The given artifact's coefficients, not recomputed coefficients, answer queries.
 */
export function evaluateConstruction(config, artifact, phase) {
    const experiment = validateExperiment(config);
    if (phase !== 'development' && phase !== 'heldout') fail('phase must be development or heldout.');
    const checkedConstruction = constructValidated(experiment);
    assertConsistent(artifact, checkedConstruction);
    const partitions = evaluationPartitions(experiment);
    const masks = partitions[phase];
    const sourceTerms = worldTerms(experiment);
    const rows = masks.map(mask => ({
        mask,
        expected: response(sourceTerms, mask),
        actual: response(artifact.model.coefficients, mask),
    }));
    const comparisons = [];
    const failureReasons = [];
    for (const row of rows) {
        const responseMatches = row.expected === row.actual;
        if (!responseMatches) {
            failureReasons.push({
                code: 'response-mismatch', mask: row.mask, expected: row.expected, actual: row.actual,
            });
        }
        if (phase === 'development') {
            comparisons.push({
                task_type: 'response-reconstruction',
                query: { mask: row.mask },
                expected: { response: row.expected },
                actual: { response: row.actual },
                pass: responseMatches,
            });
        } else {
            const expectedDecision = row.expected >= experiment.threshold;
            const actualDecision = row.actual >= experiment.threshold;
            if (expectedDecision !== actualDecision) {
                failureReasons.push({
                    code: 'threshold-decision-mismatch', mask: row.mask,
                    expected: expectedDecision, actual: actualDecision,
                });
            }
            comparisons.push({
                task_type: 'threshold-classification',
                query: { mask: row.mask, threshold: experiment.threshold },
                expected: { response: row.expected, at_or_above_threshold: expectedDecision },
                actual: { response: row.actual, at_or_above_threshold: actualDecision },
                response_match: responseMatches,
                decision_match: expectedDecision === actualDecision,
                pass: responseMatches && expectedDecision === actualDecision,
            });
        }
    }
    if (phase === 'heldout') {
        const expectedRanking = ranking(rows, 'expected');
        const actualRanking = ranking(rows, 'actual');
        const rankMatches = expectedRanking.every((mask, index) => mask === actualRanking[index]);
        comparisons.push({
            task_type: 'response-ranking',
            query: { masks: [...masks], order: 'descending-response-then-ascending-mask' },
            expected: { ordered_masks: expectedRanking },
            actual: { ordered_masks: actualRanking },
            pass: rankMatches,
        });
        if (!rankMatches) {
            failureReasons.push({ code: 'ranking-mismatch', expected: expectedRanking, actual: actualRanking });
        }
    }
    return {
        version: WITNESS_VERSION,
        kind: 'binary-interaction-evaluation',
        phase,
        synthetic: true,
        protected_holdout: false,
        task_types: phase === 'development'
            ? ['response-reconstruction'] : ['threshold-classification', 'response-ranking'],
        verdict: failureReasons.length === 0 ? 'pass' : 'fail',
        evaluation_masks: [...masks],
        calibration_overlap_count: 0,
        other_phase_overlap_count: 0,
        response_match_count: rows.filter(row => row.expected === row.actual).length,
        comparison_count: comparisons.length,
        comparisons,
        failure_reasons: failureReasons,
        acceptance: 'Every exact response and downstream decision must agree; approximate agreement is not accepted.',
        costs: {
            construction: { ...checkedConstruction.costs },
            this_evaluation: {
                artifact_validation_world_evaluations: checkedConstruction.calibration.sample_count,
                artifact_validation_world_basis_checks: checkedConstruction.costs.calibration_world_basis_checks,
                artifact_validation_coefficient_subtractions: checkedConstruction.costs.coefficient_subtractions,
                reference_world_evaluations: masks.length,
                reference_world_basis_checks: masks.length * sourceTerms.length,
                reuse_model_evaluations: masks.length,
                reuse_model_basis_checks: masks.length * artifact.model.coefficient_count,
                downstream_threshold_decisions: phase === 'heldout' ? masks.length : 0,
                downstream_rankings: phase === 'heldout' ? 1 : 0,
                total_world_evaluations: checkedConstruction.calibration.sample_count + masks.length,
            },
        },
        limitations: limitations(),
    };
}
