// SPDX-License-Identifier: Apache-2.0
// Loopback-only, fixed-action server. It has no wallet or arbitrary command API.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { randomBytes, randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const port = Number(process.env.TAE_PORT ?? 8765);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw Error('TAE_PORT must be an unprivileged local port');
const hosts = new Set([`127.0.0.1:${port}`, `localhost:${port}`]);
const origins = new Set([...hosts].map(host => `http://${host}`));
const token = randomBytes(24).toString('hex');
const staticFiles = new Map([
  ['/', ['study/interface/index.html', 'text/html; charset=utf-8']],
  ['/study/interface/', ['study/interface/index.html', 'text/html; charset=utf-8']],
  ...['index.html', 'style.css', 'app.js', 'evidence.js'].map(file => [`/study/interface/${file}`, [`study/interface/${file}`, file.endsWith('.css') ? 'text/css; charset=utf-8' : file.endsWith('.js') ? 'text/javascript; charset=utf-8' : 'text/html; charset=utf-8']]),
  ['/publication/Transformational_Autonomous_Enterprises.pdf', ['publication/Transformational_Autonomous_Enterprises.pdf', 'application/pdf']],
  ['/favicon.ico', [null, 'image/x-icon']]
]);
let active = null;
const json = (res, status, body) => { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(body)); };
function stop() { if (!active) return false; active.stopped = true; try { if (process.platform === 'win32') active.child.kill('SIGTERM'); else process.kill(-active.child.pid, 'SIGTERM'); } catch {} return true; }
async function body(req) { let bytes = 0, text = ''; for await (const chunk of req) { bytes += chunk.length; if (bytes > 1024) throw Error('Request body exceeds local API bound'); text += chunk; } if (text && text.trim() !== '{}') throw Error('This demonstration accepts only the fixed built-in missions'); }
const server = http.createServer(async (req, res) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'");
  if (!hosts.has(req.headers.host)) return json(res, 403, { error: 'Only the declared loopback host is allowed' });
  let pathname; try { pathname = new URL(req.url, `http://127.0.0.1:${port}`).pathname; } catch { return json(res, 400, { error: 'Invalid local path' }); }
  if (req.method === 'GET' && pathname === '/api/status') return json(res, 200, { local: true, busy: !!active, token, scope: 'Fixed local source composition and disposable in-process EVM only', stopSupported: process.platform !== 'win32' });
  if (req.method === 'POST' && ['/api/run', '/api/stop'].includes(pathname)) {
    if (req.headers['x-tae-token'] !== token || (req.headers.origin && !origins.has(req.headers.origin)) || !String(req.headers['content-type']).startsWith('application/json')) return json(res, 403, { error: 'Local same-origin action token required' });
    try { await body(req); } catch (error) { return json(res, 400, { error: error.message }); }
    if (pathname === '/api/stop') return json(res, 200, { stopped: stop(), scope: 'Active local process group only; previous evidence retained' });
    if (active) return json(res, 409, { error: 'One local journey is already running; wait or stop it' });
    const output = path.join(root, 'study/runs', `run-${new Date().toISOString().replace(/[:.]/g, '-')}-${randomUUID().slice(0, 8)}`);
    const child = spawn(process.execPath, [path.join(root, 'study/run-demo.mjs'), output], { cwd: root, detached: process.platform !== 'win32', stdio: ['ignore', 'pipe', 'pipe'], env: { PATH: process.env.PATH, LANG: 'C.UTF-8' } });
    const state = active = { child, output, stopped: false, log: '' };
    const append = bytes => { if (state.log.length < 2 * 1024 * 1024) state.log += bytes.toString('utf8'); };
    child.stdout.on('data', append); child.stderr.on('data', append);
    const timeout = setTimeout(() => { if (active === state) stop(); }, 60000);
    const finish = (code, error) => {
      clearTimeout(timeout); if (active === state) active = null;
      if (fs.existsSync(output)) {
        fs.writeFileSync(path.join(output, 'server-console.txt'), state.log);
        if (state.stopped) fs.writeFileSync(path.join(output, 'interrupted.json'), JSON.stringify({ stopped: true, completedArtifactsRetained: true, retry: 'Start a new run; current proof and local authority begin empty', at: new Date().toISOString() }, null, 2));
      }
      if (res.writableEnded) return;
      if (code === 0 && !state.stopped) { try { return json(res, 200, JSON.parse(fs.readFileSync(path.join(output, 'evidence.json')))); } catch (e) { error = e; } }
      json(res, state.stopped ? 409 : 500, { error: state.stopped ? 'Local journey stopped. Completed evidence was retained. Start a fresh run to recover.' : error?.message ?? 'Local journey failed. Inspect its retained failure record.', runId: path.basename(output) });
    };
    child.once('error', error => finish(null, error)); child.once('close', code => finish(code));
    return;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') return json(res, 405, { error: 'Method not supported' });
  if (pathname === '/') { res.writeHead(302, { Location: '/study/interface/' }); return res.end(); }
  const item = staticFiles.get(pathname);
  if (!item) return json(res, 404, { error: 'No such demonstration resource' });
  if (!item[0]) { res.writeHead(204); return res.end(); }
  const filename = path.join(root, item[0]);
  if (!fs.existsSync(filename)) return json(res, 404, { error: 'Resource is not included in this copy' });
  res.writeHead(200, { 'Content-Type': item[1], 'Cache-Control': 'no-cache', 'Content-Length': fs.statSync(filename).size });
  if (req.method === 'HEAD') return res.end();
  fs.createReadStream(filename).pipe(res);
});
server.listen(port, '127.0.0.1', () => console.log(`SUCCESSOR Ω local demonstration: http://127.0.0.1:${port}/study/interface/\nOne fixed run at a time; maximum 60 seconds. Ctrl+C stops the server and its active run.`));
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { stop(); server.close(); setTimeout(() => process.exit(0), 100).unref(); });
