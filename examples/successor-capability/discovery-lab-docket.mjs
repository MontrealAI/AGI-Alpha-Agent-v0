// SPDX-License-Identifier: Apache-2.0
// A derived export of the existing mission history; importing it grants no authority.
import * as contract from './discovery-lab-contract.mjs';
import * as workspace from './workspace.mjs';
import {inspectReceiverReceipt, makeReceiverContext, rawReceiptDigest, receiptRequestBindings} from './discovery-lab-receipts.mjs';

export const DOCKET_SCHEMA = 'successor-discovery-evidence-docket/v1';
export const ATTACHMENT_SCHEMA = 'successor-discovery-docket-attachments/v1';
export const DOCKET_PATHS = Object.freeze([
    '00_manifest.md', '01_claims_matrix.md', '02_environment.md',
    '03_benchmark_tasks/spec.json', '04_baselines/comparison.json', '05_agialpha_runs/run.json',
    '06_proof_bundles/capability.json', '07_replay_logs/replay.json', '08_cost_ledgers/costs.json',
    '09_safety_ledgers/safety.json', '10_validator_reports/review.json',
    '11_alpha_wu_calibration/status.json', '12_summary_tables/outcome.json'
]);
const same = (left, right) => contract.canonical(left) === contract.canonical(right);
const copy = value => JSON.parse(contract.canonical(value));
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const need = (condition, message) => { if (!condition) throw Error(message); };
const hash = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const git = value => typeof value === 'string' && /^[0-9a-f]{40}$/.test(value);
const zero = () => Object.fromEntries(['acquisitions', 'search', 'checking', 'memoryWords',
    'storageBytes', 'workerSlots', 'installations'].map(key => [key, 0]));
const receiptZero = () => Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 0]));
function capturedOptions(options) {
    const owned = copy(options);
    need(Object.keys(owned).every(key => ['expectedSources', 'expectedReceiverSources', 'expectedWorkspaceHead',
        'expectedMissionId'].includes(key)), 'Unsupported docket verifier option.');
    if (Object.hasOwn(owned, 'expectedWorkspaceHead')) need(hash(owned.expectedWorkspaceHead), 'Expected docket head is invalid.');
    return owned;
}
export const rawDigest = rawReceiptDigest;
function sum(target, vector, peaks = []) {
    for (const key of Object.keys(target)) {
        const next = peaks.includes(key) ? Math.max(target[key], vector[key]) : target[key] + vector[key];
        need(Number.isSafeInteger(next) && next >= 0, 'Docket cost total exceeds the integer bound.');
        target[key] = next;
    }
}
function validateSource(input) {
    need(exact(input, ['repository', 'commit', 'tree', 'files'])
        && /^MontrealAI\/[A-Za-z0-9_.-]+$/.test(input.repository) && git(input.commit) && git(input.tree)
        && Array.isArray(input.files) && input.files.length <= 100,
    'Docket repository source identity differs.');
    const names = new Set();
    for (const file of input.files) {
        need(exact(file, ['path', 'sha256']) && typeof file.path === 'string' && file.path.length <= 500
            && !file.path.startsWith('/') && !file.path.includes('\\')
            && file.path.split('/').every(part => part && !['.', '..'].includes(part))
            && hash(file.sha256) && !names.has(file.path), 'Docket generated/source file identity differs.');
        names.add(file.path);
    }
    return input;
}

export async function emptyDocketAttachments(value) {
    value = copy(value);
    const inspected = await workspace.inspectWorkspace(value);
    return {schema: ATTACHMENT_SCHEMA, missionId: value.missionId, workspaceHead: inspected.head,
        sources: [], receipts: []};
}

