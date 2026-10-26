import { readFileSync, writeFileSync, mkdirSync, createWriteStream } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { createGzip } from 'node:zlib';
import { once } from 'node:events';
import { finished } from 'node:stream/promises';
import { performance } from 'node:perf_hooks';
import { pairedNetwork, validateCalibration, unknownCostBoundary } from './network_market.mjs';
const root = dirname(fileURLToPath(import.meta.url));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const json = path => JSON.parse(readFileSync(path, 'utf8'));
const assert = (ok, message) => { if (!ok) throw Error(message); };
const sum = xs => xs.reduce((a, b) => a + b, 0);
const quantile = (sorted, p) => {
  const i = (sorted.length - 1) * p, j = Math.floor(i);
  return sorted[j] + (sorted[Math.min(j + 1, sorted.length - 1)] - sorted[j]) * (i - j);
};
export function distribution(values) {
  const sorted = [...values].sort((a, b) => a - b), n = sorted.length;
  const mean = sum(sorted) / n;
  const se = Math.sqrt(sum(sorted.map(v => (v - mean) ** 2)) / Math.max(1, n - 1) / n);
  return {n, mean, min: sorted[0], p05: quantile(sorted, 0.05), median: quantile(sorted, 0.5),
    p95: quantile(sorted, 0.95), max: sorted.at(-1), negative: sorted.filter(v => v < 0).length,
    zero: sorted.filter(v => v === 0).length, positive: sorted.filter(v => v > 0).length,
    conditional_monte_carlo_mean_interval: [mean - 1.96 * se, mean + 1.96 * se]};
}

export function validateInputs(protocolPath, freezePath = null) {
  const protocol = json(protocolPath), base = dirname(protocolPath);
  assert(protocol.schema === 'capability-advantage-market-protocol/v1', 'Protocol schema mismatch');
  assert(protocol.conditions.length === 48 && protocol.schedules.length === 3 && protocol.seeds.length === 16,
    'Predeclared scale changed');
  assert(new Set(protocol.seeds).size === 16, 'Duplicate seeds');
  const calibrationFile = resolve(base, protocol.calibration_path);
  const calibration = validateCalibration(json(calibrationFile));
  if (freezePath) {
    const freeze = json(freezePath);
    assert(protocol.status === 'FROZEN_BEFORE_MARKET_OUTCOMES' && protocol.market_outcomes_inspected === false,
      'Market requires a prospective source/protocol freeze');
    assert(typeof protocol.frozen_at_utc === 'string' && typeof protocol.registration_url === 'string', 'Registration required');
    assert(freeze.market_outcomes_inspected === false, 'Freeze must precede outcomes');
    const expected = new Set(['market-protocol.json', 'calibration.json', 'network_market.mjs', 'run_market.mjs',
      'inherited/upstream/src/market.mjs', 'inherited/upstream/src/market-adapter-primitives.mjs',
      'inherited/upstream/canonical/shadow-ledger.mjs', 'inherited/upstream/canonical/automated-costs.mjs',
      'inherited/continuation.mjs', 'inherited/continuation-core.mjs']);
    for (const row of freeze.files) {
      assert(!row.path.startsWith('/') && !row.path.split('/').includes('..'), 'Freeze path escapes package');
      const bytes = readFileSync(resolve(base, row.path));
      assert(hash(bytes) === row.sha256 && bytes.length === row.bytes, `Frozen identity mismatch: ${row.path}`);
      expected.delete(row.path);
    }
    assert(expected.size === 0, `Missing frozen inputs: ${[...expected].join(',')}`);
  }
  return {protocol, calibration, calibration_sha256: hash(readFileSync(calibrationFile))};
}

export function streamFinalizer(gzip, stream) {
  const completion = finished(stream);
  completion.catch(() => {});
  gzip.on('error', error => stream.destroy(error));
  return async () => {
    if (!gzip.writableEnded && !gzip.destroyed) gzip.end();
    await completion;
  };
}

