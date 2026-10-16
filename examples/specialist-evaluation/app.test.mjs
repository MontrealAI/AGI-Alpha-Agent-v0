// SPDX-License-Identifier: Apache-2.0
/** Actual application source with a controlled clock and minimal DOM; not browser QA. */
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import * as transport from '../../docs/assets/successor/engine.mjs';
import * as evaluation from './engine.mjs';
const source = await readFile(new URL('../../scripts/templates/specialist-evaluation/app.js', import.meta.url), 'utf8');
function harness() {
    let now = Date.parse('2026-10-15T12:00:00.000Z'), timerId = 0;
    const timers = new Map(), elements = new Map(), windowEvents = new Map(), documentEvents = new Map(), downloads = [];
    const element = () => ({value: '', textContent: '', hidden: true, disabled: false, handlers: {},
        addEventListener(type, handler) { this.handlers[type] = handler; }, replaceChildren(...children) { this.children = children; }, click() {}});
    const get = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
    class Clock extends Date { constructor(...args) { super(...(args.length ? args : [now])); } static now() { return now; } }
    const document = {getElementById: get, createElement: element, documentElement: {}, querySelectorAll: () => [],
        visibilityState: 'visible', addEventListener(type, handler) { documentEvents.set(type, handler); }};
    const context = vm.createContext({transport, evaluation, document, Date: Clock, Blob, TextDecoder, console,
        window: {addEventListener(type, handler) { windowEvents.set(type, handler); }},
        URL: {createObjectURL(blob) { downloads.push(blob); return 'blob:test'; }, revokeObjectURL() {}},
        setTimeout(callback, delay) { timers.set(++timerId, {callback, at: now + delay}); return timerId; },
        clearTimeout(id) { timers.delete(id); }});
    // Real engine calls also receive the controlled application clock explicitly.
    context.evaluation = {...evaluation, exampleContract: () => evaluation.exampleContract(new Clock().toISOString()),
        reportTemplate: frozen => evaluation.reportTemplate(frozen, new Clock().toISOString()),
        assess: (frozen, reports) => evaluation.assess(frozen, reports, new Clock().toISOString()),
        restoreRecord: bytes => evaluation.restoreRecord(bytes, new Clock().toISOString())};
    vm.runInContext(source, context);
    return {get, downloads, document, now: () => new Clock().toISOString(),
        click: id => get(id).handlers.click(),
        advance(ms, fire = true) { now += ms; if (fire) for (const [id, timer] of [...timers]) if (timer.at <= now) { timers.delete(id); timer.callback(); } },
        focus: () => windowEvents.get('focus')(), visible: () => documentEvents.get('visibilitychange')()};
}
async function completed(h) {
    const contract = JSON.parse(h.get('contract').value);
    contract.expiresAt = new Date(Date.parse(h.now()) + 10000).toISOString();
    h.get('contract').value = JSON.stringify(contract); await h.click('freeze');
    const report = JSON.parse(h.get('report').value); report.state = 'complete'; report.finishedAt = h.now();
    for (const row of report.rows) {
        row.trialCount = 1;
        for (const metric of row.metrics) {
            metric.lower = metric.upper = row.role === 'candidate' && metric.id === 'quality' ? 20 : 10;
            metric.evidenceDigest = 'a'.repeat(64);
        }
        row.constraints.forEach(c => { c.status = 'reported-pass'; c.evidenceDigest = 'b'.repeat(64); });
    }
    h.get('report').value = JSON.stringify(report); await h.click('add');
    assert.equal(h.get('comparison').textContent, 'reported-comparison-ready-for-review');
    return report;
}
test('actual app expires at deadline without editing and export keeps historical bytes', async () => {
    const h = harness(); await completed(h); await h.click('save'); const before = await h.downloads.at(-1).text();
    h.advance(10000); assert.equal(h.get('comparison').textContent, 'expired');
    await h.click('save'); assert.equal(h.get('comparison').textContent, 'expired');
    assert.equal(await h.downloads.at(-1).text(), before);
});
test('actual app reconciles suspended deadline on focus, visibility and export', async () => {
    for (const trigger of ['focus', 'visible', 'save']) {
        const h = harness(); await completed(h); h.advance(10000, false);
        if (trigger === 'save') await h.click('save'); else h[trigger]();
        assert.equal(h.get('comparison').textContent, 'expired', trigger);
        assert.match(h.get('inspection').textContent, /"authority": "none"/);
    }
});
test('actual app retains earlier complete regression after a passing retry', async () => {
    const h = harness(), report = await completed(h);
    report.attemptId = 'regression'; report.rows[0].metrics.find(m => m.id === 'safety').upper = 12;
    h.get('report').value = JSON.stringify(report); await h.click('add');
    assert.equal(h.get('comparison').textContent, 'retain-incumbent');
    report.attemptId = 'retry'; report.rows[0].metrics.find(m => m.id === 'safety').upper = 10;
    h.get('report').value = JSON.stringify(report); await h.click('add');
    assert.equal(h.get('comparison').textContent, 'retain-incumbent');
    const assessment = JSON.parse(h.get('inspection').textContent);
    assert.equal(assessment.attemptResults.length, 3);
    assert(assessment.failures.some(f => f.attemptId === 'regression' && f.metricId === 'safety'));
});
