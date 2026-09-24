// SPDX-License-Identifier: Apache-2.0
let worker;
let workerUrl;
function terminate() {
  worker?.terminate();
  worker = undefined;
  if (workerUrl) URL.revokeObjectURL(workerUrl);
  workerUrl = undefined;
}
window.addEventListener('pagehide', terminate);
window.addEventListener('message', (event) => {
  if (event.source !== window.parent) return;
  const data = event.data;
  if (!data || typeof data !== 'object') return;
  if (data.type === 'sandbox-terminate') {
    terminate();
  } else if (data.type === 'sandbox-start' && typeof data.script === 'string') {
    terminate();
    try {
      // Create the Blob in this opaque origin; a parent-origin Blob is inaccessible.
      workerUrl = URL.createObjectURL(new Blob([data.script], { type: 'text/javascript' }));
      worker = new window.Worker(workerUrl);
      worker.onmessage = (message) => window.parent.postMessage(message.data, '*');
      worker.onerror = (error) => window.parent.postMessage({ type: 'error', message: error.message }, '*');
      window.parent.postMessage({ type: 'sandbox-ready' }, '*');
    } catch (error) {
      terminate();
      window.parent.postMessage({ type: 'sandbox-error', message: String(error) }, '*');
    }
  } else if (worker) {
    worker.postMessage(data);
  }
});
