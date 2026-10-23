// SPDX-License-Identifier: Apache-2.0
// Reproduce the twelve publicly frozen cases against unchanged source 175d8a5.
// Run: /path/to/node-v22.17.1/bin/node runner.mjs [new-receipt.json]
import {readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname, join, resolve} from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SELF = fileURLToPath(import.meta.url);
const SOURCE_COMMIT = '175d8a50473ea94f8c63d20959c22c95dfc6b886';
const PROTOCOL_URL = 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4871#issuecomment-6352588248';
const PROTOCOL_BODY_SHA256 = '7aa9e6ee7e16a2fa6b55c3152862041c2eb8ff2765fb69e5e7a0effb0ed7709e';
const SOURCES = {
  'thermal-witness.mjs': '604bd36528e5c688d357ae91c42dd52c2987612c',
  'thermal-witness-reference.mjs': '36b7c5efa42250fb30d5c212d0a5ca0b4b07076f',
  'thermal-witness-fixtures.mjs': '00ff7fe2b1836de6801a076df7617b805ba0888d',
};
const HISTORICAL = {
  status: 'RETAINED_UNDETECTED_FAILURE',
  release: 'study-foundry-v2-2026-10-22-r1',
  predictedHeatJ: '5175.8646948056885',
  commandFlowCalorimeterHeatJ: '5445.281559253128',
  independentReferenceHeatJ: '5009.6244576737745',
  runtimeRelativeResidual: '0.049477122810963045',
  trueRelativeHeatError: '0.08696402400224054',
  scope: 'Historical simulated result; a new witness run does not rewrite or qualify it.',
};

function hash(bytes, algorithm = 'sha256') {
  return createHash(algorithm).update(bytes).digest('hex');
}
function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  }
  return JSON.stringify(value);
}
function requireCondition(ok, message) {
  if (!ok) throw Error(message);
}
function integer(value, label) {
  requireCondition(typeof value === 'string' && /^-?\d+$/.test(value), label + ' must be an integer string');
  return BigInt(value);
}
function abs(value) { return value < 0n ? -value : value; }
function hiddenKeys(value) {
  const hidden = new Set([
    'audit', 'assumptions', 'multipliers', 'parameters', 'trueSecondaryHeatJ', 'legacyCommandHeatJ',
    'volumeOracleNanoLitres', 'sampledTemperatures', 'resetState', 'finalState', 'scenario',
    'initialHistoryK', 'volumeMeterBias', 'differentialBiasK',
  ]);
  const found = [];
  function visit(node, path = '') {
    if (node === null || typeof node !== 'object') return;
    for (const [key, child] of Object.entries(node)) {
      const at = path ? path + '.' + key : key;
      if (hidden.has(key)) found.push(at);
      visit(child, at);
    }
  }
  visit(value);
  return found;
}

async function runWorker() {
  // This branch imports only the pinned production adapter. It never imports
  // fixtures/reference or receives case options, audits or reference heat.
  const checkpoints = [];
  const startedAt = new Date().toISOString();
  let raw = '';
  let result = null;
  let error = null;
  try {
    requireCondition(process.version === 'v22.17.1', 'Pinned Node v22.17.1 is required');
    process.stdin.setEncoding('utf8');
    for await (const part of process.stdin) {
      raw += part;
      requireCondition(Buffer.byteLength(raw) <= 2000000, 'Worker input exceeds existing 2 MB boundary');
    }
    const input = JSON.parse(raw);
    const {executeThermal} = await import('./thermal-witness.mjs');
    result = await executeThermal(input, async label => { checkpoints.push(label); });
  } catch (caught) {
    error = {name: caught.name, message: caught.message, stack: caught.stack};
    process.exitCode = 1;
  }
  process.stdout.write(JSON.stringify({
    nodeVersion: process.version, startedAt, finishedAt: new Date().toISOString(),
    inputSha256: hash(raw), inputBytes: Buffer.byteLength(raw),
    checkpointLabels: checkpoints, result, error,
  }) + '\n');
}

