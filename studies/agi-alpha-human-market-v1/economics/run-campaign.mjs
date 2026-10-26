// SPDX-License-Identifier: Apache-2.0
import {readFile, writeFile, appendFile, mkdir, stat} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {performance} from 'node:perf_hooks';
import {pairedHumanMarket, validateHumanConfig} from './human-market.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const [protocolArg, freezeArg, outputArg] = process.argv.slice(2);
if (!protocolArg || !freezeArg || !outputArg) throw Error('Usage: node economics/run-campaign.mjs PROTOCOL.json FREEZE.json NEW_OUTPUT_DIRECTORY');
const study = path.resolve(new URL('..', import.meta.url).pathname);
const protocolPath = path.resolve(protocolArg), freezePath = path.resolve(freezeArg), output = path.resolve(outputArg);
const protocolBytes = await readFile(protocolPath), freezeBytes = await readFile(freezePath);
const protocol = JSON.parse(protocolBytes), freeze = JSON.parse(freezeBytes);
if (protocol.schema !== 'agi-alpha-human-market-campaign/v1') throw Error('Unsupported campaign schema');
if (freeze.schema !== 'agi-alpha-human-market-freeze/v1') throw Error('Unsupported freeze schema');
if (!Array.isArray(protocol.scenarios) || !protocol.scenarios.length || protocol.scenarios.length > 2000) throw Error('Finite scenario panel required');
if (!Array.isArray(protocol.seeds) || !protocol.seeds.length || protocol.seeds.length > 100) throw Error('Finite seed list required');
if (new Set(protocol.seeds).size !== protocol.seeds.length) throw Error('Repeated seeds cannot count as fresh worlds');
if (new Set(protocol.scenarios.map(s => s.id)).size !== protocol.scenarios.length) throw Error('Unique scenario IDs required');
if (protocol.sourceFreezeSHA256 !== sha(freezeBytes)) throw Error('Source freeze differs from registered protocol');
if (!Number.isFinite(protocol.wallBudgetSeconds) || protocol.wallBudgetSeconds <= 0 || protocol.wallBudgetSeconds > 1800) throw Error('Declared execution budget required');
for (const c of protocol.scenarios) validateHumanConfig(c);
if (!Array.isArray(freeze.files) || !freeze.files.length) throw Error('Exact source and production manifests required');
const verified = [];
for (const f of freeze.files) {
  const target = path.resolve(study, f.path);
  if (!target.startsWith(study + path.sep) || !/^[a-f0-9]{64}$/.test(f.sha256)) throw Error('Invalid source path/hash');
  const actual = await readFile(target);
  if (sha(actual) !== f.sha256) throw Error(`Frozen source mismatch: ${f.path}`);
  verified.push({path: f.path, sha256: f.sha256, bytes: actual.length});
}
const requiredSources = ['economics/human-market.mjs', 'economics/run-campaign.mjs',
  'economics/upstream/market/upstream/src/cash-core.mjs',
  'economics/upstream/market/upstream/canonical/shadow-ledger.mjs',
  'economics/upstream/market/upstream/deployment-robustness/funding.mjs',
  'economics/core-transformation.json', 'economics/UPSTREAM.json'];
for (const source of requiredSources) if (!verified.some(f => f.path === source)) throw Error(`Missing frozen dependency: ${source}`);
async function recheckFrozen(coreOnly = false) {
  if (sha(await readFile(protocolPath)) !== sha(protocolBytes) || sha(await readFile(freezePath)) !== sha(freezeBytes))
    throw Error('Campaign protocol or source manifest changed during execution');
  for (const f of verified) {
    if (coreOnly && !requiredSources.includes(f.path)) continue;
    if (sha(await readFile(path.resolve(study, f.path))) !== f.sha256) throw Error(`Frozen source drift: ${f.path}`);
  }
}
await mkdir(path.dirname(output), {recursive: true});
await mkdir(output);
const start = performance.now(), cpu = process.cpuUsage();
await writeFile(path.join(output, 'STARTED.json'), JSON.stringify({schema: 'human-market-campaign-start/v1',
  campaignId: protocol.campaignId, timestampUTC: new Date().toISOString(), protocolSHA256: sha(protocolBytes),
  sourceFreezeSHA256: sha(freezeBytes), plannedWorlds: protocol.scenarios.length * protocol.seeds.length,
  plannedHistories: protocol.scenarios.length * protocol.seeds.length * 3, wallBudgetSeconds: protocol.wallBudgetSeconds,
  sources: verified, primary: protocol.edition === 'primary', edition: protocol.edition, actualCollectionsCents: 0}, null, 2) + '\n', {flag: 'wx'});
