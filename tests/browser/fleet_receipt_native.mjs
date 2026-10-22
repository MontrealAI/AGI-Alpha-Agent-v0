// SPDX-License-Identifier: Apache-2.0
// Actual native public-source interoperability; never a fixture checker or a service claim.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {parseModuleSources, checkDependencyRecords, ownedTarget, createModuleBoundary} from './fleet_module_boundary.mjs';
import {auditGitConfiguration} from './fleet_git_metadata.mjs';
const ALPHA_ROOT = path.resolve(fileURLToPath(new URL('../../', import.meta.url)));
const FLEET_COMMIT = '0dd352fdd2b1af00bc8358e0ac7f96682fd6f796';
const FLEET_TREE = '79415af24ebf57d30981f841f13b7969e4193502';
const FLEET_FILES = {
    'receiver.mjs': '55000194e7743dc9725d32a516287fec6bd7e0fc42bd36bf26c1665975f734cd',
    'contract.mjs': '98c8de8ce2774b7650bf4ee11eeedfb0a69b75fa6d1b080ef823637d77d0ab47'
};
const sha = value => createHash('sha256').update(value).digest('hex');
const gitEnv = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
Object.assign(gitEnv, {GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_SYSTEM: os.devNull, GIT_CONFIG_GLOBAL: os.devNull,
    GIT_CONFIG_COUNT: '0', GIT_NO_LAZY_FETCH: '1', GIT_TERMINAL_PROMPT: '0', GIT_ATTR_NOSYSTEM: '1', GIT_OPTIONAL_LOCKS: '0'});
const git = (root, ...args) => execFileSync('git', ['--no-replace-objects', '-c', 'protocol.allow=never',
    '-c', 'core.hooksPath=' + os.devNull, '-c', 'core.attributesFile=' + os.devNull, '-C', root, ...args],
    {env: gitEnv, maxBuffer: 8000000, timeout: 15000});
function boundedRegular(filename, limit = 2000000) {
    const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
    try {
        const before = fs.fstatSync(fd, {bigint: true});
        assert.ok(before.isFile() && before.size <= BigInt(limit), 'Bounded regular file required');
        const buffer = Buffer.alloc(limit + 1); let count = 0;
        while (count < buffer.length) {
            const read = fs.readSync(fd, buffer, count, buffer.length - count, count);
            if (!read) break; count += read;
        }
        assert.ok(count <= limit && count === Number(before.size), 'File changed beyond its captured size or input bound');
        const after = fs.fstatSync(fd, {bigint: true});
        assert.ok(before.size === after.size && before.mtimeNs === after.mtimeNs && before.ctimeNs === after.ctimeNs,
            'Input changed while capturing its owned snapshot');
        return Buffer.from(buffer.subarray(0, count));
    } finally { fs.closeSync(fd); }
}
function guardRoot(root) {
    // This acceptance helper requires ordinary independent checkout roots. Read
    // configuration before invoking Git; includes and executable filters are not
    // accepted as an alternative source of installed bytes.
    const directory = path.join(root, '.git');
    assert.ok(fs.lstatSync(directory).isDirectory() && fs.realpathSync(directory) === directory,
        'An ordinary independent Git checkout is required');
    assert.equal(fs.lstatSync(path.join(directory, 'commondir'), {throwIfNoEntry: false}), undefined,
        'A redirected common Git directory is not an ordinary independent root');
    const worktreePath = path.join(directory, 'config.worktree');
    const worktreePresent = fs.lstatSync(worktreePath, {throwIfNoEntry: false}) !== undefined;
    const decode = bytes => new TextDecoder('utf-8', {fatal: true}).decode(bytes);
    const metadata = filename => {
        assert.ok(fs.lstatSync(filename).isFile() && fs.realpathSync(filename) === filename,
            'Git metadata must be regular local files');
        return boundedRegular(filename, 128000);
    };
    const config = metadata(path.join(directory, 'config'));
    const ignored = worktreePresent ? metadata(worktreePath) : null;
    const configuration = auditGitConfiguration(decode(config), ignored === null ? null : decode(ignored));
    const packs = path.join(directory, 'objects/pack');
    assert.ok(!fs.existsSync(packs) || !fs.readdirSync(packs).some(name => name.endsWith('.promisor')),
        'Promisor object packs are not admitted by this read-only source helper');
    return {...configuration, configSha256: sha(config), ignoredWorktreeSha256: ignored === null ? null : sha(ignored)};
}
function regular(root, relative) {
    const filename = path.resolve(root, relative), actual = fs.realpathSync(filename);
    assert.ok(actual === filename && actual.startsWith(root + path.sep) && fs.lstatSync(filename).isFile(), 'Regular source path required');
    return boundedRegular(filename);
}
function capture(root, relative, commit) {
    const value = regular(root, relative);
    const entry = git(root, 'ls-tree', '-z', commit, '--', relative).toString();
    assert.ok(/^100(?:644|755) blob [a-f0-9]{40}\t/.test(entry), 'Regular Git source blob required');
    const executable = Boolean(fs.statSync(path.join(root, relative)).mode & 0o111);
    assert.equal(executable, entry.startsWith('100755 '), 'Installed executable mode changed');
    assert.deepEqual(value, git(root, 'cat-file', 'blob', commit + ':' + relative), relative + ' changed from Git source');
    return value;
}
const [fleetArg, workspacePath, requestPath, outputArg] = process.argv.slice(2);
assert.ok(fleetArg && workspacePath && requestPath && outputArg && process.argv.length === 6,
    'Use FLEET_ROOT BROWSER_WORKSPACE BROWSER_REQUEST ABSENT_OUTPUT');