async function evaluate() {
  const startedAt = new Date().toISOString();
  requireCondition(process.version === 'v22.17.1', 'Pinned Node v22.17.1 is required');
  const copiedSourceManifest = JSON.parse(readFileSync(join(HERE, 'SOURCE_MANIFEST.json'), 'utf8'));
  const verifiedSources = [];
  for (const [name, expected] of Object.entries(SOURCES)) {
    const bytes = readFileSync(join(HERE, name));
    const gitBlob = hash(Buffer.concat([Buffer.from('blob ' + bytes.length + '\0'), bytes]), 'sha1');
    requireCondition(gitBlob === expected, 'Pinned source differs: ' + name);
    verifiedSources.push({path: name, bytes: bytes.length, gitBlob, sha256: hash(bytes)});
  }
  const commentBytes = readFileSync(join(HERE, 'frozen-protocol-comment.json'));
  const comment = JSON.parse(commentBytes);
  requireCondition(comment.id === 6352588248 && comment.html_url === PROTOCOL_URL, 'Wrong frozen protocol comment');
  requireCondition(hash(comment.body) === PROTOCOL_BODY_SHA256, 'Frozen public protocol body changed');
  const blocks = [...comment.body.matchAll(/\x60{3}json\s*\n([\s\S]*?)\n\x60{3}/g)];
  requireCondition(blocks.length === 1, 'Expected one frozen JSON protocol');
  const protocol = JSON.parse(blocks[0][1]);
  requireCondition(protocol.protocol === 'thermal-heldout-v1' && protocol.sourceCommit === SOURCE_COMMIT,
    'Wrong protocol or source');
  requireCondition(protocol.cases.length === 12 &&
    protocol.cases.map(x => x.id).join(',') === Array.from({length: 12}, (_, i) => 'H' + String(i + 1).padStart(2, '0')).join(','),
    'Frozen cases missing, reordered or duplicated');

  const {foundryWitnessFixture} = await import('./thermal-witness-fixtures.mjs');
  const records = [];
  const environment = Object.fromEntries(Object.entries(process.env)
    .filter(([key]) => ['PATH', 'SYSTEMROOT', 'WINDIR', 'TMPDIR'].includes(key)));

  for (const selected of protocol.cases) {
    const {id, ...options} = selected;
    const row = {id, options, startedAt: new Date().toISOString(), criteria: [], failures: []};
    const check = (criterion, name, pass, details) => {
      const observation = {criterion, name, pass: Boolean(pass), details};
      row.criteria.push(observation);
      if (!observation.pass) row.failures.push({criterion, name, details});
    };
    try {
      const fixture = foundryWitnessFixture(options);
      const input = fixture.input;
      row.input = input;
      row.inputSha256 = hash(JSON.stringify(input));
      row.fixtureAssumptions = fixture.assumptions;
      row.evaluatorAudit = fixture.audit;
      const forbidden = hiddenKeys(input);
      const configuredAsFrozen = input.family === protocol.family &&
        input.policy.maxRelativeErrorPpm === protocol.maxRelativeErrorPpm &&
        input.policy.minimumHeatMicroJ === protocol.minimumHeatMicroJ &&
        input.maxWorkUnits === protocol.maxWorkUnits;
      const child = spawnSync(process.execPath, [SELF, '--worker'], {
        input: JSON.stringify(input), encoding: 'utf8', timeout: 15000, maxBuffer: 2000000,
        cwd: HERE, env: environment,
      });
      row.workerProcess = {
        status: child.status, signal: child.signal,
        error: child.error ? {name: child.error.name, message: child.error.message, code: child.error.code} : null,
        stderr: child.stderr, stdoutSha256: hash(child.stdout || ''),
      };
      requireCondition(Boolean(child.stdout), 'Worker did not return a receipt');
      const worker = JSON.parse(child.stdout);
      row.worker = worker;
      check(1, 'input-only worker transport', configuredAsFrozen && forbidden.length === 0 &&
        worker.inputSha256 === row.inputSha256 && child.status === 0 && child.signal === null && !child.error,
      {configuredAsFrozen, hiddenKeysInInput: forbidden, workerInputSha256: worker.inputSha256,
        transport: 'JSON stdin contains fixture.input only; separate child imports the adapter only',
        workerProcessStatus: child.status, workerSignal: child.signal});

      const result = worker.result;
      requireCondition(result && typeof result === 'object', 'Missing production adapter result');
      const evidence = result.evidence;
      const labels = worker.checkpointLabels;
      const checkpointCounts = Object.fromEntries([...new Set(labels)].map(label => [label, labels.filter(x => x === label).length]));
      const exactCheckpoints = labels.length === 721 && labels.slice(0, 720).every(x => x === 'thermal-interval') &&
        labels[720] === 'thermal-evidence';
      row.checkpointCounts = checkpointCounts;
      check(2, 'complete bounded computation', worker.error === null && worker.nodeVersion === 'v22.17.1' &&
        evidence.completion === 'COMPLETE' && evidence.intervalsDeclared === 720 &&
        evidence.intervalsProcessed === 720 && evidence.workUnits === 720 && evidence.coverageMs === 720000 &&
        evidence.propertyModel === 'CONSTANT_WITHIN_INTERVAL' && result.decision === 'CONDITIONAL_BOUNDS_MET' &&
        exactCheckpoints,
      {completion: evidence.completion, intervalsDeclared: evidence.intervalsDeclared,
        intervalsProcessed: evidence.intervalsProcessed, workUnits: evidence.workUnits,
        coverageMs: evidence.coverageMs, propertyModel: evidence.propertyModel,
        decision: result.decision, checkpointCounts, exactCheckpointOrder: exactCheckpoints, workerError: worker.error});

      const referenceJ = fixture.audit.trueSecondaryHeatJ;
      requireCondition(Number.isFinite(referenceJ) && referenceJ > 0, 'Invalid positive numerical reference');
      const floorMicroJ = Math.floor(referenceJ * 1e6);
      const ceilMicroJ = Math.ceil(referenceJ * 1e6);
      requireCondition(Number.isSafeInteger(floorMicroJ) && Number.isSafeInteger(ceilMicroJ),
        'Numerical reference endpoints are outside exact integer representation');
      const RL = BigInt(floorMicroJ), RU = BigInt(ceilMicroJ);
      const L = integer(evidence.quantity.low, 'L');
      const E = integer(evidence.quantity.estimate, 'E');
      const U = integer(evidence.quantity.high, 'U');
      const P = integer(evidence.uncertainty.worstRelativeErrorPpm, 'P');
      row.measurement = {
        referenceJ, referenceFloorMicroJ: String(RL), referenceCeilMicroJ: String(RU),
        lowerMicroJ: String(L), estimateMicroJ: String(E), upperMicroJ: String(U),
        reportedBoundPpm: String(P),
        observedNumericalRelativeError: Math.abs(Number(E) / 1e6 - referenceJ) / referenceJ,
        observedNumericalErrorPercent: 100 * Math.abs(Number(E) / 1e6 - referenceJ) / referenceJ,
      };
      check(3, 'integer bounds bracket returned numerical reference',
        0n < L && L <= E && E <= U && L <= RL && RU <= U && L >= 1000000n,
      row.measurement);
      const endpointChecks = [RL, RU].map(T => ({
        referenceMicroJ: String(T),
        absoluteErrorMicroJ: String(abs(E - T)),
        left: String(abs(E - T) * 1000000n),
        right: String(P * T),
        pass: abs(E - T) * 1000000n <= P * T,
      }));
      check(4, 'declared error covers both integer reference endpoints',
        P >= 0n && P <= 50000n && endpointChecks.every(x => x.pass),
      {reportedBoundPpm: String(P), maximumFrozenPpm: 50000, endpointChecks, addedTolerance: '0'});

      const proposals = result.artifacts.filter(x => x.name === 'thermal-capability-proposal.json');
      requireCondition(proposals.length === 1, 'Expected one capability-proposal artifact');
      const proposal = JSON.parse(proposals[0].content);
      row.noAuthority = {
        simulation: evidence.simulation, physicalValidity: evidence.physicalValidity,
        independentReview: evidence.independentReview, summaryAcceptedCapability: result.summary.acceptedCapability,
        proposalAcceptedCapability: proposal.acceptedCapability, authority: proposal.authority, settlement: proposal.settlement,
      };
      check(5, 'simulation and no-authority boundary',
        evidence.simulation === true && evidence.physicalValidity === 'NOT_ESTABLISHED' &&
        evidence.independentReview === false && result.summary.acceptedCapability === false &&
        proposal.acceptedCapability === false && Array.isArray(proposal.authority) && proposal.authority.length === 0 &&
        proposal.settlement === 'NOT_CONNECTED',
      row.noAuthority);

      const expectedHistory = canonical(HISTORICAL);
      const actualHistory = canonical(evidence.inheritedFailure);
      row.historicalFailure = {
        record: evidence.inheritedFailure, expectedCanonicalJson: expectedHistory, actualCanonicalJson: actualHistory,
        expectedCanonicalSha256: hash(expectedHistory), actualCanonicalSha256: hash(actualHistory),
      };
      check(6, 'historical failure preserved byte-for-byte in canonical JSON',
        Buffer.from(actualHistory).equals(Buffer.from(expectedHistory)),
      {expectedCanonicalSha256: hash(expectedHistory), actualCanonicalSha256: hash(actualHistory),
        status: evidence.inheritedFailure.status, release: evidence.inheritedFailure.release});
    } catch (caught) {
      row.exception = {name: caught.name, message: caught.message, stack: caught.stack};
      row.failures.push({name: 'evaluation exception', details: row.exception});
      for (let criterion = 1; criterion <= 6; criterion++) {
        if (!row.criteria.some(x => x.criterion === criterion)) {
          check(criterion, 'not completed after exception', false, row.exception);
        }
      }
    }
    row.finishedAt = new Date().toISOString();
    row.pass = row.criteria.length === 6 && row.criteria.every(x => x.pass) && row.failures.length === 0;
    records.push(row);
  }

  const measured = records.filter(x => x.measurement);
  const regimeSpans = {};
  for (const scenario of ['nominal', 'flow-power-uncertainty']) {
    const values = measured.filter(x => x.options.scenario === scenario).map(x => x.measurement.referenceJ);
    regimeSpans[scenario] = {cases: values.length, minimumReferenceJ: Math.min(...values),
      maximumReferenceJ: Math.max(...values), referenceSpanJ: Math.max(...values) - Math.min(...values)};
  }
  const receipt = {
    schema: 'thermal-heldout-native-execution/v1',
    protocol: protocol.protocol, sourceCommit: SOURCE_COMMIT,
    startedAt, finishedAt: new Date().toISOString(),
    frozenProtocol: {
      permalink: PROTOCOL_URL, publicCommentId: comment.id, publishedAt: comment.created_at,
      bodySha256: hash(comment.body), snapshotSha256: hash(commentBytes),
      exactBody: comment.body, casesAndOptions: protocol,
    },
    runtime: {node: process.version, v8: process.versions.v8, platform: process.platform, arch: process.arch,
      execPath: process.execPath, executableSha256: hash(readFileSync(process.execPath)),
      command: [process.execPath, SELF], workerInvocation: [process.execPath, SELF, '--worker']},
    sourceFiles: verifiedSources, sourceAcquisition: copiedSourceManifest,
    runner: {path: 'runner.mjs', sha256: hash(readFileSync(SELF))},
    priorV8Evidence: [{
      url: 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4871#issuecomment-6353311037',
      kind: 'Previously reported V8 evaluations and old-head hosted checks',
      retainedAs: 'Public link; original full V8 run JSON is not reconstructed or claimed available here',
    }],
    cases: records,
    summary: {
      declaredCases: 12, executedCases: records.length,
      passed: records.filter(x => x.pass).length, failed: records.filter(x => !x.pass).length,
      failures: records.filter(x => !x.pass).map(x => ({id: x.id, failures: x.failures})),
      maximumReportedBoundPpm: measured.length ? Math.max(...measured.map(x => Number(x.measurement.reportedBoundPpm))) : null,
      maximumObservedNumericalErrorPercent: measured.length ?
        Math.max(...measured.map(x => x.measurement.observedNumericalErrorPercent)) : null,
      referenceVariationByRegime: regimeSpans,
      allHistoricalRecordsUnchanged: records.every(x => x.criteria.find(y => y.criterion === 6)?.pass),
      allNoAuthorityChecksPassed: records.every(x => x.criteria.find(y => y.criterion === 5)?.pass),
    },
    scope: [
      'Unchanged production ESM adapter and frozen evaluator/fixtures executed in actual Node v22.17.1.',
      'Twelve deliberately selected acquisition-bias/history combinations in two fixed actuator regimes of the same four-state ODE.',
      'The 180-second reset suppresses most initial-history variation; this is not broad unknown-plant generalization.',
      'Returned RK4 numerical reference is bracketed under the frozen integer checks; no certified exact ODE solution is claimed.',
      'Calibration, flow coverage, fixed properties and temporal bounds remain modeled assumptions; physical validity is not established.',
      'Workers receive input-only JSON in separate subprocesses and do not import reference/fixture modules; this is not an OS filesystem sandbox.',
      'This receipt does not qualify changed PR source, installed native packaging, Python journal recovery, the held harness, Fleet review, contracts or settlement.',
      'No independent approval, accepted capability, operational authority, legal status or financial action is created.',
    ],
  };
  const output = process.argv[2] ? resolve(process.argv[2]) : join(HERE, 'native-receipt.json');
  writeFileSync(output, JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
  process.stdout.write(JSON.stringify({receipt: output, ...receipt.summary}, null, 2) + '\n');
  if (receipt.summary.failed) process.exitCode = 1;
}

if (process.argv[2] === '--worker') await runWorker();
else await evaluate();
