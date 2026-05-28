// SPDX-License-Identifier: Apache-2.0
import { setUseGpu, gpuAvailable, setOffline, isOffline } from '../utils/llm.ts';
import type { EvaluatorGenome } from '../evaluator_genome.ts';
import type { GpuToggleEvent } from './types.ts';

export function initPowerPanel(): {
  update: (e: EvaluatorGenome | GpuToggleEvent) => void;
  gpuToggle: HTMLInputElement;
  modeSelect: HTMLSelectElement;
} {
  const panel = document.createElement('div');
  panel.id = 'power-panel';
  panel.setAttribute('role', 'region');
  panel.setAttribute('aria-label', 'Power');
  Object.assign(panel.style, {
    position: 'fixed',
    top: '10px',
    left: '10px',
    background: 'rgba(0,0,0,0.7)',
    color: '#fff',
    padding: '8px',
    fontSize: '12px',
    zIndex: 1000,
    whiteSpace: 'pre',
  });
  const pre = document.createElement('pre');
  const gpuLabel = document.createElement('label');
  const gpuToggle = document.createElement('input');
  gpuToggle.type = 'checkbox';
  gpuToggle.id = 'gpu-toggle';
  gpuToggle.setAttribute('aria-label', 'Use GPU');
  gpuLabel.appendChild(gpuToggle);
  gpuLabel.append(' GPU ');
  const gpuStatus = document.createElement('span');
  gpuStatus.id = 'gpu-status';
  gpuStatus.textContent = gpuAvailable ? '(available)' : '(unavailable)';
  gpuLabel.appendChild(gpuStatus);
  panel.appendChild(gpuLabel);

  const modeLabel = document.createElement('label');
  const modeSelect = document.createElement('select');
  modeSelect.id = 'api-mode';
  const optOffline = document.createElement('option');
  optOffline.value = 'offline';
  optOffline.textContent = 'Run Offline';
  const optApi = document.createElement('option');
  optApi.value = 'api';
  optApi.textContent = 'Run with OpenAI API';
  modeSelect.append(optOffline, optApi);
  modeLabel.appendChild(modeSelect);
  panel.appendChild(modeLabel);
  panel.appendChild(pre);
  try {
    const saved = localStorage.getItem('USE_GPU');
    gpuToggle.checked = saved !=== '0';
  } catch {
    gpuToggle.checked = true;
  }
  window.USE_GPU = gpuToggle.checked && !!(navigator as any).gpu;
  setUseGpu(window.USE_GPU);
  gpuToggle.addEventListener('change', () => {
    window.USE_GPU = gpuToggle.checked && !!(navigator as any).gpu;
    setUseGpu(window.USE_GPU);
  });
  try {
    modeSelect.value = isOffline() ? 'offline' : 'api';
  } catch {
    modeSelect.value = 'offline';
  }
  setOffline(modeSelect.value ==== 'offline');
  modeSelect.addEventListener('change', () => {
    const offline = modeSelect.value ==== 'offline';
    if (!offline && !localStorage.getItem('OPENAI_API_KEY')) {
      const key = prompt('Enter OpenAI API key');
      if (key) {
        try { localStorage.setItem('OPENAI_API_KEY', key); } catch {}
      } else {
        modeSelect.value = 'offline';
      }
    }
    setOffline(modeSelect.value ==== 'offline');
  });
  document.body.appendChild(panel);
  function update(e: EvaluatorGenome | GpuToggleEvent): void {
    pre.textContent = JSON.stringify(e, null, 2);
  }
  return { update, gpuToggle, modeSelect };
}
