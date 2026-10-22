// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as workspace from './workspace.mjs';
import * as history from './discovery-lab-history.mjs';
import * as runtime from './discovery-lab.mjs';
import * as contract from './discovery-lab-contract.mjs';
import * as docket from './discovery-lab-docket.mjs';
import * as evidence from './discovery-lab-evidence-history.mjs';
import * as future from './discovery-lab-future.mjs';
import * as realTask from './discovery-lab-real-task.mjs';
const sources = {modelDigest: '1'.repeat(64), sourceDigest: '2'.repeat(64), evaluatorDigest: '3'.repeat(64)};
const copy = value => JSON.parse(contract.canonical(value));
async function campaign(input = null, charter = runtime.DEFAULT_CHARTER, parentDigest = null) {
    let value = input || await workspace.createWorkspace();
    const start = await history.startPayload(value, charter, sources, parentDigest);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    const inspection = await workspace.inspectWorkspace(value), parent = inspection.discovery.active.parent?.result || null;
    const result = runtime.runCampaign(charter, {parent});
    const verified = runtime.verifyCampaign(charter, result, {parent});
    value = await workspace.recordDiscoveryEvent(value, 'lab-completed',
        await history.completedPayload(start.attempt, result, 1, verified.verificationResources));
    return {value, record: (await workspace.inspectWorkspace(value)).discovery.campaigns.at(-1)};
}
const vector = () => Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 0]));
const receiverSource = {repository: 'MontrealAI/AGIJobManager', commit: 'a'.repeat(40), tree: 'b'.repeat(40),
    adapterSha256: 'c'.repeat(64), contractSha256: 'd'.repeat(64)};
async function modeledReceipt(record, route = 'USDC', stage = 'evolve', branch = null) {
    // A transport fixture, explicitly not proof of native/source-authenticated execution.
    const limits = Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, 100_000_000]));
    const request = await history.workRequest(record, route, limits);
    request.stage = stage; request.inputArtifacts = record.artifacts.slice(0, contract.STAGES.indexOf(stage)).map(item => item.digest);
    if (branch !== null) request.commission.branch = branch;
    const original = JSON.stringify(request);
    const native = vector(); native.checking = 10_000;
    for (let parent = record; parent; parent = parent.parent) {
        for (const key of ['acquisitions', 'search', 'checking', 'storageBytes', 'installations']) native[key] += parent.result.resources[key];
        native.memoryBytes = Math.max(native.memoryBytes, parent.result.resources.memoryWords * 8);
        native.workerCapacity = Math.max(native.workerCapacity, parent.result.resources.workerSlots);
    }
    const receiver = {...vector(), checking: 10_000, elapsedMs: 1};
    const reserved = {...receiver, memoryBytes: 1_000_000, storageBytes: 500_000};
    const source = {...receiverSource, repository: route === 'USDC' ? 'MontrealAI/AGIJobManager' : 'MontrealAI/AGIJobsv0'};
    const receipt = {schema: (route === 'USDC' ? 'agijobmanager' : 'agijobsv0') + '/discovery-lab-admission/v1',
        state: 'local-checked', original, requestSha256: await docket.rawDigest(original), bindings: record.bindings,
        commission: request.commission, stage: request.stage, inputArtifacts: request.inputArtifacts,
        payloadDigest: request.payloadDigest, source: {adapterSha256: source.adapterSha256, contractSha256: source.contractSha256},
        checker: {report: {accepted: true, resourceUsed: native, reasons: []}, withinResourceEnvelope: true, nativeWithinResourceEnvelope: true},
        resources: {units: 'transport-fixture; not native execution evidence', receiverUsed: receiver, checkerUsed: native,
            totalUsed: vector(), receiverReservation: reserved,
            nativeLimits: Object.fromEntries(contract.RESOURCE_KEYS.map(key => [key, limits[key] - reserved[key]])), reservationAvailable: true},
        reason: null, lifecycle: {commission: 'DRAFT_NOT_SUBMITTED', reservedBaseUnits: '0', execution: 'unprovisioned',
            review: 'separate-review-required', settlement: 'not-connected'}, capabilityAcceptance: 'not-granted-by-import', authority: 'none'};
    const encode = () => JSON.stringify(receipt);
    for (let index = 0; index < 12; index++) {
        receiver.storageBytes = new TextEncoder().encode(encode()).length;
        receiver.memoryBytes = new TextEncoder().encode(original).length + receiver.storageBytes;
        for (const key of contract.RESOURCE_KEYS) receipt.resources.totalUsed[key] = receiver[key] + native[key];
    }
    return {raw: encode(), source};
}
async function reframeEmbeddedRequest(wrapper, pretty) {
    const receipt = JSON.parse(wrapper.raw), previousBytes = new TextEncoder().encode(receipt.original).length;
    const request = JSON.parse(receipt.original);
    receipt.original = pretty ? JSON.stringify(request, null, 2)
        : JSON.stringify(Object.fromEntries(Object.entries(request).reverse()));
    receipt.requestSha256 = await docket.rawDigest(receipt.original);
    const delta = new TextEncoder().encode(receipt.original).length - previousBytes;
    const workingBytes = receipt.resources.receiverUsed.memoryBytes - receipt.resources.receiverUsed.storageBytes + delta;
    receipt.resources.receiverReservation.memoryBytes += 3 * delta;
    receipt.resources.receiverReservation.storageBytes += 2 * delta;
    for (const key of contract.RESOURCE_KEYS) receipt.resources.nativeLimits[key]
        = request.resourceLimits[key] - receipt.resources.receiverReservation[key];
    for (let index = 0; index < 12; index++) {
        receipt.resources.receiverUsed.storageBytes = new TextEncoder().encode(JSON.stringify(receipt)).length;
        receipt.resources.receiverUsed.memoryBytes = workingBytes + receipt.resources.receiverUsed.storageBytes;
        for (const key of contract.RESOURCE_KEYS) receipt.resources.totalUsed[key]
            = receipt.resources.receiverUsed[key] + receipt.resources.checkerUsed[key];
    }
    return {...wrapper, raw: JSON.stringify(receipt)};
}
async function rehashFiles(value) {
    for (const path of docket.DOCKET_PATHS) value.checksums[path] = await docket.rawDigest(value.files[path]);
    return value;
}

