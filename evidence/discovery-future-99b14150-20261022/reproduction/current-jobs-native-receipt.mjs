// SPDX-License-Identifier: Apache-2.0
// Local exact-source interoperability exercise; no installed-release or publication claim.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const ALPHA = '/workspace/scratch/32717074a7f1/alpha';
const JOBS = '/workspace/scratch/32717074a7f1/jobs-successor';
const JOBS_COMMIT = '852420e82ae3f5bbf0c397a4c1d550d210d4916f';
const JOBS_TREE = 'cb29f676e1e6d43f0d19ed72b34c248bca9a3af1';
const jobsFiles = {
    'integrations/alpha-agent/discovery-lab-work-request.mjs': '337fabca02ece2a25b8cc50e56fea5bf5338f2b6f18343eb4a3353a634aefec4',
    'integrations/alpha-agent/discovery-lab-contract.mjs': '98c8de8ce2774b7650bf4ee11eeedfb0a69b75fa6d1b080ef823637d77d0ab47'
};
const sha = raw => createHash('sha256').update(raw).digest('hex');
function boundedFile(name, limit = 2_000_000) {
    const stat = fs.lstatSync(name);
    assert.ok(stat.isFile() && !stat.isSymbolicLink() && stat.size <= limit, 'Expected bounded regular file: ' + name);
    return fs.readFileSync(name);
}
assert.equal(process.argv.length, 5, 'Usage: node current-jobs-native-receipt.mjs workspace.json jobs-draft.json output-wrapper.json');
const [workspaceFile, requestFile, outputFile] = process.argv.slice(2).map(item => path.resolve(item));
assert.ok(!fs.existsSync(outputFile) && !fs.existsSync(outputFile + '.provenance.json'), 'Retain prior output; select fresh paths.');
const workspaceRaw = boundedFile(workspaceFile).toString('utf8'), requestRaw = boundedFile(requestFile).toString('utf8');
const catalogRaw = boundedFile(path.join(ALPHA, 'docs/successor/capabilities/sources.json'));
const catalog = JSON.parse(catalogRaw);
assert.equal(catalog.schema, 'successor-capability-source/v1');
assert.ok(Object.keys(catalog.sources).length <= 256);
const sortedSources = Object.fromEntries(Object.entries(catalog.sources).sort(([a], [b]) => a.localeCompare(b, 'en')));
// Python's sort_keys order is ASCII for these repository paths, not locale collation.
const ordered = {}; for (const key of Object.keys(catalog.sources).sort()) ordered[key] = catalog.sources[key];
assert.equal(sha(Buffer.from(JSON.stringify(ordered))), catalog.sourceHash, 'Generated catalog identity differs.');
const alphaSnapshot = fs.mkdtempSync(path.join(os.tmpdir(), 'alpha-current-receipt-'));
const jobsSnapshot = fs.mkdtempSync(path.join(os.tmpdir(), 'jobs-public-receipt-'));
function capture(root, destination, name, expected) {
    assert.ok(name && !path.isAbsolute(name) && !name.includes('\\') && name.split('/').every(part => part && !['.', '..'].includes(part)));
    const raw = boundedFile(path.join(root, name));
    assert.equal(sha(raw), expected, 'Current source bytes differ: ' + name);
    fs.mkdirSync(path.dirname(path.join(destination, name)), {recursive: true});
    fs.writeFileSync(path.join(destination, name), raw, {flag: 'wx', mode: 0o600});
    return raw;
}
try {
    assert.equal(execFileSync('git',['--no-replace-objects','-C',JOBS,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),JOBS_COMMIT);
    assert.equal(execFileSync('git',['--no-replace-objects','-C',JOBS,'rev-parse','HEAD^{tree}'],{encoding:'utf8'}).trim(),JOBS_TREE);
    for (const [name, digest] of Object.entries(sortedSources)) capture(ALPHA, alphaSnapshot, name, digest);
    const inspectorPath = 'examples/successor-capability/discovery-lab-inspector.mjs';
    const inspectorRaw = boundedFile(path.join(ALPHA, inspectorPath));
    if (!Object.hasOwn(catalog.sources, inspectorPath)) capture(ALPHA, alphaSnapshot, inspectorPath, sha(inspectorRaw));
    for (const [name, digest] of Object.entries(jobsFiles)) capture(JOBS, jobsSnapshot, name, digest);
    const load = (root, name) => import(pathToFileURL(path.join(root, name)).href);
    const [workspace, history, contract, {createInspector}, jobs] = await Promise.all([
        load(alphaSnapshot, 'examples/successor-capability/workspace.mjs'),
        load(alphaSnapshot, 'examples/successor-capability/discovery-lab-history.mjs'),
        load(alphaSnapshot, 'examples/successor-capability/discovery-lab-contract.mjs'),
        load(alphaSnapshot, inspectorPath),
        load(jobsSnapshot, 'integrations/alpha-agent/discovery-lab-work-request.mjs')
    ]);
    const installedSources = {modelDigest: catalog.sources['examples/successor-capability/discovery-lab.mjs'],
        sourceDigest: catalog.sourceHash, evaluatorDigest: catalog.sources['examples/successor-capability/discovery-lab-checker.mjs']};
    const saved = await workspace.parseWorkspace(workspaceRaw), inspection = await workspace.inspectWorkspace(saved);
    const request = await contract.parseWorkRequest(requestRaw);
    const same = (left, right) => contract.canonical(left) === contract.canonical(right);
    const selected = inspection.discovery.campaigns.find(item => same(item.bindings,
        Object.fromEntries(contract.BINDING_KEYS.map(key => [key, request[key]]))));
    assert.ok(selected && selected.state === 'accepted' && selected.lineageQualified !== false, 'Current accepted campaign is absent.');
    assert.ok(Object.entries(installedSources).every(([key, value]) => selected.bindings[key] === value), 'Campaign is not bound to the current captured Alpha sources.');
    const limits = {acquisitions: 0, search: 0, checking: jobs.DISCOVERY_LAB_ADMISSION_CHECKS + contract.DISCOVERY_LAB_INSPECTION_CHECKS,
        memoryBytes: 10_000_000, storageBytes: 4_000_000, workerCapacity: 4, installations: 0, elapsedMs: 120_000};
    for (let item = selected; item; item = item.parent) for (const key of ['acquisitions', 'search', 'checking', 'installations']) limits[key] += item.charter.budget[key];
    const expected = await history.workRequest(selected, 'AGIALPHA', limits);
    assert.ok(same(request, expected), 'Actual browser request differs from independently reconstructed context and caps.');
    const receipt = await jobs.receiveDiscoveryLabWorkRequest(requestRaw, {
        expectedBindings: Object.fromEntries(contract.BINDING_KEYS.map(key => [key, selected.bindings[key]])),
        expectedCommission: Object.fromEntries(['id', 'branch', 'route'].map(key => [key, expected.commission[key]])),
        inspectCampaign: createInspector(installedSources)
    });
    assert.equal(receipt.original, requestRaw); assert.equal(receipt.authority, 'none');
    const wrapper = {raw: JSON.stringify(receipt), source: {repository: 'MontrealAI/AGIJobsv0',
        commit: JOBS_COMMIT, tree: JOBS_TREE, ...receipt.source}};
    const {inspectReceiverReceipt, makeReceiverContext} = await load(alphaSnapshot, 'examples/successor-capability/discovery-lab-receipts.mjs');
    const checked = await inspectReceiverReceipt(wrapper, makeReceiverContext(selected), {expectedReceiverSources: [wrapper.source]});
    fs.writeFileSync(outputFile, JSON.stringify(wrapper), {flag: 'wx'});
    const provenance = {schema: 'successor/current-source-native-receipt-exercise/v1',
        scope: 'Actual captured current Alpha source modules and public Jobs852 receiver. Not installed-package, hosted, release, public deployment or operational acceptance.',
        workspaceFileSha256: sha(Buffer.from(workspaceRaw)), requestFileSha256: sha(Buffer.from(requestRaw)),
        wrapperFileSha256: sha(Buffer.from(JSON.stringify(wrapper))), alphaCatalogSha256: sha(catalogRaw),
        alphaSourceHash: catalog.sourceHash, alphaInspectorSha256: sha(inspectorRaw), installedSources,
        jobsCommit: JOBS_COMMIT, jobsTree: JOBS_TREE, jobsFiles,
        campaignDigest: selected.campaignDigest, missionId: saved.missionId, workspaceHead: inspection.head,
        state: receipt.state, receiptId: checked.receiptId, receiptRawSha256: checked.receiptDigest,
        authority: 'none', externalExecution: 'unprovisioned', immutablePublicAlphaSourceQualification: false};
    fs.writeFileSync(outputFile + '.provenance.json', JSON.stringify(provenance, null, 2) + '\n', {flag: 'wx'});
    console.log(JSON.stringify({outputFile, state: receipt.state, receiptId: checked.receiptId, alphaSourceHash: catalog.sourceHash,
        scope: provenance.scope, authority: 'none'}));
} finally {
    fs.rmSync(alphaSnapshot, {recursive: true, force: true}); fs.rmSync(jobsSnapshot, {recursive: true, force: true});
}
