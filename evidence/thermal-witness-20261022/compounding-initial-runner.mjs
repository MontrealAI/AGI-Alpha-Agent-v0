// SPDX-License-Identifier: Apache-2.0
/** Bounded evaluation of the existing enterprise engine; no controller or authority is added. */
import {readFile, writeFile, mkdtemp, rm} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {performance} from 'node:perf_hooks';
import {buildFoundry, executeQualified, constructInverse} from '../autonomous-enterprises/foundry.mjs';
import {qualifyArtifact, verifyBundle, specificationApplication} from '../autonomous-enterprises/checker.mjs';
import {additionalCheckingWork, defaultCharter, auditSnapshot} from '../autonomous-enterprises/protocol.mjs';
import {applySpecialist} from '../autonomous-enterprises/specialist.mjs';
import {resourceWitness} from '../autonomous-enterprises/capital.mjs';
import {canonical, payloadDigest} from '../successor-capability/discovery-lab-contract.mjs';
import * as workspace from '../successor-capability/workspace.mjs';
import * as controller from '../autonomous-enterprises/controller.mjs';

export const FROZEN_EVALUATION = Object.freeze({
    schema: 'enterprise-compounding-evaluation/v1',
    engineBase: '8f13b39ed1718f5e8141ac1b37a10bb05c0f2900',
    sourceManifest: 'docs/successor/capabilities/sources.json',
    sourceManifestSHA256: 'd1c3cb9a5c3eb96e9e5eb111b83a713786ec18ed1213a407cd77bbaf018c5adb',
    sourceClosure: '54769dbfde99ae13708a33292866f0ca7e6b8b7792a7a944f76bf2fbf1de1358',
    maxN: 8, rounds: [1, 4, 16], seed: 20261022,
    kinds: ['walsh', 'xor-convolution', 'inverse'],
    arms: ['retained-assets', 'rebuild-per-round', 'competent-static-specialist'],
    workBudgets: [1000, 60000, 250000],
    changedKernel: ['11', '1', '1', '1', '1', '1', '1', '1'],
    singularKernel: ['1', '1', '1', '1', '1', '1', '1', '1'],
    metric: 'paper-declared-arithmetic-work/v1',
    loadScope: 'Sequential batches in one process; not concurrent load, throughput or a statistical benchmark.',
    inputRule: 'Reset public LCG seed for each workload; state=(imul(state,1664525)+1013904223)>>>0; value=String(state%15-7). Eight entries per vector; convolution has two vectors.',
    costRule: 'Retain every actual construction, rejected candidate, selected qualification, dependency/scope check, current admission, productive arithmetic, independent reference arithmetic and comparison. Scenario attribution reuses the same ancestor charge; do not sum alternative scenario totals. Actual campaign totals deduplicate charge identities, not repeated execution.',
    specialistPreparation: 'Zero additional arithmetic preparation exposed by this fixed implementation. Supplied authorship, proof, parsing and institutional qualification costs are unknown, not zero.',
    breakEven: 'For identical checked task families, B=complete counted build, V=current complete admission, W(R)=checked execution. Retained=B+V+W(R); rebuilding=R*(B+V)+W(R). Difference=(R-1)*(B+V); R=1 ties. Unknown costs are excluded; this is not monetary break-even.',
    criteria: [
        'Every base task output in all three arms equals the independently implemented exact specification; retain every failure.',
        'Every construction and admission is actually executed; full observed ledgers, including search failures and direct/inherited controls, remain in evidence. Never substitute selected-path cost for campaign cost.',
        'All nine alternative scenario costs and budget fits are reported, including losses and ties. No required economic advantage or budget fit.',
        'Changed kernel: independently qualified direct/inherited constructions agree in artifact identity; stale inverse fails the new residual; successor passes. Singular kernel is rejected and its spent work retained. Ancestors remain charged.',
        'Observed rebuilding-minus-retention equals the predeclared formula for each workload. Specialist comparison counts its exposed preparation and keeps unknown preparation explicit.',
        'Existing source-bound controller reaches SUCCESSOR_ACCEPTED_LOCAL, writes a completed workspace, reads and validates it, and retains identical canonical bytes and final state. No external approval, physical qualification, payment or thermal acceptance is inferred.'
    ],
    unknownCosts: ['humanActiveMilliseconds', 'authoringAndEngineering', 'institutionalReview', 'moneyByCurrency',
        'energy', 'peakMemory', 'maintenanceOutsideThisRun', 'bitComplexity', 'framingHashingSerialization'],
    recoveryScope: 'Completed-workspace file roundtrip only; not a pending-invocation OS crash test.'
});

