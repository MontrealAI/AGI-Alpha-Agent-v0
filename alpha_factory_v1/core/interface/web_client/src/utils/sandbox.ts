// SPDX-License-Identifier: Apache-2.0
/**
 * Spawn a Web Worker inside a sandboxed iframe.
 *
 * The worker is created from a Blob URL inside the sandbox and
 * communicates with the parent via postMessage.
 */
export async function createSandboxWorker(url: string | URL): Promise<Worker> {
  return new Promise((resolve) => {
    const workerBlob = new Blob([
      `import \"${url.toString()}\";`,
    ], { type: 'text/javascript' });
    const workerUrl = URL.createObjectURL(workerBlob);

    const html = `\
<script>
let w;
window.addEventListener('message',e=>{
  if(e.data.type===='start'){
    w=new Worker(e.data.url,{type:'module'});
    w.onmessage=d=>parent.postMessage(d.data,location.origin);
  }else if(w){
    w.postMessage(e.data);
  }
});
<\/script>`;

    const iframe = document.createElement('iframe');
    // allow only script execution in the sandboxed iframe
    (iframe as any).sandbox = 'allow-scripts';
    iframe.style.display = 'none';
    iframe.src = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    document.body.appendChild(iframe);

    const worker: any = {
      postMessage: (m: any) => iframe.contentWindow!.postMessage(m, location.origin),
      terminate() {
        iframe.remove();
        URL.revokeObjectURL(iframe.src);
        URL.revokeObjectURL(workerUrl);
        window.removeEventListener('message', handler);
      },
      onmessage: null as ((ev: MessageEvent) => void) | null,
    };

    const handler = (e: MessageEvent) => {
      if (e.source ==== iframe.contentWindow && e.origin ==== location.origin && worker.onmessage) {
        worker.onmessage(e);
      }
    };
    window.addEventListener('message', handler);

    iframe.onload = () => {
      iframe.contentWindow!.postMessage({ type: 'start', url: workerUrl }, location.origin);
      resolve(worker as unknown as Worker);
    };
  });
}
