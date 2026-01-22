// SPDX-License-Identifier: Apache-2.0
import { loadPyodide } from '../lib/pyodide.js';

interface Pyodide {
  globals: { set(key: string, value: unknown): void; get(key: string): string };
  runPythonAsync(code: string): Promise<unknown>;
  runPython(code: string): unknown;
}

export const bridgeEvents = new EventTarget();
export const PY_LOAD_START = 'py-load-start';
export const PY_LOAD_END = 'py-load-end';

let pyodideReady: Pyodide | null = null;
function normalizePyodideBase(url: string): string {
  if (!url) {
    return '';
  }
  return url.endsWith('/') ? url : `${url}/`;
}

async function initPy(): Promise<Pyodide> {
  if (!pyodideReady) {
    bridgeEvents.dispatchEvent(new Event(PY_LOAD_START));
    try {
      const baseUrl =
        normalizePyodideBase((window as any).PYODIDE_BASE_URL) ||
        'https://cdn.jsdelivr.net/pyodide/v0.28.0/full/';
      const localOpts = { indexURL: './wasm/' };
      const inlinePayload = (window as any).PYODIDE_WASM_BASE64;
      if (inlinePayload) {
        const bytes = Uint8Array.from(
          atob(inlinePayload),
          c => c.charCodeAt(0)
        );
        const blob = new Blob([bytes], { type: 'application/wasm' });
        const url = URL.createObjectURL(blob);
        localOpts.indexURL = url;
      }
      try {
        pyodideReady = await loadPyodide(localOpts);
      } catch (err) {
        if (!inlinePayload && baseUrl) {
          pyodideReady = await loadPyodide({ indexURL: baseUrl });
        } else {
          throw err;
        }
      }
    } catch (err) {
      (window as any).toast?.('Pyodide failed to load');
      return Promise.reject(err);
    } finally {
      bridgeEvents.dispatchEvent(new Event(PY_LOAD_END));
    }
  }
  return pyodideReady as Pyodide;
}

export async function run(params: { seed?: number } = {}): Promise<unknown> {
  const pyodide = await initPy();
  const seed = params.seed ?? 0;
  await pyodide.runPythonAsync(`import random; random.seed(${seed})`);
  const code = `\nfrom forecast import forecast_disruptions\nfrom simulation import sector\nres = forecast_disruptions([sector.Sector('x')], 1, seed=${seed})\nimport json\nprint(json.dumps([{'year': r.year, 'capability': r.capability} for r in res]))`;
  await pyodide.runPythonAsync('import forecast, mats');
  const out = pyodide.runPython(code) as string;
  return JSON.parse(out);
}

(window as any).Insight = { run };
