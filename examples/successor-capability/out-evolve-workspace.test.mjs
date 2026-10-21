// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {apparatus} from './apparatus.mjs';
import {createSearch, advanceSearch, construct, exportSearchCheckpoint, importSearchCheckpoint, canonical} from './constructor.mjs';
import {buildSuccessor, evaluateFrozenReuse} from './evaluation.mjs';
import {freezeCapability, digestCapability} from './capability-package.mjs';
import {createOutEvolveWorkspace, appendOutEvolveEvent, inspectOutEvolveWorkspace,
    requireHistoryContinuation, searchHistoryCapacity, evaluationHistoryCapacity, retainedEvaluationReport,
    WORKSPACE_LIMITS} from './out-evolve-workspace.mjs';

const bytes = value => new TextEncoder().encode(canonical(value)).length;
const uiBounds = {maxCost: 100000, maxStates: 2000, maxMemoryStates: 2000, maxProgramSize: 12};

test('retained successor reports reconstruct constructor evidence without changing packages or observed results', async () => {
    const app = apparatus('shielded');
    const parent = await freezeCapability(app, construct(app, uiBounds));
    const raw = await buildSuccessor(parent, {seed: 9, searchOptions: parent.search.limits});
    const original = canonical(raw);
    const retained = retainedEvaluationReport(raw);
    assert.equal(canonical(raw), original);
    assert.deepEqual(retained.package, raw.package);
    for (const key of ['oldScope', 'reuse', 'scratchReuse', 'obligations', 'newFunction', 'costs', 'limitations']) {
        assert.deepEqual(retained[key], raw[key]);
    }
    for (const [key, source] of [['result', parent], ['scratch', null]]) {
        assert.equal(Object.hasOwn(retained[key], 'attempts'), false);
        assert.equal(Object.hasOwn(retained[key], 'frontier'), false);
        const restored = importSearchCheckpoint(retained[key].checkpoint, {parent: source});
        const replayed = advanceSearch(restored, {steps: 0});
        assert.deepEqual(replayed.ledger, raw[key].ledger);
        assert.deepEqual(replayed.program, raw[key].program);
        assert.deepEqual(replayed.attempts, raw[key].attempts);
        assert.deepEqual(replayed.frontier, raw[key].frontier);
    }
    let history = await appendOutEvolveEvent(createOutEvolveWorkspace('out-evolve-report-compact'), 'package-frozen', {package: parent});
    const capacity = evaluationHistoryCapacity(history, parent, 'successor');
    assert.equal(capacity.canRun, true);
    assert.ok(bytes(retained) < capacity.reportBytes);
    history = await appendOutEvolveEvent(history, 'successor', retained);
    assert.equal((await inspectOutEvolveWorkspace(history)).latestPackage.digest, raw.package.digest);
});

