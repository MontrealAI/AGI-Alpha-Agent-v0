// SPDX-License-Identifier: Apache-2.0
/** Spawn a self-contained worker in an opaque-origin, script-only iframe. */
export async function createSandboxWorker(url: string | URL): Promise<Worker> {
  const source = new URL(url.toString(), window.location.href);
  if (source.origin !== window.location.origin) throw new Error('Worker source must be same-origin');
  const response = await fetch(source);
  if (!response.ok) throw new Error(`Worker source unavailable: ${response.status}`);
  const script = await response.text();
  return new Promise((resolve, reject) => {
    const iframe = document.createElement('iframe');
    iframe.setAttribute('sandbox', 'allow-scripts');
    iframe.style.display = 'none';
    iframe.src = new URL('./sandbox_worker_host.html', window.location.href).toString();
    let timer: ReturnType<typeof setTimeout>;
    let settled = false;
    const worker: any = {
      postMessage: (message: unknown) => iframe.contentWindow!.postMessage(message, '*'),
      terminate() {
        clearTimeout(timer);
        iframe.contentWindow?.postMessage({ type: 'sandbox-terminate' }, '*');
        iframe.remove();
        window.removeEventListener('message', handler);
      },
      onmessage: null as ((event: MessageEvent) => void) | null,
    };
    const handler = (event: MessageEvent) => {
      if (event.source !== iframe.contentWindow) return;
      if (event.data?.type === 'sandbox-ready' && !settled) {
        settled = true;
        clearTimeout(timer);
        resolve(worker as Worker);
      } else if (event.data?.type === 'sandbox-error' && !settled) {
        settled = true;
        worker.terminate();
        reject(new Error(event.data.message));
      } else if (worker.onmessage) {
        worker.onmessage(event);
      }
    };
    window.addEventListener('message', handler);
    iframe.onload = () => iframe.contentWindow!.postMessage({ type: 'sandbox-start', script }, '*');
    timer = setTimeout(() => {
      worker.terminate();
      reject(new Error('Sandbox worker startup timed out'));
    }, 10000);
    document.body.appendChild(iframe);
  });
}
