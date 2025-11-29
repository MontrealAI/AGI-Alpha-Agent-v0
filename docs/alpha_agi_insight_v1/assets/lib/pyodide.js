// SPDX-License-Identifier: Apache-2.0
export async function loadPyodide(opts) {
  if (typeof window.loadPyodide === 'function') {
    if (window.PYODIDE_WASM_BASE64) {
      const bytes = Uint8Array.from(atob(window.PYODIDE_WASM_BASE64), c => c.charCodeAt(0));
      const blob = new Blob([bytes], { type: 'application/wasm' });
      const url = URL.createObjectURL(blob);
      return window.loadPyodide({ ...opts, indexURL: url });
    }
    return window.loadPyodide(opts);
  }
  throw new Error('pyodide.js not bundled');
}
