// SPDX-License-Identifier: Apache-2.0
// Classical templates are supplied. These are independently generated, checked implementations.
import * as q from './rational.mjs';
import {canonical} from '../successor-capability/discovery-lab-contract.mjs';
export {canonical};

export const SCHEMA = 'autonomous-enterprise-artifact/v1';
export const METRIC = 'paper-declared-arithmetic-work/v1';
export const EXCLUDED_COSTS = Object.freeze(['indexing', 'allocation', 'serialization', 'hashing',
    'control overhead', 'rational bit growth', 'authoring', 'engineering', 'institutional review', 'money', 'energy']);
const need = (condition, message) => { if (!condition) throw Error(message); };
const clone = value => JSON.parse(canonical(value));
const sizeOK = n => Number.isSafeInteger(n) && n >= 1 && n <= 32 && (n & (n - 1)) === 0;
function checkerOptions(value, allowSize) {
    need(value && Object.getPrototypeOf(value) === Object.prototype, 'Provide ordinary checker configuration.');
    const captured = {};
    for (const key of Reflect.ownKeys(value)) {
        need(key === 'qualifyArtifact' || allowSize && key === 'maxN', 'Unsupported checker configuration.');
        const descriptor = Object.getOwnPropertyDescriptor(value, key);
        need(descriptor && Object.hasOwn(descriptor, 'value') && descriptor.enumerable,
            'Checker configuration must contain data descriptors.');
        captured[key] = descriptor.value;
    }
    need(typeof captured.qualifyArtifact === 'function', 'Provide the separately installed checker.');
    return captured;
}
export async function digestArtifact(artifact) {
    const bytes = new TextEncoder().encode(canonical(artifact));
    const hash = await crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(hash)].map(value => value.toString(16).padStart(2, '0')).join('');
}
const basis = (n, at) => Array.from({length: n}, (_, i) => i === at ? '1' : '0');
function parity(value) { let result = 0; while (value) { result ^= value & 1; value >>>= 1; } return result; }
function rowMix(left, right, a, b, meter) {
    meter.arithmetic += 1;
    if (a === 1) return b === 1 ? q.add(left, right) : q.subtract(left, right);
    if (b === 1) return q.subtract(right, left);
    meter.arithmetic += 1; return q.negate(q.add(left, right));
}
function transformWork(childWork, n, mix) {
    return 2 * childWork + (n / 2) * (2 + Number(mix[0] === -1 && mix[1] === -1)
        + Number(mix[2] === -1 && mix[3] === -1));
}
function internalEvaluate(artifact, byDigest, inputs, meter, depth = 0) {
    need(depth <= 7 && sizeOK(artifact.n), 'Artifact dimensions or depth exceed the foundry bound.');
    const n = artifact.n; const ast = artifact.ast;
    if (artifact.kind === 'identity') return inputs[0].slice();
    const transform = digest => {
        const child = byDigest.get(digest); need(child, 'Missing executable dependency.'); return child;
    };
    if (artifact.kind === 'walsh') {
        const parts = ast.inputLayout === 'halves'
            ? [inputs[0].slice(0, n / 2), inputs[0].slice(n / 2)]
            : [inputs[0].filter((_, i) => i % 2 === 0), inputs[0].filter((_, i) => i % 2 === 1)];
        const child = transform(ast.child);
        const left = internalEvaluate(child, byDigest, [parts[0]], meter, depth + 1);
        const right = internalEvaluate(child, byDigest, [parts[1]], meter, depth + 1);
        const first = [], second = [];
        for (let i = 0; i < n / 2; i++) {
            first.push(rowMix(left[i], right[i], ast.mix[0], ast.mix[1], meter));
            second.push(rowMix(left[i], right[i], ast.mix[2], ast.mix[3], meter));
        }
        return ast.outputLayout === 'blocks' ? first.concat(second) : first.flatMap((value, i) => [value, second[i]]);
    }
    const child = transform(ast.transform);
    if (artifact.kind === 'xor-convolution') {
        const left = internalEvaluate(child, byDigest, [inputs[0]], meter, depth + 1);
        const right = internalEvaluate(child, byDigest, [inputs[1]], meter, depth + 1);
        const products = left.map((value, i) => { meter.arithmetic++; return q.multiply(value, right[i]); });
        const result = internalEvaluate(child, byDigest, [products], meter, depth + 1);
        return result.map(value => { meter.arithmetic++; return q.divide(value, q.parse(ast.divisor)); });
    }
    need(artifact.kind === 'inverse', 'Unsupported arithmetic grammar.');
    const spectrum = ast.spectrum.map(q.parse);
    const transformed = internalEvaluate(child, byDigest, [inputs[0]], meter, depth + 1);
    const ratios = transformed.map((value, i) => { meter.arithmetic++; return q.divide(value, spectrum[i]); });
    return internalEvaluate(child, byDigest, [ratios], meter, depth + 1)
        .map(value => { meter.arithmetic++; return q.divide(value, q.parse(ast.divisor)); });
}