async function derive(value, attachments, options) {
    // Own both graphs before the first digest/replay suspension.
    value = copy(value); attachments = copy(attachments);
    const expectedSources = options.expectedSources === undefined ? undefined : copy(options.expectedSources);
    const receiverSources = options.expectedReceiverSources === undefined ? undefined : copy(options.expectedReceiverSources);
    const expectedHead = options.expectedWorkspaceHead, expectedMission = options.expectedMissionId;
    const inspection = await workspace.inspectWorkspace(value);
    need(expectedHead === undefined || inspection.head === expectedHead, 'Docket history differs from the independently retained head.');
    need(expectedMission === undefined || value.missionId === expectedMission, 'Docket mission differs from the independently retained identity.');
    need(exact(attachments, ['schema', 'missionId', 'workspaceHead', 'sources', 'receipts'])
        && attachments.schema === ATTACHMENT_SCHEMA && attachments.missionId === value.missionId
        && attachments.workspaceHead === inspection.head
        && ['sources', 'receipts'].every(key => Array.isArray(attachments[key])
            && attachments[key].length <= 24), 'Docket attachment mission/head or fields differ.');
    attachments.sources.forEach(validateSource);
    need(new Set(attachments.sources.map(item => item.repository + ':' + item.commit)).size === attachments.sources.length,
        'Docket repeats or contradicts a repository commit source context.');
    if (expectedSources !== undefined) need(same(attachments.sources, expectedSources), 'Docket source context differs from installed expectations.');
    const historyAttachments = inspection.discovery.attachments || [];
    const receipts = [], receiptIds = new Set(), branches = new Map();
    const combinedReceipts = [...historyAttachments.filter(item => item.kind === 'receiver-receipt').map(item => item.record),
        ...attachments.receipts];
    for (const item of combinedReceipts) {
        const bindings = await receiptRequestBindings(item);
        const campaign = inspection.discovery.campaigns.find(record => same(record.bindings, bindings));
        need(campaign, 'Receipt has no independently replayed campaign.');
        const checked = await inspectReceiverReceipt(item, makeReceiverContext(campaign),
            receiverSources === undefined ? {} : {expectedReceiverSources: receiverSources});
        const branch = checked.commission.id + ':' + checked.commission.route;
        need(!receiptIds.has(checked.receiptId), 'Docket repeats a semantic receipt.');
        const branchIdentity = {branch: checked.commission.branch, currency: checked.commission.currency};
        const previous = branches.get(branch), fleet = checked.inspectionKind === 'fleet-local-review' || previous?.fleet;
        need(!previous || same(previous.identity, branchIdentity), fleet
            ? 'Contradictory original work reference: Fleet review cannot change the retained request branch.'
            : 'Docket commission route changes its frozen branch.');
        receiptIds.add(checked.receiptId); branches.set(branch, {identity: branchIdentity, fleet}); receipts.push(checked);
    }
    // These records have already passed the installed event replay. They can only
    // enter through original ordered hash-chain events, never caller aggregates.
    const futureEvaluations = historyAttachments.filter(item => item.kind === 'future-evaluation').map(item => ({
        campaignDigest: item.campaignDigest, eventDigest: item.eventDigest, recordDigest: item.recordDigest, result: item.record}));
    const realTaskRecords = historyAttachments.filter(item => item.kind === 'real-task-contract').map(item => ({
        campaignDigest: item.campaignDigest, eventDigest: item.eventDigest, recordDigest: item.recordDigest, record: item.record}));
    const unresolvedFuture = historyAttachments.filter(item => item.kind === 'future-run-reserved'
        && item.resolution?.kind !== 'future-evaluation').map(item => {
        const bank = historyAttachments.find(record => record.kind === 'future-task-bank'
            && record.campaignDigest === item.campaignDigest && record.record.digest === item.record.taskBankDigest);
        const maximumLogicalWork = bank.record.tasks.length * item.capsule.protocol.treatments.length * item.record.perTaskWorkLimit;
        need(Number.isSafeInteger(maximumLogicalWork), 'Future execution reservation exceeds the integer bound.');
        return {campaignDigest: item.campaignDigest, recordDigest: item.recordDigest, eventDigest: item.eventDigest,
            attempt: item.record.attempt, taskBankDigest: item.record.taskBankDigest,
            perTaskWorkLimit: item.record.perTaskWorkLimit, maximumLogicalWork,
            state: item.resolution?.kind === 'future-run-stopped' ? 'stopped' : 'reserved', spent: 'unknown-reservation-retained'};
    });
    const evidenceReplayLogical = {acquisitions: 0, search: 0, checking: 0, installations: 0};
    for (const item of historyAttachments) {
        if (item.kind === 'future-freeze' || item.kind === 'future-evaluation') sum(evidenceReplayLogical, item.capsule.admissionReplay);
        if (item.kind === 'future-evaluation') for (const run of item.record.runs) sum(evidenceReplayLogical, run.costs);
    }
    const legacyWitnessCosts = value.events.filter(item => item.kind === 'evaluation').map(item => ({
        eventDigest: item.digest, version: item.payload.number, phase: item.payload.phase, costs: item.payload.report.costs,
        accounting: 'Original witness metrics retained separately; repeated construction references are not a second construction charge or Discovery units'}));
    const realTaskChecks = [], seenChecks = new Set();
    for (const item of realTaskRecords) {
        const record = item.record;
        const proposalIdentity = record.proposalDigest;
        need(hash(proposalIdentity), 'A source/history-bound immutable real-task proposal is required.');
        for (const check of item.record.checks) {
            const checkIdentity = proposalIdentity + ':' + check.digest;
            if (seenChecks.has(checkIdentity)) continue;
            seenChecks.add(checkIdentity);
            realTaskChecks.push({eventDigest: item.eventDigest, proposalIdentity, checkDigest: check.digest, taskId: check.taskId,
                state: check.status, reportedObservation: check.observation.resourceUsed, contractChecker: check.checkerCharge,
                accounting: check.resourceAccounting, operationalState: item.record.operationalState});
        }
    }
    const construction = zero(), recordedReplay = zero();
    const campaigns = inspection.discovery.campaigns.map(record => {
        sum(construction, record.result.resources, ['memoryWords', 'workerSlots']);
        sum(recordedReplay, record.recordedVerification, ['memoryWords', 'workerSlots']);
        return {attempt: record.attempt, campaignDigest: record.campaignDigest, resultDigest: record.resultDigest,
            bindings: record.bindings, state: record.state, parent: record.parent?.campaignDigest || null,
            lineageQualified: record.lineageQualified, invalidations: record.result.invalidations,
            generation: record.result.lineage.generation, lineageCumulative: record.result.lineage.cumulative,
            construction: record.result.resources, recordedReplay: record.recordedVerification,
            elapsedReceipt: record.elapsedReceipt, artifactDigests: record.artifacts.map(item => item.digest)};
    });
    const unresolved = inspection.discovery.attempts.filter(record => !record.result).map(record => ({
        attempt: record.attempt, state: record.state, reservation: record.reservation,
        spent: 'unknown', disposition: record.resourceDisposition || 'active-reservation-retained'}));
    const total = zero(); sum(total, construction, ['memoryWords', 'workerSlots']); sum(total, recordedReplay, ['memoryWords', 'workerSlots']);
    const routeCosts = {}, fleetCosts = receiptZero();
    for (const receipt of receipts) {
        if (receipt.inspectionKind === 'fleet-local-review') {
            sum(fleetCosts, receipt.resources, ['memoryBytes', 'workerCapacity']);
            continue;
        }
        routeCosts[receipt.commission.route] ||= receiptZero();
        sum(routeCosts[receipt.commission.route], receipt.resources, ['memoryBytes', 'workerCapacity']);
    }
    const commissioned = receipts.filter(item => item.inspectionKind !== 'fleet-local-review');
    const commissions = [...new Set(commissioned.map(item => item.commission.id))].map(id => ({id,
        alternatives: [...new Set(commissioned.filter(item => item.commission.id === id).map(item => item.commission.route))].map(route => {
            const inspected = commissioned.filter(item => item.commission.id === id && item.commission.route === route);
            return {route, currency: inspected[0].commission.currency, reservedBaseUnits: '0', status: 'DRAFT_NOT_SUBMITTED',
                inspectionReceiptIds: inspected.map(item => item.receiptId)};
        }),
        interpretation: 'alternative routes; no currency conversion or duplicate payment obligation'}));
    return {value, attachments, inspection, campaigns, receipts, unresolved, construction, recordedReplay,
        total, routeCosts, fleetCosts, commissions, futureEvaluations, realTaskRecords, historyAttachments, unresolvedFuture,
        evidenceReplayLogical, legacyWitnessCosts, realTaskChecks};
}

