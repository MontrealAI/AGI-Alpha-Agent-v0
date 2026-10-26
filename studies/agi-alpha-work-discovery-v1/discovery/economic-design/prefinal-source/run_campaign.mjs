// SPDX-License-Identifier: Apache-2.0
import {readFile, writeFile, mkdir, lstat, open} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {dirname, resolve, relative, sep} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {PROTOCOL} from './protocol.mjs';
import {normalizeExecutedCampaign} from './normalize.mjs';
import {
  validateCalibration, campaignWorlds, deploymentDiagnostics, WEEKLY_COLUMNS, compactHistory, summarizeCampaign,
  paperSummary,
} from './model.mjs';

export const STUDY_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
export const SOURCE_FILES = [
  'src/economics/protocol.mjs', 'src/economics/ledger.mjs', 'src/economics/model.mjs',
  'src/economics/run_campaign.mjs', 'src/economics/normalize.mjs', 'tests/economics.test.mjs',
  'heritage/graph-foundations/market/inherited/upstream/canonical/shadow-ledger.mjs',
  'heritage/graph-foundations/market/inherited/upstream/src/market.mjs',
];
const hash = value => createHash('sha256').update(value).digest('hex');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const protocolHash = () => hash(JSON.stringify(PROTOCOL));

function containedPath(path) {
  const absolute = resolve(path), rel = relative(STUDY_ROOT, absolute);
  if (!rel || rel.startsWith(`..${sep}`) || rel === '..' || rel.startsWith(sep)) throw Error('Path must stay inside this study');
  return {absolute, rel: rel.split(sep).join('/')};
}

async function regularBytes(path) {
  const {absolute, rel} = containedPath(path);
  const parts = rel.split('/');
  let cursor = STUDY_ROOT;
  for (let index = 0; index < parts.length; index++) {
    cursor = resolve(cursor, parts[index]);
    const metadata = await lstat(cursor);
    if (metadata.isSymbolicLink() || (index < parts.length - 1 ? !metadata.isDirectory() : !metadata.isFile())) {
      throw Error('Only ordinary directories and regular evidence files are accepted');
    }
  }
  return readFile(absolute);
}

export async function prepareCalibration(path) {
  const inputs = {
    campaign: 'outputs/primary/campaign.json', productionProtocol: 'protocol/production.json',
    acquisitionManifest: 'inputs/acquired/manifest.json', acceptance: 'tests/accept_dossier.py',
    productionFreeze: 'protocol/production-freeze.json',
  };
  const bytes = {}, evidence = [];
  for (const [key, file] of Object.entries(inputs)) {
    bytes[key] = await regularBytes(resolve(STUDY_ROOT, file));
    evidence.push({path: file, sha256: hash(bytes[key])});
  }
  const normalized = normalizeExecutedCampaign({campaign: JSON.parse(bytes.campaign),
    productionProtocol: JSON.parse(bytes.productionProtocol), acquisitionManifest: JSON.parse(bytes.acquisitionManifest),
    evidence, acceptanceSpecificationSha256: hash(bytes.acceptance)});
  validateCalibration(normalized);
  await writeFile(containedPath(path).absolute, serialize(normalized), {flag: 'wx'});
  return normalized;
}

export async function prepareFreeze(path, calibrationPath) {
  const destination = containedPath(path).absolute;
  const calibrationBytes = await regularBytes(calibrationPath);
  const calibration = validateCalibration(JSON.parse(calibrationBytes));
  for (const evidence of calibration.evidence) {
    if (hash(await regularBytes(resolve(STUDY_ROOT, evidence.path))) !== evidence.sha256) throw Error('Calibration evidence drift');
  }
  const sourceFiles = [];
  for (const path of SOURCE_FILES) {
    const bytes = await regularBytes(resolve(STUDY_ROOT, path));
    sourceFiles.push({path, sha256: hash(bytes), bytes: bytes.length});
  }
  const record = {
    schema: 'agi-alpha.work-discovery.economic-freeze.v1',
    status: 'SELF_DECLARED_BEFORE_ECONOMIC_OUTCOME_CAMPAIGN',
    frozenAt: new Date().toISOString(), protocolSha256: protocolHash(), sourceFiles,
    calibration: {path: containedPath(calibrationPath).rel, sha256: hash(calibrationBytes), bytes: calibrationBytes.length},
    campaign: PROTOCOL.campaign,
    limitation: 'Local byte binding and declared ordering only; not an authenticated timestamp or authority grant.',
  };
  await writeFile(destination, serialize(record), {flag: 'wx'});
  return record;
}

export async function verifyFreeze(freeze) {
  if (freeze.schema !== 'agi-alpha.work-discovery.economic-freeze.v1' ||
      freeze.status !== 'SELF_DECLARED_BEFORE_ECONOMIC_OUTCOME_CAMPAIGN' ||
      freeze.protocolSha256 !== protocolHash() || !Array.isArray(freeze.sourceFiles) ||
      freeze.sourceFiles.map(item => item.path).sort().join('|') !== [...SOURCE_FILES].sort().join('|')) {
    throw Error('Economic source and protocol freeze required');
  }
  if (!freeze.calibration || typeof freeze.calibration.path !== 'string' || !/^[a-f0-9]{64}$/.test(freeze.calibration.sha256)) {
    throw Error('Exact calibrated input freeze required');
  }
  const calibrationBytes = await regularBytes(resolve(STUDY_ROOT, freeze.calibration.path));
  if (calibrationBytes.length !== freeze.calibration.bytes || hash(calibrationBytes) !== freeze.calibration.sha256) {
    throw Error('Frozen calibration changed');
  }
  for (const file of freeze.sourceFiles) {
    const bytes = await regularBytes(resolve(STUDY_ROOT, file.path));
    if (hash(bytes) !== file.sha256 || bytes.length !== file.bytes) throw Error(`Frozen source changed: ${file.path}`);
  }
  const canonical = freeze.sourceFiles.find(file => file.path.endsWith('/canonical/shadow-ledger.mjs'));
  if (canonical.sha256 !== PROTOCOL.provenance.accounting.sha256) throw Error('Inherited accounting source drift');
  return true;
}