const fleetRoot = fs.realpathSync(fleetArg), output = path.resolve(outputArg);
assert.ok(path.isAbsolute(fleetArg) && path.isAbsolute(outputArg) && !fs.existsSync(output), 'Explicit source and absent evidence paths required');
const workspaceBytes = boundedRegular(workspacePath), requestBytes = boundedRegular(requestPath), original = requestBytes.toString();
const gitMetadata = {fleet: guardRoot(fleetRoot), alpha: guardRoot(ALPHA_ROOT)};
assert.equal(git(fleetRoot, 'rev-parse', '--show-toplevel').toString().trim(), fleetRoot, 'Fleet must be its own Git root');
assert.equal(git(fleetRoot, 'rev-parse', 'HEAD').toString().trim(), FLEET_COMMIT);
assert.equal(git(fleetRoot, 'rev-parse', 'HEAD^{tree}').toString().trim(), FLEET_TREE);
assert.equal(git(ALPHA_ROOT, 'rev-parse', '--show-toplevel').toString().trim(), ALPHA_ROOT);
const alphaCommit = git(ALPHA_ROOT, 'rev-parse', 'HEAD').toString().trim();
const alphaTree = git(ALPHA_ROOT, 'rev-parse', 'HEAD^{tree}').toString().trim();
const catalog = JSON.parse(capture(ALPHA_ROOT, 'docs/successor/capabilities/sources.json', alphaCommit));
const sourceMap = Object.fromEntries(Object.keys(catalog.sources).sort().map(key => [key, catalog.sources[key]]));
assert.equal(sha(JSON.stringify(sourceMap)), catalog.sourceHash, 'Installed source catalog must reproduce');
const boundarySource = capture(ALPHA_ROOT, 'tests/browser/fleet_module_boundary.mjs', alphaCommit);
const harnessSources = {'tests/browser/fleet_module_boundary.mjs': sha(boundarySource),
    'tests/browser/fleet_git_metadata.mjs': sha(capture(ALPHA_ROOT, 'tests/browser/fleet_git_metadata.mjs', alphaCommit)),
    'tests/browser/fleet_receipt_native.mjs': sha(capture(ALPHA_ROOT, 'tests/browser/fleet_receipt_native.mjs', alphaCommit))};
