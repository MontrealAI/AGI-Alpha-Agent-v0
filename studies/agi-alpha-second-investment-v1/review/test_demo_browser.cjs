/* SPDX-License-Identifier: Apache-2.0 */
'use strict';
// Reuse an existing local browser. No download, app runtime or research campaign.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES + '/playwright');
const root = path.resolve(__dirname, '..');
const executable = '/tmp/agi-alpha-autonomous-work-20261026/browser_runtime/chrome-headless-shell-linux64/chrome-headless-shell';
const html = path.join(root, 'publication/AGI_ALPHA_Second_Investment_Demo.html');
const output = path.join(root, 'resources/demo-qa/screenshots');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const checks = [], errors = [], network = [];
let browser;
async function check(name, operation) {
  const details = await operation(); checks.push({name, passed: true, details: details ?? null});
}
(async () => {
  fs.mkdirSync(output, {recursive: true});
  browser = await chromium.launch({headless: true, executablePath: executable});
  const browserVersion = browser.version();
  const context = await browser.newContext({viewport: {width: 1360, height: 1000}, deviceScaleFactor: 1});
  await context.route('**/*', route => {
    const url = route.request().url();
    if (url.startsWith('file:') || url.startsWith('data:') || url.startsWith('blob:')) return route.continue();
    network.push(url); return route.abort();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto(pathToFileURL(html).href);
  await check('Desktop English default binds to unfinanced reference and zero second uses', async () => {
    assert.equal(await page.locator('#ledger-cost').inputValue(), 'reference');
    assert.equal(await page.locator('#ledger-uses').textContent(), '0');
    assert.match(await page.locator('#ledger-status').textContent(), /Not financed/);
    await page.screenshot({path: path.join(output, 'desktop-en.png'), fullPage: true});
  });
  await check('Actual browser low-cost selection and French toggle preserve correct loss and 15 uses', async () => {
    await page.selectOption('#ledger-cost', 'low');
    assert.equal(await page.locator('#ledger-uses').textContent(), '15');
    assert.equal(await page.locator('#ledger-delta').textContent(), '-$27.47');
    await page.locator('[data-lang="fr"]').click();
    assert.equal(await page.locator('html').getAttribute('lang'), 'fr');
    assert.match(await page.locator('#ledger-status').textContent(), /remboursement non atteint/);
    assert.match(await page.locator('#ledger-delta').textContent(), /27,47/);
    await page.screenshot({path: path.join(output, 'desktop-fr.png'), fullPage: true});
  });
  await check('Native browser unknown cost controls prevent unavailable scenario selection', async () => {
    await page.selectOption('#market-condition', 'price-1600c');
    await page.selectOption('#market-cost', 'actual-unknown');
    assert.equal(await page.locator('#market-condition').inputValue(), 'reference');
    assert.equal(await page.locator('#market-mean').textContent(), 'Inconnu');
    assert.equal(await page.locator('#market-condition option:not([disabled])').count(), 1);
    assert.equal(await page.locator('#market-gates').textContent(), '0 / 24');
    await page.selectOption('#market-cost', 'reference');
    assert.equal(await page.locator('#market-condition option:not([disabled])').count(), 13);
  });
  await check('Native number-input clearing is rejected and exploratory positive result remains caveated', async () => {
    await page.locator('#calc-cost').fill('');
    assert.equal(await page.locator('#calc-net').textContent(), 'Vérifier les entrées');
    await page.locator('#calc-cost').fill('1'); await page.locator('#calc-upkeep').fill('0');
    await page.locator('#calc-minutes').evaluate(element => {
      element.value = '2'; element.dispatchEvent(new Event('input', {bubbles: true}));
    });
    assert.match(await page.locator('#calc-net').textContent(), /31,69/);
    assert.match(await page.locator('#calc-interpretation').textContent(), /ne valide ni les économies/);
    await page.locator('#calc-reset').click();
    assert.equal(await page.locator('#calc-minutes').inputValue(), '0');
  });
  await check('Native browser embedded download is byte-identical and inspector renders text', async () => {
    const artifact = 'publication/publication-data.json';
    await page.locator('details').filter({has: page.locator('#artifact-select')}).locator('summary').first().click();
    await page.selectOption('#artifact-select', artifact);
    const downloaded = page.waitForEvent('download');
    await page.locator('#download-selected').click();
    const download = await downloaded;
    const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'agialpha-demo-download-'));
    const destination = path.join(temporary, 'download.json');
    await download.saveAs(destination);
    const actualHash = hash(destination); assert.equal(actualHash, hash(path.join(root, artifact)));
    fs.rmSync(temporary, {recursive: true});
    await page.locator('#inspect-selected').click();
    assert.equal(await page.locator('#inspector').isVisible(), true);
    assert.match(await page.locator('#inspector-content').textContent(), /agi-alpha-second-investment-publication-data/);
    await page.evaluate(() => { document.getElementById('inspector').hidden = true; });
    const pdfEvent = page.waitForEvent('download');
    await page.locator('[data-file-download="publication/paper.pdf"]').first().click();
    const pdf = await pdfEvent;
    const pdfTemporary = fs.mkdtempSync(path.join(os.tmpdir(), 'agialpha-demo-pdf-'));
    const pdfDestination = path.join(pdfTemporary, 'paper.pdf');
    await pdf.saveAs(pdfDestination);
    const pdfHash = hash(pdfDestination);
    assert.equal(pdfHash, hash(path.join(root, 'publication/paper.pdf')));
    assert.equal(pdf.suggestedFilename(), 'AGI_ALPHA_Second_Investment_Paper.pdf');
    fs.rmSync(pdfTemporary, {recursive: true});
    return {artifact, sha256: actualHash, suggestedFilename: download.suggestedFilename(),
      embeddedPDFSHA256: pdfHash, embeddedPDFFilename: pdf.suggestedFilename()};
  });
  await check('360px English and French layouts have no document overflow and retain reachable controls', async () => {
    await page.setViewportSize({width: 360, height: 800});
    const dimensions = [];
    for (const language of ['en', 'fr']) {
      await page.locator(`[data-lang="${language}"]`).click();
      await page.evaluate(() => scrollTo(0, 0));
      const size = await page.evaluate(() => ({viewport: innerWidth,
        document: document.documentElement.scrollWidth, body: document.body.scrollWidth,
        controls: [...document.querySelectorAll('input,select')].map(element => {
          const rect = element.getBoundingClientRect();
          return {id: element.id, left: rect.left, right: rect.right, width: rect.width};
        })}));
      if (size.document > size.viewport) {
        const offenders = await page.evaluate(() => [...document.querySelectorAll('body *')]
          .filter(element => element.getBoundingClientRect().right > innerWidth && !element.closest('.table-scroll'))
          .map(element => ({tag: element.tagName, id: element.id, class: element.className,
            right: element.getBoundingClientRect().right, text: element.textContent.slice(0, 160)})).slice(0, 30));
        fs.writeFileSync(path.join(root, 'resources/demo-qa/mobile-overflow.json'),
          JSON.stringify({language, htmlSHA256: hash(html), ...size, offenders}, null, 2) + '\n');
        await page.screenshot({path: path.join(output, `${language}-overflow.png`), fullPage: true});
      }
      assert.ok(size.document <= size.viewport, `${language} horizontal document overflow: ${size.document}px`);
      assert.ok(size.body <= size.viewport, `${language} horizontal body overflow`);
      assert.ok(size.controls.every(rect => rect.left >= 0 && rect.right <= size.viewport && rect.width > 30));
      await page.screenshot({path: path.join(output, `mobile-${language}.png`), fullPage: true});
      dimensions.push({language, ...size});
    }
    for (const section of ['ledger', 'market', 'calculator']) {
      await page.locator(`#${section}`).screenshot({path: path.join(output, `mobile-fr-${section}.png`)});
    }
    return dimensions;
  });
  await check('No-JavaScript page still presents reference result and six outputs', async () => {
    const nojsContext = await browser.newContext({javaScriptEnabled: false, viewport: {width: 360, height: 800}});
    const nojs = await nojsContext.newPage();
    await nojs.goto(pathToFileURL(html).href);
    assert.equal(await nojs.locator('noscript').isVisible(), true);
    assert.match(await nojs.locator('#ledger-status').textContent(), /cannot be financed/);
    assert.equal(await nojs.locator('#ledger-uses').textContent(), '0');
    assert.equal(await nojs.locator('.delivery-card').count(), 6);
    await nojs.screenshot({path: path.join(output, 'mobile-nojs.png'), fullPage: true});
    await nojsContext.close();
  });
  assert.equal(errors.length, 0, JSON.stringify(errors));
  assert.equal(network.length, 0, JSON.stringify(network));
  await browser.close(); browser = null;
  const report = {schema: 'agi-alpha-demo-browser-qa/v1', passed: true,
    html: path.relative(root, html), htmlSHA256: hash(html), browserExecutable: executable,
    browserVersion, reusedExistingExecutable: true, downloadedBrowser: false,
    appRuntimeRestarted: false, primaryCampaignsRun: 0, checks, pageErrors: errors, externalRequests: network,
    screenshots: fs.readdirSync(output).filter(name => name.endsWith('.png')).map(name => ({
      path: path.relative(root, path.join(output, name)), sha256: hash(path.join(output, name))})),
    limitations: ['Headless screenshots and DOM bounds are not manual screen-reader or cross-browser compatibility testing.',
      'Only the existing Chromium executable was exercised; unsupported browsers may use the exact-gzip download fallback.']};
  fs.writeFileSync(path.join(root, 'review/demo-browser-results.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({passed: true, browserVersion, checks: checks.map(c => c.name), screenshots: report.screenshots}));
})().catch(async error => {
  if (browser) await browser.close();
  const report = {passed: false, htmlSHA256: hash(html), checks, errors, network, failure: error.stack};
  fs.writeFileSync(path.join(root, 'review/demo-browser-results.json'), JSON.stringify(report, null, 2) + '\n');
  console.error(JSON.stringify(report)); process.exitCode = 1;
});