test('complete thirteen-section export replays original rejected/inconclusive/accepted history and exact costs', async () => {
    const low = {...copy(runtime.DEFAULT_CHARTER), budget: {...runtime.DEFAULT_CHARTER.budget, search: 0}};
    const first = await campaign(null, low);
    const second = await campaign(first.value, {...copy(runtime.DEFAULT_CHARTER), memory: 1});
    const third = await campaign(second.value);
    const exported = await docket.createDiscoveryDocket(third.value);
    assert.deepEqual(Object.keys(exported.files).sort(), [...docket.DOCKET_PATHS].sort());
    const outcomes = JSON.parse(exported.files['12_summary_tables/outcome.json']);
    assert.deepEqual(outcomes.campaigns.map(item => item.state), ['inconclusive', 'rejected', 'accepted']);
    const costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.construction.checking, outcomes.campaigns.reduce((total, item) => total + item.construction.checking, 0));
    assert.equal(costs.knownHistoryTotal.checking, costs.construction.checking + costs.recordedReplay.checking);
    assert.equal((await docket.verifyDiscoveryDocket(exported, {expectedWorkspaceHead: third.value.events.at(-1).digest})).verified, true);
    assert.equal((await docket.verifyDiscoveryDocket(await docket.exportDiscoveryDocket(third.value))).authority, 'none');
});

test('omitted files, rehashed erased failures, forged summaries and wrong retained history head reject', async () => {
    const {value} = await campaign();
    const original = await docket.createDiscoveryDocket(value);
    const absent = copy(original); delete absent.files['09_safety_ledgers/safety.json'];
    await assert.rejects(docket.verifyDiscoveryDocket(absent), /paths/);
    for (const path of ['12_summary_tables/outcome.json', '08_cost_ledgers/costs.json', '06_proof_bundles/capability.json']) {
        const changed = copy(original); changed.files[path] = '{}\n';
        await assert.rejects(docket.verifyDiscoveryDocket(await rehashFiles(changed)), /differs from finite replay/);
    }
    await assert.rejects(docket.verifyDiscoveryDocket(original, {expectedWorkspaceHead: 'f'.repeat(64)}), /retained head/);
    const changed = copy(original), run = JSON.parse(changed.files['05_agialpha_runs/run.json']);
    run.workspace.events[2].payload.result.state = 'released';
    changed.files['05_agialpha_runs/run.json'] = contract.canonical(run) + '\n';
    await assert.rejects(docket.verifyDiscoveryDocket(await rehashFiles(changed)), /mismatch|binding/);
});

