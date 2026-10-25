// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {chromium, executablePath} from './qa-tools.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
const hashFile = async name => createHash('sha256').update(await fs.readFile(path.join(root, name))).digest('hex');
const testedArtifact = {html_sha256: await hashFile('index.html'), manifest: JSON.parse(await fs.readFile(path.join(root, 'BUNDLE_MANIFEST.json'), 'utf8'))};
const browser = await chromium.launch({
    executablePath,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
});
const context = await browser.newContext({viewport: {width: 1440, height: 1100}, reducedMotion: 'reduce'});
const errors = [];
const network = [];
await context.route(/^https?:/, route => { network.push(route.request().url()); return route.abort(); });
const page = await context.newPage();
await page.addInitScript(() => {
    const original = crypto.subtle.digest.bind(crypto.subtle);
    window.__configInputs = [];
    crypto.subtle.digest = async (algorithm, bytes) => {
        const text = new TextDecoder().decode(bytes);
        if (text.startsWith('successor-omega/v1:release-stream\0')) {
            try {
                const config = JSON.parse(JSON.parse(text.split('\0')[1]));
                if (config.tasks && config.qualification && config.policy) window.__configInputs.push(config);
            } catch {}
        }
        return original(algorithm, bytes);
    };
});
page.on('pageerror', error => errors.push(error.message));
const checks = [];
const record = name => checks.push({name, passed: true});
const saved = async mode => page.evaluate(mode => {
    const key = Object.keys(localStorage).find(key => key.startsWith('agialpha:strategy-succession:') && key.endsWith(`:${mode}:v1`));
    return key ? JSON.parse(localStorage.getItem(key)) : null;
}, mode);
try {
    await page.goto(pathToFileURL(path.join(root, 'index.html')).href);
    await page.waitForFunction(() => document.documentElement.dataset.ready === 'true');
    await page.click('#tab-stream');
    assert.equal(await page.locator('.mission-card-item').count(), 6);
    assert.equal(await page.locator('#diagnostic-notice').isVisible(), false);
    record('Six missions and the selective full-cost gate are the default');
    await page.click('#stream-start');
    await page.waitForFunction(() => Object.keys(localStorage).some(key => key.endsWith(':flywheel:v1') && JSON.parse(localStorage.getItem(key)).cursor >= 1), null, {timeout: 60000});
    await page.click('#stream-stop');
    await page.waitForFunction(() => Object.keys(localStorage).some(key => key.endsWith(':flywheel:v1') && JSON.parse(localStorage.getItem(key)).status === 'STOPPED'), null, {timeout: 60000});
    const before = await saved('flywheel');
    await fs.writeFile(path.join(root, 'qa-config-digest-before.json'), JSON.stringify(await page.evaluate(() => window.__configInputs), null, 2));
    assert.equal(before.reason, 'USER_STOP');
    assert.ok(before.missions.length >= 1);
    const first = before.missions[0];
    record('STOP reaches a durable phase boundary after accepted work');
    await page.reload();
    await page.waitForFunction(() => document.documentElement.dataset.ready === 'true');
    await page.click('#tab-stream');
    const restored = await saved('flywheel');
    await fs.writeFile(path.join(root, 'qa-config-digest-after.json'), JSON.stringify(await page.evaluate(() => window.__configInputs), null, 2));
    assert.deepEqual(
        JSON.parse(await fs.readFile(path.join(root, 'qa-config-digest-before.json'), 'utf8')),
        JSON.parse(await fs.readFile(path.join(root, 'qa-config-digest-after.json'), 'utf8')),
    );
    record('The exact hashed fixed mission configuration is identical across reload');
    assert.equal(restored.missions[0].receipt_digest, first.receipt_digest);
    assert.equal(restored.cursor, before.cursor);
    assert.deepEqual(restored.proof, []);
    assert.deepEqual(restored.authority, []);
    assert.ok(restored.work >= before.work);
    assert.equal(await page.locator('#stream-resume').isEnabled(), true);
    assert.ok(restored.events.some(event => event.kind === 'RECOVER' && event.authentication === 'UNAUTHENTICATED_LOCAL_HISTORY'));
    record('Reload restores accepted work, charges inspection and inherits no proof or authority');
    await page.click('#stream-resume');
    await page.waitForFunction(() => {
        const key = Object.keys(localStorage).find(key => key.endsWith(':flywheel:v1'));
        const value = key && JSON.parse(localStorage.getItem(key));
        return value && (value.status === 'COMPLETE' || (value.status === 'STOPPED' && value.reason !== 'USER_STOP'));
    }, null, {timeout: 120000});
    const complete = await saved('flywheel');
    assert.equal(complete.status, 'COMPLETE', `Finite default run stopped: ${complete.reason}`);
    assert.equal(complete.missions.length, 6);
    assert.equal(new Set(complete.missions.map(value => value.task_id)).size, 6);
    assert.equal(complete.missions[0].receipt_digest, first.receipt_digest);
    assert.equal(complete.ledger.filter(value => value.kind === 'mission' && value.task_id === first.task_id).length, 1);
    assert.ok(complete.work <= complete.policy.totalWork);
    record('Explicit resume completes six distinct missions without replaying the accepted first mission');
    await fs.writeFile(path.join(root, 'qa-resumed-stream.json'), `${JSON.stringify(complete, null, 2)}\n`);
    await page.click('#clear-stream');
    await page.click('#stream-start');
    await page.waitForFunction(() => {
        const key = Object.keys(localStorage).find(key => key.endsWith(':flywheel:v1'));
        const value = key && JSON.parse(localStorage.getItem(key));
        return value && ['COMPLETE', 'STOPPED'].includes(value.status);
    }, null, {timeout: 120000});
    const uninterrupted = await saved('flywheel');
    assert.equal(uninterrupted.status, 'COMPLETE', uninterrupted.reason);
    assert.equal(uninterrupted.missions.length, 6);
    assert.ok(uninterrupted.assets.every(asset => asset.gate.correctness && asset.gate.net_benefit));
    assert.ok(uninterrupted.discoveries.some(discovery => discovery.gate?.decision === 'RETAIN_INCUMBENT'));
    await fs.writeFile(path.join(root, 'qa-uninterrupted-stream.json'), `${JSON.stringify(uninterrupted, null, 2)}\n`);
    record('An uninterrupted selective run completes and refuses an uneconomic investment');
    await page.screenshot({path: path.join(root, 'screenshot-stream-selective.png'), fullPage: true});
    await page.click('#stream-diagnostic');
    assert.equal(await page.locator('#diagnostic-notice').isVisible(), true);
    assert.match(await page.locator('#diagnostic-notice').textContent(), /not an economic promotion/);
    record('Construction diagnostic is a separate explicitly labeled mode');
    await page.click('#stream-start');
    await page.waitForFunction(() => {
        const key = Object.keys(localStorage).find(key => key.endsWith(':diagnostic:v1'));
        const value = key && JSON.parse(localStorage.getItem(key));
        return value && ['COMPLETE', 'STOPPED'].includes(value.status);
    }, null, {timeout: 120000});
    const diagnostic = await saved('diagnostic');
    await page.screenshot({path: path.join(root, 'screenshot-stream-diagnostic.png'), fullPage: true});
    assert.equal(diagnostic.status, 'COMPLETE', diagnostic.reason);
    assert.equal(diagnostic.missions.length, 6);
    assert.ok(diagnostic.assets.every(asset => asset.proof.length === 0 && asset.authority.length === 0));
    assert.ok(diagnostic.work <= diagnostic.policy.totalWork);
    await fs.writeFile(path.join(root, 'qa-diagnostic-stream.json'), `${JSON.stringify(diagnostic, null, 2)}\n`);
    record('Diagnostic remains bounded and retained programs inherit no proof or authority');
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    assert.equal(await hashFile('index.html'), testedArtifact.html_sha256);
    const report = {
        schema: 'strategy-succession-stream-browser-qa/v1', status: 'PASS', checks, errors, network, tested_artifact: testedArtifact,
        resumed: {work: complete.work, missions: complete.missions.length, assets: complete.assets.length},
        selective: {work: uninterrupted.work, missions: uninterrupted.missions.length, assets: uninterrupted.assets.length,
            decisions: uninterrupted.discoveries.map(value => ({stage: value.stage, decision: value.gate?.decision}))},
        diagnostic: {work: diagnostic.work, missions: diagnostic.missions.length, assets: diagnostic.assets.length,
            decisions: diagnostic.discoveries.map(value => ({stage: value.stage, decision: value.gate?.decision}))},
    };
    await fs.writeFile(path.join(root, 'STREAM_BROWSER_QA.json'), `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify(report));
} catch (error) {
    await page.screenshot({path: path.join(root, 'screenshot-stream-failure.png'), fullPage: true});
    await fs.writeFile(path.join(root, 'STREAM_BROWSER_QA.json'), `${JSON.stringify({status: 'FAIL', checks, errors, network, error: error.message, tested_artifact: testedArtifact, selective: await saved('flywheel'), diagnostic: await saved('diagnostic'), localStorage: await page.evaluate(() => Object.fromEntries(Object.keys(localStorage).map(key => [key,localStorage.getItem(key)]))), app_status: await page.locator('#app-status').textContent()}, null, 2)}\n`);
    console.error(error);
    process.exitCode = 1;
} finally {
    await browser.close();
}
