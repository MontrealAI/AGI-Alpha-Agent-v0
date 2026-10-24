// SPDX-License-Identifier: Apache-2.0
// Fixed, local-only demonstration. No user-supplied code, network or wallet route.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createWorkspace, solve, sourceManifest } from './enterprise/compiler.mjs';
import { checkArtifact } from './evaluation/checker.mjs';
import { createQualifier } from './evaluation/qualifier.mjs';
import { artifactFor, externalAdmission } from './integration/artifact.mjs';
import { canonicalBytes, createMissionDelivery } from './integration/mission-delivery.mjs';
import { verifyJourney, compactEvm, tokenFlow } from './verify-journey.mjs';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const study = path.join(root, 'study');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const read = relative => fs.readFileSync(path.join(root, relative));
const json = relative => JSON.parse(read(relative));
const exec = promisify(execFile);
const FROZEN = { manifest: '7c25e93b04ed72764824241db825e38b185672625746253bc61abb0318850352', checker: '7eebf95de7ff0b36ebf0029b3bf441e42a2fb325205723b46afc385beb2105c6', criteria: '58dd0ba793d9277e47fdd4e0c336fc6d7b1a9502985fcea7fb117cf47b16aa33' };

export async function runDemo({ outputDirectory, repositoriesRoot = path.join(root, 'repos'), onStage = () => {} } = {}) {
  const started = performance.now(), cpu = process.cpuUsage();
  const output = path.resolve(outputDirectory ?? path.join(study, 'runs', `run-${new Date().toISOString().replace(/[:.]/g, '-')}-${randomUUID().slice(0, 8)}`));
  assert(!fs.existsSync(output), 'Run directory already exists; previous evidence is never overwritten');
  fs.mkdirSync(output, { recursive: true });
  const history = [];
  const save = (name, value, canonical = false) => fs.writeFileSync(path.join(output, name), canonical ? canonicalBytes(value) : JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
  const stage = (name, details = {}) => { const event = { name, elapsedMs: performance.now() - started, ...details }; history.push(event); onStage(event); fs.writeFileSync(path.join(output, 'progress.json'), JSON.stringify({ schema: 'tae.local-progress.v1', history }, null, 2) + '\n'); };
  try {
    stage('Check frozen source and local dependencies');
    const manifestBytes = read('study/evaluation/SCORING_FREEZE_V2.json');
    const criteria = read('study/evaluation/criteria.json');
    assert.equal(sha(manifestBytes), FROZEN.manifest, 'Frozen manifest changed');
    assert.equal(sha(criteria), FROZEN.criteria, 'Frozen criteria changed');
    assert.equal(sha(read('study/evaluation/checker.mjs')), FROZEN.checker, 'Frozen checker changed');
    const frozen = JSON.parse(manifestBytes);
    assert.equal(sourceManifest().rootSha256, frozen.candidateManifest.rootSha256, 'Candidate source changed; revalidation required');
    for (const file of frozen.evaluatorFiles) assert.equal(sha(read(`study/evaluation/${file.path}`)), file.sha256, `Evaluator changed: ${file.path}`);
    assert(fs.existsSync(path.join(repositoriesRoot, 'alpha/tests/contracts/node_modules/hardhat')), 'Run node study/setup.mjs first');
    const qualifier = await createQualifier(path.join(study, 'enterprise'), { mode: 'sliced' });
    const inputs = Object.fromEntries(['parent', 'successor'].map(name => [name, json(`study/results/journey-inputs/${name}/input.json`)]));
    const packages = {};
    let workspace = createWorkspace({ id: 'writer4-local-enterprise' });
    for (const name of ['parent', 'successor']) {
      stage(name === 'parent' ? 'Construct weighted-demand capability' : 'Construct Boolean successor; reset proof and authority');
      if (name === 'successor') workspace = createWorkspace({ id: 'writer4-local-successor', parent: workspace });
      assert.equal(workspace.currentProof, null); assert.deepEqual(workspace.authority, []);
      const mission = inputs[name];
      const result = solve(mission, { workspace, variant: 'full-loop', budget: { operations: 1000000, hashBytes: 10000000, elapsedMs: 10000 } });
      assert.equal(result.status, 'complete'); assert.equal(result.delivery.status, 'ready');
      const qualification = await qualifier.qualify(mission.kind);
      const artifact = artifactFor(mission, result);
      const proof = checkArtifact(canonicalBytes(artifact), canonicalBytes(mission), criteria);
      assert.equal(proof.accepted, true);
      fs.mkdirSync(path.join(output, name));
      for (const [file, value] of Object.entries({ input: mission, candidate: result, artifact, proof, qualification })) save(`${name}/${file}.json`, value, true);
      packages[name] = { mission, result, artifact, proof, qualification };
      workspace = result.workspace;
    }
    assert.equal(packages.successor.result.capability.parentCapabilityId, packages.parent.result.capability.id);
    assert.notEqual(packages.successor.result.capability.id, packages.parent.result.capability.id);
    stage('Execute Alpha → Manager → Jobs → Fleet for both missions');
    const delivery = createMissionDelivery({ repositories: Object.fromEntries(['alpha', 'manager', 'jobs', 'fleet'].map(name => [name, path.join(repositoriesRoot, name)])), check: externalAdmission(checkArtifact, criteria), concurrency: 2 });
    const parent = await delivery.deliver(inputs.parent, packages.parent.result, { projectId: 'writer4-graph-enterprise' });
    const successor = await delivery.deliver(inputs.successor, packages.successor.result, { projectId: 'writer4-graph-enterprise', parentProject: parent.native.artifacts.alpha });
    const journey = { schema: 'tae/two-mission-four-repository-journey-v1', createdAt: new Date().toISOString(), scope: { mode: 'local-source-composition', nativeHostAdmission: 'NOT_RUN', processIsolation: 'NOT_TESTED', settlement: 'separate exact-artifact local-EVM adapter', financialTransfers: 'mock tokens only', learnedProviderSwap: 'unverified', independentCustomerDemand: 'unverified', dispatch: 'Checked computation precedes local job posting; no live award-triggered worker dispatcher' }, parent, successor, statistics: delivery.statistics() };
    save('journey.json', journey);
    stage('Rerun frozen checker; settle exact bytes on disposable local EVM');
    const args = [path.join(study, 'integration/evm-run.cjs'), '--alpha-root', path.join(repositoriesRoot, 'alpha'), '--criteria', path.join(study, 'evaluation/criteria.json'), '--checker', path.join(study, 'evaluation/checker.mjs'), '--checker-sha256', FROZEN.checker, '--criteria-sha256', FROZEN.criteria, '--node', process.execPath, '--candidate-manifest', path.join(study, 'evaluation/SCORING_FREEZE_V2.json'), '--candidate-manifest-sha256', FROZEN.manifest, '--output', path.join(output, 'evm.json'), '--successor-output', path.join(output, 'successor-evm.json')];
    for (const name of ['parent', 'successor']) for (const file of ['artifact', 'proof', 'input', 'candidate']) args.push('--' + (name === 'parent' ? '' : 'successor-') + file, path.join(output, name, file + '.json'));
    const evmStarted = performance.now();
    let child;
    try { child = await exec(process.execPath, args, { cwd: root, timeout: 30000, maxBuffer: 2 * 1024 * 1024, env: { PATH: process.env.PATH, LANG: 'C.UTF-8', HARDHAT_NETWORK: 'hardhat' } }); }
    catch (error) {
      fs.writeFileSync(path.join(output, 'evm-console.txt'), (error.stdout ?? '') + (error.stderr ?? ''));
      save('evm-failure.json', { error: error.message, exitCode: error.code ?? null, signal: error.signal ?? null, killed: error.killed ?? false, elapsedMs: performance.now() - evmStarted, retainedConsole: 'evm-console.txt', automaticRetries: 0 });
      throw error;
    }
    fs.writeFileSync(path.join(output, 'evm-console.txt'), child.stdout + child.stderr);
    const evm = JSON.parse(fs.readFileSync(path.join(output, 'evm.json')));
    const acceptance = verifyJourney(journey, evm);
    save('joined-acceptance.json', acceptance);
    stage('Verify all four envelopes, local settlements and successor lineage', { accepted: true });
    const costs = { elapsedMs: performance.now() - started, cpuMicroseconds: process.cpuUsage(cpu), evmElapsedMs: performance.now() - evmStarted, candidateMetrics: Object.fromEntries(Object.entries(packages).map(([name, pack]) => [name, pack.result.metrics])), qualifier: qualifier.snapshot(), providerCalls: 0, newPaidServicesUSD: 0, cashReceivedUSD: 0, realizedProfitUSD: null, fullyAttributableCostUSD: null, caveat: 'Local timing and instrumented work measured; model authoring, host valuation and human oversight not fully metered. Mock token flow is not revenue.' };
    save('costs.json', costs);
    const evidence = { schema: 'tae.interface-evidence.v1', mode: 'fresh local execution', runId: path.basename(output), recordedComparison: 'study/results/scored-v2/summary.json; frozen comparison is displayed, not rerun by this button', summary: json('study/results/scored-v2/summary.json'), journey, sourceScope: json('study/results/source-scope.json'), evm: { ...compactEvm(evm), observedLiveRead: json('evidence/contracts/live-readonly-observation-proxy.json') }, tokenFlow: tokenFlow(evm), acceptance, costs, workspaces: Object.fromEntries(Object.entries(packages).map(([name, pack]) => [name, pack.result.workspace])), currentProof: null, authority: [] };
    save('evidence.json', evidence);
    return { output, evidence };
  } catch (error) {
    save('failure.json', { schema: 'tae.local-failure.v1', error: error.message, code: error.code ?? null, elapsedMs: performance.now() - started, history, automaticRetries: 0, productionAuthority: false });
    throw error;
  }
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  if (process.argv.length > 3) throw Error('Usage: node study/run-demo.mjs [new-output-directory]');
  runDemo({ outputDirectory: process.argv[2], onStage: event => console.log(JSON.stringify(event)) }).then(({ output }) => console.log(JSON.stringify({ complete: true, output }))).catch(error => { console.error(error.stack); process.exitCode = 1; });
}