test('interruption preserves unknown spent work and the original reservation', async () => {
    let value = await workspace.createWorkspace();
    const start = await history.startPayload(value, runtime.DEFAULT_CHARTER, sources);
    value = await workspace.recordDiscoveryEvent(value, 'lab-started', start);
    value = await workspace.recordDiscoveryEvent(value, 'lab-stopped', history.stoppedPayload(start.attempt, 'Operator interruption'));
    const exported = await docket.createDiscoveryDocket(value), costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.totalComplete, false);
    assert.equal(costs.unresolvedAttempts[0].spent, 'unknown');
    assert.deepEqual(costs.unresolvedAttempts[0].reservation, start.reservation);
});

test('raw alternative-route receipts bind exact campaign bytes without double payment or authenticity claims', async () => {
    const {value, record} = await campaign(), attachments = await docket.emptyDocketAttachments(value);
    attachments.receipts = [await modeledReceipt(record), await modeledReceipt(record, 'AGIALPHA')];
    const exported = await docket.createDiscoveryDocket(value, attachments);
    const costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.commissions.length, 1); assert.equal(costs.commissions[0].alternatives.length, 2);
    assert.equal(costs.currenciesCombined, false);
    const proofs = JSON.parse(exported.files['06_proof_bundles/capability.json']);
    assert.equal(proofs.receiverReceipts[0].authenticity, 'not-attested');
    const run = JSON.parse(exported.files['05_agialpha_runs/run.json']);
    assert.equal(run.attachments.receipts[0].raw, attachments.receipts[0].raw);
    assert.equal((await docket.verifyDiscoveryDocket(exported, {expectedReceiverSources: attachments.receipts.map(item => item.source)})).verified, true);
    const duplicate = copy(attachments); duplicate.receipts.push(duplicate.receipts[0]);
    await assert.rejects(docket.createDiscoveryDocket(value, duplicate), /repeats/);
    await assert.rejects(docket.createDiscoveryDocket(value, attachments, {expectedReceiverSources: []}), /installed source/);
});

test('forged receipt status, omitted native charges, swapped source and stale attachment head reject', async () => {
    const {value, record} = await campaign(), attachments = await docket.emptyDocketAttachments(value);
    attachments.receipts = [await modeledReceipt(record)];
    for (const change of [receipt => {receipt.state = 'settled';}, receipt => {receipt.resources.checkerUsed.checking = 0;},
        receipt => {receipt.source.contractSha256 = 'e'.repeat(64);}, receipt => {receipt.authority = 'execute';}]) {
        const changed = copy(attachments), receipt = JSON.parse(changed.receipts[0].raw); change(receipt);
        changed.receipts[0].raw = JSON.stringify(receipt);
        await assert.rejects(docket.createDiscoveryDocket(value, changed));
    }
    await assert.rejects(docket.createDiscoveryDocket(value, {...attachments, workspaceHead: 'e'.repeat(64)}), /head/);
});