export async function runCampaign(protocolPath, freezePath, output) {
  const {protocol, calibration, calibration_sha256} = validateInputs(protocolPath, freezePath);
  assert(freezePath, 'Campaign requires a source freeze');
  mkdirSync(output, {recursive: false});
  const start = performance.now(), cpuStart = process.cpuUsage();
  const stream = createWriteStream(join(output, 'complete-worlds.jsonl.gz'), {flags: 'wx'});
  const gzip = createGzip({level: 1});
  const finish = streamFinalizer(gzip, stream);
  gzip.pipe(stream);
  const write = async row => { if (!gzip.write(JSON.stringify(row) + '\n')) await once(gzip, 'drain'); };
  const compact = [], summaries = [];
  let completed = 0, fullFinanceControls = 0;
  try {
    for (const condition of protocol.conditions) for (const schedule of protocol.schedules) {
      const group = [];
      for (const seed of protocol.seeds) {
        const elapsed = (performance.now() - start) / 1000, cpu = process.cpuUsage(cpuStart);
        assert(elapsed <= protocol.limits.wall_seconds && (cpu.user + cpu.system) / 1e6 <= protocol.limits.cpu_seconds,
          'Declared campaign time boundary exceeded');
        const world = pairedNetwork(calibration, condition, schedule, seed,
          {validated: true, keepFinanceHistories: true, includeOffers: false});
        fullFinanceControls += Object.values(world.finance_controls).filter(c => c.histories).length;
        await write(world);
        const row = {seed, condition_id: condition.id, schedule_id: schedule.id, differences: world.differences,
          arms: Object.fromEntries(Object.entries(world.arms).map(([id, run]) => [id, run.summary])),
          succession: world.succession,
          later_investment_counts: Object.fromEntries(Object.entries(world.arms).map(([id, run]) => [id,
            Object.keys(run.assets).filter(g => g !== 'G1').length])),
          finance_differences: Object.fromEntries(Object.entries(world.finance_controls).map(([id, c]) => [id, c.incremental_project_profit_cents]))};
        compact.push(row); group.push(row); completed++;
        const rep = protocol.representative;
        if (rep.condition_id === condition.id && rep.schedule_id === schedule.id && rep.seed === seed)
          writeFileSync(join(output, 'preselected-representative.json'), JSON.stringify(world, null, 2) + '\n', {flag: 'wx'});
      }
      summaries.push({condition_id: condition.id, schedule_id: schedule.id, condition,
        differences: Object.fromEntries(Object.keys(group[0].differences).map(k => [k, distribution(group.map(r => r.differences[k]))])),
        arms: Object.fromEntries(['A', 'B', 'C', 'D'].map(arm => [arm, {
          profit: distribution(group.map(r => r.arms[arm].profit_cents)),
          project_profit: distribution(group.map(r => r.arms[arm].project_inclusive_profit_cents)),
          accepted: distribution(group.map(r => r.arms[arm].accepted)),
          collections: distribution(group.map(r => r.arms[arm].collected_cents)),
          transfers: distribution(group.map(r => r.arms[arm].useful_transfers)),
          funded_later_capabilities: sum(group.map(r => r.later_investment_counts[arm])),
          qualifying_later_bundle_worlds: group.filter(r => r.succession[arm].qualifies).length
        }]))});
      if (summaries.length % 12 === 0) process.stdout.write(JSON.stringify({groups_completed: summaries.length,
        worlds_completed: completed, wall_seconds: (performance.now() - start) / 1000}) + '\n');
    }
    await finish();
    const elapsed = (performance.now() - start) / 1000, cpu = process.cpuUsage(cpuStart);
    assert(elapsed <= protocol.limits.wall_seconds && (cpu.user + cpu.system) / 1e6 <= protocol.limits.cpu_seconds,
      'Declared serialization/compression boundary exceeded');
    assert(completed === protocol.expected.paired_worlds, 'Incomplete campaign');
    writeFileSync(join(output, 'compact-worlds.json'), JSON.stringify(compact) + '\n', {flag: 'wx'});
    writeFileSync(join(output, 'summary.json'), JSON.stringify({schema: 'capability-advantage-market-summary/v1',
      conditions: summaries, unknown_actual_cost_boundary: unknownCostBoundary(),
      interpretation: 'Conditional sensitivity panel; counts are not estimated real-market probabilities.'}, null, 2) + '\n', {flag: 'wx'});
    const fields = ['condition_id', 'schedule_id', 'seed', 'B_minus_A_cents', 'C_minus_B_cents', 'C_minus_D_cents',
      'B_minus_A_project_cents', 'C_minus_B_project_cents', 'C_minus_D_project_cents'];
    const csv = [fields.join(','), ...compact.map(row => fields.map(f => row[f] ?? row.differences[f]).join(','))].join('\n') + '\n';
    writeFileSync(join(output, 'paired-results.csv'), csv, {flag: 'wx'});
    const finalCpu = process.cpuUsage(cpuStart);
    assert((performance.now() - start) / 1000 <= protocol.limits.wall_seconds &&
      (finalCpu.user + finalCpu.system) / 1e6 <= protocol.limits.cpu_seconds, 'Final serialization boundary exceeded');
    const receipt = {schema: 'capability-advantage-market-completion/v1', status: 'COMPLETE',
      completed_at_utc: new Date().toISOString(), worlds: completed, primary_histories: completed * 4,
      additional_same_world_finance_controls: fullFinanceControls, wall_seconds: (performance.now() - start) / 1000,
      cpu_seconds: (finalCpu.user + finalCpu.system) / 1e6, calibration_sha256,
      protocol_sha256: hash(readFileSync(protocolPath)), source_freeze_sha256: hash(readFileSync(freezePath)),
      actual_customer_collections_cents: 0};
    writeFileSync(join(output, 'completion.json'), JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
    return receipt;
  } catch (error) {
    await finish().catch(() => {});
    const receipt = {status: 'FAILED_OR_PARTIAL', worlds_completed: completed,
      reason: String(error?.stack ?? error), elapsed_seconds: (performance.now() - start) / 1000,
      retry_permitted_automatically: false, partial_evidence_preserved: true};
    writeFileSync(join(output, 'failure.json'), JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
    throw error;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = Object.fromEntries(process.argv.slice(2).map(arg => {
    const [key, ...parts] = arg.replace(/^--/, '').split('='); return [key, parts.length ? parts.join('=') : true];
  }));
  const protocolPath = resolve(String(args.protocol || join(root, 'market-protocol.json')));
  if (args['validate-only']) {
    const validated = validateInputs(protocolPath, args.freeze ? resolve(String(args.freeze)) : null);
    process.stdout.write(JSON.stringify({validated: true, market_outcomes_run: 0,
      calibration_sha256: validated.calibration_sha256, paired_worlds: validated.protocol.expected.paired_worlds}) + '\n');
  } else {
    assert(args.freeze && args.output, 'Supply --freeze=... and --output=...; no implicit campaign');
    process.stdout.write(JSON.stringify(await runCampaign(protocolPath, resolve(String(args.freeze)), resolve(String(args.output)))) + '\n');
  }
}
