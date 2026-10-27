// SPDX-License-Identifier: Apache-2.0
'use strict';
const fs = require('fs');
const path = require('path');
const {chromium} = require('playwright');
const root = __dirname;
const qa = path.resolve(root, '../../../../browser_qa');
const checks = [];
let launchedBrowser;
const check = (name, condition, details = null) => {
  checks.push({name, passed: Boolean(condition), details});
  if (!condition) throw new Error(name + ': ' + JSON.stringify(details));
};

(async () => {
  fs.mkdirSync(qa, {recursive: true});
  const browser = await chromium.launch({headless: true,
    executablePath: '/root/.cache/ms-playwright/chromium-1181/chrome-linux/chrome',
    args: ['--no-sandbox']});
  launchedBrowser = browser;
  const page = await browser.newPage({viewport: {width: 1440, height: 1050}});
  await page.emulateMedia({reducedMotion: 'reduce'});
  const errors = [];
  const requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push(request.url()));
  await page.goto('file://' + path.join(root, 'index.html'));
  check('initial-language-en', await page.getAttribute('html', 'lang') === 'en');
  const opportunityEvidence = await page.locator('#evidence-data').textContent().then(JSON.parse);
  check('opportunity-edition-2.1.0', opportunityEvidence.edition === '2.1.0');
  check('opportunity-first-order', await page.evaluate(() => document.querySelector('main > section').id) === 'opportunity');
  check('six-preserved-discovery-candidates', await page.locator('#discovery-table tbody tr').count() === 6);
  check('science-four-of-four-three-arms', (await page.locator('#science-results .metric').allTextContents()).every(x => x === '4 / 4'));
  check('scientific-zero-increments', await page.locator('#science-alpha').textContent() === '0 pp' && await page.locator('#science-learned').textContent() === '0 pp');
  check('source-equilibrium-value', await page.locator('#mission-measure').textContent() === '0.376423');
  await page.screenshot({path: path.join(qa, 'opportunity-desktop-top.png')});
  await page.locator('#mission-equilibrium').focus();
  await page.locator('#mission-equilibrium').press('ArrowRight');
  check('mission-keyboard-focus', await page.evaluate(() => document.activeElement.id) === 'mission-unsupported_clock');
  check('source-clock-witness-value', await page.locator('#mission-measure').textContent() === '0.143317');
  await page.locator('#qualification').scrollIntoViewIfNeeded();
  await page.screenshot({path: path.join(qa, 'opportunity-desktop-clock.png')});
  await page.locator('#mission-calibrated_clock').click();
  check('source-assumed-interval', await page.locator('#mission-measure').textContent() === '0.801 – 3.2038');
  check('calibration-is-explicitly-assumed', (await page.locator('#mission-kind').textContent()).startsWith('Assumed'));
  await page.locator('#mission-new_mission').click();
  check('source-finite-time-rows', await page.locator('#mission-measure').textContent() === '48');
  check('inheritance-withdrawn', (await page.locator('#mission-decision').textContent()).includes('Withdraw'));
  await page.locator('#science-E').click();
  await page.locator('#science-E').press('ArrowRight');
  check('science-method-keyboard', await page.getAttribute('#science-E_plus', 'aria-selected') === 'true');
  check('source-capsule-identity', await page.locator('#capsule-hash').textContent() === opportunityEvidence.opportunity.confirmation.recipient.actual_capsule_sha256);
  const usd = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 2});
  for (const record of opportunityEvidence.opportunity.timing.cases) {
    await page.locator('#cash-mode').selectOption(record.mode);
    await page.locator('#cash-delay').selectOption(String(record.payment_release_delay_days));
    check('exact-cash-timing-' + record.mode + '-' + record.payment_release_delay_days,
      await page.locator('#cash-required').textContent() === usd.format(record.result.required_opening_cash_cents / 100) &&
      await page.locator('#cash-contribution').textContent() === usd.format(record.result.contribution_cents / 100));
  }
  check('synthetic-stress-all-losses-retained', await page.locator('#stress-grid span').count() === 32 && await page.locator('#stress-grid .loss').count() === 17);
  check('zero-saving-conventional-selection', opportunityEvidence.opportunity.selection_result.selection.plan.technical === false);
  check('hold-avoided-modeled-loss', await page.locator('#hold-increment').textContent() === '+$13.62');
  await page.locator('#arrangement').scrollIntoViewIfNeeded();
  await page.screenshot({path: path.join(qa, 'opportunity-desktop-cash.png')});
  await page.getByRole('button', {name: 'FR', exact: true}).click();
  check('opportunity-french-heading', (await page.locator('#opportunity h2').textContent()).includes('modèle scientifique'));
  check('mission-preserved-after-translation', await page.getAttribute('#mission-new_mission', 'aria-selected') === 'true');
  check('cash-preserved-after-translation', await page.locator('#cash-delay').inputValue() === '10');
  check('all-opportunity-translations-present', await page.evaluate(() => [...document.querySelectorAll('[data-en]')].every(e => e.dataset.fr && e.textContent.trim())));
  await page.setViewportSize({width: 390, height: 844});
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({path: path.join(qa, 'opportunity-mobile-fr-top.png')});
  check('opportunity-mobile-390-no-overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.locator('#qualification').scrollIntoViewIfNeeded();
  await page.screenshot({path: path.join(qa, 'opportunity-mobile-fr-mission.png')});
  await page.locator('#arrangement').scrollIntoViewIfNeeded();
  await page.screenshot({path: path.join(qa, 'opportunity-mobile-fr-cash.png')});
  await page.setViewportSize({width: 320, height: 740});
  check('opportunity-mobile-320-no-overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.getByRole('button', {name: 'EN', exact: true}).click();
  await page.setViewportSize({width: 1440, height: 1050});
  await page.locator('#earlier-study > summary').click();
  check('all-C5-arms-accepted', (await page.locator('#composition-results p').allTextContents()).length === 3 && (await page.locator('#composition-results p').allTextContents()).every(x => x.includes('Accepted')));
  check('all-primary-arms-render', await page.locator('#result-cards .metric').allTextContents().then(v => v.length === 3 && v.every(x => x === '4 / 4')));
  await page.screenshot({path: path.join(qa, 'desktop-top.png')});
  await page.locator('#results').scrollIntoViewIfNeeded();
  await page.screenshot({path: path.join(qa, 'desktop-results.png')});
  await page.locator('#tab-E').click();
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
    check('final-scientific-confirmation-present', !!data.opportunity?.confirmation?.arms?.E_plus);
  }
  check('no-script-errors', errors.length === 0, errors);
  check('self-contained-no-network', requests.every(url => url.startsWith('file:') || url.startsWith('data:')), requests);
  const receipt = {
    schema: 'operational-alpha-browser-qa/v1', html_sha256: require('crypto').createHash('sha256').update(fs.readFileSync(path.join(root, 'index.html'))).digest('hex'),
    final_data_required: data.final_data_required, checks, passed: checks.filter(c => c.passed).length, total: checks.length,
    screenshots: ['opportunity-desktop-top.png', 'opportunity-desktop-clock.png', 'opportunity-desktop-cash.png',
      'opportunity-mobile-fr-top.png', 'opportunity-mobile-fr-mission.png', 'opportunity-mobile-fr-cash.png',
      'desktop-top.png', 'desktop-results.png', 'desktop-economics.png', 'mobile-fr-top.png', 'mobile-fr-transfer.png'].map(x => path.join(qa, x)),
    environment: {node: process.version, chromium: await browser.version()},
    preserved_initial_failures: [
      'Default Playwright launcher expected absent chromium_headless_shell-1234; no download performed.',
      'Installed Chromium launch in ordinary sandbox failed setsockopt EPERM before any page opened.',
      'Edition 2.1 QA first expected padded 0.8010 while the actual locale formatter displays 0.801; corrected test expectation without changing data.',
      'Edition 2.1 QA old E-tab selector matched both studies; scoped it to the preserved software-study tab.'
    ],
    scope: 'Actual local desktop/mobile/keyboard/language/calculator checks. Not public HTTPS, external security review or production qualification.'
  };
  fs.writeFileSync(path.join(root, 'validation.json'), JSON.stringify(receipt, null, 2) + '\n');
  await browser.close();
  console.log(JSON.stringify({passed: receipt.passed, total: receipt.total, final_data_required: receipt.final_data_required, qa}));
})().catch(async error => { console.error(error.stack); if (launchedBrowser) await launchedBrowser.close(); process.exitCode = 1; });
