// SPDX-License-Identifier: Apache-2.0
/** Portable model-only executable packages. Import recomputes semantics and replay. */
import * as runtime from './typed-runtime.mjs';
import * as checker from './independent-checker.mjs';
import * as constructor from './constructor.mjs';

export const PACKAGE_SCHEMA = 'out-evolve-capability-package/v1';
const clone = value => JSON.parse(constructor.canonical(value));
const same = (a, b) => constructor.canonical(a) === constructor.canonical(b);
const fail = message => { throw new TypeError(message); };
const KEYS = ['schema', 'runtimeVersion', 'constructorVersion', 'apparatus', 'apparatusDigest', 'objectiveDigest',
    'catalogueDigest', 'ast', 'installations', 'executablePlan', 'interfaces', 'certificate', 'scope',
    'errorEnvelope', 'invalidationRules', 'replayFixtures', 'frozenEvidence', 'costLedger', 'search', 'parentAssets', 'digest'];
const INTERFACES = Object.freeze({prepare: 'out-evolve-prepare/v1', measure: 'out-evolve-measure/v1',
    qualify: 'out-evolve-independent-qualify/v1'});
const INVALIDATION = Object.freeze(['Runtime or schema change', 'Objective, tolerance or required scope change',
    'Apparatus channels, graph, primitive guards, effects, gains or resource bounds change',
    'Unmodeled coupling or disturbance exceeds supplied support envelope', 'Physical use requires separate qualification']);

