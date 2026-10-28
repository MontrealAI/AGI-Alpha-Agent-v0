// SPDX-License-Identifier: Apache-2.0
// Run: node studies/agi-alpha-profitable-possibility-v1/product/browser-test.mjs
// Requires Playwright + Chromium and Python 3.11+. No network calls are needed.
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
let playwright;
try {
    playwright = require('playwright');
} catch {
    assert(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES, 'Install Playwright or provide the runtime module directory.');
    playwright = require(join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES, 'playwright'));
}
const product = dirname(fileURLToPath(import.meta.url));
const output = process.env.AGI_ALPHA_QA_OUTPUT || mkdtempSync(join(tmpdir(), 'agi-alpha-worlds-qa-'));
const candidates = [process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE, playwright.chromium.executablePath()];
const cache = join(homedir(), '.cache', 'ms-playwright');
if (existsSync(cache)) {
    for (const entry of readdirSync(cache).filter(name => /^chromium-\d+$/.test(name)).sort().reverse()) {
        candidates.push(join(cache, entry, 'chrome-linux', 'chrome'));
        candidates.push(join(cache, entry, 'chrome-linux64', 'chrome'));
    }
}
const executablePath = candidates.find(path => path && existsSync(path));
assert(executablePath, 'A local Chromium executable is required.');
const browser = await playwright.chromium.launch({ headless: true, executablePath });
const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
const page = await context.newPage();
const errors = [], requests = [], checks = [];
page.on('pageerror', error => errors.push(error.message));
page.on('request', request => { if (/^https?:/.test(request.url())) requests.push(request.url()); });
const record = (name, detail) => checks.push({ name, detail, passed: true });

async function ready() {
    await page.waitForFunction(() => window.ExactWorlds && !window.ExactWorlds.state.busy);
}
async function buildPreset(key) {
    await page.locator(`[data-preset="${key}"]`).click();
    await page.locator('#build').click();
    await ready();
    assert.equal(await page.evaluate(() => ExactWorlds.state.phase), 'built', await page.locator('#statusText').innerText());
    return page.evaluate(() => ExactWorlds.state.stats);
}
async function custom(problem, accepted = true) {
    await page.locator('#customDetails').evaluate(element => { element.open = true; });
    await page.locator('#problemInput').fill(typeof problem === 'string' ? problem : JSON.stringify(problem));
    await page.locator('#build').click();
    await ready();
    if (accepted) assert.equal(await page.evaluate(() => ExactWorlds.state.phase), 'built', await page.locator('#statusText').innerText());
    else assert.equal(await page.evaluate(() => ExactWorlds.state.asset), null);
}
async function download(selector, name) {
    const event = page.waitForEvent('download');
    await page.locator(selector).click();
    const result = await event;
    const path = join(output, name);
    await result.saveAs(path);
    return path;
}
function pythonCheck(path) {
    const code = [
        'import json, sys',
        'sys.path.insert(0, sys.argv[1])',
        'from kernel import Fiber',
        'data=json.load(open(sys.argv[2]))',
        'fiber=Fiber.from_dict(data)',
        'distribution,_=fiber.collision_distribution()',
        'print(json.dumps({"count":str(fiber.count),"sha256":fiber.as_dict()["sha256"],',
        '"distribution":[[k,str(v)] for k,v in sorted(distribution.items())]}))',
    ].join('\n');
    return JSON.parse(execFileSync(process.env.PYTHON || 'python3', ['-c', code, resolve(product, '..'), path], { encoding: 'utf8' }));
}

// Deliberately simple labeled enumeration, independent of the quotient recurrence.
function brute(problem) {
    const rows = problem.rows.slice(), cols = problem.cols.slice();
    const table = rows.map(() => cols.map(() => 0)), worlds = [];
    function visit(index) {
        if (index === rows.length * cols.length) {
            if (rows.every(x => x === 0) && cols.every(x => x === 0)) worlds.push(JSON.parse(JSON.stringify(table)));
            return;
        }
        const i = Math.floor(index / cols.length), j = index % cols.length;
        const hi = Math.min(rows[i], cols[j], problem.caps[i][j]);
        const lo = j === cols.length - 1 ? rows[i] : 0;
        for (let x = lo; x <= hi; x++) {
            table[i][j] = x; rows[i] -= x; cols[j] -= x;
            visit(index + 1);
            rows[i] += x; cols[j] += x;
        }
    }
    visit(0);
    return worlds;
}
async function exhaustive(problem) {
    await custom(problem);
    const expected = brute(problem), actual = await page.evaluate(() => ExactWorlds.rpc('enumerate'));
    const expectedSet = new Set(expected.map(table => JSON.stringify(table)));
    const actualSet = new Set(actual.map(sample => JSON.stringify(sample.table)));
    assert.equal(actual.length, expected.length);
    assert.equal(actualSet.size, actual.length, 'Each integer rank must name a different table.');
    assert.deepEqual([...actualSet].sort(), [...expectedSet].sort());
    assert(actual.every(sample => sample.rank === sample.roundtrip), 'rank(unrank(k)) must equal k.');
    const histogram = new Map();
    for (const table of expected) {
        const k = table.flat().reduce((n, x) => n + x * (x - 1) / 2, 0);
        histogram.set(k, (histogram.get(k) || 0n) + 1n);
    }
    const distribution = [...histogram].sort((a, b) => a[0] - b[0]).map(([k, n]) => [k, String(n)]);
    assert.deepEqual(await page.evaluate(() => ExactWorlds.state.distribution), distribution);
    for (const [threshold] of distribution) {
        const tail = await page.evaluate(k => ExactWorlds.rpc('enumerate', { threshold: k }), threshold);
        const expectedTail = expected.filter(table => table.flat().reduce((n, x) => n + x * (x - 1) / 2, 0) >= threshold);
        const tailSet = new Set(tail.map(sample => JSON.stringify(sample.table)));
        assert.equal(tailSet.size, tail.length, 'Conditional ranks must also be bijective.');
        assert.deepEqual([...tailSet].sort(), expectedTail.map(table => JSON.stringify(table)).sort());
    }
    record(`Exhaustive family and every attainable tail: ${problem.name}`, { worlds: actual.length, distribution });
}

