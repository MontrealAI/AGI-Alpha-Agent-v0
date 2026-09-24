// SPDX-License-Identifier: Apache-2.0
'use strict';
const $ = (id) => document.getElementById(id);
let token = '', selected = null, paused = false;
const examples = {
  research: {goal: 'Summarize the pilot observations and identify what still needs verification.', work: {kind: 'research', sources: [
    {id: 'pilot', title: 'Sample pilot observations', text: 'The pilot processed 120 requests. Nine requests required manual review. The pilot ran for one week. No production reliability conclusion was established.'},
    {id: 'cost', title: 'Sample cost notes', text: 'Measured compute cost was 24 planning units. Staff review time was not measured. Revenue has not been observed.'}
  ]}},
  allocation: {goal: 'Choose sample projects with the highest stated value within the resource and risk limits.', work: {kind: 'allocation', budget: 10, max_risk: 5, unit: 'sample planning units', items: [
    {id: 'prototype', cost: 6, value: 12, risk: 3}, {id: 'instrumentation', cost: 5, value: 11, risk: 1}, {id: 'workflow', cost: 5, value: 11, risk: 2}
  ]}},
  schedule: {goal: 'Reduce the sample schedule makespan while respecting machine availability and job precedence.', work: {kind: 'schedule', unit: 'minutes', jobs: [
    {id: 'A', due: 16, operations: [{machine: 'mill', duration: 3}, {machine: 'lathe', duration: 6}]},
    {id: 'B', due: 16, operations: [{machine: 'lathe', duration: 2}, {machine: 'mill', duration: 5}]},
    {id: 'C', due: 20, operations: [{machine: 'mill', duration: 2}, {machine: 'lathe', duration: 3}]}
  ]}},
  forecast: {goal: 'Compare forecasting policies on the sample history and report separate holdout error.', work: {kind: 'forecast', observations: [10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44], holdout: 4, horizon: 3, season: 1, unit: 'sample observed units'}}
};
examples.code = {goal: 'Implement solve(values): return the sum of the squares of the supplied integers.', work: {kind: 'code', examples: [{args: [[1, 2]], expected: 5}], heldout: [{args: [[-3, 0, 4]], expected: 25}, {args: [[]], expected: 0}], candidate: ''}};
const hints = {code: 'Requires enabled code execution, Docker and a configured model (or supplied candidate). Held-out expected answers stay outside the model and sandbox. Results require all cases to pass and your review.', research: 'Each source needs a unique id, title and text. The result cites exact passages.', allocation: 'Each item has integer cost, value and risk. Use one consistent unit for cost, value and budget.', schedule: 'Each job lists its operations in order, with a machine, duration and optional due time.', forecast: 'List at least 12 chronological observations. The final holdout is excluded from model selection.'};
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
async function api(path, options = {}) {
  const response = await fetch('/api' + path, {...options, headers: {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', ...(options.headers || {})}});
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.error === 'string' ? body.error : typeof body.detail === 'string' ? body.detail : 'Request failed; check your mission data and agent state.');
  return body;
}
function loadExample() { const kind = $('kind').value; $('goal').value = examples[kind].goal; $('input').value = JSON.stringify(examples[kind].work, null, 2); $('input-help').textContent = hints[kind]; }
function render(record) {
  if (selected && selected.id === record.id && selected.revision > record.revision) return;
  const changed = !selected || selected.id !== record.id || selected.revision !== record.revision;
  selected = record; $('empty').hidden = true; $('detail').hidden = false;
  $('mission-label').textContent = record.state + ' · ' + record.request.work.kind;
  $('mission-goal').textContent = record.request.goal;
  $('stages').replaceChildren(...(record.stages || []).map(stage => {const li = document.createElement('li'); li.textContent = stage.role; return li;}));
  $('result').textContent = JSON.stringify(record.result ? {result: record.result, verification: record.verification, inference: record.inference} : {state: record.state, error: record.error || null}, null, 2);
  $('result-summary').replaceChildren();
  if (record.result && record.result.improvement !== undefined) {const p = document.createElement('p'); p.className = 'metric'; p.textContent = 'Measured objective improvement: ' + record.result.improvement + ' ' + record.result.unit + '. ' + record.result.limits; $('result-summary').append(p);}
  $('review-box').hidden = record.state !== 'review'; $('download').hidden = record.state !== 'completed';
  $('recover').hidden = !['failed', 'running', 'queued'].includes(record.state); $('recover').textContent = record.state === 'queued' ? 'Execute queued mission' : 'Recover and rerun';
  if (changed) $('review-note').value = '';
}
async function refresh() {
  const status = await api('/status'); paused = status.control === 'paused';
  $('agent-name').textContent = status.name; $('integrity').textContent = status.events + ' signed events · verified';
  $('inference').textContent = status.inference; $('identity').textContent = status.identity;
  $('pause').textContent = paused ? 'Resume agent' : 'Pause agent'; $('connection').textContent = paused ? 'Paused' : 'Connected';
  $('start').disabled = paused;
  const records = await api('/missions');
  $('missions').replaceChildren(...records.slice().reverse().map(record => {const row = document.createElement('button'); row.className = 'mission-row'; const title = document.createElement('span'); title.textContent = record.request.goal; const state = document.createElement('small'); state.textContent = record.state; row.append(title, state); row.addEventListener('click', () => render(record)); return row;}));
  if (!records.length) $('missions').textContent = 'No missions yet. Start with an example or load your own data.';
  if (selected) {const current = records.find(r => r.id === selected.id); if (current) render(current);}
}
async function guarded(action) {try {await action();} catch (error) {message(error.message, true);}}
$('login-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {token = $('token').value.trim(); await refresh(); $('token').value = ''; $('login').hidden = true; $('workspace').hidden = false; message('Connected. All execution stays under your review.');});});
$('disconnect').addEventListener('click', () => {token = ''; selected = null; $('workspace').hidden = true; $('login').hidden = false; $('connection').textContent = 'Disconnected'; $('missions').replaceChildren(); $('result').textContent = ''; message('Disconnected.');});
$('kind').addEventListener('change', loadExample);
$('mission-file').addEventListener('change', () => guarded(async () => {const file = $('mission-file').files[0]; if (!file) return; if (file.size > 512 * 1024) throw new Error('Mission file exceeds 512 KiB.'); const data = JSON.parse(await file.text()); if (!data.work || !examples[data.work.kind]) throw new Error('Choose a supported mission file.'); $('kind').value = data.work.kind; $('goal').value = data.goal; $('input').value = JSON.stringify(data.work, null, 2); $('input-help').textContent = hints[data.work.kind];}));
$('mission-form').addEventListener('submit', event => {event.preventDefault(); guarded(async () => {
  $('start').disabled = true; message('Running the mission. You can pause the agent while it works.');
  try {const input = {goal: $('goal').value, work: JSON.parse($('input').value)}; const queued = await api('/missions', {method: 'POST', headers: {'Idempotency-Key': crypto.randomUUID()}, body: JSON.stringify(input)}); render(queued); const result = await api('/missions/' + queued.id + '/execute', {method: 'POST', body: '{}'}); render(result); await refresh(); message('Result ready. Inspect the evidence and add your review.');}
  finally {$('start').disabled = paused;}
});});
$('pause').addEventListener('click', () => guarded(async () => {await api('/control', {method: 'POST', body: JSON.stringify({state: paused ? 'ready' : 'paused'})}); await refresh(); message(paused ? 'Agent paused. Active bounded work stops at its next checkpoint; inference may finish its current request.' : 'Agent resumed.');}));
$('refresh').addEventListener('click', () => guarded(refresh));
async function review(approve) {if (!selected) return; const note = $('review-note').value.trim(); if (!note) throw new Error('Add a review note before deciding.'); const record = await api('/missions/' + selected.id + '/review', {method: 'POST', body: JSON.stringify({revision: selected.revision, result_hash: selected.verification.result_hash, approve, note})}); render(record); await refresh(); message(approve ? 'Approved and archived. The signed result is ready to download.' : 'Rejected. The result and review remain in the journal.');}
$('approve').addEventListener('click', () => guarded(() => review(true)));
$('reject').addEventListener('click', () => guarded(() => review(false)));
$('download').addEventListener('click', () => guarded(async () => {const data = await api('/missions/' + selected.id + '/export'); const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'})); const link = document.createElement('a'); link.href = url; link.download = 'agialpha-' + selected.id + '.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);}));
$('recover').addEventListener('click', () => guarded(async () => {if (selected.state !== 'queued') await api('/missions/' + selected.id + '/recover', {method: 'POST', body: '{}'}); render(await api('/missions/' + selected.id + '/execute', {method: 'POST', body: '{}'})); await refresh();}));
loadExample();
