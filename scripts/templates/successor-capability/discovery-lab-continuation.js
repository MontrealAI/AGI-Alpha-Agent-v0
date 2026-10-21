// SPDX-License-Identifier: Apache-2.0
// Append-only evidence steps share the existing store, recovery controls and mission chain.
(() => {
    const el = id => document.getElementById('lab-' + id);
    if (!el('freeze-future')) return;
    let notice = '', inFlight = false, inventory = null, continuationRecovery = null, recoveryPrepared = false;
    const recoveryExport = document.createElement('button'), recoveryConfirm = document.createElement('button');
    recoveryExport.type = 'button'; recoveryExport.id = 'lab-future-recovery-export';
    recoveryExport.textContent = 'Download exact future-result recovery';
    recoveryConfirm.type = 'button'; recoveryConfirm.id = 'lab-future-recovery-confirm';
    recoveryConfirm.textContent = 'I retained this exact result';
    el('future-report').after(recoveryExport, recoveryConfirm);
    const sourceKeys = ['modelDigest', 'sourceDigest', 'evaluatorDigest'];
    const saved = () => ready && current && inspected && storedRevision !== null
        && !pending && !dirty && !successorEditing;
    function selection() {
        return [...(inspected?.discovery?.campaigns || [])].reverse().find(record => record.state === 'accepted'
            && record.lineageQualified !== false && sourceKeys.every(key => record.bindings[key] === DISCOVERY_SOURCES[key])) || null;
    }
    function evidence(record, kind) {
        return (inspected?.discovery?.attachments || []).find(item => item.campaignDigest === record?.campaignDigest && item.kind === kind);
    }
    function capacity(base, requiredEvents = 3) {
        if (!base) return false;
        const room = discoveryHistory.historyCapacity(base);
        let nodes = 0;
        const visit = value => {
            if (++nodes > 80000) return;
            if (value && typeof value === 'object') for (const child of Object.values(value)) visit(child);
        };
        visit(base);
        return room.remainingBytes >= room.reportReserveBytes && room.remainingEvents >= requiredEvents && nodes <= 80000;
    }
    function requireCapacity(base, requiredEvents = 3) {
        if (!capacity(base, requiredEvents)) throw Error('History space cannot reserve the complete result and terminal recovery record. Export this complete history before more work.');
    }
    function refreshContinuation() {
        const record = selection(), freeze = evidence(record, 'future-freeze');
        const bank = evidence(record, 'future-task-bank'), completed = evidence(record, 'future-evaluation');
        const executionHistory = (inspected?.discovery?.attachments || []).filter(item => item.campaignDigest === record?.campaignDigest
            && ['future-run-reserved', 'future-run-stopped'].includes(item.kind)).map(item => ({kind: item.kind,
            record: item.record, recordDigest: item.recordDigest, eventDigest: item.eventDigest,
            resolution: item.resolution || null}));
        const idle = !busy && !inFlight, usable = saved() && idle && !!record && !continuationRecovery;
        const unresolvedRun = executionHistory.some(item => item.kind === 'future-run-reserved' && !item.resolution);
        const room = capacity(current, bank ? unresolvedRun ? 3 : 2 : freeze ? 3 : 4);
        el('freeze-future').disabled = !usable || !capacity(current, 4) || !!freeze;
        el('commit-future').disabled = !usable || !room || !freeze || !!bank;
        el('run-future').disabled = !usable || !room || !bank || !!completed;
        el('future-seed').disabled = !usable || !freeze || !!bank;
        el('future-budget').disabled = !usable || !bank || !!completed;
        el('export-docket').disabled = !idle || !current || !inspected;
        if (el('prepare-real-task')) el('prepare-real-task').disabled = !usable || !capacity(current, 2) || !!evidence(record, 'real-task-contract');
        if (el('import-receipt')) el('import-receipt').disabled = !saved() || !idle || !!continuationRecovery
            || !!inspected?.discovery?.active || !capacity(current, 2);
        recoveryExport.hidden = !continuationRecovery; recoveryConfirm.hidden = !continuationRecovery;
        recoveryExport.disabled = !idle || !continuationRecovery;
        recoveryConfirm.disabled = !idle || !continuationRecovery || !recoveryPrepared;
        el('future-status').textContent = continuationRecovery
            ? 'The exact computed result is protected here because its history event could not be saved. Download and retain this recovery before further continuation work. Its reservation and unknown additional work remain retained.'
            : pending ? 'This exact candidate history is not confirmed saved. Retain the protected recovery export or retry saving before continuing.'
                : !room && record && !completed ? 'History capacity must reserve the complete result and a terminal recovery record. Export the complete history before more work.'
                    : notice || (!record ? 'Construct and save an accepted six-stage campaign first. These steps use the latest saved campaign under the installed sources.'
                : completed ? 'The complete future-task protocol is saved. Earlier failures and costs remain in this mission history.'
                    : bank ? 'The whole future-task bank is committed in saved history. Execute these unchanged tasks under one matched allowance.'
                        : freeze ? 'Executable, environment, obligations and evaluator are frozen in saved history. Commit future tasks next.'
                            : 'Freeze the latest saved accepted campaign before generating or supplying future task specifications. Extra UI admission work and crash costs are not assumed to be zero.');
        if (completed) {
            el('future-report').textContent = JSON.stringify({evaluation: completed.record, executionHistory}, null, 2);
            el('future-report').hidden = false;
        } else {
            el('future-report').textContent = bank ? JSON.stringify({freeze: freeze.record, futureTaskBank: bank.record, executionHistory,
                execution: 'NOT_RUN; interrupted or unrecorded work has unknown cost until a terminal record exists.'}, null, 2)
                : freeze ? JSON.stringify(freeze.record, null, 2) : '';
            el('future-report').hidden = !freeze;
        }
        if (inventory) el('deployment-summary').textContent = JSON.stringify(inventory, null, 2);
        const prepared = evidence(record, 'real-task-contract');
        if (prepared && el('real-task-report')) {
            el('real-task-report').textContent = JSON.stringify(prepared.record, null, 2);
            el('real-task-report').hidden = false;
        }
    }
    function integerInput(id, maximum) {
        const raw = el(id).value;
        if (!/^(?:0|[1-9][0-9]*)$/.test(raw)) throw Error('Provide a nonnegative whole number for ' + id + '.');
        const value = Number(raw);
        if (!Number.isSafeInteger(value) || value > maximum) throw Error('The ' + id + ' value exceeds its supported bound.');
        return value;
    }
    async function appendEvidence(base, revision, record, kind, data) {
        if (current !== base || storedRevision !== revision || pending) throw Error('History changed before this evidence could be saved.');
        const payload = await discoveryEvidence.evidencePayload(record.campaignDigest, kind, data);
        const next = await capability.recordDiscoveryEvent(base, 'lab-evidence-attached', payload);
        await persist(next, revision, base);
        if (pending) throw Error('The evidence history is protected in memory and is not confirmed saved. Use recovery before continuing.');
        return payload;
    }
    async function action(message, operation) {
        if (busy || inFlight || !saved() || continuationRecovery) return;
        const record = selection();
        if (!record) { notice = 'Save an accepted campaign under the installed sources first.'; refreshContinuation(); return; }
        const base = current, revision = storedRevision;
        busy = true; inFlight = true; notice = message; render();
        try { await operation({base, revision, record}); }
        catch (error) {
            notice = String(error?.message || error).slice(0, 1000)
                + ' Prior saved evidence remains retained; interrupted or unrecorded work is not assumed to cost zero.';
        } finally { busy = false; inFlight = false; render(); }
    }
    el('freeze-future').addEventListener('click', () => void action('Checking and freezing the latest saved accepted capability…',
        async ({base, revision, record}) => {
            requireCapacity(base, 4);
            if (evidence(record, 'future-freeze')) throw Error('This campaign already has a saved freeze.');
            const capsule = await discoveryEvidence.freezeRecord(record);
            await appendEvidence(base, revision, record, 'future-freeze', discoveryEvidence.freezeReference(capsule));
            notice = 'Freeze saved. Future tasks have not been generated or executed. Commit the complete bank next.';
        }));
    el('commit-future').addEventListener('click', () => {
        let seed;
        try { seed = integerInput('future-seed', 0xffffffff); }
        catch (error) { notice = error.message; refreshContinuation(); return; }
        void action('Committing the complete public future-task bank after the saved freeze…', async ({base, revision, record}) => {
            requireCapacity(base);
            const frozen = evidence(record, 'future-freeze');
            if (!frozen || evidence(record, 'future-task-bank')) throw Error('One saved freeze and no previous task bank are required.');
            const bank = await discoveryFuture.publicFutureBank(frozen.capsule, seed);
            await appendEvidence(base, revision, record, 'future-task-bank', bank);
            notice = 'Task bank saved. Public seeded tasks are synthetic protocol holdouts; they are not a secret external benchmark.';
        });
    });
    el('run-future').addEventListener('click', () => {
        let allowance;
        try { allowance = integerInput('future-budget', 10_000_000); }
        catch (error) { notice = error.message; refreshContinuation(); return; }
        void action('Executing the unchanged committed bank and retaining every treatment, failure and cost…', async ({base, revision, record}) => {
            const bankRecord = evidence(record, 'future-task-bank');
            if (!bankRecord || evidence(record, 'future-evaluation')) throw Error('A saved task bank without a completed evaluation is required.');
            const interrupted = (inspected.discovery.attachments || []).find(item => item.kind === 'future-run-reserved'
                && item.campaignDigest === record.campaignDigest && !item.resolution);
            requireCapacity(base, interrupted ? 3 : 2);
            // Inspection stores inert bank bytes. Re-admit those exact bytes under the retained verified freeze.
            const bank = await discoveryFuture.commitFutureTasks(bankRecord.capsule, bankRecord.record.tasks);
            if (canonical(bank) !== canonical(bankRecord.record)) throw Error('The saved future-task commitment no longer matches.');
            if (interrupted) {
                await appendEvidence(base, revision, record, 'future-run-stopped', {
                    schema: 'discovery-lab-future-stop/v1', reservationDigest: interrupted.recordDigest,
                    reason: 'An earlier saved future-task reservation has no terminal record. Its unknown spent work remains retained.',
                    spent: 'unknown-reservation-retained'});
                base = current; revision = storedRevision;
            }
            const reserved = await appendEvidence(base, revision, record, 'future-run-reserved', {
                schema: 'discovery-lab-future-reservation/v1', taskBankDigest: bank.digest,
                perTaskWorkLimit: allowance, attempt: 'future-' + crypto.randomUUID()});
            let result = null;
            try {
                result = await discoveryFuture.evaluateFutureTasks(bankRecord.capsule, bank, {perTaskWorkLimit: allowance});
                await appendEvidence(current, storedRevision, record, 'future-evaluation', result);
            } catch (error) {
                if (result && !pending) {
                    continuationRecovery = {schema: 'discovery-lab-future-result-recovery/v1', workspace: current,
                        campaignDigest: record.campaignDigest, reservation: reserved, taskBank: bank, result,
                        authority: false, scope: 'Exact computed result; not recorded in mission history or authorized for promotion.'};
                    recoveryPrepared = false;
                }
                if (!pending && saved()) {
                    await appendEvidence(current, storedRevision, record, 'future-run-stopped', {
                        schema: 'discovery-lab-future-stop/v1', reservationDigest: reserved.recordDigest,
                        reason: String(error?.message || error).slice(0, 1000), spent: 'unknown-reservation-retained'});
                }
                throw error;
            }
            notice = 'Complete comparison saved. Inspect warm ties, cheaper static alternatives, shifted-regime failures and inconclusive budgets below. No promotion or settlement occurred.';
        });
    });
    el('export-docket').addEventListener('click', () => {
        if (busy || inFlight || !current || !inspected) return;
        const captured = current;
        busy = true; inFlight = true; notice = 'Replaying the complete history and preparing its 13-section evidence docket…'; render();
        void (async () => {
            try {
                const text = await discoveryDocket.exportDiscoveryDocket(captured);
                download(text, captured.missionId + '-discovery-evidence-docket.json');
                notice = 'Docket download prepared with the complete history and explicit missing evidence. Keep the exact file for replay.';
            } catch (error) { notice = 'Docket export could not complete: ' + String(error?.message || error).slice(0, 800); }
            finally { busy = false; inFlight = false; render(); }
        })();
    });
    if (el('prepare-real-task')) el('prepare-real-task').addEventListener('click', () => {
        const route = document.getElementById('lab-route')?.value || 'USDC';
        void action('Preparing a bounded public-software task contract without launching any model or runtime…', async ({base, revision, record}) => {
            requireCapacity(base, 2);
            if (evidence(record, 'real-task-contract')) throw Error('This campaign already has a prepared real-task contract.');
            const limits = {acquisitions: 0, search: 0, checking: 10000 + discoveryContract.DISCOVERY_LAB_INSPECTION_CHECKS,
                memoryBytes: 10000000, storageBytes: 4000000, workerCapacity: 4, installations: 0, elapsedMs: 120000};
            for (let ancestor = record; ancestor; ancestor = ancestor.parent) {
                for (const key of ['acquisitions', 'search', 'checking', 'installations']) limits[key] += ancestor.charter.budget[key];
            }
            const request = await discoveryHistory.workRequest(record, route, limits);
            const proposal = await discoveryRealTask.createRealTaskRecord({workRequest: request,
                workspaceHead: base.events.at(-1).digest, campaignDigest: record.campaignDigest,
                publicSource: 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0',
                specification: {multiplier: '2', offset: '1', maxBatchRows: 32},
                resourceLimits: {acquisitions: 100, search: 100000, checking: 100000, memoryBytes: 10000000,
                    storageBytes: 1000000, workerCapacity: 1, installations: 0, elapsedMs: 60000},
                adapterSources: REAL_TASK_SOURCES});
            await appendEvidence(base, revision, record, 'real-task-contract', proposal);
            notice = 'Public-software contract saved as NOT_RUN. The source URL is a declared reference; no model call, source download, executable invocation, payment or settlement occurred.';
        });
    });
    if (el('import-receipt')) el('import-receipt').addEventListener('change', () => {
        const input = el('import-receipt'), file = input.files?.[0];
        if (!file || busy || inFlight || !saved() || continuationRecovery) return;
        const base = current, revision = storedRevision;
        busy = true; inFlight = true;
        el('receipt-status').textContent = 'Inspecting the original receiver bytes against this retained mission…'; render();
        void (async () => {
            try {
                requireCapacity(base, 2);
                if (inspected.discovery.active) throw Error('Resolve the active reserved campaign before importing a receipt.');
                if (file.size > 2000000) throw Error('Receiver receipt wrapper exceeds the two-megabyte input bound.');
                const wrapper = discoveryContract.parseBounded(await file.text());
                if (typeof wrapper.raw !== 'string') throw Error('A wrapper with original raw receiver bytes is required.');
                const receipt = discoveryContract.parseBounded(wrapper.raw);
                const bindings = discoveryContract.validateBindings(receipt.bindings);
                const matching = inspected.discovery.campaigns.filter(record => record.state === 'accepted'
                    && record.lineageQualified !== false && canonical(record.bindings) === canonical(bindings));
                if (matching.length !== 1) throw Error('The receipt does not identify one retained accepted source-bound campaign.');
                await appendEvidence(base, revision, matching[0], 'receiver-receipt', wrapper);
                el('receipt-status').textContent = 'Receiver receipt retained in this mission with original raw bytes. Source context is unattested; imported evidence grants no execution, payment, promotion or settlement authority.';
            } catch (error) {
                el('receipt-status').textContent = 'Receiver receipt rejected: ' + String(error?.message || error).slice(0, 1000)
                    + (pending ? ' The exact pending history remains protected by recovery.' : ' The saved mission was preserved.');
            } finally { input.value = ''; busy = false; inFlight = false; render(); }
        })();
    });
    recoveryExport.addEventListener('click', () => {
        if (!continuationRecovery || busy || inFlight) return;
        download(JSON.stringify(continuationRecovery, null, 2), continuationRecovery.workspace.missionId + '-future-result-recovery.json');
        recoveryPrepared = true; refreshContinuation();
    });
    recoveryConfirm.addEventListener('click', () => {
        if (!continuationRecovery || !recoveryPrepared || busy || inFlight) return;
        continuationRecovery = null; recoveryPrepared = false;
        notice = 'You acknowledged retaining the exact external result. Its earlier reservation remains in history; an unrecorded result does not become accepted history by acknowledgement.';
        refreshContinuation();
    });
    window.addEventListener('beforeunload', event => {
        if (!continuationRecovery) return;
        event.preventDefault(); event.returnValue = '';
    });
    const previousRender = render;
    render = function () { previousRender(); refreshContinuation(); };
    discoveryBridge.subscribe(refreshContinuation);
    void discoveryDeployments.loadDeploymentInventory(DEPLOYMENT_INVENTORY).then(handle => {
        inventory = discoveryDeployments.deploymentSummary(handle); refreshContinuation();
    }).catch(error => {
        el('deployment-summary').textContent = 'Deployment inventory unavailable: ' + String(error?.message || error)
            + '. Live compatibility and operational readiness remain unestablished.';
    });
    refreshContinuation();
})();
