// SPDX-License-Identifier: Apache-2.0
/** Post-freeze synthetic evaluation. The constructor never receives response laws or final task truth. */
import { apparatus, expandApparatus, TOPOLOGIES } from './apparatus.mjs';
import { qualify, measure, prepare, compile, validateApparatus } from './typed-runtime.mjs';
import { verify } from './independent-checker.mjs';
import { construct } from './constructor.mjs';
import { freezeCapability, importCapability, digestCapability, verificationCostCapability } from './capability-package.mjs';

export const EVALUATION_VERSION = 'out-evolve-evaluation/v1';
export const LIMITATIONS = Object.freeze([
    'Finite synthetic apparatus only; no physical, scientific, commercial or general invention validation.',
    'Cases are generated after freezing. This public local evaluator is not a protected remote holdout.',
    'Constructor and classical baseline use identical deterministic uniform-cost planning semantics; ties are valid.',
    'Abstract model-work units are not currency, energy or measured wall-clock acceleration.'
]);

function canonical(value) {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
}
const clone = value => JSON.parse(canonical(value));
const ensure = (condition, message) => { if (!condition) throw Error(message); };
const sum = values => values.reduce((total, value) => total + value, 0);
function seedValue(seed) {
    if (seed === undefined) return globalThis.crypto.getRandomValues(new Uint32Array(1))[0];
    ensure(Number.isSafeInteger(seed) && seed >= 0 && seed <= 0xffffffff, 'Seed must be a uint32.');
    return seed;
}
function random(seed) {
    let state = seed >>> 0;
    return maximum => {
        state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
        return state % maximum;
    };
}
async function hash(value) {
    const bytes = new TextEncoder().encode(canonical(value));
    const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}
function exposure(id, exposed) {
    return exposed.has(id) ? 'previously-exposed-regression' : 'generated-after-freeze-public-model';
}
function outcome(cases) {
    if (cases.some(test => test.status === 'FAIL')) return 'FAIL';
    if (cases.some(test => test.status !== 'PASS')) return 'INCONCLUSIVE';
    return cases.length ? 'PASS' : 'INCONCLUSIVE';
}