test('evaluation reservation accounts for UTF8 exposures and refuses event, byte, node and depth boundaries before work', async () => {
    const app = apparatus('shielded');
    const pkg = await freezeCapability(app, construct(app, uiBounds));
    const base = await appendOutEvolveEvent(createOutEvolveWorkspace('out-evolve-report-limits'), 'package-frozen', {package: pkg});
    const exposures = ['\u0000'.repeat(1000) + '🧪'.repeat(1000)];
    const capacity = evaluationHistoryCapacity(base, pkg, 'reuse', exposures);
    assert.equal(capacity.exposureBytes, bytes(exposures));
    const report = await evaluateFrozenReuse(pkg, {seed: 9, exposedCaseIds: exposures});
    assert.ok(bytes(report) < capacity.reportBytes);
    assert.deepEqual(report.exposedCaseIds[0], exposures[0]);
    assert.equal(evaluationHistoryCapacity(base, pkg, 'reuse', Array.from({length: 4097}, (_, i) => String(i))).reason, 'exposure-limit');
    let full = base;
    while (full.events.length < WORKSPACE_LIMITS.events) full = await appendOutEvolveEvent(full, 'comparison', {status: 'NOT-EVALUATED'});
    for (const kind of ['reuse', 'successor']) {
        assert.equal(evaluationHistoryCapacity(full, pkg, kind).reason, 'event-limit');
    }
    const padded = await appendOutEvolveEvent(base, 'comparison', {note: 'x'.repeat(7_700_000)});
    assert.equal(evaluationHistoryCapacity(padded, pkg, 'reuse').reason, 'byte-reserve');
    const manyNodes = await appendOutEvolveEvent(base, 'comparison', {data: Array(1_910_000).fill(0)});
    assert.equal(evaluationHistoryCapacity(manyNodes, pkg, 'reuse').reason, 'structural-reserve');
    let deep = 'historical';
    for (let i = 0; i < 49; i++) deep = [deep];
    assert.equal(evaluationHistoryCapacity(base, pkg, 'reuse', [deep]).reason, 'structural-reserve');
    const expensive = await freezeCapability(app, construct(app, {...uiBounds, maxStates: 100000, maxMemoryStates: 100000}));
    const refused = evaluationHistoryCapacity(base, expensive, 'successor');
    assert.equal(refused.canRun, false);
    assert.equal(refused.fitsSeparateHistory, false);
    let evidence = 'historical context';
    for (let i = 0; i < 58; i++) evidence = {nested: evidence};
    const deepPackage = await freezeCapability(app, construct(app, uiBounds), {evidence});
    const deepHistory = await appendOutEvolveEvent(createOutEvolveWorkspace('out-evolve-report-depth'), 'package-frozen', {package: deepPackage});
    assert.equal((await inspectOutEvolveWorkspace(deepHistory)).latestPackage.digest, deepPackage.digest);
    assert.equal(evaluationHistoryCapacity(deepHistory, deepPackage, 'reuse').canRun, true);
    assert.equal(evaluationHistoryCapacity(deepHistory, deepPackage, 'successor').reason, 'structural-reserve');
    assert.equal(evaluationHistoryCapacity(deepHistory, deepPackage, 'successor').fitsSeparateHistory, false);
});

test('the conservative last-fit byte reservation retains a real report and the preceding history exactly', async () => {
    const app = apparatus('shielded');
    const pkg = await freezeCapability(app, construct(app, uiBounds));
    const base = await appendOutEvolveEvent(createOutEvolveWorkspace('out-evolve-report-last-fit'), 'package-frozen', {package: pkg});
    const emptyPadding = await appendOutEvolveEvent(base, 'comparison', {note: ''});
    const reserve = evaluationHistoryCapacity(emptyPadding, pkg, 'reuse').requiredBytes;
    const length = WORKSPACE_LIMITS.bytes - bytes(emptyPadding) - reserve;
    const lastFit = await appendOutEvolveEvent(base, 'comparison', {note: 'x'.repeat(length)});
    assert.equal(evaluationHistoryCapacity(lastFit, pkg, 'reuse').canRun, true);
    const oneLess = await appendOutEvolveEvent(base, 'comparison', {note: 'x'.repeat(length + 1)});
    assert.equal(evaluationHistoryCapacity(oneLess, pkg, 'reuse').canRun, false);
    const raw = await evaluateFrozenReuse(pkg, {seed: 12});
    const complete = await appendOutEvolveEvent(lastFit, 'reuse', retainedEvaluationReport(raw));
    assert.deepEqual(complete.events.slice(0, lastFit.events.length), lastFit.events);
    assert.deepEqual(complete.events.at(-1).payload, raw);
    assert.ok(bytes(complete) <= WORKSPACE_LIMITS.bytes);
});

test('uppercase failed and inconclusive evidence survives a later qualifying package and reload', async () => {
    let history = createOutEvolveWorkspace('out-evolve-history-test');
    history = await appendOutEvolveEvent(history, 'reuse', {status: 'FAIL', cases: [{status: 'FAIL', actual: 0, expected: 1}]});
    history = await appendOutEvolveEvent(history, 'reuse', {status: 'INCONCLUSIVE', cases: []});
    const app = apparatus('shielded');
    const pkg = await freezeCapability(app, construct(app));
    history = await appendOutEvolveEvent(history, 'package-frozen', {status: 'qualified', package: pkg});
    const checked = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.equal(checked.failed, 1);
    assert.equal(checked.inconclusive, 1);
    assert.equal(checked.packageCount, 1);
    assert.equal(checked.evidenceStatus, 'retained-failure');
    assert.equal(checked.latestPackage.digest, pkg.digest);
    assert.equal(checked.workspace.events[0].payload.cases[0].actual, 0);
});

