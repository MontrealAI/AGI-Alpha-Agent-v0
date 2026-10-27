// SPDX-License-Identifier: Apache-2.0
'use strict';
const fs = require('fs');
const path = require('path');
const {chromium} = require('playwright');
const root = __dirname;
const qa = path.resolve(root, '../../../../browser_qa');
const checks = [];
const check = (name, condition, details = null) => {
  checks.push({name, passed: Boolean(condition), details});
  if (!condition) throw new Error(name + ': ' + JSON.stringify(details));
};

(async () => {
  fs.mkdirSync(qa, {recursive: true});
  const browser = await chromium.launch({headless: true,
    executablePath: '/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome',
    args: ['--no-sandbox']});
  const page = await browser.newPage({viewport: {width: 1440, height: 1050}});
  const errors = [];
  const requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push(request.url()));
  await page.goto('file://' + path.join(root, 'index.html'));
  check('initial-language-en', await page.getAttribute('html', 'lang') === 'en');
  check('all-primary-arms-render', await page.locator('#result-cards .metric').allTextContents().then(v => v.length === 3 && v.every(x => x === '4 / 4')));
  await page.screenshot({path: path.join(qa, 'desktop-top.png')});
  await page.locator('#results').scrollIntoViewIfNeeded();
  await page.screenshot({path: path.join(qa, 'desktop-results.png')});
  await page.getByRole('tab', {name: 'E', exact: true}).click();
  check('expert-tab', await page.getAttribute('#tab-E', 'aria-selected') === 'true');
  await page.locator('#tab-E').press('ArrowRight');
  check('tab-keyboard-navigation', await page.getAttribute('#tab-E_plus', 'aria-selected') === 'true');
  check('tab-keyboard-focus', await page.evaluate(() => document.activeElement.id) === 'tab-E_plus');
  await page.locator('#benefit').evaluate(el => {el.value = '2'; el.dispatchEvent(new Event('input', {bubbles: true}));});
  check('retention-calculator', await page.locator('#net-alpha').textContent() === '$12.40');
  await page.locator('#benefit').evaluate(el => {el.value = '0'; el.dispatchEvent(new Event('input', {bubbles: true}));});
  check('zero-benefit-cost-remains', await page.locator('#net-alpha').textContent() === '-$27.60');
  await page.locator('#price').evaluate(el => {el.value = '10'; el.dispatchEvent(new Event('input', {bubbles: true}));});
  await page.locator('#cost').evaluate(el => {el.value = '20'; el.dispatchEvent(new Event('input', {bubbles: true}));});
  check('negative-delivery-margin', await page.locator('#margin').textContent() === '-$10.00');
  await page.locator('#price').evaluate(el => {el.value = '49'; el.dispatchEvent(new Event('input', {bubbles: true}));});
  await page.locator('#cost').evaluate(el => {el.value = '8'; el.dispatchEvent(new Event('input', {bubbles: true}));});
  await page.locator('#economics').scrollIntoViewIfNeeded();
  await page.screenshot({path: path.join(qa, 'desktop-economics.png')});
  await page.locator('#scenario').selectOption('thin_demand');
  check('scenario-selection', await page.locator('#scenario').inputValue() === 'thin_demand');
  const embedded = await page.locator('#evidence-data').textContent().then(JSON.parse);
  if (embedded.economics) {
    const formatter = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 2});
    const policies = ['ordinary_U', 'expert_E', 'enhanced_Eplus', 'private_retention', 'shared_retention', 'library_retention'];
    for (const scenario of ['reference', 'thin_demand', 'low_price_human', 'residual_5min', 'residual_15min',
      'validator_correlation', 'model_upgrade', 'transfer_shift', 'high_shadow_cost']) {
      await page.locator('#scenario').selectOption(scenario);
      const rendered = await page.locator('#economic-table tbody tr').evaluateAll(rows => rows.map(row => [...row.querySelectorAll('td')].map(td => td.textContent)));
      check('economic-source-values-' + scenario, policies.every((policy, i) => {
        const source = embedded.economics.groups[scenario + '/' + policy];
        return ['mean_collections_usd', 'mean_complete_cost_usd', 'mean_profit_usd', 'mean_available_usd']
          .every((key, j) => rendered[i][j + 1] === formatter.format(source[key]));
      }));
    }
    await page.locator('#scenario').selectOption('thin_demand');
  }
  await page.getByRole('button', {name: 'FR', exact: true}).click();
  check('french-language', await page.getAttribute('html', 'lang') === 'fr');
  check('french-headings', (await page.locator('#results h2').textContent()).includes('nouveaux travaux'));
  check('language-preserves-scenario', await page.locator('#scenario').inputValue() === 'thin_demand');
  check('language-preserves-selected-arm', await page.getAttribute('#tab-E_plus', 'aria-selected') === 'true');
  check('all-translation-keys-covered', await page.evaluate(() => Object.keys(EN).every(key => key in FR)));
  await page.setViewportSize({width: 390, height: 844});
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({path: path.join(qa, 'mobile-fr-top.png')});
  check('mobile-390-no-page-overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.locator('#transfer').scrollIntoViewIfNeeded();
  await page.screenshot({path: path.join(qa, 'mobile-fr-transfer.png')});
  await page.setViewportSize({width: 320, height: 740});
  check('mobile-320-no-page-overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.getByRole('button', {name: 'EN', exact: true}).click();
  check('english-restored', await page.getAttribute('html', 'lang') === 'en');
  await page.locator('#uses').focus();
  const before = Number(await page.locator('#uses').inputValue());
  await page.locator('#uses').press('ArrowRight');
  check('slider-keyboard', Number(await page.locator('#uses').inputValue()) === before + 1);
  const data = await page.locator('#evidence-data').textContent().then(JSON.parse);
  if (data.final_data_required) {
    check('final-no-development-banner', await page.locator('#draft').isHidden());
    check('final-economics-present', !!data.economics?.groups?.['reference/ordinary_U']);
    check('final-composition-present', !!data.composition_raw);
  }
  check('no-script-errors', errors.length === 0, errors);
  check('self-contained-no-network', requests.every(url => url.startsWith('file:') || url.startsWith('data:')), requests);
  const receipt = {
    schema: 'operational-alpha-browser-qa/v1', html_sha256: require('crypto').createHash('sha256').update(fs.readFileSync(path.join(root, 'index.html'))).digest('hex'),
    final_data_required: data.final_data_required, checks, passed: checks.filter(c => c.passed).length, total: checks.length,
    screenshots: ['desktop-top.png', 'desktop-results.png', 'desktop-economics.png', 'mobile-fr-top.png', 'mobile-fr-transfer.png'].map(x => path.join(qa, x)),
    environment: {node: process.version, chromium: await browser.version()},
    preserved_initial_failures: [
      'Default Playwright launcher expected absent chromium_headless_shell-1234; no download performed.',
      'Installed Chromium launch in ordinary sandbox failed setsockopt EPERM before any page opened.'
    ],
    scope: 'Actual local desktop/mobile/keyboard/language/calculator checks. Not public HTTPS, external security review or production qualification.'
  };
  fs.writeFileSync(path.join(root, 'validation.json'), JSON.stringify(receipt, null, 2) + '\n');
  await browser.close();
  console.log(JSON.stringify({passed: receipt.passed, total: receipt.total, final_data_required: receipt.final_data_required, qa}));
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
