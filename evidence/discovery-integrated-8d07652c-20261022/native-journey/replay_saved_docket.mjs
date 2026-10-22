// SPDX-License-Identifier: Apache-2.0
// Portable replay of one fixed saved evidence packet. No native receiver reruns.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createHash} from 'node:crypto';

const FIXED = Object.freeze({
  zipSha256: '6c8c0d8283505101078f63a79d8c03144b3ee550bc27f265b027bbd5d55f9314',
  checksumsSha256: '486b9312a1d11b33f379e250be382ce68ef28999ad704bfdc9b2b3abb958feac',
  manifestSha256: '28e4f16d9e9f469f429eba52f99ed9be3a142ede41b8ec9ac72dec3fb57701c8',
  reportSha256: 'ae3a121cf9e39efa72c756ee70564d941a1b8cb6ea436ff73e37c459ddd2f0a0',
  catalogSha256: '9cddd00ed38a3500efeaac8977bf3db46363face0cfe56e713ec91750662e09a',
  graphSha256: '8d3575ece582c158c30f3cc1c5f438b9b32ad2a31f190d6867acf9712beedad5',
  alphaRepository: 'MontrealAI/AGI-Alpha-Agent-v0',
  alphaCommit: 'cde3010e1e137c49885477f1f514ece6efec0fdd',
  alphaTree: 'dca53a253eae34c67ee7ea7ad0dffd264239bd41',
  sourceHash: '644258ac21cc938aff861d02ad728e8f3c9716f6ea78700acc35e4d7400eebf2',
  missionId: 'capability-511cd038-a94f-4dc1-9303-c69974db703c',
  workspaceHead: '1d3796e068c5e3723835e096366eb2e222dc6f610dc0353bdb402160c3b0f0b7',
  workspaceSha256: '4b4a5b025c0df02137e278f4f5ebede79b70a6c3eddd49a4c6dca9bfb72abec5',
  docketSha256: '7f526e3bb61a03be0658c5601d66c04aec615399c25d1f9e34ed71b88a5102cf',
  payloadFiles: 146,
  payloadBytes: 15_966_009,
  totalFiles: 147,
});
const RECEIVERS = Object.freeze({
  manager: {repository: 'MontrealAI/AGIJobManager', commit: '68d1d3cae2e6f2d46c21e8e73311d309b2b307fd',
    tree: 'c96140e3e0db9e47a68cab5883bb900ce9670912',
    adapter: 'scripts/integrations/discovery-lab-work-request.mjs', contract: 'scripts/integrations/discovery-lab-contract.mjs',
    adapterSha256: 'da307c2d0621a2f323d60c56dfec01d2fda2b72b753939657ea303d619d68e43'},
  jobs: {repository: 'MontrealAI/AGIJobsv0', commit: '285034830b6cddc47c7e1002ee85a8b008b9763d',
    tree: '6e7630783248ca95777f92a6729942caebe909df',
    adapter: 'integrations/alpha-agent/discovery-lab-work-request.mjs', contract: 'integrations/alpha-agent/discovery-lab-contract.mjs',
    adapterSha256: '337fabca02ece2a25b8cc50e56fea5bf5338f2b6f18343eb4a3353a634aefec4'},
  fleet: {repository: 'MontrealAI/AGI-Fleet-Linux', commit: '0dd352fdd2b1af00bc8358e0ac7f96682fd6f796',
    tree: '79415af24ebf57d30981f841f13b7969e4193502',
    adapter: 'discovery-lab/receiver.mjs', contract: 'discovery-lab/contract.mjs',
    adapterSha256: '55000194e7743dc9725d32a516287fec6bd7e0fc42bd36bf26c1665975f734cd'},
});
const CONTRACT_SHA256 = '98c8de8ce2774b7650bf4ee11eeedfb0a69b75fa6d1b080ef823637d77d0ab47';
const sha = raw => createHash('sha256').update(raw).digest('hex');
const json = raw => JSON.parse(raw.toString('utf8'));
const safeName = name => typeof name === 'string' && name.length > 0 && name.length <= 4096
  && !path.posix.isAbsolute(name) && !/[\u0000-\u0020\u007f\\]/.test(name)
  && name.split('/').every(part => part && !['.', '..'].includes(part));