const same = (a, b) => canonical(a) === canonical(b);
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const unknownCosts = () => Object.fromEntries(FROZEN_EVALUATION.unknownCosts.map(key => [key, null]));
const sum = entries => entries.reduce((total, entry) => total + (entry.countedWork ?? 0), 0);
const fullQualification = proof => proof.totalWork + additionalCheckingWork(proof);
const kernel = first => Array.from({length: FROZEN_EVALUATION.maxN}, (_, i) => String(i ? 1 : first));

function tasks(rounds) {
    let state = FROZEN_EVALUATION.seed;
    const next = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return String(state % 15 - 7); };
    return Array.from({length: rounds}, (_, round) => FROZEN_EVALUATION.kinds.map(kind => ({
        id: `round-${round + 1}/${kind}`, kind,
        inputs: Array.from({length: kind === 'xor-convolution' ? 2 : 1}, () => Array.from({length: 8}, next))
    })));
}

/** Pure component orchestration: imports existing constructors/checkers; no new enterprise state machine. */
export async function runCompoundingProbe() {
    const ledger = [], rawReceipts = {}, scenarios = [], failures = [], began = performance.now();
    async function charge(phase, scope, operation, count, describe = value => ({receipt: value})) {
        const started = performance.now();
        try {
            const value = await operation(), countedWork = count(value), details = describe(value);
            if (!Number.isSafeInteger(countedWork) || countedWork < 0) throw Error('Invalid observed work charge.');
            for (const key of ['receipt', 'rawConstructionReceipt']) if (details[key] !== undefined) {
                const digest = await payloadDigest(details[key]);
                rawReceipts[digest] ??= details[key]; delete details[key]; details[key + 'Digest'] = digest;
            }
            const entry = {id: `charge-${ledger.length + 1}`, phase, scope, status: 'OBSERVED', countedWork,
                elapsedMicroseconds: Math.round((performance.now() - started) * 1000), ...details};
            ledger.push(entry); return {value, entry};
        } catch (error) {
            ledger.push({id: `charge-${ledger.length + 1}`, phase, scope, status: 'UNKNOWN_PARTIAL_WORK',
                countedWork: null, elapsedMicroseconds: Math.round((performance.now() - started) * 1000), error: String(error.message)});
            throw error;
        }
    }
    const construct = scope => charge('construction-search-validation', scope,
        () => buildFoundry({qualifyArtifact, maxN: 8}), value => value.observedWorkLedger.totalCountedCampaignWork,
        value => ({components: value.observedWorkLedger, selectedCounts: value.counts,
            candidateCount: value.transforms.reduce((count, item) => count + item.attempts.length, 0)
                + value.convolution.attempts.length, rawConstructionReceipt: value}));
    const admit = (bundle, scope) => charge('maintenance-current-admission', scope,
        () => verifyBundle(bundle), value => value.currentReplayWork);
    async function invoke(bundle, task, arm, scope, selectedChild = null) {
        return charge('productive-execution-and-independent-review', scope, () => {
            const envelope = selectedChild || bundle?.envelopes.find(item => item.artifact.kind === task.kind && item.artifact.n === 8);
            const result = arm === 'competent-static-specialist' ? applySpecialist(task.kind, task.inputs)
                : executeQualified(envelope.artifact, bundle.envelopes, task.inputs);
            const reference = selectedChild ? specificationApplication('xor-convolution',
                [FROZEN_EVALUATION.changedKernel, result.output])
                : specificationApplication(task.kind, task.inputs, task.kind === 'inverse' ? {kernel: kernel(9)} : {});
            const accepted = selectedChild ? same(reference.output, task.inputs[0]) : same(result.output, reference.output);
            return {task, artifactDigest: envelope?.digest ?? null, output: result.output,
                referenceOutput: reference.output, accepted, productiveArithmetic: result.arithmetic,
                independentReferenceArithmetic: reference.arithmetic, comparisons: 8};
        }, value => value.productiveArithmetic + value.independentReferenceArithmetic + value.comparisons);
    }
    try {
        const ancestor = await construct('shared-ancestor');
        for (const rounds of FROZEN_EVALUATION.rounds) for (const arm of FROZEN_EVALUATION.arms) {
            const scope = `${arm}/${rounds}`, entries = [], batches = tasks(rounds);
            let bundle = ancestor.value;
            if (arm === 'retained-assets') {
                entries.push(ancestor.entry);
                const proof = await admit(bundle, scope); entries.push(proof.entry);
                if (!proof.value.verified) failures.push({scope, reason: 'CURRENT_ADMISSION_REJECTED'});
            }
            for (const batch of batches) {
                if (arm === 'rebuild-per-round') {
                    const build = await construct(scope); bundle = build.value; entries.push(build.entry);
                    const proof = await admit(bundle, scope); entries.push(proof.entry);
                    if (!proof.value.verified) failures.push({scope, reason: 'CURRENT_ADMISSION_REJECTED'});
                }
                for (const task of batch) {
                    const result = await invoke(bundle, task, arm, scope); entries.push(result.entry);
                    if (!result.value.accepted) failures.push({scope, task: task.id, reason: 'OUTPUT_MISMATCH'});
                }
            }
            const knownCountedWork = sum(entries);
            scenarios.push({arm, rounds, requests: rounds * 3, chargeIds: entries.map(entry => entry.id), knownCountedWork,
                knownPreparationWork: sum(entries.filter(entry => entry.phase !== 'productive-execution-and-independent-review')),
                specialistExposedArithmeticPreparation: arm === 'competent-static-specialist' ? 0 : null,
                budgetFits: FROZEN_EVALUATION.workBudgets.map(budget => ({budget,
                    witness: resourceWitness([{id: scope, steps: [[knownCountedWork]]}], [budget])})),
                unknownCosts: unknownCosts(), totalEconomicCostComplete: false});
        }
        const analyticalChecks = FROZEN_EVALUATION.rounds.map(rounds => {
            const retained = scenarios.find(item => item.rounds === rounds && item.arm === 'retained-assets');
            const rebuilt = scenarios.find(item => item.rounds === rounds && item.arm === 'rebuild-per-round');
            const expected = (rounds - 1) * retained.knownPreparationWork;
            const actual = rebuilt.knownCountedWork - retained.knownCountedWork;
            if (actual !== expected) failures.push({rounds, reason: 'PREDECLARED_COST_FORMULA_FAILED', actual, expected});
            return {rounds, expected, actual, matches: actual === expected};
        });
        const changedEntries = [], children = [];
        for (const reference of ['direct', 'inherited']) {
            const child = await charge('changed-condition-construction-and-validation', reference,
                () => constructInverse(ancestor.value.transforms.at(-1).envelope, ancestor.value.envelopes, qualifyArtifact,
                    {reference, kernel: FROZEN_EVALUATION.changedKernel,
                        ...(reference === 'inherited' ? {convolutionDigest: ancestor.value.convolution.envelope.digest} : {})}),
                value => value.constructionWork + fullQualification(value.verification));
            children.push(child.value); changedEntries.push(child.entry);
        }
        const child = children[1], options = {reference: 'inherited', convolutionDigest: ancestor.value.convolution.envelope.digest};
        const replay = await charge('maintenance-changed-child-admission', 'changed-kernel',
            () => qualifyArtifact(child.envelope.artifact, ancestor.value.envelopes, options), fullQualification);
        changedEntries.push(replay.entry);
        const changedTask = tasks(1)[0].find(task => task.kind === 'inverse');
        const old = ancestor.value.inverseInherited.envelope;
        const stale = await invoke(ancestor.value, changedTask, 'retained-assets', 'changed-kernel/stale', old);
        const current = await invoke(ancestor.value, changedTask, 'retained-assets', 'changed-kernel/successor', child.envelope);
        changedEntries.push(stale.entry, current.entry);
        const rejected = await charge('rejected-changed-condition-search', 'singular-kernel',
            () => constructInverse(ancestor.value.transforms.at(-1).envelope, ancestor.value.envelopes, qualifyArtifact,
                {kernel: FROZEN_EVALUATION.singularKernel}), value => value.totalWork);
        changedEntries.push(rejected.entry);
        const changed = {ancestorChargeId: ancestor.entry.id, chargeIds: changedEntries.map(entry => entry.id),
            knownIncrementalWork: sum(changedEntries), knownLineageWork: ancestor.entry.countedWork + sum(changedEntries),
            sameChildIdentity: children[0].envelope.digest === child.envelope.digest,
            directAccepted: children[0].verification.accepted, inheritedAccepted: child.verification.accepted,
            currentAdmissionAccepted: replay.value.accepted, stalePassesChangedRequirement: stale.value.accepted,
            successorPassesChangedRequirement: current.value.accepted,
            rejectedState: rejected.value.state, rejectedReason: rejected.value.reason, rejectedSpentWork: rejected.entry.countedWork,
            retainedArtifactDigests: ancestor.value.envelopes.map(item => item.digest), successorDigest: child.envelope.digest};
        if (!changed.sameChildIdentity || !changed.directAccepted || !changed.inheritedAccepted || !changed.currentAdmissionAccepted
            || changed.stalePassesChangedRequirement || !changed.successorPassesChangedRequirement
            || changed.rejectedState !== 'REJECTED' || changed.rejectedReason !== 'SINGULAR_KERNEL' || !changed.rejectedSpentWork) {
            failures.push({reason: 'CHANGED_CONDITION_CRITERION_FAILED', changed});
        }
        return {schema: 'enterprise-compounding-result/v1', state: failures.length ? 'FAILED_CRITERIA' : 'PASSED_COMPONENT_CRITERIA',
            criteria: FROZEN_EVALUATION, scenarios, analyticalChecks, changed, failures, ledger, rawReceipts,
            actualCampaignKnownWork: sum(ledger), elapsedMicroseconds: Math.round((performance.now() - began) * 1000),
            campaignScope: 'All actual component experiment operations, including comparison arms and evaluation overhead. Alternative scenario totals share attribution and must not be summed.',
            unknownCosts: unknownCosts(), totalEconomicCostComplete: false, externalAuthority: false,
            enterpriseAcceptance: 'REQUIRES_SEPARATE_EXISTING_CONTROLLER_JOURNEY', physicalQualification: 'NOT_ESTABLISHED'};
    } catch (error) {
        return {schema: 'enterprise-compounding-result/v1', state: 'FAILED_EXECUTION', criteria: FROZEN_EVALUATION,
            error: String(error.message), scenarios, failures, ledger, rawReceipts, actualCampaignKnownWork: sum(ledger),
            unknownPartialWork: true, unknownCosts: unknownCosts(), totalEconomicCostComplete: false, externalAuthority: false};
    }
}

