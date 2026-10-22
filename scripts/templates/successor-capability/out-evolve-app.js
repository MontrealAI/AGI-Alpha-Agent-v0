// SPDX-License-Identifier: Apache-2.0
// Additive v2 constructor UI. The original v1 workshop keeps its own storage and events.
(() => {
    const byId = id => document.getElementById(id);
    const view = name => byId(`evolve-${name}`);
    let record = outEvolve.createOutEvolveWorkspace();
    let packageValue = null;
    let checkpoint = null;
    let runningApparatus = null;
    let database = null;
    let storedRevision = null;
    let storedIdentity = null;
    let busyNow = false;
    let cancelled = false;
    let unsaved = false;
    let readyNow = false;
    let pendingEvaluation = null;
    let executionCheckpoint = null;
    let executionCancel = false;
    let executionUnsaved = null;
    let executionRestored = false;
    const json = value => JSON.stringify(value, null, 2);
    const pause = () => new Promise(resolve => setTimeout(resolve, 16));
    const freshSeed = () => globalThis.crypto.getRandomValues(new Uint32Array(1))[0];
    const setStatus = text => { view('status').textContent = text; };
    const asError = error => String(error?.message || error).slice(0, 1000);
    const resultStatus = value => String(value?.status || '').toLowerCase();
    const failedStatus = value => ['fail', 'failed', 'exhausted', 'infeasible'].includes(resultStatus(value));
    const pendingSearch = () => ['cancelled', 'searching', 'qualified'].includes(checkpoint?.status);

    function problem(error) {
        view('error').hidden = false;
        view('error').textContent = asError(error);
    }
    function clearProblem() { view('error').hidden = true; view('error').textContent = ''; }
    function download(value, filename) {
        const url = URL.createObjectURL(new Blob([JSON.stringify(value)], {type: 'application/json'}));
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    function node(tag, parent, text) {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        parent.append(element);
        return element;
    }
    function qualifiedFinalization() {
        if (checkpoint?.status !== 'qualified') return null;
        const result = outEvolveConstructor.advanceSearch(checkpoint, {steps: 0});
        const parent = checkpoint.inheritance.parent || null;
        const projected = outEvolvePackages.projectedFreezeCostCapability(checkpoint.apparatus, result, {parent});
        return {result, parent, projected, funded: projected.total <= checkpoint.options.maxCost};
    }
    function qualifiedRecoveryStatus() {
        const pending = qualifiedFinalization();
        if (!pending.funded) return 'The candidate checkpoint is retained, but package qualification exceeds its frozen budget. No package has been accepted for this search.';
        if (!outEvolve.searchHistoryCapacity(record, checkpoint).canFinalize) return 'The candidate checkpoint is retained, but this history cannot retain its remaining acceptance records. Export the checkpoint.';
        return 'Qualified search recovered. Finish qualifying its package without repeating construction work.';
    }
    function capacityNotice(capacity, declined = false) {
        const message = capacity.fitsSeparateHistory
            ? 'This history cannot reserve room for another complete evaluation report. Export it or start a separate history and import the package there.'
            : 'This workspace cannot reserve a complete evaluation report for this package and its frozen bounds. Export the package for separate evidence.';
        return message + (declined ? ' No evaluation was run.' : '');
    }
    function reportCapacity(kind, exposures = exposedCases()) {
        return packageValue ? outEvolve.evaluationHistoryCapacity(record, packageValue, kind, exposures) : null;
    }
    function requireReportCapacity(kind, exposures) {
        if (pendingEvaluation && !pendingEvaluation.exported) {
            setStatus('Export the unrecorded evaluation before starting more work. Its complete generated report is retained in this session.');
            return null;
        }
        const capacity = reportCapacity(kind, exposures);
        if (!capacity?.canRun) { setStatus(capacity ? capacityNotice(capacity, true) : 'Import or construct a package first.'); return null; }
        return capacity;
    }
    function controls() {
        const reportBlocked = pendingEvaluation && !pendingEvaluation.exported || Boolean(executionUnsaved);
        view('form').setAttribute('aria-busy', String(busyNow));
        for (const name of ['purpose', 'constraints', 'topology', 'budget', 'apparatus', 'construct', 'import']) {
            view(name).disabled = !readyNow || busyNow || unsaved || reportBlocked;
        }
        if (pendingSearch()) view('construct').disabled = true;
        view('new-history').disabled = !readyNow || busyNow || unsaved || reportBlocked || !record.events.length;
        view('cancel').disabled = !busyNow || !['cancelled', 'searching'].includes(checkpoint?.status) || cancelled;
        const finalization = qualifiedFinalization();
        const capacity = checkpoint ? outEvolve.searchHistoryCapacity(record, checkpoint) : null;
        view('resume').disabled = !readyNow || busyNow || unsaved || reportBlocked || checkpoint === null
            || (finalization ? !finalization.funded || !capacity.canFinalize
                : !['cancelled', 'searching'].includes(checkpoint.status) || !capacity.canAdvance);
        view('resume').textContent = finalization ? 'Finish qualifying package' : 'Resume search';
        const exposures = packageValue ? exposedCases() : [];
        const reuseCapacity = reportCapacity('reuse', exposures), successorCapacity = reportCapacity('successor', exposures);
        for (const [name, capacity] of [['reuse', reuseCapacity], ['successor', successorCapacity]]) {
            view(name).disabled = !readyNow || busyNow || unsaved || reportBlocked || !packageValue || !capacity?.canRun;
        }
        if (packageValue?.scope?.includes('reservoir')) view('successor').disabled = true;
        view('successor').textContent = packageValue?.scope?.includes('reservoir')
            ? 'Reservoir scope already qualified' : 'Build successor';
        for (const name of ['saved', 'open']) view(name).disabled = !readyNow || busyNow || unsaved || reportBlocked || !view('saved').value;
        const denied = !reuseCapacity?.canRun ? reuseCapacity
            : !packageValue?.scope?.includes('reservoir') && !successorCapacity?.canRun ? successorCapacity : null;
        view('capacity').textContent = reportBlocked
            ? 'An unrecorded evaluation is retained. Export its complete report before more work.' : denied ? capacityNotice(denied) : '';
        view('export-report').hidden = !pendingEvaluation;
        view('export-package').disabled = !packageValue;
        view('export-history').disabled = !record.events.length;
        view('retry-save').hidden = !unsaved;
        executionControls();
    }
    function renderHistory() {
        const list = view('events');
        list.replaceChildren();
        const labels = {
            brief: 'Purpose and constraints frozen', 'search-started': 'Construction search started',
            'search-stopped': 'Construction search stopped', 'search-paused': 'Unfinished search retained at the storage bound',
            'package-frozen': 'Executable capability frozen',
            reuse: 'Frozen package tested on new uses', comparison: 'Matched comparisons recorded',
            successor: 'Scope-expanding successor accepted', failure: 'Failed attempt retained', execution: 'Out-Execute completion progress'
        };
        let failures = 0;
        let inconclusive = 0;
        for (const event of record.events) {
            const payload = event.payload;
            const outcome = event.kind === 'execution' ? {status: payload.checkpoint.status} : payload;
            const item = node('li', list);
            if (event.kind === 'failure' && resultStatus(payload) !== 'inconclusive'
                || failedStatus(outcome)) { item.dataset.result = 'fail'; failures += 1; }
            else if (['inconclusive', 'cancelled'].includes(resultStatus(outcome))) { inconclusive += 1; }
            else if (['qualified', 'pass'].includes(resultStatus(payload)) || event.kind === 'package-frozen') item.dataset.result = 'pass';
            const label = event.kind === 'failure' && resultStatus(payload) === 'inconclusive'
                ? 'Inconclusive attempt retained' : event.kind === 'search-stopped' && payload.status === 'searching'
                ? 'Search checkpoint saved' : event.kind === 'successor' && resultStatus(payload) !== 'pass'
                    ? 'Scope-expanding successor evaluated' : labels[event.kind] || event.kind;
            node('h4', item, `${event.sequence + 1}. ${label}`);
            const description = payload.message || payload.reason || payload.purpose
                || payload.checkpoint?.status || payload.status || payload.package?.digest || 'Frozen, append-only event.';
            node('p', item, String(description));
            if (event.kind === 'successor') node('p', item, payload.oldScope?.status === 'FAIL'
                ? 'The old package is insufficient for the expanded scope. Its failure and the new obligations remain in this record.'
                : `Recorded prior-scope result: ${payload.oldScope?.status || 'unreported'}. Inspect the report before treating this attempt as a new function.`);
            const details = node('details', item);
            node('summary', details, 'Inspect this original event');
            const pre = node('pre', details, json(event));
            pre.tabIndex = 0;
            pre.setAttribute('aria-label', `Out-Evolve event ${event.sequence + 1}`);
            pre.setAttribute('role', 'group');
        }
        if (!record.events.length) node('li', list, 'No construction attempts recorded.');
        view('retained').textContent = failures || inconclusive
            ? `${failures} failed attempt${failures === 1 ? '' : 's'} and ${inconclusive} inconclusive result${inconclusive === 1 ? '' : 's'} retained. Later success does not replace them.`
            : 'Failures and interrupted searches stay visible after later successes.';
        view('history-json').textContent = json(record);
        controls();
    }
    function renderPackage(value) {
        if (!value) return;
        packageValue = value;
        view('outcome').hidden = false;
        view('result-heading').textContent = 'An executable preparation interface.';
        view('mechanism').textContent = 'A generated composition changes experimental access to this apparatus. '
            + 'Its independent checker derives preservation and a recurring error envelope from the supplied model.';
        view('program').textContent = json({ast: value.ast, installations: value.installations,
            executablePlan: value.executablePlan, interfaces: value.interfaces, certificate: value.certificate,
            scope: value.scope, errorEnvelope: value.errorEnvelope, invalidationRules: value.invalidationRules,
            parentAssets: value.parentAssets});
        const metrics = view('metrics');
        metrics.replaceChildren();
        const inherited = Boolean(value.parentAssets?.parentDigest);
        const costMetrics = inherited ? [
            ['Frozen package construction cost', value.costLedger?.total ?? 'Inspect ledger'],
            ['Frozen package lineage cost', (value.parentAssets.ancestorCost || 0) + value.costLedger.total]
        ] : [['Frozen package construction cost', value.costLedger?.total ?? 'Inspect ledger']];
        for (const [label, text] of [
            ['Qualified scope', Array.isArray(value.scope) ? value.scope.join(', ') : json(value.scope)],
            ...costMetrics,
            ['Error envelope', json(value.errorEnvelope)],
            ['Package identity', String(value.digest).slice(0, 16) + '…']
        ]) {
            const box = node('div', metrics);
            node('dt', box, label); node('dd', box, String(text));
        }
        renderExperimentWork(null);
        controls();
    }
    function renderExperimentWork(report) {
        let text = 'Later evaluation costs are reported separately from frozen package construction.';
        if (report?.kind === 'matched-comparison') {
            const total = (report.runs || []).reduce((sum, run) => sum + (run.ledger?.total || 0), 0)
                + (report.sensingCorrection?.ledger?.total || 0) + (report.evaluationOverhead?.total || 0);
            text = `Matched experiment: ${report.relation}. ${total} model units across the recorded candidate, `
                + 'classical planner, scratch construction, sensing comparison and comparison audit. '
                + 'The input cap applies to each construction.';
            const sensing = report.sensingCorrection;
            if (sensing) {
                const qualified = sensing.qualification?.status === 'qualified';
                const completed = sensing.search?.complete === true;
                text += ` Sensing attempt: ${sensing.ledger.total} model units; `
                    + (qualified ? 'qualified' : completed ? 'did not qualify' : 'qualification inconclusive')
                    + `; search ${sensing.search?.status || 'unreported'}.`;
            }
        } else if (report?.kind === 'frozen-package-reuse') {
            text = `This frozen reuse evaluation: ${report.status}; ${report.ledger.total} model units, `
                + 'including its import check and qualification. Earlier construction and comparisons remain in the history.';
        } else if (report?.kind === 'scope-expanding-successor') {
            const costs = report.costs;
            text = `This successor experiment: ${report.status}; ${costs.remainingAfterAcceptance ?? costs.remaining} model units of remaining work, `
                + `${costs.cumulativeAfterAcceptance ?? costs.cumulative} including ancestor construction. `
                + (costs.scratchQualified === false
                    ? `Scratch comparator inconclusive; ${costs.scratchAfterAcceptance ?? costs.scratchConstructionWork} model units actually spent. `
                    : `Matched scratch work: ${costs.scratchAfterAcceptance ?? costs.constructionFromScratch ?? 'inconclusive'} model units. `)
                + (report.result?.freeze?.status === 'not-run'
                    ? 'Successor package acceptance was not run; its candidate ledger and checkpoint remain in the report. No successor package was accepted.'
                    : 'These amounts include the reported scope diagnostics and acceptance checks.');
        }
        view('work-total').textContent = text;
    }
    async function openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('agialpha.out-evolve.workspace.v1', 1);
            request.onupgradeneeded = () => request.result.createObjectStore('history');
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error || Error('Local history storage is unavailable.'));
        });
    }
    async function readSaved(key = 'current') {
        if (!database) return null;
        return new Promise((resolve, reject) => {
            const tx = database.transaction('history', 'readonly');
            const request = tx.objectStore('history').get(key);
            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => reject(request.error);
        });
    }
    async function requireSavedContinuation(incoming) {
        const saved = await readSaved(incoming.id);
        if (!saved) return;
        const inspected = await outEvolve.inspectOutEvolveWorkspace(saved);
        outEvolve.requireHistoryContinuation(inspected.workspace, incoming);
    }
    async function refreshHistories() {
        if (!database) return;
        const rows = await new Promise((resolve, reject) => {
            const request = database.transaction('history', 'readonly').objectStore('history').getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
        const select = view('saved');
        select.replaceChildren();
        const unique = new Map(rows.filter(row => row?.id && Array.isArray(row.events)).map(row => [row.id, row]));
        for (const [id, row] of unique) {
            const purpose = row.events.filter(event => event.kind === 'brief').at(-1)?.payload?.purpose;
            const option = node('option', select, `${purpose?.slice(0, 55) || 'Imported capability history'} · ${row.events.length} events`);
            option.value = id;
        }
        if (unique.has(record.id)) select.value = record.id;
        if (!unique.size) { const option = node('option', select, 'No saved histories'); option.value = ''; }
        controls();
    }
    async function persist() {
        renderHistory();
        try {
            if (!database) throw Error('Local storage is unavailable. Export this history before leaving.');
            await new Promise((resolve, reject) => {
                const tx = database.transaction('history', 'readwrite');
                const objectStore = tx.objectStore('history');
                const request = objectStore.get('current');
                let reason = null;
                request.onsuccess = () => {
                    const saved = request.result || null;
                    if ((saved?.id || null) !== storedIdentity || (saved?.revision ?? null) !== storedRevision) {
                        reason = Error('Another tab changed the saved Out-Evolve history. Export this copy before reloading.');
                        tx.abort(); return;
                    }
                    try {
                        if (saved?.id) outEvolve.requireHistoryContinuation(saved, record);
                    } catch (error) { reason = error; tx.abort(); return; }
                    const targets = new Map();
                    if (saved?.id && saved.id !== record.id) targets.set(saved.id, saved);
                    targets.set(record.id, record);
                    let pending = targets.size;
                    for (const [id, incoming] of targets) {
                        const archived = objectStore.get(id);
                        archived.onsuccess = () => {
                            if (reason) return;
                            try {
                                if (archived.result) outEvolve.requireHistoryContinuation(archived.result, incoming);
                            } catch (error) { reason = error; tx.abort(); return; }
                            if (--pending) return;
                            if (saved?.id && saved.id !== record.id) objectStore.put(saved, saved.id);
                            objectStore.put(record, record.id);
                            objectStore.put(record, 'current');
                        };
                    }
                };
                tx.oncomplete = resolve;
                tx.onerror = () => reject(reason || tx.error || Error('Saving failed.'));
                tx.onabort = () => reject(reason || tx.error || Error('Saving was interrupted.'));
            });
            storedRevision = record.revision;
            storedIdentity = record.id;
            unsaved = false;
            view('storage').textContent = 'Saved locally. Reload resumes this history; export a copy for backup. The original workshop has separate storage.';
            await refreshHistories();
        } catch (error) {
            unsaved = true;
            view('storage').textContent = 'This history has not been saved. Export it now or retry this same save.';
            problem(error);
        }
        controls();
        return !unsaved;
    }
    async function append(kind, payload) {
        record = await outEvolve.appendOutEvolveEvent(record, kind, payload);
        return persist();
    }
    async function retainEvaluation(kind, report, capacity) {
        pendingEvaluation = {schema: 'out-evolve-unrecorded-evaluation/v1', eventKind: kind,
            history: record, package: packageValue, report, exported: false};
        try {
            const retained = outEvolve.retainedEvaluationReport(report);
            const eventKind = kind === 'reuse' ? 'reuse' : report.package ? 'successor' : 'failure';
            const payload = eventKind === 'failure'
                ? {status: retained.status, message: retained.reason || 'No qualifying successor construction found within budget.', report: retained}
                : retained;
            const bytes = new TextEncoder().encode(outEvolveConstructor.canonical(payload)).length;
            if (bytes > capacity.reportBytes) throw Error('The generated report exceeded its conservative storage reservation.');
            const saved = await append(eventKind, payload);
            pendingEvaluation = null;
            return {report: retained, saved};
        } catch (error) {
            pendingEvaluation.reason = asError(error);
            problem(error);
            setStatus('The evaluation completed but its report could not enter this history. Export the unrecorded evaluation now; its complete report and source package are retained in this session.');
            controls();
            return null;
        }
    }
    function readBrief() {
        const purpose = view('purpose').value.trim();
        const constraints = view('constraints').value.trim();
        const budget = Number(view('budget').value);
        const apparatus = JSON.parse(view('apparatus').value);
        if (!purpose || !constraints) throw Error('Provide the purpose and what must be preserved.');
        if (!Number.isSafeInteger(budget) || budget < 1 || budget > 100000) throw Error('Use an integer budget between 1 and 100,000 model units.');
        return {purpose, constraints, budget, apparatus};
    }
    function fillDefault() {
        view('apparatus').value = json(outEvolveApparatus.apparatus(view('topology').value));
    }
    function checkpointApparatus() {
        return checkpoint?.apparatus || outEvolve.latestOutEvolveEvent(record, 'brief')?.payload.apparatus;
    }
    function restoreView() {
        view('outcome').hidden = !packageValue;
        if (packageValue) renderPackage(packageValue);
        else view('result-heading').textContent = 'No frozen capability in this history.';
        const brief = outEvolve.latestOutEvolveEvent(record, 'brief')?.payload;
        if (brief) {
            view('purpose').value = brief.purpose; view('constraints').value = brief.constraints;
            view('budget').value = String(brief.budget); view('apparatus').value = json(brief.apparatus);
        }
        const latestFrozen = record.events.filter(event => ['package-frozen', 'successor'].includes(event.kind)).at(-1);
        const comparison = record.events.filter(event => event.kind === 'comparison'
            && event.sequence >= (latestFrozen?.sequence ?? 0)).at(-1);
        view('comparison').textContent = latestFrozen?.kind === 'successor' ? json(latestFrozen.payload.costs)
            : comparison ? json(comparison.payload) : 'Not evaluated.';
        const evidence = record.events.filter(event => (['reuse', 'successor'].includes(event.kind)
            || event.kind === 'failure' && event.payload.report?.kind === 'scope-expanding-successor')
            && event.sequence >= (latestFrozen?.sequence ?? 0)).at(-1);
        view('evidence').textContent = evidence ? json(evidence.payload.report || evidence.payload) : 'No evaluation recorded.';
        const latestWork = record.events.filter(event => (['comparison', 'reuse', 'successor'].includes(event.kind)
            || event.kind === 'failure' && event.payload.report?.kind === 'scope-expanding-successor')
            && event.sequence >= (latestFrozen?.sequence ?? 0)).at(-1);
        renderExperimentWork(latestWork?.payload.report || latestWork?.payload);
        renderExecution();
        renderHistory();
    }
    function exposedCases() {
        const ids = value => Array.isArray(value) ? value : [];
        return [...new Set(record.events.flatMap(event => [
            ...ids(event.payload.exposedCaseIds), ...ids(event.payload.reuse?.exposedCaseIds)
        ]))];
    }
    async function finalizeQualifiedSearch() {
        const pending = qualifiedFinalization();
        if (!pending) throw Error('No qualified search is awaiting package acceptance.');
        if (!pending.funded) {
            view('result-heading').textContent = 'Candidate found; package qualification is unfunded.';
            setStatus(`Package qualification is inconclusive: ${pending.projected.total} model units would exceed the frozen ${checkpoint.options.maxCost}-unit cap. No package replay was run. Export the retained search evidence or start a separate history.`);
            return;
        }
        if (!outEvolve.searchHistoryCapacity(record, checkpoint).canFinalize) {
            setStatus('Package qualification is unfinished: this history cannot retain both remaining acceptance records. No package replay was run. Export the retained checkpoint.');
            return;
        }
        const {result, parent} = pending;
        runningApparatus = checkpointApparatus();
        const frozen = await outEvolvePackages.freezeCapability(runningApparatus, result, {parent});
        if (!await append('package-frozen', {status: 'qualified', package: frozen})) return;
        checkpoint = null;
        renderPackage(frozen);
        setStatus('Capability qualified in the supplied model. Running matched comparisons…');
        const comparison = await outEvolveEvaluation.compareCapability(frozen, {searchOptions: result.checkpoint?.options});
        view('comparison').textContent = json(comparison);
        renderExperimentWork(comparison);
        if (!await append('comparison', comparison)) return;
        setStatus('Capability qualified. Test new uses with the frozen package, or build its scope-expanding successor.');
    }
    async function finishSearch(result) {
        await append('search-stopped', {status: result.status, reason: result.reason,
            checkpoint: outEvolveConstructor.exportSearchCheckpoint(result.checkpoint), ledger: result.ledger});
        if (unsaved) return;
        checkpoint = result.checkpoint;
        if (result.status === 'qualified') await finalizeQualifiedSearch();
        else {
            checkpoint = result.checkpoint;
            view('result-heading').textContent = result.status === 'cancelled' ? 'Search cancelled; evidence retained.' : 'No qualifying construction found within budget.';
            setStatus(result.reason || 'No qualifying construction found within budget.');
        }
    }
    async function runSearch() {
        while (true) {
            const capacity = outEvolve.searchHistoryCapacity(record, checkpoint);
            if (!capacity.canAdvance) {
                const reason = 'Search is unfinished: the bounded history has reserved its final recovery record. '
                    + 'No further constructor steps were run. Export this history to retain the complete replayable checkpoint.';
                await append('search-paused', {status: 'INCONCLUSIVE', reason, pauseReason: 'history-capacity',
                    checkpoint: outEvolveConstructor.exportSearchCheckpoint(checkpoint)});
                view('result-heading').textContent = 'Search paused; unfinished work retained.';
                setStatus(reason);
                return;
            }
            const result = outEvolveConstructor.advanceSearch(checkpoint, {steps: 16, cancel: cancelled, timeLimitMs: 1000});
            checkpoint = result.checkpoint;
            controls();
            if (result.status !== 'searching') { await finishSearch(result); return; }
            if (!await append('search-stopped', {status: result.status, reason: result.reason,
                checkpoint: outEvolveConstructor.exportSearchCheckpoint(result.checkpoint), ledger: result.ledger})) return;
            setStatus(`Searching bounded compositions. ${result.ledger?.synthesis ?? result.checkpoint?.expanded ?? 'More'} model work recorded; failed candidates remain in the ledger.`);
            await pause();
        }
    }
    async function withWork(action, evaluation = null) {
        if (busyNow || unsaved || !readyNow || executionUnsaved || pendingEvaluation && !pendingEvaluation.exported) return;
        clearProblem(); busyNow = true; cancelled = false; controls();
        try { await action(); }
        catch (error) {
            problem(error);
            let failureRetained = false;
            try { await append('failure', {status: 'FAIL', message: asError(error), ...(evaluation
                ? {operation: evaluation, packageDigest: packageValue?.digest || null} : {draft: {
                purpose: view('purpose').value, constraints: view('constraints').value,
                budget: view('budget').value, apparatusText: view('apparatus').value.slice(0, 100000)
            }})}); failureRetained = true; }
            catch (recordError) { problem(recordError); }
            setStatus(failureRetained ? 'This attempt failed. Its evidence remains in the history.'
                : 'This attempt failed and its failure record could not be added. The existing history is retained; export it or start a separate history.');
        } finally { busyNow = false; controls(); }
    }
    const executionSource = () => ({compilerSha256: SOURCE_HASH, checkerSha256: SOURCE_HASH,
        evaluatorVersion: outExecuteModel.CHECKER_VERSION});
    const executionPending = () => ['PAUSED', 'CANCELLED'].includes(executionCheckpoint?.status);
    function executionControls() {
        const blocked = !readyNow || busyNow || unsaved || Boolean(executionUnsaved)
            || pendingEvaluation && !pendingEvaluation.exported;
        for (const name of ['base', 'change', 'outside', 'extend', 'model']) byId(`execute-${name}`).disabled = blocked || executionPending();
        byId('execute-start').disabled = blocked || executionPending();
        for (const name of ['step', 'finish']) byId(`execute-${name}`).disabled = blocked || !executionPending();
        byId('execute-pause').disabled = !executionPending() || unsaved || executionCancel || executionCheckpoint?.status === 'CANCELLED';
        byId('execute-export').disabled = !executionCheckpoint && !executionUnsaved;
        for (const name of ['manager', 'jobs', 'fleet']) byId(`execute-${name}`).disabled = blocked || executionCheckpoint?.status !== 'COMPLETE';
    }
    function renderExecution() {
        const latest = executionCheckpoint || outEvolve.latestOutEvolveEvent(record, 'execution')?.payload.checkpoint;
        byId('execute-result').hidden = !latest;
        if (!latest) { byId('execute-status').textContent = 'No completion run yet. This work shares the construction history below.'; return; }
        const complete = latest.completion;
        byId('execute-status').textContent = `${latest.status}: ${latest.next} of ${latest.contracts.length} components processed. ${latest.reason || ''}`;
        byId('execute-acceptance').textContent = complete && (executionRestored || !outExecuteModel.same(latest.source, executionSource()))
            ? 'Historical finite-model acceptance rechecked. No new execution or external authority was created by reopening.'
            : complete ? complete.selection.status === 'OPTIMAL'
            ? `Current finite-model optimum accepted: ${complete.selection.cost}.`
            : 'Current finite model proved infeasible; no artifact delivered.' : 'Unfinished: no current accepted artifact.';
        const change = complete?.change || latest.plan;
        byId('execute-changes').textContent = `Preserved: ${change.retained.join(', ') || 'none'}. Rebuild: ${change.invalidated.map(item => `${item.module} (${item.reason})`).join('; ') || 'none'}. `
            + (complete?.change.semanticStop ? 'Complete external values agree. The outside optimization stopped; current acceptance was still checked.' : 'No semantic stopping claim.');
        const work = latest.work, counted = Object.values(work).reduce((a, b) => a + b, 0);
        const admission = record.events.filter(event => event.kind === 'execution').reduce((total, event) => total
            + event.payload.admissionVerification.total + event.payload.admissionVerification.historyRecheckTotal, 0);
        byId('execute-costs').textContent = `Run work: ${counted} counted model operations. Construction assignments: ${work.constructionAssignments}. Independent local checks: ${work.qualificationAssignments}. Import audit assignments: ${work.reuseAuditAssignments}. Coordinator boundary choices: ${work.boundaryAssignments}. Acceptance boundary choices: ${work.acceptanceBoundaryAssignments}. History admission and recheck work: ${admission} additional operations. These are not money, energy or wall-clock savings; JSON, hashing and host bookkeeping are excluded.`;
        byId('execute-lineage').textContent = `Same project: ${record.id}. Attempt: ${latest.attemptId}. Parent completion: ${complete?.parentDigest || latest.archive.completions.at(-1)?.digest || 'none'}. Historical acceptance does not authorize external execution.`;
        byId('execute-contract').textContent = json({source: latest.source, selector: latest.selection,
            contracts: latest.contracts, selection: complete?.selection || null, artifact: complete?.artifact || null,
            ledger: latest.work, cumulativeCountedWork: complete?.cumulativeCountedWork || null});
        byId('execute-recovery').textContent = executionUnsaved
            ? 'New work could not enter the saved history. Export its complete recovery record before leaving.'
            : 'Progress, failures and acceptance travel in the same whole-history export below. Reopening independently rechecks evidence; it never resumes automatically.';
    }
    function executionCapacity(model = executionCheckpoint?.model, archive = executionCheckpoint?.archive,
        remaining = null) {
        if (!model) throw Error('A complete finite model is required for capacity reservation.');
        const selected = outExecute.selectBoundary(model), domains = outExecuteModel.domainMap(model);
        const rowBytes = selected.decomposition.modules.reduce((total, module) => total
            + outExecuteModel.cardinality(module.interface, domains) * (128 + 8 * (module.interface.length + module.private.length)), 0);
        const bytes = value => new TextEncoder().encode(outEvolveConstructor.canonical(value)).length;
        const checkpointReserve = 25000 + 3 * bytes(model) + 3 * bytes(selected) + 2 * rowBytes + bytes(archive || null);
        const events = (remaining ?? selected.decomposition.modules.length) + 3;
        if (record.events.length + events > outEvolve.WORKSPACE_LIMITS.events
            || bytes(record) + checkpointReserve * events > outEvolve.WORKSPACE_LIMITS.bytes) {
            throw Error('This history cannot reserve complete execution progress and recovery. Export it before starting a separate history. No new execution was started.');
        }
    }
    async function retainExecution(state) {
        executionCheckpoint = state; executionRestored = false;
        executionUnsaved = {schema: 'out-execute-unsaved-recovery/v1', history: record, checkpoint: state};
        try {
            const saved = await append('execution', {projectId: record.id, checkpoint: state});
            // If persistence fails, the appended in-memory history is the retryable authoritative copy.
            executionUnsaved = null;
            renderExecution(); renderHistory(); return saved;
        } catch (error) { renderExecution(); throw error; }
    }
    async function advanceExecutionRun(all) {
        if (!executionPending()) return;
        executionCapacity(executionCheckpoint.model, executionCheckpoint.archive, executionCheckpoint.contracts.length - executionCheckpoint.next);
        if (!outExecuteModel.same(executionCheckpoint.source, executionSource())) {
            throw Error('Installed execution source changed. Export this historical checkpoint; do not resume it under another source.');
        }
        executionCancel = false;
        do {
            const state = await outExecute.advanceExecution(executionCheckpoint, {modules: 1, cancel: executionCancel});
            if (!await retainExecution(state)) return;
            if (state.status !== 'PAUSED' || !all) break;
            await pause();
        } while (true);
    }
    byId('execute-base').addEventListener('click', () => { byId('execute-model').value = json(outExecuteFixtures.containment()); });
    byId('execute-change').addEventListener('click', () => { byId('execute-model').value = json(outExecuteFixtures.containment(true)); });
    byId('execute-outside').addEventListener('click', () => {
        const model = outExecuteModel.clone(executionCheckpoint?.model || outExecuteFixtures.containment());
        const outside = model.factors.find(factor => factor.id === 'outside');
        if (outside) outside.costs = [9, 0];
        byId('execute-model').value = json(model);
    });
    byId('execute-extend').addEventListener('click', () => {
        const model = outExecuteModel.clone(executionCheckpoint?.model || outExecuteFixtures.containment());
        if (!model.variables.some(variable => variable.id === 'z')) {
            model.variables.push({id: 'z', domain: [0, 1]});
            model.factors.push({id: 'newModule', scope: ['b', 'z'], costs: [0, 4, 4, 0]});
        }
        byId('execute-model').value = json(model);
    });
    byId('execute-start').addEventListener('click', () => { void withWork(async () => {
        if (executionPending()) throw Error('Resume the existing attempt, or export it and start a separate history; its frozen inputs cannot be replaced.');
        const raw = byId('execute-model').value;
        if (raw.length > 100000) throw Error('Execution input exceeds the local UI bound.');
        const model = outExecuteModel.validateModel(JSON.parse(raw));
        if (model.variables.length > 8) throw Error('This browser panel admits at most eight variables. Use the separately bounded typed backend for larger models.');
        const completions = record.events.filter(event => event.kind === 'execution' && event.payload.checkpoint.status === 'COMPLETE')
            .map(event => event.payload.checkpoint.completion);
        const archive = {schema: outExecute.ARCHIVE_SCHEMA, completions};
        executionCapacity(model, archive);
        const state = await outExecute.startExecution(model, {source: executionSource(), budget: 1000000, archive});
        await retainExecution(state);
    }, 'out-execute'); });
    byId('execute-step').addEventListener('click', () => { void withWork(() => advanceExecutionRun(false), 'out-execute'); });
    byId('execute-finish').addEventListener('click', () => { void withWork(() => advanceExecutionRun(true), 'out-execute'); });
    byId('execute-pause').addEventListener('click', () => {
        executionCancel = true;
        if (!busyNow) void withWork(async () => {
            if (executionPending()) await retainExecution(await outExecute.advanceExecution(executionCheckpoint, {cancel: true}));
        }, 'out-execute');
        controls();
    });
    byId('execute-export').addEventListener('click', () => {
        download(executionUnsaved ? {...executionUnsaved, history: record}
            : {schema: 'out-execute-recovery/v1', history: record, checkpoint: executionCheckpoint}, 'out-execute-recovery.json');
    });
    for (const [name, target] of [['manager', 'manager-usdc'], ['jobs', 'jobs-agialpha'], ['fleet', 'fleet-qualified-review']]) {
        byId(`execute-${name}`).addEventListener('click', () => { void withWork(async () => {
            const draft = await outExecuteTransport.prepareWorkRequest(await outExecute.retainCompletion(executionCheckpoint),
                {projectId: record.id, target, expectedSource: executionSource()});
            byId('execute-draft').textContent = json(draft);
            await append('comparison', {kind: 'out-execute-inert-work-request', status: 'DRAFT_NOT_SUBMITTED', draft});
            renderHistory(); download(draft, `${target}-unsubmitted-draft.json`);
        }, 'out-execute-draft'); });
    }
    view('form').addEventListener('submit', event => {
        event.preventDefault();
        if (pendingSearch()) {
            setStatus('This history retains a pending search. Use its available Resume or Finish action, or start a separate history. Its original checkpoint is unchanged.');
            controls();
            return;
        }
        void withWork(async () => {
            const brief = readBrief();
            const next = outEvolveConstructor.createSearch(brief.apparatus, {
                maxCost: brief.budget, maxStates: 2000, maxMemoryStates: 2000, maxProgramSize: 12
            });
            if (!await append('brief', brief)) return;
            checkpoint = next; runningApparatus = brief.apparatus;
            if (!await append('search-started', {status: 'searching',
                checkpoint: outEvolveConstructor.exportSearchCheckpoint(checkpoint)})) return;
            setStatus('Constructing an executable preparation interface…');
            await pause(); await runSearch();
        });
    });
    view('new-history').addEventListener('click', () => { void withWork(async () => {
        if (!await persist()) {
            setStatus('A separate history was not started because the current history could not be saved. Its checkpoint is unchanged. Export this copy or retry saving.');
            return;
        }
        record = outEvolve.createOutEvolveWorkspace();
        checkpoint = null; packageValue = null; runningApparatus = null; executionCheckpoint = null; executionRestored = false; executionCancel = false;
        restoreView();
        if (!await persist()) {
            setStatus('The separate empty history has not been saved. Retry saving; the previous history remains saved and can be reopened.');
            return;
        }
        setStatus('Separate construction history started. The previous history and its original checkpoint remain available under saved histories.');
    }); });
    view('cancel').addEventListener('click', () => { cancelled = true; setStatus('Cancelling at the next bounded search step…'); controls(); });
    view('resume').addEventListener('click', () => { void withWork(async () => {
        if (checkpoint?.status === 'qualified') { await finalizeQualifiedSearch(); return; }
        runningApparatus = checkpointApparatus(); setStatus('Resuming the same frozen search bounds…'); await pause(); await runSearch();
    }); });
    view('topology').addEventListener('change', fillDefault);
    view('reuse').addEventListener('click', () => {
        const exposedCaseIds = exposedCases();
        const capacity = requireReportCapacity('reuse', exposedCaseIds);
        if (!capacity) return;
        void withWork(async () => {
        setStatus('Testing new purposes using the unchanged frozen package…'); await pause();
        const report = await outEvolveEvaluation.evaluateFrozenReuse(packageValue, {seed: freshSeed(), exposedCaseIds});
        const retained = await retainEvaluation('reuse', report, capacity);
        if (!retained?.saved) return;
        view('evidence').textContent = json(retained.report);
        renderExperimentWork(retained.report);
        setStatus(`Frozen-package reuse: ${report.status}. All accepted, failed and inconclusive cases are retained.`);
    }, 'reuse'); });
    view('successor').addEventListener('click', () => {
        const exposedCaseIds = exposedCases();
        const capacity = requireReportCapacity('successor', exposedCaseIds);
        if (!capacity) return;
        void withWork(async () => {
        setStatus('Exposing the dormant reservoir and checking which parent assets remain valid…'); await pause();
        const report = await outEvolveEvaluation.buildSuccessor(packageValue, {seed: freshSeed(),
            exposedCaseIds, searchOptions: packageValue.search.limits});
        const retained = await retainEvaluation('successor', report, capacity);
        if (!retained?.saved) return;
        if (report.package) {
            renderPackage(report.package);
            view('comparison').textContent = json(report.costs);
        }
        view('evidence').textContent = json(retained.report);
        renderExperimentWork(retained.report);
        setStatus(`Scope-expanding successor: ${report.status}. `
            + (report.reason || 'Inspect preserved obligations, the prior-scope result and cumulative cost.'));
    }, 'successor'); });
    view('export-report').addEventListener('click', () => {
        if (!pendingEvaluation) return;
        download(pendingEvaluation, 'out-evolve-unrecorded-evaluation.json');
        pendingEvaluation.exported = true;
        setStatus('Unrecorded evaluation exported with its complete report and original history. Start a separate history to continue.');
        controls();
    });
    view('export-history').addEventListener('click', () => download(record, 'out-evolve-history.json'));
    view('export-package').addEventListener('click', () => download(packageValue, 'out-evolve-capability.json'));
    view('retry-save').addEventListener('click', () => { void (async () => {
        if (busyNow || !readyNow) return;
        busyNow = true; controls();
        try {
            if (!await persist()) return;
            clearProblem();
            const inspected = await outEvolve.inspectOutEvolveWorkspace(record);
            record = inspected.workspace; executionCheckpoint = inspected.latestExecution; executionRestored = Boolean(executionCheckpoint); checkpoint = inspected.checkpoint; packageValue = inspected.latestPackage;
            runningApparatus = checkpointApparatus(); restoreView();
            setStatus(checkpoint?.status === 'qualified'
                ? qualifiedRecoveryStatus()
                : checkpoint ? 'Search saved. Resume keeps its original apparatus, bounds and costs.' : 'History saved. Accepted packages and reports remain intact.');
        } catch (error) { problem(error); }
        finally { busyNow = false; controls(); }
    })(); });
    view('open').addEventListener('click', () => { void withWork(async () => {
        const saved = await new Promise((resolve, reject) => {
            const request = database.transaction('history', 'readonly').objectStore('history').get(view('saved').value);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
        const inspected = await outEvolve.inspectOutEvolveWorkspace(saved);
        outEvolve.requireHistoryContinuation(record, inspected.workspace);
        record = inspected.workspace; executionCheckpoint = inspected.latestExecution; executionRestored = Boolean(executionCheckpoint); checkpoint = inspected.checkpoint; packageValue = inspected.latestPackage;
        runningApparatus = checkpointApparatus(); restoreView();
        if (!await persist()) { setStatus('This history has not been saved. Export this copy or retry saving.'); return; }
        setStatus('Saved history opened after semantic checks. Its original events remain intact.');
    }); });
    view('import').addEventListener('change', event => {
        const file = event.target.files?.[0];
        if (!file) return;
        void withWork(async () => {
            if (file.size > outEvolve.EXECUTION_RECOVERY_MAX_BYTES) throw Error('Import exceeds the bounded recovery size.');
            const value = JSON.parse(await file.text());
            if (outEvolve.EXECUTION_RECOVERY_SCHEMAS.includes(value.schema)) {
                const inspected = await outEvolve.inspectExecutionRecovery(value, {current: record});
                await requireSavedContinuation(inspected.workspace);
                record = inspected.workspace; executionCheckpoint = inspected.latestExecution; executionRestored = true;
                checkpoint = inspected.checkpoint; packageValue = inspected.latestPackage; runningApparatus = checkpointApparatus();
                restoreView();
                if (!await persist()) { setStatus('Recovered history is not saved. Export this copy or retry saving.'); return; }
                setStatus(inspected.recovery.appended
                    ? 'Unsaved execution progress independently checked and appended to its original history. No new execution was run.'
                    : 'Execution checkpoint reopened with its complete original history. Historical acceptance is not new execution.');
            } else if (value.schema === outEvolve.WORKSPACE_SCHEMA) {
                const inspected = await outEvolve.inspectOutEvolveWorkspace(value);
                outEvolve.requireHistoryContinuation(record, inspected.workspace);
                await requireSavedContinuation(inspected.workspace);
                record = inspected.workspace; executionCheckpoint = inspected.latestExecution; executionRestored = Boolean(executionCheckpoint); checkpoint = inspected.checkpoint;
                packageValue = inspected.latestPackage; runningApparatus = checkpointApparatus();
                restoreView();
                if (!await persist()) { setStatus('Imported history has not been saved. Export this copy or retry saving.'); return; }
                setStatus('History imported. Package semantics were rechecked; historical reports are not fresh evaluations.');
            } else {
                await outEvolvePackages.importCapability(value);
                const saved = await append('package-frozen', {status: 'qualified', package: value});
                if (outEvolve.packageCompletesSearch(checkpoint, value)) checkpoint = null;
                runningApparatus = checkpointApparatus();
                renderPackage(value);
                if (!saved) { setStatus('Imported package history has not been saved. Export this copy or retry saving.'); return; }
                setStatus('Executable package imported after independent semantic checks.'
                    + (checkpoint?.status === 'qualified'
                        ? ' The earlier candidate checkpoint remains pending its own package acceptance.'
                        : ['cancelled', 'searching'].includes(checkpoint?.status)
                        ? ' The unfinished search remains resumable with its original apparatus, bounds and costs.' : ''));
            }
        }).finally(() => { event.target.value = ''; });
    });
    window.addEventListener('beforeunload', event => {
        if (busyNow || unsaved || executionUnsaved || pendingEvaluation && !pendingEvaluation.exported) { event.preventDefault(); event.returnValue = ''; }
    });
    void (async () => {
        fillDefault(); byId('execute-model').value = json(outExecuteFixtures.containment()); controls();
        try {
            database = await openDatabase();
            const saved = await readSaved();
            if (saved) {
                storedRevision = saved.revision;
                storedIdentity = saved.id;
                const inspected = await outEvolve.inspectOutEvolveWorkspace(saved);
                record = inspected.workspace; executionCheckpoint = inspected.latestExecution; executionRestored = Boolean(executionCheckpoint); checkpoint = inspected.checkpoint; packageValue = inspected.latestPackage;
                storedRevision = record.revision; storedIdentity = record.id;
                runningApparatus = checkpointApparatus();
                restoreView();
                setStatus(checkpoint?.status === 'qualified'
                    ? qualifiedRecoveryStatus()
                    : checkpoint ? 'Saved search recovered. Resume keeps its original bounds, failures and costs.' : 'Saved Out-Evolve history recovered. Frozen package semantics rechecked.');
            }
            view('storage').textContent = 'History is stored locally on this device. Export a copy for backup.';
            await refreshHistories();
        } catch (error) { problem(error); view('storage').textContent = 'Saved history could not be opened. Import an exported copy to recover it.'; }
        readyNow = true; renderExecution(); renderHistory();
    })();
})();