/** Freeze identity before generating tasks, and use the same package bytes for every purpose. */
export async function evaluateFrozenReuse(input, options = {}) {
    const pkg = await importCapability(input);
    const frozenBytes = canonical(pkg);
    const frozenDigest = await digestCapability(pkg);
    const seed = seedValue(options.seed);
    const rng = random(seed);
    const exposed = new Set(options.exposedCaseIds || []);
    ensure(exposed.size <= 4096, 'Too many exposed evaluation cases.');
    const coefficients = [rng(11) - 5, 4 + rng(4), 1 + rng(3)];
    // This closure exists only after package freeze and is never supplied to synthesis.
    const truth = (x, operation = 'standard') => coefficients[0] + coefficients[1] * x
        + coefficients[2] * x * x + (operation === 'reservoir' ? 17 + 3 * x : 0);
    const scope = pkg.ast.scope;
    const operations = scope.includes('reservoir') ? ['standard', 'reservoir'] : ['standard'];
    const qualification = verify(pkg.apparatus, pkg.ast, pkg.certificate);
    const measurements = [];
    let runtimeCost = 0;
    let preservation = true;
    for (const operation of operations) {
        for (let cycle = 0; cycle < 3; cycle++) {
            for (let x = 0; x < 8; x++) {
                const signal = truth(x, operation);
                const reading = measure(pkg.apparatus, pkg.ast, signal,
                    {cycle, sign: rng(2) ? 1 : -1, operation});
                runtimeCost += reading.cost;
                const valid = Number.isFinite(reading.value) && Math.abs(reading.value - signal)
                    <= pkg.certificate.errorBound + 1e-10;
                preservation = preservation && reading.productive === signal;
                measurements.push({operation, cycle, x, expected: signal, actual: reading.value,
                    error: reading.value - signal, valid, productive: reading.productive});
            }
        }
    }
    const cases = [];
    for (const operation of operations) {
        const rows = measurements.filter(row => row.operation === operation && row.cycle === 2);
        const threshold = (truth(3, operation) + truth(4, operation)) / 2;
        const thresholdExpected = rows.filter(row => row.expected >= threshold).map(row => row.x);
        const thresholdActual = rows.filter(row => row.actual >= threshold).map(row => row.x);
        const target = truth(2 + rng(4), operation);
        const nearest = field => rows.toSorted((a, b) => Math.abs(a[field] - target)
            - Math.abs(b[field] - target) || a.x - b.x)[0].x;
        const maximum = 3 + rng(4);
        const best = field => rows.filter(row => row.x <= maximum)
            .toSorted((a, b) => b[field] - a[field] || a.x - b.x)[0].x;
        for (const [kind, expected, actual, task] of [
            ['threshold-screening', thresholdExpected, thresholdActual, {threshold}],
            ['inverse-design', nearest('expected'), nearest('actual'), {target}],
            ['constrained-selection', best('expected'), best('actual'), {maximumInput: maximum}]
        ]) {
            const id = await hash({seed, operation, kind, task, truthCoefficients: coefficients});
            const sound = measurements.filter(row => row.operation === operation).every(row => row.valid)
                && preservation && qualification.ok;
            cases.push({id, kind, operation, task, expected, actual,
                status: sound && canonical(expected) === canonical(actual) ? 'PASS' : 'FAIL',
                exposure: exposure(id, exposed)});
            exposed.add(id);
        }
    }
    const digestAfter = await digestCapability(pkg);
    ensure(canonical(pkg) === frozenBytes && frozenDigest === digestAfter, 'Frozen package changed during reuse.');
    return {schema: EVALUATION_VERSION, kind: 'frozen-package-reuse', status: outcome(cases),
        freeze: {packageDigest: frozenDigest, order: 'package-frozen-before-seed-and-case-generation'},
        packageDigestBefore: frozenDigest, packageDigestAfter: digestAfter, seed, cases, measurements,
        qualification, preservation, exposedCaseIds: [...exposed],
        ledger: {unit: 'abstract-model-work', tasks: cases.length, measurementCalls: measurements.length,
            qualification: verificationCostCapability(pkg) + 1 + cases.length,
            operation: runtimeCost, maintenance: 0,
            total: verificationCostCapability(pkg) + 1 + cases.length + runtimeCost},
        limitations: [...LIMITATIONS]};
}

function ledgerTotal(ledger) {
    ensure(ledger && Number.isFinite(ledger.total) && ledger.total >= 0, 'Invalid evaluated cost ledger.');
    return ledger.total;
}

/** The same objective, tolerance, graph, primitive information and budget apply to both planning runs. */
export async function compareCapability(input, options = {}) {
    const pkg = await importCapability(input);
    const searchOptions = {...pkg.search.limits};
    if (options.searchOptions) ensure(Object.entries(options.searchOptions).every(([key, value]) =>
        Object.hasOwn(searchOptions, key) && canonical(value) === canonical(searchOptions[key])),
        'Comparison must use the effective construction limits recorded in the frozen package.');
    const classical = construct(pkg.apparatus, searchOptions);
    const scratch = construct(pkg.apparatus, {...searchOptions});
    const classicalPackage = classical.status === 'qualified' ? await freezeCapability(pkg.apparatus, classical) : null;
    const scratchPackage = scratch.status === 'qualified' ? await freezeCapability(pkg.apparatus, scratch) : null;
    const remaining = ledgerTotal(pkg.costLedger);
    const ancestor = pkg.parentAssets.ancestorCost;
    const ours = ancestor + remaining;
    const runs = [
        {name: 'constructed-package', status: 'qualified', ast: pkg.ast, certificate: pkg.certificate,
            ledger: pkg.costLedger},
        {name: 'classical-uniform-cost-planner', status: classical.status, ast: classical.program,
            certificate: classical.certificate, ledger: classicalPackage?.costLedger || classical.ledger,
            method: 'Classical uniform-cost planning with the same sound semantic deduplication; it may tie or win.'},
        {name: 'construction-from-scratch', status: scratch.status, ast: scratch.program,
            certificate: scratch.certificate, ledger: scratchPackage?.costLedger || scratch.ledger}
    ];
    const sensing = await sensingCorrectionBaseline(pkg, searchOptions);
    const uses = options.uses === undefined ? 24 : options.uses;
    ensure(Number.isSafeInteger(uses) && uses > 0 && uses <= 10000, 'Invalid amortization horizon.');
    const compiled = compile(pkg.apparatus, pkg.ast);
    const operation = 1 + compiled.steps.reduce((total, key) => total
        + pkg.apparatus.primitives.find(primitive => primitive.id === key).cost, 0);
    const classicalCost = classicalPackage ? ledgerTotal(classicalPackage.costLedger) : null;
    const relation = classical.status !== 'qualified' ? 'baseline-inconclusive'
        : ours < classicalCost ? 'lower-total-modeled-cost'
            : ours === classicalCost ? 'tie' : 'classical-baseline-lower-total-modeled-cost';
    return {schema: EVALUATION_VERSION, kind: 'matched-comparison', status: 'COMPLETED',
        frozenPackageDigest: pkg.digest, matched: {apparatus: true, objective: true, tolerance: true,
            primitives: true, information: true, budgets: searchOptions}, runs, sensingCorrection: sensing,
        relation, costs: {unit: 'abstract-model-work', coldStart: ours, remainingConstructionCost: remaining, ancestorConstructionCost: ancestor,
            operationPerUse: operation, uses, totalAtHorizon: ours + uses * operation,
            amortizedPerUse: ours / uses + operation},
        evaluationOverhead: {qualification: verificationCostCapability(pkg), total: verificationCostCapability(pkg),
            unit: 'abstract-model-work', reason: 'Verified import of the candidate used for this comparison.'},
        limitations: [...LIMITATIONS, 'Planner total includes abstract synthesis effort; no novel planning superiority is claimed.']};
}

