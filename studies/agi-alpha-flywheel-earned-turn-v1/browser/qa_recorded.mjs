// Presentation-only QA: no mission starts and no native confirmation reruns.
import {chromium, executablePath} from './qa-tools.mjs';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';

const root = new URL('../', import.meta.url);
const out = new URL('./qa/', import.meta.url);
await mkdir(out, {recursive: true});
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const readJSON = async url => JSON.parse(await readFile(url, 'utf8'));
const record = await readJSON(new URL('./recorded-summary.json', import.meta.url));
const analysis = await readJSON(new URL('results/confirmation-v1/ANALYSIS.json', root));
const derived = await readJSON(new URL('results/confirmation-v1/DERIVED_REPORT.json', root));
const freeze = await readJSON(new URL('protocol/FREEZE.json', root));
const manifest = await readJSON(new URL('./BUNDLE_MANIFEST.json', import.meta.url));
const results = [], errors = [], requests = [];
function check(name, value, detail) {
    results.push({name, passed: Boolean(value), ...(detail === undefined ? {} : {detail})});
    if (!value) throw Error(name);
}
let browser;
try {
    assert.deepStrictEqual(record.analysis, analysis);
    check('embedded_analysis_exactly_matches_original', true);
    assert.deepStrictEqual(record.example_first_registered_stream, derived.example_first_registered_stream);
    check('first_registered_lineage_exactly_matches_derived_record', true);
    check('protocol_and_freeze_identities', record.protocol_hash === freeze.protocol_sha256 && record.freeze_hash === freeze.freeze_sha256);
    check('frozen_browser_execution_identity', manifest.execution_source_hash === 'ccf229979ee484c3a4f754998a309f2d10bc6e4fc4cc6f4b995d7261dd2c4e5b');
    const changed = [];
    for (const [path, digest] of Object.entries(freeze.files)) {
        if (hash(await readFile(new URL(path, root))) !== digest) changed.push(path);
    }
    check('all_scientific_frozen_files_unchanged', changed.length === 0, changed);
    for (const ref of record.evidence_files) {
        assert.equal(hash(await readFile(new URL(ref.path, root))), ref.sha256);
    }
    check('all_recorded_source_references_match_bytes', true, record.evidence_files.length);
    check('all_seven_arm_results_preserved', Object.keys(record.analysis.arms).length === 7 && Object.values(record.analysis.arms).every(arm => arm.trials === 24 && arm.qualified === 492 && arm.offered === 492));
    check('hold_and_unresolved_claims_preserved', record.decision.product_admission === 'HOLD' && !record.decision.primary_gate && record.resource_interpretation.full_investment_recovery === 'UNRESOLVED' && record.decision.acceleration === 'NOT_TESTED');
    browser = await chromium.launch({headless: true, executablePath, args: ['--no-sandbox']});
    for (const [label, viewport] of [['desktop', {width:1440,height:1100}], ['mobile', {width:390,height:844}]]) {
        const context = await browser.newContext({viewport, acceptDownloads:true});
        await context.route('http**/*', route => {requests.push(route.request().url());route.abort();});
        const page = await context.newPage();
        page.on('pageerror', error => errors.push(String(error)));
        await page.goto(new URL('./index.html', import.meta.url).href);
        await page.waitForFunction(() => globalThis.__earnedTurnReady);
        check(label + '_fresh_start_remains_available', await page.locator('#start-button').isEnabled());
        check(label + '_recorded_headline', await page.locator('#research-summary h3').textContent() === record.headline);
        check(label + '_native_disconnection_visible', (await page.locator('#research').textContent()).includes('Native executor disconnected'));
        check(label + '_not_automatically_executing_missions', await page.evaluate(() => !globalThis.__earnedTurnState?.accepted?.length));
        check(label + '_all_visible_primary_values', await page.locator('.recorded-ratio').innerText() === '0.99395% CI [0.967, 1.026]' || (await page.locator('.recorded-ratio').innerText()).replace(/\s+/g, '') === '0.99395%CI[0.967,1.026]');
        check(label + '_no_horizontal_overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await page.locator('#research').screenshot({path:fileURLToPath(new URL('recorded-' + label + '.png', out))});
        await page.locator('.recorded-detail').nth(0).locator('summary').click();
        await page.locator('.recorded-detail').nth(1).locator('summary').click();
        check(label + '_seven_comparison_rows', await page.locator('.recorded-detail tbody tr').count() === 7);
        check(label + '_four_actual_lineage_steps', await page.locator('.recorded-lineage li').count() === 4);
        check(label + '_expanded_no_page_overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await page.locator('.research-card').screenshot({path:fileURLToPath(new URL('recorded-' + label + '-expanded.png', out))});
        const waiting = page.waitForEvent('download');
        await page.click('#research-download');
        const download = await waiting;
        const downloaded = new URL('recorded-download-' + label + '.json', out);
        await download.saveAs(fileURLToPath(downloaded));
        check(label + '_download_name', download.suggestedFilename() === 'AGI_ALPHA_Earned_Turn_Recorded_Study.json');
        assert.deepStrictEqual(await readJSON(downloaded), record);
        check(label + '_download_exact_data', true);
        await context.close();
    }
    check('no_network_requests', requests.length === 0, requests);
    check('no_browser_errors', errors.length === 0, errors);
} catch (error) {
    results.push({name:'unexpected_exception',passed:false,detail:String(error)});
} finally {
    if (browser) await browser.close();
    const report = {
        schema:'earned-turn-recorded-browser-qa/v1',
        at:new Date().toISOString(),
        scope:'PRESENTATION_AND_RECORDED_DOWNLOAD_ONLY_NOT_ADDITIONAL_CONFIRMATION',
        html_sha256:hash(await readFile(new URL('./index.html',import.meta.url))),
        recorded_sha256:hash(await readFile(new URL('./recorded-summary.json',import.meta.url))),
        execution_source_hash:manifest.execution_source_hash,
        results, errors, requests,
        pass:results.every(result=>result.passed),
    };
    await writeFile(new URL('RECORDED_QA.json',out),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
    if (!report.pass) process.exitCode=1;
}