/** Execute only already qualified artifact envelopes. The separately implemented checker admits them. */
export async function evaluateArtifact(envelope, dependencies, inputs, options = {}) {
    const {qualifyArtifact} = checkerOptions(options, false);
    const retained = clone(envelope); const inherited = clone(dependencies); const capturedInputs = clone(inputs);
    need(retained.digest === await digestArtifact(retained.artifact), 'Artifact bytes do not match the frozen digest.');
    const checked = await qualifyArtifact(retained.artifact, inherited, {reference: 'direct'});
    need(checked.accepted === true, 'The frozen artifact failed current qualification.');
    const execution = executeQualified(retained.artifact, inherited, capturedInputs);
    const qualificationWork = selectedCharge(checked) + additionalCheckingWork(checked);
    return {...execution, qualificationWork, validationReceipt: checked,
        observedCountedWork: qualificationWork + execution.arithmetic};
}
export function executeQualified(artifact, dependencies, inputs) {
    need(sizeOK(artifact.n) && Array.isArray(inputs)
        && inputs.length === (artifact.kind === 'xor-convolution' ? 2 : 1)
        && inputs.every(input => Array.isArray(input) && input.length === artifact.n), 'Input shape mismatch.');
    const byDigest = new Map(dependencies.map(item => [item.digest, item.artifact]));
    const meter = {arithmetic: 0};
    const result = internalEvaluate(artifact, byDigest, inputs.map(input => input.map(q.parse)), meter);
    need(meter.arithmetic === artifact.operatingWork, 'Executed arithmetic differs from the bound.');
    return {output: result.map(q.encode), arithmetic: meter.arithmetic};
}
function newArtifact(kind, n, dependencies, ast, operatingWork, certificate = {}) {
    return {schema: SCHEMA, kind, n, dependencies, ast, operatingWork, certificate};
}
function selectedCharge(verification) {
    need(verification.accepted === true && ['arithmetic', 'comparisons', 'matrixComparisons']
        .every(key => Number.isSafeInteger(verification[key] || 0) && (verification[key] || 0) >= 0),
    'Independent qualification did not provide a valid counted receipt.');
    return verification.arithmetic + verification.comparisons + (verification.matrixComparisons || 0);
}
function additionalCheckingWork(verification) {
    return ['dependencyChecks', 'scopeChecks'].reduce((sum, key) => sum
        + (verification[key]?.arithmetic || 0) + (verification[key]?.comparisons || 0), 0);
}
async function admit(artifact, envelopes, qualifyArtifact, options = {reference: 'direct'}) {
    const digest = await digestArtifact(artifact);
    const verification = await qualifyArtifact(clone(artifact), clone(envelopes), options);
    const work = selectedCharge(verification);
    return {envelope: {digest, artifact}, verification, work};
}
function candidateMatrix(child, n, ast, meter) {
    const result = [];
    for (let out = 0; out < n; out++) {
        const row = [];
        const block = ast.outputLayout === 'blocks' ? Math.floor(out / (n / 2)) : out % 2;
        const at = ast.outputLayout === 'blocks' ? out % (n / 2) : Math.floor(out / 2);
        for (let input = 0; input < n; input++) {
            const part = ast.inputLayout === 'halves' ? Math.floor(input / (n / 2)) : input % 2;
            const col = ast.inputLayout === 'halves' ? input % (n / 2) : Math.floor(input / 2);
            const coefficient = q.multiply(q.parse(ast.mix[block * 2 + part]), q.parse(child.certificate.matrix[at][col]));
            meter.coefficientOperations++; row.push(q.encode(coefficient));
        }
        result.push(row);
    }
    return result;
}
export async function constructTransform(childEnvelope, envelopes, qualifyArtifact) {
    childEnvelope = clone(childEnvelope); envelopes = clone(envelopes);
    const child = childEnvelope.artifact; const n = child.n * 2;
    need(sizeOK(n), 'Transform construction is bounded at dimension32.');
    const specification = []; const preparation = {specificationCells: 0, candidateRecords: 0,
        coefficientOperations: 0, coefficientComparisons: 0};
    for (let i = 0; i < n; i++) {
        const row = [];
        for (let j = 0; j < n; j++) { row.push(parity(i & j) ? '-1' : '1'); preparation.specificationCells++; }
        specification.push(row);
    }
    const attempts = []; let selected = null;
    for (const inputLayout of ['halves', 'alternating']) for (const outputLayout of ['blocks', 'interleaving']) {
        for (let bits = 0; bits < 16; bits++) {
            const mix = Array.from({length: 4}, (_, i) => bits & (1 << i) ? -1 : 1);
            const ast = {op: 'split-mix', child: childEnvelope.digest, inputLayout, outputLayout, mix};
            const local = {coefficientOperations: 0, coefficientComparisons: 0};
            const matrix = candidateMatrix(child, n, ast, local); let mismatches = 0; let firstMismatch = null;
            for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
                local.coefficientComparisons++;
                if (matrix[i][j] !== specification[i][j]) {
                    mismatches++; firstMismatch ||= {row: i, column: j, actual: matrix[i][j], expected: specification[i][j]};
                }
            }
            preparation.candidateRecords++; preparation.coefficientOperations += local.coefficientOperations;
            preparation.coefficientComparisons += local.coefficientComparisons;
            const candidate = {index: attempts.length, ast, status: mismatches ? 'REJECTED' : 'MATCH',
                mismatches, firstMismatch, receipts: {candidateRecords: 1, ...local}};
            attempts.push(candidate);
            if (!mismatches && !selected) selected = newArtifact('walsh', n, [childEnvelope.digest], ast,
                transformWork(child.operatingWork, n, mix), {matrix});
        }
    }
    need(selected !== null, 'Finite transform grammar produced no candidate.');
    const admitted = await admit(selected, envelopes, qualifyArtifact);
    const constructionWork = Object.values(preparation).reduce((sum, value) => sum + value, 0);
    return {...admitted, attempts, preparation, constructionWork, totalWork: constructionWork + admitted.work};
}
export async function constructConvolution(transformEnvelope, envelopes, qualifyArtifact) {
    transformEnvelope = clone(transformEnvelope); envelopes = clone(envelopes);
    const n = transformEnvelope.artifact.n; const attempts = []; let selected = null;
    const preparation = {candidateRecords: 0, arithmetic: 0, comparisons: 0};
    const anchor = [basis(n, 0), basis(n, 0)];
    for (const divisor of [-n, -1, 1, n]) {
        const artifact = newArtifact('xor-convolution', n, [transformEnvelope.digest],
            {op: 'xor-convolution', transform: transformEnvelope.digest, divisor: String(divisor)},
            3 * transformEnvelope.artifact.operatingWork + 2 * n);
        const execution = executeQualified(artifact, envelopes, anchor); let mismatches = 0;
        for (let i = 0; i < n; i++) { preparation.comparisons++; if (execution.output[i] !== anchor[0][i]) mismatches++; }
        preparation.candidateRecords++; preparation.arithmetic += execution.arithmetic;
        attempts.push({ast: artifact.ast, status: mismatches ? 'REJECTED' : 'ANCHOR_MATCH_NOT_CERTIFIED',
            inputs: anchor, output: execution.output, mismatches,
            receipts: {candidateRecords: 1, arithmetic: execution.arithmetic, comparisons: n}});
        if (!mismatches && !selected) selected = artifact;
    }
    need(selected !== null, 'Convolution normalization search failed.');
    const admitted = await admit(selected, envelopes, qualifyArtifact);
    const constructionWork = Object.values(preparation).reduce((sum, value) => sum + value, 0);
    return {...admitted, attempts, preparation, constructionWork, totalWork: constructionWork + admitted.work};
}
export async function constructInverse(transformEnvelope, envelopes, qualifyArtifact,
    options = {}) {
    transformEnvelope = clone(transformEnvelope); envelopes = clone(envelopes); options = clone(options);
    let {kernel, reference = 'direct', convolutionDigest} = options;
    const n = transformEnvelope.artifact.n;
    kernel = kernel || Array.from({length: n}, (_, i) => String(i === 0 ? n + 1 : 1));
    const capturedKernel = kernel.map(value => q.encode(q.parse(value)));
    need(capturedKernel.length === n, 'Kernel dimension mismatch.');
    const transformed = executeQualified(transformEnvelope.artifact, envelopes, [capturedKernel]);
    const preparation = {arithmetic: transformed.arithmetic, comparisons: 0}; const singular = [];
    for (let i = 0; i < n; i++) { preparation.comparisons++; if (transformed.output[i] === '0') singular.push(i); }
    const constructionWork = preparation.arithmetic + preparation.comparisons;
    if (singular.length) return {state: 'REJECTED', reason: 'SINGULAR_KERNEL', kernel: capturedKernel,
        spectrum: transformed.output, singular, preparation, constructionWork, totalWork: constructionWork};
    const artifact = newArtifact('inverse', n, [transformEnvelope.digest], {op: 'spectral-inverse',
        transform: transformEnvelope.digest, kernel: capturedKernel, spectrum: transformed.output, divisor: String(n)},
    2 * transformEnvelope.artifact.operatingWork + 2 * n);
    const admitted = await admit(artifact, envelopes, qualifyArtifact,
        convolutionDigest === undefined ? {reference} : {reference, convolutionDigest});
    return {...admitted, state: 'ACCEPTED', preparation, constructionWork,
        totalWork: constructionWork + admitted.work};
}