test('cancelled search reloads and resumes its deterministic frontier and accumulated work', async () => {
    let history = createOutEvolveWorkspace('out-evolve-cancel-test');
    const checkpoint = createSearch(apparatus('referenced'));
    const started = await appendOutEvolveEvent(history, 'search-started', {status: 'searching', checkpoint});
    let result = advanceSearch(checkpoint, {steps: 5});
    result = advanceSearch(result.checkpoint, {cancel: true});
    history = await appendOutEvolveEvent(started, 'search-stopped', {status: result.status, checkpoint: result.checkpoint});
    const restored = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.equal(restored.checkpoint.status, 'cancelled');
    assert.equal(restored.checkpoint.expanded, 5);
    const resumed = advanceSearch(restored.checkpoint, {steps: 1000});
    assert.equal(resumed.status, 'qualified');
    assert.ok(resumed.ledger.synthesis >= result.ledger.synthesis);
    assert.deepEqual(resumed.program, construct(apparatus('referenced')).program);
    assert.equal(history.events[1].payload.status, 'cancelled');
    assert.equal(started.events[0].payload.checkpoint.expanded, 0);
});

test('unrelated package import preserves active search apparatus, bounds and work across history recovery', async () => {
    const original = apparatus('referenced');
    const other = apparatus('shielded');
    const imported = await freezeCapability(other, construct(other));
    for (const status of ['searching', 'cancelled']) {
        let history = createOutEvolveWorkspace(`out-evolve-import-${status}`);
        let search = advanceSearch(createSearch(original, {maxCost: 100000, maxStates: 2000}), {steps: 5});
        if (status === 'cancelled') search = advanceSearch(search.checkpoint, {cancel: true});
        history = await appendOutEvolveEvent(history, 'search-stopped', {status, checkpoint: search.checkpoint});
        const stopped = structuredClone(history);
        history = await appendOutEvolveEvent(history, 'package-frozen', {status: 'qualified', package: imported});
        const restored = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
        assert.equal(restored.latestPackage.digest, imported.digest);
        assert.equal(restored.checkpoint.status, status);
        assert.deepEqual(restored.checkpoint.apparatus, original);
        assert.deepEqual(restored.checkpoint.options, search.checkpoint.options);
        assert.deepEqual(restored.checkpoint.work, search.checkpoint.work);
        assert.deepEqual(restored.workspace.events.slice(0, stopped.events.length), stopped.events);
        const resumed = advanceSearch(restored.checkpoint, {steps: 1000});
        assert.equal(resumed.status, 'qualified');
        assert.deepEqual(resumed.checkpoint.apparatus, original);
        assert.deepEqual(resumed.program, construct(original).program);
    }
});

test('qualified search remains finalizable until its matching package is accepted', async () => {
    const original = apparatus('referenced');
    const search = construct(original);
    const ownPackage = await freezeCapability(original, search);
    const other = apparatus('shielded');
    const imported = await freezeCapability(other, construct(other));
    let history = createOutEvolveWorkspace('out-evolve-qualified-pending');
    history = await appendOutEvolveEvent(history, 'search-stopped', {status: 'qualified', checkpoint: search.checkpoint});
    const stopped = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.equal(stopped.latestPackage, null);
    assert.equal(stopped.checkpoint.status, 'qualified');
    history = await appendOutEvolveEvent(history, 'package-frozen', {status: 'qualified', package: imported});
    const unrelated = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.equal(unrelated.latestPackage.digest, imported.digest);
    assert.deepEqual(exportSearchCheckpoint(unrelated.checkpoint), exportSearchCheckpoint(search.checkpoint));
    const finalized = advanceSearch(unrelated.checkpoint, {steps: 0});
    assert.deepEqual(finalized.ledger, search.ledger);
    assert.equal(finalized.checkpoint.expanded, search.checkpoint.expanded);
    history = await appendOutEvolveEvent(history, 'package-frozen', {status: 'qualified', package: ownPackage});
    const accepted = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.equal(accepted.checkpoint, null);
    assert.equal(accepted.latestPackage.digest, ownPackage.digest);
    assert.equal(accepted.workspace.events.filter(event => event.kind === 'search-stopped').length, 1);
});

