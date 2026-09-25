"use strict";
(() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __esm = (fn, res) => function __init() {
    return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
  };
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };

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
  var init_pyodide = __esm({
    "lib/pyodide.js"() {
      "use strict";
    }
  });

  // src/wasm/bridge.ts
  var bridge_exports = {};
  __export(bridge_exports, {
    PY_LOAD_END: () => PY_LOAD_END,
    PY_LOAD_START: () => PY_LOAD_START,
    bridgeEvents: () => bridgeEvents,
    run: () => run
  });
  async function initPy() {
    if (!pyodideReady) {
      bridgeEvents.dispatchEvent(new Event(PY_LOAD_START));
      try {
        let opts = { indexURL: "./wasm/" };
        if (window.PYODIDE_WASM_BASE64) {
          const bytes = Uint8Array.from(
            atob(window.PYODIDE_WASM_BASE64),
            (c) => c.charCodeAt(0)
          );
          const blob = new Blob([bytes], { type: "application/wasm" });
          const url = URL.createObjectURL(blob);
          opts.indexURL = url;
        }
        pyodideReady = await loadPyodide(opts);
      } catch (err) {
        window.toast?.("Pyodide failed to load");
        return Promise.reject(err);
      } finally {
        bridgeEvents.dispatchEvent(new Event(PY_LOAD_END));
      }
    }
    return pyodideReady;
  }
  async function run(params = {}) {
    const pyodide = await initPy();
    const seed = params.seed ?? 0;
    await pyodide.runPythonAsync(`import random; random.seed(${seed})`);
    const code = `
from forecast import forecast_disruptions
from simulation import sector
res = forecast_disruptions([sector.Sector('x')], 1, seed=${seed})
import json
print(json.dumps([{'year': r.year, 'capability': r.capability} for r in res]))`;
    await pyodide.runPythonAsync("import forecast, mats");
    const out = pyodide.runPython(code);
    return JSON.parse(out);
  }
  var bridgeEvents, PY_LOAD_START, PY_LOAD_END, pyodideReady;
  var init_bridge = __esm({
    "src/wasm/bridge.ts"() {
      "use strict";
      init_pyodide();
      bridgeEvents = new EventTarget();
      PY_LOAD_START = "py-load-start";
      PY_LOAD_END = "py-load-end";
      pyodideReady = null;
      window.Insight = { run };
    }
  });

  // src/evolve/mutate.ts
  function mutate(pop, rand, strategies, gen = 0, adaptive = false, scale = 1, gpu = false) {
    const clamp = (v) => Math.min(1, Math.max(0, v));
    const mutants = [];
    function converged() {
      if (!adaptive) return false;
      const meanL = pop.reduce((s, d) => s + (d.logic ?? 0), 0) / pop.length;
      const meanF = pop.reduce((s, d) => s + (d.feasible ?? 0), 0) / pop.length;
      const varL = pop.reduce((s, d) => s + Math.pow((d.logic ?? 0) - meanL, 2), 0) / pop.length;
      const varF = pop.reduce((s, d) => s + Math.pow((d.feasible ?? 0) - meanF, 2), 0) / pop.length;
      return varL + varF < 1e-3;
    }
    const isConv = converged();
    for (const d of pop) {
      for (const s of strategies) {
        switch (s) {
          case "gaussian":
            {
              let sigma = 0.12 * Math.log1p(d.horizonYears || 0) * scale;
              if (isConv) sigma *= 0.5;
              mutants.push({
                logic: clamp(d.logic + (rand() - 0.5) * sigma),
                feasible: clamp(d.feasible + (rand() - 0.5) * sigma),
                strategy: s,
                depth: gen,
                horizonYears: d.horizonYears
              });
            }
            break;
          case "swap": {
            const other = pop[Math.floor(rand() * pop.length)];
            mutants.push({
              logic: other.logic,
              feasible: d.feasible,
              strategy: s,
              depth: gen,
              horizonYears: d.horizonYears
            });
            break;
          }
          case "jump":
            mutants.push({
              logic: rand(),
              feasible: rand(),
              strategy: s,
              depth: gen,
              horizonYears: d.horizonYears
            });
            break;
          case "scramble": {
            const other = pop[Math.floor(rand() * pop.length)];
            mutants.push({
              logic: d.logic,
              feasible: other.feasible,
              strategy: s,
              depth: gen,
              horizonYears: d.horizonYears
            });
            break;
          }
        }
      }
    }
    return pop.concat(mutants);
  }

  // src/utils/pareto.ts
  function paretoFront(pop) {
    if (pop.length === 0) return [];
    const sorted = [...pop].sort(
      (a, b) => b.logic - a.logic || b.feasible - a.feasible
    );
    const front = [];
    let bestFeasible = -Infinity;
    for (const p of sorted) {
      if (p.feasible >= bestFeasible) {
        front.push(p);
        bestFeasible = p.feasible;
      }
    }
    return front;
  }

  // src/utils/rng.ts
  function lcg(seed) {
    function rand() {
      seed = Math.imul(1664525, seed) + 1013904223 >>> 0;
      return seed / 2 ** 32;
    }
    rand.state = () => seed;
    rand.set = (s) => {
      seed = s >>> 0;
    };
    return rand;
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

  // worker/evolver.ts
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
  var ua = self.navigator?.userAgent ?? "";
  var isSafari = /Safari/.test(ua) && !/Chrome|Chromium|Edge/.test(ua);
  var isIOS = /(iPad|iPhone|iPod)/.test(ua);
  var pyReady;
  var warned = false;
  var pySupported = !(isSafari || isIOS);
  var gpuAvailable = false;
  async function loadPy() {
    if (!pySupported) {
      if (!warned) {
        self.postMessage({ toast: t("pyodide_unavailable") });
        warned = true;
      }
      return null;
    }
    if (!pyReady) {
      try {
        const mod = await Promise.resolve().then(() => (init_bridge(), bridge_exports));
        pyReady = mod.initPy ? mod.initPy() : null;
      } catch {
        pyReady = null;
        pySupported = false;
        if (!warned) {
          self.postMessage({ toast: t("pyodide_failed") });
          warned = true;
        }
      }
    }
    return pyReady;
  }
  function shuffle(arr, rand) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
  }
  self.onmessage = async (ev) => {
    if (ev.data?.type === "gpu") {
      gpuAvailable = !!ev.data.available;
      return;
    }
    const {
      pop,
      rngState,
      mutations,
      popSize,
      critic,
      gen,
      adaptive,
      sigmaScale = 1
    } = ev.data;
    const rand = lcg(0);
    rand.set(rngState);
    let next = mutate(
      pop,
      rand,
      mutations,
      gen,
      adaptive,
      sigmaScale,
      gpuAvailable
    );
    const front = paretoFront(next);
    next.forEach((d) => d.front = front.includes(d));
    if (critic === "llm") {
      await loadPy();
    }
    shuffle(next, rand);
    next = front.concat(next.slice(0, popSize - 10));
    const metrics = {
      avgLogic: next.reduce((s, d) => s + (d.logic ?? 0), 0) / next.length,
      avgFeasible: next.reduce(
        (s, d) => s + (d.feasible ?? 0),
        0
      ) / next.length,
      frontSize: front.length
    };
    const result = {
      pop: next,
      rngState: rand.state(),
      front,
      metrics
    };
    self.postMessage(result);
  };
})();
