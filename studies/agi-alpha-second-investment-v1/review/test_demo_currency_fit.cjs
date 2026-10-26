/* SPDX-License-Identifier: Apache-2.0 */
'use strict';
// Final narrow CSS regression check. Prior complete functional checks are reused
// only after proving all non-style HTML bytes and embedded scripts are identical.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES + '/playwright');
const root = path.resolve(__dirname, '..');
const current = path.join(root, 'publication/AGI_ALPHA_Second_Investment_Demo.html');
const previous = path.join(root, 'resources/demo/history/demo-before-currency-fit.html');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const html = fs.readFileSync(current, 'utf8'), priorHTML = fs.readFileSync(previous, 'utf8');
const withoutStyle = source => source.replace(/<style>[\s\S]*?<\/style>/, '<style>STYLE-ONLY-COMPARISON</style>');
let browser;
(async () => {
  assert.equal(hash(priorHTML), 'a7108b80af3a1b4b1bbe7f456ff6f6ae91c5e4a6c6756b6858a5c484caa87016');
  assert.equal(withoutStyle(html), withoutStyle(priorHTML), 'All HTML outside CSS must be identical');
  const previousStyles = priorHTML.match(/<style>([\s\S]*?)<\/style>/)[1];
  const currentStyles = html.match(/<style>([\s\S]*?)<\/style>/)[1];
  assert.equal(currentStyles.replace('#market .result-tile .value{font-size:1.1rem}', ''), previousStyles);
  const errors = [], network = [];
  const executable = '/tmp/agi-alpha-autonomous-work-20261026/browser_runtime/chrome-headless-shell-linux64/chrome-headless-shell';
  browser = await chromium.launch({headless: true, executablePath: executable});
  const version = browser.version();
  const page = await browser.newPage({viewport: {width: 360, height: 800}, deviceScaleFactor: 1});
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => errors.push(String(error)));
  await page.route('**/*', route => {
    if (route.request().url().startsWith('file:')) return route.continue();
    network.push(route.request().url()); return route.abort();
  });
  await page.goto(pathToFileURL(current).href);
  await page.locator('[data-lang="fr"]').click();
  const result = await page.locator('#market-mean').evaluate(element => {
    const node = element.firstChild;
    const characterBounds = [...node.textContent].map((text, index) => {
      const range = document.createRange(); range.setStart(node, index); range.setEnd(node, index + 1);
      const rect = range.getBoundingClientRect();
      return {text, top: rect.top, left: rect.left, right: rect.right};
    });
    return {text: element.textContent, characterBounds, fontSize: getComputedStyle(element).fontSize,
      viewport: innerWidth, documentWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth};
  });
  assert.equal(result.documentWidth, 360); assert.equal(result.bodyWidth, 360);
  assert.equal(new Set(result.characterBounds.map(rect => rect.top)).size, 1, 'Whole currency value fits on one line');
  assert.ok(result.text.includes('-107,56')); assert.ok(result.text.endsWith('US'));
  assert.ok(result.characterBounds.every(rect => rect.left >= 0 && rect.right <= 360));
  const screenshot = 'resources/demo-qa/screenshots/mobile-fr-market-final.png';
  await page.locator('#market').screenshot({path: path.join(root, screenshot)});
  assert.equal(errors.length, 0); assert.equal(network.length, 0);
  await browser.close(); browser = null;
  const report = {schema: 'agi-alpha-demo-currency-fit/v1', passed: true,
    htmlSHA256: hash(html), predecessorSHA256: hash(priorHTML),
    nonStyleHTMLSHA256: hash(withoutStyle(html)), allNonStyleHTMLIdentical: true,
    unchangedChecksReused: ['review/demo-functional-before-currency-fit.json', 'review/demo-browser-before-currency-fit.json'],
    onlyChange: 'Mobile market result metrics font-size1.1rem', browserVersion: version,
    result, screenshot: {path: screenshot, sha256: hash(fs.readFileSync(path.join(root, screenshot)))},
    pageErrors: errors, externalRequests: network, newResearchCampaigns: 0};
  fs.writeFileSync(path.join(root, 'review/demo-currency-fit-results.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
})().catch(async error => {
  if (browser) await browser.close();
  const report = {passed: false, htmlSHA256: hash(html), failure: error.stack};
  fs.writeFileSync(path.join(root, 'review/demo-currency-fit-results.json'), JSON.stringify(report, null, 2) + '\n');
  console.error(JSON.stringify(report)); process.exitCode = 1;
});
