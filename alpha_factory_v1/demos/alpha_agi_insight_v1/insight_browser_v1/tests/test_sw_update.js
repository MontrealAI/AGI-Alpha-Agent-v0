// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {promises as fs} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';
import http from 'http';
import {chromium} from 'playwright';

function startServer(dir) {
  const server = http.createServer((req, res) => {
    const filePath = path.join(dir, req.url === '/' ? '/index.html' : req.url);
    fs.readFile(filePath).then(data => {
      res.writeHead(200);
      res.end(data);
    }).catch(() => {
      res.writeHead(404);
      res.end();
    });
  });
  return new Promise(resolve => {
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

const skip = !!process.env.CI;

test('service worker update reloads page', { skip }, async () => {
  let browser;
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const dist = path.resolve(__dirname, '../dist');
  const server = await startServer(dist);
  const {port} = server.address();
  const url = `http://127.0.0.1:${port}/index.html`;
  const swPath = path.join(dist, 'service-worker.js');
  const original = await fs.readFile(swPath, 'utf8');

  try {
    browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(url);
    await page.waitForSelector('#controls', { state: 'attached' });
    await page.waitForFunction('navigator.serviceWorker.ready');
    const initial = await page.evaluate(() => navigator.serviceWorker.controller?.scriptURL);

    const updated = original.replace(/CACHE_VERSION\s*=\s*['"](?:.*?)['"]/,'CACHE_VERSION="test"');
    await fs.writeFile(swPath, updated);

    await page.evaluate('navigator.serviceWorker.getRegistration().then(r=>r.update())');
    await page.waitForFunction('performance.getEntriesByType("navigation").length > 1');
    const after = await page.evaluate(() => navigator.serviceWorker.controller?.scriptURL);

    assert.notEqual(initial, after);
    await browser.close();
  } catch (err) {
    if (err instanceof Error && err.message.includes('browser')) {
      test.skip('Playwright browser not installed');
    } else {
      throw err;
    }
  } finally {
    if (browser) await browser.close();
    server.close();
  await fs.writeFile(swPath, original);
  }
  });
