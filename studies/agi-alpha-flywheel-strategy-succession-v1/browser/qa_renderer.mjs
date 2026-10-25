// SPDX-License-Identifier: Apache-2.0
// Synthetic rendering fixture only; never embedded as study evidence in index.html.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {chromium, executablePath} from './qa-tools.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
const original = await fs.readFile(path.join(root, 'index.html'), 'utf8');
const fixturePath = path.join(root, 'qa-renderer-temporary.html');
const expression = /(<script type="application\/json" id="bundle-data">)([\s\S]*?)(<\/script>)/;
const match = original.match(expression);
if (!match) throw new Error('Bundle data missing');
const data = JSON.parse(match[2]);
data.research = {
    headline: 'QA fixture only — not a study result',
    description: 'Synthetic rendering values. This file is removed after the focused UI test.',
    metrics: [{label: 'Fixture rows', value: '2'}],
    tables: [{
        title: 'Synthetic renderer comparison',
        columns: [{key: 'method', label: 'Method'}, {key: 'coverage', label: 'Targets met', align: 'right'},
            {key: 'cost', label: 'Separate counter', align: 'right'}],
        rows: [{method: 'Fixture A', coverage: '2 / 3', cost: 100},
            {method: '<img src="https://invalid.example/never-request">', coverage: '1 / 3', cost: 200}],
        note: 'These values are invented only to test safe table rendering.',
    }],
};
const encoded = JSON.stringify(data).replaceAll('<', '\\u003c').replaceAll('\u2028', '\\u2028').replaceAll('\u2029', '\\u2029');
await fs.writeFile(fixturePath, original.replace(expression, (_, start, _body, end) => `${start}${encoded}${end}`));
const browser = await chromium.launch({executablePath, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']});
const context = await browser.newContext({viewport: {width: 390, height: 844}, reducedMotion: 'reduce'});
const network = [];
await context.route(/^https?:/, route => {network.push(route.request().url()); return route.abort();});
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
    await page.goto(pathToFileURL(fixturePath).href);
    await page.waitForFunction(() => document.documentElement.dataset.ready === 'true');
    assert.equal(await page.locator('#empty-result').isVisible(), true);
    await page.click('#tab-evidence');
    assert.equal(await page.locator('.research-table tbody tr').count(), 2);
    assert.equal(await page.locator('.research-table thead th').count(), 3);
    assert.equal(await page.locator('.research-table img').count(), 0);
    assert.match(await page.locator('.research-table tbody').textContent(), /<img src=/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.deepEqual(network, []);
    assert.deepEqual(errors, []);
    const report = {
        schema: 'strategy-succession-recorded-renderer-qa/v1', status: 'PASS', synthetic_fixture_only: true,
        original_html_sha256: createHash('sha256').update(original).digest('hex'),
        execution_source_hash: data.execution_source_hash,
        checks: ['Default useful-plan page remains uncomputed', 'Comparison table rows and headers render',
            'Cells are escaped text, not executable HTML', 'Mobile scroll stays inside the table', 'No network or page errors'],
    };
    await fs.writeFile(path.join(root, 'RENDERER_QA.json'), `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify(report));
} finally {
    await browser.close();
    await fs.unlink(fixturePath);
}
