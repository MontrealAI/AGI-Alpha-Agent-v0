// SPDX-License-Identifier: Apache-2.0
// The only qualified profile below lives in a temporary copy. Fixture mutations
// remain restricted to the newly created unforked, in-process Hardhat provider.
const { ethers, network, artifacts } = require('hardhat');
const { fixture, jump } = require('./fixture');
const { requireDisposableLocalNetwork } = require('./disposable');
const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const http = require('node:http'), readline = require('node:readline');
const { createHash } = require('node:crypto'), { spawn, execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '../../..');
const interruptionBrowser = process.env.ASCENSION_CYCLE_INTERRUPTION_BROWSER === '1';
const nativeRunner = interruptionBrowser ? 'cycle-interruptions-native.py' : 'cycle-native.py';
const browserRunner = interruptionBrowser ? 'cycle-interruptions-browser.py' : 'cycle-browser.py';
const out = path.resolve(process.env.ASCENSION_CYCLE_EVIDENCE || path.join(root, 'evidence/ascension-cycle'));
const serialize = value => JSON.stringify(value, (_, item) => typeof item === 'bigint' ? String(item) : item, 2) + '\n';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const readonly = new Set(['eth_call', 'eth_chainId', 'eth_getCode', 'eth_getBlockByNumber', 'eth_getTransactionReceipt', 'eth_getLogs']);
function freshStore() {
  const values = new Map();
  return { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value) };
}
function native(input) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.ALPHA_PYTHON || 'python3', [path.join(root, 'tests/nova-studio', nativeRunner)], {
      cwd: root, env: { ...process.env, PYTHONPATH: root, NO_DISCLAIMER: '1' }, stdio: ['pipe', 'pipe', 'pipe'],
    });
    let result, failure, stderr = '';
    const timer = setTimeout(() => { child.kill(); reject(Error('Native cycle acceptance exceeded 90 seconds')); }, 90000);
    child.stdin.write(JSON.stringify(input) + '\n');
    child.stderr.on('data', data => { stderr += data; });
    const lines = readline.createInterface({ input: child.stdout });
    lines.on('line', async line => {
      try {
        const message = JSON.parse(line);
        if (message.rpc) {
          if (!readonly.has(message.rpc)) throw Error('The native observer attempted a mutating RPC');
          child.stdin.write(JSON.stringify({ result: await ethers.provider.send(message.rpc, message.params) }) + '\n');
        } else if ('result' in message) result = message.result;
        else if (message.error) failure = Error(message.error);
      } catch (error) {
        failure = error;
        if (!child.stdin.destroyed) child.stdin.write(JSON.stringify({ error: String(error) }) + '\n');
      }
    });
    child.on('error', error => { clearTimeout(timer); reject(error); });
    child.on('exit', code => {
      clearTimeout(timer);
      if (failure || code !== 0 || result === undefined) reject(failure || Error(stderr || `Native exit ${code}`));
      else resolve(result);
    });
  });
}
function cid(bytes) {
  const source = Buffer.concat([Buffer.from([1, 85, 18, 32]), createHash('sha256').update(Buffer.from(bytes)).digest()]);
  let bits = 0, value = 0, result = 'b';
  for (const byte of source) {
    value = (value << 8) | byte; bits += 8;
    while (bits >= 5) { result += 'abcdefghijklmnopqrstuvwxyz234567'[(value >>> (bits - 5)) & 31]; bits -= 5; }
  }
  return result + (bits ? 'abcdefghijklmnopqrstuvwxyz234567'[(value << (5 - bits)) & 31] : '');
}
async function marketContext(f, seedId) {
  const identity = async contract => ethers.keccak256(await ethers.provider.getCode(contract.target));
  return {
    schema_version: 1, chain_id: (await ethers.provider.getNetwork()).chainId.toString(),
    market: f.jobs.target.toLowerCase(), market_code_hash: await identity(f.jobs), token_code_hash: await identity(f.token),
    protocol: 'agialpha.ascension.v1', scope: 'disposable-local-fixture', confirmations: 1,
    mark: f.mark.target.toLowerCase(), mark_code_hash: await identity(f.mark),
    seed: f.seed.target.toLowerCase(), seed_code_hash: await identity(f.seed), seed_id: String(seedId),
  };
}
async function setup() {
  await requireDisposableLocalNetwork();
  const f = await fixture(), temp = fs.mkdtempSync(path.join(os.tmpdir(), 'ascension-cycle-'));
  fs.mkdirSync(out, { recursive: true });
  for (const folder of ['ascension', 'ascension-wallet', 'nova-studio', 'successor'])
    fs.cpSync(path.join(root, 'docs/assets', folder), path.join(temp, 'assets', folder), { recursive: true });
  fs.cpSync(path.join(root, 'docs/ascension/mainnet'), path.join(temp, 'ascension/mainnet'), { recursive: true });
  const { ACTIONS } = await import(path.join(root, 'docs/assets/ascension-wallet/protocol.mjs'));
  const { canonicalProfile } = await import(path.join(root, 'docs/assets/ascension-wallet/client.mjs'));
  const { qualificationIdentity } = await import(path.join(root, 'docs/assets/ascension-wallet/qualification.mjs'));
  const contracts = {}, sourceHashes = {}, compilerBuilds = {};
  for (const [key, contract] of Object.entries({ Access: f.access, Seed: f.seed, Oracle: f.oracle, Jobs: f.jobs, Mark: f.mark, Token: f.token }))
    contracts[key] = { address: contract.target, sha256: sha(Buffer.from((await ethers.provider.getCode(contract.target)).slice(2), 'hex')) };
  for (const name of ['AscensionAccess', 'NovaSeed', 'AscensionRiskOracle', 'AscensionJobMarket', 'AscensionMark', 'AscensionToken']) {
    const artifact = await artifacts.readArtifact(name), build = await artifacts.getBuildInfo(`${artifact.sourceName}:${name}`);
    assert.ok(build, `Missing exact compiler input for ${name}`);
    assert.equal(build.solcVersion, require('./compiler-policy').SOLC_VERSION);
    assert.deepEqual(build.input.settings.optimizer, { enabled: true, runs: 200 });
    assert.equal(build.input.settings.viaIR, true); assert.equal(build.input.settings.evmVersion, 'cancun');
    for (const [file, input] of Object.entries(build.input.sources)) {
      if (!file.startsWith('contracts/ascension/') || !fs.existsSync(path.join(root, file))) continue;
      assert.equal(input.content, fs.readFileSync(path.join(root, file), 'utf8'), `Stale compiled source: ${file}`);
      assert.equal(input.content, fs.readFileSync(path.join(root, 'tests/contracts', file), 'utf8'), `Divergent fixture: ${file}`);
      sourceHashes[file] = sha(Buffer.from(input.content));
    }
    compilerBuilds[name] = { source: artifact.sourceName, solcVersion: build.solcVersion,
      inputSHA256: sha(JSON.stringify(build.input)), settings: build.input.settings };
  }
  const sourceSHA256 = sha(canonicalProfile({ sources: sourceHashes, compilerBuilds }));
  const copiedSources = {};
  for (const relative of fs.readdirSync(temp, { recursive: true })) {
    const file = path.join(temp, relative);
    if (fs.statSync(file).isFile()) copiedSources['docs/' + relative] = sha(fs.readFileSync(file));
  }
  const actors = [f.business, f.funder, f.agent, ...f.validators].map(signer => signer.address.toLowerCase());
  const genesis = await network.provider.request({ method: 'eth_getBlockByNumber', params: ['0x0', false] });
  const deployment = await network.provider.request({ method: 'eth_getBlockByNumber', params: ['latest', false] });
  const profile = {
    schema: 'agialpha.nova-local-profile.v1', chainId: 31337, profile: 'disposable-exact-source-ascension-cycle',
    environment: 'local-exact-source', mainnetQualification: false, newExposureEnabled: true,
    contracts, actions: Object.keys(ACTIONS), sourceSHA256, abiSHA256: sha(qualificationIdentity()),
    genesisHash: genesis.hash, deploymentBlock: deployment.number, deploymentBlockHash: deployment.hash,
    dependencies: [], authorities: ['Access', 'Oracle', 'Jobs'].map(contract => ({ contract, owner: f.governor.address })),
    evidence: { classification: 'exact-source-local-with-mock-external-dependencies', sourceHashes, notMainnet: true },
  };
  for (const contract of [f.ens, f.wrapper]) profile.dependencies.push({
    address: contract.target, sha256: sha(Buffer.from((await ethers.provider.getCode(contract.target)).slice(2), 'hex')), slots: [],
  });
  const registryEntry = { canonicalJSON: canonicalProfile(profile), sha256: sha(canonicalProfile(profile)), stage: 'local' };
  fs.writeFileSync(path.join(temp, 'assets/ascension-wallet/qualified-profiles.mjs'), `export const QUALIFIED_PROFILES=Object.freeze(${JSON.stringify([registryEntry])});\n`);
  fs.writeFileSync(path.join(temp, 'assets/ascension-wallet/profile.json'), serialize(profile));
  const fixtureModifications = ['assets/ascension-wallet/qualified-profiles.mjs', 'assets/ascension-wallet/profile.json'].map(relative => ({
    path:'docs/'+relative, originalSourceSha256:copiedSources['docs/'+relative],
    disposableCopySha256:sha(fs.readFileSync(path.join(temp,relative))),
    reason:'Disposable fixture identities only; the production registry remains empty.',
  }));
  const { WalletSession } = await import(path.join(temp, 'assets/ascension-wallet/session.mjs'));
  const { NovaWorkflow } = await import(path.join(temp, 'assets/nova-studio/workflow.mjs'));
  const { PinataStorage } = await import(path.join(temp, 'assets/nova-studio/storage.mjs'));
  const files = new Map(), events = [], walletTraffic = {sends:0}, financialEvidence = {};
  function publish(bytes) { const key = cid(bytes); files.set(key, Buffer.from(bytes)); return key; }
  const storage = new PinataStorage(async (url, options) => {
    if (options.method === 'POST') return new Response(JSON.stringify({ data: { cid: publish(await options.body.get('file').arrayBuffer()) } }));
    const bytes = files.get(url.split('/').at(-1)); return new Response(bytes || '', { status: bytes ? 200 : 404 });
  });
  const locks = { request: async (_name, _options, fn) => fn({ name: 'disposable-node-lock' }) };
  const session = new WalletSession(profile, freshStore(), locks), flow = new NovaWorkflow(session, storage);
  async function choose(signer) {
    session.client.select({ request: async ({ method, params = [] }) => {
      if (method === 'eth_accounts' || method === 'eth_requestAccounts') return [signer.address];
      if (method === 'eth_sendTransaction') { assert.equal(params[0].from.toLowerCase(), signer.address.toLowerCase()); walletTraffic.sends++; }
      return network.provider.request({ method, params });
    } });
    await session.client.connect();
  }
  async function action(name, input = {}) {
    const preview = await flow.prepare(name, input); assert.equal(preview.transaction.value, '0x0');
    const hash = await flow.confirm(true), record = await flow.reconcile(hash); assert.equal(record.status, 'finalized');
    events.push({ action: name, hash, seedId: flow.seedId, status: record.status }); return record;
  }
  return { f, temp, profile, compilerBuilds, copiedSources, fixtureModifications, actors, files, publish, storage, locks, session, flow, choose, action, events, walletTraffic, financialEvidence, WalletSession, NovaWorkflow };
}