async function filesFor(value, attachments, options = {}) {
    const data = await derive(value, attachments, options);
    const {inspection, campaigns, receipts, unresolved} = data;
    const render = item => contract.canonical(item) + '\n';
    const run = {schema: DOCKET_SCHEMA, workspace: data.value, attachments: data.attachments};
    const runDigest = await contract.payloadDigest(run);
    const unknown = ['independent organizational reproduction', 'current mainnet readiness', 'real settlement',
        'energy', 'monetary compute cost', 'human review/coordination time', 'calibrated alpha-WU', 'delayed commercial outcomes',
        'current export/replay overhead outside recorded campaign checks'];
    if (data.attachments.sources.length === 0) unknown.push('authenticated repository/generated-asset source inventory');
    const files = {
        '00_manifest.md': '# Discovery Lab Evidence Docket\n\nSchema: ' + DOCKET_SCHEMA + '\n\nMission: ' + data.value.missionId
            + '\n\nHistory head: ' + inspection.head + '\n\nRun commitment: ' + runDigest
            + '\n\nDerived from the complete existing mission history. Attachments bind this exact head; they are not new history events.\n'
            + 'Replay checks bounded synthetic computations. Imported evidence grants no capability, payment or execution authority.\n',
        '01_claims_matrix.md': '# Claims\n\n| Claim | Status |\n|---|---|\n'
            + '| Six-stage finite campaign evidence | Replayed; each original outcome retained |\n'
            + '| Future-task advantage | ' + (data.futureEvaluations.length ? 'Separate protocol evidence retained in history; inspect its comparisons' : 'NOT_RUN: no future-task protocol evidence attached') + ' |\n'
            + '| Real-task operational pilot | NOT_ESTABLISHED: contract records do not establish execution |\n'
            + '| Independent organizational validation / commercial value / AGI or ASI | Unproven |\n'
            + '| Promotion, release, live execution and settlement authority | Not granted by this docket |\n',
        '02_environment.md': '# Environment\n\nBounded public synthetic integer computations in the installed browser/Node runtime.\n'
            + 'Source/file identities are retained declarations unless separately authenticated against installed context.\n'
            + 'Receiver checking is local; no remote execution, payment, energy measurement or organizational independence is inferred.\n',
        '03_benchmark_tasks/spec.json': render({charters: inspection.discovery.attempts.map(item => ({attempt: item.attempt,
            bindings: item.bindings, charter: item.charter})), futureTaskAttachments: data.futureEvaluations.length,
        realTaskAttachments: data.realTaskRecords.length, exposure: 'Public seeded synthetic protocol; not secret external benchmarks'}),
        '04_baselines/comparison.json': render({campaigns: inspection.discovery.campaigns.map(item => ({
            campaignDigest: item.campaignDigest, comparisons: item.result.comparisons})),
        futureTaskAttachments: data.futureEvaluations.length, unmeasured: unknown}),
        '05_agialpha_runs/run.json': render(run),
        '06_proof_bundles/capability.json': render({campaigns: inspection.discovery.campaigns.map(item => ({
            campaignDigest: item.campaignDigest, artifacts: item.artifacts})), sources: data.attachments.sources,
        receiverReceipts: receipts, historyAttachments: data.historyAttachments.map(item => ({campaignDigest: item.campaignDigest,
            kind: item.kind, recordDigest: item.recordDigest, eventDigest: item.eventDigest})), importedAuthority: 'none'}),
        '07_replay_logs/replay.json': render({method: 'Reconstruct every original workspace event and finite campaign; rebuild every docket section',
            head: inspection.head, eventDigests: data.value.events.map(item => item.digest),
            sourceContext: 'retained declarations; optional independently installed expectations checked separately',
            independentOrganization: false, cachedOrCurrentReplayWork: 'not-separately-metered', rawReceiptDigests: receipts.map(item => item.receiptDigest)}),
        '08_cost_ledgers/costs.json': render({construction: data.construction, recordedReplay: data.recordedReplay,
            knownHistoryTotal: data.total, accounting: 'Each completed campaign increment and its recorded verification counted once; ancestor cumulative totals are descriptive and never summed again',
            historyTotalScope: 'Discovery Lab campaign construction and its recorded verification only; other metric schemas remain separate below',
            legacyWitnessCosts: data.legacyWitnessCosts, realTaskContractChecks: data.realTaskChecks,
            peakMetrics: ['memoryWords', 'workerSlots'], unresolvedAttempts: unresolved,
            unresolvedFutureAttempts: data.unresolvedFuture,
            knownAttemptOutcomesComplete: unresolved.length === 0 && data.unresolvedFuture.length === 0,
            totalComplete: false, totalCompletenessReason: 'Review, coordination, energy, monetary and aggregate export/reopen overhead remain unmeasured',
            receiverInspectionByRoute: data.routeCosts, fleetLocalReviewObservations: data.fleetCosts,
            fleetAccounting: 'Separate observed invocation costs, not combined with commission routes or a complete system total',
            commissions: data.commissions, currenciesCombined: false,
            futureTaskCosts: data.futureEvaluations.map(item => ({eventDigest: item.eventDigest,
                freezeDigest: item.result.freezeDigest, taskBankDigest: item.result.taskBankDigest,
                summaries: item.result.summaries, accounting: item.result.accounting})),
            evidencePerFullReplayLogical: data.evidenceReplayLogical,
            evidenceReplayScope: 'One complete attached-evidence replay; cumulative number of exports/reopens and wall time remain unmeasured',
            amortization: 'No universal amortization assumed; inspect each attached future-task comparison', unmeasured: unknown}),
        '09_safety_ledgers/safety.json': render({authority: [], transactionSubmission: 'not-performed-by-docket',
            importedCodeExecution: false, rollback: 'Prior accepted campaigns and rejected/inconclusive attempts remain in the original history',
            unresolvedAttempts: unresolved, unresolvedFutureAttempts: data.unresolvedFuture,
            promotion: 'external explicit authorization required; no imported self-promotion'}),
        '10_validator_reports/review.json': render({producer: 'Discovery Lab finite stage builders',
            checker: 'Installed separately implemented finite checker and deterministic replay',
            organizationalIndependence: 'not-established', receiverReceipts: receipts.map(item => ({
                receiptDigest: item.receiptDigest, state: item.state, authenticity: item.authenticity})),
            externalReview: 'pending', realTaskExecution: 'not-established'}),
        '11_alpha_wu_calibration/status.json': render({status: 'uncalibrated', alphaWU: null,
            reason: 'No external workload calibration or verifier; abstract resource counts are not alpha-WU or currency'}),
        '12_summary_tables/outcome.json': render({campaigns, unresolved, unresolvedFuture: data.unresolvedFuture,
            receiverReceiptCount: receipts.length,
            futureEvaluationCount: data.futureEvaluations.length, realTaskRecordCount: data.realTaskRecords.length,
            operationalAcceptance: 'not-established', authority: 'none', unknown})
    };
    const checksums = {};
    for (const path of DOCKET_PATHS) checksums[path] = await rawDigest(files[path]);
    return {schema: DOCKET_SCHEMA, format: 'bounded-canonical-file-map', files, checksums};
}