try {
    await page.goto(pathToFileURL(join(product, 'index.html')).href);
    await ready();
    assert.equal(await page.title(), 'AGI ALPHA — Exact Worlds');
    assert(await page.locator('#accept').isDisabled());
    const defaultStats = await buildPreset('capacity');
    assert.equal(defaultStats.count, '20322');
    assert.equal(defaultStats.states, 106);
    assert.equal(defaultStats.edges, 703);
    assert(await page.locator('#accept').isDisabled());
    const instrumentPath = await download('#downloadInstrument', 'capacity-instrument.json');
    const exported = JSON.parse(readFileSync(instrumentPath, 'utf8'));
    const independent = pythonCheck(instrumentPath);
    assert.equal(independent.count, '20322');
    assert.equal(independent.sha256, exported.sha256);
    assert.deepEqual(independent.distribution, await page.evaluate(() => ExactWorlds.state.distribution));
    record('Browser/Python canonical artifact identity', { count: independent.count, sha256: independent.sha256 });

    const first = await page.evaluate(() => ExactWorlds.state.batch.samples);
    await page.locator('#resample').click(); await ready();
    assert.deepEqual(await page.evaluate(() => ExactWorlds.state.batch.samples), first);
    await page.locator('#seed').fill('a-different-seed');
    await page.locator('#resample').click(); await ready();
    assert.notDeepEqual(await page.evaluate(() => ExactWorlds.state.batch.samples), first);
    await page.locator('#verify').click();
    assert.equal(await page.evaluate(() => ExactWorlds.state.verification.passed), true);
    assert.equal(await page.evaluate(() => ExactWorlds.state.verification.worlds), 32);
    assert.equal(await page.evaluate(() => {
        const table = structuredClone(ExactWorlds.state.batch.samples[0].table);
        table[0][0] = 1;
        return ExactWorlds.validateTable(ExactWorlds.state.problem, table).length > 0;
    }), true);
    await page.locator('#accept').click(); await ready();
    assert.equal(await page.evaluate(() => ExactWorlds.state.receipt.status), 'SIMULATED_ACCEPTED');
    const receiptPath = await download('#downloadReceipt', 'receipt.json');
    const jsonPath = await download('#downloadJson', 'tables.json');
    const csvPath = await download('#downloadCsv', 'tables.csv');
    const receipt = JSON.parse(readFileSync(receiptPath, 'utf8'));
    assert.equal(receipt.amount_paid_usd, 0);
    assert.equal(receipt.instrument_sha256, exported.sha256);
    assert.equal(receipt.seed, 'a-different-seed');
    assert.equal(JSON.parse(readFileSync(jsonPath, 'utf8')).samples.length, 32);
    const csv = readFileSync(csvPath, 'utf8').trim().split(/\r?\n/);
    assert.equal(csv.length, 33);
    assert.equal(csv[0].split(',').length, 36);
    record('Seed replay, independent feasibility verification, acceptance and all four exports', { worlds: 32 });

    const inheritedDigest = await page.evaluate(() => ExactWorlds.state.asset.sha256);
    await page.locator('#threshold').selectOption('8');
    await page.locator('#condition').click(); await ready();
    assert.equal(await page.evaluate(() => ExactWorlds.state.batch.count), '297');
    assert.equal(await page.locator('#worldCount').innerText(), '297');
    assert.equal(await page.evaluate(() => ExactWorlds.state.asset.sha256), inheritedDigest);
    assert.equal(await page.evaluate(() => ExactWorlds.state.batch.samples.every(s => s.concentration === 8)), true);
    assert.equal(await page.evaluate(() => ExactWorlds.state.verification), null);
    assert.equal(await page.evaluate(() => ExactWorlds.state.receipt), null);
    await page.locator('#verify').click();
    assert.equal(await page.evaluate(() => ExactWorlds.state.verification.passed), true);
    record('Successor tail reuses the unchanged artifact and invalidates previous acceptance', { threshold: 8, tailWorlds: 297 });

    await exhaustive({ name: 'transparent_2x2', rows: [2, 2], cols: [2, 2], caps: [[2, 2], [2, 2]] });
    await exhaustive({ name: 'asymmetric_future_caps', rows: [3, 2, 3], cols: [2, 2, 2, 2], caps: [[2, 1, 2, 0], [1, 2, 0, 2], [2, 2, 2, 2]] });
    await exhaustive({ name: 'bounded_3x4', rows: [3, 3, 2], cols: [2, 2, 2, 2], caps: [[2, 2, 2, 2], [2, 2, 2, 2], [2, 2, 2, 2]] });
    await exhaustive({ name: 'zero_mass', rows: [0, 0], cols: [0, 0, 0], caps: [[1, 0, 2], [0, 1, 2]] });
    const binaryStats = await buildPreset('binary');
    assert.equal(binaryStats.count, '1860');
    assert.deepEqual(await page.evaluate(() => ExactWorlds.state.distribution), [[0, '1860']]);
    assert.match(await page.locator('#tailSize').innerText(), /cannot select a rarer tail/);
    record('Binary preset honestly reports a constant concentration statistic', { worlds: 1860 });

    const large = { name: 'Épreuve 😀', rows: [8, 8, 8, 8, 8, 8], cols: Array(24).fill(2), caps: Array.from({ length: 6 }, () => Array(24).fill(1)) };
    await custom(large);
    const largeCount = await page.evaluate(() => ExactWorlds.state.stats.count);
    assert(BigInt(largeCount) > BigInt(Number.MAX_SAFE_INTEGER));
    const largePath = await download('#downloadInstrument', 'large-unicode-instrument.json');
    assert.equal(pythonCheck(largePath).count, largeCount);
    await page.locator('#verify').click();
    assert.equal(await page.evaluate(() => ExactWorlds.state.verification.passed), true);
    record('BigInt counts above 2^53 and Unicode canonicalization', { count: largeCount });

    const invalid = [
        ['json', '{this is not JSON'],
        ['totals', { rows: [2, 1], cols: [2, 2], caps: [[2, 2], [2, 2]] }],
        ['empty', { rows: [2, 2], cols: [2, 2], caps: [[0, 0], [0, 0]] }],
        ['dimensions', { rows: Array(9).fill(0), cols: [0], caps: Array.from({ length: 9 }, () => [0]) }],
        ['caps', { rows: [1], cols: [1], caps: [[1.5]] }],
        ['margins', { rows: [-1], cols: [-1], caps: [[1]] }],
    ];
    for (const [code, input] of invalid) {
        await custom(input, false);
        assert.equal(await page.evaluate(() => ExactWorlds.state.status.params.code), code);
        assert(await page.locator('#downloadInstrument').isDisabled());
    }
    record('Explicit refusal leaves no accepted artifact', { cases: invalid.map(([code]) => code) });

    await page.locator('[data-preset="capacity"]').click();
    await page.evaluate(() => { document.querySelector('#build').click(); document.querySelector('#cancel').click(); });
    await ready();
    assert.equal(await page.evaluate(() => ExactWorlds.state.asset), null);
    assert.equal(await page.evaluate(() => ExactWorlds.state.status.key), 'cancelled');
    record('Cancellation discards partial construction', {});

    await buildPreset('capacity');
    await page.locator('#customDetails').evaluate(element => { element.open = false; });
    await page.locator('#verify').click();
    await page.locator('#accept').click(); await ready();
    await page.screenshot({ path: join(output, 'desktop-en.png'), fullPage: true });
    for (const width of [1024, 390, 360]) {
        await page.setViewportSize({ width, height: 900 });
        await page.locator('#fr').click();
        assert.equal(await page.locator('html').getAttribute('lang'), 'fr');
        assert.equal(await page.locator('#build').innerText(), 'Construire l’instrument');
        assert.match(await page.locator('#verifyLine').innerText(), /tableaux respectent/);
        assert.match(await page.locator('#receiptTitle').innerText(), /Évaluation acceptée/);
        const dimensions = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
        assert(dimensions.document <= dimensions.width + 1, `No page overflow at ${width}px: ${JSON.stringify(dimensions)}`);
    }
    await page.screenshot({ path: join(output, 'mobile-fr.png'), fullPage: true });
    record('Responsive English/French workflow', { widths: [1440, 1024, 390, 360] });
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, []);
    record('Offline file:// execution', { pageErrors: errors.length, httpRequests: requests.length });
    const report = { tested_at_utc: new Date().toISOString(), engine: await browser.version(), output, checks };
    writeFileSync(join(output, 'browser-report.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
} finally {
    await browser.close();
}
