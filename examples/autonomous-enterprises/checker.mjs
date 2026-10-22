// SPDX-License-Identifier: Apache-2.0
// Separately authored finite checker; no constructor or constructor interpreter is imported.
import {canonical as dataCanonical} from '../successor-capability/discovery-lab-contract.mjs';

const SCHEMA = 'autonomous-enterprise-artifact/v1';
const HASH = /^[a-f0-9]{64}$/;
const utf8 = new TextEncoder();
const need = (condition, message) => { if (!condition) throw Error(message); };
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const width = n => Number.isSafeInteger(n) && n >= 1 && n <= 32 && (n & (n - 1)) === 0;
const integer = n => Number.isSafeInteger(n) && n >= 0 && !Object.is(n, -0);

function snapshot(value) { return JSON.parse(dataCanonical(value)); }

export function canonical(value) { return dataCanonical(value); }
async function digestCanonical(encoded) {
    const digest = await crypto.subtle.digest('SHA-256', utf8.encode(encoded));
    return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}
export async function hashArtifact(value) { return digestCanonical(canonical(value)); }

const abs = x => x < 0n ? -x : x;
function fraction(a, b = 1n) {
    need(b !== 0n, 'Division by zero in rational grammar.');
    if (b < 0n) { a = -a; b = -b; }
    let x = abs(a), y = b;
    while (y) { const r = x % y; x = y; y = r; }
    const out = {a: a / x, b: b / x};
    need(abs(out.a).toString(2).length <= 2048 && out.b.toString(2).length <= 2048,
        'Rational arithmetic bit bound exceeded.');
    return out;
}
const format = q => q.b === 1n ? String(q.a) : `${q.a}/${q.b}`;
function parse(text) {
    need(typeof text === 'string' && text.length <= 160 && /^-?(?:0|[1-9][0-9]*)(?:\/[1-9][0-9]*)?$/.test(text),
        'Canonical bounded rational text required.');
    const [a, b = '1'] = text.split('/');
    const out = fraction(BigInt(a), BigInt(b));
    need(format(out) === text, 'Rational text must be reduced with a positive denominator.');
    return out;
}
const zero = () => fraction(0n);
const one = () => fraction(1n);
const equal = (a, b) => a.a === b.a && a.b === b.b;
function add(a, b, meter) { meter.arithmetic++; return fraction(a.a * b.b + b.a * a.b, a.b * b.b); }
function subtract(a, b, meter) { meter.arithmetic++; return fraction(a.a * b.b - b.a * a.b, a.b * b.b); }
function negate(a, meter) { meter.arithmetic++; return fraction(-a.a, a.b); }
function multiply(a, b, meter) { meter.arithmetic++; return fraction(a.a * b.a, a.b * b.b); }
function divide(a, b, meter) { meter.arithmetic++; return fraction(a.a * b.b, a.b * b.a); }
const vector = (n, at) => Array.from({length: n}, (_, i) => i === at ? one() : zero());
function vectorInput(value, n) {
    need(Array.isArray(value) && value.length === n, 'Input vector dimension differs from artifact.');
    return value.map(parse);
}
function character(i, j) {
    let bits = i & j, sign = 1n;
    while (bits) { sign = -sign; bits &= bits - 1; }
    return fraction(sign);
}
function directWalsh(input, meter) {
    return input.map((_, i) => {
        let out = character(i, 0).a > 0n ? input[0] : negate(input[0], meter);
        for (let j = 1; j < input.length; j++) {
            out = character(i, j).a > 0n ? add(out, input[j], meter) : subtract(out, input[j], meter);
        }
        return out;
    });
}
function directXor(left, right, meter) {
    return left.map((_, i) => {
        let out = multiply(left[0], right[i], meter);
        for (let j = 1; j < left.length; j++) out = add(out, multiply(left[j], right[i ^ j], meter), meter);
        return out;
    });
}

