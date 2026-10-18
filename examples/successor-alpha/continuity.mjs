// SPDX-License-Identifier: Apache-2.0
/** Installed native workbench adapter. Imported files never supply executable code. */
import { canonical, digest, parseBounded } from '../../docs/assets/successor/engine.mjs';
import { createWorkbench } from '../successor-workbench/engine.mjs';
import * as catalog from './engine.mjs';
import { inspectProject, serializeProject } from './project.mjs';

export const HANDOFF_SCHEMA = 'successor-alpha-native-handoff/v1';
export const RETURN_SCHEMA = 'successor-alpha-native-return/v1';
export const CONTINUITY_SCHEMA = 'successor-alpha-native-continuity/v1';
export const LIMITS = Object.freeze({ bytes: 2_000_000, returns: 8, snapshots: 8 });
export const COMPATIBILITY = Object.freeze({
    workbench: 'installed-catalog-adapter', jobs: 'native-compiler-unfunded-AGIALPHA',
    manager: 'catalog-executor-not-installed', fleet: 'catalog-executor-not-installed',
});
const encoder = new TextEncoder();
const clone = value => parseBounded(canonical(value));
const same = (left, right) => canonical(left) === canonical(right);
const scope = Object.freeze({ authority: 'none', qualification: 'not_independently_qualified',
    settlement: 'not-connected' });
const limits = Object.freeze([
    'Exact catalog output is independently recomputed; local timings remain historical observations.',
    'Installed deterministic code only; no model, live provider, wallet or external request.',
    'Native Jobs compilation is an unfunded AGIALPHA draft; no Manager or Fleet catalog executor is installed.',
    'Protected evaluation, independent review, production admission and realized economic advantage remain unestablished.',
]);
const artifacts = Object.freeze({ joinedCsv: 'joined.csv', unmatchedLeftCsv: 'unmatched-left.csv',
    unmatchedRightCsv: 'unmatched-right.csv', conflictsCsv: 'conflicts.csv', exactJson: 'exact-result.json' });
function fail(ok, code) { if (!ok) throw Error('ALPHA_CONTINUITY_' + code); }
function fields(value, names) {
    fail(value && typeof value === 'object' && !Array.isArray(value)
        && Object.keys(value).sort().join('|') === [...names].sort().join('|'), 'FIELDS');
}
function hash(value) { fail(typeof value === 'string' && /^[0-9a-f]{64}$/.test(value), 'SOURCE_HASH'); }
function bounded(raw) {
    fail(typeof raw === 'string' && encoder.encode(raw).length <= LIMITS.bytes, 'CAPACITY');
    return parseBounded(raw);
}
function integer(value, maximum) {
    fail(Number.isSafeInteger(value) && !Object.is(value, -0) && value >= 0 && value <= maximum, 'INTEGER');
}
export async function exactDigest(raw) {
    fail(typeof raw === 'string', 'BYTES');
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(raw))),
        value => value.toString(16).padStart(2, '0')).join('');
}
async function seal(body) {
    const raw = canonical({ ...body, sha256: await exactDigest(canonical(body)) });
    bounded(raw); return raw;
}
async function opened(raw, expectedSchema, names) {
    const value = bounded(raw); fields(value, [...names, 'sha256']);
    const { sha256, ...body } = value;
    fail(value.schema === expectedSchema && sha256 === await exactDigest(canonical(body)), 'INTEGRITY');
    for (const [key, expected] of Object.entries(scope)) fail(value[key] === expected, 'AUTHORITY');
    return value;
}
function outputArtifacts(mission, experiment) {
    const files = catalog.buildArtifacts(mission, experiment);
    files.exactJson = canonical({ schemaVersion: 1, mission, result: experiment }) + '\n';
    return Object.entries(artifacts).map(([key, name]) => ({ name,
        type: key === 'exactJson' ? 'application/json' : 'text/csv', content: files[key] }));
}
function summary(experiment) {
    const rec = experiment.reconciliation;
    return { matchedPairs: rec.matchedPairs, unmatchedLeft: rec.unmatchedLeft.length,
        unmatchedRight: rec.unmatchedRight.length, conflicts: rec.conflicts.length };
}
const adapter = {
    manifest: { id: 'catalog-reconciliation', version: 1, en: 'Reconcile exact catalogs',
        fr: 'Rapprocher exactement les catalogues', artifact: 'joined.csv',
        scope: 'Reconcile exact string-key catalog rows, preserve duplicate multiplicity, report unmatched rows and conflicts.' },
    validate(input) { fields(input, ['mission']); catalog.validateJoinMission(input.mission); },
    async execute(input, checkpoint) {
        await checkpoint('reconciling-catalogs');
        const experiment = await catalog.runJoinExperiment(input.mission,
            { onProgress: () => {}, checkpoint });
        await checkpoint('checking-catalog-output');
        catalog.verifyExperiment(input.mission, experiment);
        return { decision: 'REVIEW_REQUIRED', summary: summary(experiment), evidence: { experiment },
            artifacts: outputArtifacts(input.mission, experiment), limits: [...limits] };
    },
};
export const nativeCatalog = createWorkbench([adapter]);

