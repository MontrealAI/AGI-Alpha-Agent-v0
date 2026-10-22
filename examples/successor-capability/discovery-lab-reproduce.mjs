// SPDX-License-Identifier: Apache-2.0
/** Reproduce the public finite campaign bank; output carries no execution authority. */
import {readFileSync, mkdirSync, writeFileSync, lstatSync, realpathSync} from 'node:fs';
import {resolve, relative, isAbsolute, dirname, basename, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {DEFAULT_CHARTER, runCampaign, verifyCampaign} from './discovery-lab.mjs';
import {canonical} from './discovery-lab-contract.mjs';
const arguments_ = process.argv.slice(2);
let full = false, output = null;
for (let index = 0; index < arguments_.length; index++) {
    if (arguments_[index] === '--full') full = true;
    else if (arguments_[index] === '--output' && arguments_[index + 1] && output === null) output = resolve(arguments_[++index]);
    else throw Error('Usage: node discovery-lab-reproduce.mjs [--full] [--output <evidence-directory>]');
}
const repository = realpathSync(fileURLToPath(new URL('../../', import.meta.url)));
function outsideRepository(path) {
    const missing = [];
    let existing = resolve(path);
    while (true) {
        try { lstatSync(existing); break; }
        catch (error) {
            if (error.code !== 'ENOENT' || dirname(existing) === existing) throw error;
            missing.unshift(basename(existing));
            existing = dirname(existing);
        }
    }
    // Resolve an existing output or its nearest existing ancestor. A dangling
    // symlink remains an error; never treat it as a missing plain directory.
    const actual = resolve(realpathSync(existing), ...missing);
    const inRepo = relative(repository, actual);
    if (!inRepo || !isAbsolute(inRepo) && inRepo !== '..' && !inRepo.startsWith('..' + sep)) {
        throw Error('Choose an evidence directory outside this repository.');
    }
    return actual;
}
if (output) output = outsideRepository(output);
const destinations = new Map();
if (output) {
    // Preflight the complete finite bank before mkdir or any report write. Keep
    // run()'s immediate reports, including evidence from an unexpected outcome.
    const names = ['accepted-default', 'noisy-one-use', 'noisy-twelve-uses', 'undeclared-quadratic-drift',
        'quadratic-reconstruction', 'non-updatable-memory', 'wrong-location', 'staging-enabled',
        'hidden-private-coupling', 'exhausted-search', 'stronger-checkpoint', 'stronger-four-control-successor',
        'route-before-change', 'equal-profiles-current-route', 'lineage-generation-two', 'lineage-generation-three'];
    const reports = outsideRepository(resolve(output, 'reports'));
    for (const name of [...names.map(id => 'reports/' + id + '.json'), 'summary.json', 'elapsed-receipts.json']) {
        destinations.set(name, outsideRepository(resolve(output, name)));
    }
    mkdirSync(reports, {recursive: true});
}
function writeEvidence(name, bytes) {
    if (!destinations.has(name)) throw Error('Unplanned evidence destination.');
    writeFileSync(outsideRepository(destinations.get(name)), bytes);
}
const hash = value => createHash('sha256').update(value).digest('hex');
const sources = Object.fromEntries(['discovery-lab.mjs', 'discovery-lab-checker.mjs', 'discovery-lab-baselines.mjs',
    'discovery-lab-contract.mjs', 'discovery-lab-reproduce.mjs'].map(name => [name, hash(readFileSync(new URL(name, import.meta.url)))]));
const records = [], elapsedReceipts = [], ancestry = new WeakMap();
const charter = changes => ({...structuredClone(DEFAULT_CHARTER), ...changes});
function run(id, specification, expected, parent = null) {
    const constructionStart = performance.now();
    const report = runCampaign(specification, {parent});
    const constructionElapsedMs = Math.max(0, Math.round(performance.now() - constructionStart));
    const verificationStart = performance.now();
    const verification = verifyCampaign(specification, report, {parent});
    const verificationElapsedMs = Math.max(0, Math.round(performance.now() - verificationStart));
    elapsedReceipts.push({id, constructionElapsedMs, verificationElapsedMs,
        scope: 'Actual local wall clock; separate from deterministic logical resource vectors.'});
    const ancestors = parent ? [...(ancestry.get(parent) || []), {charter: parent.charter, result: parent}] : [];
    ancestry.set(report, ancestors);
    const evidence = {schema: 'discovery-lab-campaign-evidence/v1', charter: specification, result: report, ancestors};
    if (output) writeEvidence('reports/' + id + '.json', JSON.stringify(evidence, null, 2) + '\n');
    if (!verification.verified || report.state !== expected) throw Error(`Unexpected ${id} outcome: ${report.state}`);
    records.push({id, expected, state: report.state, charter: specification,
        reportDigest: hash(canonical(report)), stages: report.stages.map(({kind, status, reason}) => ({kind, status, reason})),
        resources: report.resources, verificationResources: verification.verificationResources,
        queryVerification: report.queryChecker, reportPath: `reports/${id}.json`,
        ancestorReportDigests: ancestors.map(item => hash(canonical(item.result))),
        lineage: report.lineage, reuse: report.reuse,
        queryOutcome: report.queryResults ? {threshold: report.queryResults.thresholdScreening.results,
            inverse: report.queryResults.inverseDesign, selection: report.queryResults.constrainedSelection} : null,
        competitors: report.comparisons.map(({name, status, relation, measuredWork}) =>
            ({name, status, relation: relation || null, measuredWork})), ...(full ? {report, ancestors} : {})});
    return report;
}
const base = run('accepted-default', charter({}), 'accepted');
run('noisy-one-use', charter({noise: 1, accuracy: 4, intendedUses: 1}), 'accepted');
run('noisy-twelve-uses', charter({noise: 1, accuracy: 4, intendedUses: 12}), 'accepted');
run('undeclared-quadratic-drift', charter({actualDrift: 'quadratic'}), 'rejected');
run('quadratic-reconstruction', charter({actualDrift: 'quadratic', driftScope: 'quadratic'}), 'accepted');
run('non-updatable-memory', charter({memory: 6, operations: ['flip-z', 'flip-x']}), 'rejected');
run('wrong-location', charter({topology: 'wrong'}), 'rejected');
run('staging-enabled', charter({topology: 'staged'}), 'accepted');
run('hidden-private-coupling', charter({hiddenCoupling: true}), 'rejected');
run('exhausted-search', charter({budget: {...DEFAULT_CHARTER.budget, search: 5}}), 'inconclusive');
run('stronger-checkpoint', charter({checkpoints: ['safety', 'sterile']}), 'accepted', base);
run('stronger-four-control-successor', charter({controls: 4, memory: 16, operations: ['flip-z', 'flip-w']}), 'accepted', base);
const oldRoute = run('route-before-change', charter({faultHypotheses: ['clear', 'left']}), 'accepted');
run('equal-profiles-current-route', charter({faultHypotheses: ['clear', 'right']}), 'accepted', oldRoute);
const second = run('lineage-generation-two', charter({}), 'accepted', base);
run('lineage-generation-three', charter({}), 'accepted', second);
const summary = {schema: 'discovery-lab-public-campaign-bank/v1',
    scope: 'Public authored supplied-model cases, not protected holdouts or physical measurements.',
    runtime: process.version, sourceSha256: sources, count: records.length, records};
if (output) {
    writeEvidence('summary.json', JSON.stringify(summary, null, 2) + '\n');
    writeEvidence('elapsed-receipts.json', JSON.stringify({schema: 'discovery-lab-wall-clock-receipts/v1',
        receipts: elapsedReceipts}, null, 2) + '\n');
    console.log(JSON.stringify({evidenceDirectory: output, count: records.length, summary: 'summary.json',
        elapsedReceipt: 'elapsed-receipts.json', reportDirectory: 'reports'}));
} else console.log(JSON.stringify({...summary, elapsedReceipt: {schema: 'discovery-lab-wall-clock-receipts/v1',
    receipts: elapsedReceipts}}, null, 2));