function shape(artifact) {
    need(exact(artifact, ['schema', 'kind', 'n', 'dependencies', 'ast', 'operatingWork', 'certificate'])
        && artifact.schema === SCHEMA && width(artifact.n) && integer(artifact.operatingWork),
    'Unsupported artifact frame.');
    const {n, ast, kind, certificate, dependencies} = artifact;
    need(Array.isArray(dependencies) && dependencies.length <= 1
        && dependencies.every(hash => typeof hash === 'string' && HASH.test(hash)), 'Invalid dependency identities.');
    if (kind === 'identity') {
        need(n === 1 && exact(ast, ['op']) && ast.op === 'identity' && dependencies.length === 0,
            'Identity grammar is one-dimensional.');
    } else if (kind === 'walsh') {
        need(n >= 2 && exact(ast, ['op', 'child', 'inputLayout', 'outputLayout', 'mix']) && ast.op === 'split-mix'
            && ['halves', 'alternating'].includes(ast.inputLayout)
            && ['blocks', 'interleaving'].includes(ast.outputLayout)
            && Array.isArray(ast.mix) && ast.mix.length === 4 && ast.mix.every(x => x === 1 || x === -1)
            && dependencies.length === 1 && dependencies[0] === ast.child, 'Invalid linear split/mix grammar.');
    } else if (kind === 'xor-convolution') {
        need(exact(ast, ['op', 'transform', 'divisor']) && ast.op === 'xor-convolution'
            && dependencies.length === 1 && dependencies[0] === ast.transform, 'Invalid bilinear convolution grammar.');
        need(parse(ast.divisor).a !== 0n, 'Convolution divisor is zero.');
    } else if (kind === 'inverse') {
        need(exact(ast, ['op', 'transform', 'kernel', 'spectrum', 'divisor']) && ast.op === 'spectral-inverse'
            && dependencies.length === 1 && dependencies[0] === ast.transform, 'Invalid fixed-kernel linear inverse grammar.');
        vectorInput(ast.kernel, n); vectorInput(ast.spectrum, n);
        need(parse(ast.divisor).a !== 0n, 'Inverse divisor is zero.');
        need(ast.spectrum.every(x => parse(x).a !== 0n), 'Singular kernel spectrum is not invertible.');
    } else throw Error('Unknown arithmetic artifact kind.');
    if (kind === 'identity' || kind === 'walsh') {
        need(exact(certificate, ['matrix']) && Array.isArray(certificate.matrix) && certificate.matrix.length === n,
            'Linear matrix certificate missing.');
        certificate.matrix.forEach(row => vectorInput(row, n));
    } else need(exact(certificate, []), 'Unexpected certificate metadata.');
    return artifact;
}

function execute(artifact, registry, inputs, meter, depth = 0) {
    need(depth <= 6, 'Arithmetic dependency depth exceeds the finite grammar.');
    const {n, ast, kind} = artifact;
    if (kind === 'identity') return inputs[0].slice();
    if (kind === 'walsh') {
        const child = registry.get(ast.child), half = n / 2;
        const left = [], right = [];
        for (let i = 0; i < half; i++) {
            left.push(inputs[0][ast.inputLayout === 'halves' ? i : 2 * i]);
            right.push(inputs[0][ast.inputLayout === 'halves' ? i + half : 2 * i + 1]);
        }
        const u = execute(child, registry, [left], meter, depth + 1);
        const v = execute(child, registry, [right], meter, depth + 1);
        const out = Array(n), [a, b, c, d] = ast.mix;
        for (let i = 0; i < half; i++) {
            const mix = (x, y) => x === 1 ? (y === 1 ? add(u[i], v[i], meter) : subtract(u[i], v[i], meter))
                : y === 1 ? subtract(v[i], u[i], meter) : negate(add(u[i], v[i], meter), meter);
            out[ast.outputLayout === 'blocks' ? i : 2 * i] = mix(a, b);
            out[ast.outputLayout === 'blocks' ? i + half : 2 * i + 1] = mix(c, d);
        }
        return out;
    }
    const transform = registry.get(ast.transform);
    if (kind === 'xor-convolution') {
        const left = execute(transform, registry, [inputs[0]], meter, depth + 1);
        const right = execute(transform, registry, [inputs[1]], meter, depth + 1);
        const product = left.map((x, i) => multiply(x, right[i], meter));
        return execute(transform, registry, [product], meter, depth + 1).map(x => divide(x, parse(ast.divisor), meter));
    }
    const spectrum = ast.spectrum.map(parse);
    const transformed = execute(transform, registry, [inputs[0]], meter, depth + 1);
    const quotient = transformed.map((x, i) => divide(x, spectrum[i], meter));
    return execute(transform, registry, [quotient], meter, depth + 1).map(x => divide(x, parse(ast.divisor), meter));
}

function operatingWork(artifact, registry) {
    if (artifact.kind === 'identity') return 0;
    const {n, ast} = artifact;
    if (artifact.kind === 'walsh') {
        return 2 * operatingWork(registry.get(ast.child), registry) + n
            + n / 2 * Number(ast.mix[0] === -1 && ast.mix[1] === -1)
            + n / 2 * Number(ast.mix[2] === -1 && ast.mix[3] === -1);
    }
    return (artifact.kind === 'xor-convolution' ? 3 : 2) * operatingWork(registry.get(ast.transform), registry) + 2 * n;
}