export async function createDiscoveryDocket(value, attachments, options = {}) {
    options = capturedOptions(options);
    const captured = copy(value);
    const bound = attachments === undefined ? await emptyDocketAttachments(captured) : copy(attachments);
    const docket = await filesFor(captured, bound, options);
    // The complete export shares the established two-megabyte bounded input language.
    return copy(docket);
}
export async function exportDiscoveryDocket(value, attachments, options = {}) {
    return contract.canonical(await createDiscoveryDocket(value, attachments, options));
}
export async function verifyDiscoveryDocket(input, options = {}) {
    options = capturedOptions(options);
    const docket = typeof input === 'string' ? contract.parseBounded(input) : copy(input);
    need(exact(docket, ['schema', 'format', 'files', 'checksums']) && docket.schema === DOCKET_SCHEMA
        && docket.format === 'bounded-canonical-file-map' && exact(docket.files, DOCKET_PATHS)
        && exact(docket.checksums, DOCKET_PATHS), 'Docket paths, format or fields differ.');
    for (const path of DOCKET_PATHS) {
        need(typeof docket.files[path] === 'string' && docket.checksums[path] === await rawDigest(docket.files[path]),
            'Docket file checksum differs: ' + path);
    }
    const run = contract.parseBounded(docket.files['05_agialpha_runs/run.json']);
    need(exact(run, ['schema', 'workspace', 'attachments']) && run.schema === DOCKET_SCHEMA, 'Unsupported docket run.');
    const expected = await filesFor(run.workspace, run.attachments, options);
    need(same(docket, expected), 'Docket content differs from finite replay or omits retained evidence.');
    return {verified: true, scope: 'complete-local-synthetic-history-and-bound-attachments',
        missionId: run.workspace.missionId, workspaceHead: run.attachments.workspaceHead,
        authority: 'none', externalReplication: 'pending', settlement: 'not-performed'};
}
