// SPDX-License-Identifier: Apache-2.0
// Local-file visual/interaction qualification; no browser account or live service.
const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const {chromium} = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL, fileURLToPath} = require('node:url');

let activeBrowser;
(async () => {
  const root = __dirname;
  const evidencePath = path.join(root, 'evidence');
  await fs.mkdir(evidencePath, {recursive: true});
  const executablePath = process.argv[2];
  assert.ok(executablePath, 'Supply the already acquired public browser executable path');
  const browser = await chromium.launch({headless: true, executablePath});
  activeBrowser = browser;
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
  const errors = [], remoteRequests = [];
  page.on('pageerror', error => errors.push(String(error)));
  page.on('request', request => {
    if (/^https?:/.test(request.url())) remoteRequests.push(request.url());
  });
  const url = pathToFileURL(path.join(root, 'index.html')).href;
  await page.goto(url);
  const data = await page.locator('#evidence').textContent().then(JSON.parse);
  assert.equal(await page.locator('main section.section').count(), 3);
  const titles = [], localTargets = new Set();
  for (const language of ['en', 'fr']) {
    await page.getByRole('button', {name: language.toUpperCase(), exact: true}).click();
    assert.equal(await page.locator('html').getAttribute('lang'), language);
    const title = await page.locator('h1').innerText();
    assert.ok(title.includes(language === 'en' ? 'Useful work.' : 'Du travail utile.'));
    titles.push({language, title});
    const count = (data.jobs || []).length;
    assert.equal(await page.getByRole('tab').count(), count);
    for (let index = 0; index < count; index++) {
      await page.getByRole('tab').nth(index).click();
      assert.equal(await page.getByRole('tab').nth(index).getAttribute('aria-selected'), 'true');
      for (const href of await page.locator('a[href]').evaluateAll(anchors => anchors.map(anchor => anchor.getAttribute('href')))) if (/^\.\.?\//.test(href)) localTargets.add(href);
      const expected = data.jobs[index].title;
      assert.equal(await page.locator('#jobContent h3').innerText(), typeof expected === 'object' ? expected[language] || expected.en : expected);
    }
    if (count) await page.getByRole('tab').nth(0).click();
    for (const metric of ['wallSeconds', 'cpuSeconds', 'fullCostUsd']) await page.locator('#metric').selectOption(metric);
    await page.locator('#metric').selectOption('cpuSeconds');
    const scenarios = data.cash?.scenarios || [];
    for (let index = 0; index < scenarios.length; index++) {
      await page.locator('#scenario').selectOption(String(index));
      assert.ok((await page.locator('#cashContent').innerText()).length > 50);
      assert.equal(await page.locator('#cashContent tbody tr').count(), scenarios[index].ledger.length);
      assert.equal(await page.locator('#cashContent svg polyline').count(), 2);
    }
    if (scenarios.length) await page.locator('#scenario').selectOption('0');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path: path.join(evidencePath, `desktop-${language}.png`), fullPage: true});
  }
  await page.setViewportSize({width: 390, height: 844});
  await page.waitForFunction(() => document.querySelector('#cashContent svg').viewBox.baseVal.width <= document.getElementById('cashContent').clientWidth);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile horizontal overflow');
  const cashMetricOverflow = await page.locator('#cashContent .metric strong').evaluateAll(nodes => nodes.filter(node => node.scrollWidth > node.clientWidth + 1).map(node => node.textContent));
  assert.deepEqual(cashMetricOverflow, [], 'mobile cash numeral overflow');
  await page.locator('#cash').screenshot({path: path.join(evidencePath, 'cash-mobile-fr.png')});
  await page.screenshot({path: path.join(evidencePath, 'mobile-fr.png'), fullPage: true});
  const linkChecks = [];
  const targets = await page.locator('a[href]').evaluateAll(anchors => anchors.map(anchor => anchor.getAttribute('href')));
  for (const href of targets.filter(href => /^\.\.?\//.test(href))) localTargets.add(href);
  for (const href of localTargets) {
    const target = fileURLToPath(new URL(href, url));
    let exists = true;
    try { await fs.stat(target); } catch { exists = false; }
    linkChecks.push({href, exists});
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(remoteRequests, []);
  const result = {
    checkedAt: new Date().toISOString(), browserVersion: await browser.version(),
    renderedHtmlSha256: createHash('sha256').update(await fs.readFile(path.join(root, 'index.html'))).digest('hex'),
    dataStatus: data.evidenceStatus, errors, remoteRequests, titles,
    jobTabs: (data.jobs || []).length, scenarioOptions: (data.cash?.scenarios || []).length,
    desktopViewport: {width: 1440, height: 1000}, mobileViewport: {width: 390, height: 844},
    mobileScrollWidth: await page.evaluate(() => document.documentElement.scrollWidth), cashMetricOverflow,
    linkChecks, missingLocalLinks: linkChecks.filter(row => !row.exists),
    acceptance: 'Interactive render, bilingual titles/tabs, metric and scenario switches, no page errors, no automatic remote requests, no horizontal overflow',
  };
  await fs.writeFile(path.join(evidencePath, 'browser-check.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
  await browser.close();
})().catch(async error => {console.error(error); if (activeBrowser) await activeBrowser.close(); process.exitCode = 1;});
