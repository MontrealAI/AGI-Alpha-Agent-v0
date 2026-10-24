// SPDX-License-Identifier: Apache-2.0
// Optional browser QA: Playwright 1.62.1, new Writer4 HTTP interface only.
const { chromium } = require('../browser-tools/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const output = path.resolve(process.env.TAE_QA_OUTPUT ?? 'evidence/interface');
fs.mkdirSync(output, { recursive: true });
const report = { target: 'http://127.0.0.1:8765/study/interface/', priorDeniedTargetsAttempted: false, browser: 'Playwright Chromium', checks: [], errors: [], startedAt: new Date().toISOString() };
const apiUrl = name => 'http://127.0.0.1:8765/api/' + name;
const isRun = request => request.url() === apiUrl('run') && request.method() === 'POST';
const outcome = promise => promise.then(async response => ({ status: response.status(), body: await response.json() })).catch(error => ({ transportError: error.message }));
const runsRoot = path.resolve(__dirname, '../runs');
const runDirectories = () => fs.existsSync(runsRoot) ? fs.readdirSync(runsRoot, { withFileTypes: true }).filter(entry => entry.isDirectory() && /^run-[A-Za-z0-9-]+$/.test(entry.name)).map(entry => entry.name) : [];
async function waitForOwnRunDirectory(before) {
  // Same 60-second bound as the fixed server action, not a new mission budget.
  const deadline = Date.now() + 60000;
  while (runDirectories().filter(name => !before.includes(name)).length === 0) {
    assert.ok(Date.now() < deadline, 'The launched attempt must create its own retained run directory');
    await new Promise(resolve => setTimeout(resolve, 50));
  }
}
function observeRun(page) {
  let request = null, settled = false, finish;
  const promise = new Promise(resolve => { finish = resolve; });
  const settle = value => { if (!settled) { settled = true; finish(value); } };
  const sent = value => { if (!request && isRun(value)) request = value; };
  const received = response => { if (response.request() === request) outcome(Promise.resolve(response)).then(settle); };
  const failed = value => { if (value === request) settle({ requestFailure: value.failure()?.errorText ?? 'Run request failed' }); };
  // All three listeners exist before the click: a quick response or Stop-abort
  // is a retained outcome, never a missing response-only waiter.
  page.on('request', sent); page.on('response', received); page.on('requestfailed', failed);
  return { promise, started: () => request !== null, dispose: () => { page.off('request', sent); page.off('response', received); page.off('requestfailed', failed); } };
}
function retainAttempt(schedule, result, before, startedAt) {
  const created = runDirectories().filter(name => !before.includes(name));
  const reported = result.body?.runId;
  const runId = typeof reported === 'string' && /^run-[A-Za-z0-9-]+$/.test(reported) ? reported : created.length === 1 ? created[0] : null;
  const record = { schedule, responseStatus: result.status ?? null, responseError: result.body?.error ?? result.transportError ?? result.requestFailure ?? null, runId, runIdEvidence: runId === reported ? 'server-response' : runId ? 'single-owned-run-directory-delta' : 'unavailable', createdRunDirectories: created, elapsedBrowserMs: Date.now() - startedAt, fullyAttributableCostUSD: null, executedLocalTransactions: null, retained: {} };
  if (typeof runId === 'string' && /^run-[A-Za-z0-9-]+$/.test(runId)) {
    const directory = path.join(runsRoot, runId);
    record.runDirectoryExists = fs.existsSync(directory);
    for (const name of ['interrupted.json', 'progress.json', 'failure.json', 'evm-failure.json']) {
      const filename = path.join(directory, name);
      if (fs.existsSync(filename)) record.retained[name] = JSON.parse(fs.readFileSync(filename));
    }
    const consoleFile = path.join(directory, 'server-console.txt');
    if (fs.existsSync(consoleFile)) { const raw = fs.readFileSync(consoleFile); record.consoleIdentity = { bytes: raw.length, sha256: createHash('sha256').update(raw).digest('hex') }; }
  }
  return record;
}
function assertStoppedAttempt(attempt) {
  assert.equal(attempt.createdRunDirectories.length, 1);
  assert.equal(attempt.runId, attempt.createdRunDirectories[0], 'Response/delta identity must name the sole newly created owned directory');
  assert.equal(attempt.runDirectoryExists, true);
  assert.equal(attempt.retained['interrupted.json']?.stopped, true, 'Observed idle must retain the server-owned stopped record');
}
async function stopForCleanup(context, page) {
  const state = await (await context.request.get(apiUrl('status'))).json();
  if (state.busy) await context.request.post(apiUrl('stop'), { headers: { 'Content-Type': 'application/json', 'X-TAE-Token': state.token }, data: '{}' });
  await page.waitForFunction(async () => !(await (await fetch('/api/status')).json()).busy);
}
async function main() {
  const packaged = (await import('../browser-tools/node_modules/@sparticuz/chromium/build/index.js')).default;
  const executablePath = await packaged.executablePath();
  report.executableSource = '@sparticuz/chromium@153.0.0 pinned npm package';
  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    page.on('pageerror', error => report.errors.push(error.message));
    await page.goto(report.target); await page.waitForFunction(() => !document.querySelector('#run').disabled);
    assert.equal(await page.locator('#accepted-count').innerText(), '40 / 40');
    assert.match(await page.locator('#evidence-mode').innerText(), /record|replay|histor/i);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(output, 'desktop-en.png'), fullPage: true });
    report.checks.push({ name: 'Recorded evidence, 40/40 score and desktop layout', passed: true });
    await page.locator('[data-step="0"]').focus(); await page.keyboard.press('End');
    assert.equal(await page.locator('[data-step="5"]').getAttribute('aria-selected'), 'true');
    await page.keyboard.press('Home'); assert.equal(await page.locator('[data-step="0"]').getAttribute('aria-selected'), 'true');
    report.checks.push({ name: 'Keyboard stage navigation and visible focus', passed: true });
    const api = await page.evaluate(async () => {
      const status = await (await fetch('/api/status')).json();
      const denied = await fetch('/api/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const changed = await fetch('/api/run', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-TAE-Token': status.token }, body: '{"mission":"arbitrary"}' });
      const hidden = await fetch('/study/evaluation/checker.mjs');
      return { denied: denied.status, changed: changed.status, hidden: hidden.status };
    });
    assert.deepEqual(api, { denied: 403, changed: 400, hidden: 404 });
    report.checks.push({ name: 'Unauthorized API, arbitrary input and unlisted path refused', passed: true, observed: api });
    const ownedBefore = runDirectories(), ownedStarted = Date.now(), owned = observeRun(page);
    let ownedPassed = false;
    try {
      await page.locator('#run').click();
      await page.waitForFunction(() => !document.querySelector('#stop-run').disabled);
      await page.waitForFunction(async () => (await (await fetch('/api/status')).json()).busy);
      await waitForOwnRunDirectory(ownedBefore);
      const busyStatus = await page.evaluate(async () => { const { token } = await (await fetch('/api/status')).json(); return (await fetch('/api/run', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-TAE-Token': token }, body: '{}' })).status; });
      assert.equal(busyStatus, 409);
      await page.locator('#stop-run').click(); await page.waitForFunction(() => !document.querySelector('#run').disabled);
      await page.waitForFunction(async () => !(await (await fetch('/api/status')).json()).busy);
      const result = await owned.promise;
      assert.ok(result.requestFailure || result.status === 409);
      const attempt = retainAttempt('original-page-owned-stop', result, ownedBefore, ownedStarted);
      assertStoppedAttempt(attempt);
      ownedPassed = true;
    } finally {
      await stopForCleanup(context, page);
      const result = owned.started() ? await owned.promise : { transportError: 'Page never launched' };
      owned.dispose();
      report.checks.push({ name: 'Concurrent run refused; active local process group stopped; previous evidence retained', passed: ownedPassed, observed: retainAttempt('original-page-owned-stop', result, ownedBefore, ownedStarted) });
    }
    // Two real loopback schedules cover rejected/lost Run responses. Routing is
    // client-side only; the production app/server, token, origin and actions are unchanged.
    const other = await context.newPage();
    other.on('pageerror', error => report.errors.push(error.message));
    await other.goto(report.target); await other.waitForFunction(() => !document.querySelector('#run').disabled);
    const otherBefore = runDirectories(), otherStarted = Date.now(), otherObserved = observeRun(other), rejected = observeRun(page);
    let racePassed = false;
    const otherWins = async route => {
      try {
        await other.locator('#run').click();
        await page.waitForFunction(async () => (await (await fetch('/api/status')).json()).busy);
        await waitForOwnRunDirectory(otherBefore);
        await route.continue();
      } catch (error) { report.errors.push(error.message); await route.abort('failed').catch(() => {}); }
    };
    await page.route(apiUrl('run'), otherWins);
    try {
      await page.locator('#run').click(); const refused = await rejected.promise;
      assert.equal(refused.status, 409);
      await page.waitForFunction(() => document.querySelector('#connection').dataset.state === 'error');
      assert.equal(await page.locator('#run').isDisabled(), true);
      assert.equal(await page.locator('#restore').isDisabled(), true);
      assert.equal(await page.locator('#stop-run').isDisabled(), false);
      assert.equal((await (await context.request.get(apiUrl('status'))).json()).busy, true);
      await page.locator('#stop-run').click();
      await page.waitForFunction(() => !document.querySelector('#run').disabled);
      await page.waitForFunction(async () => !(await (await fetch('/api/status')).json()).busy);
      const result = await otherObserved.promise; assert.equal(result.status, 409);
      const attempt = retainAttempt('other-tab-wins-409', result, otherBefore, otherStarted);
      assertStoppedAttempt(attempt);
      racePassed = true;
    } finally {
      await page.unroute(apiUrl('run'), otherWins);
      await stopForCleanup(context, page);
      const result = otherObserved.started() ? await otherObserved.promise : { transportError: 'Second page never launched' };
      otherObserved.dispose(); rejected.dispose();
      report.checks.push({ name: 'Another tab wins after idle: rejected Run keeps guards and Stop until verified idle', passed: racePassed, observed: retainAttempt('other-tab-wins-409', result, otherBefore, otherStarted) });
      await other.close();
    }
    const lostBefore = runDirectories(), lostStarted = Date.now(), lostObserved = observeRun(page);
    let forwarded, lossPassed = false;
    const loseResponse = async route => {
      try {
        const request = route.request(); assert.equal(request.url(), apiUrl('run'));
        forwarded = outcome(context.request.post(request.url(), { headers: request.headers(), data: request.postData(), timeout: 60000 }));
        await page.waitForFunction(async () => (await (await fetch('/api/status')).json()).busy);
        await waitForOwnRunDirectory(lostBefore);
        await route.abort('failed');
      } catch (error) { report.errors.push(error.message); await route.abort('failed').catch(() => {}); }
    };
    await page.route(apiUrl('run'), loseResponse);
    try {
      await page.locator('#run').click(); const lost = await lostObserved.promise;
      assert.ok(lost.requestFailure, 'The page must lose its real launched request response');
      await page.waitForFunction(() => document.querySelector('#connection').dataset.state === 'error');
      assert.equal(await page.locator('#run').isDisabled(), true);
      assert.equal(await page.locator('#restore').isDisabled(), true);
      assert.equal(await page.locator('#stop-run').isDisabled(), false);
      assert.equal((await (await context.request.get(apiUrl('status'))).json()).busy, true);
      await page.locator('#stop-run').click();
      await page.waitForFunction(() => !document.querySelector('#run').disabled);
      await page.waitForFunction(async () => !(await (await fetch('/api/status')).json()).busy);
      const result = await forwarded; assert.equal(result.status, 409);
      const attempt = retainAttempt('response-lost-after-launch', result, lostBefore, lostStarted);
      assertStoppedAttempt(attempt);
      lossPassed = true;
    } finally {
      await page.unroute(apiUrl('run'), loseResponse);
      await stopForCleanup(context, page);
      const result = forwarded ? await forwarded : { transportError: 'Forwarded request never launched' };
      lostObserved.dispose();
      report.checks.push({ name: 'Lost response after real launch keeps Run/restore guarded and Stop usable until idle', passed: lossPassed, observed: retainAttempt('response-lost-after-launch', result, lostBefore, lostStarted) });
    }
    const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/run') && response.status() === 200, { timeout: 60000 });
    const begin = Date.now(); await page.locator('#run').click();
    const response = await responsePromise; const fresh = await response.json();
    assert.equal(fresh.acceptance.accepted, true); assert.equal(fresh.evm.lifecycleTransactions, 32);
    assert.equal(fresh.evm.missions[1].parentSeedId, fresh.evm.missions[0].seedId);
    await page.waitForFunction(() => !document.querySelector('#run').disabled);
    assert.match(await page.locator('#comparison-note').count() ? await page.locator('#comparison-note').innerText() : await page.locator('#evidence').innerText(), /record|replay|frozen/i);
    fs.writeFileSync(path.join(output, 'fresh-run-reference.json'), JSON.stringify({ runId: fresh.runId, elapsedBrowserMs: Date.now() - begin, acceptance: fresh.acceptance, costs: fresh.costs }, null, 2));
    report.checks.push({ name: 'Recovery runs both actual missions through four repositories and32 local settlement transactions', passed: true, runId: fresh.runId, elapsedBrowserMs: Date.now() - begin });
    const downloadPromise = page.waitForEvent('download'); await page.locator('#export').click();
    const download = await downloadPromise; const filename = path.join(output, 'browser-export.json'); await download.saveAs(filename);
    const exported = JSON.parse(fs.readFileSync(filename)); assert.equal(exported.currentProof, null); assert.deepEqual(exported.authority, []); assert(exported.evidence.workspaces.successor.capability.programs);
    await page.locator('#restore').setInputFiles(filename); await page.waitForFunction(() => document.querySelector('#restore-status').textContent.includes('Restored as historical'));
    report.checks.push({ name: 'Export retains executable capability; restore marks historical unverified evidence and empty authority', passed: true });
    const before = await page.locator('#accepted-count').innerText();
    await page.locator('#restore').setInputFiles({ name: 'invalid.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({ schema: 'tae.interface-export.v1', currentProof: { accepted: true }, authority: ['mainnet'], evidence: {} })) });
    await page.waitForFunction(() => /refused|failed|error|unsupported/i.test(document.querySelector('#restore-status').textContent));
    assert.equal(await page.locator('#accepted-count').innerText(), before);
    report.checks.push({ name: 'Imported permission/invalid record refused without losing existing evidence', passed: true });
    await page.locator('#language').click(); assert.equal(await page.locator('html').getAttribute('lang'), 'fr');
    await page.screenshot({ path: path.join(output, 'desktop-fr.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 }); await page.evaluate(() => scrollTo(0, 0));
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(output, 'mobile-fr.png'), fullPage: true });
    await page.locator('#language').click(); await page.screenshot({ path: path.join(output, 'mobile-en.png'), fullPage: true });
    await page.setViewportSize({ width: 320, height: 720 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(output, 'mobile-320.png'), fullPage: true });
    report.checks.push({ name: 'English/French layouts at1440,390 and320px with no horizontal document overflow', passed: true });
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto');
    report.checks.push({ name: 'Reduced-motion setting respected', passed: true });
    const pdf = await context.request.get('http://127.0.0.1:8765/publication/Transformational_Autonomous_Enterprises.pdf'); assert.equal(pdf.status(), 200); assert.equal((await pdf.body()).subarray(0, 5).toString(), '%PDF-');
    report.checks.push({ name: 'Paper link serves a real PDF', passed: true });
    assert.deepEqual(report.errors, []);
    report.lineageText = await page.locator('#lineage-identities').innerText();
    assert.match(report.lineageText, /e55b1394508e/); assert.match(report.lineageText, /cfff8e0c431a/);
    report.checks.push({name:'Actual capability, module and local job identities displayed',passed:true});
  } finally { await browser.close(); }
}
main().then(() => { report.passed = true; report.finishedAt = new Date().toISOString(); fs.writeFileSync(path.join(output, 'browser-qa.json'), JSON.stringify(report, null, 2)); console.log(JSON.stringify(report)); }).catch(error => { report.passed = false; report.failure = error.stack; fs.writeFileSync(path.join(output, 'browser-qa-failed.json'), JSON.stringify(report, null, 2)); console.error(error); process.exitCode = 1; });
