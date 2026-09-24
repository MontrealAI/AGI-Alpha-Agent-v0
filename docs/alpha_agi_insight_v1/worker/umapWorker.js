"use strict";
(() => {
  // lib/pyodide.js
  async function loadPyodide(opts) {
    if (typeof window.loadPyodide === "function") {
      if (window.PYODIDE_WASM_BASE64) {
        const bytes = Uint8Array.from(atob(window.PYODIDE_WASM_BASE64), (c) => c.charCodeAt(0));
        const blob = new Blob([bytes], { type: "application/wasm" });
        const url = URL.createObjectURL(blob);
        return window.loadPyodide({ ...opts, indexURL: url });
      }
      return window.loadPyodide(opts);
    }
    throw new Error("pyodide.js not bundled");
  }

  // src/i18n/en.json
  var en_default = {
    seed: "Seed",
    population: "Population",
    generations: "Generations",
    gaussian: "gaussian",
    swap: "swap",
    jump: "jump",
    scramble: "scramble",
    adaptive: "Adaptive",
    pause: "Pause",
    resume: "Resume",
    export: "Export",
    drop: "Drop JSON here",
    csv: "CSV",
    png: "PNG",
    share: "Share",
    theme: "Theme",
    iframe_copied: "iframe snippet copied",
    link_copied: "permalink copied",
    state_loaded: "state loaded",
    invalid_file: "invalid file",
    simulation_restarted: "simulation restarted",
    telemetry_consent: "Allow anonymous telemetry?",
    download_log: "Download log",
    "summary.debateArena": "Debate Arena",
    "summary.debate": "Debate",
    "label.rank": "Rank",
    "label.score": "Score",
    score: "Score",
    novelty: "Novelty",
    time: "Time",
    respawn: "Re-spawn",
    pyodide_unavailable: "Pyodide unavailable; using JS only",
    pyodide_failed: "Pyodide failed to load; using JS only",
    archive_disabled: "Archive disabled (no storage access)",
    archive_full: "Archive full; oldest runs pruned",
    pin_failed: "pin failed",
    worker_error: "worker error",
    error_unknown: "unknown error",
    disclaimer: "This repository is a conceptual research prototype. References to 'AGI' and 'superintelligence' describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software."
  };

  // src/ui/i18n.ts
  var enStrings = en_default;
  var strings = enStrings;
  function t(key) {
    return strings[key] || enStrings[key] || key;
  }

  // worker/umapWorker.ts
  self.onerror = (e) => {
    self.postMessage({
      type: "error",
      message: e.message,
      url: e.filename,
      line: e.lineno,
      column: e.colno,
      stack: e.error?.stack,
      ts: Date.now()
    });
  };
  self.onunhandledrejection = (ev) => {
    const reason = ev.reason || {};
    self.postMessage({
      type: "error",
      message: reason.message ? String(reason.message) : String(reason),
      stack: reason.stack,
      ts: Date.now()
    });
  };
  var pyReady = null;
  async function initPy() {
    if (!pyReady) {
      pyReady = await loadPyodide({ indexURL: "./wasm/" }).catch(() => null);
      if (!pyReady) self.postMessage({ toast: t("pyodide_failed") });
    }
    return pyReady;
  }
  async function embedTexts(texts) {
    const py = await initPy();
    if (!py) return texts.map(() => [Math.random(), Math.random()]);
    try {
      py.globals.set("texts", texts);
      await py.runPythonAsync(`import json
from sentence_transformers import SentenceTransformer
from umap import UMAP
_model = SentenceTransformer('all-MiniLM-L6-v2')
_emb = _model.encode(texts, normalize_embeddings=True)
_coords = UMAP(n_components=2).fit_transform(_emb)
result = json.dumps(_coords.tolist())`);
      const res = py.globals.get("result");
      return JSON.parse(res);
    } catch {
      return texts.map(() => [Math.random(), Math.random()]);
    }
  }
  self.onmessage = async (ev) => {
    const { population } = ev.data;
    const texts = population.map((p) => p.summary || "");
    const coords = await embedTexts(texts);
    const out = population.map((p, i) => ({ ...p, umap: coords[i] }));
    self.postMessage(out);
  };
})();
