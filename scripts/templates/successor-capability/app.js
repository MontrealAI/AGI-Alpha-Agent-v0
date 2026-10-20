// SPDX-License-Identifier: Apache-2.0
// The injected capability model owns construction, validation and evidence replay.
// User-authored descriptions and imported text are data, never executable code.
const $ = id => document.getElementById(id);
const STORE_NAME = 'agialpha.successor-capability.v1';
const IMPORT_LIMIT = 2_000_000;
const fields = [
    ['title', 'Capability name', 'framing', 'Name the new capability, not a promise of success.', 'wide'],
    ['unmetNeed', 'What important need is still unmet?', 'framing', 'Who cannot do what today? What evidence would establish the need?', 'wide'],
    ['problemFamily', 'What family of problems could this unlock?', 'framing', 'Describe several related uses, discoveries or potential businesses rather than a single task.', 'wide'],
    ['restrictiveAssumption', 'Which limiting assumption might be unnecessary?', 'framing', 'Make the assumption explicit. Changing it is a hypothesis, not yet an advantage.', 'wide'],
    ['constructionKind', 'What kind of capability are you proposing?', 'construction', 'Choose a category, not an execution permission.', 'wide'],
    ['proposedConstruction', 'What new thing would you construct?', 'construction', 'Specify the instrument, representation, architecture or other reusable mechanism.', 'wide'],
    ['objective', 'What useful outcome must it preserve?', 'construction', 'A changed formulation still needs to serve the original unmet need.', 'wide'],
    ['constraints', 'What boundaries must it respect?', 'construction', 'Resources, permitted inputs, safety, operating limits and unacceptable failure modes.', 'wide'],
    ['constructionPlan', 'How would you construct it?', 'construction', 'Separate completed work from proposed steps. Describe dependencies and unresolved questions.', 'wide'],
    ['acceptanceEvidence', 'What evidence would justify keeping it?', 'construction', 'Name credible alternatives, falsification tests, acceptance criteria and independent checks still needed.', 'wide'],
    ['reusePlan', 'How could others build on this capability?', 'reuse', 'Describe the reusable output, interface or method and its possible applications.', 'wide'],
    ['scopeAssumptions', 'Where might it work, and where might it fail?', 'reuse', 'List scope assumptions and what would need to change for a different use.', 'wide'],
    ['beneficiariesHypothesis', 'Possible beneficiaries · hypothesis', 'economics', 'Who might benefit? Do not imply they have adopted or agreed to buy.', 'wide'],
    ['valueHypothesis', 'Possible value · hypothesis', 'economics', 'What improvement might matter? Realized value is not measured by this page.', 'wide'],
    ['costHypothesis', 'Costs and resource burden · hypothesis', 'economics', 'Include development, compute, maintenance, evaluation and human effort. Unknowns stay unknown.', 'wide'],
    ['financingHypothesis', 'Possible financing · hypothesis only', 'economics', 'No budget is funded, committed or spent here.', 'wide'],
    ['adoptionEvidence', 'Adoption evidence · unknown unless established elsewhere', 'economics', 'Distinguish supplied, unverified observations from missing evidence. A synthetic pass is not demand.', 'wide'],
];
const kinds = [
    ['instrument', 'Instrument'], ['representation', 'Representation'],
    ['experimental-architecture', 'Experimental architecture'],
    ['productive-architecture', 'Productive architecture'], ['other', 'Other reusable construction'],
];
let store = null;
let current = null;
let inspected = null;
let storedRevision = null;
let pending = null;
let dirty = true;
let successorEditing = false;
let busy = false;
let ready = false;
let recoveryDownloaded = false;
let recoveryRetained = false;
let savedCount = 0;

