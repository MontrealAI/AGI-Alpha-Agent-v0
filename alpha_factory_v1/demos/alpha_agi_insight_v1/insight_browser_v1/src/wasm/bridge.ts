// SPDX-License-Identifier: Apache-2.0
import { loadPyodide } from '../../lib/pyodide.js';

interface Pyodide {
  globals: { set(key: string, value: unknown): void; get(key: string): string };
  runPythonAsync(code: string): Promise<unknown>;
  runPython(code: string): unknown;
}

export const bridgeEvents = new EventTarget();
export const PY_LOAD_START = 'py-load-start';
export const PY_LOAD_END = 'py-load-end';

let pyodideReady: Pyodide | null = null;
async function initPy(): Promise<Pyodide> {
  if (!pyodideReady) {
    bridgeEvents.dispatchEvent(new Event(PY_LOAD_START));
    try {
      let opts = { indexURL: './wasm/' };
      if ((window as any).PYODIDE_WASM_BASE64) {
        const bytes = Uint8Array.from(
          atob((window as any).PYODIDE_WASM_BASE64),
          c => c.charCodeAt(0)
        );
        const blob = new Blob([bytes], { type: 'application/wasm' });
        const url = URL.createObjectURL(blob);
        opts.indexURL = url;
      }
      pyodideReady = await loadPyodide(opts);
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
