// SPDX-License-Identifier: Apache-2.0
// Additive local-EVM adapter. Existing Alpha contracts and fixtures are unchanged.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
// A caller cannot substitute an accepted:true object for a fresh checker run.
// The captured, validated package remains private after checking.
const checkedPackages = new WeakMap();

const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const hex = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const canonical = value => {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (object(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  return JSON.stringify(value);
};
function keys(value, names, label) {
  assert(object(value), `${label}: object required`);
  assert.deepEqual(Object.keys(value).sort(), [...names].sort(), `${label}: exact fields required`);
}
function readBytes(filename, limit = 4 * 1024 * 1024) {
  const before = fs.lstatSync(filename);
  assert(before.isFile() && before.size <= limit, 'Bounded regular file required');
  const fd = fs.openSync(filename, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
  try {
    const opened = fs.fstatSync(fd);
    assert(opened.isFile() && opened.dev === before.dev && opened.ino === before.ino, 'File changed before capture');
    const bytes = fs.readFileSync(fd);
    assert(bytes.length <= limit, 'File exceeds byte bound');
    return bytes;
  } finally { fs.closeSync(fd); }
}
function canonicalJson(bytes, label) {
  const value = JSON.parse(bytes.toString('utf8'));
  const normalized = canonical(value);
  assert(bytes.equals(Buffer.from(normalized)) || bytes.equals(Buffer.from(normalized + '\n')), `${label}: canonical JSON required`);
  return value;
}
function validatePackage({ artifactBytes, proofBytes, inputBytes, criteriaBytes, checkerBytes, checkerSha256, criteriaSha256, candidateBytes = null, manifestBytes = null, manifestSha256 = null }) {
  assert(hex(checkerSha256) && hex(criteriaSha256), 'Independently supplied frozen checker/criteria hashes required');
  assert.equal(sha256(checkerBytes), checkerSha256, 'Frozen checker hash mismatch');
  assert.equal(sha256(criteriaBytes), criteriaSha256, 'Frozen criteria hash mismatch');
  const artifact = canonicalJson(artifactBytes, 'artifact');
  const proof = JSON.parse(proofBytes.toString('utf8'));
  keys(artifact, ['schema', 'missionId', 'capabilityHash', 'inputHash', 'output', 'currentProof', 'authority'], 'artifact');
  assert.equal(artifact.schema, 'tae.artifact.v1');
  assert(typeof artifact.missionId === 'string' && /^[A-Za-z0-9._:/-]{1,128}$/.test(artifact.missionId), 'Bounded mission ID required');
  assert(hex(artifact.capabilityHash) && hex(artifact.inputHash), 'Artifact hashes required');
  assert.equal(artifact.currentProof, null, 'The deliverable cannot self-certify');
  assert.deepEqual(artifact.authority, [], 'The deliverable cannot grant authority');
  keys(artifact.output, ['groups', 'total'], 'output');
  assert(Array.isArray(artifact.output.groups) && artifact.output.groups.length <= 1024, 'Bounded output groups required');
  const names = new Set(); let total = 0n;
  for (const group of artifact.output.groups) {
    keys(group, ['group', 'total'], 'group');
    assert(typeof group.group === 'string' && group.group.length > 0 && group.group.length <= 128 && !names.has(group.group), 'Unique bounded group required');
    assert(Number.isSafeInteger(group.total), 'Exact integer group total required');
    names.add(group.group); total += BigInt(group.total);
  }
  assert(Number.isSafeInteger(artifact.output.total) && total === BigInt(artifact.output.total), 'Output total invariant failed');
  keys(proof, ['schema', 'missionId', 'artifactSha256', 'inputSha256', 'capabilityHash', 'accepted', 'scope', 'criteriaSha256', 'checkerSha256', 'failures', 'counts', 'authority', 'independence'], 'proof');
  assert.equal(proof.schema, 'tae.proof.v1');
  assert.equal(proof.scope, 'finite synthetic DAG mission');
  assert.equal(proof.missionId, artifact.missionId, 'Mission identity mismatch');
  assert.equal(proof.artifactSha256, sha256(artifactBytes), 'Artifact byte hash mismatch');
  assert.equal(proof.inputSha256, sha256(inputBytes), 'Input byte hash mismatch');
  assert.equal(artifact.inputHash, proof.inputSha256, 'Artifact/input mismatch');
  assert.equal(proof.capabilityHash, artifact.capabilityHash, 'Capability mismatch');
  assert.equal(proof.checkerSha256, checkerSha256, 'Receipt checker differs from frozen checker');
  assert.equal(proof.criteriaSha256, criteriaSha256, 'Receipt criteria differ from frozen criteria');
  assert.equal(proof.accepted, true, 'Rejected or missing evaluation verdict');
  assert.deepEqual(proof.failures, [], 'Evaluation failures remain');
  assert.deepEqual(proof.authority, [], 'Evaluator evidence cannot grant authority');
  keys(proof.counts, ['inputFacts', 'referenceSteps'], 'proof counts');
  assert(Object.values(proof.counts).every(value => Number.isSafeInteger(value) && value >= 0), 'Evaluation counts required');
  assert.equal(proof.independence, 'separate checker implementation; same controller, not external institutional review');
  let candidateBinding = null;
  if (candidateBytes || manifestBytes || manifestSha256) {
    assert(candidateBytes && manifestBytes && hex(manifestSha256), 'Candidate and separately anchored source manifest required together');
    assert.equal(sha256(manifestBytes), manifestSha256, 'Frozen source manifest hash mismatch');
    const frozen = JSON.parse(manifestBytes.toString('utf8'));
    const inventory = frozen.candidateManifest;
    assert.equal(inventory?.schema, 'tae/source-manifest-v1', 'Frozen candidate source manifest required');
    assert.equal(sha256(canonical(inventory.installedCatalog)), inventory.rootSha256, 'Source inventory commitment mismatch');
    const candidate = JSON.parse(candidateBytes.toString('utf8'));
    assert.equal(candidate.schema, 'tae/candidate-result-v1');
    assert.equal(candidate.missionId, artifact.missionId, 'Candidate mission mismatch');
    assert.equal(candidate.status, 'complete', 'Candidate did not complete');
    assert.equal(candidate.delivery?.status, 'ready', 'Candidate delivery is not ready');
    assert.equal(candidate.currentProof, null); assert.deepEqual(candidate.authority, []);
    assert.equal(candidate.capability?.currentProof, null); assert.deepEqual(candidate.capability?.authority, []);
    assert.equal(candidate.capability?.id, artifact.capabilityHash, 'Candidate capability mismatch');
    const capability = candidate.capability;
    const definition = { programs: capability.programs, modules: capability.modules, limits: capability.limits, modelId: capability.modelId };
    assert.equal(sha256(canonical(definition)), artifact.capabilityHash, 'Capability definition commitment mismatch');
    assert.equal(candidate.sources?.rootSha256, inventory.rootSha256, 'Candidate source inventory differs from freeze');
    for (const module of capability.modules) {
      const pinned = inventory.installedCatalog.find(entry => entry.name === module.name);
      assert(pinned && pinned.sha256 === module.sha256, 'Capability module differs from frozen source');
    }
    assert(Array.isArray(candidate.rows), 'Candidate rows required');
    const groups = candidate.rows.map(row => {
      assert(typeof row.amount === 'string' && /^(0|-?[1-9][0-9]*)$/.test(row.amount), 'Candidate decimal rows required');
      const total = Number(row.amount); assert(Number.isSafeInteger(total), 'Candidate row out of exact integer range');
      return { group: row.group, total };
    });
    assert.deepEqual(groups, artifact.output.groups, 'Candidate rows differ from checked delivery');
    candidateBinding = { candidateFileSha256: sha256(candidateBytes), frozenSourceManifestSha256: manifestSha256, sourceCatalogSha256: inventory.rootSha256, capabilityHash: artifact.capabilityHash, declaredModules: capability.modules.map(({ name, sha256 }) => ({ name, sha256 })), scope: 'Captured identity and declared-module binding; execution semantics established by fresh independent output check, not this hash alone' };
  }
  return { artifact, proof, artifactBytes, proofBytes, inputBytes, criteriaBytes, checkerBytes, checkerSha256, criteriaSha256, candidateBytes, manifestBytes, manifestSha256, candidateBinding };
}
function rerunChecker(pack, node) {
  assert(path.isAbsolute(node), 'An absolute pinned Node executable path is required');
  assert.equal(fs.realpathSync(node), fs.realpathSync(process.execPath), 'Checker must use the runner Node executable');
  const captured = validatePackage({ ...Object.fromEntries(['artifactBytes', 'proofBytes', 'inputBytes', 'criteriaBytes', 'checkerBytes', 'candidateBytes', 'manifestBytes'].map(name => [name, pack[name] ? Buffer.from(pack[name]) : null])), checkerSha256: pack.checkerSha256, criteriaSha256: pack.criteriaSha256, manifestSha256: pack.manifestSha256 });
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'tae-checker-'));
  fs.chmodSync(directory, 0o700);
  try {
    for (const [name, bytes] of [['checker.mjs', captured.checkerBytes], ['input.json', captured.inputBytes], ['artifact.json', captured.artifactBytes], ['criteria.json', captured.criteriaBytes]]) {
      fs.writeFileSync(path.join(directory, name), bytes, { mode: 0o400, flag: 'wx' });
    }
    const started = process.hrtime.bigint();
    const result = execFileSync(node, [path.join(directory, 'checker.mjs'), '--input', path.join(directory, 'input.json'), '--artifact', path.join(directory, 'artifact.json'), '--criteria', path.join(directory, 'criteria.json')], {
      cwd: directory, timeout: 15000, maxBuffer: 2 * 1024 * 1024,
      env: { PATH: path.dirname(node), LANG: 'C.UTF-8' },
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
    });
    const observed = JSON.parse(result);
    assert.deepEqual(observed, captured.proof, 'Fresh frozen-checker verdict differs from supplied receipt');
    const checkerRun = Object.freeze({ mode: 'fresh separate-process frozen-checker execution', nodeExecutable: fs.realpathSync(node), nodeVersion: process.version, checkerSha256: captured.checkerSha256, criteriaSha256: captured.criteriaSha256, identicalReceipt: true, elapsedMilliseconds: Number(process.hrtime.bigint() - started) / 1e6, institutionalIndependence: false, hostileProcessIsolationClaimed: false });
    checkedPackages.set(pack, { captured, checkerRun });
    return checkerRun;
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
}
async function runLocalLifecycle(pack, { alphaRoot, checkerRun, fixtureOnly = false, successor = null }) {
  const checked = checkedPackages.get(pack);
  assert(checked && checked.checkerRun === checkerRun, 'Fresh checker execution required');
  pack = checked.captured;
  let successorPackage = null;
  if (successor) {
    const next = checkedPackages.get(successor.pack);
    assert(next && next.checkerRun === successor.checkerRun, 'Fresh successor checker execution required');
    successorPackage = next.captured;
    assert.notEqual(successorPackage.artifact.missionId, pack.artifact.missionId, 'A successor requires a distinct mission');
    assert.notEqual(successorPackage.proof.inputSha256, pack.proof.inputSha256, 'A successor requires a distinct input');
    const parentMission = JSON.parse(pack.inputBytes), childMission = JSON.parse(successorPackage.inputBytes);
    assert.notEqual(childMission.kind, parentMission.kind, 'The connected successor requires a genuinely different declared algebra');
  }
  assert(!process.env.NODE_OPTIONS && !process.env.NODE_PATH, 'Inherited Node preloads are not supported');
  assert(!process.env.HARDHAT_NETWORK || process.env.HARDHAT_NETWORK === 'hardhat', 'External network selection forbidden');
  const contractRoot = path.join(alphaRoot, 'tests/contracts');
  process.env.HARDHAT_CONFIG = path.join(contractRoot, 'hardhat.config.js');
  process.env.HARDHAT_NETWORK = 'hardhat';
  process.chdir(contractRoot);
  const { ethers } = require(path.join(contractRoot, 'node_modules/hardhat'));
  const { requireDisposableLocalNetwork } = require(path.join(contractRoot, 'scripts/disposable'));
  const { fixture, units, now, jump } = require(path.join(contractRoot, 'scripts/fixture'));
  const { compilePlan } = require(path.join(contractRoot, 'scripts/plan'));
  await requireDisposableLocalNetwork();
  assert.equal((await ethers.provider.getNetwork()).chainId, 31337n, 'Local chain required');
  const startedUtc = new Date().toISOString();
  const f = await fixture();
  const graph = { AscensionAccess: f.access, NovaSeed: f.seed, AscensionRiskOracle: f.oracle, AscensionJobMarket: f.jobs, AscensionMark: f.mark, AGIALPHA_fixture: f.token };
  const decoded = receipt => {
    const events = [];
    for (const log of receipt.logs) for (const [contract, instance] of Object.entries(graph)) {
      if (log.address.toLowerCase() !== instance.target.toLowerCase()) continue;
      let item; try { item = instance.interface.parseLog(log); } catch { continue; }
      if (item) events.push({ contract, event: item.name, args: Object.fromEntries(item.fragment.inputs.map((input, i) => [input.name || String(i), item.args[i]])) });
    }
    return { transactionHash: receipt.hash, block: receipt.blockNumber, gasUsed: receipt.gasUsed, status: receipt.status, events };
  };
  const setup = [];
  const setupHeight = (await ethers.provider.getBlock('latest')).number;
  assert(setupHeight <= 256, 'Unexpected local fixture size');
  for (let n = 1; n <= setupHeight; n++) {
    const block = await ethers.provider.getBlock(n);
    for (const tx of block.transactions) setup.push(decoded(await ethers.provider.getTransactionReceipt(tx)));
  }
  async function executeMission(current, { parentSeedId = 0n, currentCheckerRun, setupTransactions = [] } = {}) {
  const missionStartedUtc = new Date().toISOString();
  const steps = [];
  const record = async (stage, transaction) => {
    const receipt = await (await transaction).wait(); assert.equal(receipt.status, 1);
    const entry = { stage, ...decoded(receipt) }; steps.push(entry); return receipt;
  };
  const artifactSha256 = sha256(current.artifactBytes), proofSha256 = sha256(current.proofBytes);
  const bundleComponents = { artifactSha256, proofSha256, candidateFileSha256: current.candidateBinding?.candidateFileSha256 || '0'.repeat(64), frozenSourceManifestSha256: current.manifestSha256 || '0'.repeat(64) };
  const bundleCommitment = ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(['bytes32', 'bytes32', 'bytes32', 'bytes32', 'bytes32'], [ethers.id('TAE artifact/evaluator/source byte envelope v1'), ...Object.values(bundleComponents).map(hash => '0x' + hash)]));
  const spec = { goal: `Evaluate reusable capability for ${current.artifact.missionId}`, successMetric: `Frozen finite DAG checker accepts artifact sha256:${artifactSha256}; evaluator receipt sha256:${proofSha256}`, bounty: units('100').toString(), duration: 86400, priceWeight: 6000 };
  const plan = compilePlan([spec]);
  const eligibility = {
    business: await f.access.eligible(f.business.address, 0),
    worker: await f.access.eligible(f.agent.address, 1),
    validators: await Promise.all(f.validators.map(v => f.access.eligible(v.address, 2))),
  };
  assert(eligibility.business && eligibility.worker && eligibility.validators.every(Boolean));
  await record('Commit mission and evaluator bytes', f.seed.connect(f.business).seal(bundleCommitment, plan.planRoot, 1, 'urn:tae:artifact:' + artifactSha256, parentSeedId, '0x' + proofSha256));
  const seedId = await f.seed.nextId();
  const genome = await f.seed.genomes(seedId);
  assert.equal(genome.parent, parentSeedId, 'On-chain seed parent differs from requested lineage');
  assert.equal(genome.capsuleHash, bundleCommitment, 'On-chain byte envelope commitment mismatch');
  assert.equal(genome.planRoot, plan.planRoot, 'On-chain FusionPlan root mismatch');
  assert.equal(genome.evidenceHash, '0x' + proofSha256, 'On-chain evaluator receipt commitment mismatch');
  const riskApprovedBeforeNewReview = await f.oracle.green(seedId);
  assert.equal(riskApprovedBeforeNewReview, false, 'A new seed must not inherit risk approval');
  await record('Open local risk review', f.oracle.connect(f.business).openReview(seedId));
  for (const validator of f.validators.slice(0, 2)) await record('Local staked risk attestation', f.oracle.connect(validator).attest(seedId, 1000, true, bundleCommitment));
  await record('Open plan-restricted funding', f.mark.connect(f.business).open(seedId, units('2'), units('0.1'), 100, units('100'), (await now()) + 86400, 14 * 86400));
  await record('Fund with local fixture tokens', f.mark.connect(f.funder).buy(seedId, 40, units('158')));
  await record('Activate local plan treasury', f.mark.connect(f.business).bloom(seedId));
  await record('Route committed bounded job', f.mark.connect(f.business).route(seedId, 0, spec, plan.jobs[0].proof, 60, f.committee));
  const jobId = await f.jobs.nextId();
  await record('Collateral-backed local bid', f.jobs.connect(f.agent).bid(jobId, units('80'), 3600));
  await jump((await f.jobs.jobs(jobId)).auctionEnd);
  await record('Assign the bounded job', f.jobs.award(jobId));
  const resultHash = ethers.keccak256(current.artifactBytes);
  await record('Deliver exact checked artifact', f.jobs.connect(f.agent).submit(jobId, resultHash, 'urn:tae:artifact:' + artifactSha256));
  const before = { supply: await f.token.totalSupply(), worker: await f.token.balanceOf(f.agent.address), validators: await Promise.all(f.validators.slice(0, 2).map(v => f.token.balanceOf(v.address))) };
  for (const validator of f.validators.slice(0, 2)) await record('Local exact-artifact validator vote', f.jobs.connect(validator).validate(jobId, resultHash, true, '0x' + proofSha256));
  assert.equal((await f.jobs.jobs(jobId)).state, 4n);
  await record('Collect unused job escrow', f.mark.collect(jobId));
  await record('Close completed campaign', f.mark.close(seedId));
  const beforeRefund = await f.token.balanceOf(f.funder.address);
  await record('Return unused local capital', f.mark.connect(f.funder).reclaim(seedId));
  const accounting = { token: 'AGIALPHA', decimals: 18, mode: 'mock local tokens', funded: units('158'), acceptedPrice: units('80'), workerNet: (await f.token.balanceOf(f.agent.address)) - before.worker, validatorsNet: (await Promise.all(f.validators.slice(0, 2).map(v => f.token.balanceOf(v.address)))).reduce((sum, x, i) => sum + x - before.validators[i], 0n), burned: before.supply - await f.token.totalSupply(), refunded: (await f.token.balanceOf(f.funder.address)) - beforeRefund, remainingReserve: (await f.mark.campaigns(seedId)).reserve };
  assert.equal(accounting.workerNet, units('75.24')); assert.equal(accounting.validatorsNet, units('3.96')); assert.equal(accounting.burned, units('0.8')); assert.equal(accounting.refunded, units('78')); assert.equal(accounting.remainingReserve, 0n);
  assert.equal(accounting.funded, accounting.workerNet + accounting.validatorsNet + accounting.burned + accounting.refunded);
  return {
    schema: 'tae.local-evm-receipt.v1', mode: fixtureOnly ? 'LOCAL_EVM_PROTOTYPE_FIXTURE_ONLY' : 'LOCAL_EVM_EXECUTED_ARTIFACT', startedUtc: missionStartedUtc, finishedUtc: new Date().toISOString(), chainId: '31337', missionId: current.artifact.missionId,
    artifactSha256, proofSha256, inputSha256: current.proof.inputSha256, capabilityHash: current.artifact.capabilityHash, bundleCommitment, bundleComponents, candidateBinding: current.candidateBinding, resultHash, checkerRun: currentCheckerRun, plan, seedId, jobId, parentSeedId,
    lineageBeforeReview: { currentProof: null, authority: [], riskApproved: riskApprovedBeforeNewReview, parentSeedId, onChainParentVerified: true, onChainByteCommitmentsVerified: true },
    authority: { source: 'Operator invocation of the disposable local demonstration; separate test-governor Access admissions', scope: 'Test signers on the guarded in-process chain31337 only', inheritedFromArtifact: false, productionAuthority: false },
    localContractAddresses: Object.fromEntries(Object.entries(graph).map(([name, instance]) => [name, instance.target])),
    localCodeHashes: Object.fromEntries(await Promise.all(Object.entries(graph).map(async ([name, instance]) => [name, ethers.keccak256(await ethers.provider.getCode(instance.target))]))),
    sourceHashes: Object.fromEntries(['AscensionAccess', 'NovaSeed', 'AscensionRiskOracle', 'AscensionJobMarket', 'AscensionMark', 'AscensionToken'].map(name => [name, sha256(readBytes(path.join(alphaRoot, `contracts/ascension/${name}.sol`)))])),
    eligibility, fixtureSetup: { mockTokenInjectedAtCanonicalAddress: true, mockEns: true, localClockAdvancedToAuctionEnd: true, reusedExistingLocalSession: parentSeedId !== 0n, transactions: setupTransactions, gasUsed: setupTransactions.reduce((sum, item) => sum + item.gasUsed, 0n) },
    steps, lifecycleGasUsed: steps.reduce((sum, item) => sum + item.gasUsed, 0n), accounting,
    limitations: ['Actual disposable local EVM; mock token and ENS; no mainnet transactions or real funds.', 'Local signers are not independent organizations; the checker is separately implemented, not institutionally independent.', 'Contracts bind commitments and votes; they do not run the finite semantic checker.', 'Fresh frozen checker ran before settlement; a hash or accepted:true field alone was insufficient.', 'This runner does not grant production authority or establish customer demand, cash revenue, profit or AGI.', 'A child starts without risk approval; a lineage transaction is not proof of successor improvement.'],
  };
  }
  const report = await executeMission(pack, { currentCheckerRun: checkerRun, setupTransactions: setup });
  if (successorPackage) {
    report.successorLifecycle = await executeMission(successorPackage, { parentSeedId: report.seedId, currentCheckerRun: successor.checkerRun });
    report.successor = { seedId: report.successorLifecycle.seedId, parentSeedId: report.seedId, missionId: successorPackage.artifact.missionId, currentProofAtCreation: null, authorityAtCreation: [], riskApprovedAtCreation: false, freshReceiptSha256: report.successorLifecycle.proofSha256, freshLocalSettlement: true };
  } else {
    const child = { schema: 'tae.lineage-child.v1', missionId: pack.artifact.missionId + '/successor-unvalidated', parentMissionId: pack.artifact.missionId, capabilityHash: pack.artifact.capabilityHash, historicalArtifactSha256: report.artifactSha256, historicalReceiptSha256: report.proofSha256, currentProof: null, authority: [] };
    const childBytes = Buffer.from(canonical(child) + '\n');
    const childPlan = compilePlan([{ ...report.plan.jobs[0].spec, goal: 'Distinct successor mission requires new evaluation', successMetric: 'Fresh mission-specific evidence and explicit authority are required before consequential execution.' }]);
    const receipt = await (await f.seed.connect(f.business).seal('0x' + sha256(childBytes), childPlan.planRoot, 1, 'urn:tae:successor:' + sha256(childBytes), report.seedId, report.bundleCommitment)).wait();
    const childId = await f.seed.nextId(); assert.equal(await f.oracle.green(childId), false);
    report.steps.push({ stage: 'Record unapproved successor lineage', ...decoded(receipt) });
    report.lifecycleGasUsed += receipt.gasUsed;
    report.successor = { seedId: childId, manifest: child, riskApproved: false, currentProof: null, authority: [], scope: 'lineage reset only; a distinct successor evaluation is a separate experiment' };
  }
  report.sessionStartedUtc = startedUtc;
  report.sessionFinishedUtc = new Date().toISOString();
  report.sessionLifecycleTransactions = report.steps.length + (report.successorLifecycle?.steps.length || 0);
  report.sessionLifecycleGasUsed = report.lifecycleGasUsed + (report.successorLifecycle?.lifecycleGasUsed || 0n);
  return report;
}
function parseArgs(argv) {
  const required = ['alpha-root', 'artifact', 'proof', 'input', 'criteria', 'checker', 'checker-sha256', 'criteria-sha256', 'node', 'output'];
  const names = new Set([...required, 'fixture-only', 'candidate', 'candidate-manifest', 'candidate-manifest-sha256', 'successor-artifact', 'successor-proof', 'successor-input', 'successor-candidate', 'successor-output']);
  const options = {};
  for (let i = 0; i < argv.length; i += 2) {
    assert(/^--/.test(argv[i]) && names.has(argv[i].slice(2)) && argv[i + 1] !== undefined, 'Unknown or incomplete option');
    const key = argv[i].slice(2); assert(!Object.hasOwn(options, key), 'Duplicate option'); options[key] = argv[i + 1];
  }
  for (const name of required) assert(options[name], `Missing --${name}`);
  assert(!options['fixture-only'] || ['true', 'false'].includes(options['fixture-only']), 'Invalid fixture flag');
  const successorFields = ['successor-artifact', 'successor-proof', 'successor-input'];
  if (successorFields.some(name => options[name])) assert(successorFields.every(name => options[name]), 'Complete successor package required');
  if (options['successor-output'] || options['successor-candidate']) assert(options['successor-artifact'], 'Successor package required');
  if (options.candidate || options['candidate-manifest'] || options['candidate-manifest-sha256']) {
    assert(options.candidate && options['candidate-manifest'] && options['candidate-manifest-sha256'], 'Candidate source binding options required together');
    if (options['successor-artifact']) assert(options['successor-candidate'], 'Successor candidate binding required');
  }
  return options;
}
async function main(argv) {
  const options = parseArgs(argv);
  const invocationRoot = process.cwd();
  const filename = name => path.resolve(invocationRoot, options[name]);
  const output = filename('output'); assert(!fs.existsSync(output), 'Output already exists');
  if (options['successor-output']) assert(!fs.existsSync(filename('successor-output')), 'Successor output already exists');
  const common = { criteriaBytes: readBytes(filename('criteria')), checkerBytes: readBytes(filename('checker')), checkerSha256: options['checker-sha256'], criteriaSha256: options['criteria-sha256'], manifestBytes: options['candidate-manifest'] ? readBytes(filename('candidate-manifest')) : null, manifestSha256: options['candidate-manifest-sha256'] || null };
  const capture = (prefix = '') => validatePackage({ ...common, artifactBytes: readBytes(filename(prefix + 'artifact')), proofBytes: readBytes(filename(prefix + 'proof')), inputBytes: readBytes(filename(prefix + 'input')), candidateBytes: options[prefix + 'candidate'] ? readBytes(filename(prefix + 'candidate')) : null });
  const pack = capture();
  const checkerRun = rerunChecker(pack, filename('node'));
  let successor = null;
  if (options['successor-artifact']) { const next = capture('successor-'); successor = { pack: next, checkerRun: rerunChecker(next, filename('node')) }; }
  const report = await runLocalLifecycle(pack, { alphaRoot: filename('alpha-root'), checkerRun, fixtureOnly: options['fixture-only'] === 'true', successor });
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(report, (_, value) => typeof value === 'bigint' ? value.toString() : value, 2) + '\n', { flag: 'wx' });
  if (options['successor-output']) { const target = filename('successor-output'); fs.mkdirSync(path.dirname(target), { recursive: true }); fs.writeFileSync(target, JSON.stringify(report.successorLifecycle, (_, value) => typeof value === 'bigint' ? value.toString() : value, 2) + '\n', { flag: 'wx' }); }
  console.log(JSON.stringify({ output, mode: report.mode, missionId: report.missionId, transactions: report.sessionLifecycleTransactions, setupTransactions: report.fixtureSetup.transactions.length, artifactSha256: report.artifactSha256, proofSha256: report.proofSha256, successorMissionId: report.successorLifecycle?.missionId || null, successorProofAtCreation: null, successorAuthorityAtCreation: [] }));
}
module.exports = { sha256, canonical, readBytes, canonicalJson, validatePackage, rerunChecker, runLocalLifecycle, parseArgs, main };
if (require.main === module) main(process.argv.slice(2)).catch(error => { console.error('Local EVM request refused: ' + error.message); process.exitCode = 1; });