export async function runPrimaryCampaign({freezePath, calibrationPath, outputPath}) {
  const frozenBytes = await regularBytes(freezePath), freeze = JSON.parse(frozenBytes);
  await verifyFreeze(freeze);
  const calibrationBytes = await regularBytes(calibrationPath);
  if (hash(calibrationBytes) !== freeze.calibration.sha256) throw Error('Campaign calibration differs from frozen input');
  if (calibrationBytes.length > 1_000_000) throw Error('Oversized calibration');
  const calibration = validateCalibration(JSON.parse(calibrationBytes));
  for (const evidence of calibration.evidence) {
    const bytes = await regularBytes(resolve(STUDY_ROOT, evidence.path));
    if (hash(bytes) !== evidence.sha256) throw Error(`Calibration evidence changed: ${evidence.path}`);
  }
  const destination = containedPath(outputPath).absolute;
  // An existing output directory is never erased or overwritten.
  await mkdir(destination);
  let outputBytes = 0;
  const reserveBytes = chunk => {
    outputBytes += Buffer.byteLength(chunk);
    if (outputBytes > PROTOCOL.campaign.maxOutputBytes) throw Error('Predeclared output budget exceeded');
  };
  const write = async (name, value) => {
    const bytes = serialize(value);
    reserveBytes(bytes);
    await writeFile(resolve(destination, name), bytes, {flag: 'wx'});
  };
  await write('protocol.json', PROTOCOL);
  await write('freeze.json', freeze);
  await write('calibration.json', calibration);
  await write('weekly-schema.json', {schema: 'agi-alpha.work-discovery.compact-weekly.v1', columns: WEEKLY_COLUMNS,
    unit: 'Money in integer USD cents; CPU/wall in seconds; attention in minutes.',
    replay: 'Each line contains one complete 52-week counterfactual enterprise. Do not add policies as if they shared one seed.'});
  const historyFile = await open(resolve(destination, 'weekly-histories.ndjson'), 'wx');
  const policiesFile = await open(resolve(destination, 'policy-summaries.ndjson'), 'wx');
  const summaries = [];
  let worlds = 0;
  try {
    for (const world of campaignWorlds(calibration)) {
      for (const result of world.policies) {
        const {history, ...summary} = result;
        summaries.push(summary);
        const record = `${JSON.stringify({cell: result.cell.id, seed: result.seed, policy: result.policy,
          rows: compactHistory(result)})}\n`;
        const summaryLine = `${JSON.stringify(summary)}\n`;
        reserveBytes(record);
        reserveBytes(summaryLine);
        await historyFile.write(record);
        await policiesFile.write(summaryLine);
      }
      worlds++;
    }
  } finally {
    await historyFile.close();
    await policiesFile.close();
  }
  if (worlds !== PROTOCOL.campaign.expectedWorlds) throw Error('Incomplete economic campaign');
  const diagnostics = deploymentDiagnostics(calibration), summary = summarizeCampaign(summaries);
  await write('diagnostics.json', diagnostics);
  await write('summary.json', summary);
  await write('paper-summary.json', paperSummary(summary, diagnostics));
  await verifyFreeze(freeze);
  if (hash(await regularBytes(calibrationPath)) !== hash(calibrationBytes)) throw Error('Calibration changed during campaign');
  await write('completion.json', {
    schema: 'agi-alpha.work-discovery.economic-completion.v1', status: 'COMPLETE_SIMULATION_ONLY',
    completedAt: new Date().toISOString(), worlds, policyExecutions: summaries.length,
    protocolSha256: protocolHash(), freezeSha256: hash(frozenBytes), calibrationSha256: hash(calibrationBytes),
    actualCollectionsCents: 0, actualPaidDemandEstablished: false, tokenEarningsCents: 0,
    bytesBeforeCompletion: outputBytes, maximumOutputBytes: PROTOCOL.campaign.maxOutputBytes,
  });
  return {worlds, policyExecutions: summaries.length, outputBytes, actualCollectionsCents: 0};
}

async function main() {
  const [mode, ...args] = process.argv.slice(2);
  if (mode === 'calibrate' && args.length === 1) {
    const result = await prepareCalibration(resolve(args[0]));
    process.stdout.write(`${JSON.stringify({status: 'NORMALIZED_EXECUTED_INPUT_ONLY', sourceAvailability: result.sourceAvailability})}\n`);
  } else if (mode === 'freeze' && args.length === 2) {
    const result = await prepareFreeze(resolve(args[1]), resolve(args[0]));
    process.stdout.write(`${JSON.stringify({status: result.status, sourceFiles: result.sourceFiles.length})}\n`);
  } else if (mode === 'run' && args.length === 3) {
    const result = await runPrimaryCampaign({freezePath: resolve(args[0]), calibrationPath: resolve(args[1]), outputPath: resolve(args[2])});
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } else {
    throw Error('Usage: node run_campaign.mjs calibrate NEW_CALIBRATION.json | freeze CALIBRATION.json NEW_FREEZE.json | run FREEZE.json CALIBRATION.json NEW_OUTPUT_DIRECTORY');
  }
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  main().catch(error => {process.stderr.write(`${error.message}\n`); process.exitCode = 1;});
}