test('distinct same-route inspection receipts retain every cost while semantic reframing cannot duplicate work', async () => {
    const {value, record} = await campaign(), attachments = await docket.emptyDocketAttachments(value);
    attachments.receipts = [await modeledReceipt(record, 'USDC', 'learn'), await modeledReceipt(record)];
    const exported = await docket.createDiscoveryDocket(value, attachments);
    const costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    const first = JSON.parse(attachments.receipts[0].raw);
    assert.equal(costs.receiverInspectionByRoute['manager-usdc'].checking, 2 * first.resources.totalUsed.checking);
    assert.equal(costs.commissions.length, 1); assert.equal(costs.commissions[0].alternatives.length, 1);
    assert.equal(costs.commissions[0].alternatives[0].inspectionReceiptIds.length, 2);
    const duplicate = copy(attachments);
    duplicate.receipts.push({...duplicate.receipts[0], raw: JSON.stringify(JSON.parse(duplicate.receipts[0].raw), null, 2)});
    await assert.rejects(docket.createDiscoveryDocket(value, duplicate), /repeats a semantic receipt/);
    const changed = copy(attachments);
    changed.receipts.push(await modeledReceipt(record, 'USDC', 'think', record.attempt + '-another-branch'));
    await assert.rejects(docket.createDiscoveryDocket(value, changed), /frozen branch/);
});
test('same-stage incomplete retry and completed inspection retain distinct native work and costs', async () => {
    const {value, record} = await campaign(), attachments = await docket.emptyDocketAttachments(value);
    const completed = await modeledReceipt(record), incomplete = JSON.parse(completed.raw);
    incomplete.state = 'inconclusive';
    incomplete.checker.report = {accepted: false, resourceUsed: {...vector(), checking: 10_000},
        reasons: ['INSPECTION_PREFLIGHT_CHECK_INCOMPLETE']};
    incomplete.resources.checkerUsed = incomplete.checker.report.resourceUsed;
    for (let index = 0; index < 12; index++) {
        incomplete.resources.receiverUsed.storageBytes = new TextEncoder().encode(JSON.stringify(incomplete)).length;
        incomplete.resources.receiverUsed.memoryBytes = new TextEncoder().encode(incomplete.original).length
            + incomplete.resources.receiverUsed.storageBytes;
        for (const key of contract.RESOURCE_KEYS) incomplete.resources.totalUsed[key]
            = incomplete.resources.receiverUsed[key] + incomplete.resources.checkerUsed[key];
    }
    attachments.receipts = [{...completed, raw: JSON.stringify(incomplete)}, completed];
    const exported = await docket.createDiscoveryDocket(value, attachments);
    const costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.commissions[0].alternatives[0].inspectionReceiptIds.length, 2);
    assert.equal(costs.receiverInspectionByRoute['manager-usdc'].checking,
        incomplete.resources.totalUsed.checking + JSON.parse(completed.raw).resources.totalUsed.checking);
});

test('returned receipt bytes persist in the same history and deduplicate across history plus legacy attachments', async () => {
    const built = await campaign(); let value = built.value;
    const receipt = await modeledReceipt(built.record);
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'receiver-receipt', receipt));
    const reloaded = await workspace.parseWorkspace(contract.canonical(value));
    const inspected = await workspace.inspectWorkspace(reloaded);
    assert.equal(inspected.discovery.attachments[0].record.raw, receipt.raw);
    assert.equal(inspected.discovery.attachments[0].receipt.authenticity, 'not-attested');
    const exported = await docket.createDiscoveryDocket(reloaded);
    assert.equal(JSON.parse(exported.files['12_summary_tables/outcome.json']).receiverReceiptCount, 1);
    assert.equal((await docket.verifyDiscoveryDocket(exported)).verified, true);
    const duplicate = {...receipt, raw: JSON.stringify(JSON.parse(receipt.raw), null, 2)};
    await assert.rejects(workspace.recordDiscoveryEvent(reloaded, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'receiver-receipt', duplicate)), /Duplicate semantic receipt/);
    const external = await docket.emptyDocketAttachments(reloaded); external.receipts = [duplicate];
    await assert.rejects(docket.createDiscoveryDocket(reloaded, external), /repeats a semantic receipt/);
    const otherStage = await modeledReceipt(built.record, 'USDC', 'learn');
    const next = await workspace.recordDiscoveryEvent(reloaded, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'receiver-receipt', otherStage));
    const updated = await docket.createDiscoveryDocket(next), costs = JSON.parse(updated.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.commissions[0].alternatives[0].inspectionReceiptIds.length, 2);
});
test('nested request reframing cannot bypass history or docket exactly-once inspection costs', async () => {
    const built = await campaign(), receipt = await modeledReceipt(built.record);
    const value = await workspace.recordDiscoveryEvent(built.value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'receiver-receipt', receipt));
    for (const pretty of [true, false]) {
        const reframed = await reframeEmbeddedRequest(receipt, pretty);
        await assert.rejects(workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
            await evidence.evidencePayload(built.record.campaignDigest, 'receiver-receipt', reframed)), /Duplicate semantic receipt/);
        const external = await docket.emptyDocketAttachments(value); external.receipts = [reframed];
        await assert.rejects(docket.createDiscoveryDocket(value, external), /repeats a semantic receipt/);
        const externalOnly = await docket.emptyDocketAttachments(built.value); externalOnly.receipts = [receipt, reframed];
        await assert.rejects(docket.createDiscoveryDocket(built.value, externalOnly), /repeats a semantic receipt/);
    }
});

