// SPDX-License-Identifier: Apache-2.0

let worker;

window.addEventListener('message', (event) => {
  const data = event.data;
  if (!data || typeof data !== 'object') {
    return;
  }

  if (data.type === 'start') {
    if (worker) {
      worker.terminate();
    }
    worker = new Worker(data.url, { type: 'module' });
    worker.onmessage = (messageEvent) => {
      parent.postMessage(messageEvent.data, '*');
    };
    return;
  }

  if (worker) {
    worker.postMessage(data);
  }
});
