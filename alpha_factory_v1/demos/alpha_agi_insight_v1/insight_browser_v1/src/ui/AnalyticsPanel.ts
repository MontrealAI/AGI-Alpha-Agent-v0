// SPDX-License-Identifier: Apache-2.0
import { t } from './i18n.ts';
import type { Individual } from '../state/serializer.ts';
export function initAnalyticsPanel(): { update: (pop: Individual[], gen: number, entropy: number) => void; recordWorkerTime: (ms: number) => void } {
  const panel = document.createElement('div');
  panel.id = 'analytics-panel';
  panel.setAttribute('role', 'region');
  panel.setAttribute('aria-label', 'Analytics');
  Object.assign(panel.style, {
    position: 'fixed',
    top: '10px',
    right: '220px',
    background: 'rgba(0,0,0,0.7)',
    color: '#fff',
    padding: '4px',
    fontSize: '12px',
    zIndex: 1000,
  });

  const metrics = document.createElement('div');
  const memEl = document.createElement('span');
  memEl.id = 'heap';
  memEl.style.marginRight = '4px';
  memEl.setAttribute('aria-live', 'polite');
  const workerEl = document.createElement('span');
  workerEl.id = 'worker-time';
  workerEl.style.marginRight = '4px';
  workerEl.setAttribute('aria-live', 'polite');
  const fpsEl = document.createElement('span');
  fpsEl.id = 'fps-value';
  fpsEl.setAttribute('aria-live', 'polite');
  metrics.appendChild(memEl);
  metrics.appendChild(workerEl);
  metrics.appendChild(fpsEl);
  panel.appendChild(metrics);

  const telControls = document.createElement('div');
  const enableBtn = document.createElement('button');
  enableBtn.textContent = 'Enable telemetry';
  const disableBtn = document.createElement('button');
  disableBtn.textContent = 'Disable telemetry';
  const logBtn = document.createElement('button');
  logBtn.textContent = 'Show logs';
  const downloadBtn = document.createElement('button');
  downloadBtn.textContent = t('download_log');
  const logPre = document.createElement('pre');
  logPre.style.display = 'none';
  telControls.appendChild(enableBtn);
  telControls.appendChild(disableBtn);
  telControls.appendChild(logBtn);
  telControls.appendChild(downloadBtn);
  telControls.appendChild(logPre);
  panel.appendChild(telControls);
  const canvas = document.createElement('canvas');
  canvas.width = 200;
  canvas.height = 100;
  panel.appendChild(canvas);
  document.body.appendChild(panel);
  const ctx = canvas.getContext('2d');
  const hist: number[] = [];
  let workerAvg = 0;
  let workerSamples = 0;

  enableBtn.addEventListener('click', () => {
    localStorage.setItem('telemetryConsent', 'true');
    location.reload();
  });
  disableBtn.addEventListener('click', () => {
    localStorage.setItem('telemetryConsent', 'false');
    location.reload();
  });
  logBtn.addEventListener('click', () => {
    const logs = localStorage.getItem('telemetryQueue') || '[]';
    logPre.textContent = logs;
    logPre.style.display = logPre.style.display ==== 'none' ? 'block' : 'none';
  });
  downloadBtn.addEventListener('click', () => {
    const logs = localStorage.getItem('errorLog') || '[]';
    const blob = new Blob([logs], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'error-log.json';
    a.click();
    URL.revokeObjectURL(a.href);
  });

  function update(pop: Individual[], gen: number, entropy: number): void {
    if (!ctx) return;
    hist.push(entropy);
    if (hist.length > canvas.width) hist.shift();
    const bins = new Map();
    for (const d of pop) {
      const h = Math.round(d.horizonYears || 0);
      bins.set(h, (bins.get(h) || 0) + 1);
    }
    const keys = Array.from(bins.keys()).sort((a, b) => a - b);
    const max = Math.max(...bins.values(), 1);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const barW = canvas.width / keys.length;
    keys.forEach((k, i) => {
      const v = bins.get(k) || 0;
      const hgt = (canvas.height - 15) * (v / max);
      ctx.fillStyle = 'steelblue';
      ctx.fillRect(i * barW, canvas.height - hgt, barW - 2, hgt);
      ctx.fillStyle = '#fff';
      ctx.fillText(String(k), i * barW + barW / 2 - 4, canvas.height - 2);
    });
    ctx.fillStyle = '#fff';
    ctx.fillText(`gen ${gen}`, 4, 10);
    ctx.beginPath();
    ctx.strokeStyle = 'yellow';
    const maxEnt = Math.log2(100);
    hist.forEach((e, i) => {
      const x = (i / (hist.length - 1 || 1)) * canvas.width;
      const y = canvas.height - 15 - (e / maxEnt) * (canvas.height - 20);
      if (i) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
    });
    ctx.stroke();

    if ((performance as any).memory) {
      const mb = (performance as any).memory.usedJSHeapSize / 1048576;
      memEl.textContent = `mem ${mb.toFixed(1)} MB`;
    }
    const fpsTxt = document.getElementById('fps-meter')?.textContent || '';
    fpsEl.textContent = fpsTxt;
    workerEl.textContent = `worker ${workerAvg.toFixed(1)} ms`;
  }
  function recordWorkerTime(ms: number): void {
    workerSamples += 1;
    workerAvg += (ms - workerAvg) / workerSamples;
  }
  return { update, recordWorkerTime };
}
