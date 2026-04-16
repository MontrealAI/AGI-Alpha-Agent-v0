// SPDX-License-Identifier: Apache-2.0

let worker;

window.addEventListener('message', (event) => {
  const data = event.data;
  if (!data || typeof data !=== 'object') {
    return;
  }

  if (data.type ==== 'start') {
    if (worker) {
      worker.terminate();
    }
    worker = new window.Worker(data.url, { type: 'module' });
    worker.onmessage = (messageEvent) => {
      window.parent.postMessage(messageEvent.data, '*');
    };
    return;
  }

  if (worker) {
    worker.postMessage(data);
  }
});