function cheapestRecipePlan(recipes, target, initial = 0) {
    const pending = [{stock: initial, cost: 0, steps: []}]; const best = new Map([[initial, 0]]);
    while (pending.length) {
        pending.sort((a, b) => a.cost - b.cost || a.stock - b.stock);
        const current = pending.shift();
        if (current.cost !== best.get(current.stock)) continue;
        if ((current.stock & target) === target) return {...current, status: 'OPTIMAL'};
        for (const recipe of recipes) {
            if ((current.stock & recipe.requires) !== recipe.requires) continue;
            const stock = current.stock | recipe.produces; const cost = current.cost + recipe.charge;
            if (stock === current.stock || cost >= (best.get(stock) ?? Infinity)) continue;
            best.set(stock, cost);
            pending.push({stock, cost, steps: current.steps.concat({recipe: recipe.id,
                before: current.stock, after: stock, charge: recipe.charge, cumulativeCharge: cost})});
        }
    }
    return {status: 'UNREACHABLE', stock: initial, cost: null, steps: []};
}

/** All 320 transform candidates, four divisors, every selected basis case and both inverse paths. */
export async function buildFoundry(options = {}) {
    const {qualifyArtifact, maxN = 32} = checkerOptions(options, true);
    need(typeof qualifyArtifact === 'function' && sizeOK(maxN) && maxN >= 2,
        'Provide the independently implemented checker and a power-of-two maximum2..32.');
    const identity = newArtifact('identity', 1, [], {op: 'identity'}, 0, {matrix: [['1']]});
    const envelopes = [{digest: await digestArtifact(identity), artifact: identity}];
    const identityVerification = await qualifyArtifact(clone(identity), []);
    need(identityVerification.accepted === true, 'Identity admission failed.');
    const transforms = []; let retained = envelopes[0];
    for (let n = 2; n <= maxN; n *= 2) {
        const next = await constructTransform(retained, envelopes, qualifyArtifact);
        transforms.push(next); retained = next.envelope; envelopes.push(retained);
    }
    const convolution = await constructConvolution(retained, envelopes, qualifyArtifact);
    envelopes.push(convolution.envelope);
    const inverseDirect = await constructInverse(retained, envelopes, qualifyArtifact);
    const inverseInherited = await constructInverse(retained, envelopes, qualifyArtifact,
        {reference: 'inherited', convolutionDigest: convolution.envelope.digest});
    need(inverseDirect.envelope.digest === inverseInherited.envelope.digest, 'Inverse architectures changed the product.');
    envelopes.push(inverseInherited.envelope);
    const transformChain = transforms.reduce((sum, item) => sum + item.totalWork, 0);
    const counts = {transformChain, incrementalConvolution: convolution.totalWork,
        inverseDirect: inverseDirect.totalWork, inverseInherited: inverseInherited.totalWork,
        inverseOnlyViaNewConvolution: convolution.totalWork + inverseInherited.totalWork,
        isolated: 3 * transformChain + convolution.totalWork + inverseDirect.totalWork,
        joint: transformChain + convolution.totalWork + inverseInherited.totalWork,
        operating: {transform: retained.artifact.operatingWork,
            convolution: convolution.envelope.artifact.operatingWork, inverse: inverseInherited.envelope.artifact.operatingWork}};
    const recipes = transforms.map((item, i) => ({id: `construct-F${item.envelope.artifact.n}`,
        requires: i === 0 ? 0 : 1 << (i - 1), produces: 1 << i, charge: item.totalWork}));
    const transformBit = 1 << (transforms.length - 1);
    const convolutionBit = 1 << transforms.length; const inverseBit = convolutionBit << 1;
    recipes.push({id: 'construct-convolution', requires: transformBit, produces: convolutionBit,
        charge: convolution.totalWork}, {id: 'construct-inverse-direct', requires: transformBit,
        produces: inverseBit, charge: inverseDirect.totalWork}, {id: 'construct-inverse-inherited',
        requires: transformBit | convolutionBit, produces: inverseBit, charge: inverseInherited.totalWork});
    const jointPlan = cheapestRecipePlan(recipes, transformBit | convolutionBit | inverseBit);
    const inverseOnlyPlan = cheapestRecipePlan(recipes, inverseBit, (1 << transforms.length) - 1);
    counts.unrestrictedSamePrimitiveJointPlanner = jointPlan.cost;
    const builds = transforms.concat([convolution, inverseDirect, inverseInherited]);
    const observedWorkLedger = {
        constructorPreparation: builds.reduce((sum, build) => sum + build.constructionWork, 0),
        selectedQualifications: builds.reduce((sum, build) => sum + build.work, 0),
        additionalCurrentDependencyAndScopeChecks: builds.reduce((sum, build) => sum
            + additionalCheckingWork(build.verification), 0),
        identityResearchAdmission: selectedCharge(identityVerification) + additionalCheckingWork(identityVerification)
    };
    observedWorkLedger.totalCountedCampaignWork = Object.values(observedWorkLedger).reduce((sum, value) => sum + value, 0);
    return {schema: 'autonomous-enterprise-foundry/v1', reproduction: 'INDEPENDENT_REIMPLEMENTATION', maxN,
        metric: METRIC, excludedCosts: [...EXCLUDED_COSTS], totalCostComplete: false,
        isolatedComparisonScope: 'Specified isolated architecture recomposed from executed per-build receipts; repeated full builds are not separately wall-clock metered.',
        identity: {envelope: envelopes[0], verification: identityVerification, chargeScope: 'additional research admission'},
        transforms, convolution, inverseDirect, inverseInherited, envelopes, counts,
        observedWorkLedger, recipes, plans: {joint: jointPlan, inverseOnly: inverseOnlyPlan},
        controls: {inverseOnly: {selected: inverseOnlyPlan.steps.at(-1).recipe,
            alternatives: [counts.inverseDirect, counts.inverseOnlyViaNewConvolution],
            result: counts.inverseOnlyViaNewConvolution > counts.inverseDirect ? 'DO_NOT_BUILD_CONVOLUTION_FOR_ONE_INVERSE' : 'TIE_OR_REVIEW'},
        unrestrictedJoint: {result: jointPlan.cost === counts.joint ? 'TIE' : 'DIFFERENT', cost: jointPlan.cost,
            scope: 'Same supplied primitives and build/checking recipes; not a compiler benchmark.'}},
        claims: ['Classical transform/convolution/inverse templates and finite grammar are supplied.',
            'Basis completeness follows only within the structurally linear/bilinear grammar.',
            'Arithmetic counts exclude bit complexity, wall-clock time, money and energy.',
            'The historical transform and convolution charges remain charged to the complete lineage.']};
}