test('qualified finalization uses its two reserved terminal slots without another search step or stop', async () => {
    const app = apparatus('shielded');
    const search = construct(app, {maxCost: 100000, maxStates: 2000, maxMemoryStates: 2000, maxProgramSize: 12});
    let history = createOutEvolveWorkspace('out-evolve-finalize-reserve');
    for (let index = 0; index < WORKSPACE_LIMITS.events - 3; index++) {
        history = await appendOutEvolveEvent(history, 'comparison', {status: 'COMPLETED', index});
    }
    assert.equal(searchHistoryCapacity(history, search.checkpoint).canAdvance, true);
    history = await appendOutEvolveEvent(history, 'search-stopped', {status: 'qualified', checkpoint: search.checkpoint});
    const restored = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    const capacity = searchHistoryCapacity(restored.workspace, restored.checkpoint);
    assert.equal(capacity.remainingEvents, 2);
    assert.equal(capacity.canAdvance, false);
    assert.equal(capacity.canFinalize, true);
    const replayed = advanceSearch(restored.checkpoint, {steps: 0});
    assert.deepEqual(replayed.ledger, search.ledger);
    history = await appendOutEvolveEvent(history, 'package-frozen', {
        status: 'qualified', package: await freezeCapability(app, replayed)
    });
    history = await appendOutEvolveEvent(history, 'comparison', {status: 'COMPLETED'});
    assert.equal(history.events.length, WORKSPACE_LIMITS.events);
    assert.equal((await inspectOutEvolveWorkspace(history)).checkpoint, null);
    assert.equal(history.events.filter(event => event.kind === 'search-stopped').length, 1);
});

test('imports reject changed events and executable claims even when package digest is recomputed', async () => {
    let history = createOutEvolveWorkspace('out-evolve-tamper-test');
    history = await appendOutEvolveEvent(history, 'failure', {message: 'Retain original failure.', status: 'FAIL'});
    const changed = structuredClone(history);
    changed.events[0].payload.message = 'Pretend this passed.';
    await assert.rejects(inspectOutEvolveWorkspace(changed), /digest mismatch/);
    const app = apparatus('shielded');
    const pkg = await freezeCapability(app, construct(app));
    pkg.ast.prepare.steps = [{op: 'primitive', id: 'erase-product'}];
    pkg.digest = await digestCapability(pkg);
    await assert.rejects(appendOutEvolveEvent(history, 'package-frozen', {package: pkg, status: 'qualified'}));
    assert.equal(history.events.length, 1);
});

test('tampered checkpoint and mismatched status cannot enter append-only history', async () => {
    const history = createOutEvolveWorkspace('out-evolve-invalid-checkpoint');
    const checkpoint = createSearch(apparatus());
    checkpoint.work.synthesis = 0.5;
    await assert.rejects(appendOutEvolveEvent(history, 'search-started', {status: 'searching', checkpoint}), /tampering rejected/);
    await assert.rejects(appendOutEvolveEvent(history, 'search-stopped', {
        status: 'qualified', checkpoint: createSearch(apparatus())
    }), /status differs/);
});

test('history admits fractional model data while rejecting authority and malformed briefs', async () => {
    let history = createOutEvolveWorkspace('out-evolve-finite-test');
    history = await appendOutEvolveEvent(history, 'comparison', {status: 'COMPLETED', amortizedPerUse: 1.25});
    assert.equal((await inspectOutEvolveWorkspace(history)).workspace.events[0].payload.amortizedPerUse, 1.25);
    const changed = structuredClone(history); changed.authority = ['network'];
    await assert.rejects(inspectOutEvolveWorkspace(changed), /authority/);
    await assert.rejects(appendOutEvolveEvent(history, 'brief', {purpose: 'x', constraints: 'y', budget: 1.5, apparatus: apparatus()}));
    await assert.rejects(appendOutEvolveEvent(history, 'comparison', {status: 'COMPLETED', total: Infinity}));
});

test('importing an earlier same-identity history cannot erase its failures', async () => {
    const earlier = createOutEvolveWorkspace('out-evolve-no-rollback');
    const later = await appendOutEvolveEvent(earlier, 'failure', {status: 'FAIL', message: 'Still failed.'});
    assert.throws(() => requireHistoryContinuation(later, earlier), /discard or replace/);
    requireHistoryContinuation(earlier, later);
    requireHistoryContinuation(later, createOutEvolveWorkspace('out-evolve-separate-history'));
});

function dustyApparatus() {
    const app = apparatus('shielded');
    for (const suffix of ['a', 'b', 'c']) {
        const name = `dust-${suffix}`;
        app.channels.push({...app.channels[0], id: name});
        app.edges.push({id: `${name}-readout`, from: name, to: 'readout', gain: 1});
        for (const original of app.primitives.slice(0, 2)) {
            app.primitives.push({...original, id: `${original.kind}-${name}`, target: name});
        }
    }
    return app;
}

