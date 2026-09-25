// SPDX-License-Identifier: Apache-2.0
type Generator = (prompt: string, options: Record<string, unknown>) => Promise<any>;
let localModel: Promise<Generator> | undefined;
let useGpu = false;
let apiKey = '';
export const llmEvents = new EventTarget();
export const LLM_LOAD_START = 'llm-load-start';
export const LLM_LOAD_END = 'llm-load-end';
export const gpuAvailable = typeof navigator !== 'undefined' && !!(navigator as any).gpu;
let runOffline = true;
try {
  runOffline = localStorage.getItem('RUN_OFFLINE') !== '0';
  useGpu = localStorage.getItem('USE_GPU') === '1';
  // Earlier versions persisted credentials; migrate once to memory and erase storage.
  apiKey = localStorage.getItem('OPENAI_API_KEY') || '';
  localStorage.removeItem('OPENAI_API_KEY');
} catch {}

export function setApiKey(key: string): void { apiKey = key.trim(); }
export function hasApiKey(): boolean { return apiKey.length > 0; }

export function setUseGpu(flag: boolean) {
  useGpu = !!flag;
  try {
    localStorage.setItem('USE_GPU', useGpu ? '1' : '0');
  } catch {}
  // The quantized baseline uses WASM on all platforms; GPU preference is retained.
}

export function setOffline(flag: boolean) {
  runOffline = !!flag;
  try {
    localStorage.setItem('RUN_OFFLINE', runOffline ? '1' : '0');
  } catch {}
}

export function isOffline(): boolean {
  return runOffline;
}

export async function gpuBackend(): Promise<string> {
  // Report the backend actually used by the quantized baseline.
  return 'wasm-simd';
}

async function loadLocal(): Promise<Generator> {
  if (!localModel) {
    llmEvents.dispatchEvent(new Event(LLM_LOAD_START));
    localModel = (async () => {
      const base = new URL('./assets/local-llm/', document.baseURI);
      const moduleUrl = new URL('transformers.min.js', base).href;
      const { pipeline, env } = await import(moduleUrl);
      env.allowRemoteModels = false;
      env.allowLocalModels = true;
      env.localModelPath = new URL('models/', base).href;
      env.backends.onnx.wasm.wasmPaths = base.href;
      env.backends.onnx.wasm.numThreads = 1;
      env.backends.onnx.wasm.proxy = false;
      const generator = await pipeline('text-generation', 'gpt2', { device: 'wasm', dtype: 'q8' });
      (window as any).LLM_BACKEND = await gpuBackend();
      return generator as Generator;
    })();
    try { return await localModel; }
    catch (error) {
      localModel = undefined;
      throw new Error('Local model unavailable. Install the full browser build with its verified ONNX assets. ' + String(error));
    } finally { llmEvents.dispatchEvent(new Event(LLM_LOAD_END)); }
  }
  return localModel;
}

export async function chat(prompt: string): Promise<string> {
  if (!prompt.trim() || prompt.length > 4096) throw new Error('Enter a prompt of 1–4096 characters.');
  if (!runOffline && apiKey) {
    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      signal: AbortSignal.timeout(60000),
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ model: 'gpt-3.5-turbo', messages: [{ role: 'user', content: prompt }], max_tokens: 256 }),
    });
    if (!resp.ok) throw new Error(`Model provider returned HTTP ${resp.status}`);
    const data = await resp.json();
    const text = data?.choices?.[0]?.message?.content;
    if (typeof text !== 'string' || !text.trim()) throw new Error('Model provider returned no text.');
    return text.trim();
  }
  if (!runOffline) throw new Error('Enter an API key or select offline mode.');
  const generator = await loadLocal();
  const output = await generator(prompt, { max_new_tokens: 32, do_sample: false, return_full_text: false });
  const text = output?.[0]?.generated_text;
  if (typeof text !== 'string' || !text.trim()) throw new Error('Local model returned no text.');
  return text.trim();
}