function element(tag, parent, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    if (parent) parent.append(node);
    return node;
}
function buildFields() {
    for (const [key, label, group, help, width] of fields) {
        const field = element('div', $(`${group}-fields`), undefined, `field field-${width}`);
        const caption = element('label', field, label);
        caption.htmlFor = `brief-${key}`;
        let input;
        if (key === 'constructionKind') {
            input = element('select', field);
            for (const [value, text] of kinds) {
                const option = element('option', input, text);
                option.value = value;
            }
        } else {
            input = element(key === 'title' ? 'input' : 'textarea', field);
            input.maxLength = key === 'title' ? 160 : 2000;
            if (key !== 'title') input.rows = 3;
        }
        input.id = `brief-${key}`;
        input.name = key;
        input.required = true;
        input.disabled = true;
        input.setAttribute('aria-describedby', `help-${key}`);
        element('p', field, help, 'field-help').id = `help-${key}`;
        input.addEventListener('input', markDraft);
        input.addEventListener('change', markDraft);
    }
}
function status(message) { $('status').textContent = message; }
function clearError() { $('error').hidden = true; $('error').textContent = ''; }
function showError(error) {
    const reason = String(error?.code || error?.message || error).slice(0, 700);
    $('error').textContent = reason;
    $('error').hidden = false;
}
function canonical(value) { return capability.canonical(value); }
function isProtected() { return pending !== null && !recoveryRetained; }
function publicConfirmed() {
    if (!$('public-confirmation').checked) {
        $('public-confirmation').focus();
        throw Error('Confirm public, non-personal material before saving or importing.');
    }
}
function protectReplacement() {
    if (isProtected()) {
        $('recovery-export').focus();
        throw Error('Keep and acknowledge the protected recovery file before opening, importing or starting another history.');
    }
    if (dirty && !window.confirm('This will replace your unsaved working draft. Download the working draft first if you need it. Continue?')) {
        return false;
    }
    return true;
}
function rawDraft() {
    return {
        brief: Object.fromEntries(fields.map(([key]) => [key, $(`brief-${key}`).value])),
        witnessEnabled: $('witness-enabled').checked,
        experimentText: $('experiment').value,
        successorReason: $('successor-reason').value,
    };
}
function inputSpec() {
    const draft = rawDraft();
    for (const [key, value] of Object.entries(draft.brief)) {
        if (!value.trim()) throw Error(`Complete the ${key} field, using “unknown” where appropriate.`);
        if (value.length > (key === 'title' ? 160 : 2000)) throw Error(`The ${key} field exceeds its character limit.`);
    }
    let experiment = null;
    if (draft.witnessEnabled) {
        if (draft.experimentText.length > 20000) throw Error('The synthetic configuration exceeds 20,000 characters.');
        try { experiment = capability.parseExperiment(draft.experimentText); }
        catch (error) { throw Error(`The synthetic instrument configuration is invalid: ${error.message}`); }
    }
    return { brief: draft.brief, experiment, reason: draft.successorReason };
}
function defaultExperimentText() {
    // Resolve only at runtime, after every injected module has initialized.
    return JSON.stringify(capability.defaultExperiment(), null, 2);
}
function fillBrief(brief, experiment) {
    for (const [key] of fields) $(`brief-${key}`).value = brief[key] ?? '';
    $('witness-enabled').checked = experiment !== null;
    $('experiment').value = experiment === null ? defaultExperimentText() : JSON.stringify(experiment, null, 2);
    $('successor-reason').value = '';
    successorEditing = false;
    dirty = !current;
}
function markDraft() {
    if (busy || pending) return;
    dirty = true;
    if (current) successorEditing = true;
    render();
}
function verdict(payload) {
    if (!payload) return { text: 'Not evaluated', result: 'none' };
    const value = payload.report?.verdict;
    if (value === 'fail') {
        return { text: 'Computed FAIL · synthetic witness only', result: 'fail' };
    }
    if (value === 'pass') {
        return { text: 'Computed PASS · synthetic witness only', result: 'pass' };
    }
    return { text: 'Computed report · inspect the scoped verdict', result: 'report' };
}
function exposure(payload) {
    if (!payload) return null;
    const value = payload.exposure;
    if (!value) return 'Exposure metadata is not available; no protected or fresh-data claim is made.';
    if (value.status === 'previously-exposed-not-heldout') {
        return 'Previously exposed cases: not fresh held-out evidence. Retuning and repeated-case results must be read in that context.';
    }
    return 'First recorded exposure within this history only. Cases are public and inspectable, not independently protected.';
}
function phaseReport(phase, payload) {
    const result = verdict(payload);
    $(`${phase}-state`).textContent = result.text;
    $(`${phase}-state`).dataset.result = result.result;
    const report = payload?.report;
    const construction = payload?.construction;
    $(`${phase}-summary`).textContent = payload
        ? `${construction.calibration.sample_count} synthetic calibration observations; ${construction.model.coefficient_count} derived coefficients. ${report.response_match_count} of ${report.evaluation_masks.length} responses matched exactly across ${report.comparison_count} comparisons. Counts are abstract software work, not monetary or physical savings.`
        : 'No construction or measurements recorded for this phase.';
    $(`${phase}-report`).textContent = payload ? JSON.stringify(payload, null, 2) : `No ${phase === 'heldout' ? 'held-out' : 'development'} report.`;
}
function renderVersions() {
    const list = $('version-list');
    list.replaceChildren();
    if (!inspected) {
        element('li', list, 'No frozen versions yet.');
        $('history-json').textContent = 'No workspace history.';
        return;
    }
    for (const version of inspected.versions) {
        const item = element('li', list);
        element('h3', item, `Version ${version.number} · ${version.brief.title}`);
        element('p', item, `${version.parent === null ? 'Initial construction proposal' : `Successor of version ${version.number - 1}`} · ${version.reason || 'Initial brief'}`);
        element('p', item, version.brief.proposedConstruction);
        element('p', item, version.experiment === null ? 'Proposal only. No evaluator executes this described construction.' : 'Optional supported synthetic witness included. The broad brief is not evaluated.');
        element('p', item, `Development: ${verdict(version.development).text}. Held-out: ${verdict(version.heldout).text}.`);
        for (const [label, payload] of [['Development', version.development], ['Held-out', version.heldout]]) {
            if (payload) element('p', item, `${label}: ${exposure(payload)}`);
        }
        element('p', item, 'Economic outcome: not evaluated. Prior-version evidence: historical only.');
        element('p', item, `Frozen input digest: ${version.frozenDigest}`, 'hash-line');
        const details = element('details', item);
        element('summary', details, `Inspect version ${version.number}: original brief, configuration and full evidence`);
        const full = element('pre', details, JSON.stringify(version, null, 2));
        full.tabIndex = 0;
        full.setAttribute('aria-label', `Complete version ${version.number}`);
    }
    $('history-json').textContent = JSON.stringify(current, null, 2);
}
function controls() {
    const idle = ready && !busy;
    const editable = idle && !pending;
    for (const [key] of fields) $(`brief-${key}`).disabled = !editable;
    $('witness-enabled').disabled = !editable;
    $('experiment').disabled = !editable || !$('witness-enabled').checked;
    $('experiment-editor').hidden = !$('witness-enabled').checked;
    $('public-confirmation').disabled = !idle;
    $('successor-reason').disabled = !editable || !successorEditing;
    $('successor-reason-field').hidden = !successorEditing;
    $('freeze').disabled = !editable || (current !== null && !dirty) || !$('public-confirmation').checked;
    $('freeze').textContent = current ? `Save & freeze successor ${Number(inspected?.latest.number) + 1}` : 'Save & freeze version 1';
    $('start-successor').disabled = !editable || !current || storedRevision === null || successorEditing;
    $('revert').disabled = !editable || !current || !dirty;
    $('new').disabled = !idle;
    $('saved').disabled = !idle || !store || savedCount === 0;
    $('open').disabled = !idle || !store || !$('saved').value;
    $('import').disabled = !idle;
    $('export').disabled = !idle || !current;
    $('export-draft').disabled = !idle;
    const runnable = idle && current && storedRevision !== null && !dirty && !successorEditing && !pending && inspected?.latest.experiment !== null;
    $('development').disabled = !runnable || !!inspected?.latest.development;
    $('heldout').disabled = !runnable || !inspected?.latest.development || !!inspected?.latest.heldout;
    $('recovery').hidden = !pending;
    $('recovery-export').disabled = !idle || !pending;
    $('recovery-retry').disabled = !idle || !pending;
    $('recovery-confirm').disabled = !idle || !pending || !recoveryDownloaded || recoveryRetained;
    $('brief-form').setAttribute('aria-busy', String(busy));
    $('text-size').disabled = !ready;
}
function render() {
    const latest = inspected?.latest;
    $('identity').textContent = current ? `${current.missionId} · history revision ${current.revision} · ${pending ? 'not confirmed saved' : storedRevision === null ? 'in memory only' : `saved locally · storage revision ${storedRevision}`}` : 'No frozen version yet. The default example is an editable proposal.';
    $('draft-badge').textContent = pending ? 'Unsaved recovery copy' : dirty ? current ? 'Stale · successor draft' : 'Unsaved proposal' : `Frozen version ${latest.number}`;
    $('editor-eyebrow').textContent = successorEditing ? '01 · DEVELOP AN EXPLICIT SUCCESSOR' : '01 · DESIGN THE POSSIBILITY';
    $('draft-state').textContent = pending ? 'The candidate history is protected in memory. Retry saving or retain its recovery export before replacing it.' : dirty ? current ? 'Inputs have changed. Earlier results are historical and do not validate this draft. Freeze a successor with a reason before another test.' : 'Saving this brief creates a frozen proposal, not an executed invention. Confirm public, non-personal material above first.' : 'These inputs are frozen. Editing starts an unvalidated successor draft; original evidence remains unchanged.';
    $('version-state').textContent = !latest ? 'No validation yet.' : dirty ? 'Draft changed · no current validation.' : latest.experiment === null ? 'Proposal only · not executed.' : latest.witnessAcceptance === 'fail' ? 'Computed FAIL · synthetic witness only' : latest.witnessAcceptance === 'pass' ? 'Computed PASS · both synthetic phases only' : latest.development ? 'Development passed · reuse still pending' : 'No validation yet.';
    $('version-detail').textContent = !latest ? 'First save a frozen version. A plain brief has no executable construction here.' : dirty ? `Reports below belong to frozen version ${latest.number}, not the edited draft.` : latest.experiment === null ? 'The brief has been retained. No evaluator executes or validates its described capability.' : 'Only the fixed supported synthetic instrument is constructed and evaluated. The broad capability brief and economic hypotheses remain unevaluated.';
    $('run-gate').textContent = pending ? 'Testing is locked while this history is not confirmed saved.' : dirty ? 'Save a frozen version with unchanged inputs before constructing or evaluating the witness.' : latest?.experiment === null ? 'No synthetic witness selected. Proposal mode does not run any evaluator.' : latest?.heldout ? 'Both recorded phases are retained. Develop a successor to make a new explicit experiment.' : latest?.development ? 'Development is retained. Evaluate the unchanged frozen configuration next.' : 'The construction and development evaluation run only when you press the button.';
    phaseReport('development', latest?.development);
    phaseReport('heldout', latest?.heldout);
    const exposures = [];
    if (latest?.development) exposures.push(`Development: ${exposure(latest.development)}`);
    if (latest?.heldout) exposures.push(`Held-out: ${exposure(latest.heldout)}`);
    $('exposure-summary').textContent = exposures.join(' ') || 'No synthetic cases evaluated yet.';
    $('recovery-summary').textContent = pending ? `${current.missionId} · candidate history revision ${current.revision}. A failed save never overwrites another tab’s history.` : '';
    $('recovery-retained').textContent = recoveryRetained ? 'You acknowledged keeping this exact recovery history. It is still not confirmed in local storage.' : recoveryDownloaded ? 'Download prepared. Confirm only after you have retained the exact file.' : 'Keep the exact recovery file, then acknowledge retaining it.';
    controls();
}
async function inspectStored(envelope) {
    if (!envelope || !Number.isSafeInteger(envelope.revision) || envelope.revision < 0 || !envelope.workspace) {
        throw Error('The stored capability history has an invalid storage envelope.');
    }
    const workspace = await capability.parseWorkspace(canonical(envelope.workspace));
    if (envelope.missionId !== workspace.missionId) throw Error('The saved workspace identity does not match its envelope.');
    return { workspace, inspection: await capability.inspectWorkspace(workspace), revision: envelope.revision };
}
async function refreshList() {
    if (!store) return;
    const all = await store.list();
    const options = [];
    for (const item of all) {
        const checked = await inspectStored(item);
        options.push({ id: checked.workspace.missionId, title: checked.inspection.latest.brief.title, revision: checked.revision });
    }
    const previous = $('saved').value;
    $('saved').replaceChildren();
    element('option', $('saved'), options.length ? 'Choose a saved history' : 'No saved capability histories').value = '';
    for (const item of options) {
        const option = element('option', $('saved'), `${item.title} · local r${item.revision}`);
        option.value = item.id;
    }
    savedCount = options.length;
    $('saved').value = options.some(item => item.id === current?.missionId) ? current.missionId : previous;
}
async function refreshAfterSave() {
    try { await refreshList(); }
    catch (error) {
        showError(error);
        status('The change is saved, but the saved-history list could not be refreshed. Keep an exported copy.');
    }
}
function isStrictExtension(before, after) {
    return before.missionId === after.missionId && after.events.length > before.events.length &&
        before.events.every((event, index) => canonical(event) === canonical(after.events[index]));
}
async function commitPending() {
    if (!pending) throw Error('No pending history needs saving.');
    if (!store) store = await storage.openMissionStore({ name: STORE_NAME });
    const candidate = pending;
    const actualEnvelope = await store.get(candidate.workspace.missionId);
    let actual = null;
    if (actualEnvelope) actual = await inspectStored(actualEnvelope);
    if (actual && canonical(actual.workspace) === canonical(candidate.workspace)) {
        storedRevision = actual.revision;
    } else {
        if (candidate.expected === null ? actual !== null : !actual || actual.revision !== candidate.expected) {
            throw Error('LOCAL_REVISION_CONFLICT: Another saved history exists. Keep this recovery copy, then reopen the saved history. Nothing was overwritten.');
        }
        if (actual && canonical(actual.workspace) !== candidate.base) {
            throw Error('LOCAL_HISTORY_CONFLICT: The saved event history differs. It will not be overwritten.');
        }
        const revision = candidate.expected === null ? 0 : candidate.expected + 1;
        const saved = await store.save({ missionId: candidate.workspace.missionId, revision, workspace: candidate.workspace }, candidate.expected);
        if (!saved || saved.revision !== revision || canonical(saved.workspace) !== canonical(candidate.workspace)) {
            throw Error('Storage did not confirm the exact candidate. Keep the recovery file and retry to inspect the saved outcome.');
        }
        storedRevision = revision;
    }
    pending = null;
    recoveryDownloaded = false;
    recoveryRetained = false;
    dirty = false;
    successorEditing = false;
    await refreshAfterSave();
}
async function persist(next, expected, base) {
    const nextInspection = await capability.inspectWorkspace(next);
    current = next;
    inspected = nextInspection;
    pending = { workspace: next, expected, base: base ? canonical(base) : null };
    recoveryDownloaded = false;
    recoveryRetained = false;
    dirty = false;
    successorEditing = false;
    fillBrief(nextInspection.latest.brief, nextInspection.latest.experiment);
    renderVersions();
    try { await commitPending(); }
    catch (error) {
        status('This candidate could not be confirmed saved. Its full history is protected here. Download recovery or retry; no conflicting history will be overwritten.');
        throw error;
    }
}
async function operation(action) {
    if (busy || !ready) return;
    busy = true;
    clearError();
    controls();
    try { await action(); }
    catch (error) { showError(error); }
    finally { busy = false; render(); }
}
function download(text, filename) {
    const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    const link = element('a', document.body);
    link.href = url;
    link.download = filename;
    link.hidden = true;
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function downloadCurrent(recovery = false) {
    if (!current) throw Error('There is no frozen history to export.');
    download(canonical(current), `successor-capability-${recovery ? 'recovery-' : ''}${current.missionId}.json`);
}
function resetDraft() {
    current = null;
    inspected = null;
    storedRevision = null;
    pending = null;
    recoveryDownloaded = false;
    recoveryRetained = false;
    $('public-confirmation').checked = false;
    fillBrief(capability.DEFAULT_BRIEF, null);
    renderVersions();
}
function assertFrozenWitness() {
    if (!current || !inspected || storedRevision === null || pending || dirty || successorEditing) {
        throw Error('Save unchanged frozen inputs before evaluating a synthetic witness.');
    }
    const selected = inputSpec();
    if (canonical(selected.brief) !== canonical(inspected.latest.brief) || canonical(selected.experiment) !== canonical(inspected.latest.experiment)) {
        dirty = true;
        successorEditing = true;
        throw Error('The inputs no longer match the frozen version. Save a successor before evaluation.');
    }
    if (inspected.latest.experiment === null) throw Error('Proposal-only mode has no executable evaluator.');
}

buildFields();
$('brief-form').addEventListener('submit', event => {
    event.preventDefault();
    operation(async () => {
        if (pending) throw Error('Resolve the protected recovery history before creating another version.');
        publicConfirmed();
        const selected = inputSpec();
        let next;
        const base = current;
        const expected = storedRevision;
        if (current) {
            if (expected === null) throw Error('Save or reopen the current history before developing a successor.');
            if (!dirty) throw Error('There are no successor edits to freeze.');
            if (!selected.reason.trim()) throw Error('Explain the reason for this successor version.');
            if (selected.reason.length > 2000) throw Error('The successor reason exceeds 2,000 characters.');
            next = await capability.addSuccessor(current, selected.brief, selected.experiment, selected.reason);
        } else {
            next = await capability.createWorkspace(selected.brief, selected.experiment);
        }
        await persist(next, expected, base);
        status(selected.experiment === null ? 'Frozen proposal saved. Nothing described in the brief has been executed or validated.' : 'Version saved and frozen. The optional synthetic witness is ready for an explicit construction and development test.');
    });
});
$('witness-enabled').addEventListener('change', markDraft);
$('experiment').addEventListener('input', markDraft);
$('successor-reason').addEventListener('input', markDraft);
$('public-confirmation').addEventListener('change', controls);
$('saved').addEventListener('change', controls);
$('start-successor').addEventListener('click', () => operation(async () => {
    if (!current || pending || storedRevision === null) throw Error('A saved history is required.');
    successorEditing = true;
    dirty = true;
    $('public-confirmation').checked = false;
    status('A successor draft is open. Explain what you learned and change the construction deliberately. Earlier evidence does not transfer.');
    $('brief-title').focus();
}));
$('revert').addEventListener('click', () => operation(async () => {
    if (!current || pending) return;
    if (!window.confirm('Discard the edited draft and restore the exact latest frozen inputs? Earlier evidence will remain unchanged.')) return;
    fillBrief(inspected.latest.brief, inspected.latest.experiment);
    status('Exact frozen inputs restored. No version or evidence was changed.');
}));
$('new').addEventListener('click', () => operation(async () => {
    if (!protectReplacement()) return;
    resetDraft();
    status('A separate public example brief is ready to edit. No existing history has changed.');
}));
$('open').addEventListener('click', () => operation(async () => {
    if (!protectReplacement()) return;
    if (!store || !$('saved').value) throw Error('Choose a saved capability history.');
    const envelope = await store.get($('saved').value);
    if (!envelope) throw Error('This saved capability history was not found.');
    const checked = await inspectStored(envelope);
    current = checked.workspace;
    inspected = checked.inspection;
    storedRevision = checked.revision;
    pending = null;
    recoveryDownloaded = false;
    recoveryRetained = false;
    $('public-confirmation').checked = false;
    fillBrief(inspected.latest.brief, inspected.latest.experiment);
    renderVersions();
    status('Saved history opened and inspected. No experiment restarted. Retained synthetic evidence is not external authorization.');
}));
$('import').addEventListener('change', () => {
    const file = $('import').files[0];
    if (!file || busy) return;
    operation(async () => {
        try {
            publicConfirmed();
            if (!protectReplacement()) return;
            if (file.size > IMPORT_LIMIT) throw Error('The whole-history file must be at most 2,000,000 bytes.');
            const bytes = await file.arrayBuffer();
            const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
            const next = await capability.parseWorkspace(text);
            await capability.inspectWorkspace(next);
            if (!store) {
                try { store = await storage.openMissionStore({ name: STORE_NAME }); }
                catch { /* The validated candidate is protected by persist if storage remains unavailable. */ }
            }
            const envelope = store ? await store.get(next.missionId) : null;
            const saved = envelope ? await inspectStored(envelope) : null;
            if (saved && canonical(saved.workspace) !== canonical(next) && !isStrictExtension(saved.workspace, next)) {
                throw Error('Import refused: this same-ID file is divergent or shorter than the saved history. The saved history and current workspace are unchanged.');
            }
            await persist(next, saved?.revision ?? null, saved?.workspace ?? null);
            status('Whole history imported, validated and saved. Original evidence stays with its versions. No experiment restarted and no external permission was restored.');
        } finally { $('import').value = ''; }
    });
});
for (const phase of ['development', 'heldout']) {
    $(phase).addEventListener('click', () => operation(async () => {
        assertFrozenWitness();
        if (phase === 'heldout' && !inspected.latest.development) throw Error('Record development evidence before the held-out evaluation.');
        if (inspected.latest[phase]) throw Error('This phase already has retained evidence. Develop a successor for a new experiment.');
        const before = current;
        const expected = storedRevision;
        status(phase === 'development' ? 'Constructing the fixed supported synthetic instrument and measuring development cases…' : 'Evaluating the exact frozen instrument on the fixed held-out synthetic cases…');
        const next = await capability.recordEvaluation(before, phase);
        await persist(next, expected, before);
        status(`${phase === 'development' ? 'Development' : 'Held-out'} report saved. ${verdict(inspected.latest[phase]).text}. The broad brief and economic hypotheses remain unevaluated.`);
        renderVersions();
    }));
}
$('export').addEventListener('click', () => operation(async () => {
    downloadCurrent(!!pending);
    status('Whole-history download prepared. It includes every retained version and report, not unsaved editor changes. Check that you retained the file.');
}));
$('export-draft').addEventListener('click', () => operation(async () => {
    download(JSON.stringify({
        format: 'successor-capability-working-draft-v1',
        notice: 'Unvalidated working notes, not a frozen or executable capability history. This file is not accepted by the whole-history importer.',
        baseWorkspace: current,
        draft: rawDraft(),
    }, null, 2), 'successor-capability-working-draft.json');
    status('Working-draft download prepared. It retains the current text and base history as notes, not as evaluated evidence.');
}));
$('recovery-export').addEventListener('click', () => operation(async () => {
    if (!pending) throw Error('No protected recovery copy is pending.');
    downloadCurrent(true);
    recoveryDownloaded = true;
    status('Exact recovery download prepared. Confirm you retained the file before replacing this protected history.');
}));
$('recovery-retry').addEventListener('click', () => operation(async () => {
    if (!pending) throw Error('No protected recovery copy is pending.');
    try { store?.close(); } catch { /* Reopening is a safe read/write recovery, not an overwrite. */ }
    store = null;
    await commitPending();
    status('The exact recovery history is confirmed saved. No divergent history was overwritten.');
}));
$('recovery-confirm').addEventListener('click', () => operation(async () => {
    if (!pending || !recoveryDownloaded) throw Error('Download and retain this exact recovery history first.');
    recoveryRetained = true;
    status('You confirmed keeping the recovery file. You may open another history, but this candidate is still not confirmed saved locally.');
}));
$('text-size').addEventListener('click', () => {
    const large = document.documentElement.classList.toggle('large-text');
    $('text-size').setAttribute('aria-pressed', String(large));
    $('text-size').textContent = large ? 'Standard text' : 'Larger text';
});
window.addEventListener('beforeunload', event => {
    if (isProtected() || dirty) { event.preventDefault(); event.returnValue = ''; }
});
(async () => {
    try {
        resetDraft();
        store = await storage.openMissionStore({ name: STORE_NAME });
        await refreshList();
        status('Ready. Shape a capability brief, then save a frozen version. The optional synthetic witness is off by default.');
    } catch (error) {
        showError(error);
        status('Local storage is not ready. You can edit and download working notes; a failed save will keep a protected recovery copy.');
    } finally {
        ready = true;
        render();
    }
})();