function nativeSpec(project, cycle, options) {
    // Rights are explicitly entered. CSV content cannot establish its own permitted uses.
    fail(options.rights !== undefined, 'EXPLICIT_RIGHTS_REQUIRED');
    const spec = { schema: 'successor-workbench/v1', family: adapter.manifest.id,
        name: options.name ?? project.name, language: options.language ?? 'en', owner: options.owner,
        rights: clone(options.rights), reviewMinutes: options.reviewMinutes,
        inputs: { mission: clone(cycle.mission) } };
    fail(typeof spec.name === 'string' && spec.name.length <= 48
        && spec.name === spec.name.normalize('NFC'), 'NATIVE_NAME');
    return nativeCatalog.validate(spec);
}
const handoffFields = ['schema', 'project', 'cycle', 'runtimeSourceHash', 'route', 'specRaw',
    'compilationRaw', 'compiledAt', ...Object.keys(scope)];

/** Produces real native workbench input and an actual compiler-validated unfunded Jobs plan. */
export async function createNativeHandoff(dossier, options = {}) {
    const project = inspectProject(dossier), cycle = project.cycles.at(-1);
    fail(cycle, 'RUN_CATALOG_FIRST');
    fail(options.route === 'AGIALPHA', 'NATIVE_ROUTE_UNSUPPORTED');
    hash(options.sourceHash);
    const spec = nativeSpec(project, cycle, options), raw = serializeProject(project);
    const compiledAt = options.compiledAt ?? new Date().toISOString();
    fail(typeof compiledAt === 'string' && Number.isFinite(Date.parse(compiledAt))
        && new Date(compiledAt).toISOString() === compiledAt, 'CLOCK');
    const compilation = await nativeCatalog.plan(spec, compiledAt);
    return seal({ schema: HANDOFF_SCHEMA,
        project: { id: project.id, revision: project.revision, raw, sha256: await exactDigest(raw) },
        cycle: { id: cycle.id, index: project.cycles.length - 1, sourceHash: cycle.sourceHash,
            missionSha256: await exactDigest(canonical(cycle.mission)) },
        runtimeSourceHash: options.sourceHash,
        route: { backend: 'native-jobs-compiler-local', asset: 'AGIALPHA', funding: 'unfunded-proposal' },
        specRaw: canonical(spec), compilationRaw: canonical(compilation), compiledAt, ...scope });
}

export async function inspectNativeHandoff(raw) {
    const handoff = await opened(raw, HANDOFF_SCHEMA, handoffFields);
    fields(handoff.project, ['id', 'revision', 'raw', 'sha256']);
    fields(handoff.cycle, ['id', 'index', 'sourceHash', 'missionSha256']);
    const project = inspectProject(handoff.project.raw), cycle = project.cycles.at(-1);
    fail(cycle && handoff.project.sha256 === await exactDigest(handoff.project.raw)
        && handoff.project.raw === serializeProject(project) && handoff.project.id === project.id
        && handoff.project.revision === project.revision, 'PROJECT_BINDING');
    fail(handoff.cycle.id === cycle.id && handoff.cycle.index === project.cycles.length - 1
        && handoff.cycle.sourceHash === cycle.sourceHash
        && handoff.cycle.missionSha256 === await exactDigest(canonical(cycle.mission)), 'CYCLE_BINDING');
    hash(handoff.runtimeSourceHash);
    fail(same(handoff.route, { backend: 'native-jobs-compiler-local', asset: 'AGIALPHA',
        funding: 'unfunded-proposal' }), 'ROUTE');
    const spec = bounded(handoff.specRaw);
    const expected = nativeSpec(project, cycle, spec);
    fail(handoff.specRaw === canonical(expected), 'NATIVE_SPEC_BINDING');
    fail(typeof handoff.compiledAt === 'string' && Number.isFinite(Date.parse(handoff.compiledAt))
        && new Date(handoff.compiledAt).toISOString() === handoff.compiledAt, 'CLOCK');
    fail(handoff.compilationRaw === canonical(await nativeCatalog.plan(spec, handoff.compiledAt)),
        'NATIVE_JOBS_BINDING');
    return { handoff, project, cycle, spec, compilation: bounded(handoff.compilationRaw),
        authority: [], activeProof: [], sourceAuthenticity: 'not-established', compatibility: COMPATIBILITY };
}
const returnFields = ['schema', 'handoffSha256', 'projectId', 'cycleId', 'runtimeSourceHash',
    'nativePackRaw', ...Object.keys(scope)];