/** Strong bounded sensing comparator: install any supplied sensors and use all admissible paired references. */
export async function sensingCorrectionBaseline(pkg, searchOptions = {}) {
    const app = pkg.apparatus;
    const maximum = searchOptions.maxProgramSize || 8;
    const budget = searchOptions.maxCost || app.limits.maxCost;
    const sensors = app.primitives.filter(primitive => primitive.kind === 'sensor');
    const references = app.primitives.filter(primitive => primitive.kind === 'reference');
    const maximumSubsets = Math.min(2 ** sensors.length, searchOptions.maxStates || 4096);
    let best = null;
    let tested = 0;
    let failed = 0;
    let simulationWork = 0;
    for (let mask = 0; mask < maximumSubsets; mask++) {
        const installations = sensors.filter((_, index) => mask & 2 ** index).map(primitive => primitive.id);
        const refs = references.filter(primitive => primitive.requires.every(key => installations.includes(key)));
        if (installations.length + refs.length > maximum) continue;
        simulationWork += 1 + installations.length + refs.length;
        const ast = {schema: 'out-evolve-ast/v1', installations,
            prepare: {op: 'sequence', steps: refs.map(primitive => ({op: 'primitive', id: primitive.id}))},
            scope: [...pkg.ast.scope]};
        try {
            const report = qualify(app, ast);
            tested++;
            if (!report.ok || report.cost > budget) failed++;
            if (report.cost > budget) continue;
            if (!best || report.ok && !best.ok || report.ok === best.ok && (report.errorBound < best.errorBound
                || report.errorBound === best.errorBound && report.cost < best.cost)) best = {...report, ast};
        } catch { tested++; failed++; }
    }
    const independent = best ? verify(app, best.ast, best.certificate) : null;
    const replay = best?.ok ? app.scope.flatMap(operation => [
        {signal: 7, options: {operation, cycle: 0, sign: 1}},
        {signal: -3, options: {operation, cycle: app.limits.maxCycles - 1, sign: -1}}
    ]).map(input => ({...input, actual: measure(app, best.ast, input.signal, input.options)})) : [];
    const operationCost = replay.reduce((total, fixture) => total + fixture.actual.cost, 0);
    const qualificationCost = tested + (best ? 1 : 0) + replay.length;
    const installations = best?.ast.installations || [];
    const installCost = installations.reduce((total, key) => total
        + app.primitives.find(primitive => primitive.id === key).cost, 0);
    return {name: 'competent-sensing-and-paired-reference-correction',
        status: best?.ok ? 'qualified' : 'not-qualified-within-supplied-sensing-language',
        best, tested, independent, replay, constructionChanges: installations.length > 0,
        experimentalAccessChange: installations.length ? 'additional nuisance sensor access; no nuisance routing or suppression'
            : 'unchanged sensor access',
        matched: {graph: true, information: true, tolerance: true, maxProgramSize: maximum, maxCost: budget},
        reason: 'Enumerates all sensor subsets within the budget and every admissible simultaneous reference; repeated references add no information in this model.',
        ledger: {unit: 'abstract-model-work', synthesis: simulationWork, unsuccessfulCandidates: failed,
            qualification: qualificationCost, installation: installCost, calibration: (best?.cost || 0) - installCost,
            tuning: 0, operation: operationCost, maintenance: 0,
            total: simulationWork + qualificationCost + (best?.cost || 0) + operationCost},
        limitation: 'Where the supplied catalogue lacks a required sensor, this bounded comparator cannot identify unobserved independent nuisance. This is not a universal sensing impossibility proof.'};
}

