// SPDX-License-Identifier: Apache-2.0
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {chromium} = require('playwright');
const study = path.resolve(__dirname, '../..');
const paper = path.join(study, 'paper', 'Browser_Edition.html');
const screenshotDir = path.resolve(study, '../../../browser_qa/reader');
let browser;
(async () => {
  fs.mkdirSync(screenshotDir, {recursive: true});
  const htmlHash = crypto.createHash('sha256').update(fs.readFileSync(paper)).digest('hex');
  const buildReceipt = JSON.parse(fs.readFileSync(path.join(study, 'paper/reader_build_receipt.json')));
  browser = await chromium.launch({headless: true,
    executablePath: '/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome', args: ['--no-sandbox']});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
  const errors = [], requests = [], checks = [], screenshots = [];
  const check = (name, condition, details = null) => { checks.push({name, passed: Boolean(condition), details}); };
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => requests.push(r.url()));
  await page.goto('file://' + paper, {waitUntil: 'load'});
  check('reader-receipt-matches-html', htmlHash === buildReceipt.files['Browser_Edition.html'].sha256);
  const structure = await page.evaluate(() => {
    const visible = el => getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().height > 0;
    const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(visible).map(el => ({level: el.tagName, text: el.textContent.trim(), id: el.id}));
    const math = [...document.querySelectorAll('math')].map(el => ({display: el.getAttribute('display'), width: el.getBoundingClientRect().width, height: el.getBoundingClientRect().height}));
    const rawMath = [...document.querySelectorAll('.math')].filter(el => /\\[a-z]+|\$\$/.test(el.textContent)).map(el => el.textContent.trim());
    const figures = [...document.querySelectorAll('figure')].map(el => ({caption: el.querySelector('figcaption')?.textContent, images: [...el.querySelectorAll('img')].map(im => ({loaded: im.complete && im.naturalWidth > 0, alt: im.getAttribute('alt'), width: im.naturalWidth, height: im.naturalHeight}))}));
    const brokenAnchors = [...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href').slice(1)).filter(id => id && !document.getElementById(decodeURIComponent(id)));
    const localLinks = [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(x => !/^(#|https?:|mailto:|data:)/.test(x));
    return {headings, math, rawMath, figures, brokenAnchors, localLinks};
  });
  check('single-visible-main-title', structure.headings.filter(h => h.level === 'H1').length === 1);
  check('headings-present', structure.headings.length > 30, {count: structure.headings.length});
  check('no-unconverted-math', structure.rawMath.length === 0, structure.rawMath);
  check('native-math-has-layout', structure.math.length > 40 && structure.math.every(m => m.width > 0 && m.height > 0), {count: structure.math.length});
  check('all-seven-figures-loaded', structure.figures.length === 7 && structure.figures.every(f => f.images.every(i => i.loaded)));
  check('all-figures-captioned', structure.figures.every(f => f.caption?.trim()));
  check('all-figures-have-alt-text', structure.figures.every(f => f.images.every(i => i.alt?.trim())));
  check('all-internal-anchors-resolve', structure.brokenAnchors.length === 0, structure.brokenAnchors);
  const missingLocal = structure.localLinks.filter(x => !fs.existsSync(path.resolve(path.dirname(paper), x.split('#')[0])));
  check('all-reader-relative-links-resolve', missingLocal.length === 0, missingLocal);
  const overflow = {};
  async function shot(name) { const target = path.join(screenshotDir, name); await page.screenshot({path: target}); screenshots.push(target); }
  for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile390', 390, 844], ['mobile320', 320, 740]]) {
    await page.setViewportSize({width, height});
    await page.evaluate(() => scrollTo(0, 0));
    await shot(name + '-top.png');
    overflow[name] = await page.evaluate(() => {
      const viewport = innerWidth;
      const candidates = [...document.querySelectorAll('body *')].filter(e => {
        const r = e.getBoundingClientRect();
        return r.width > 0 && r.right > viewport + 1 && !e.closest('table,pre,math');
      }).slice(0, 15).map(e => ({tag: e.tagName, id: e.id, class: String(e.className), width: e.getBoundingClientRect().width, text: e.textContent.slice(0, 120)}));
      const wideMath = [...document.querySelectorAll('math')].map(e => ({width: e.getBoundingClientRect().width, right: e.getBoundingClientRect().right, display: e.getAttribute('display'), cssDisplay: getComputedStyle(e).display, overflow: getComputedStyle(e).overflowX, tex: e.querySelector('annotation')?.textContent})).filter(e => e.right > viewport + 1);
      return {viewport, scrollWidth: document.documentElement.scrollWidth, candidates, wideMath};
    });
    check(name + '-no-document-overflow', overflow[name].scrollWidth <= width, overflow[name]);
    await page.locator('figure').first().scrollIntoViewIfNeeded();
    await shot(name + '-scientific-figure.png');
    const raw = page.locator('.math').first();
    if (await raw.count()) await raw.scrollIntoViewIfNeeded();
    else await page.locator('math[display="block"]').first().scrollIntoViewIfNeeded();
    await shot(name + '-equation.png');
    await page.locator('table').last().scrollIntoViewIfNeeded();
    await shot(name + '-last-table.png');
  }
  check('no-reader-script-errors', errors.length === 0, errors);
  check('reader-self-contained-no-network', requests.every(url => url.startsWith('file:') || url.startsWith('data:')), requests);
  const report = {schema: 'opportunity-reader-browser-qa/v1', edition: '2.1.0', html_sha256: htmlHash,
    reader_build_receipt_sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(study, 'paper/reader_build_receipt.json'))).digest('hex'),
    passed: checks.filter(c => c.passed).length, total: checks.length, checks, structure, overflow, screenshots,
    environment: {node: process.version, chromium: await browser.version()},
    scope: 'Actual local full-reader rendering at desktop and 390/320 px. No external link fetching, scientific re-evaluation or public publication.'};
  const out = path.join(__dirname, 'reader_validation.json');
  if (fs.existsSync(out)) {
    const old = JSON.parse(fs.readFileSync(out));
    fs.mkdirSync(path.join(__dirname, 'history'), {recursive: true});
    fs.copyFileSync(out, path.join(__dirname, 'history', old.html_sha256.slice(0, 12) + '.json'));
  }
  fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
  await browser.close();
  console.log(JSON.stringify({passed: report.passed, total: report.total, hash: htmlHash, findings: checks.filter(c => !c.passed), screenshots: screenshotDir}));
})().catch(async error => {console.error(error.stack); if (browser) await browser.close(); process.exitCode = 1;});