async function captureLedger(state,observerKey,label,count) {
  const before=state.walletTraffic.sends, ledger=await state.flow.ledger(observerKey);
  assert.equal(state.walletTraffic.sends,before);
  assert.equal(ledger.settlements.length,count);
  assert.equal(ledger.recipients.reduce((sum,row)=>sum+BigInt(row.grossPayout),0n),ethers.parseEther(String(80*count)));
  assert.equal(ledger.recipients.reduce((sum,row)=>sum+BigInt(row.burned),0n),ethers.parseEther('0.8')*BigInt(count));
  assert.equal(ledger.recipients.reduce((sum,row)=>sum+BigInt(row.netPayout),0n),ethers.parseEther('79.2')*BigInt(count));
  assert.equal(ledger.profit,null); assert.equal(ledger.spendableIncrease,null);
  assert(ledger.refunds.every(row=>row.spendable===false));
  state.financialEvidence[label]=ledger;
  fs.writeFileSync(path.join(out,`financial-${label}.json`),serialize(ledger));
  return ledger;
}

async function main() {
  const state = await setup();
  try { await qualify(state); }
  finally { fs.rmSync(state.temp, { recursive: true, force: true }); }
}

async function qualify(state) {
  const { f, flow, choose, action, publish, profile, temp, events } = state;
  const example = await native({ operation: 'example' });
  const firstWork = { ...example, name: 'Polynomial accuracy report', inputs: {
    coefficients: [0, 0, 0, 0, 1], lower: 0, upper: 3, steps: 2, tolerancePpm: 10,
  } };
  const secondWork = { ...example, name: 'Fresh polynomial validation', inputs: {
    coefficients: [2, -1, 1], lower: 0, upper: 5, steps: 12, tolerancePpm: 10,
  } };
  const jobSpec = {
    goal: 'Produce a reproducible exact-rational polynomial integration report for supplied synthetic inputs.',
    successMetric: 'Return the exact integral, both numerical estimates, residuals and tolerance decisions. Accurate negative reports qualify.',
    bounty: ethers.parseEther('100').toString(), duration: 86400, priceWeight: 6000,
  };
  await choose(f.business);
  await flow.create({ title: 'Inspectable numerical work', description: 'Public synthetic qualification with retained failures.',
    jobs: [jobSpec, jobSpec], evidence: 'Local exact-source acceptance; fixture actors are not independent humans.' }, 'local cycle capsule passphrase');
  await flow.ensureProject({ title: 'Inspectable numerical work', opportunity: { objective: 'Compare exact calculation results before adopting any method.' } });
  const projectId = flow.project.projectId, firstCycleId = flow.cycleId;
  const first = await runCycle(state, firstWork, 1, '200');
  assert.equal(first.result.candidate_verdict, 'FAIL');
  assert.equal(first.settlement.candidate_verdict, 'FAIL');
  assert.equal(first.settlement.settlement_status, 'paid');
  assert.equal(first.settlement.authority_status, 'not_granted');
  assert.equal(first.settlement.memory_admission, 'not_granted');
  assert.equal(first.settlement.institutional_admission, 'not_granted');
  assert.equal(first.settlement.customer_realized_value, null);
  assert.notEqual(first.seal.body.plan_binding.indexed_leaf, first.seal.body.market_spec_hash);
  assert.equal(first.seal.body.plan_binding.indexed_leaf, await f.jobs.hashSpec(1, jobSpec));
  assert.equal(first.seal.body.market_spec_hash, await f.jobs.hashSpec(0, jobSpec));
  const firstLedger=await captureLedger(state,first.sourceKey,'first-output-before-collect',1);
  assert.equal(firstLedger.refunds[0].status,'collectible-by-mark');
  await choose(f.business);
  await action('collect', { jobId: first.jobId });
  await assert.rejects(flow.prepare('close'), /missions still open/);
  const evaluationWork = { ...example, name: 'Fresh same-input method comparison', inputs: {
    coefficients: [1, 0, 1], lower: 0, upper: 5, steps: 12, tolerancePpm: 10,
  } };
  const evaluationRequest = await flow.runtimeRequest(0, evaluationWork);
  const evaluationBase = { home: path.join(temp, 'native-state'), worker: f.agent.address.toLowerCase(),
    request: evaluationRequest, context: await marketContext(f, first.seedId),
    baseline_request: first.request, baseline_result: first.result };
  const evaluationFreeze = await native({ ...evaluationBase, operation: 'freeze-evaluation', evaluation_id: crypto.randomUUID() });
  await flow.importEvaluationFreeze(serialize(evaluationFreeze), first.sourceKey);
  const evaluated = await runJob(state, evaluationWork, 0);
  const comparison = await native({ ...evaluationBase, operation: 'evaluate-comparison', freeze: evaluationFreeze, result: evaluated.result });
  assert.equal(comparison.body.outcome,'PASS');
  assert.equal(comparison.body.admission,'HOLD');
  assert.equal(comparison.body.authority_status,'not_granted');
  assert.equal(comparison.body.compute_cost,null);
  assert.equal(comparison.body.human_cost,null);
  fs.writeFileSync(path.join(out, 'candidate-evaluation.json'), serialize({ freeze: evaluationFreeze, report: comparison }));
  await flow.importEvaluation(serialize(evaluationFreeze), serialize(comparison), evaluated.sourceKey);
  await flow.decideImprovement('adopt', 'Fixture controller', 'The reviewed fresh common task met the frozen exact-error criterion; no money savings inferred.');
  await choose(f.business); await action('collect', { jobId: evaluated.jobId }); await action('close');
  await choose(f.funder);
  const beforeReclaim = await f.token.balanceOf(f.funder.address), reclaimed = (await f.mark.campaigns(first.seedId)).reserve;
  await action('reclaim');
  assert.equal(await f.token.balanceOf(f.funder.address) - beforeReclaim, reclaimed);
  assert.equal((await f.mark.campaigns(first.seedId)).reserve, 0n);
  const firstExitLedger=await captureLedger(state,evaluated.sourceKey,'first-cycle-after-reclaim',2);
  assert.equal(firstExitLedger.ownerTotals.netPayout,'0');
  assert.equal(firstExitLedger.principalReturns.length,1);
  assert.equal(BigInt(firstExitLedger.ownerTotals.returnedPrincipal),reclaimed);
  assert.equal(firstExitLedger.principalReturns[0].recipient,f.funder.address.toLowerCase());
  assert.equal(firstExitLedger.principalReturns[0].income,false);
  assert(firstExitLedger.refunds.every(row=>row.status==='collected-into-campaign'));
  assert(firstExitLedger.campaigns.every(row=>row.reserve==='0'));
  const recovery = await flow.projectKit('encrypted full project passphrase');
  fs.writeFileSync(path.join(out, 'first-cycle-project-recovery.json'), serialize(recovery));
  const restored = new state.NovaWorkflow(new state.WalletSession(profile, freshStore(), state.locks), state.storage);
  await assert.rejects(restored.restoreProject(serialize(recovery), 'wrong project passphrase'));
  await restored.restoreProject(serialize(recovery), 'encrypted full project passphrase', 'local cycle capsule passphrase');
  assert.equal(restored.project.projectId, projectId);
  assert.equal(restored.cycleId, firstCycleId);
  assert.equal(restored.runtimeResult, null);
  assert.equal(restored.client.account, null);
  await choose(f.business);
  const reuse = await flow.authorizeArtifactReuse({reviewer:'Fixture controller',
    rationale:'Reviewed the exact accepted calculation-input.json source, declared synthetic inputs and Apache-2.0 license. Carry the exact bounds, steps and absolute tolerance into the fresh coefficient task.',
    license:evaluated.request.work_spec.rights.license, validUntil:new Date(Date.now()+3600000).toISOString()});
  assert.equal(reuse.asset.digest, '0x'+sha(reuse.sourceBytes));
  assert.deepEqual(JSON.parse(new TextDecoder().decode(reuse.sourceBytes)), evaluationWork.inputs);
  await flow.nextCycle({ title: 'Fresh successor numerical mission', description: 'Different synthetic polynomial inputs; prior reviewed artifact retained.',
    jobs: [{ ...jobSpec, goal: 'Reproduce a new exact-rational polynomial calculation using fresh coefficients and the retained reviewed calculation procedure.' }],
    evidence: 'Distinct second local mission with fresh authorization; no realized commercial value claim.' },
  'second local capsule passphrase');
  assert.equal(flow.project.projectId, projectId);
  assert.notEqual(flow.cycleId, firstCycleId);
  assert.equal(flow.package.parent, first.seedId);
  await assert.rejects(flow.runtimeRequest(0,{...secondWork,inputs:{...secondWork.inputs,steps:14}}), /Inherited steps/);
  const second = await runCycle(state, secondWork, 0, '100');
  assert.deepEqual(flow.currentCycle.missions[0].sourceAssetIds,[reuse.asset.assetId]);
  assert(second.request.work_spec.rights.source.includes(reuse.asset.digest));
  assert.equal(second.result.candidate_verdict, 'PASS');
  assert.equal(second.settlement.settlement_status, 'paid');
  assert.notEqual(second.seedId, first.seedId);
  assert.notEqual(second.jobId, first.jobId);
  assert.notEqual(second.request.cycle_id, first.request.cycle_id);
  assert.notEqual(second.result.request_digest, first.result.request_digest);
  assert.notEqual(second.result.artifact_sha256, first.result.artifact_sha256);
  assert.notEqual(second.result.execution_binding.body.execution_authorization.authorization_id,
    first.result.execution_binding.body.execution_authorization.authorization_id);
  assert.notEqual(JSON.stringify(second.settlement.chain), JSON.stringify(first.settlement.chain));
  assert.equal((await f.seed.genomes(second.seedId)).parent.toString(), first.seedId);
  await choose(f.business); await action('collect', { jobId: second.jobId }); await action('close');
  await choose(f.funder);
  const secondBeforeReclaim=await f.token.balanceOf(f.funder.address), secondReclaimed=(await f.mark.campaigns(second.seedId)).reserve;
  await action('reclaim');
  assert.equal(await f.token.balanceOf(f.funder.address)-secondBeforeReclaim,secondReclaimed);
  const secondLedger=await captureLedger(state,second.sourceKey,'second-cycle-after-reclaim',3);
  assert.equal(secondLedger.ownerTotals.netPayout,'0');
  assert.equal(secondLedger.principalReturns.length,2);
  assert.equal(BigInt(secondLedger.ownerTotals.returnedPrincipal),reclaimed+secondReclaimed);
  assert.equal(secondLedger.principalCoverage.completeHistory,false);
  assert(secondLedger.refunds.every(row=>row.status==='collected-into-campaign'));
  assert(secondLedger.campaigns.every(row=>row.reserve==='0'));
  const finalKit = await flow.projectKit('encrypted full project passphrase');
  fs.writeFileSync(path.join(out, 'two-cycle-project-recovery.json'), serialize(finalKit));
  const fresh = new state.NovaWorkflow(new state.WalletSession(profile, freshStore(), state.locks), state.storage);
  await fresh.restoreProject(serialize(finalKit), 'encrypted full project passphrase', 'second local capsule passphrase');
  assert.equal(fresh.project.projectId, projectId); assert.equal(fresh.project.cycles.length, 2);
  assert.equal(fresh.runtimeResult, null); assert.equal(fresh.client.account, null);
  const sourceHashes = { ...profile.evidence.sourceHashes, ...state.copiedSources };
  for (const relative of ['alpha_factory_v1/core/runtime/successor/studio.py', 'alpha_factory_v1/core/runtime/successor/workbench.py',
    'tests/contracts/scripts/ascension-cycle.js', 'tests/contracts/scripts/disposable.js',
    'tests/nova-studio/cycle-native.py', 'tests/nova-studio/cycle-browser.py', 'tests/nova-studio/edge_browser.py',
    'tests/nova-studio/browser-provider.js',
    ...(interruptionBrowser ? ['tests/nova-studio/cycle-interruptions-browser.py', 'tests/nova-studio/cycle-interruptions-native.py'] : [])]) sourceHashes[relative] = sha(fs.readFileSync(path.join(root, relative)));
  const environment = {
    node:process.version,hardhat:require('hardhat/package.json').version,ethers:ethers.version,
    python:JSON.parse(execFileSync(process.env.ALPHA_PYTHON||'python3',['-c',
      'import json,sys; from importlib.metadata import version; print(json.dumps({"version":sys.version,"packages":{name:version(name) for name in ["cryptography","pydantic","eth-abi","eth-hash","pycryptodome","playwright"]}}))'],{encoding:'utf8'})),
    dependencyLocks:Object.fromEntries(['requirements-agent.lock','tests/contracts/package-lock.json','tests/browser/package-lock.json'].map(relative=>[relative,sha(fs.readFileSync(path.join(root,relative)))])),
  };
  fs.writeFileSync(path.join(out, 'cycle-report.json'), serialize({
    schema: 'agialpha.ascension.complete-cycle.acceptance.v1',
    classification: 'production workflow plus genuine bounded local executor and disposable exact-source EVM',
    commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
    worktreeDirty: Boolean(execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' }).trim()),
    sourceHashes, environment, fixtureModifications:state.fixtureModifications, profile, compilerBuilds:state.compilerBuilds, projectId,
    cycles: [first, second], evaluatedJob: evaluated, evaluationFreeze, comparison,
    reuse:{asset:reuse.asset,selection:reuse.selection,sourceBytesUtf8:new TextDecoder().decode(reuse.sourceBytes)},
    reclaimedBaseUnits: String(reclaimed), actions: events,
    financialEvidence:state.financialEvidence,
    checks: ['preposting richer terms', 'nonzero indexed leaf', 'separate controller signature', 'actual fixed runtime execution',
      'paid negative evaluation', 'idempotent settlement attribution', 'rightful lot-holder reclaim', 'frozen comparable evaluation',
      'actual accepted artifact reuse with current explicit rights review', 'distinct second mission/input/run/result/settlement', 'fresh recovery with no active authority'],
    browser: process.env.ASCENSION_CYCLE_BROWSER === '1' ? 'requested separately below' : 'not performed',
    externalIndependentReview: false, liveModel: false, physicalWallet: false, realStorageAccount: false,
    operatorTransport:'Test-only loopback transport invokes maintained native APIs; fixture principals were explicitly preconfigured by one operator.',
    mainnetTransactions: 0, realizedCommercialValue: null,
  }));
  if (process.env.ASCENSION_CYCLE_BROWSER === '1') {
    await browserAcceptance(state);
    const file=path.join(out,'cycle-report.json'), report=JSON.parse(fs.readFileSync(file,'utf8'));
    report.browser={status:'passed',report:'cycle-browser-report.json',sha256:sha(fs.readFileSync(path.join(out,'cycle-browser-report.json')))};
    fs.writeFileSync(file,serialize(report));
  }
  assert.deepEqual((await import(path.join(root, 'docs/assets/ascension-wallet/qualified-profiles.mjs'))).QUALIFIED_PROFILES, []);
  console.log('Ascension complete-cycle workflow/native acceptance passed');
}

async function runCycle(state, work, planIndex, funding) {
  const { f, flow, choose, action, publish, temp } = state;
  await choose(f.business); await flow.kit(); await flow.publish('synthetic-local-storage-token', true);
  await action('seal'); const seedId = flow.seedId;
  assert.equal((await flow.inspect()).green, false);
  await action('openReview');
  for (const reviewer of f.validators.slice(0, 2)) {
    await choose(reviewer);
    await action('attest', { risk: '1000', approved: 'true', reviewed: true,
      findings: 'Exact synthetic package reviewed by distinct fixture signer; common operator, no independence claim.' });
  }
  await choose(f.business);
  await action('open', { base: '1', slope: '0', maxLots: '1000', target: funding, fundingHours: '24', executionDays: '14' });
  await choose(f.funder);
  if (flow.currentCycle.ordinal===2) {
    const input={amount:ethers.parseEther(funding).toString(),lotCount:funding,
      rationale:'Propose currently owned funds for the distinct successor mission after rightful prior exit.',
      risk:'Returned principal is not profit. External costs and other devices remain unreconciled; confirm each funding action separately.'};
    const sends=state.walletTraffic.sends, proposal=await flow.reinvestmentProposal(input);
    assert.equal(proposal.sourceOwner,f.funder.address.toLowerCase());
    assert.equal(proposal.status,'proposal-only'); assert.equal(proposal.exactCalls,null);
    assert.equal(proposal.quote.baseUnits,input.amount);
    assert.equal(proposal.destination.seedId,seedId);
    await assert.rejects(flow.reinvestmentProposal({...input,amount:String((await f.token.balanceOf(f.funder.address))+1n)}),/exceeds.*funds/);
    assert.equal(state.walletTraffic.sends,sends);
    state.financialEvidence.successorProposal=proposal;
    fs.writeFileSync(path.join(out,'financial-successor-proposal.json'),serialize(proposal));
  }
  await action('approveFunding', { count: funding, limit: funding });
  await action('buy', { count: funding, limit: funding });
  await choose(f.business); await action('bloom', { irreversible: true });
  return runJob(state, work, planIndex);
}

async function runJob(state, work, planIndex) {
  const { f, flow, choose, action, publish, temp } = state, seedId = flow.seedId;
  await choose(f.business);
  const request = await flow.runtimeRequest(planIndex, work);
  await assert.rejects(flow.prepare('route', { index:String(planIndex), auction:'60', reviewers:f.committee }), /preposting|signed|terms|seal/i);
  const base = { home: path.join(temp, 'native-state'), worker: f.agent.address.toLowerCase(), request, context: await marketContext(f, seedId) };
  const { seal, prepared, source_public_key: sourceKey } = await native({ ...base, operation: 'seal' });
  fs.writeFileSync(path.join(out, `cycle-${request.cycle_id}-${planIndex}-preposting.json`), serialize({ request, seal, prepared }));
  assert.equal(prepared.active_authority.length, 0);
  await flow.importTerms(planIndex, serialize(seal), sourceKey);
  const posting = await action('route', { index: String(planIndex), auction: '60', reviewers: f.committee });
  const jobId = flow.jobIds.at(-1);
  assert(BigInt(seal.body.preposting_checkpoint.number) < BigInt(posting.receipt.blockNumber));
  await choose(f.agent); await action('bid', { jobId, price: '80', duration: '3600' });
  await jump((await f.jobs.jobs(jobId)).auctionEnd);
  const assignment = await action('award', { jobId });
  const bound = await native({ ...base, operation: 'bind', seal, job_id: jobId, posting_tx: posting.hash,
    assignment_tx: assignment.hash, expires_at: new Date(Number((await f.jobs.jobs(jobId)).due) * 1000).toISOString() });
  await assert.rejects(native({ ...base, ...bound, operation: 'execute_without_grant', seal }), /trusted|required role|controller/);
  await assert.rejects(native({ ...base, ...bound, operation: 'execute_revoked', seal }), /trusted|required role/);
  const changed = structuredClone(request); changed.work_spec.inputs.upper += 1;
  await assert.rejects(native({ ...base, ...bound, request: changed, operation: 'execute_with_changed_inputs', seal }), /request|terms|seal/);
  const result = await native({ ...base, ...bound, operation: 'execute', seal });
  fs.writeFileSync(path.join(out, `cycle-${request.cycle_id}-${planIndex}-runtime-result.json`), serialize(result));
  assert.equal(result.artifact_keccak256, ethers.keccak256(ethers.toUtf8Bytes(result.artifact_utf8)));
  assert.equal(result.artifact_sha256, '0x' + sha(Buffer.from(result.artifact_utf8)));
  assert.notEqual(result.artifact_keccak256, result.artifact_sha256);
  assert.deepEqual(await native({ ...base, ...bound, operation: 'execute', seal }), result);
  await flow.importRuntimeResult(serialize(result), sourceKey);
  const uri = 'ipfs://' + publish(Buffer.from(result.artifact_utf8));
  await action('submit', { jobId, result: result.artifact_keccak256, hashAlgorithm: 'keccak256', uri });
  const supply = await f.token.totalSupply();
  let receipt;
  for (const reviewer of f.validators.slice(0, 2)) {
    await choose(reviewer);
    receipt = await action('validate', { jobId, result: result.artifact_keccak256, approved: 'true', reviewed: true,
      findings: 'Exact rational report matches declared synthetic inputs and acceptance criteria, including retained failures.' });
  }
  assert.equal(supply - await f.token.totalSupply(), ethers.parseEther('0.8'));
  const imported = await native({ ...base, operation: 'settle', result, settlement_tx: receipt.hash });
  assert.deepEqual(await native({ ...base, operation: 'settle', result, settlement_tx: receipt.hash }), imported);
  const { settlement } = imported;
  fs.writeFileSync(path.join(out, `cycle-${request.cycle_id}-${planIndex}-settlement-record.json`), serialize(imported.record));
  await flow.importRuntimeSettlement(serialize(imported.record), sourceKey);
  const accepted = await native({ ...base, operation: 'accept', result });
  assert.equal(accepted.before.reserved.calls, 1);
  assert.equal(accepted.after.reserved.calls, 0);
  assert.equal(accepted.after.spent.calls, 1);
  const output = { seedId, jobId, sourceKey, environment:prepared.environment, request, seal, result, settlement, accepted, settlementTransaction: receipt.hash };
  fs.writeFileSync(path.join(out, `cycle-${request.cycle_id}-${planIndex}.json`), serialize(output));
  return output;
}

async function browserAcceptance(state) {
  const { f, temp, actors, files, publish } = state;
  const observations = { rpcSends: [], nativeOperations: [], uploads: [] };
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost');
      let raw;
      async function body() {
        if (raw !== undefined) return raw;
        const parts = []; let size = 0;
        for await (const chunk of req) { parts.push(chunk); size += chunk.length; if (size > 2000000) throw Error('Test request exceeds limit'); }
        raw = Buffer.concat(parts); return raw;
      }
      function json(value) { res.setHeader('Content-Type', 'application/json'); res.end(serialize(value)); }
      if (interruptionBrowser && url.pathname === '/interruption-observations' && req.method === 'GET') {
        json(observations); return;
      }
      if (url.pathname === '/operator' && req.method === 'POST') {
        await requireDisposableLocalNetwork();
        const source = JSON.parse((await body()).toString());
        if (!['example', 'seal', 'bind', 'execute', 'settle', 'freeze-evaluation', 'evaluate-comparison', 'accept',
          ...(interruptionBrowser ? ['recover-output', 'recover-settlement'] : [])].includes(source.operation)) throw Error('Unsupported test operator operation');
        if (interruptionBrowser) observations.nativeOperations.push({ operation:source.operation,
          projectId:source.request?.project_id, cycleId:source.request?.cycle_id, planIndex:source.request?.plan_index });
        json(await native({ ...source, home: path.join(temp, 'browser-native-state'), worker: f.agent.address.toLowerCase(),
          ...(source.seed_id ? { context: await marketContext(f, source.seed_id) } : {}) })); return;
      }
      if (url.pathname === '/clock' && req.method === 'POST') {
        await requireDisposableLocalNetwork();
        const source = JSON.parse((await body()).toString());
        if (source.job_id) await jump((await f.jobs.jobs(source.job_id)).auctionEnd);
        else if (source.seed_id) await jump((await f.mark.campaigns(source.seed_id)).executionEnd + 1n);
        else throw Error('Select a fixture auction or campaign deadline');
        json({}); return;
      }
      if (url.pathname === '/rpc' && req.method === 'POST') {
        const { method, params = [] } = JSON.parse((await body()).toString());
        if (!['eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_call', 'eth_estimateGas', 'eth_getBalance',
          'eth_getTransactionCount', 'eth_getTransactionReceipt', 'eth_getTransactionByHash', 'eth_getLogs',
          'eth_getStorageAt', 'eth_sendTransaction'].includes(method)) throw Error('RPC forbidden by disposable test transport');
        if (method === 'eth_sendTransaction' && !actors.includes(params[0]?.from?.toLowerCase())) throw Error('Unknown fixture signer');
        const result = await network.provider.request({ method, params });
        if (interruptionBrowser && method === 'eth_sendTransaction') observations.rpcSends.push({ hash:result, from:params[0].from });
        json({ result }); return;
      }
      if (url.pathname === '/upload' && req.method === 'POST') {
        const form = await new Request('http://localhost/upload', { method: 'POST',
          headers: { 'Content-Type': req.headers['content-type'] }, body: await body() }).formData();
        assert.equal(form.get('network'), 'public');
        const file=form.get('file'), bytes=await file.arrayBuffer(), published=publish(bytes);
        if (interruptionBrowser) observations.uploads.push({ filename:file.name, sha256:sha(Buffer.from(bytes)), cid:published });
        json({ data: { cid:published } }); return;
      }
      if (url.pathname.startsWith('/ipfs/')) {
        const bytes = files.get(url.pathname.slice(6)); res.statusCode = bytes ? 200 : 404;
        res.setHeader('Content-Type', 'application/json'); res.end(bytes || 'missing'); return;
      }
      const relative = decodeURIComponent(url.pathname).replace(/^\//, '');
      const file = path.resolve(temp, relative.endsWith('/') ? relative + 'index.html' : relative);
      if (!file.startsWith(temp + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        res.statusCode = 404; res.end('not found'); return;
      }
      res.setHeader('Content-Type', { '.html': 'text/html', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json' }[path.extname(file)] || 'application/octet-stream');
      res.end(fs.readFileSync(file));
    } catch (error) { res.statusCode = 400; res.setHeader('Content-Type', 'application/json'); res.end(serialize({ error: { message: error.message, code: error.code || -32000 } })); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const config = { url: `http://127.0.0.1:${server.address().port}/ascension/mainnet/`, actors,
    profile:state.profile, fixtureModifications:state.fixtureModifications,
    sourceHashes:JSON.parse(fs.readFileSync(path.join(out,'cycle-report.json'),'utf8')).sourceHashes,
    environment:JSON.parse(fs.readFileSync(path.join(out,'cycle-report.json'),'utf8')).environment,
    committee: f.committee, output: out, firstSeedId: String((await f.seed.nextId()) + 1n),
    firstJobId: String((await f.jobs.nextId()) + 1n) };
  fs.writeFileSync(path.join(out, 'cycle-browser-config.json'), serialize(config));
  try {
    await new Promise((resolve, reject) => {
      const child = spawn(process.env.ALPHA_PYTHON || 'python3', [path.join(root, 'tests/nova-studio', browserRunner),
        path.join(out, 'cycle-browser-config.json')], { cwd: root, stdio: 'inherit' });
      child.on('error', reject); child.on('exit', code => code === 0 ? resolve() : reject(Error(`Browser cycle acceptance exit ${code}`)));
    });
  } finally {
    if (interruptionBrowser) fs.writeFileSync(path.join(out,'cycle-interruptions-transport.json'),serialize(observations));
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
