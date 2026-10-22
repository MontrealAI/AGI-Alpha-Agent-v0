// SPDX-License-Identifier: Apache-2.0
(() => {
    const el = id => document.getElementById('enterprise-' + id);
    let stopRequested = false;
    const source = ENTERPRISE_SOURCES;
    const latest = () => inspected?.enterprises?.attempts.at(-1) || null;
    function refreshEnterprise() {
        const row = latest(), active = inspected?.enterprises?.active;
        const idle = ready && !busy && !pending && (!current || !dirty && !successorEditing);
        el('build').disabled = !idle || !!active;
        el('continue').disabled = !idle || !active || !['ACCEPTED_CONSTRUCTION', 'FROZEN', 'TASKS_COMMITTED', 'INVOCATION_RECONCILED', 'READY_FOR_SUCCESSOR'].includes(active.state);
        el('continue').textContent = active?.state === 'ACCEPTED_CONSTRUCTION' ? 'Freeze accepted construction' : 'Supply future tasks & continue';
        el('seed').disabled = !idle || active?.state !== 'FROZEN';
        el('stop').disabled = !active || !!pending;
        el('export').disabled = !idle || !current;
        el('inspect').disabled = !row?.bundle || busy;
        const labels = {RESERVED: 'Construction reserved', ACCEPTED_CONSTRUCTION: 'Construction accepted', FROZEN: 'Frozen · ready for future tasks', TASKS_COMMITTED: 'Future inputs committed', INVOCATION_RESERVED: 'Future execution reserved', INVOCATION_RECONCILED: 'Future results checked', READY_FOR_SUCCESSOR: 'Ready to construct the successor', SUCCESSOR_RESERVED: 'Successor construction reserved', SUCCESSOR_ACCEPTED_LOCAL: 'Successor accepted locally', INCONCLUSIVE: 'Inconclusive · evidence retained', REJECTED: 'Not accepted · evidence retained', CANCELLED: 'Stopped · evidence retained'};
        el('status').textContent = row ? `${labels[row.state] || row.state}. ${row.reason || 'Original mission history and earlier outcomes remain retained.'}`
            : ready ? 'Ready. Build and freeze first; future inputs are supplied afterward.' : 'Preparing the existing mission history…';
        el('facts').replaceChildren();
        const fact = (name, value) => { element('dt', el('facts'), name); element('dd', el('facts'), String(value)); };
        if (row?.bundle) {
            const c = row.bundle.counts;
            fact('Transform chain', c.transformChain.toLocaleString());
            fact('Convolution, incremental', c.incrementalConvolution.toLocaleString());
            fact('Inverse: direct / inherited', `${c.inverseDirect.toLocaleString()} / ${c.inverseInherited.toLocaleString()}`);
            fact('One inverse: build convolution first?', `${c.inverseOnlyViaNewConvolution.toLocaleString()} > ${c.inverseDirect.toLocaleString()} · choose direct`);
            fact('Specified isolated / shared', `${c.isolated.toLocaleString()} / ${c.joint.toLocaleString()}`);
            fact('Unrestricted same-primitive planner', `${c.unrestrictedSamePrimitiveJointPlanner.toLocaleString()} · tie`);
            fact('Complete counted comparison campaign', row.bundle.observedWorkLedger.totalCountedCampaignWork.toLocaleString());
            fact('Factory lineage', 'Historical costs remain charged; no financial value inferred.');
        }
        if (row) {
            el('future-result').textContent = JSON.stringify(enterpriseHistory.summary(inspected.enterprises), null, 2);
            const outcomes = row.future?.runs || [];
            el('future-summary').textContent = outcomes.length ? `${outcomes.filter(run => run.state === 'ACCEPTED').length} of ${outcomes.length} matched comparisons accepted. ${row.successor ? 'A changed-kernel inverse is separately constructed and checked; the original factory remains intact.' : 'Inspect all results before qualifying the successor.'}` : 'Freeze first, then supply later inputs. No future outcome is assumed.';
        }
    }
    async function save(next) {
        await persist(next, storedRevision, current);
        if (pending) throw Error('Exact history was not confirmed saved. Keep recovery before more computation.');
        try { localStorage.setItem('agialpha.discovery-lab.last-workspace', current.missionId); } catch { /* Pointer only. */ }
        refreshEnterprise();
    }
    async function advance(untilFreeze) {
        for (let count = 0; count < 11; count++) {
            const row = inspected?.enterprises?.active;
            if (!row || untilFreeze && row.state === 'FROZEN') return;
            if (stopRequested) { await save(await enterpriseController.stop(current, 'Operator requested a stop between bounded steps.')); return; }
            const next = row.state === 'INVOCATION_RESERVED'
                ? await enterpriseController.invokeReserved(current, source)
                : await enterpriseController.next(current, {expectedSource: source, seed: Number(el('seed').value)});
            await save(next);
            await new Promise(resolve => setTimeout(resolve, 0));
        }
        throw Error('Bounded controller step limit reached. Preserve and inspect this history.');
    }
    async function perform(action) {
        el('error').hidden = true; stopRequested = false;
        await operation(async () => {
            try { await action(); }
            catch (error) { el('error').hidden = false; el('error').textContent = error.message || String(error); throw error; }
        });
        refreshEnterprise();
    }
    el('build').addEventListener('click', () => void perform(async () => {
        if (!current) {
            const unchanged = {brief: capability.DEFAULT_BRIEF, witnessEnabled: false,
                experimentText: defaultExperimentText(), successorReason: ''};
            if (canonical(rawDraft()) !== canonical(unchanged)) throw Error('Save or export your edited proposal before starting another mission.');
            await save(await capability.createWorkspace({...capability.DEFAULT_BRIEF,
                title: 'Autonomous Enterprises · Build the Means of Building',
                objective: 'Construct and preserve checked reusable computational capabilities.'}, null));
        }
        await save(await enterpriseController.start(current, enterpriseProtocol.defaultCharter(source)));
        await advance(true);
    }));
    el('continue').addEventListener('click', () => void perform(() => advance(inspected?.enterprises?.active?.state === 'ACCEPTED_CONSTRUCTION')));
    el('stop').addEventListener('click', () => {
        if (busy) { stopRequested = true; el('status').textContent = 'Stop requested. The current bounded step will be retained before stopping.'; }
        else void perform(async () => save(await enterpriseController.stop(current, 'Operator stopped the bounded local controller.')));
    });
    el('inspect').addEventListener('click', () => { el('evidence').textContent = JSON.stringify(latest().bundle, null, 2); });
    el('capital-run').addEventListener('click', () => {
        try {
            const result = enterpriseCapital.syntheticCapitalExample();
            el('capital-result').textContent = JSON.stringify(result, null, 2);
            el('capital-summary').textContent = result.targets.map(target => `${target.target.join('+')}, terminal cash ${target.terminalCash}: ${target.full.capital} launch units with the productive portfolio, ${target.cashOnly.capital} after cash-only pruning.`).join(' ');
        }
        catch (error) { el('capital-result').textContent = error.message; }
    });
    el('export').addEventListener('click', () => void perform(async () => {
        download(await discoveryDocket.exportDiscoveryDocket(current), `autonomous-enterprise-docket-${current.missionId}.json`);
    }));
    el('account').addEventListener('click', () => download(canonical(enterpriseProtocol.auditSnapshot()), 'autonomous-enterprise-session-account.json'));
    const earlierRender = render;
    render = function () { earlierRender(); refreshEnterprise(); };
    refreshEnterprise();
})();