/** Fixed installed local code; this is not a Fleet receipt or a commissioned provider result. */
export async function runNativeHandoff(raw, { sourceHash, signal, onProgress } = {}) {
    const { handoff, spec } = await inspectNativeHandoff(raw);
    hash(sourceHash); fail(sourceHash === handoff.runtimeSourceHash, 'SOURCE_DRIFT');
    const pack = await nativeCatalog.run(spec, { sourceHash, signal, onProgress });
    const returned = await seal({ schema: RETURN_SCHEMA, handoffSha256: await exactDigest(raw),
        projectId: handoff.project.id, cycleId: handoff.cycle.id, runtimeSourceHash: sourceHash,
        nativePackRaw: canonical(pack), ...scope });
    await inspectNativeReturn(raw, returned);
    return returned;
}

export async function inspectNativeReturn(handoffRaw, returnRaw) {
    const checked = await inspectNativeHandoff(handoffRaw);
    const returned = await opened(returnRaw, RETURN_SCHEMA, returnFields);
    fail(returned.handoffSha256 === await exactDigest(handoffRaw)
        && returned.projectId === checked.project.id && returned.cycleId === checked.cycle.id
        && returned.runtimeSourceHash === checked.handoff.runtimeSourceHash, 'RETURN_BINDING');
    const pack = bounded(returned.nativePackRaw);
    await nativeCatalog.inspectPack(pack);
    fail(returned.nativePackRaw === canonical(pack) && same(pack.spec, checked.spec), 'RETURN_SPEC');
    const expectedFrozen = { schema: 'successor-workbench/v1',
        missionDigest: await digest('workbench-mission', (({ name, language, ...rest }) => rest)(checked.spec)),
        sourceHash: returned.runtimeSourceHash, adapter: adapter.manifest.id, adapterVersion: 1,
        model: null, provider: null, authority: [], inputPolicy: checked.spec.rights,
        reviewMinutes: checked.spec.reviewMinutes };
    fail(same(pack.frozen, expectedFrozen), 'RETURN_FROZEN');
    fail(same(pack.evaluation, { scope: 'PUBLIC_LOCAL_EXECUTION', independentProof: false,
        admission: 'HOLD', authority: [], settlement: 'NOT_CONNECTED' }), 'RETURN_SCOPE');
    fields(pack.economics, ['elapsedMilliseconds', 'providerSpendBaseUnits', 'settlementSpendBaseUnits',
        'computeCost', 'humanMinutes', 'reviewCapacityMinutes', 'allowanceIs']);
    integer(pack.economics.elapsedMilliseconds, Number.MAX_SAFE_INTEGER);
    fail(same({ ...pack.economics, elapsedMilliseconds: 0 }, { elapsedMilliseconds: 0,
        providerSpendBaseUnits: '0', settlementSpendBaseUnits: '0', computeCost: null, humanMinutes: null,
        reviewCapacityMinutes: checked.spec.reviewMinutes, allowanceIs: 'UNFUNDED' }), 'RETURN_ECONOMICS');
    fields(pack.result, ['decision', 'summary', 'evidence', 'artifacts', 'limits']);
    fields(pack.result.evidence, ['experiment']);
    catalog.verifyExperiment(checked.cycle.mission, pack.result.evidence.experiment);
    const expectedArtifacts = outputArtifacts(checked.cycle.mission, pack.result.evidence.experiment);
    const actualArtifacts = pack.result.artifacts.map(({ digest: _, ...file }) => file);
    fail(pack.result.decision === 'REVIEW_REQUIRED'
        && same(pack.result.summary, summary(pack.result.evidence.experiment))
        && same(pack.result.limits, limits) && same(actualArtifacts, expectedArtifacts), 'RETURN_OUTPUT');
    fail(same(pack.chronicle, [{ kind: 'local-result', decision: 'REVIEW_REQUIRED',
        missionDigest: pack.frozen.missionDigest, releaseDigest: pack.releaseDigest,
        inheritedProof: false, inheritedAuthority: false }]), 'RETURN_CHRONICLE');
    return { ...checked, returned, pack, files: expectedArtifacts, reviewClass: 'historical-local-unreviewed',
        independentReview: false, productionQualified: false, runAuthorized: false,
        currentReview: null, qualification: scope.qualification };
}

