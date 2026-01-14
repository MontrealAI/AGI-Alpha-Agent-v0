// SPDX-License-Identifier: Apache-2.0
let localModel: any;
let useGpu = true;
let ortLoaded: boolean | undefined;
export const llmEvents = new EventTarget();
export const LLM_LOAD_START = 'llm-load-start';
export const LLM_LOAD_END = 'llm-load-end';
export const gpuAvailable =
  typeof navigator !== 'undefined' && !!(navigator as any).gpu;
let runOffline = false;

try {
  const offline = localStorage.getItem('RUN_OFFLINE');
  runOffline = offline === '1';
} catch {}

try {
  const saved = localStorage.getItem('USE_GPU');
  if (saved !== null) {
    useGpu = saved !== '0';
  }
} catch {}

export function setUseGpu(flag: boolean) {
  useGpu = !!flag;
  try {
    localStorage.setItem('USE_GPU', useGpu ? '1' : '0');
  } catch {}
  localModel = null;
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

async function ensureOrt(): Promise<boolean> {
  if (ortLoaded !== undefined) return ortLoaded;
  const runtime: any =
    typeof window !== 'undefined'
      ? window
      : typeof globalThis !== 'undefined'
        ? globalThis
        : undefined;
  if (!runtime) return false;
  if (!runtime.ort) {
    try {
      await import('onnxruntime-web');
    } catch {
      ortLoaded = false;
      return false;
    }
  }
  ortLoaded = !!runtime.ort;
  return ortLoaded;
}

export async function gpuBackend(): Promise<string> {
  if (useGpu && gpuAvailable) {
    const ok = await ensureOrt();
    if (ok) return 'webgpu';
  }
  return 'wasm-simd';
}

async function loadLocal(): Promise<any> {
  if (!localModel) {
    llmEvents.dispatchEvent(new Event(LLM_LOAD_START));
    try {
      const mod = await import('../lib/bundle.esm.min.js');
      const { pipeline } = mod as any;
      const backend = await gpuBackend();
      if (typeof window !== 'undefined') {
        (window as any).LLM_BACKEND = backend;
      }
      if ((window as any).GPT2_MODEL_BASE64) {
        const bytes = Uint8Array.from(atob((window as any).GPT2_MODEL_BASE64), c => c.charCodeAt(0));
        const blob = new Blob([bytes]);
        const url = URL.createObjectURL(blob);
        localModel = await pipeline('text-generation', url, { backend });
      } else {
        localModel = await pipeline('text-generation', './wasm_llm/', { backend });
      }
    } catch (err) {
      localModel = async (p: string) => `[offline] ${p}`;
    } finally {
      llmEvents.dispatchEvent(new Event(LLM_LOAD_END));
    }
  }
  return localModel;
}

export async function chat(prompt: string): Promise<string> {
  const offline = runOffline;
  const key = offline ? null : localStorage.getItem('OPENAI_API_KEY');
  if (key) {
    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages: [{ role: 'user', content: prompt }],
      }),
    });
    const data = await resp.json();
    return data.choices[0].message.content.trim();
  }
  const model = await loadLocal();
  const out = await model(prompt);
  return typeof out === 'string' ? out : out[0]?.generated_text?.trim();
}