test('future evidence is derived from ordered existing history and cannot be supplied as a caller aggregate', async () => {
    const built = await campaign(); let value = built.value;
    const capsule = await evidence.freezeRecord(built.record);
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'future-freeze', evidence.freezeReference(capsule)));
    const bank = await future.publicFutureBank(capsule, 7);
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'future-task-bank', bank));
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'future-run-reserved', {
            schema: 'discovery-lab-future-reservation/v1', taskBankDigest: bank.digest,
            perTaskWorkLimit: 1000, attempt: 'future-' + crypto.randomUUID()}));
    const result = await future.evaluateFutureTasks(capsule, bank, {perTaskWorkLimit: 1000});
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'future-evaluation', result));
    const exported = await docket.createDiscoveryDocket(value);
    assert.equal(JSON.parse(exported.files['12_summary_tables/outcome.json']).futureEvaluationCount, 1);
    assert.equal((await docket.verifyDiscoveryDocket(exported)).verified, true);
    assert.deepEqual(JSON.parse(exported.files['08_cost_ledgers/costs.json']).unresolvedFutureAttempts, []);
    const attachments = await docket.emptyDocketAttachments(value);
    await assert.rejects(docket.createDiscoveryDocket(value, {...attachments, futureEvaluations: [{result}]}), /fields/);
});

test('stopped future work retains unknown spent reservation after reload rather than a free attempt', async () => {
    const built = await campaign(); let value = built.value;
    const capsule = await evidence.freezeRecord(built.record);
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'future-freeze', evidence.freezeReference(capsule)));
    const bank = await future.publicFutureBank(capsule, 9);
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'future-task-bank', bank));
    const reservation = await evidence.evidencePayload(built.record.campaignDigest, 'future-run-reserved', {
        schema: 'discovery-lab-future-reservation/v1', taskBankDigest: bank.digest,
        perTaskWorkLimit: 1000, attempt: 'future-' + crypto.randomUUID()});
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached', reservation);
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'future-run-stopped', {
            schema: 'discovery-lab-future-stop/v1', reservationDigest: reservation.recordDigest,
            reason: 'Browser interruption', spent: 'unknown-reservation-retained'}));
    const exported = await docket.createDiscoveryDocket(await workspace.parseWorkspace(contract.canonical(value)));
    const costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.totalComplete, false);
    assert.equal(costs.unresolvedFutureAttempts[0].spent, 'unknown-reservation-retained');
    assert.equal(costs.unresolvedFutureAttempts[0].maximumLogicalWork, bank.tasks.length * 7 * 1000);
    assert.equal(costs.unresolvedFutureAttempts[0].state, 'stopped');
    assert.equal((await docket.verifyDiscoveryDocket(exported)).verified, true);
});

test('inert snapshots reject getters, duplicate JSON and forged source context before replay', async () => {
    const {value} = await campaign(); let reads = 0;
    const trap = {...value}; Object.defineProperty(trap, 'events', {enumerable: true, get() {reads++; return value.events;}});
    await assert.rejects(docket.createDiscoveryDocket(trap), /Accessor/); assert.equal(reads, 0);
    await assert.rejects(docket.verifyDiscoveryDocket('{"schema":1,"schema":2}'), /Duplicate/);
    const attachments = await docket.emptyDocketAttachments(value);
    attachments.sources = [{repository: 'MontrealAI/AGI-Alpha-Agent-v0', commit: 'a'.repeat(40), tree: 'b'.repeat(40),
        files: [{path: '../escape', sha256: 'c'.repeat(64)}]}];
    await assert.rejects(docket.createDiscoveryDocket(value, attachments), /file identity/);
});

