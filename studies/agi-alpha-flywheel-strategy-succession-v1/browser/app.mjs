// SPDX-License-Identifier: Apache-2.0
import {runMission, inspectMissionPack} from '../companion/adapter.mjs';
import {createMissionStream} from '../companion/stream.mjs';
import {browserConfiguration} from './mission-fixtures.mjs';
import {inspectTask, SPECIALISTS} from '../companion/core.mjs';
import {SOURCE_HASH} from '../companion/binding.mjs';
import {checkForWorkbench} from './checker.mjs';
import {initialTask, TASK_LABELS} from './demo-task.mjs';

const $ = id => document.getElementById(id);
const clone = value => JSON.parse(JSON.stringify(value));
const json = value => JSON.stringify(value, null, 2);
const number = value => Number(value ?? 0).toLocaleString('en-CA', {maximumFractionDigits: 2});
const names = {
    'critical-path': 'Critical path',
    'longest-first': 'Longest task first',
    'shortest-first': 'Shortest task first',
    'descendant-work': 'Remaining downstream work',
    'critical-resource': 'Critical path + resource demand',
};

function element(tag, text = '', className = '') {
    const node = document.createElement(tag);
    if (text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
}

function download(name, value, type = 'application/json') {
    const text = typeof value === 'string' ? value : `${json(value)}\n`;
    const url = URL.createObjectURL(new Blob([text], {type: `${type};charset=utf-8`}));
    const link = element('a');
    link.href = url;
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function notice(text, error = false) {
    const node = $('app-status');
    node.textContent = text;
    node.hidden = !text;
    node.className = error ? 'notice error' : 'notice';
}

function panel(name, focus = false) {
    for (const tab of document.querySelectorAll('[data-panel]')) {
        const active = tab.dataset.panel === name;
        tab.setAttribute('aria-selected', String(active));
        tab.tabIndex = active ? 0 : -1;
        $(tab.getAttribute('aria-controls')).hidden = !active;
        if (active && focus) tab.focus();
    }
}

function safeInput(task) {
    if (task?.planning_only !== true) throw new Error('This companion accepts planning-only missions.');
    if (!['synthetic', 'public'].includes(task?.public_or_synthetic)) {
        throw new Error('Declare synthetic or public nonpersonal inputs.');
    }
    const suppliedStatus = value => value !== undefined && value !== null
        && (!Array.isArray(value) || value.length > 0);
    if (suppliedStatus(task.authority) || suppliedStatus(task.proof) || task.external_execution || task.execute) {
        throw new Error('Operational execution and imported proof or authority are outside this scope.');
    }
    inspectTask(task);
    return task;
}

function humanError(error) {
    const code = error?.message ?? String(error);
    const messages = {
        DEPENDENCY_CYCLE: 'These dependencies form a cycle. Remove a dependency so the first task can begin.',
        UNKNOWN_DEPENDENCY: 'A dependency refers to a task that is not in this mission.',
        JOB_SCOPE: 'Use between 1 and 18 tasks for this bounded planner.',
        JOB_SCHEMA: 'Each task needs a unique J-number, 1–12 whole hours, 1–4 workers and valid dependencies.',
        DEADLINE_SCOPE: 'The target finish must be inside the mission calendar.',
        WORK_LIMIT: 'The planning budget was reached. No target-qualified result is claimed.',
        CHECK_RESERVE: 'The remaining budget is too small to check this result. It has not been accepted.',
        NO_FEASIBLE_PORTFOLIO: 'The available methods found no feasible schedule within these limits.',
        LOCK_PREFIX_NOT_CLOSED: 'A locked task depends on work that is not also locked before it.',
        LOCK_CAPACITY_CONFLICT: 'The locked work exceeds the current worker capacity.',
    };
    return messages[code] ?? code;
}

function makeStorage(key) {
    let memory = null;
    let memoryGuard = null;
    let available = true;
    try {
        localStorage.setItem(`${key}:probe`, '1');
        localStorage.removeItem(`${key}:probe`);
    } catch {
        available = false;
    }
    return {
        get available() { return available; },
        async load() {
            if (!available) return memory;
            const text = localStorage.getItem(key);
            if (!text) return null;
            if (text.length > 8_000_000) throw new Error('Saved history exceeds the local storage bound.');
            return JSON.parse(text);
        },
        async save(value) {
            const text = json(value);
            if (text.length > 8_000_000) throw new Error('Local history storage budget exhausted.');
            memory = clone(value);
            if (available) {
                try { localStorage.setItem(key, text); }
                catch { available = false; }
            }
        },
        async loadGuard() {
            if (!available) return memoryGuard;
            const text = localStorage.getItem(`${key}:guard`);
            return text ? JSON.parse(text) : null;
        },
        async saveGuard(value) {
            memoryGuard = clone(value);
            if (available) {
                try { localStorage.setItem(`${key}:guard`, json(value)); }
                catch { available = false; }
            }
        },
        async clear() {
            memory = null;
            memoryGuard = null;
            if (available) {
                localStorage.removeItem(key);
                localStorage.removeItem(`${key}:guard`);
            }
        },
    };
}

export async function startApp({data}) {
    let task = initialTask();
    let current = null;
    let submittedTask = null;
    let inputRevision = 0;
    let runningPlan = false;
    let customCalendar = false;
    let controller = null;
    let streamRunning = false;
    let snapshot = null;
    let eventRows = [];
    let configuration = browserConfiguration();
    configuration.policy.mode = 'flywheel';
    configuration.policy.actor = 'browser-user';
    let storage = makeStorage(`agialpha:strategy-succession:${data.execution_source_hash}:flywheel:v1`);

    function renderInputs() {
        $('workers').value = Math.max(...task.capacity);
        $('deadline').value = task.deadline ?? task.capacity.length;
        $('deadline').max = task.capacity.length;
        $('mission-json').value = json(task);
        $('job-inputs').replaceChildren();
        for (const job of task.jobs) {
            const row = element('tr');
            const label = element('td', null);
            label.append(element('b', TASK_LABELS[job.id] ?? `Task ${job.id.slice(1)}`));
            label.append(element('span', job.id));
            row.append(label);
            for (const [field, title, min, max] of [
                ['duration', 'duration in hours', 1, 12],
                ['crew', 'workers needed', 1, 4],
                ['deps', 'dependency task identifiers', null, null],
            ]) {
                const cell = element('td', null);
                const input = element('input');
                input.dataset.job = job.id;
                input.dataset.field = field;
                input.setAttribute('aria-label', `${job.id} ${title}`);
                if (field === 'deps') {
                    input.type = 'text';
                    input.className = 'deps';
                    input.value = job.deps.join(',');
                    input.placeholder = 'None';
                    input.maxLength = 85;
                    input.spellcheck = false;
                } else {
                    input.type = 'number';
                    input.min = min;
                    input.max = max;
                    input.step = 1;
                    input.required = true;
                    input.value = job[field];
                }
                cell.append(input);
                row.append(cell);
            }
            $('job-inputs').append(row);
        }
        $('add-job').disabled = task.jobs.length >= 18;
    }

    function readInputs() {
        const next = clone(task);
        const map = new Map(next.jobs.map(job => [job.id, job]));
        for (const input of $('job-inputs').querySelectorAll('input')) {
            const job = map.get(input.dataset.job);
            job[input.dataset.field] = input.dataset.field === 'deps'
                ? input.value.split(',').map(value => value.trim()).filter(Boolean)
                : Number(input.value);
        }
        next.deadline = Number($('deadline').value);
        if (!customCalendar) next.capacity = Array(next.capacity.length).fill(Number($('workers').value));
        next.id = `browser-release-${++inputRevision}`;
        return safeInput(next);
    }

    function drawGantt(input, result) {
        const chart = $('gantt');
        chart.replaceChildren();
        const maximum = Math.max(result.makespan, input.deadline ?? 0, 1);
        const axis = element('div', null, 'gantt-axis');
        axis.append(element('span', 'TASK'));
        const ticks = element('div', null, 'gantt-ticks');
        for (let index = 0; index <= 4; index += 1) {
            const tick = element('span', number(maximum * index / 4));
            tick.style.left = `${index * 25}%`;
            ticks.append(tick);
        }
        axis.append(ticks);
        chart.append(axis);
        const lookup = new Map(input.jobs.map(job => [job.id, job]));
        $('schedule-table').replaceChildren();
        for (const [index, item] of result.schedule.entries()) {
            const label = TASK_LABELS[item.id] ?? item.id;
            const row = element('div', null, 'gantt-row');
            const name = element('span', label, 'gantt-label');
            name.title = `${item.id} · ${label}`;
            row.append(name);
            const track = element('div', null, 'gantt-track');
            const bar = element('div', item.end - item.start >= 2 ? `${item.start}–${item.end}` : '', `gantt-bar tone-${index % 4}`);
            bar.style.left = `${100 * item.start / maximum}%`;
            bar.style.width = `${100 * (item.end - item.start) / maximum}%`;
            bar.title = `${label}: hour ${item.start} to ${item.end}; ${lookup.get(item.id).crew} workers`;
            track.append(bar);
            row.append(track);
            chart.append(row);
            const tableRow = element('tr');
            for (const value of [`${item.id} · ${label}`, item.start, item.end, lookup.get(item.id).crew]) {
                tableRow.append(element('td', value));
            }
            $('schedule-table').append(tableRow);
        }
        chart.setAttribute('aria-label', `Computed schedule: ${result.schedule.length} tasks, finish at hour ${result.makespan}. A full data table follows.`);
    }

    function renderPlan(input, receipt) {
        const result = receipt.result;
        $('empty-result').hidden = true;
        $('plan-result').hidden = false;
        $('result-badge').textContent = receipt.qualified ? 'TARGET MET' : 'TARGET MISSED';
        $('result-badge').className = receipt.qualified ? 'tiny-tag good' : 'tiny-tag warn';
        $('result-heading').textContent = receipt.qualified ? 'Ready to review and use' : 'A checked plan, with a limit';
        $('result-verdict').textContent = receipt.qualified
            ? '✓ Feasible and within the declared finish target.'
            : 'Feasible schedule found. The current finish target was not met.';
        $('result-verdict').className = receipt.qualified ? 'result-verdict' : 'result-verdict warn';
        $('metric-finish').textContent = `${result.makespan} h`;
        const margin = (input.deadline ?? input.capacity.length) - result.makespan;
        $('metric-margin').textContent = margin >= 0 ? `${margin} h left` : `${-margin} h late`;
        $('metric-tasks').textContent = `${result.schedule.length}/${input.jobs.length}`;
        drawGantt(input, result);
        $('verification-note').textContent = result.optimal_by_lower_bound
            ? '✓ Checked by a separate browser implementation. The finish matches the recomputed lower bound.'
            : '✓ Checked by a separate browser implementation. A globally optimal finish has not been established.';
        const costs = element('div', null, 'cost-list');
        const pairs = [
            ['Full counted work', `${number(receipt.work)} units`],
            ['Elapsed on this device', `${number(receipt.wall_ms)} ms`],
            ['Separate checking', `${number(receipt.checker?.counts?.total)} units`],
            ['External paid calls', '0'],
        ];
        for (const [key, value] of pairs) {
            const line = element('div');
            line.append(element('span', key), element('b', value));
            costs.append(line);
        }
        $('plan-costs').replaceChildren(costs, element('p', 'Browser work units are an explicit accounting model. They are not CPU instructions, hours or money and cannot be pooled with Python specialist counters. Host energy, hardware and human review cost are unpriced.', 'fine muted'));
        const methods = element('p', null, 'fine muted');
        methods.textContent = 'Available methods: ' + (input.kind === 'repair' ? 'preserve previous ordering; ' : '') + SPECIALISTS.map(method => names[method.name] ?? method.name).join('; ') + '. The conventional portfolio stops when a qualified result or a matched lower bound is reached.';
        $('method-comparison').replaceChildren(methods);
        if (receipt.attempts?.length) {
            const table = element('table', null, 'plain-table');
            const head = element('thead');
            const header = element('tr');
            for (const value of ['Actually tried', 'Finish', 'Work']) header.append(element('th', value));
            head.append(header);
            table.append(head);
            const body = element('tbody');
            for (const attempt of receipt.attempts) {
                const row = element('tr');
                for (const value of [names[attempt.method] ?? attempt.method, attempt.makespan ?? attempt.error, number(attempt.work)]) row.append(element('td', value));
                body.append(row);
            }
            table.append(body);
            $('method-comparison').append(table);
        }
    }

    async function planNow(event) {
        event?.preventDefault();
        if (runningPlan) return;
        notice('');
        try {
            submittedTask = readInputs();
            task = clone(submittedTask);
            $('mission-json').value = json(task);
            runningPlan = true;
            $('plan-button').disabled = true;
            $('plan-button').textContent = 'Computing and checking…';
            await new Promise(resolve => requestAnimationFrame(resolve));
            current = await runMission(submittedTask, {check: checkForWorkbench, budget: 100000, sourceHash: data.execution_source_hash});
            if (!current.valid || !current.result) throw new Error(current.error ?? 'The separate checker refused this result.');
            const imported = await inspectMissionPack(current.pack);
            if (imported.activeProof.length || imported.activeAuthority.length) throw new Error('Unexpected inherited authority.');
            renderPlan(submittedTask, current);
            if (innerWidth < 761) $('result-heading').scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
        } catch (error) {
            current = null;
            notice(humanError(error), true);
            $('result-badge').textContent = 'REFUSED';
            $('result-badge').className = 'tiny-tag warn';
            $('plan-result').hidden = true;
            $('empty-result').hidden = false;
        } finally {
            runningPlan = false;
            $('plan-button').disabled = false;
            $('plan-button').replaceChildren(document.createTextNode('Plan this mission '), element('span', '↗'));
        }
    }

    function renderMissionCards(state = null) {
        const outcomes = state?.missions ?? [];
        $('mission-cards').replaceChildren();
        const titles = ['Plan the first release', 'Try a fresh release', 'Meet a tighter target', 'Check the next method', 'Repair after disruption', 'Try a fresh repair'];
        const descriptions = [
            'A fresh dependency graph and a finite worker calendar.',
            'Changed inputs test whether a retained priority rule applies.',
            'A new requirement arrives before the next investment.',
            'A constructed look-ahead method may serve fresh work.',
            'Preserve committed work while capacity changes.',
            'The next repair tests the admitted method or incumbent.',
        ];
        for (const [index, mission] of configuration.tasks.entries()) {
            const card = element('article', null, 'mission-card-item');
            if (state?.status === 'RUNNING' && state.cursor === index) card.classList.add('current');
            card.append(element('div', `0${index + 1}`, 'number'), element('h3', titles[index]), element('p', descriptions[index]));
            card.append(element('p', `${mission.jobs.length} tasks · ${Math.max(...mission.capacity)} workers · target ${mission.deadline} h`, 'fine'));
            const entry = outcomes.find(value => value.task_id === mission.id || value.task?.id === mission.id || value.mission_id === mission.id);
            const receipt = entry?.receipt ?? entry?.outcome ?? entry;
            const text = receipt?.result ? `${receipt.qualified ? 'Target met' : 'Target missed'} · ${receipt.result.makespan} h · ${number(receipt.work)} work units` : entry?.error ? `Refused: ${entry.error}` : 'Waiting for fresh execution';
            card.append(element('div', text, `mission-outcome${receipt?.result && !receipt.qualified ? ' outcome-missed' : ''}`));
            if (receipt?.result) {
                const inherited = state.assets?.find(asset => asset.digest === entry.asset_digest);
                card.append(element('p', inherited
                    ? `Used retained ${inherited.stage} method · ${inherited.digest.slice(0, 12)}`
                    : 'Used the conventional specialist portfolio', 'fine muted'));
            }
            $('mission-cards').append(card);
        }
    }

    function renderLineage(state = null) {
        $('lineage').replaceChildren();
        const assets = state?.assets ?? state?.archive ?? [];
        const expected = [
            ['dispatch', 'A priority rule', 'A bounded search proposes a way to order ready work.'],
            ['lookahead', 'A look-ahead method', 'A child embeds its parent rule while testing possible next moves.'],
            ['repair', 'A disruption response', 'A later method uses retained structure to repair a changed plan.'],
        ];
        for (const [kind, title, detail] of expected) {
            const found = assets.find(value => value.active && value.stage === kind);
            const decision = state?.discoveries?.find(value => value.stage === kind);
            const latestEvent = [...(state?.events ?? [])].reverse().find(value => value.stage === kind && value.decision);
            const asset = element('article', null, 'asset');
            const laboratory = found?.gate?.decision === 'DIAGNOSTIC_CORRECTNESS_ONLY';
            const tag = found ? laboratory ? 'LAB RETENTION ONLY' : configuration.policy.mode === 'diagnostic' ? 'STAGE FORECAST PASSES' : 'RETAINED FOR LOCAL SCOPE' : decision ? 'INCUMBENT RETAINED' : latestEvent ? 'DEFERRED OR REFUSED' : 'AWAITING DECISION';
            asset.append(element('span', tag, 'tiny-tag'));
            asset.append(element('h4', title), element('p', detail));
            if (found) {
                asset.append(element('p', `Identity: ${(found.digest ?? found.id ?? found.asset_id ?? kind).slice(0, 20)}`, 'hash'));
                const inspect = element('details');
                inspect.append(element('summary', 'Inspect this inheritance'));
                const record = element('pre', json({
                    scope: found.scope,
                    parent_digest: found.parent_digest,
                    strategy: found.strategy,
                    active: found.active,
                    admission: found.gate,
                    proof: found.proof,
                    authority: found.authority,
                }), 'hash');
                record.style.whiteSpace = 'pre-wrap';
                inspect.append(record);
                asset.append(inspect);
            }
            if (decision?.gate) {
                asset.append(element('p', `Correctness: ${decision.gate.correctness ? 'pass' : 'refused'}. Net-benefit gate: ${decision.gate.net_benefit ? 'forecast passes' : 'retain incumbent'}.`, 'fine'));
                asset.append(element('p', `Construction + qualification: ${number(decision.acquisition)} units.`, 'fine'));
                if (decision.qualification) {
                    const q = decision.qualification;
                    asset.append(element('p', `Qualification targets met: ${q.candidate.qualified}/${q.candidate.count} candidate; ${q.incumbent.qualified}/${q.incumbent.count} incumbent.`, 'fine'));
                }
                asset.append(element('p', decision.gate.break_even_missions === null
                    ? 'Cost-only break-even: not reached by this forecast.'
                    : `Cost-only break-even: ${number(decision.gate.break_even_missions)} matching future missions.`, 'fine'));
            } else if (latestEvent?.decision) {
                const reason = latestEvent.decision === 'DEFER_NO_ACCEPTED_PARENT'
                    ? 'No retained parent was available. No child was admitted.'
                    : latestEvent.decision.replaceAll('_', ' ').toLowerCase() + '.';
                asset.append(element('p', reason, 'fine'));
            }
            $('lineage').append(asset);
        }
    }

    function addEvent(event) {
        eventRows.push(clone(event));
        if (eventRows.length > 160) eventRows = eventRows.slice(-160);
        $('event-log').replaceChildren();
        for (const item of [...eventRows].reverse()) {
            const row = element('li');
            const title = String(item.kind ?? 'EVENT').replaceAll('_', ' ');
            row.append(element('b', `${item.sequence ?? ''} · ${title}`));
            const detail = item.decision ? `${item.stage ?? ''}: ${item.decision.replaceAll('_', ' ')}` : item.reason ?? item.mission_id ?? (item.detail ? JSON.stringify(item.detail) : '');
            row.append(element('span', detail.slice(0, 500)));
            $('event-log').append(row);
        }
        if (event.kind) $('stream-state').textContent = String(event.kind).replaceAll('_', ' ');
        if (event.mission_id) $('stream-progress').textContent = event.mission_id;
        if (Number.isFinite(event.work_total)) $('stream-budget').textContent = `${number(event.work_total)} / ${number(configuration.policy.totalWork)} work units`;
        queueMicrotask(() => refreshStream().catch(error => notice(humanError(error), true)));
    }

    async function refreshStream() {
        if (!controller) return;
        snapshot = await controller.snapshot();
        const state = snapshot.payload ?? snapshot.state ?? snapshot;
        renderMissionCards(state);
        renderLineage(state);
        const work = state.work_total ?? state.work ?? state.spent ?? 0;
        const total = typeof work === 'number' ? work : work.total ?? 0;
        $('stream-budget').textContent = `${number(total)} / ${number(configuration.policy.totalWork)} work units`;
        const costs = element('div', null, 'cost-list');
        for (const [key, value] of [['Counted cumulative work', number(total)], ['Configured work ceiling', number(configuration.policy.totalWork)], ['Local storage', `${number(new TextEncoder().encode(json(snapshot)).length)} bytes`], ['Current authority', 'None']]) {
            const line = element('div');
            line.append(element('span', key), element('b', value));
            costs.append(line);
        }
        $('stream-costs').replaceChildren(costs, element('p', 'Construction, rejected proposals and checks remain part of the recorded run. A correctness-qualified method can still be refused as an investment.', 'fine muted'));
        $('download-stream').disabled = false;
        $('storage-note').textContent = storage.available
            ? 'Checkpointed in this browser. Download the evidence for a separate copy. A stored history does not run by itself.'
            : 'Persistent browser storage is unavailable. This run is held in memory; download its evidence before closing.';
    }

    async function makeController() {
        controller = await createMissionStream({...clone(configuration), storage, onEvent: addEvent, check: checkForWorkbench, sourceHash: data.execution_source_hash});
        return controller;
    }

    async function startStream(resume = false) {
        if (streamRunning) return;
        notice('');
        streamRunning = true;
        $('stream-start').disabled = true;
        $('stream-resume').disabled = true;
        $('stream-stop').disabled = false;
        $('clear-stream').disabled = true;
        $('stream-diagnostic').disabled = true;
        try {
            if (!controller) await makeController();
            await controller.start({resume});
            await refreshStream();
        } catch (error) {
            notice(humanError(error), true);
        } finally {
            streamRunning = false;
            $('stream-stop').disabled = true;
            $('clear-stream').disabled = false;
            $('stream-diagnostic').disabled = false;
            $('stream-start').disabled = Boolean(snapshot);
            const state = snapshot?.payload ?? snapshot?.state ?? snapshot;
            $('stream-resume').disabled = state?.status !== 'STOPPED' || state?.reason !== 'USER_STOP';
        }
    }

    function renderEvidence() {
        $('bundle-hash').textContent = `Browser source set: ${data.source_hash}\nBrowser execution + checker: ${data.execution_source_hash}\nScientific core: ${SOURCE_HASH}\nReleased workbench: ${data.upstream_release} / ${data.upstream_commit}`;
        const downloads = $('evidence-downloads');
        const add = (label, file, value) => {
            const button = element('button', label, 'secondary small');
            button.addEventListener('click', () => download(file, value));
            downloads.append(button);
        };
        add('Source identities ↓', 'strategy-succession-source-manifest.json', data);
        add('Mission stream configuration ↓', 'browser-mission-stream.json', configuration);
        if (data.research) {
            const research = data.research;
            const container = $('research-summary');
            container.replaceChildren();
            container.append(element('p', research.headline ?? 'Frozen research evidence', 'research-headline'));
            container.append(element('p', research.description ?? research.scope ?? 'See the complete evidence docket for the registered definitions and limits.', 'muted'));
            if (research.metrics) {
                const list = element('div', null, 'cost-list');
                for (const metric of research.metrics) {
                    const row = element('div');
                    row.append(element('span', metric.label), element('b', metric.value));
                    list.append(row);
                }
                container.append(list);
            }
            for (const source of research.tables ?? []) {
                if (!Array.isArray(source.columns) || !Array.isArray(source.rows)) continue;
                const columns = source.columns.slice(0, 8);
                container.append(element('h3', source.title ?? 'Study comparison'));
                const scroll = element('div', null, 'table-scroll research-table-scroll');
                scroll.tabIndex = 0;
                scroll.setAttribute('role', 'region');
                scroll.setAttribute('aria-label', `${source.title ?? 'Study comparison'}: scroll horizontally if needed`);
                const table = element('table', null, 'plain-table research-table');
                table.append(element('caption', source.title ?? 'Study comparison', 'sr-only'));
                const head = element('thead');
                const heading = element('tr');
                for (const column of columns) {
                    const cell = element('th', column.label ?? column.key);
                    cell.scope = 'col';
                    if (column.align === 'right') cell.className = 'numeric';
                    heading.append(cell);
                }
                head.append(heading);
                table.append(head);
                const body = element('tbody');
                for (const sourceRow of source.rows.slice(0, 100)) {
                    const row = element('tr');
                    for (const [index, column] of columns.entries()) {
                        const value = sourceRow[column.key];
                        const cell = element(index === 0 ? 'th' : 'td', value === undefined || value === null ? '—'
                            : typeof value === 'object' ? json(value) : value);
                        if (index === 0) cell.scope = 'row';
                        if (column.align === 'right') cell.className = 'numeric';
                        row.append(cell);
                    }
                    body.append(row);
                }
                table.append(body);
                scroll.append(table);
                container.append(scroll);
                if (source.note) container.append(element('p', source.note, 'fine muted'));
            }
            for (const item of research.downloads ?? []) add(item.label, item.filename, item.data);
            add('Recorded research summary ↓', 'recorded-research-summary.json', research);
            const detail = element('details');
            detail.append(element('summary', 'Inspect the complete embedded record'));
            const pre = element('pre', json(research), 'hash');
            pre.style.whiteSpace = 'pre-wrap';
            detail.append(pre);
            container.append(detail);
        }
    }

    for (const tab of document.querySelectorAll('[data-panel]')) {
        tab.addEventListener('click', () => panel(tab.dataset.panel));
        tab.addEventListener('keydown', event => {
            const tabs = [...document.querySelectorAll('[data-panel]')];
            let index = tabs.indexOf(tab);
            if (event.key === 'ArrowRight') index = (index + 1) % tabs.length;
            else if (event.key === 'ArrowLeft') index = (index - 1 + tabs.length) % tabs.length;
            else if (event.key === 'Home') index = 0;
            else if (event.key === 'End') index = tabs.length - 1;
            else return;
            event.preventDefault();
            panel(tabs[index].dataset.panel, true);
        });
    }
    $('mission-form').addEventListener('submit', planNow);
    $('workers').addEventListener('change', () => { customCalendar = false; });
    $('add-job').addEventListener('click', () => {
        try { task = readInputs(); }
        catch (error) { notice(humanError(error), true); return; }
        const id = `J${Math.max(...task.jobs.map(job => Number(job.id.slice(1)))) + 1}`;
        task.jobs.push({id, duration: 2, crew: 1, deps: []});
        renderInputs();
    });
    $('reset-example').addEventListener('click', () => { task = initialTask(); customCalendar = false; renderInputs(); notice('Synthetic example restored. Select Plan this mission to compute a new result.'); });
    $('advanced-input').addEventListener('toggle', () => {
        if ($('advanced-input').open) {
            try { $('mission-json').value = json(readInputs()); }
            catch { /* Preserve the editable JSON while the table is incomplete. */ }
        }
    });
    $('apply-json').addEventListener('click', () => {
        try {
            if ($('mission-json').value.length > 100000) throw new Error('Mission input is too large.');
            task = safeInput(JSON.parse($('mission-json').value));
            customCalendar = new Set(task.capacity).size > 1;
            renderInputs();
            notice(customCalendar ? 'JSON applied. The changing worker calendar is preserved; editing Available workers replaces it with a constant calendar.' : 'JSON applied. Select Plan this mission for fresh computation.');
        } catch (error) { notice(humanError(error), true); }
    });
    $('download-plan').addEventListener('click', () => current && download('checked-release-plan.json', {task: submittedTask, result: current.result, checker: current.checker}));
    $('download-receipt').addEventListener('click', () => current && download('release-workbench-receipt.json', current));
    $('download-csv').addEventListener('click', () => {
        if (!current) return;
        const lines = ['task,start_hour,finish_hour,workers'];
        for (const item of current.result.schedule) lines.push([item.id, item.start, item.end, submittedTask.jobs.find(job => job.id === item.id).crew].join(','));
        download('release-schedule.csv', `${lines.join('\n')}\n`, 'text/csv');
    });
    $('next-missions').addEventListener('click', () => { panel('stream', true); $('workspace').scrollIntoView({block: 'start'}); });
    $('stream-start').addEventListener('click', () => startStream(false));
    $('stream-diagnostic').addEventListener('click', async () => {
        if (streamRunning) return;
        const diagnostic = configuration.policy.mode !== 'diagnostic';
        configuration = browserConfiguration({diagnostic});
        configuration.policy.mode = diagnostic ? 'diagnostic' : 'flywheel';
        configuration.policy.actor = 'browser-user';
        storage = makeStorage(`agialpha:strategy-succession:${data.execution_source_hash}:${configuration.policy.mode}:v1`);
        controller = null;
        snapshot = null;
        eventRows = [];
        $('diagnostic-notice').hidden = !diagnostic;
        $('stream-diagnostic').textContent = diagnostic ? 'Return to full-cost gate' : 'Inspect construction chain';
        $('stream-start').disabled = false;
        $('stream-resume').disabled = true;
        $('stream-state').textContent = diagnostic ? 'CONSTRUCTION LAB' : 'READY';
        $('stream-progress').textContent = diagnostic ? 'Correctness-only retention. Economic admission remains separate.' : 'Selective admission after full counted costs.';
        $('event-log').replaceChildren(element('li', 'A separate run mode is selected. Start explicitly to compute.'));
        renderMissionCards();
        renderLineage();
        try {
            const saved = await storage.load();
            if (saved) {
                await makeController();
                await controller.restore(saved);
                await refreshStream();
                $('stream-start').disabled = true;
                $('stream-resume').disabled = snapshot.status === 'COMPLETE' || snapshot.reason !== 'USER_STOP';
            }
        } catch (error) {
            $('stream-start').disabled = true;
            $('stream-resume').disabled = true;
            notice(`Saved history was refused: ${humanError(error)}. Clear local history before a new run.`, true);
        }
    });
    $('stream-resume').addEventListener('click', () => startStream(true));
    $('stream-stop').addEventListener('click', () => { controller?.stop('USER_STOP'); $('stream-stop').disabled = true; $('stream-state').textContent = 'STOP REQUESTED'; });
    $('download-stream').addEventListener('click', async () => { await refreshStream(); download('strategy-succession-run.json', snapshot); });
    $('clear-stream').addEventListener('click', async () => {
        if (streamRunning) return;
        await storage.clear();
        controller = null;
        snapshot = null;
        eventRows = [];
        $('event-log').replaceChildren(element('li', 'History cleared locally. Downloaded evidence is unchanged.'));
        $('stream-state').textContent = 'NOT STARTED';
        $('stream-progress').textContent = 'Ready for a new explicit start';
        $('stream-budget').textContent = '';
        $('stream-start').disabled = false;
        $('stream-resume').disabled = true;
        $('download-stream').disabled = true;
        renderMissionCards();
        renderLineage();
    });
    renderInputs();
    // Keep the single starting action visible before the longer editable task table.
    const form = $('mission-form');
    form.insertBefore($('plan-button'), form.querySelector('.table-scroll'));
    $('plan-button').style.marginBottom = '16px';
    renderMissionCards();
    renderLineage();
    renderEvidence();
    try {
        const saved = await storage.load();
        if (saved) {
            await makeController();
            await controller.restore(saved);
            await refreshStream();
            $('stream-start').disabled = true;
            $('stream-resume').disabled = snapshot.status !== 'STOPPED' || snapshot.reason !== 'USER_STOP';
            $('stream-state').textContent = 'SAVED HISTORY';
            $('stream-progress').textContent = 'Inspect retained evidence. Resume explicitly if interrupted.';
        }
    } catch (error) {
        $('stream-start').disabled = true;
        $('stream-resume').disabled = true;
        notice(`Saved history could not be accepted: ${humanError(error)}. Clear local history to start a new bounded run.`, true);
    }
    document.documentElement.dataset.ready = 'true';
}