function certificateFor(artifact, registry, options) {
    const {n, kind, ast} = artifact;
    const ownWork = operatingWork(artifact, registry);
    need(artifact.operatingWork === ownWork, 'Declared operating-work bound differs from the executable grammar.');
    const scopeChecks = {arithmetic: 0, comparisons: 0};
    let scopeAccepted = true;
    if (kind === 'inverse') {
        const computed = directWalsh(ast.kernel.map(parse), scopeChecks);
        for (let i = 0; i < n; i++) {
            scopeChecks.comparisons++;
            if (!equal(computed[i], parse(ast.spectrum[i]))) scopeAccepted = false;
        }
    }
    const cases = [];
    let arithmetic = 0, comparisons = 0, matrixComparisons = 0;
    const linear = kind !== 'xor-convolution';
    for (let first = 0; first < n; first++) {
        for (let second = 0; second < (linear ? 1 : n); second++) {
            const meter = {arithmetic: 0};
            const inputs = linear ? [vector(n, first)] : [vector(n, first), vector(n, second)];
            const output = execute(artifact, registry, inputs, meter);
            need(meter.arithmetic === ownWork, 'Executable arithmetic disagrees with its structural bound.');
            let actual = output, expected;
            if (kind === 'identity' || kind === 'walsh') expected = Array.from({length: n}, (_, row) => character(row, first));
            else if (kind === 'xor-convolution') expected = vector(n, first ^ second);
            else {
                const kernel = ast.kernel.map(parse);
                actual = options.reference === 'inherited'
                    ? execute(registry.get(options.convolutionDigest), registry, [kernel, output], meter)
                    : directXor(kernel, output, meter);
                expected = vector(n, first);
            }
            let accepted = true;
            for (let i = 0; i < n; i++) {
                comparisons++;
                if (!equal(actual[i], expected[i])) accepted = false;
                if (kind === 'identity' || kind === 'walsh') {
                    matrixComparisons++;
                    if (!equal(output[i], parse(artifact.certificate.matrix[i][first]))) accepted = false;
                }
            }
            arithmetic += meter.arithmetic;
            cases.push({basis: linear ? [first] : [first, second], output: output.map(format),
                ...(kind === 'inverse' ? {composedOutput: actual.map(format)} : {}),
                accepted, arithmetic: meter.arithmetic, comparisons: n});
        }
    }
    return {accepted: scopeAccepted && cases.every(item => item.accepted),
        semantics: kind === 'xor-convolution' ? 'bilinear-over-rationals' : 'linear-over-rationals',
        basisCases: cases.length, arithmetic, comparisons, matrixComparisons,
        totalWork: arithmetic + comparisons + matrixComparisons, operatingWork: ownWork, cases, scopeChecks,
        reference: kind === 'inverse' ? options.reference : 'independent-direct-specification'};
}