const resultPath = path.join(output, 'histories.jsonl.gz');
const columns = ['scenario', 'seed', 'maximumInvestments', 'referenceCents', 'discountBps', 'attempts', 'accepted',
  'grossCollectionsCents', 'accruedCostsCents', 'fullProjectProfitCents', 'finalCashCents', 'obligationsCents',
  'totalProtectedReservesCents', 'operatingGeneratedAvailableCents', 'investmentCount', 'deltaProjectProfitCents',
  'secondIncrementalProjectValueCents', 'fullCycleWithinModel', 'insolvent'];
await writeFile(path.join(output, 'outcomes.csv'), columns.join(',') + '\n', {flag: 'wx'});
const summaries = [], failures = []; let completedWorlds = 0;
for (const scenario of protocol.scenarios) {
  const group = [];
  try { await recheckFrozen(true); }
  catch (error) {
    failures.push({scenario: scenario.id, stage: 'source-drift-before-scenario', error: String(error)});
    await appendFile(path.join(output, 'failures.jsonl'), JSON.stringify(failures.at(-1)) + '\n');
    break;
  }
  for (const seed of protocol.seeds) {
    if ((performance.now() - start) / 1000 > protocol.wallBudgetSeconds) {
      failures.push({scenario: scenario.id, seed, stage: 'budget', error: 'Declared campaign wall budget exceeded'});
      break;
    }
    try {
      const result = pairedHumanMarket(scenario, seed);
      await appendFile(resultPath, gzipSync(JSON.stringify(result) + '\n'));
      const lines = result.runs.map((r, i) => {
        const row = {scenario: scenario.id, seed, maximumInvestments: i,
          referenceCents: scenario.classes[0].humanReferenceCents, discountBps: scenario.discountBps,
          ...r.summary, deltaProjectProfitCents: r.summary.fullProjectProfitCents - result.runs[0].summary.fullProjectProfitCents,
          secondIncrementalProjectValueCents: result.connectedCycle.secondIncrementalProjectValueCents,
          fullCycleWithinModel: result.connectedCycle.fullCycleWithinModel};
        return columns.map(k => String(row[k])).join(',');
      });
      await appendFile(path.join(output, 'outcomes.csv'), lines.join('\n') + '\n');
      group.push({seed, summaries: result.runs.map(r => r.summary), comparisons: result.comparisons,
        connectedCycle: result.connectedCycle});
      completedWorlds++;
    } catch (error) {
      failures.push({scenario: scenario.id, seed, stage: 'simulation', error: String(error), stack: error.stack});
      await appendFile(path.join(output, 'failures.jsonl'), JSON.stringify(failures.at(-1)) + '\n');
      break;
    }
  }
  summaries.push({scenarioId: scenario.id, completed: group.length, seeds: group});
  if (failures.length) break;
}
try { await recheckFrozen(); }
catch (error) {
  failures.push({stage: 'source-drift-at-campaign-end', error: String(error)});
  await appendFile(path.join(output, 'failures.jsonl'), JSON.stringify(failures.at(-1)) + '\n');
}
const endCPU = process.cpuUsage(cpu), complete = completedWorlds === protocol.scenarios.length * protocol.seeds.length && !failures.length;
await writeFile(path.join(output, 'summary.json'), JSON.stringify({schema: 'human-market-campaign-summary/v1',
  basis: 'SIMULATED', actualCollectionsCents: 0, completedWorlds, completedHistories: completedWorlds * 3,
  sourceFreezeSHA256: sha(freezeBytes), protocolSHA256: sha(protocolBytes), groups: summaries, failures}, null, 2) + '\n');
const artifacts = [];
for (const file of ['histories.jsonl.gz', 'outcomes.csv', 'summary.json']) {
  try { const bytes = await readFile(path.join(output, file)); artifacts.push({path: file, bytes: bytes.length, sha256: sha(bytes)}); }
  catch { artifacts.push({path: file, missing: true}); }
}
await writeFile(path.join(output, 'completion.json'), JSON.stringify({schema: 'human-market-campaign-completion/v1',
  complete, timestampUTC: new Date().toISOString(), completedWorlds, completedHistories: completedWorlds * 3,
  wallSeconds: (performance.now() - start) / 1000, cpuSeconds: (endCPU.user + endCPU.system) / 1e6,
  sourceIdentityCheckedBeforeEveryScenarioAndAtCampaignEnd: true,
  outputBytes: (await stat(path.join(output, 'summary.json'))).size, artifacts, failures,
  noReplacementOrRetry: true, actualCollectionsCents: 0}, null, 2) + '\n');
console.log(JSON.stringify({complete, completedWorlds, completedHistories: completedWorlds * 3, failures: failures.length}));
if (!complete) process.exitCode = 1;