const inside = (root, target) => {const rel = path.relative(root, target); return rel === '' || (!rel.startsWith('..' + path.sep) && rel !== '..' && !path.isAbsolute(rel));};

/** Capture bounded regular bytes; code later runs from owned buffers, not paths. */
function readRegular(root, name) {
  assert.ok(safeName(name), 'Unsafe evidence path');
  const target = path.join(root, ...name.split('/'));
  assert.equal(fs.realpathSync(target), target, 'Symlinked evidence path or ancestor');
  const fd = fs.openSync(target, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const before = fs.fstatSync(fd);
    assert.ok(before.isFile() && before.size <= 4_000_000, 'Nonregular or oversized evidence member');
    const raw = Buffer.alloc(before.size + 1); let count = 0;
    while (count < raw.length) {const n = fs.readSync(fd, raw, count, raw.length - count, null); if (!n) break; count += n;}
    const after = fs.fstatSync(fd), current = fs.lstatSync(target);
    assert.equal(count, before.size, 'Evidence changed while captured');
    for (const key of ['dev', 'ino', 'mode', 'size', 'mtimeMs', 'ctimeMs']) assert.equal(after[key], before[key], 'Evidence changed while captured');
    for (const key of ['dev', 'ino', 'mode', 'size']) assert.equal(current[key], before[key], 'Evidence path changed while captured');
    return raw.subarray(0, count);
  } finally {fs.closeSync(fd);}
}
function inventory(root) {
  const names = [];
  function walk(directory, prefix = '') {
    for (const item of fs.readdirSync(directory, {withFileTypes: true})) {
      const name = prefix + item.name, target = path.join(directory, item.name), info = fs.lstatSync(target);
      assert.ok(safeName(name) && !info.isSymbolicLink(), 'Unsupported evidence path');
      if (info.isDirectory()) walk(target, name + '/');
      else {assert.ok(info.isFile(), 'Special evidence member'); names.push(name); assert.ok(names.length <= FIXED.totalFiles);}
    }
  }
  walk(root); return names.sort();
}
function verifyAll(root, control) {
  assert.equal(control.schema, 'bounded-cli-evidence-file-checksums/v1');
  assert.equal(control.files.length, FIXED.payloadFiles);
  const names = new Set(), captured = new Map(); let total = 0;
  for (const item of control.files) {
    assert.deepEqual(Object.keys(item).sort(), ['bytes', 'path', 'sha256']);
    assert.ok(safeName(item.path) && item.path !== 'evidence-file-checksums.json' && !names.has(item.path)); names.add(item.path);
    assert.ok(Number.isSafeInteger(item.bytes) && item.bytes >= 0 && item.bytes <= 4_000_000 && /^[a-f0-9]{64}$/.test(item.sha256));
    const raw = readRegular(root, item.path); assert.equal(raw.length, item.bytes, item.path); assert.equal(sha(raw), item.sha256, item.path);
    total += raw.length; assert.ok(total <= FIXED.payloadBytes); captured.set(item.path, raw);
  }
  assert.equal(total, FIXED.payloadBytes);
  assert.deepEqual(inventory(root), [...names, 'evidence-file-checksums.json'].sort(), 'Missing or extra evidence files');
  return captured;
}
let boundary;
try {
  assert.equal(process.argv.length, 4, 'Usage: node --experimental-vm-modules replay_saved_docket.mjs /absolute/extracted-evidence /absolute/absent-result.json');
  const [input, output] = process.argv.slice(2);
  assert.ok(path.isAbsolute(input) && path.isAbsolute(output), 'Explicit absolute input and output paths are required');
  const root = path.resolve(input), resultPath = path.resolve(output);
  assert.equal(fs.realpathSync(root), root, 'Evidence root must not traverse symlinks');
  assert.ok(fs.lstatSync(root).isDirectory());
  assert.ok(!inside(root, resultPath), 'Result must be outside the evidence directory');
  assert.equal(fs.realpathSync(path.dirname(resultPath)), path.dirname(resultPath), 'Result parent must exist without symlinks');
  assert.ok(!fs.existsSync(resultPath), 'Result must be an absent path');
  assert.equal(typeof vm.SourceTextModule, 'function', 'Use the --experimental-vm-modules Node flag');

  // Authenticate the complete input inventory before importing any captured code.
  const controlRaw = readRegular(root, 'evidence-file-checksums.json'); assert.equal(sha(controlRaw), FIXED.checksumsSha256);
  const control = json(controlRaw), captured = verifyAll(root, control);
  for (const [name, expected] of [['exact-source-manifest.json', FIXED.manifestSha256], ['report.json', FIXED.reportSha256],
    ['captured/module-closure.mjs', FIXED.graphSha256], ['workspace.json', FIXED.workspaceSha256], ['docket.json', FIXED.docketSha256],
    ['captured/alpha/docs/successor/capabilities/sources.json', FIXED.catalogSha256]]) assert.equal(sha(captured.get(name)), expected, name);
  const manifest = json(captured.get('exact-source-manifest.json')), originalReport = json(captured.get('report.json'));
  assert.equal(manifest.schema, 'alpha-41-cli-journey-exact-source/v1'); assert.equal(manifest.authority, 'none');
  for (const [key, expected] of [['repository', FIXED.alphaRepository], ['commit', FIXED.alphaCommit], ['tree', FIXED.alphaTree], ['sourceHash', FIXED.sourceHash], ['catalogCount', 41]]) assert.equal(manifest.alpha[key], expected);
  for (const [key, expected] of [['alphaCommit', FIXED.alphaCommit], ['alphaTree', FIXED.alphaTree], ['sourceHash', FIXED.sourceHash],
    ['missionId', FIXED.missionId], ['workspaceHead', FIXED.workspaceHead], ['workspaceSha256', FIXED.workspaceSha256], ['docketSha256', FIXED.docketSha256], ['eventCount', 23], ['authority', 'none']]) assert.equal(originalReport[key], expected);
  assert.equal(manifest.graph.sourceCommit, '40c2c6b540dcfcf4c7e9cd0f7bb2e77cab785b2c'); assert.equal(manifest.graph.sha256, FIXED.graphSha256);
  const catalog = json(captured.get('captured/alpha/docs/successor/capabilities/sources.json'));
  assert.equal(catalog.schema, 'successor-capability-source/v1'); assert.equal(catalog.sourceHash, FIXED.sourceHash); assert.equal(Object.keys(catalog.sources).length, 41);
  assert.equal(sha(JSON.stringify(Object.fromEntries(Object.keys(catalog.sources).sort().map(k => [k, catalog.sources[k]])))), FIXED.sourceHash);
  assert.equal(manifest.alpha.files.length, 43);
  const sourceNames = new Set(), modules = new Map();
  for (const item of manifest.alpha.files) {
    const name = 'captured/alpha/' + item.path, raw = captured.get(name);
    assert.ok(safeName(item.path) && !sourceNames.has(name) && raw); sourceNames.add(name);
    assert.equal(raw.length, item.bytes); assert.equal(sha(raw), item.sha256); assert.ok(['100644', '100755'].includes(item.mode));
    if (Object.hasOwn(catalog.sources, item.path)) assert.equal(item.sha256, catalog.sources[item.path]);
    if (item.path.endsWith('.mjs')) modules.set(item.path, raw);
  }
  for (const name of Object.keys(catalog.sources)) assert.ok(sourceNames.has('captured/alpha/' + name));
  assert.equal(modules.size, 31);
  const expectedSources = [{repository: FIXED.alphaRepository, commit: FIXED.alphaCommit, tree: FIXED.alphaTree,
    files: manifest.alpha.files.map(({path, sha256}) => ({path, sha256}))}];
  const expectedReceiverSources = [];
  for (const [key, fixed] of Object.entries(RECEIVERS)) {
    const declared = manifest.receivers[key];
    for (const field of ['repository', 'commit', 'tree', 'adapter', 'contract', 'adapterSha256']) assert.equal(declared[field], fixed[field]);
    assert.equal(declared.files.length, 2);
    const expectedFiles = [{path: fixed.adapter, sha256: fixed.adapterSha256}, {path: fixed.contract, sha256: CONTRACT_SHA256}];
    assert.deepEqual(declared.files.map(({path, sha256}) => ({path, sha256})), expectedFiles);
    for (const item of declared.files) {
      const name = 'captured/' + key + '/' + item.path, raw = captured.get(name); assert.ok(raw && !sourceNames.has(name)); sourceNames.add(name);
      assert.equal(raw.length, item.bytes); assert.equal(sha(raw), item.sha256); assert.ok(['100644', '100755'].includes(item.mode));
    }
    expectedSources.push({repository: fixed.repository, commit: fixed.commit, tree: fixed.tree, files: expectedFiles});
    expectedReceiverSources.push({repository: fixed.repository, commit: fixed.commit, tree: fixed.tree, adapterSha256: fixed.adapterSha256, contractSha256: CONTRACT_SHA256});
  }
  assert.equal(sourceNames.size, 49); sourceNames.add('captured/module-closure.mjs');
  assert.deepEqual([...captured.keys()].filter(x => x.startsWith('captured/')).sort(), [...sourceNames].sort());
  const attachments = json(captured.get('docket-attachments.json'));
  assert.deepEqual(attachments.sources, expectedSources); assert.deepEqual(attachments.receipts, []);
  assert.equal(attachments.missionId, FIXED.missionId); assert.equal(attachments.workspaceHead, FIXED.workspaceHead);
  const options = {expectedSources, expectedReceiverSources, expectedMissionId: FIXED.missionId, expectedWorkspaceHead: FIXED.workspaceHead};

  // Only the authenticated fixed helper and Alpha replay modules can execute.
  // SourceTextModule constructs parser records without linking/evaluating input.
  const graphRaw = captured.get('captured/module-closure.mjs');
  const graph = await import('data:text/javascript;base64,' + graphRaw.toString('base64'));
  const parserRecords = graph.staticDependencyRecords([...modules].map(([name, raw]) => ({name, source: raw.toString('utf8')})));
  assert.deepEqual(parserRecords, json(captured.get('alpha-static-module-records.json')));
  graph.checkDependencyRecords(parserRecords, new Set(modules.keys()));
  const entries = ['examples/successor-capability/workspace.mjs', 'examples/successor-capability/discovery-lab-docket.mjs'];
  boundary = graph.createModuleBoundary(path.join(root, 'captured/alpha'), modules, entries);
  const [workspace, docket] = await Promise.all(entries.map(name => boundary.importModule(name)));
  const workspaceRaw = captured.get('workspace.json').toString('utf8'), docketRaw = captured.get('docket.json').toString('utf8');
  const reopened = await workspace.parseWorkspace(workspaceRaw), inspected = await workspace.inspectWorkspace(reopened);
  assert.equal(reopened.missionId, FIXED.missionId); assert.equal(inspected.head, FIXED.workspaceHead); assert.equal(reopened.events.length, 23);
  assert.equal(workspace.canonical(reopened), workspaceRaw); assert.deepEqual(reopened.authority, []); assert.equal(reopened.paymentRoute, 'none');
  assert.deepEqual(inspected.discovery.campaigns.map(x => x.state), ['accepted', 'accepted']);
  for (const campaign of inspected.discovery.campaigns) {
    assert.equal(campaign.bindings.sourceDigest, FIXED.sourceHash); assert.equal(campaign.lineageQualified, true);
    assert.deepEqual(campaign.result.stages.map(x => x.status), Array(6).fill('accepted'));
  }
  const evidence = inspected.discovery.attachments;
  assert.equal(evidence.filter(x => x.kind === 'receiver-receipt').length, 13);
  assert.equal(evidence.find(x => x.kind === 'future-evaluation').record.runs.length, 42);
  const real = evidence.find(x => x.kind === 'real-task-contract').record;
  assert.equal(real.operationalState, 'NOT_RUN'); assert.equal(real.artifact, null); assert.deepEqual(real.checks, []);
  const verification = await docket.verifyDiscoveryDocket(docketRaw, options); assert.equal(verification.verified, true);
  const reexported = await docket.exportDiscoveryDocket(reopened, attachments, options); assert.equal(reexported, docketRaw);
  assert.equal(sha(workspace.canonical(reopened)), FIXED.workspaceSha256); assert.equal(sha(reexported), FIXED.docketSha256);
  const decoded = json(captured.get('docket.json')); assert.equal(Object.keys(decoded.files).length, 13);
  for (const name of docket.DOCKET_PATHS) assert.equal(decoded.files[name], captured.get('docket-sections/' + name).toString('utf8'));
  const costs = JSON.parse(decoded.files['08_cost_ledgers/costs.json']); assert.equal(costs.currenciesCombined, false); assert.equal(costs.totalComplete, false);
  assert.equal(captured.get('reopened-workspace.json').toString('utf8'), workspaceRaw); assert.equal(captured.get('reopened-docket.json').toString('utf8'), docketRaw);
  // Check every input again after semantic replay. Never write inside input.
  assert.equal(sha(readRegular(root, 'evidence-file-checksums.json')), FIXED.checksumsSha256); verifyAll(root, control);
  const result = {schema: 'saved-alpha41-docket-portable-replay/v1', verified: true,
    method: 'Fixed full raw inventory, pinned source manifest/report, direct parse-only module records, owned-byte Alpha workspace/docket semantic replay and exact reexport',
    node: process.version, evidenceDirectory: root, fileCount: FIXED.totalFiles, payloadFiles: FIXED.payloadFiles, payloadBytes: FIXED.payloadBytes,
    checksumManifestSha256: FIXED.checksumsSha256, expectedArchiveSha256: FIXED.zipSha256,
    alphaCommit: FIXED.alphaCommit, alphaTree: FIXED.alphaTree, sourceHash: FIXED.sourceHash, catalogCount: 41,
    missionId: FIXED.missionId, workspaceHead: FIXED.workspaceHead, eventCount: 23, savedNativeReceiptCount: 13, savedFutureOutcomes: 42,
    realTaskOperationalState: 'NOT_RUN', docketSections: 13, workspaceSha256: FIXED.workspaceSha256, docketSha256: FIXED.docketSha256,
    workspaceReopenedByteIdentical: true, docketReexportedByteIdentical: true, fullInputHashesStillMatchAfterReplay: true,
    originalNativeObservationsRerun: false, receiverImplementationsImported: false, importedArtifactOrProposalExecuted: false,
    laterGitIdentityQualified: false, hostedOrReleasedInstalledQualification: false, organizationalAcceptance: false,
    authority: 'none', externalExecution: 'unprovisioned', totalCostComplete: false, verification};
  boundary.close(); boundary = null;
  const raw = JSON.stringify(result, null, 2) + '\n';
  fs.writeFileSync(resultPath, raw, {flag: 'wx', mode: 0o600}); process.stdout.write(raw);
} catch (error) {process.stderr.write(error.message + '\n'); process.exitCode = 1;}
finally {boundary?.close();}