async function context(artifactInput, envelopeInputs, optionsInput) {
    const captured = snapshot({artifact: artifactInput, envelopes: envelopeInputs, options: optionsInput});
    const artifact = shape(captured.artifact), options = exact(captured.options, [])
        ? {reference: 'direct'} : captured.options;
    need(Array.isArray(captured.envelopes) && captured.envelopes.length <= 8, 'At most eight dependency artifacts are admitted.');
    need(exact(options, ['reference']) || exact(options, ['reference', 'convolutionDigest']), 'Unsupported checker options.');
    need(options.reference === 'direct' || options.reference === 'inherited', 'Unknown inverse checking architecture.');
    const registry = new Map();
    for (const envelope of captured.envelopes) {
        need(exact(envelope, ['digest', 'artifact']) && typeof envelope.digest === 'string' && HASH.test(envelope.digest), 'Invalid dependency envelope.');
        const encoded = canonical(envelope.artifact);
        need(await digestCanonical(encoded) === envelope.digest, 'Dependency content hash mismatch.');
        need(!registry.has(envelope.digest), 'Duplicate dependency envelope.');
        registry.set(envelope.digest, shape(envelope.artifact));
    }
    const dependencyChecks = {qualifiedNow: [], reused: [], arithmetic: 0, comparisons: 0};
    const stack = new Set(), checkedHere = new Set();
    function ensure(hash) {
        need(registry.has(hash), 'Dependency bytes are missing.');
        need(!stack.has(hash), 'Cyclic dependency is not qualified.');
        stack.add(hash);
        const dependency = registry.get(hash);
        for (const child of dependency.dependencies) ensure(child);
        dimensions(dependency);
        if (checkedHere.has(hash)) {
            dependencyChecks.reused.push(hash); stack.delete(hash); return;
        }
        const receipt = certificateFor(dependency, registry, {reference: 'direct'});
        need(receipt.accepted, 'Dependency lacks a valid complete-domain certificate.');
        checkedHere.add(hash);
        dependencyChecks.qualifiedNow.push(hash);
        dependencyChecks.arithmetic += receipt.arithmetic + receipt.scopeChecks.arithmetic;
        dependencyChecks.comparisons += receipt.comparisons + receipt.matrixComparisons + receipt.scopeChecks.comparisons;
        stack.delete(hash);
    }
    function dimensions(item) {
        if (!item.dependencies.length) return;
        const dependency = registry.get(item.dependencies[0]);
        need(dependency && ['identity', 'walsh'].includes(dependency.kind), 'Arithmetic grammar requires a qualified transform.');
        need(dependency.n === (item.kind === 'walsh' ? item.n / 2 : item.n), 'Dependency dimension mismatch.');
    }
    for (const hash of artifact.dependencies) ensure(hash);
    dimensions(artifact);
    if (artifact.kind === 'inverse' && options.reference === 'inherited') {
        need(typeof options.convolutionDigest === 'string' && HASH.test(options.convolutionDigest),
            'Inherited inverse qualification requires a content-bound convolution.');
        ensure(options.convolutionDigest);
        const convolution = registry.get(options.convolutionDigest);
        need(convolution.kind === 'xor-convolution' && convolution.n === artifact.n
            && convolution.ast.transform === artifact.ast.transform, 'Inherited convolution context mismatch.');
    } else need(!Object.hasOwn(options, 'convolutionDigest'), 'Unused convolution context is not admitted.');
    return {artifact, registry, options, dependencyChecks};
}

export async function qualifyArtifact(artifactInput, dependencyEnvelopes = [], optionsInput = {reference: 'direct'}) {
    const prepared = await context(artifactInput, dependencyEnvelopes, optionsInput);
    const receipt = certificateFor(prepared.artifact, prepared.registry, prepared.options);
    return {...receipt, dependencyChecks: prepared.dependencyChecks,
        accountingScope: 'Arithmetic and comparisons; hashing, framing, allocation, bit complexity and authoring are unmeasured.'};
}

export async function interpretArtifact(artifactInput, dependencyEnvelopes, inputVectors) {
    const inputs = snapshot(inputVectors);
    const prepared = await context(artifactInput, dependencyEnvelopes, {reference: 'direct'});
    const {artifact, registry} = prepared;
    need(Array.isArray(inputs) && inputs.length === (artifact.kind === 'xor-convolution' ? 2 : 1),
        'Arithmetic input arity mismatch.');
    const receipt = certificateFor(artifact, registry, {reference: 'direct'});
    need(receipt.accepted, 'Unqualified artifact cannot be invoked.');
    const meter = {arithmetic: 0};
    const output = execute(artifact, registry, inputs.map(input => vectorInput(input, artifact.n)), meter);
    return {output: output.map(format), arithmetic: meter.arithmetic, qualificationWork: receipt.totalWork,
        dependencyChecks: prepared.dependencyChecks};
}

/** Actual invocation with independent present-source qualification and one owned public frame. */
export async function evaluateEnvelope(envelopeInput, registryInput, inputsInput) {
    const frame = snapshot({envelope: envelopeInput, registry: registryInput, inputs: inputsInput});
    need(exact(frame.envelope, ['digest', 'artifact']) && typeof frame.envelope.digest === 'string'
        && HASH.test(frame.envelope.digest), 'Invalid invocation envelope.');
    need(frame.envelope.digest === await hashArtifact(frame.envelope.artifact), 'Invocation content hash mismatch.');
    need(Array.isArray(frame.registry), 'Invocation dependencies must be an envelope array.');
    const seen = new Set();
    for (const item of frame.registry) {
        need(exact(item, ['digest', 'artifact']) && typeof item.digest === 'string' && HASH.test(item.digest)
            && !seen.has(item.digest), 'Invocation dependency inventory is invalid or duplicated.');
        seen.add(item.digest);
        if (item.digest === frame.envelope.digest) {
            need(canonical(item) === canonical(frame.envelope), 'Invocation inventory redefines the selected artifact.');
        }
    }
    const dependencies = frame.registry.filter(item => item.digest !== frame.envelope.digest);
    return interpretArtifact(frame.envelope.artifact, dependencies, frame.inputs);
}

