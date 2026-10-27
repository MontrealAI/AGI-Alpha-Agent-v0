// SPDX-License-Identifier: Apache-2.0
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require(process.env.CUSTOMER_FUNDS_JSDOM);
const errors = [], checks = [];
const consoleLog = new VirtualConsole();
consoleLog.on('jsdomError', error => errors.push(error.message));
const dom = new JSDOM(fs.readFileSync('docs/flywheel/index.html', 'utf8'), {
  runScripts: 'dangerously', url: 'https://example.test/flywheel/', virtualConsole: consoleLog,
  beforeParse(window) {
    window.TextEncoder = require('node:util').TextEncoder;
    window.TextDecoder = require('node:util').TextDecoder;
    window.URL.createObjectURL = () => 'blob:fixture'; window.URL.revokeObjectURL = () => {};
  }
});
const window = dom.window, document = window.document, byId = id => document.getElementById(id);
assert.deepEqual(errors, []);
assert.equal(byId('customer-stage').options.length, 7);
for (const language of ['en', 'fr']) {
  byId('lang-' + language).click();
  for (let index = 0; index < 7; index++) {
    byId('customer-stage').value = String(index);
    byId('customer-stage').dispatchEvent(new window.Event('change'));
    assert.equal(byId('customer-stage').value, String(index));
    assert.match(byId('customer-operating-boundary').textContent, /0[,.]00/);
    assert.match(byId('customer-balances').textContent, /USD 0/);
    checks.push(language + ': receipt state ' + index + ' renders with no operating cash increment');
  }
  assert.match(byId('customer-margin').textContent, /2[,.\s\u00a0\u202f]900[,.]21/);
  assert.match(byId('customer-alpha').textContent, language === 'en' ? /unmeasured/ : /non mesuré/);
  assert.equal(byId('customer-confirmation').querySelectorAll('tbody tr').length, 4);
  checks.push(language + ': price/Alpha/downside views render');
}
assert.deepEqual(errors, []);
console.log(JSON.stringify({passed: true, checks, count: checks.length, errors,
  scope: 'Actual generated JavaScript in jsdom 26.1.0; no rendered layout, browser, CSP, download or accessibility qualification'}, null, 2));
window.close();