/** Freeze implementation identity/configuration first, then generate unseen public structural variants. */
export async function evaluateConstructorGeneralization(options = {}) {
    const searchOptions = {...options.searchOptions};
    ensure(typeof options.constructorDigest === 'string' && /^[0-9a-f]{64}$/.test(options.constructorDigest),
        'Provide the verified full constructor/runtime/checker source-closure SHA-256 before final family generation.');
    const identity = options.constructorDigest;
    const freeze = Object.freeze({constructorDigest: identity, configuration: clone(searchOptions)});
    const seed = seedValue(options.seed);
    const rng = random(seed);
    const exposed = new Set(options.exposedCaseIds || []);
    const cases = [];
    for (const topology of TOPOLOGIES) {
        const app = apparatus(topology, false);
        const variant = structuralVariant(app, rng);
        const structuralWorld = clone(variant);
        delete structuralWorld.id;
        const id = await hash({seed, structuralWorld});
        const obstruction = proveRecurringObstruction(variant);
        const result = obstruction ? {status: 'infeasible', program: null, certificate: null,
            reason: 'Independent zero-tolerance recurring-channel obstruction proves infeasibility in the supplied model.',
            proof: obstruction, ledger: {unit: 'abstract-model-work', synthesis: 0, unsuccessfulCandidates: 0,
                tuning: 0, installation: 0, calibration: 0, qualification: 1, operation: 0, maintenance: 0, total: 1}}
            : construct(variant, searchOptions);
        let pkg = null;
        let reuse = null;
        if (result.status === 'qualified') {
            pkg = await freezeCapability(variant, result);
            reuse = await evaluateFrozenReuse(pkg, {seed: rng(0xffffffff), exposedCaseIds: [...exposed]});
            for (const used of reuse.exposedCaseIds) exposed.add(used);
        }
        cases.push({id, topology, structuralFamily: variant.family || variant.id || topology,
            exposure: exposure(id, exposed), status: obstruction ? 'PASS' : pkg && reuse.status === 'PASS' ? 'PASS'
                : result.status === 'qualified' ? 'FAIL' : 'INCONCLUSIVE',
            constructionStatus: obstruction ? 'proved-infeasible-no-construction' : result.status,
            acceptedOutcome: obstruction ? 'independently-proved-negative-case' : pkg ? 'constructed-and-reused' : 'unfinished',
            constructorCalled: !obstruction, obstruction,
            result, package: pkg, reuse, publicApparatus: variant});
        exposed.add(id);
    }
    return {schema: EVALUATION_VERSION, kind: 'constructor-generalization', status: outcome(cases),
        freeze, order: 'constructor-frozen-before-structural-case-generation', seed, cases,
        constructedFamilies: cases.filter(test => test.package).length,
        provedInfeasibleFamilies: cases.filter(test => test.obstruction).length,
        exposedCaseIds: [...exposed], limitations: [...LIMITATIONS,
            'Structural variants belong to this supplied finite model; this does not establish cross-domain generalization.']};
}