export async function sha256(value) {
    const bytes = new TextEncoder().encode(typeof value === 'string' ? value : constructor.canonical(value));
    const result = await globalThis.crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(result)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

export async function digestCapability(input) {
    const {digest, ...body} = input;
    return sha256(body);
}

function objective(apparatus) {
    return {requiredProductiveGain: 1, scope: apparatus.scope, tolerance: apparatus.tolerance,
        usefulPurpose: 'Measure unchanged productive response with bounded recurring nuisance.'};
}
function catalogue(apparatus) {
    return {channels: apparatus.channels, edges: apparatus.edges, primitives: apparatus.primitives, limits: apparatus.limits};
}
function validCost(ledger) {
    const numeric = ['synthesis', 'unsuccessfulCandidates', 'tuning', 'installation', 'calibration',
        'qualification', 'operation', 'maintenance', 'total'];
    if (!ledger || ledger.unit !== 'abstract-model-work' || numeric.some(key =>
        !Number.isSafeInteger(ledger[key]) || ledger[key] < 0)) fail('Invalid complete cost ledger.');
    const sum = ['synthesis', 'tuning', 'installation', 'calibration', 'qualification', 'operation', 'maintenance']
        .reduce((total, key) => total + ledger[key], 0);
    if (sum !== ledger.total) fail('Cost ledger total mismatch.');
}

function frozenCost(result, fixtures, parent = null) {
    const ledger = clone(result.ledger);
    const replayCost = fixtures.reduce((sum, fixture) => sum + fixture.expected.cost, 0);
    const auditCost = result.ledger.synthesis + result.ledger.qualification;
    const checkingCost = 2 + fixtures.length + auditCost + (parent ? verificationCostCapability(parent) : 0);
    ledger.qualification += checkingCost;
    ledger.operation += replayCost;
    ledger.total += checkingCost + replayCost;
    return ledger;
}

export function verificationCostCapability(pkg) {
    const work = pkg.search.work;
    const semanticReplay = work.synthesis + work.qualification;
    const fixtureReplay = pkg.replayFixtures.reduce((total, fixture) => total + fixture.expected.cost + 1, 0);
    const parent = pkg.search.parentSource ?? pkg.search.checkpoint.inheritance.parent ?? null;
    return semanticReplay + 2 + fixtureReplay + (parent ? verificationCostCapability(parent) : 0);
}

function fixtureInputs(apparatus) {
    return apparatus.scope.flatMap(operation => [
        {signal: 7, options: {operation, cycle: 0, sign: 1}},
        {signal: -3, options: {operation, cycle: apparatus.limits.maxCycles - 1, sign: -1}}
    ]);
}

function parentAssets(apparatus, parent, inherited) {
    if (!parent) return {parentDigest: null, installations: [], observations: [], priorEvidence: 'none', ancestorCost: 0};
    const matching = inherited || parent.ast.installations;
    if (matching.some(id => !parent.ast.installations.includes(id))) fail('Cannot inherit unavailable installation.');
    for (const id of matching) {
        const before = parent.apparatus.primitives.find(item => item.id === id);
        const after = apparatus.primitives.find(item => item.id === id);
        if (!same(before, after)) fail('Incompatible inherited primitive.');
    }
    if (!same(parent.apparatus.channels, apparatus.channels) || !same(parent.apparatus.edges, apparatus.edges)
        || parent.apparatus.tolerance !== apparatus.tolerance) fail('Incompatible inherited apparatus support.');
    return {parentDigest: parent.digest, installations: [...matching], observations: [],
        priorEvidence: 'historical-only; new scope independently requalified',
        ancestorCost: constructor.lineageConstructionCost(parent)};
}

export async function freezeCapability(apparatus, result, {parent = null, inheritedAssets = null, evidence = null} = {}) {
    if (result.status !== 'qualified' || !result.program || !result.checkpoint) fail('Cannot freeze unfinished construction.');
    const checkpoint = constructor.importSearchCheckpoint(result.checkpoint);
    if (!same(checkpoint.apparatus, apparatus) || !same(checkpoint.result.program, result.program)) {
        fail('Search source or program changed before freeze.');
    }
    if (!same(result.ledger, constructor.advanceSearch(checkpoint, {steps: 0}).ledger)) fail('Search cost ledger changed.');
    const verifiedParent = parent ? await importCapability(parent) : null;
    if ((checkpoint.inheritance.parentDigest || null) !== (verifiedParent?.digest || null)) {
        fail('Parent inheritance differs from construction search.');
    }
    const ast = clone(result.program), report = runtime.qualify(apparatus, ast);
    const independent = checker.verify(apparatus, ast, report.certificate);
    if (!report.ok || !independent.ok) fail('Independent qualification failed before freeze.');
    const fixtures = fixtureInputs(apparatus).map(input => ({...input, expected: runtime.measure(apparatus, ast,
        input.signal, input.options)}));
    const costLedger = frozenCost(result, fixtures, verifiedParent);
    if (costLedger.total > checkpoint.options.maxCost) {
        fail('No qualifying construction found within budget: independent replay and package freeze qualification cost.');
    }
    const output = {schema: PACKAGE_SCHEMA, runtimeVersion: runtime.RUNTIME_VERSION,
        constructorVersion: constructor.CONSTRUCTOR_VERSION, apparatus: clone(apparatus),
        apparatusDigest: await sha256(apparatus), objectiveDigest: await sha256(objective(apparatus)),
        catalogueDigest: await sha256(catalogue(apparatus)), ast, installations: [...ast.installations],
        executablePlan: runtime.compile(apparatus, ast), interfaces: clone(INTERFACES), certificate: report.certificate,
        scope: [...ast.scope], errorEnvelope: clone(report.certificate.errors), invalidationRules: [...INVALIDATION],
        replayFixtures: fixtures, frozenEvidence: {status: 'supplied-model-qualified', physicalValidation: false,
            reuseStatus: 'not-yet-evaluated', externalReport: evidence === null ? null : clone(evidence)},
        costLedger, search: {schema: constructor.SEARCH_SCHEMA, limits: clone(checkpoint.options),
            expanded: checkpoint.expanded, generated: checkpoint.generated, work: clone(checkpoint.work),
            attempts: clone(result.attempts), frontier: clone(result.frontier)},
        parentAssets: parentAssets(apparatus, verifiedParent, inheritedAssets), digest: ''};
    output.search.checkpoint = constructor.compactSearchCheckpoint(checkpoint);
    output.search.parentSource = verifiedParent;
    if (!same(output.parentAssets.installations, checkpoint.inheritance.assets)) fail('Inherited asset selection changed.');
    output.digest = await digestCapability(output);
    return output;
}

export async function importCapability(input) {
    constructor.canonical(input);
    if (!input || Object.keys(input).length !== KEYS.length || !KEYS.every(key => Object.hasOwn(input, key))
        || input.schema !== PACKAGE_SCHEMA || input.runtimeVersion !== runtime.RUNTIME_VERSION
        || input.constructorVersion !== constructor.CONSTRUCTOR_VERSION) fail('Unsupported executable capability package.');
    const pkg = clone(input);
    if (pkg.digest !== await digestCapability(pkg) || pkg.apparatusDigest !== await sha256(pkg.apparatus)
        || pkg.objectiveDigest !== await sha256(objective(pkg.apparatus))
        || pkg.catalogueDigest !== await sha256(catalogue(pkg.apparatus))) fail('Package identity binding mismatch.');
    const report = runtime.qualify(pkg.apparatus, pkg.ast);
    const independent = checker.verify(pkg.apparatus, pkg.ast, pkg.certificate);
    if (!report.ok || !independent.ok || !same(report.certificate, pkg.certificate)
        || !same(runtime.compile(pkg.apparatus, pkg.ast), pkg.executablePlan)
        || !same(pkg.interfaces, INTERFACES) || !same(pkg.scope, pkg.ast.scope)
        || !same(pkg.installations, pkg.ast.installations) || !same(pkg.errorEnvelope, report.certificate.errors)
        || !same(pkg.invalidationRules, INVALIDATION)) fail('Package executable contract does not independently qualify.');
    if (!same(pkg.replayFixtures.map(({signal, options}) => ({signal, options})), fixtureInputs(pkg.apparatus))) {
        fail('Package replay coverage changed.');
    }
    for (const fixture of pkg.replayFixtures) {
        if (!same(runtime.measure(pkg.apparatus, pkg.ast, fixture.signal, fixture.options), fixture.expected)) {
            fail('Package replay fixture mismatch.');
        }
    }
    validCost(pkg.costLedger);
    if (!pkg.search || pkg.search.schema !== constructor.SEARCH_SCHEMA || !Array.isArray(pkg.search.attempts)
        || pkg.search.attempts.length !== pkg.search.expanded || pkg.costLedger.total > pkg.search.limits.maxCost
        || pkg.frozenEvidence.physicalValidation !== false || pkg.frozenEvidence.status !== 'supplied-model-qualified'
        || pkg.frozenEvidence.reuseStatus !== 'not-yet-evaluated') fail('Package evidence or search bounds changed.');
    const parentSource = pkg.search.parentSource ?? pkg.search.checkpoint.inheritance.parent ?? null;
    const verifiedParent = parentSource ? await importCapability(parentSource) : null;
    const checkpoint = constructor.importSearchCheckpoint(pkg.search.checkpoint, {parent: verifiedParent});
    const searchResult = constructor.advanceSearch(checkpoint, {steps: 0});
    if (searchResult.status !== 'qualified' || !same(checkpoint.apparatus, pkg.apparatus)
        || !same(searchResult.program, pkg.ast) || !same(checkpoint.options, pkg.search.limits)
        || checkpoint.expanded !== pkg.search.expanded || checkpoint.generated !== pkg.search.generated
        || !same(checkpoint.work, pkg.search.work) || !same(searchResult.attempts, pkg.search.attempts)
        || !same(searchResult.frontier, pkg.search.frontier)
        || !same(frozenCost(searchResult, pkg.replayFixtures, verifiedParent), pkg.costLedger)) {
        fail('Package search, failures or total costs do not reproduce.');
    }
    if (!pkg.parentAssets || !Array.isArray(pkg.parentAssets.installations)
        || !same(pkg.parentAssets.observations, []) || !Number.isSafeInteger(pkg.parentAssets.ancestorCost)
        || pkg.parentAssets.ancestorCost < 0 || pkg.parentAssets.installations.some(id => !pkg.ast.installations.includes(id))) {
        fail('Invalid compatibility-scoped parent assets.');
    }
    if (!same(parentAssets(pkg.apparatus, verifiedParent, checkpoint.inheritance.assets), pkg.parentAssets)) {
        fail('Parent compatibility or cumulative ancestor cost does not reproduce.');
    }
    return pkg;
}

export async function prepareCapability(input) {
    const pkg = await importCapability(input);
    return runtime.prepare(pkg.apparatus, pkg.ast);
}

export async function measureCapability(input, signal, options = {}) {
    const pkg = await importCapability(input);
    return runtime.measure(pkg.apparatus, pkg.ast, signal, options);
}

export async function qualifyCapability(input) {
    const pkg = await importCapability(input);
    return checker.verify(pkg.apparatus, pkg.ast, pkg.certificate);
}