/** Use existing enterprise transitions, real source bindings and a completed-workspace disk roundtrip. */
export async function runEnterpriseJourney(source) {
    const began = performance.now(), before = auditSnapshot(), transitions = [], charter = defaultCharter(source);
    charter.maxN = 8;
    let value = await controller.start(await workspace.createWorkspace({...workspace.DEFAULT_BRIEF,
        title: 'Bounded reusable computation enterprise: n=8 compounding probe'}, null), charter);
    for (let step = 0; step < 11; step++) {
        const inspection = await controller.state(value);
        if (!inspection.current) break;
        transitions.push(inspection.current.state);
        value = inspection.current.state === 'INVOCATION_RESERVED' ? await controller.invokeReserved(value, source)
            : await controller.next(value, {seed: 20261021, expectedSource: source});
    }
    const finished = await controller.state(value), row = finished.history.at(-1);
    if (row?.state !== 'SUCCESSOR_ACCEPTED_LOCAL') throw Error('Controller did not accept local successor: ' + row?.state);
    const directory = await mkdtemp(join(tmpdir(), 'agi-alpha-compounding-'));
    try {
        const bytes = workspace.canonical(value) + '\n', path = join(directory, 'workspace.json');
        await writeFile(path, bytes, {flag: 'wx'});
        const saved = await readFile(path, 'utf8'), reopened = await workspace.parseWorkspace(saved);
        const recovered = await controller.state(reopened), recoveredState = recovered.history.at(-1)?.state;
        const identical = saved === bytes && workspace.canonical(reopened) === workspace.canonical(value);
        if (!identical || recoveredState !== row.state) throw Error('Completed workspace roundtrip changed accepted history.');
        const after = auditSnapshot(), replay = Object.fromEntries(['bundleReplayWork', 'futureReplayWork', 'successorReplayWork']
            .map(key => [key, after[key] - before[key]]));
        const originalExecutionWork = row.actualConstructionWork + row.future.lineage.knownFutureTreatmentWork
            + row.successor.observedSuccessorWork;
        return {state: row.state, source, transitions: transitions.concat(row.state), savedWorkspaceSHA256: sha256(saved),
            fileRoundtripIdentical: identical, recoveredState, workspace: reopened,
            historicalLineageWork: row.successor.lineageWork,
            originalExecutionWork, actualReplayWork: replay,
            knownObservedControllerWork: originalExecutionWork + Object.values(replay).reduce((a, b) => a + b, 0),
            accounting: 'Original construction, original future treatment campaign and child construction plus each actually executed replay in this loaded-session delta. The original future bundle admission appears in bundleReplayWork; it is not added twice from historicalLineageWork.',
            sessionReplayAudit: {before, after}, elapsedMicroseconds: Math.round((performance.now() - began) * 1000),
            recoveryScope: FROZEN_EVALUATION.recoveryScope, totalEconomicCostComplete: false,
            unknownCosts: unknownCosts(), institutionalAcceptance: false, externalAuthority: false, settlement: 'SIMULATED_ONLY'};
    } finally { await rm(directory, {recursive: true, force: true}); }
}

