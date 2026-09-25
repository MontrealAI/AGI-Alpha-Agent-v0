/* SPDX-License-Identifier: Apache-2.0 */
/* eslint-env browser */
/* global Chart */
/* eslint-disable no-undef */
import {setupPyodideDemo} from './pyodide_demo.js';

function normalizeExperiments(data) {
  if (!data || typeof data !== 'object') {
    return [{id: 'default', payload: {steps: [], values: [], logs: []}}];
  }

  if (Array.isArray(data.experiments)) {
    return data.experiments.map((experiment, idx) => {
      if (experiment && typeof experiment === 'object' && !Array.isArray(experiment)) {
        const id = experiment.id || experiment.name || `experiment-${idx + 1}`;
        return {id, payload: experiment};
      }
      return {id: `experiment-${idx + 1}`, payload: {steps: [], values: [], logs: []}};
    });
  }

  if (data.experiments && typeof data.experiments === 'object') {
    return Object.entries(data.experiments).map(([id, payload]) => ({id, payload}));
  }

  if (data.runs && typeof data.runs === 'object') {
    return Object.entries(data.runs).map(([id, payload]) => ({id, payload}));
  }

  return [{id: data.id || 'default', payload: data}];
}

function ensureExperimentTabs(experiments, onSelect) {
  if (experiments.length <= 1) {
    return;
  }

  const host = document.getElementById('experiment-tabs') || (() => {
    const el = document.createElement('div');
    el.id = 'experiment-tabs';
    el.setAttribute('role', 'group');
    el.setAttribute('aria-label', 'Bundled experiments');
    const chart = document.getElementById('chart');
    chart?.parentNode?.insertBefore(el, chart);
    return el;
  })();

  host.textContent = '';

  experiments.forEach((experiment, idx) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = experiment.id;
    btn.dataset.expId = experiment.id;
    btn.setAttribute('data-experiment', 'true');
    btn.setAttribute('aria-pressed', idx === 0 ? 'true' : 'false');
    btn.addEventListener('click', () => onSelect(experiment.id));
    host.appendChild(btn);
  });
}

export async function replayChart({logsUrl, chartId = 'chart', logElId = 'logs-panel', label = 'Demo Metric', color = 'blue'}) {
  try {
    const res = await fetch(logsUrl);
    if (!res.ok) throw new Error(`Sample data returned HTTP ${res.status}`);
    const data = await res.json();
    const experiments = normalizeExperiments(data);
    const ctx = document.getElementById(chartId);
    if (!ctx) return;
    const chart = new Chart(ctx, {
      type: 'line',
      data: { labels: [], datasets: [{ label, data: [], fill: false, borderColor: color }] },
      options: { animation: false, responsive: true, maintainAspectRatio: false }
    });
    const logEl = document.getElementById(logElId);
    setupPyodideDemo(chart, logEl, experiments, (activeId) => {
      const tabButtons = document.querySelectorAll('#experiment-tabs [data-experiment]');
      tabButtons.forEach((btn) => {
        btn.setAttribute('aria-pressed', btn.dataset.expId === activeId ? 'true' : 'false');
      });
    });
    ensureExperimentTabs(experiments, (id) => window.dispatchEvent(new CustomEvent('experiment-change', {detail: {id}})));
  } catch (err) {
    const status = document.getElementById(logElId);
    if (status) {
      status.setAttribute('role', 'alert');
      status.textContent = `Demo could not load: ${err.message}. Reload the page or open the local guide.`;
    }
    console.error('replay failed', err);
  }
}