/** Direct specification only; future expected outputs belong to the checker, after production. */
export function specificationApplication(kindInput, inputsInput, optionsInput = {}) {
    const frame = snapshot({kind: kindInput, inputs: inputsInput, options: optionsInput});
    need(Array.isArray(frame.inputs) && frame.inputs.length >= 1 && Array.isArray(frame.inputs[0]),
        'Specification input vectors required.');
    const {kind, options} = frame, n = frame.inputs[0].length;
    need(width(n) && exact(options, kind === 'inverse' ? ['kernel'] : []), 'Unsupported specification scope.');
    need(frame.inputs.length === (kind === 'xor-convolution' ? 2 : 1), 'Specification input arity mismatch.');
    const inputs = frame.inputs.map(input => vectorInput(input, n)), meter = {arithmetic: 0};
    let output;
    if (kind === 'walsh') output = directWalsh(inputs[0], meter);
    else if (kind === 'xor-convolution') output = directXor(inputs[0], inputs[1], meter);
    else if (kind === 'identity') { need(n === 1, 'Identity dimension mismatch.'); output = inputs[0]; }
    else if (kind === 'inverse') {
        const kernel = vectorInput(options.kernel, n);
        need(kernel.every((value, i) => equal(value, fraction(BigInt(i === 0 ? n + 1 : 1)))),
            'Independent closed-form application is scoped to kernel (n+1,1,...,1).');
        let sum = inputs[0][0];
        for (let i = 1; i < n; i++) sum = add(sum, inputs[0][i], meter);
        const offset = divide(sum, fraction(BigInt(2 * n * n)), meter);
        output = inputs[0].map(value => subtract(divide(value, fraction(BigInt(n)), meter), offset, meter));
    } else throw Error('Unknown specification interface.');
    return {output: output.map(format), arithmetic: meter.arithmetic,
        scope: 'Direct exact mathematical specification; separate from generated artifact execution.'};
}

function verificationProjection(receipt) {
    const fields = ['accepted', 'semantics', 'basisCases', 'arithmetic', 'comparisons', 'matrixComparisons',
        'totalWork', 'operatingWork', 'cases', 'scopeChecks', 'reference', 'dependencyChecks', 'accountingScope'];
    return Object.fromEntries(fields.map(key => [key, receipt[key]]));
}
const same = (left, right) => canonical(left) === canonical(right);
function retainedReceipt(record, receipt) {
    need(receipt.accepted && same(verificationProjection(record.verification), verificationProjection(receipt)),
        'Saved complete-domain certificate or selected work receipt differs from current replay.');
    need(record.work === receipt.totalWork && record.totalWork === record.constructionWork + receipt.totalWork,
        'Saved construction/qualification sum is inconsistent.');
}

function auditTransform(record, child, audit) {
    const {n, ast} = record.envelope.artifact;
    need(n === child.artifact.n * 2 && Array.isArray(record.attempts) && record.attempts.length === 64,
        'Every transform needs all sixty-four supplied candidates.');
    const measured = {specificationCells: 0, candidateRecords: 0, coefficientOperations: 0, coefficientComparisons: 0};
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { character(i, j); measured.specificationCells++; }
    let at = 0, selected = null;
    for (const inputLayout of ['halves', 'alternating']) for (const outputLayout of ['blocks', 'interleaving']) {
        for (let bits = 0; bits < 16; bits++) {
            const mix = Array.from({length: 4}, (_, i) => bits & (1 << i) ? -1 : 1);
            const candidateAst = {op: 'split-mix', child: child.digest, inputLayout, outputLayout, mix};
            let mismatches = 0, firstMismatch = null;
            const local = {coefficientOperations: 0, coefficientComparisons: 0};
            for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
                const rowPart = outputLayout === 'blocks' ? Math.floor(i / (n / 2)) : i % 2;
                const row = outputLayout === 'blocks' ? i % (n / 2) : Math.floor(i / 2);
                const colPart = inputLayout === 'halves' ? Math.floor(j / (n / 2)) : j % 2;
                const col = inputLayout === 'halves' ? j % (n / 2) : Math.floor(j / 2);
                const actual = format(multiply(fraction(BigInt(mix[rowPart * 2 + colPart])),
                    parse(child.artifact.certificate.matrix[row][col]), audit));
                const expected = format(character(i, j));
                local.coefficientOperations++; local.coefficientComparisons++; audit.comparisons++;
                if (actual !== expected) { mismatches++; firstMismatch ||= {row: i, column: j, actual, expected}; }
            }
            const expected = {index: at, ast: candidateAst, status: mismatches ? 'REJECTED' : 'MATCH',
                mismatches, firstMismatch, receipts: {candidateRecords: 1, ...local}};
            need(same(record.attempts[at], expected), 'A retained transform candidate or failure charge differs from replay.');
            if (!mismatches && !selected) selected = candidateAst;
            measured.candidateRecords++; measured.coefficientOperations += local.coefficientOperations;
            measured.coefficientComparisons += local.coefficientComparisons; at++;
        }
    }
    need(selected && same(ast, selected) && same(record.preparation, measured), 'Transform selection or preparation ledger differs.');
    need(record.constructionWork === Object.values(measured).reduce((a, b) => a + b, 0), 'Transform preparation total differs.');
    audit.specificationCells += measured.specificationCells;
    audit.candidateRecords += measured.candidateRecords;
}