async function main() {
    if (process.argv.length !== 2) throw Error('Usage: node examples/successor-workbench/compounding-probe.mjs');
    const startedAt = new Date().toISOString(), root = new URL('../../', import.meta.url);
    const manifestBytes = await readFile(new URL(FROZEN_EVALUATION.sourceManifest, root));
    if (sha256(manifestBytes) !== FROZEN_EVALUATION.sourceManifestSHA256) throw Error('Frozen source manifest changed.');
    const manifest = JSON.parse(manifestBytes), sources = {};
    if (manifest.sourceHash !== FROZEN_EVALUATION.sourceClosure) throw Error('Frozen source closure changed.');
    for (const [path, expected] of Object.entries(manifest.sources)) {
        sources[path] = sha256(await readFile(new URL(path, root)));
        if (sources[path] !== expected) throw Error('Source bytes differ from frozen experiment: ' + path);
    }
    const source = {constructor: sources['examples/autonomous-enterprises/foundry.mjs'],
        checker: sources['examples/autonomous-enterprises/checker.mjs'], closure: manifest.sourceHash};
    const environment = {runtime: 'Node.js', node: process.version, platform: process.platform, architecture: process.arch,
        startedAt, source, sources, runnerSHA256: sha256(await readFile(fileURLToPath(import.meta.url))),
        installedCustody: 'NOT_ESTABLISHED', liveProviders: 'NOT_INVOKED'};
    const components = await runCompoundingProbe();
    let enterpriseJourney;
    try { enterpriseJourney = await runEnterpriseJourney(source); }
    catch (error) { enterpriseJourney = {state: 'FAILED_EXECUTION', error: String(error.message),
        sessionReplayAudit: auditSnapshot(), unknownPartialWork: true, externalAuthority: false}; }
    console.log(JSON.stringify({schema: 'enterprise-compounding-native-report/v1', environment, components,
        enterpriseJourney, finishedAt: new Date().toISOString()}, null, 2));
    if (components.state !== 'PASSED_COMPONENT_CRITERIA' || enterpriseJourney.state !== 'SUCCESSOR_ACCEPTED_LOCAL') process.exitCode = 1;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
