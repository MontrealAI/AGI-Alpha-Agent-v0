// SPDX-License-Identifier: Apache-2.0
import { setUseGpu, gpuAvailable, setOffline, isOffline, setApiKey, hasApiKey, setApiModel, getApiModel, chat } from '../utils/llm.ts';
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
    whiteSpace: 'normal',
    maxWidth: 'calc(100vw - 20px)',
    maxHeight: 'calc(100vh - 20px)',
    overflow: 'auto',
    boxSizing: 'border-box',
  });
  const pre = document.createElement('pre');
  pre.style.whiteSpace = 'pre-wrap';
  pre.style.overflowWrap = 'anywhere';
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
  optOffline.textContent = 'Offline GPT-2 (full build)';
  const optApi = document.createElement('option');
  optApi.value = 'api';
  optApi.textContent = 'Run with OpenAI API';
  modeSelect.append(optOffline, optApi);
  modeLabel.appendChild(modeSelect);
  panel.appendChild(modeLabel);
  panel.appendChild(pre);
  const apiModelLabel = document.createElement('label');
  apiModelLabel.textContent = ' API model ID ';
  const apiModelInput = document.createElement('input');
  apiModelInput.id = 'api-model-id';
  apiModelInput.maxLength = 128;
  apiModelInput.placeholder = 'Model available in your account';
  apiModelInput.setAttribute('aria-label', 'OpenAI model ID');
  apiModelInput.value = getApiModel();
  apiModelLabel.style.display = 'block';
  apiModelInput.style.maxWidth = '100%';
  apiModelInput.addEventListener('input', () => setApiModel(apiModelInput.value));
  apiModelLabel.append(apiModelInput);
  panel.appendChild(apiModelLabel);

  const completion = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = 'Try text generation';
  const promptInput = document.createElement('textarea');
  promptInput.id = 'llm-prompt';
  promptInput.maxLength = 4096;
  promptInput.rows = 3;
  promptInput.placeholder = 'The capital of France is';
  promptInput.setAttribute('aria-label', 'Text generation prompt');
  const generate = document.createElement('button');
  generate.id = 'llm-generate';
  generate.textContent = 'Generate';
  const output = document.createElement('p');
  output.id = 'llm-output';
  output.setAttribute('role', 'status');
  output.style.whiteSpace = 'pre-wrap';
  output.style.maxWidth = '320px';
  output.textContent = 'Offline: GPT-2 text completion. First load caches the model for offline use.';
  generate.addEventListener('click', async () => {
    generate.disabled = true;
    output.textContent = 'Generating… The first local model load may take a minute.';
    try { output.textContent = await chat(promptInput.value); }
    catch (error) { output.textContent = error instanceof Error ? error.message : String(error); }
    finally { generate.disabled = false; }
  });
  completion.append(summary, promptInput, document.createElement('br'), generate, output);
  panel.appendChild(completion);

  try {
    const saved = localStorage.getItem('USE_GPU');
    gpuToggle.checked = saved !== '0';
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
  setOffline(modeSelect.value === 'offline');
  modeSelect.addEventListener('change', () => {
    const offline = modeSelect.value === 'offline';
    if (!offline && !getApiModel()) {
      const model = prompt('OpenAI model ID for this paid request');
      if (!model?.trim()) { modeSelect.value = 'offline'; setOffline(true); return; }
      setApiModel(model); apiModelInput.value = model.trim();
    }
    if (!offline && !hasApiKey()) {
      const key = prompt('Enter OpenAI API key');
      if (key) {
        setApiKey(key);
      } else {
        modeSelect.value = 'offline';
      }
    }
    setOffline(modeSelect.value === 'offline');
  });
  document.body.appendChild(panel);
  function update(e: EvaluatorGenome | GpuToggleEvent): void {
    pre.textContent = JSON.stringify(e, null, 2);
  }
  return { update, gpuToggle, modeSelect };
}