/** Independent necessary-condition proof; it assumes every available route can be installed. */
export function proveRecurringObstruction(app) {
    app = validateApparatus(app);
    if (app.tolerance !== 0) return null;
    const removed = new Set(app.primitives.filter(primitive => primitive.kind === 'route').map(primitive => primitive.target));
    const weights = new Map([['readout', 1]]);
    const weight = key => {
        if (!weights.has(key)) weights.set(key, app.edges.filter(edge => edge.from === key && !removed.has(edge.id))
            .reduce((total, edge) => total + edge.gain * weight(edge.to), 0));
        return weights.get(key);
    };
    for (const channel of app.channels) {
        const operation = app.scope.find(scope => channel.scopes.includes(scope));
        if (!operation || channel.drift === 0 || weight(channel.id) === 0) continue;
        if (app.primitives.some(primitive => primitive.target === channel.id
            && ['shield', 'reference'].includes(primitive.kind))) continue;
        return {schema: 'out-evolve-recurring-obstruction/v1', modelOnly: true, channel: channel.id,
            operation, recurringDisturbance: channel.drift, pathGainAfterEveryAvailableRoute: weight(channel.id),
            strictLowerBound: channel.drift * weight(channel.id), tolerance: 0,
            reasoning: 'A positive recurring source still reaches readout after all possible routes; no shield or paired reference targets it. Attenuation cannot remove disturbance injected after preparation, and destructive shortcuts violate productive preservation.'};
    }
    return null;
}

function structuralVariant(input, rng) {
    const app = clone(input);
    const suffix = rng(0x1000000).toString(16);
    app.id = app.id + '-post-freeze-' + suffix;
    const productive = app.channels.filter(channel => channel.id !== 'reservoir');
    const source = productive[rng(productive.length)];
    const relayId = 'relay-' + suffix;
    // Split a randomly selected live outgoing edge through a new state channel: a genuinely new graph.
    const outgoing = app.edges.filter(edge => edge.from === source.id);
    const edge = outgoing[rng(outgoing.length)];
    if (edge) {
        const originalTarget = edge.to;
        edge.to = relayId;
        app.channels.push({id: relayId, initial: 3 + rng(5), drift: 1 + rng(3), cap: 16,
            scopes: ['standard', 'reservoir']});
        app.edges.push({id: relayId + '-link', from: relayId, to: originalTarget, gain: 1});
        const protection = clone(app.primitives.find(primitive => primitive.kind === 'shield'));
        protection.id = 'protect-' + relayId; protection.target = relayId; protection.cost = 2 + rng(4);
        const attenuation = clone(app.primitives.find(primitive => primitive.kind === 'attenuate' && primitive.gain === 0));
        attenuation.id = 'flush-' + relayId; attenuation.target = relayId; attenuation.cost = 1 + rng(2);
        app.primitives.push(protection, attenuation);
    }
    // Costs and recurrence parameters vary only within the declared public contract. No truth law is supplied.
    source.initial = Math.min(source.cap, source.initial + rng(4));
    source.drift = Math.min(source.cap, source.drift + rng(3));
    for (const primitive of app.primitives) primitive.cost += rng(3);
    return app;
}

function semanticBehavior(app, ast) {
    const state = prepare(app, ast);
    const catalogue = new Map(app.primitives.map(primitive => [primitive.id, primitive]));
    const interventions = state.installed.map(key => catalogue.get(key))
        .filter(primitive => ['shield', 'route', 'sensor'].includes(primitive.kind))
        .map(primitive => ({kind: primitive.kind, target: primitive.target}));
    return canonical({interventions, transfer: state.transfer, references: state.references,
        recurrence: qualify(app, ast).certificate.recurrence});
}

