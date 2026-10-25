// SPDX-License-Identifier: Apache-2.0
// Publication-data verification only; outside the frozen scientific/browser inventory.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {chromium, executablePath} from '../browser/qa-tools.mjs';

const publication = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(publication, '..');
const browserRoot = path.join(root, 'browser');
const file = path.join(browserRoot, 'index.html');
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const original = await fs.readFile(file);
const manifest = JSON.parse(await fs.readFile(path.join(browserRoot, 'BUNDLE_MANIFEST.json'), 'utf8'));
const recorded = JSON.parse(await fs.readFile(path.join(browserRoot, 'recorded-summary.json'), 'utf8'));
assert.equal(digest(original), manifest.output_sha256);
assert.equal(manifest.execution_source_hash, '67fa72590db37750936fce825c34e1d207aa61a831f1678ded24a768d43dc407');
const evidenceDir = path.join(publication, 'verification');
await fs.mkdir(evidenceDir, {recursive: true});
const reportPath = path.join(publication, 'FINAL_RECORDED_QA.json');
try {
    const previousBytes = await fs.readFile(reportPath);
    const previous = JSON.parse(previousBytes);
    if (previous.html_sha256 !== digest(original)) {
        const previousDir = path.join(evidenceDir, `recorded-${previous.html_sha256.slice(0, 16)}`);
        await fs.mkdir(previousDir, {recursive: true});
        await fs.writeFile(path.join(previousDir, 'RECORDED_QA.json'), previousBytes, {flag: 'wx'}).catch(error => {
            if (error.code !== 'EEXIST') throw error;
        });
        for (const name of ['actual-recorded-desktop.png', 'actual-recorded-mobile.png']) {
            const previousImage = await fs.readFile(path.join(evidenceDir, name));
            await fs.writeFile(path.join(previousDir, name), previousImage, {flag: 'wx'}).catch(error => {
                if (error.code !== 'EEXIST') throw error;
            });
        }
    }
} catch (error) {
    if (error.code !== 'ENOENT') throw error;
}
const browser = await chromium.launch({executablePath, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']});
const context = await browser.newContext({viewport: {width: 1440, height: 1100}, reducedMotion: 'reduce'});
const network = [];
const errors = [];
await context.route(/^https?:/, route => {network.push(route.request().url()); return route.abort();});
const page = await context.newPage();
page.on('pageerror', error => errors.push(error.message));
const checks = [];
const downloads = [];
try {
    await page.goto(pathToFileURL(file).href);
    await page.waitForFunction(() => document.documentElement.dataset.ready === 'true');
    assert.equal(await page.locator('#empty-result').isVisible(), true);
    assert.equal(await page.locator('#plan-result').isVisible(), false);
    checks.push('Default first-mission screen remains fresh and uncomputed');
    await page.click('#tab-evidence');
    assert.match(await page.locator('#panel-evidence .recorded-tag').textContent(), /RECORDED RESEARCH/);
    assert.equal(await page.locator('.research-headline').textContent(), recorded.headline);
    const tables = page.locator('.research-table');
    assert.equal(await tables.count(), (recorded.tables ?? []).length);
    for (const [tableIndex, expected] of (recorded.tables ?? []).entries()) {
        const table = tables.nth(tableIndex);
        assert.deepEqual(await table.locator('thead th').allTextContents(), expected.columns.slice(0, 8).map(column => column.label ?? column.key));
        assert.equal(await table.locator('tbody tr').count(), Math.min(expected.rows.length, 100));
        for (const [rowIndex, row] of expected.rows.slice(0, 100).entries()) {
            const values = expected.columns.slice(0, 8).map(column => row[column.key] === undefined || row[column.key] === null
                ? '—' : typeof row[column.key] === 'object' ? JSON.stringify(row[column.key], null, 2) : String(row[column.key]));
            assert.deepEqual(await table.locator('tbody tr').nth(rowIndex).locator('th,td').allTextContents(), values);
        }
    }
    checks.push('Actual recorded headline, headers and every visible result cell match the source JSON');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({path: path.join(evidenceDir, 'actual-recorded-desktop.png'), fullPage: true});
    checks.push('Desktop evidence panel has no page overflow');
    const expectedDownloads = [...(recorded.downloads ?? []), {
        label: 'Recorded research summary ↓', filename: 'recorded-research-summary.json', data: recorded,
    }];
    for (const item of expectedDownloads) {
        const waiting = page.waitForEvent('download');
        await page.getByRole('button', {name: item.label, exact: true}).click();
        const result = await waiting;
        const bytes = await fs.readFile(await result.path());
        assert.equal(result.suggestedFilename(), item.filename);
        if (typeof item.data === 'string') assert.equal(bytes.toString('utf8'), item.data);
        else assert.deepEqual(JSON.parse(bytes.toString('utf8')), item.data);
        downloads.push({filename: item.filename, bytes: bytes.length, sha256: digest(bytes)});
    }
    checks.push('Every embedded evidence download and full summary download matches the source data');
    await page.setViewportSize({width: 390, height: 844});
    await page.evaluate(() => {
        if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
        window.scrollTo(0, 0);
    });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.ok(await page.locator('.research-table-scroll').evaluateAll(nodes => nodes.every(node => node.clientWidth <= innerWidth)));
    await page.screenshot({path: path.join(evidenceDir, 'actual-recorded-mobile.png'), fullPage: true});
    checks.push('Mobile comparison tables scroll within their containers without page overflow');
    assert.deepEqual(network, []);
    assert.deepEqual(errors, []);
    assert.equal(digest(await fs.readFile(file)), digest(original));
    checks.push('No network calls, page errors or artifact changes during verification');
    const report = {
        schema: 'strategy-succession-final-recorded-ui-qa/v1', status: 'PASS', mode: 'file:// offline',
        html_sha256: digest(original), html_bytes: original.length,
        execution_source_hash: manifest.execution_source_hash,
        recorded_data_sha256: digest(await fs.readFile(path.join(browserRoot, 'recorded-summary.json'))),
        pre_embedding_qa_html_sha256: '60013139060365e1f122e98c9f87acc6b47ab7eac69fd897b3548928f9c4282e',
        checks, downloads, errors, network, browser: await browser.version(),
        scope: 'Actual recorded research rendering and data downloads; no scientific rerun, source edit or deployment.',
    };
    await fs.writeFile(path.join(publication, 'FINAL_RECORDED_QA.json'), `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify({status: report.status, checks: checks.length, downloads: downloads.length, html_sha256: report.html_sha256}));
} catch (error) {
    await page.screenshot({path: path.join(evidenceDir, 'actual-recorded-failure.png'), fullPage: true});
    await fs.writeFile(path.join(publication, 'FINAL_RECORDED_QA.json'), `${JSON.stringify({status: 'FAIL', error: error.message,
        html_sha256: digest(original), checks, downloads, errors, network}, null, 2)}\n`);
    throw error;
} finally {
    await browser.close();
}
