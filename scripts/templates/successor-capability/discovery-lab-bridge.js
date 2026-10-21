// SPDX-License-Identifier: Apache-2.0
// One store, one existing workspace hash chain, and explicit protected recovery.
var discoveryUi = null;
let discoveryRestored = false;
const discoveryListeners = new Set();
function aggregateDiscoveryAccount(attempts) {
    const recorded = {};
    const unknownReservations = [];
    let elapsedMs = 0;
    for (const attempt of attempts) {
        if (!attempt.result) { unknownReservations.push({attempt: attempt.attempt, reservation: attempt.reservation}); continue; }
        for (const resource of [attempt.result.resources, attempt.recordedVerification]) {
            for (const [key, value] of Object.entries(resource || {})) {
                recorded[key] = ['memoryWords', 'workerSlots'].includes(key)
                    ? Math.max(recorded[key] || 0, value) : (recorded[key] || 0) + value;
            }
        }
        elapsedMs += attempt.elapsedReceipt.elapsedMs;
    }
    return {recordedConstructionAndVerification: recorded, measuredConstructionAndVerificationMs: elapsedMs,
        currentSessionInspectionReplay: discoveryHistory.auditSnapshot(), unknownReservations,
        units: {acquisitions: 'simulated readings', search: 'declared logical work', checking: 'finite predicates',
            memoryWords: 'peak integer slots', storageBytes: 'retained serialized bytes', workerSlots: 'peak concurrent workers',
            installations: 'synthetic installation actions'},
        notice: 'Current-session replay is separately metered. Unknown interrupted work retains its reservation; it is not zero. Save an account receipt to retain this session observation.'};
}
const discoveryBridge = {
    reservePlan(charter) { return discoveryHistory.reservationFor(discoveryLab.validateCharter(charter)); },
    async state() {
        if (ready && !current && !pending && !discoveryRestored && store) {
            discoveryRestored = true;
            const originalStore = store;
            const originalDraft = canonical(rawDraft());
            const originalStoredRevision = storedRevision;
            let id = null;
            try { id = localStorage.getItem('agialpha.discovery-lab.last-workspace'); } catch { /* Pointer only; history remains in the existing store. */ }
            if (id) {
                const envelope = await originalStore.get(id);
                if (envelope) {
                    const restored = await inspectStored(envelope);
                    if (store !== originalStore || current !== null || pending || storedRevision !== originalStoredRevision
                        || canonical(rawDraft()) !== originalDraft) return this.state();
                    current = restored.workspace; inspected = restored.inspection; storedRevision = restored.revision;
                    fillBrief(inspected.latest.brief, inspected.latest.experiment);
                    renderVersions();
                }
            }
        }
        const campaigns = inspected?.discovery?.attempts || [];
        const capacity = current ? discoveryHistory.historyCapacity(current) : {canRun: true};
        const originalDraftModified = current === null && canonical(rawDraft()) !== canonical({
            brief: capability.DEFAULT_BRIEF, witnessEnabled: false, experimentText: defaultExperimentText(), successorReason: ''});
        const locked = !!pending || originalDraftModified || (current !== null && (dirty || successorEditing)) || busy || !capacity.canRun;
        const reason = pending ? 'This exact history is not confirmed saved. Use the protected recovery export or retry below before more work.'
            : originalDraftModified ? 'Your original proposal contains unsaved edits. Save or export that draft before creating the lab history.'
            : current && (dirty || successorEditing) ? 'Save or restore the edited original capability brief before adding a lab campaign.'
            : !capacity.canRun ? 'History capacity is reserved for recovery. Export this complete history before starting another one.'
            : !ready ? 'Preparing the existing capability history…' : '';
        return {ready, locked, reason, campaigns, workspaceId: current?.missionId || null,
            resourceAccount: aggregateDiscoveryAccount(campaigns)};
    },
    async run(charter, {parent = null} = {}) {
        const state = await this.state();
        if (!state.ready || state.locked || !$('lab-public-confirmation').checked) {
            throw Error(state.reason || 'Confirm the supplied public synthetic scope before construction.');
        }
        busy = true; clearError(); controls();
        try {
            if (!current) {
                const brief = {...capability.DEFAULT_BRIEF, title: 'Build the Next Discovery Lab',
                    objective: 'Qualify a finite synthetic experimentation platform while preserving existing services.'};
                await persist(await capability.createWorkspace(brief, null), null, null);
            }
            if (inspected.discovery.active) {
                const stopped = await capability.recordDiscoveryEvent(current, 'lab-stopped',
                    discoveryHistory.stoppedPayload(inspected.discovery.active.attempt,
                        'An earlier reserved attempt has no terminal record. This explicit new run retains its unknown work reservation.'));
                await persist(stopped, storedRevision, current);
            }
            if (!discoveryHistory.historyCapacity(current).canRun) throw Error('Not enough history capacity for a complete attempt and recovery.');
            const selectedParent = parent ? discoveryHistory.selectCampaign(inspected.discovery.campaigns, parent) : null;
            const parentDigest = selectedParent?.campaignDigest || null;
            if (selectedParent && (selectedParent.state !== 'accepted'
                || !['modelDigest', 'sourceDigest', 'evaluatorDigest'].every(key => selectedParent.bindings[key] === DISCOVERY_SOURCES[key]))) {
                throw Error('The selected parent is not currently qualified under these installed sources.');
            }
            const start = await discoveryHistory.startPayload(current, charter, DISCOVERY_SOURCES, parentDigest);
            let next = await capability.recordDiscoveryEvent(current, 'lab-started', start);
            await persist(next, storedRevision, current);
            // The reservation must be confirmed before any construction or semantic verification.
            if (pending) throw Error('The construction reservation was not saved. No construction was started.');
            try { localStorage.setItem('agialpha.discovery-lab.last-workspace', current.missionId); } catch { /* A failed pointer never discards history. */ }
            const active = inspected.discovery.active;
            const began = performance.now();
            let result, verification;
            try {
                result = discoveryLab.runCampaign(start.charter, {parent: active.parent?.result || null});
                verification = discoveryHistory.verifyForRecording(start.charter, result, active.parent?.result || null);
                if (!verification.verified) throw Error('Current finite verification did not complete.');
            } catch (error) {
                next = await capability.recordDiscoveryEvent(current, 'lab-stopped',
                    discoveryHistory.stoppedPayload(start.attempt, String(error.message), 'inconclusive'));
                await persist(next, storedRevision, current);
                throw error;
            }
            const payload = await discoveryHistory.completedPayload(start.attempt, result,
                Math.ceil(performance.now() - began), verification.verificationResources);
            next = await capability.recordDiscoveryEvent(current, 'lab-completed', payload);
            await persist(next, storedRevision, current);
            return inspected.discovery.campaigns.at(-1);
        } finally {
            busy = false; render();
            for (const listener of discoveryListeners) listener();
        }
    },
    async workRequest(record, route) {
        const state = await this.state();
        if (!state.ready || state.locked || !record?.campaignDigest) throw Error('A saved current campaign is required.');
        const currentRecord = discoveryHistory.selectCampaign(inspected.discovery.campaigns, record);
        if (!currentRecord || currentRecord.state !== 'accepted'
            || !['modelDigest', 'sourceDigest', 'evaluatorDigest'].every(key => currentRecord.bindings[key] === DISCOVERY_SOURCES[key])) {
            throw Error('This campaign does not match the currently installed model/source/evaluator.');
        }
        const chain = [];
        for (let item = currentRecord; item; item = item.parent) chain.push(item.charter);
        const resourceLimits = {acquisitions: 0, search: 0, checking: 10000, memoryBytes: 10000000,
            storageBytes: 4000000, workerCapacity: 4, installations: 0, elapsedMs: 120000};
        for (const charter of chain) {
            for (const key of ['acquisitions', 'search', 'checking', 'installations']) resourceLimits[key] += charter.budget[key];
        }
        return discoveryHistory.workRequest(currentRecord, route, resourceLimits);
    },
    async accountReceipt() {
        const state = await this.state();
        return {schema: 'discovery-lab-account-receipt/v1', workspaceId: state.workspaceId,
            revision: current?.revision ?? null, sources: DISCOVERY_SOURCES, account: state.resourceAccount,
            scope: 'Recorded synthetic construction, verification and current-session inspection. Not currency or external authority.'};
    },
    subscribe(listener) { discoveryListeners.add(listener); return () => discoveryListeners.delete(listener); }
};
const renderWithoutDiscovery = render;
render = function () {
    renderWithoutDiscovery();
    if (discoveryUi) void discoveryUi.refresh();
};
discoveryUi = mountDiscoveryLab({runtime: discoveryLab, history: discoveryBridge});