/** Retain the old scope failure; inherit only independently checked compatible installed modules. */
export async function buildSuccessor(input, options = {}) {
    const parent = await importCapability(input);
    const expanded = expandApparatus(parent.apparatus);
    const diagnosticAST = clone(parent.ast);
    diagnosticAST.scope = [...expanded.scope];
    const diagnosticEnvelope = qualify(expanded, diagnosticAST);
    const diagnosticVerification = verify(expanded, diagnosticAST, diagnosticEnvelope.certificate);
    const diagnosticMeasurement = measure(expanded, diagnosticAST, 17,
        {operation: 'reservoir', cycle: expanded.limits.maxCycles - 1, sign: 1});
    const oldScopeAuditCost = 3 + diagnosticMeasurement.cost;
    let oldScope;
    try {
        const report = qualify(expanded, parent.ast);
        oldScope = {status: report.ok ? 'UNEXPECTED-PASS' : 'FAIL', report,
            reason: 'Original package was not qualified for the reservoir-exposing productive operation.'};
    } catch (error) {
        oldScope = {status: 'FAIL', reason: String(error.message)};
    }
    oldScope.diagnostic = {frozenPackageUnchanged: true, prospectiveScopeOnlyAdaptation: true,
        requiredScope: expanded.scope, envelope: diagnosticEnvelope, independent: diagnosticVerification,
        reservoirMeasurement: {expected: 17, ...diagnosticMeasurement},
        explanation: 'Replaying the old plan under the newly required operation exposes recurring reservoir contamination.'};
    const searchOptions = {...options.searchOptions};
    const result = construct(expanded, {...searchOptions, parent});
    const scratch = construct(expanded, searchOptions);
    if (result.status !== 'qualified') {
        return {schema: EVALUATION_VERSION, kind: 'scope-expanding-successor', status: 'INCONCLUSIVE',
            oldScope, result, scratch, parentDigest: parent.digest,
            costs: {unit: 'abstract-model-work', ancestor: ledgerTotal(parent.costLedger),
                remaining: ledgerTotal(result.ledger) + verificationCostCapability(parent) + oldScopeAuditCost,
                cumulative: ledgerTotal(parent.costLedger) + ledgerTotal(result.ledger)
                    + verificationCostCapability(parent) + oldScopeAuditCost,
                constructionFromScratch: ledgerTotal(scratch.ledger)},
            reason: 'No qualifying construction found within budget.', limitations: [...LIMITATIONS]};
    }
    const pkg = await freezeCapability(expanded, result, {parent});
    const reuse = await evaluateFrozenReuse(pkg, options);
    const prior = reuse.cases.filter(test => test.operation === 'standard');
    const added = reuse.cases.filter(test => test.operation === 'reservoir');
    const preserved = prior.length === 3 && prior.every(test => test.status === 'PASS');
    const newFunction = added.length === 3 && added.every(test => test.status === 'PASS');
    const parentCost = ledgerTotal(parent.costLedger);
    const parentAudit = verificationCostCapability(parent);
    const remaining = ledgerTotal(pkg.costLedger) + parentAudit + oldScopeAuditCost;
    const scratchPackage = scratch.status === 'qualified' ? await freezeCapability(expanded, scratch) : null;
    const scratchCost = scratchPackage ? ledgerTotal(scratchPackage.costLedger) : null;
    const scratchReuse = scratchPackage ? await evaluateFrozenReuse(scratchPackage, options) : null;
    return {schema: EVALUATION_VERSION, kind: 'scope-expanding-successor',
        status: oldScope.status === 'FAIL' && preserved && newFunction ? 'PASS' : 'FAIL',
        oldScope, parentDigest: parent.digest, package: pkg, result, scratch, reuse, scratchReuse,
        inheritedAssets: pkg.parentAssets, invalidated: ['parent scope certificate', 'prior observations as fresh evidence'],
        obligations: {preserved, standardCases: prior},
        newFunction: {accepted: newFunction, operation: 'reservoir', cases: added,
            description: 'Operate the reservoir-exposing productive mode while retaining the earlier measurement obligations.'},
        costs: {unit: 'abstract-model-work', ancestor: parentCost, remaining, cumulative: parentCost + remaining,
            packageConstruction: ledgerTotal(pkg.costLedger), parentImportAudit: parentAudit, oldScopeCheck: oldScopeAuditCost,
            frozenReuseAcceptance: reuse.ledger.total,
            remainingAfterAcceptance: remaining + reuse.ledger.total,
            cumulativeAfterAcceptance: parentCost + remaining + reuse.ledger.total,
            scratchAfterAcceptance: scratchCost === null ? null : scratchCost + scratchReuse.ledger.total,
            constructionFromScratch: scratchCost, remainingSaving: scratchCost === null ? null : scratchCost - remaining,
            cumulativeSaving: scratchCost === null ? null : scratchCost - parentCost - remaining},
        limitations: [...LIMITATIONS, 'Inherited installations do not make ancestor construction cost disappear.']};
}