const snapshot = fs.mkdtempSync(path.join(os.tmpdir(), 'fleet-native-captured-'));
let boundary;
try {
    const allCatalogInputs = new Map();
    for (const [relative, digest] of Object.entries(catalog.sources)) {
        const value = capture(ALPHA_ROOT, relative, alphaCommit); assert.equal(sha(value), digest, relative + ' catalog identity changed');
        allCatalogInputs.set(relative, value);
    }
    const sourceFiles = {}, modules = new Map();
    for (const [relative, value] of allCatalogInputs) if (relative.endsWith('.mjs')) modules.set('alpha/' + relative, value);
    const inspector = 'examples/successor-capability/discovery-lab-inspector.mjs';
    modules.set('alpha/' + inspector, capture(ALPHA_ROOT, inspector, alphaCommit));
    for (const [name, digest] of Object.entries(FLEET_FILES)) {
        const value = capture(fleetRoot, 'discovery-lab/' + name, FLEET_COMMIT);
        assert.equal(sha(value), digest); modules.set('fleet/' + name, value);
    }
    const builtins = {'fleet/receiver.mjs': ['node:crypto', 'node:perf_hooks'], 'fleet/contract.mjs': ['node:crypto']};
    const records = parseModuleSources([...modules].map(([name, value]) => ({name, source: value.toString()})), boundarySource.toString());
    const names = new Set(modules.keys()); checkDependencyRecords(records, names, builtins);
    const recordsByName = new Map(records.map(record => [record.name, record.requests]));
    const entries = ['workspace.mjs', 'discovery-lab-contract.mjs', 'discovery-lab-history.mjs',
        'discovery-lab-receipts.mjs', 'discovery-lab-inspector.mjs'].map(name => 'alpha/examples/successor-capability/' + name);
    entries.push('fleet/receiver.mjs');
    const captured = new Map();
    function visit(name) {
        if (captured.has(name)) return;
        const value = modules.get(name); assert.ok(value, 'Every native module must have owned captured bytes');
        captured.set(name, value); sourceFiles[name] = sha(value);
        for (const request of recordsByName.get(name)) {
            const target = ownedTarget(request, name, names, builtins);
            if (!target.startsWith('node:')) visit(target);
        }
    }
    for (const name of entries) visit(name);
    // Static parsing checks the declared graph. The lifetime resolver/load boundary
    // separately denies every uncaptured target, including computed dynamic imports.
    boundary = createModuleBoundary(snapshot, captured, entries, builtins);
    const module = name => boundary.importModule('alpha/examples/successor-capability/' + name);
    const contract = await module('discovery-lab-contract.mjs'), workspace = await module('workspace.mjs');
    const history = await module('discovery-lab-history.mjs'), receipts = await module('discovery-lab-receipts.mjs');
    const {createInspector} = await module('discovery-lab-inspector.mjs');
    const {reviewDiscoveryRequest} = await boundary.importModule('fleet/receiver.mjs');
    const value = await workspace.parseWorkspace(workspaceBytes.toString()), inspection = await workspace.inspectWorkspace(value);
    assert.equal(inspection.discovery.active, null, 'Only completed saved campaigns can be selected');
    const installedSources = {sourceDigest: catalog.sourceHash,
        modelDigest: catalog.sources['examples/successor-capability/discovery-lab.mjs'],
        evaluatorDigest: catalog.sources['examples/successor-capability/discovery-lab-checker.mjs']};
    const candidates = inspection.discovery.campaigns.filter(row => row.state === 'accepted' && row.lineageQualified !== false
        && Object.entries(installedSources).every(([key, digest]) => row.bindings[key] === digest));
    assert.equal(candidates.length, 1, 'Operator selects the unique current accepted browser campaign');
    const selected = candidates[0], capacity = {acquisitions: 0, search: 0, checking: 20000, memoryBytes: 10000000,
        storageBytes: 4000000, workerCapacity: 4, installations: 0, elapsedMs: 120000};
    for (let row = selected; row; row = row.parent) for (const key of ['acquisitions', 'search', 'checking', 'installations']) capacity[key] += row.charter.budget[key];
    const expected = await history.workRequest(selected, 'USDC', capacity), request = await contract.parseWorkRequest(original);
    assert.equal(contract.canonical(request), contract.canonical(expected), 'Exact browser draft must match independently reconstructed bridge policy');
    const runtime = {version: process.version, flags: process.execArgv, platform: process.platform, arch: process.arch, binarySha256: sha(fs.readFileSync(process.execPath))};
    const runtimeDigest = await contract.payloadDigest({runtime, sourceFiles, harnessSources, sourceHash: catalog.sourceHash});
    const installed = {executorId: 'captured-public-fleet-local-review', runtimeDigest, currentRuntimeDigest: runtimeDigest,
        expected: Object.fromEntries(contract.BINDING_KEYS.map(key => [key, selected.bindings[key]])),
        expectedCommission: Object.fromEntries(['id', 'branch', 'route'].map(key => [key, expected.commission[key]])),
        stages: contract.STAGES, resourceCapacity: capacity, inspectCampaign: createInspector(installedSources)};
    const receipt = await reviewDiscoveryRequest(original, installed);
    assert.equal(receipt.state, 'accepted-local-review'); assert.equal(receipt.remoteExecution, 'unprovisioned'); assert.equal(receipt.authority, 'none');
    const source = {repository: 'MontrealAI/AGI-Fleet-Linux', commit: FLEET_COMMIT, tree: FLEET_TREE,
        adapterSha256: FLEET_FILES['receiver.mjs'], contractSha256: FLEET_FILES['contract.mjs']};
    const envelope = {schema: 'agi-fleet/discovery-review-return/v1', original, receiptRaw: JSON.stringify(receipt, null, 2)};
    const wrapper = {raw: JSON.stringify(envelope), source}, context = receipts.makeReceiverContext(selected);
    const checked = await receipts.inspectReceiverReceipt(wrapper, context, {expectedReceiverSources: [source]});
    const variants = [];
    for (const [name, change] of Object.entries({executor: r => {r.executorId = 'other-unattested-executor';},
        runtime: r => {r.runtimeDigest = '0'.repeat(64);}, elapsed: r => {r.resourceUsed.elapsedMs += 3;},
        memory: r => {r.resourceUsed.memoryBytes += 5;}, outcome: r => {r.state = 'inconclusive'; r.reasons = ['ELAPSED_REPLAY_CHECK_INCOMPLETE'];}})) {
        const r = JSON.parse(envelope.receiptRaw), nativeStorage = r.resourceUsed.storageBytes - Buffer.byteLength(contract.canonical(r)); change(r);
        for (let i = 0; i < 12; i++) r.resourceUsed.storageBytes = nativeStorage + Buffer.byteLength(contract.canonical(r));
        const variant = {raw: JSON.stringify({...envelope, receiptRaw: JSON.stringify(r)}), source};
        const observed = await receipts.inspectReceiverReceipt(variant, context, {expectedReceiverSources: [source]});
        assert.equal(observed.receiptId, checked.receiptId); variants.push({name, wrapper: variant});
    }
    variants.push({name: 'raw-framing', wrapper: {raw: JSON.stringify(envelope, null, 2), source}});
    const compactReceipt = {raw: JSON.stringify({...envelope, receiptRaw: JSON.stringify(receipt)}), source};
    assert.equal((await receipts.inspectReceiverReceipt(compactReceipt, context, {expectedReceiverSources: [source]})).receiptId, checked.receiptId);
    variants.push({name: 'receipt-framing', wrapper: compactReceipt});
    const reframedRequest = JSON.stringify(Object.fromEntries(Object.entries(request).reverse())), reframedReceipt = JSON.parse(envelope.receiptRaw);
    const nativeStorage = reframedReceipt.resourceUsed.storageBytes - Buffer.byteLength(contract.canonical(reframedReceipt));
    reframedReceipt.requestDigest = sha(reframedRequest);
    for (let i = 0; i < 12; i++) reframedReceipt.resourceUsed.storageBytes = nativeStorage + Buffer.byteLength(contract.canonical(reframedReceipt));
    const reframed = {raw: JSON.stringify({...envelope, original: reframedRequest, receiptRaw: JSON.stringify(reframedReceipt)}), source};
    assert.equal((await receipts.inspectReceiverReceipt(reframed, context, {expectedReceiverSources: [source]})).receiptId, checked.receiptId);
    variants.push({name: 'request-framing', wrapper: reframed});
    variants.push({name: 'source-repository', wrapper: {...wrapper, source: {...source, repository: 'MontrealAI/AGIJobManager'}}});
    const unauthorized = JSON.parse(envelope.receiptRaw); unauthorized.authority = 'promote';
    variants.push({name: 'forged-authority', wrapper: {raw: JSON.stringify({...envelope, receiptRaw: JSON.stringify(unauthorized)}), source}});
    const badEnvelope = {...envelope, original: envelope.original.replace(request.missionId, 'capability-00000000-0000-4000-8000-000000000000')};
    variants.push({name: 'swapped-mission', wrapper: {raw: JSON.stringify(badEnvelope), source}});
    fs.mkdirSync(output);
    fs.writeFileSync(path.join(output, 'wrapper.json'), JSON.stringify(wrapper, null, 2) + '\n');
    for (const item of variants) fs.writeFileSync(path.join(output, item.name + '.json'), JSON.stringify(item.wrapper, null, 2) + '\n');
    const report = {schema: 'actual-browser-fleet-native-return/v1', alphaCommit, alphaTree, sourceHash: catalog.sourceHash,
        fleetSource: source, runtime, runtimeDigest, sourceFiles, harnessSources, moduleBoundarySha256: sha(boundarySource),
        allCatalogInputsVerified: allCatalogInputs.size, gitMetadata,
        workspaceSha256: sha(workspaceBytes), requestSha256: sha(requestBytes),
        missionId: value.missionId, campaignDigest: selected.campaignDigest, receipt: checked, variants: variants.map(item => item.name),
        scope: 'Actual captured public Fleet source and Alpha inspector; no installed released Fleet service, remote execution or institutional independence',
        authority: 'none', totalComplete: false};
    fs.writeFileSync(path.join(output, 'native-proof.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({passed: true, receiptId: checked.receiptId, variants: report.variants.length, sourceHash: catalog.sourceHash}));
} finally { boundary?.close(); fs.rmSync(snapshot, {recursive: true, force: true}); }
