"use strict";
(() => {
  // worker/arenaWorker.ts
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
  self.onmessage = (ev) => {
    const { hypothesis } = ev.data || {};
    if (!hypothesis) return;
    const messages = [
      { role: "Proposer", text: `I propose that ${hypothesis}.` },
      { role: "Skeptic", text: `I doubt that ${hypothesis} holds under scrutiny.` },
      { role: "Regulator", text: `Any implementation of ${hypothesis} must be safe.` }
    ];
    const approved = Math.random() > 0.5;
    messages.push({
      role: "Investor",
      text: approved ? `Funding approved for: ${hypothesis}.` : `Funding denied for: ${hypothesis}.`
    });
    const score = approved ? 1 : 0;
    const result = { messages, score };
    self.postMessage(result);
  };
})();
