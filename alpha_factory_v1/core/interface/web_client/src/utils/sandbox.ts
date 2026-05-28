// SPDX-License-Identifier: Apache-2.0
/**
 * Spawn a Web Worker inside a sandboxed iframe.
 *
 * The worker is created from a Blob URL inside the sandbox and
 * communicates with the parent via postMessage.
 */
export async function createSandboxWorker(url: string | URL): Promise<Worker> {
  return new Promise((resolve) => {
    const workerBlob = new Blob([`import "${url.toString()}";`], { type: "text/javascript" });
    const workerUrl = URL.createObjectURL(workerBlob);

    const iframe = document.createElement('iframe');
    // allow only script execution in the sandboxed iframe
    (iframe as any).sandbox = 'allow-scripts';
    iframe.style.display = 'none';
    iframe.src = new URL("./sandbox_worker_host.html", window.location.href).toString();
    document.body.appendChild(iframe);

    const worker: any = {
      postMessage: (m: any) => iframe.contentWindow!.postMessage(m, "*"),
      terminate() {
        iframe.remove();
        URL.revokeObjectURL(workerUrl);
        window.removeEventListener('message', handler);
      },
      onmessage: null as ((ev: MessageEvent) => void) | null,
    };

    const handler = (e: MessageEvent) => {
      if (e.source === iframe.contentWindow && worker.onmessage) {
        worker.onmessage(e);
      }
    };
    window.addEventListener('message', handler);

    iframe.onload = () => {
      iframe.contentWindow!.postMessage({ type: 'start', url: workerUrl }, "*");
      resolve(worker as unknown as Worker);
    };
  });
}