function extension(previous, next) {
    fail(previous.id === next.id && previous.createdAt === next.createdAt && previous.goal === next.goal
        && next.revision >= previous.revision && next.cycles.length >= previous.cycles.length
        && next.opportunities.length >= previous.opportunities.length
        && same(previous.cycles, next.cycles.slice(0, previous.cycles.length))
        && same(previous.opportunities, next.opportunities.slice(0, previous.opportunities.length)), 'PROJECT_HISTORY_REWRITE');
    if (next.revision === previous.revision) {
        fail(serializeProject(next) === serializeProject(previous), 'REVISION_CONFLICT');
    }
}
const continuityFields = ['schema', 'projectId', 'snapshots', 'returns', ...Object.keys(scope)];

export async function inspectContinuity(raw) {
    const value = await opened(raw, CONTINUITY_SCHEMA, continuityFields);
    fail(Array.isArray(value.snapshots) && value.snapshots.length >= 1
        && value.snapshots.length <= LIMITS.snapshots && Array.isArray(value.returns)
        && value.returns.length >= 1 && value.returns.length <= LIMITS.returns, 'HISTORY_CAPACITY');
    const snapshots = new Map(); let previous = null;
    for (const snapshot of value.snapshots) {
        fields(snapshot, ['raw', 'sha256']);
        const project = inspectProject(snapshot.raw);
        fail(snapshot.raw === serializeProject(project) && snapshot.sha256 === await exactDigest(snapshot.raw)
            && project.id === value.projectId && !snapshots.has(snapshot.sha256), 'SNAPSHOT_BINDING');
        if (previous) extension(previous, project);
        snapshots.set(snapshot.sha256, project); previous = project;
    }
    const seen = new Set();
    for (const entry of value.returns) {
        fields(entry, ['handoffRaw', 'returnRaw', 'handoffSha256', 'returnSha256', 'projectSha256']);
        fail(entry.handoffSha256 === await exactDigest(entry.handoffRaw)
            && entry.returnSha256 === await exactDigest(entry.returnRaw)
            && !seen.has(entry.returnSha256), 'DUPLICATE_OR_CHANGED_RETURN');
        const checked = await inspectNativeReturn(entry.handoffRaw, entry.returnRaw);
        fail(checked.project.id === value.projectId && checked.handoff.project.sha256 === entry.projectSha256
            && snapshots.has(entry.projectSha256), 'RETURN_SNAPSHOT');
        seen.add(entry.returnSha256);
    }
    return { continuity: value, project: previous, authority: [], activeProof: [],
        currentReview: null, sourceAuthenticity: 'not-established', compatibility: COMPATIBILITY };
}

/** Retains exact project history and checked returns separately from the strict flagship project schema. */
export async function importNativeReturn(dossier, handoffRaw, returnRaw,
    { sourceHash, priorRecord = null } = {}) {
    const project = inspectProject(dossier), checked = await inspectNativeReturn(handoffRaw, returnRaw);
    fail(serializeProject(project) === checked.handoff.project.raw, 'STALE_PROJECT_RETURN');
    if (sourceHash !== undefined) { hash(sourceHash); fail(sourceHash === checked.returned.runtimeSourceHash, 'SOURCE_DRIFT'); }
    let body;
    if (priorRecord !== null) {
        const existing = await inspectContinuity(priorRecord); extension(existing.project, project);
        body = clone(existing.continuity); delete body.sha256;
    } else body = { schema: CONTINUITY_SCHEMA, projectId: project.id, snapshots: [], returns: [], ...scope };
    const projectSha256 = checked.handoff.project.sha256;
    if (body.snapshots.at(-1)?.sha256 !== projectSha256) {
        body.snapshots.push({ raw: serializeProject(project), sha256: projectSha256 });
    }
    body.returns.push({ handoffRaw, returnRaw, handoffSha256: await exactDigest(handoffRaw),
        returnSha256: await exactDigest(returnRaw), projectSha256 });
    const raw = await seal(body); await inspectContinuity(raw); return raw;
}