/** Complete synthetic vertical, retaining all topology, reuse, baseline and succession evidence. */
export async function runEvaluation(options = {}) {
    const seed = seedValue(options.seed);
    const exposed = new Set(options.exposedCaseIds || []);
    const topologies = [];
    for (let index = 0; index < TOPOLOGIES.length; index++) {
        const topology = TOPOLOGIES[index];
        const app = apparatus(topology);
        const result = construct(app, options.searchOptions || {});
        if (result.status !== 'qualified') {
            topologies.push({topology, status: 'INCONCLUSIVE', result});
            continue;
        }
        const pkg = await freezeCapability(app, result);
        const reuse = await evaluateFrozenReuse(pkg, {seed: (seed + index) >>> 0, exposedCaseIds: [...exposed]});
        for (const id of reuse.exposedCaseIds) exposed.add(id);
        const comparison = await compareCapability(pkg, options);
        topologies.push({topology, status: reuse.status, package: pkg, result, reuse, comparison});
    }
    const parent = topologies.find(test => test.package)?.package;
    const successor = parent ? await buildSuccessor(parent, {...options, seed: (seed + 10) >>> 0, exposedCaseIds: [...exposed]}) : null;
    if (successor?.reuse) for (const id of successor.reuse.exposedCaseIds) exposed.add(id);
    const generalization = await evaluateConstructorGeneralization({...options, seed: (seed + 20) >>> 0,
        exposedCaseIds: [...exposed]});
    for (const id of generalization.exposedCaseIds) exposed.add(id);
    const asts = new Set(topologies.filter(test => test.package).map(test =>
        semanticBehavior(test.package.apparatus, test.package.ast)));
    const topologyCosts = topologies.map(test => test.package ? ledgerTotal(test.package.costLedger)
        + test.reuse.ledger.total + test.comparison.evaluationOverhead.total
        + ledgerTotal(test.comparison.runs[1].ledger) + ledgerTotal(test.comparison.runs[2].ledger)
        + test.comparison.sensingCorrection.ledger.total : ledgerTotal(test.result.ledger));
    const familyCosts = generalization.cases.map(test => test.package ? ledgerTotal(test.package.costLedger)
        + test.reuse.ledger.total : ledgerTotal(test.result.ledger));
    const successorCost = successor?.package ? successor.costs.remainingAfterAcceptance
        + successor.costs.scratchAfterAcceptance : successor ? successor.costs.remaining
            + successor.costs.constructionFromScratch : 0;
    const aggregateCost = sum(topologyCosts) + sum(familyCosts) + successorCost;
    return {schema: EVALUATION_VERSION, seed, status: topologies.every(test => test.status === 'PASS')
        && successor?.status === 'PASS' && generalization.status === 'PASS' && asts.size >= 3 ? 'PASS' : 'INCONCLUSIVE',
        topologies, behaviorallyDistinctPrograms: asts.size, successor, generalization,
        acceptanceScope: 'finite-synthetic-machinery-with-explicit-positive-and-negative-tests',
        allGeneratedFamiliesConstructed: generalization.constructedFamilies === generalization.cases.length,
        constructionOutcomes: {qualified: generalization.constructedFamilies,
            provedInfeasible: generalization.provedInfeasibleFamilies,
            unfinished: generalization.cases.filter(test => test.status !== 'PASS').length},
        exposedCaseIds: [...exposed],
        aggregateCost, costAccounting: {unit: 'abstract-model-work', topologyJourneys: topologyCosts,
            unseenFamilies: familyCosts, successorAndMatchedColdStart: successorCost, total: aggregateCost,
            schedule: 'Includes each construction/freeze audit, verified import, independent decision check, measurement and comparison actually invoked; failed-candidate counts are included in synthesis, not added twice.',
            excludes: 'Host CPU, serialization, file I/O and money; this ledger is an explicit model-work schedule.'},
        limitations: [...LIMITATIONS]};
}
