// SPDX-License-Identifier: Apache-2.0
// The existing workspace bridge owns reservation, execution, verification and persistence.
function mountDiscoveryLab({runtime, history}) {
    const root = document.getElementById('discovery-lab');
    if (!root) return {refresh: async () => {}};
    const byId = id => document.getElementById('lab-' + id);
    const copy = value => JSON.parse(JSON.stringify(value));
    const json = value => JSON.stringify(JSON.parse(stable(value)), null, 2);
    const stable = value => Array.isArray(value) ? '[' + value.map(stable).join(',') + ']'
        : value && typeof value === 'object' ? '{' + Object.keys(value).sort()
            .map(key => JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}' : JSON.stringify(value);
    const same = (a, b) => stable(a) === stable(b);
    const stages = [
        ['learn', 'Out-Learn', 'Construct the measurement interface'],
        ['think', 'Out-Think', 'Construct an updatable representation'],
        ['design', 'Out-Design', 'Construct usable worker capacity'],
        ['strategise', 'Out-Strategise', 'Construct a robust completion'],
        ['execute', 'Out-Execute', 'Retain valid progress through change'],
        ['evolve', 'Out-Evolve', 'Construct reusable discovery capability'],
    ];
    const numbers = {
        accuracy: 'accuracy', intendedUses: 'uses', controls: 'controls', memory: 'memory',
        workerCapacity: 'workers', noise: 'noise',
    };
    const selects = {topology: 'topology', driftScope: 'drift-scope', actualDrift: 'actual-drift'};
    const groups = {
        observations: ['observations', ['contrast', 'reference', 'coarse', 'full']],
        operations: ['operations', ['flip-x', 'flip-y', 'flip-z', 'flip-w', 'mix']],
        faultHypotheses: ['faults', ['clear', 'left', 'right', 'both']],
        checkpoints: ['checkpoints', ['safety', 'sterile']],
    };
    const budgetLabels = {
        acquisitions: 'Synthetic acquisitions · per phase', search: 'Search work · per phase', checking: 'Checking work · per phase',
        storageBytes: 'Phase evidence cap · bytes', installations: 'Installations · per phase',
    };
    let draft = copy(runtime.DEFAULT_CHARTER);
    let savedState = {ready: false, locked: true, campaigns: [], reason: 'Preparing the existing capability history…'};
    let selected = null;
    let busy = false;
    let changed = true;
    let manifestPending = false;
    let editorTouched = false;
    let refreshing = false;
    let refreshAgain = false;

    function node(tag, parent, text, className) {
        const item = document.createElement(tag);
        if (text !== undefined) item.textContent = text;
        if (className) item.className = className;
        if (parent) parent.append(item);
        return item;
    }
    function message(text) { byId('status').textContent = text; }
    function error(reason) {
        byId('error').textContent = String(reason?.message || reason).slice(0, 1000);
        byId('error').hidden = false;
    }
    function clearError() { byId('error').textContent = ''; byId('error').hidden = true; }
    function recordResult(record) { return record?.result || record?.campaign || null; }
    function outcomeState(record) { return record?.state || recordResult(record)?.state || 'candidate'; }
    function recordCharter(record) { return record?.charter || recordResult(record)?.charter || null; }
    function campaigns() { return Array.isArray(savedState.campaigns) ? savedState.campaigns : []; }
    function latestAccepted() {
        return [...campaigns()].reverse().find(record => outcomeState(record) === 'accepted') || null;
    }
    function fill(next) {
        draft = copy(next);
        manifestPending = false;
        for (const [key, id] of Object.entries(numbers)) byId(id).value = String(draft[key]);
        for (const [key, id] of Object.entries(selects)) byId(id).value = draft[key];
        for (const [key, [id]] of Object.entries(groups)) {
            for (const input of byId(id).querySelectorAll('input')) input.checked = draft[key].includes(input.value);
        }
        byId('hidden-coupling').checked = draft.hiddenCoupling;
        for (const key of Object.keys(draft.budget)) byId('budget-' + key).value = String(draft.budget[key]);
        byId('charter-json').value = json(draft);
        updateDraftState();
    }
    function read() {
        const next = copy(draft);
        for (const [key, id] of Object.entries(numbers)) {
            const value = byId(id).value;
            if (!/^(?:0|[1-9]\d*)$/.test(value)) throw Error('Provide a nonnegative whole number for ' + key + '.');
            next[key] = Number(value);
        }
        for (const [key, id] of Object.entries(selects)) next[key] = byId(id).value;
        for (const [key, [id]] of Object.entries(groups)) {
            const selectedValues = [...byId(id).querySelectorAll('input:checked')].map(input => input.value);
            next[key] = [...draft[key].filter(value => selectedValues.includes(value)),
                ...selectedValues.filter(value => !draft[key].includes(value))];
        }
        next.hiddenCoupling = byId('hidden-coupling').checked;
        for (const key of Object.keys(next.budget)) {
            const value = byId('budget-' + key).value;
            if (!/^(?:0|[1-9]\d*)$/.test(value)) throw Error('Provide a nonnegative whole number for ' + key + ' budget.');
            next.budget[key] = Number(value);
        }
        return runtime.validateCharter(next);
    }
    function controls() {
        const idle = !busy;
        byId('form').setAttribute('aria-busy', String(busy));
        for (const input of byId('form').querySelectorAll('input,select,textarea,button')) input.disabled = !idle;
        const runnable = idle && savedState.ready && !savedState.locked && !manifestPending
            && byId('public-confirmation').checked;
        byId('construct').disabled = !runnable;
        const parent = latestAccepted();
        byId('successor').disabled = !runnable || !parent || recordCharter(parent)?.controls >= 4;
        byId('export-request').disabled = !idle || !selected || outcomeState(selected) !== 'accepted'
            || !!savedState.locked || typeof history.workRequest !== 'function';
        byId('route').disabled = !idle;
        byId('export-account').disabled = !idle || typeof history.accountReceipt !== 'function';
        byId('reservation').textContent = manifestPending
            ? 'Apply the edited charter before construction. The previous frozen result does not validate unapplied changes.'
            : savedState.locked
            ? savedState.reason || 'Resolve the existing workspace recovery or draft before running another campaign.'
            : !byId('public-confirmation').checked
                ? 'Confirm the supplied synthetic scope to start. The existing history reserves room before work.'
                : 'The existing capability history reserves room before work and retains this campaign’s outcome.';
        byId('successor-status').textContent = !parent
            ? 'First construct an accepted parent platform.'
            : recordCharter(parent)?.controls >= 4
                ? 'The four-control purpose is already represented. Inspect its requalification and scratch comparison below.'
                : 'The accepted parent stays frozen. The challenge adds one control and rechecks old and new obligations.';
        byId('route-status').textContent = 'DRAFT_NOT_SUBMITTED · ' + byId('route').value
            + ' cap: 0. Fleet execution is unprovisioned; exporting a draft does not submit work.';
    }
    function updateDraftState() {
        if (manifestPending) {
            byId('charter-badge').textContent = 'Apply edited charter first';
            controls();
            return;
        }
        let next;
        try {
            next = read();
            draft = copy(next);
            byId('charter-json').value = json(next);
            const plan = typeof history.reservePlan === 'function' ? history.reservePlan(next) : {
                acquisitions: 2 * next.budget.acquisitions, search: 2 * next.budget.search,
                checking: 2 * next.budget.checking, memoryBytes: 500000, storageBytes: 500000,
                workerCapacity: next.workerCapacity, installations: 2 * next.budget.installations, elapsedMs: 120000};
            byId('reservation-plan').textContent = json(plan);
            byId('reserve-summary').textContent = 'Before work: construction + full replay reserve '
                + plan.acquisitions + ' acquisitions, ' + plan.search + ' search units, ' + plan.checking
                + ' checking units and ' + plan.installations + ' installations. Worker and memory limits are peaks; no currency is reserved.';
        } catch {
            byId('charter-badge').textContent = 'Incomplete charter';
            controls();
            return;
        }
        const prior = recordCharter(selected);
        changed = !prior || !same(prior, next);
        byId('charter-badge').textContent = changed ? prior ? 'Changed · needs qualification' : 'Editable charter' : 'Frozen campaign charter';
        if (prior && changed) {
            const invalidation = runtime.invalidationFor(prior, next);
            message('Charter changed. The displayed result belongs to its earlier frozen scope. '
                + (typeof invalidation === 'string' ? invalidation : json(invalidation)));
        }
        controls();
    }
    function renderStage(stage, index) {
        const kind = stage.kind || stages[index]?.[0] || 'unknown';
        const label = stages.find(value => value[0] === kind) || [kind, kind, 'Inspect construction'];
        const row = node('li', byId('stages'));
        row.dataset.state = stage.status || 'candidate';
        const heading = node('div', row, undefined, 'lab-stage-heading');
        node('h4', heading, label[1] + ' · ' + label[2]);
        node('span', heading, stage.status || 'candidate', 'lab-stage-status');
        node('p', row, stage.reason || 'Inspect the computed artifact and checker evidence.', 'lab-stage-reason');
        const detail = node('details', row);
        node('summary', detail, 'Program, assumptions, checker evidence and costs');
        const data = node('pre', detail, json(stage));
        data.tabIndex = 0;
        data.setAttribute('aria-label', label[1] + ' complete executable artifact');
        data.setAttribute('role', 'group');
    }
    function fact(label, value) {
        const box = node('div', byId('result-facts'));
        node('dt', box, label);
        node('dd', box, String(value));
    }
    function renderComparisons(result) {
        const body = byId('comparison-table').querySelector('tbody');
        body.replaceChildren();
        const raw = result.comparisons || [];
        const rows = Array.isArray(raw) ? raw : Object.entries(raw).map(([name, value]) => ({name, ...value}));
        for (const [index, row] of rows.entries()) {
            const tr = node('tr', body);
            const name = row.name || row.kind || row.id || 'Alternative ' + (index + 1);
            node('th', tr, String(name)).scope = 'row';
            node('td', tr, String(row.state || row.status || row.verdict || 'Inspect complete evidence'));
            const shown = row.measuredWork ?? row.cost ?? row.resources ?? row.work ?? row.reason ?? row;
            node('td', tr, typeof shown === 'object' ? JSON.stringify(shown) : String(shown));
        }
        byId('comparison-panel').hidden = false;
        byId('comparison-json').textContent = json(raw);
    }
    function renderResult(record) {
        const result = recordResult(record);
        if (!result) return;
        selected = record;
        byId('outcome').hidden = false;
        const state = outcomeState(record);
        byId('result-heading').textContent = state === 'accepted' ? 'A platform within reach.'
            : state === 'inconclusive' ? 'The allowance ended. The question remains.'
                : state === 'rejected' ? 'This charter needs a different construction.' : 'Inspect the current construction.';
        const summary = byId('outcome-summary');
        summary.dataset.state = state;
        summary.textContent = state === 'accepted'
            ? 'ACCEPTED · The constructed platform satisfies this frozen finite charter. Reuse and successor checks have their own scope.'
            : state === 'inconclusive'
                ? 'INCONCLUSIVE · ' + (record.wrapperOutcome || 'Finite work or resources ended before acceptance. This is not a proof of infeasibility.')
                : state.toUpperCase() + ' · ' + (result.reason || 'Inspect the retained stage evidence. Earlier accepted parents remain within their original scope.');
        byId('stages').replaceChildren();
        for (const [index, stage] of (result.stages || []).entries()) renderStage(stage, index);
        byId('result-facts').replaceChildren();
        fact('Current outcome', state);
        fact('Stage artifacts', (result.stages || []).length);
        fact('Synthetic scope', (recordCharter(record)?.controls ?? '?') + ' controls');
        fact('Intended uses', recordCharter(record)?.intendedUses ?? '?');
        renderComparisons(result);
        byId('resource-panel').hidden = false;
        byId('resources').textContent = json({currentCampaign: result.resources, lineage: result.lineage,
            reuse: result.reuse, elapsedReceipt: record.elapsedReceipt || null,
            completeHistoryAccount: savedState.resourceAccount || null});
        byId('query-panel').hidden = false;
        byId('queries').textContent = json(result.queryResults || []);
        byId('bindings').textContent = json({bindings: record.bindings || null, charter: recordCharter(record),
            invalidations: result.invalidations, lineage: result.lineage});
    }
    function renderHistory() {
        const all = campaigns();
        byId('history-status').textContent = all.length
            ? all.length + ' retained campaigns in capability history ' + (savedState.workspaceId || '') + '. Earlier failures remain visible.'
            : 'No discovery-lab campaigns recorded.';
        byId('events').replaceChildren();
        if (!all.length) node('li', byId('events'), 'No construction attempts yet.');
        for (const [index, record] of all.entries()) {
            const result = recordResult(record);
            const charter = recordCharter(record);
            const li = node('li', byId('events'));
            node('h4', li, 'Campaign ' + (index + 1) + ' · ' + outcomeState(record));
            node('p', li, charter ? charter.controls + ' controls · error ≤ ' + charter.accuracy
                + ' · ' + charter.intendedUses + ' intended uses · ' + charter.topology + ' placement'
                : 'Retained interruption or rejected attempt. Inspect its original event.');
            if (record.wrapperOutcome || result?.reason) node('p', li, record.wrapperOutcome || result.reason);
            const details = node('details', li);
            node('summary', details, 'Inspect this frozen campaign and its full evidence');
            const full = node('pre', details, json(record));
            full.tabIndex = 0;
            full.setAttribute('aria-label', 'Complete campaign ' + (index + 1));
            full.setAttribute('role', 'group');
        }
    }
    async function refresh() {
        if (refreshing) { refreshAgain = true; return; }
        refreshing = true;
        try {
            savedState = await history.state();
            if (!savedState || !Array.isArray(savedState.campaigns)) throw Error('The existing history bridge returned an unsupported state.');
            const all = campaigns();
            const latest = all.at(-1);
            if (latest && latest !== selected && recordResult(latest)) {
                const restoreCharter = selected === null && !editorTouched && !manifestPending;
                renderResult(latest);
                if (restoreCharter) fill(recordCharter(latest));
            }
            if (!all.length && selected) {
                selected = null;
                byId('outcome').hidden = true;
                for (const name of ['comparison', 'resource', 'query']) byId(name + '-panel').hidden = true;
                byId('bindings').textContent = 'No campaign.';
                message('No campaign is recorded in the selected capability history. No construction restarted.');
            }
            renderHistory();
            if (savedState.resourceAccount) {
                byId('resource-panel').hidden = false;
                const result = recordResult(selected);
                byId('resources').textContent = json({currentCampaign: result?.resources || null,
                    lineage: result?.lineage || null, reuse: result?.reuse || null,
                    elapsedReceipt: selected?.elapsedReceipt || null,
                    completeHistoryAccount: savedState.resourceAccount});
            }
            updateDraftState();
        } catch (reason) { error(reason); }
        finally {
            refreshing = false;
            controls();
            if (refreshAgain) { refreshAgain = false; void refresh(); }
        }
    }
    async function operation(action) {
        if (busy) return;
        busy = true;
        clearError();
        controls();
        try { await action(); }
        catch (reason) { error(reason); }
        finally { busy = false; await refresh(); controls(); }
    }
    function assertRunnable() {
        if (!savedState.ready || savedState.locked) throw Error(savedState.reason || 'The existing workspace is not ready.');
        if (manifestPending) throw Error('Apply the edited JSON charter before construction.');
        if (!byId('public-confirmation').checked) throw Error('Confirm the supplied synthetic scope before constructing.');
    }
    async function run(charter, parent) {
        assertRunnable();
        message('Reserving evidence storage, constructing the candidate and checking its finite obligations…');
        const record = await history.run(charter, {parent});
        if (!recordResult(record)) throw Error('The workspace did not return a retained campaign. Inspect the existing recovery controls.');
        renderResult(record);
        fill(recordCharter(record) || charter);
        message('Campaign retained. ' + outcomeState(record).toUpperCase() + ' applies to the frozen synthetic charter below.');
        byId('result-heading').focus();
    }
    for (const [key, [id, options]] of Object.entries(groups)) {
        for (const value of options) {
            const label = node('label', byId(id));
            const input = node('input', label);
            input.type = 'checkbox';
            input.value = value;
            input.id = 'lab-' + key + '-' + value;
            node('span', label, value);
        }
    }
    for (const [key, value] of Object.entries(draft.budget)) {
        const field = node('div', byId('budget-fields'), undefined, 'field');
        const label = node('label', field, budgetLabels[key] || key);
        label.htmlFor = 'lab-budget-' + key;
        const input = node('input', field);
        input.id = 'lab-budget-' + key;
        input.type = 'number'; input.min = '0'; input.step = '1'; input.required = true; input.value = String(value);
    }
    byId('form').addEventListener('input', event => {
        if (event.target !== byId('public-confirmation')) editorTouched = true;
        if (event.target === byId('charter-json')) {
            manifestPending = true;
            message('JSON charter edited. Apply charter to validate these data before construction. Earlier evidence stays historical.');
        }
        updateDraftState();
    });
    byId('form').addEventListener('change', event => {
        if (event.target === byId('charter-json')) return;
        updateDraftState();
    });
    byId('form').addEventListener('submit', event => {
        event.preventDefault();
        void operation(async () => {
            const next = read();
            const parent = latestAccepted();
            await run(next, parent && !same(recordCharter(parent), next) ? parent : null);
        });
    });
    byId('defaults').addEventListener('click', () => {
        editorTouched = true;
        fill(runtime.DEFAULT_CHARTER);
        message('Model defaults restored as an unqualified draft. Every recorded campaign remains in history.');
    });
    byId('apply-charter').addEventListener('click', () => {
        clearError();
        try {
            const text = byId('charter-json').value;
            if (new TextEncoder().encode(text).length > 20000) throw Error('The charter editor is limited to 20,000 bytes.');
            if (typeof runtime.parseCharter !== 'function') throw Error('The strict charter parser is unavailable. Use the bounded controls.');
            const next = runtime.parseCharter(text);
            fill(next);
            message('Charter data validated and applied to controls. This draft still needs construction and qualification.');
        } catch (reason) { error(reason); }
    });
    byId('successor').addEventListener('click', () => {
        void operation(async () => {
            const parent = latestAccepted();
            if (!parent || recordCharter(parent).controls >= 4) throw Error('An accepted three-control parent is required for this stronger challenge.');
            const next = copy(recordCharter(parent));
            next.controls += 1;
            next.memory = Math.max(next.memory, 16);
            if (!next.operations.includes('flip-w')) next.operations.push('flip-w');
            await run(runtime.validateCharter(next), parent);
        });
    });
    byId('route').addEventListener('change', controls);
    byId('export-account').addEventListener('click', () => {
        void operation(async () => {
            if (typeof history.accountReceipt !== 'function') throw Error('The resource account receipt is unavailable.');
            const receipt = await history.accountReceipt();
            const url = URL.createObjectURL(new Blob([json(receipt)], {type: 'application/json'}));
            const link = node('a', document.body);
            link.hidden = true; link.href = url; link.download = 'discovery-lab-resource-account.json';
            link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
            message('Resource account receipt exported. Unknown reservations remain explicitly unknown.');
        });
    });
    byId('export-request').addEventListener('click', () => {
        void operation(async () => {
            if (!selected || outcomeState(selected) !== 'accepted' || savedState.locked) throw Error('Choose a retained accepted campaign first.');
            const request = await history.workRequest(selected, byId('route').value);
            const url = URL.createObjectURL(new Blob([json(request)], {type: 'application/json'}));
            const link = node('a', document.body);
            link.hidden = true; link.href = url; link.download = 'discovery-lab-' + byId('route').value.toLowerCase() + '-review-draft.json';
            link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
            message('Zero-cap review draft exported. No work was submitted, paid or remotely executed.');
        });
    });
    fill(draft);
    if (typeof history.subscribe === 'function') history.subscribe(() => { void refresh(); });
    void refresh();
    return {refresh};
}
