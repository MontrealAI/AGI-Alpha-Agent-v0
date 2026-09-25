// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {promises as fs, createReadStream} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';
import http from 'http';
import {chromium} from 'playwright';

function startServer(dir) {
  const types = {'.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.wasm': 'application/wasm', '.svg': 'image/svg+xml'};
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    const filePath = path.join(dir, pathname === '/' ? '/index.html' : pathname);
    const stream = createReadStream(filePath);
    stream.on('error', () => { res.writeHead(404); res.end(); });
    stream.on('open', () => {
      res.writeHead(200, {'Content-Type': types[path.extname(filePath)] || 'application/octet-stream', 'Cache-Control': 'no-store'});
      stream.pipe(res);
    });
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server)));
}

test('a changed service worker installs and takes control without disabling CSP', async () => {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../dist');
  const swPath = path.join(root, 'service-worker.js');
  const original = await fs.readFile(swPath, 'utf8');
  const server = await startServer(root);
  let browser;
  try {
    browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    const session = await context.newCDPSession(page);
    const evaluate = async expression => {
      const result = await session.send('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true, allowUnsafeEvalBlockedByCSP: true});
      assert.equal(result.exceptionDetails, undefined, JSON.stringify(result.exceptionDetails));
      return result.result.value;
    };
    await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
    await evaluate('navigator.serviceWorker.ready.then(() => true)');
    await evaluate('window.previousController = navigator.serviceWorker.controller; window.workerChanged = false; navigator.serviceWorker.addEventListener("controllerchange", () => window.workerChanged = navigator.serviceWorker.controller !== window.previousController); true');
    await fs.writeFile(swPath, original + '\n// Acceptance update changes bytes, not policy or cached content.\n');
    await evaluate('navigator.serviceWorker.getRegistration().then(registration => registration.update()).then(() => true)');
    const deadline = Date.now() + 30000;
    while (!await evaluate('window.workerChanged && navigator.serviceWorker.controller.state === "activated"')) {
      assert.ok(Date.now() < deadline, 'Updated service worker did not take control');
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert.equal(await evaluate('navigator.serviceWorker.controller.state'), 'activated');
  } finally {
    if (browser) await browser.close();
    await fs.writeFile(swPath, original);
    await new Promise(resolve => server.close(resolve));
  }
});