test('real-task proposal stays bound to the earlier event head and operationally NOT_RUN in docket replay', async () => {
    const built = await campaign(); let value = built.value;
    const request = await history.workRequest(built.record, 'AGIALPHA', history.reservationFor(built.record.charter));
    let record = await realTask.createRealTaskRecord({workRequest: request, workspaceHead: value.events.at(-1).digest,
        campaignDigest: built.record.campaignDigest, publicSource: 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0',
        specification: {multiplier: '2', offset: '1', maxBatchRows: 16}, resourceLimits: request.resourceLimits,
        adapterSources: {adapterSourceDigest: 'e'.repeat(64), checkerSourceDigest: 'f'.repeat(64)}});
    record = await realTask.freezeRealTaskArtifact(record, {moduleUtf8: 'export const transform = x => x;',
        environmentDigest: '9'.repeat(64), trace: []});
    record = await realTask.commitRealTaskBank(record, [{id: 'first', inputs: ['1', '1']}]);
    record = await realTask.checkRealTaskOutput(record, {taskId: 'first', artifactFreezeDigest: record.artifact.freezeDigest,
        outputs: ['3', '3'], trace: [], resourceUsed: vector()});
    value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
        await evidence.evidencePayload(built.record.campaignDigest, 'real-task-contract', record));
    assert.notEqual(record.workspaceHead, value.events.at(-1).digest);
    const exported = await docket.createDiscoveryDocket(value);
    assert.equal(JSON.parse(exported.files['12_summary_tables/outcome.json']).realTaskRecordCount, 1);
    assert.match(exported.files['05_agialpha_runs/run.json'], /NOT_RUN/);
    const costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.realTaskContractChecks[0].contractChecker.checking, 2);
    assert.equal(costs.realTaskContractChecks[0].reportedObservation.checking, 0);
    assert.equal(costs.realTaskContractChecks[0].operationalState, 'NOT_RUN');
    assert.equal((await docket.verifyDiscoveryDocket(exported)).verified, true);
});

test('preserved original witness costs remain visible without mixing metric units into Discovery totals', async () => {
    let value = await workspace.createWorkspace(workspace.DEFAULT_BRIEF, workspace.defaultExperiment());
    value = await workspace.recordEvaluation(value, 'development');
    value = await workspace.recordEvaluation(value, 'heldout');
    const built = await campaign(value), exported = await docket.createDiscoveryDocket(built.value);
    const costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.legacyWitnessCosts.length, 2);
    assert.deepEqual(costs.legacyWitnessCosts[0].costs, value.events[1].payload.report.costs);
    assert.equal(costs.construction.checking, built.record.result.resources.checking);
    assert.match(costs.historyTotalScope, /other metric schemas remain separate/);
    assert.equal(costs.totalComplete, false);
    assert.equal((await docket.verifyDiscoveryDocket(exported)).verified, true);
});

test('separate proposals bind identical work to distinct identities and retain both checker charges', async () => {
    const built = await campaign(); let value = built.value; const checks = [];
    const request = await history.workRequest(built.record, 'AGIALPHA', history.reservationFor(built.record.charter));
    for (let attempt = 0; attempt < 2; attempt++) {
        let record = await realTask.createRealTaskRecord({workRequest: request, workspaceHead: value.events.at(-1).digest,
            campaignDigest: built.record.campaignDigest, publicSource: 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0',
            specification: {multiplier: '2', offset: '1', maxBatchRows: 16}, resourceLimits: request.resourceLimits,
            adapterSources: {adapterSourceDigest: 'e'.repeat(64), checkerSourceDigest: 'f'.repeat(64)}});
        record = await realTask.freezeRealTaskArtifact(record, {moduleUtf8: 'export const transform = x => x;',
            environmentDigest: '9'.repeat(64), trace: []});
        record = await realTask.commitRealTaskBank(record, [{id: 'first', inputs: ['1', '1']}]);
        record = await realTask.checkRealTaskOutput(record, {taskId: 'first', artifactFreezeDigest: record.artifact.freezeDigest,
            outputs: ['3', '3'], trace: [], resourceUsed: vector()});
        checks.push(record.checks[0].digest);
        value = await workspace.recordDiscoveryEvent(value, 'lab-evidence-attached',
            await evidence.evidencePayload(built.record.campaignDigest, 'real-task-contract', record));
    }
    assert.notEqual(checks[0], checks[1]);
    const exported = await docket.createDiscoveryDocket(value), costs = JSON.parse(exported.files['08_cost_ledgers/costs.json']);
    assert.equal(costs.realTaskContractChecks.length, 2);
    assert.notEqual(costs.realTaskContractChecks[0].proposalIdentity, costs.realTaskContractChecks[1].proposalIdentity);
    assert.equal(costs.realTaskContractChecks.reduce((total, item) => total + item.contractChecker.checking, 0), 4);
    assert.equal((await docket.verifyDiscoveryDocket(exported, {expectedWorkspaceHead: value.events.at(-1).digest})).verified, true);
});