function auditConvolution(record, registry, audit) {
    const {n, ast} = record.envelope.artifact;
    need(Array.isArray(record.attempts) && record.attempts.length === 4, 'Every signed normalization candidate must remain.');
    const measured = {candidateRecords: 0, arithmetic: 0, comparisons: 0};
    for (const [i, divisor] of [-n, -1, 1, n].entries()) {
        const candidateAst = {...ast, divisor: String(divisor)};
        const artifact = {...record.envelope.artifact, ast: candidateAst};
        const meter = {arithmetic: 0}, input = vector(n, 0);
        const output = execute(artifact, registry, [input, input], meter);
        let mismatches = 0;
        for (let j = 0; j < n; j++) { measured.comparisons++; audit.comparisons++; if (!equal(output[j], input[j])) mismatches++; }
        const expected = {ast: candidateAst, status: mismatches ? 'REJECTED' : 'ANCHOR_MATCH_NOT_CERTIFIED',
            inputs: [input.map(format), input.map(format)], output: output.map(format), mismatches,
            receipts: {candidateRecords: 1, arithmetic: meter.arithmetic, comparisons: n}};
        need(same(record.attempts[i], expected), 'A retained normalization attempt or failure charge differs from replay.');
        measured.candidateRecords++; measured.arithmetic += meter.arithmetic; audit.arithmetic += meter.arithmetic;
    }
    need(ast.divisor === String(n) && same(record.preparation, measured)
        && record.constructionWork === Object.values(measured).reduce((a, b) => a + b, 0),
    'Convolution selection or preparation work differs.');
    audit.candidateRecords += measured.candidateRecords;
}

function auditInverse(record, registry, audit) {
    const {n, ast} = record.envelope.artifact;
    const meter = {arithmetic: 0};
    const spectrum = execute(registry.get(ast.transform), registry, [ast.kernel.map(parse)], meter);
    need(spectrum.every(value => value.a !== 0n) && same(spectrum.map(format), ast.spectrum),
        'Inverse construction spectrum is singular or false.');
    const measured = {arithmetic: meter.arithmetic, comparisons: n};
    need(same(record.preparation, measured) && record.constructionWork === meter.arithmetic + n,
        'Inverse construction preparation ledger differs.');
    audit.arithmetic += meter.arithmetic; audit.comparisons += n;
}

function independentPlanCost(recipes, target, initial, bits) {
    const limit = 1 << bits, values = Array(limit).fill(Infinity);
    const order = Array.from({length: limit}, (_, i) => i).sort((a, b) => b.toString(2).replaceAll('0', '').length
        - a.toString(2).replaceAll('0', '').length || b - a);
    for (const stock of order) {
        if ((stock & target) === target) { values[stock] = 0; continue; }
        for (const recipe of recipes) {
            const next = stock | recipe.produces;
            if ((stock & recipe.requires) === recipe.requires && next !== stock) {
                values[stock] = Math.min(values[stock], recipe.charge + values[next]);
            }
        }
    }
    return values[initial];
}

