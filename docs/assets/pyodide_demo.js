/* SPDX-License-Identifier: Apache-2.0 */
/* eslint-env browser */
/* eslint-disable no-undef */
export async function loadRuntime() {
  // This runtime is downloaded from this site only after an explicit request.
  const base = new URL('pyodide/', import.meta.url).href;
  const mod = await import(`${base}pyodide.mjs`);
  return mod.loadPyodide({indexURL: base});
}

export function validatePayload(payload) {
  const {steps, values, logs = []} = payload || {};
  if (!Array.isArray(steps) || !steps.length || steps.length > 1000 ||
      !Array.isArray(values) || values.length !== steps.length ||
      !values.every(value => typeof value === 'number' && Number.isFinite(value)) ||
      !steps.every(step => ['number', 'string'].includes(typeof step)) ||
      !Array.isArray(logs) || !logs.every(line => typeof line === 'string')) {
    throw new Error('Expected 1–1000 steps, matching finite numeric values and text logs.');
  }
  return {steps, values, logs};
}

export function setupPyodideDemo(chart, logEl, experiments, onExperimentRendered) {
  if (!Array.isArray(experiments) || !experiments.length) throw new Error('No bundled experiments found.');
  let selected = experiments[0];
  let pyodide;
  const host = document.getElementById('mode-control');
  const offlineBtn = document.getElementById('offline-mode');
  const onlineBtn = document.getElementById('online-mode');
  const status = document.createElement('p');
  status.id = 'demo-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  host?.after(status);
  if (logEl) {
    logEl.setAttribute('aria-label', 'Experiment log');
    logEl.setAttribute('tabindex', '0');
  }
  const table = document.createElement('table');
  table.setAttribute('aria-label', 'Chart values');
  const details = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = 'View chart data as a table';
  details.append(summary, table);
  logEl?.after(details);
  const pythonBtn = document.createElement('button');
  pythonBtn.type = 'button';
  pythonBtn.textContent = 'Python example (runtime download)';
  pythonBtn.title = 'Optional synthetic example; the first run may download Pyodide.';
  host?.append(pythonBtn);
  if (offlineBtn) {
    offlineBtn.textContent = 'Replay bundled sample';
    offlineBtn.setAttribute('aria-label', 'Replay bundled sample offline');
  }
  if (onlineBtn) {
    onlineBtn.textContent = 'Generate with OpenAI…';
    onlineBtn.setAttribute('aria-label', 'Generate synthetic data with a paid OpenAI API');
  }
  const buttons = [offlineBtn, onlineBtn, pythonBtn];
  function message(text) { status.textContent = text; }
  function render(raw, activeId) {
    const {steps, values, logs} = validatePayload(raw);
    chart.data.labels = steps;
    chart.data.datasets[0].data = values;
    chart.update();
    if (logEl) logEl.textContent = logs.join('\n');
    table.replaceChildren();
    const header = table.createTHead().insertRow();
    for (const text of ['Step', 'Value']) {
      const th = document.createElement('th'); th.scope = 'col'; th.textContent = text; header.append(th);
    }
    const body = table.createTBody();
    steps.forEach((step, i) => {
      const row = body.insertRow(); row.insertCell().textContent = String(step); row.insertCell().textContent = String(values[i]);
    });
    onExperimentRendered?.(activeId);
  }
  async function run(action) {
    buttons.forEach(button => { if (button) button.disabled = true; });
    host?.setAttribute('aria-busy', 'true');
    try { await action(); }
    catch (error) { message(`Could not complete: ${error.message}. Retry or replay the bundled sample.`); }
    finally {
      buttons.forEach(button => { if (button) button.disabled = false; });
      host?.setAttribute('aria-busy', 'false');
    }
  }
  function replay() {
    render(selected.payload, selected.id);
    message('Bundled sample replay — illustrative data, not a live backend or measured investment result.');
  }
  replay();
  window.addEventListener('experiment-change', event => {
    const next = experiments.find(entry => entry.id === event.detail?.id);
    if (next) { selected = next; replay(); }
  });
  offlineBtn?.addEventListener('click', () => run(replay));
  pythonBtn.addEventListener('click', () => run(async () => {
    message('Loading the optional Python runtime…');
    pyodide ||= await loadRuntime();
    const result = await pyodide.runPythonAsync(`import json, random
rng = random.Random(42)
steps = list(range(1, 11))
json.dumps({"steps": steps, "values": [rng.random() for _ in steps], "logs": ["Seeded synthetic Python example"]})`);
    render(JSON.parse(result), 'python-example');
    message('Seeded Python example complete — synthetic data; no demo backend was executed.');
  }));
  onlineBtn?.addEventListener('click', () => run(async () => {
    const model = window.prompt('OpenAI model ID for this paid request (for example gpt-4.1-mini)');
    if (!model?.trim()) return;
    const key = window.prompt('OpenAI API key — used for this request only, never saved');
    if (!key?.trim()) return;
    message('Generating synthetic chart data with OpenAI…');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60000);
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST', signal: controller.signal,
        headers: {'Content-Type': 'application/json', Authorization: `Bearer ${key.trim()}`},
        body: JSON.stringify({model: model.trim(), max_completion_tokens: 1000,
          messages: [{role: 'user', content: 'Return only JSON with steps (10 labels), values (10 finite numbers), logs (10 strings). Use synthetic illustrative data, not investment predictions.'}]}),
      });
      if (!response.ok) throw new Error(`OpenAI returned HTTP ${response.status}`);
      const responseData = await response.json();
      render(JSON.parse(responseData.choices?.[0]?.message?.content || ''), 'openai-response');
      message('OpenAI-generated illustrative data — not a measured demo run.');
    } finally { clearTimeout(timer); }
  }));
}