test('long recovery history stores compact candidate replay rather than cumulative queue and attempt copies', async () => {
    let history = createOutEvolveWorkspace('out-evolve-compact-recovery');
    let checkpoint = createSearch(dustyApparatus(), {maxStates: 1000, maxMemoryStates: 20000, maxCost: 1000000});
    history = await appendOutEvolveEvent(history, 'search-started', {status: checkpoint.status, checkpoint});
    for (let chunk = 0; chunk < 24; chunk++) {
        const result = advanceSearch(checkpoint, {steps: 16});
        checkpoint = result.checkpoint;
        assert.equal(result.status, 'searching');
        history = await appendOutEvolveEvent(history, 'search-stopped', {status: result.status,
            checkpoint: exportSearchCheckpoint(checkpoint), ledger: result.ledger,
            attempts: result.attempts, frontier: result.frontier});
        assert.equal(Object.hasOwn(history.events.at(-1).payload, 'attempts'), false);
        assert.equal(Object.hasOwn(history.events.at(-1).payload, 'frontier'), false);
    }
    const cancelled = advanceSearch(checkpoint, {cancel: true});
    history = await appendOutEvolveEvent(history, 'search-stopped', {status: cancelled.status,
        checkpoint: exportSearchCheckpoint(cancelled.checkpoint), ledger: cancelled.ledger});
    assert.ok(checkpoint.expanded > 336);
    assert.ok(JSON.stringify(history).length < 300000);
    const restored = await inspectOutEvolveWorkspace(JSON.parse(JSON.stringify(history)));
    assert.deepEqual(restored.checkpoint.work, checkpoint.work);
    assert.deepEqual(restored.checkpoint.attempts, checkpoint.attempts);
    assert.deepEqual(restored.checkpoint.queue, checkpoint.queue);
    const actual = advanceSearch(restored.checkpoint, {steps: 16});
    const expected = advanceSearch(checkpoint, {steps: 16});
    assert.deepEqual(actual.ledger, expected.ledger);
    assert.deepEqual(actual.program, expected.program);
});

test('workspace reserves terminal evidence and a final unfinished checkpoint before more constructor work', async () => {
    let history = createOutEvolveWorkspace('out-evolve-terminal-reserve');
    const checkpoint = createSearch(apparatus('shielded'), {maxStates: 2000, maxMemoryStates: 2000});
    assert.equal(searchHistoryCapacity(history, checkpoint).canAdvance, true);
    for (let index = 0; index < WORKSPACE_LIMITS.events - 2; index++) {
        history = await appendOutEvolveEvent(history, 'comparison', {status: 'COMPLETED', sequence: index});
    }
    const capacity = searchHistoryCapacity(history, checkpoint);
    assert.equal(capacity.canAdvance, false);
    assert.equal(capacity.remainingEvents, 2);
    assert.ok(capacity.terminalEvidenceReserve > 65536);
    history = await appendOutEvolveEvent(history, 'search-paused', {status: 'INCONCLUSIVE',
        checkpoint: exportSearchCheckpoint(checkpoint), reason: 'History capacity reached before further work.'});
    const restored = await inspectOutEvolveWorkspace(history);
    assert.equal(restored.inconclusive, 1);
    assert.equal(restored.checkpoint.expanded, 0);
    assert.deepEqual(restored.checkpoint.work, checkpoint.work);
    assert.ok(history.events.length <= WORKSPACE_LIMITS.events);
    let byteBound = createOutEvolveWorkspace('out-evolve-byte-reserve');
    byteBound = await appendOutEvolveEvent(byteBound, 'comparison', {status: 'COMPLETED', note: 'x'.repeat(4500000)});
    const bytes = searchHistoryCapacity(byteBound, checkpoint);
    assert.ok(bytes.remainingEvents > 3);
    assert.equal(bytes.canAdvance, false);
    byteBound = await appendOutEvolveEvent(byteBound, 'search-paused', {status: 'INCONCLUSIVE',
        checkpoint: exportSearchCheckpoint(checkpoint), reason: 'Terminal evidence space reserved before execution.'});
    assert.equal((await inspectOutEvolveWorkspace(byteBound)).checkpoint.expanded, 0);
    assert.ok(JSON.stringify(byteBound).length < WORKSPACE_LIMITS.bytes);
});