function verifyPlanWitness(plan, recipes, initial, target, bits) {
    need(exact(plan, ['status', 'stock', 'cost', 'steps']) && plan.status === 'OPTIMAL'
        && Array.isArray(plan.steps) && plan.steps.length <= bits, 'Planner witness frame is invalid.');
    let stock = initial, cost = 0;
    for (const step of plan.steps) {
        need(exact(step, ['recipe', 'before', 'after', 'charge', 'cumulativeCharge']), 'Planner step frame differs.');
        const recipe = recipes.find(item => item.id === step.recipe);
        need(recipe && step.before === stock && (stock & recipe.requires) === recipe.requires,
            'Planner witness has an unavailable recipe.');
        const next = stock | recipe.produces; cost += recipe.charge;
        need(next !== stock && step.after === next && step.charge === recipe.charge && step.cumulativeCharge === cost,
            'Planner witness stock or paid charge differs.');
        stock = next;
    }
    need((stock & target) === target && plan.stock === stock && plan.cost === cost,
        'Planner witness does not attain the stated target and total.');
}

/** Replay every candidate, selected certificate, cost ledger and finite same-primitives optimum. */
export async function verifyBundle(bundleInput) {
    const bundle = snapshot(bundleInput);
    need(bundle.schema === 'autonomous-enterprise-foundry/v1' && bundle.reproduction === 'INDEPENDENT_REIMPLEMENTATION'
        && width(bundle.maxN) && bundle.maxN >= 2 && Array.isArray(bundle.envelopes)
        && bundle.envelopes.length <= 8 && bundle.totalCostComplete === false,
    'Unsupported bounded foundry bundle.');
    need(Array.isArray(bundle.transforms) && bundle.transforms.length === Math.log2(bundle.maxN), 'Incomplete transform chain.');
    need(bundle.transforms.every((record, i) => record.envelope.artifact.kind === 'walsh'
        && record.envelope.artifact.n === 2 ** (i + 1)) && bundle.convolution.envelope.artifact.kind === 'xor-convolution'
        && bundle.convolution.envelope.artifact.n === bundle.maxN
        && ['inverseDirect', 'inverseInherited'].every(key => bundle[key].envelope.artifact.kind === 'inverse'
            && bundle[key].envelope.artifact.n === bundle.maxN), 'Foundry stage kinds or dimensions differ from the declared chain.');
    const registry = new Map(), certificates = [], audit = {arithmetic: 0, comparisons: 0,
        specificationCells: 0, candidateRecords: 0};
    const observed = {constructorPreparation: 0, selectedQualifications: 0,
        additionalCurrentDependencyAndScopeChecks: 0, identityResearchAdmission: 0};
    for (const envelope of bundle.envelopes) {
        need(exact(envelope, ['digest', 'artifact']) && typeof envelope.digest === 'string'
            && envelope.digest === await hashArtifact(envelope.artifact) && !registry.has(envelope.digest),
        'Bundle artifact identity is invalid or duplicated.');
        registry.set(envelope.digest, shape(envelope.artifact));
    }
    const sequence = [bundle.identity, ...bundle.transforms, bundle.convolution, bundle.inverseDirect, bundle.inverseInherited];
    let predecessor = bundle.identity.envelope, transformChain = 0;
    for (let i = 0; i < sequence.length; i++) {
        const record = sequence[i], envelope = record.envelope;
        need(registry.has(envelope.digest) && same(registry.get(envelope.digest), envelope.artifact), 'Record artifact differs from bundle inventory.');
        const options = i === sequence.length - 1
            ? {reference: 'inherited', convolutionDigest: bundle.convolution.envelope.digest} : {reference: 'direct'};
        const dependencies = bundle.envelopes.filter(item => item.digest !== envelope.digest);
        const receipt = await qualifyArtifact(envelope.artifact, dependencies, options);
        need(receipt.accepted, 'Bundle selected artifact is not qualified.');
        if (i === 0) {
            need(envelope.artifact.kind === 'identity'
                && same(verificationProjection(record.verification), verificationProjection(receipt)), 'Identity certificate differs.');
            observed.identityResearchAdmission = receipt.totalWork + receipt.scopeChecks.arithmetic + receipt.scopeChecks.comparisons
                + receipt.dependencyChecks.arithmetic + receipt.dependencyChecks.comparisons;
        } else {
            retainedReceipt(record, receipt);
            observed.constructorPreparation += record.constructionWork;
            observed.selectedQualifications += receipt.totalWork;
            observed.additionalCurrentDependencyAndScopeChecks += receipt.scopeChecks.arithmetic + receipt.scopeChecks.comparisons
                + receipt.dependencyChecks.arithmetic + receipt.dependencyChecks.comparisons;
            if (envelope.artifact.kind === 'walsh') {
                auditTransform(record, predecessor, audit); predecessor = envelope; transformChain += record.totalWork;
            } else if (envelope.artifact.kind === 'xor-convolution') auditConvolution(record, registry, audit);
            else auditInverse(record, registry, audit);
        }
        audit.arithmetic += receipt.arithmetic + receipt.scopeChecks.arithmetic + receipt.dependencyChecks.arithmetic;
        audit.comparisons += receipt.comparisons + receipt.matrixComparisons + receipt.scopeChecks.comparisons
            + receipt.dependencyChecks.comparisons;
        certificates.push({digest: envelope.digest, receipt});
    }
    need(bundle.envelopes.length === bundle.transforms.length + 3
        && same(bundle.inverseDirect.envelope, bundle.inverseInherited.envelope), 'Foundry inventory closure differs.');
    const counts = {transformChain, incrementalConvolution: bundle.convolution.totalWork,
        inverseDirect: bundle.inverseDirect.totalWork, inverseInherited: bundle.inverseInherited.totalWork,
        inverseOnlyViaNewConvolution: bundle.convolution.totalWork + bundle.inverseInherited.totalWork,
        isolated: 3 * transformChain + bundle.convolution.totalWork + bundle.inverseDirect.totalWork,
        joint: transformChain + bundle.convolution.totalWork + bundle.inverseInherited.totalWork,
        operating: {transform: predecessor.artifact.operatingWork, convolution: bundle.convolution.envelope.artifact.operatingWork,
            inverse: bundle.inverseInherited.envelope.artifact.operatingWork}};
    const m = bundle.transforms.length, f = 1 << (m - 1), c = 1 << m, s = c << 1;
    const recipes = bundle.transforms.map((item, i) => ({id: `construct-F${item.envelope.artifact.n}`,
        requires: i === 0 ? 0 : 1 << (i - 1), produces: 1 << i, charge: item.totalWork}));
    recipes.push({id: 'construct-convolution', requires: f, produces: c, charge: counts.incrementalConvolution},
        {id: 'construct-inverse-direct', requires: f, produces: s, charge: counts.inverseDirect},
        {id: 'construct-inverse-inherited', requires: f | c, produces: s, charge: counts.inverseInherited});
    need(same(bundle.recipes, recipes), 'Planner charges differ from executed construction receipts.');
    counts.unrestrictedSamePrimitiveJointPlanner = independentPlanCost(recipes, f | c | s, 0, m + 2);
    const inverseOnly = independentPlanCost(recipes, s, (1 << m) - 1, m + 2);
    verifyPlanWitness(bundle.plans.joint, recipes, 0, f | c | s, m + 2);
    verifyPlanWitness(bundle.plans.inverseOnly, recipes, (1 << m) - 1, s, m + 2);
    need(same(bundle.counts, counts) && bundle.plans.joint.cost === counts.unrestrictedSamePrimitiveJointPlanner
        && bundle.plans.inverseOnly.cost === inverseOnly, 'Saved costs or planner optimum differ from independent dynamic programming.');
    need(bundle.controls.unrestrictedJoint.result === (counts.unrestrictedSamePrimitiveJointPlanner === counts.joint ? 'TIE' : 'DIFFERENT')
        && bundle.controls.unrestrictedJoint.cost === counts.unrestrictedSamePrimitiveJointPlanner,
    'Joint-planner comparison is inaccurately labeled.');
    need(bundle.controls.inverseOnly.selected === bundle.plans.inverseOnly.steps.at(-1).recipe
        && same(bundle.controls.inverseOnly.alternatives, [counts.inverseDirect, counts.inverseOnlyViaNewConvolution])
        && bundle.controls.inverseOnly.result === (counts.inverseOnlyViaNewConvolution > counts.inverseDirect
            ? 'DO_NOT_BUILD_CONVOLUTION_FOR_ONE_INVERSE' : 'TIE_OR_REVIEW'), 'Inverse-only control is inaccurately labeled.');
    observed.totalCountedCampaignWork = Object.values(observed).reduce((a, b) => a + b, 0);
    need(same(bundle.observedWorkLedger, observed), 'Observed complete campaign work ledger differs from replay.');
    return {verified: true, certificates, counts, arithmeticWork: audit.arithmetic, comparisonWork: audit.comparisons,
        specificationCells: audit.specificationCells, candidateRecords: audit.candidateRecords,
        currentReplayWork: Object.values(audit).reduce((a, b) => a + b, 0), observedWorkLedger: observed,
        scope: 'Independent implementation replay, not manuscript companion reproduction or institutional review.'};
}
