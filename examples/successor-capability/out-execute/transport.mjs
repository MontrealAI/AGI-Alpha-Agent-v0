// SPDX-License-Identifier: Apache-2.0
/** Inert compatibility proposal. No existing target accepts this new schema yet. */
import {canonical} from '../constructor.mjs';
import {sha256} from '../capability-package.mjs';
import {inspectArchive} from './engine.mjs';
import {fields, same, clone, requireValue, seal, checkSeal, bounded} from './model.mjs';
export const REQUEST_SCHEMA = 'out-execute-commissioning-draft/v1';
export const TARGETS = Object.freeze({
    'manager-usdc': {repository: 'MontrealAI/AGIJobManager', commit: '4d4c32685eebf23b0aa35dbb45abe23ac8a261cb',
        path: 'site/assets/successor/jobs.mjs', interface: 'agijobmanager/successor-improvement-draft/v1',
        asset: 'USDC', decimals: 6, role: 'bounded-construction-or-independent-evaluation'},
    'jobs-agialpha': {repository: 'MontrealAI/AGIJobsv0', commit: '83065adf18a6ee987f8fa479a496a052d35db682',
        path: 'packages/successor-core/src/compiler.mjs', interface: 'SealedWorkOrder / JobGraph',
        asset: 'AGIALPHA', decimals: 18, role: 'bounded-construction-or-independent-evaluation'},
    'fleet-qualified-review': {repository: 'MontrealAI/AGI-Fleet-Linux', commit: '45759fb096faf8988f58ae5ea71248d0f35a97c7',
        path: 'local-runtime/schemas/client-v1.d.ts', interface: 'local-task/admission/prepared-grant',
        asset: null, decimals: null, role: 'separately-qualified-execution-and-review'}
});
const constraints = Object.freeze({authority: 'none', signed: false, funded: false, executionApproved: false,
    independentProof: false, settlement: 'not-connected', spendBaseUnits: '0', reservations: [],
    deployments: [], transactions: [], modelCalls: 0, tokenConversion: 'none', membershipChanges: []});

export async function prepareWorkRequest(archiveRaw, {projectId, target, expectedSource, purpose = 'independent-evaluation'} = {}) {
    requireValue(typeof projectId === 'string' && /^[a-zA-Z0-9-]{8,80}$/.test(projectId), 'PROJECT_ID');
    requireValue(Object.hasOwn(TARGETS, target) && ['bounded-construction', 'independent-evaluation'].includes(purpose), 'TARGET_PURPOSE');
    const archive = bounded(archiveRaw);
    const inspected = await inspectArchive(archive), candidate = inspected.archive?.completions.at(-1);
    requireValue(candidate && expectedSource && same(candidate.source, expectedSource), 'INDEPENDENT_EXPECTED_SOURCE_REQUIRED');
    const raw = canonical(archive);
    const body = {schema: REQUEST_SCHEMA, projectId, purpose, target, targetInterface: clone(TARGETS[target]),
        archiveRaw: raw, archiveSha256: await sha256(raw), candidateDigest: candidate.digest,
        incumbentDigest: candidate.parentDigest, expectedSource: clone(expectedSource),
        acceptance: {scope: 'complete-declared-finite-model-only', independentEvaluator: null, acceptanceOwner: null,
            baseline: 'full-enumeration-and-equally-capable-incremental-contracts',
            obligations: ['Every factor and domain bound to current source', 'All profile rows and witnesses independently checked',
                'Current whole artifact accepted', 'Failures, unknowns and complete cost ledgers retained',
                'No source hash treated as behavioral or operational proof']},
        adapterStatus: target === 'fleet-qualified-review' ? 'BLOCKED_UNPROVISIONED_NOT_EXECUTABLE' : 'DRAFT_NEW_SCHEMA_ADAPTER_NOT_INSTALLED',
        unresolved: ['Explicit owner, producer and independent reviewer assignment', 'Exact target adapter and runtime qualification',
            'Current source/package/host admission and expiry', 'Rights and protocol-specific membership checks',
            'External budget, acceptance and any action authorization remain separate'],
        limits: clone(constraints)};
    return seal(body);
}

export async function inspectWorkRequest(input, {expectedSource, projectId, target} = {}) {
    const request = bounded(input);
    fields(request, ['schema', 'projectId', 'purpose', 'target', 'targetInterface', 'archiveRaw', 'archiveSha256',
        'candidateDigest', 'incumbentDigest', 'expectedSource', 'acceptance', 'adapterStatus', 'unresolved', 'limits', 'digest']);
    requireValue(request.schema === REQUEST_SCHEMA && request.projectId === projectId && request.target === target,
        'EXPECTED_REQUEST_CONTEXT_REQUIRED');
    const rebuilt = await prepareWorkRequest(request.archiveRaw, {projectId, target, expectedSource, purpose: request.purpose});
    requireValue(same(request, rebuilt), 'WORK_REQUEST_BINDING'); await checkSeal(request);
    return {request, authority: [], executable: false, externalEvidence: 'not-established'};
}
