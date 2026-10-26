// SPDX-License-Identifier: Apache-2.0
// A bounded retained integration stage over previously qualified GTFS results.
// Canonical Java feed validation and Python/SQLite analysis remain external.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { run, inspectPack } from '../../../../../examples/successor-workbench/engine.mjs';

const root = new URL('../', import.meta.url);
const output = new URL('../workbench/', import.meta.url);
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const json = value => `${JSON.stringify(value, null, 2)}\n`;
const started = performance.now();
const cpuStarted = process.cpuUsage();

// Parse bounded RFC 4180-style CSV produced by the audited packet builder.
function parseCsv(text) {
  assert.ok(text.length < 100000, 'bounded upstream CSV');
  const rows = [];
  let row = [], cell = '', quoted = false, closed = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (char === '"') { quoted = false; closed = true; }
      else cell += char;
    } else if (char === '"' && cell === '' && !closed) quoted = true;
    else if (char === ',') { row.push(cell); cell = ''; closed = false; }
    else if (char === '\r' || char === '\n') {
      if (char === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = ''; closed = false;
    } else { assert.ok(!closed && char !== '"', 'valid CSV quoting'); cell += char; }
  }
  assert.equal(quoted, false, 'closed CSV strings');
  if (row.length || cell || closed) { row.push(cell); rows.push(row); }
  assert.ok(rows.length > 1 && rows.length <= 2001, 'bounded nonempty CSV');
  return rows;
}

const sourceNames = [
  'output/route-date-service.csv', 'output/release-packet.json',
  'output/independent-check.json', 'inputs/rem-20261026.zip',
];
const sourceBytes = await Promise.all(sourceNames.map(name => readFile(new URL(name, root))));
const sourceHashes = Object.fromEntries(sourceNames.map((name, i) => [name, sha256(sourceBytes[i])]));
const packet = JSON.parse(sourceBytes[1]);
const independent = JSON.parse(sourceBytes[2]);
assert.equal(independent.status, 'PASS');
assert.equal(independent.packet_sha256, sourceHashes['output/release-packet.json']);
assert.equal(packet.input_sha256, sourceHashes['inputs/rem-20261026.zip']);
const rows = parseCsv(sourceBytes[0].toString('utf8'));
assert.deepEqual(rows.shift(), [
  'service_date', 'route_id', 'route_name', 'scheduled_trips',
  'first_origin_departure', 'last_origin_departure', 'active_service_ids',
]);
assert.equal(rows.length, 21);
const cells = new Set();
for (const row of rows) {
  assert.equal(row.length, 7);
  assert.match(row[0], /^2026-(10|11)-\d\d$/);
  assert.match(row[3], /^(0|[1-9]\d*)$/);
  assert.ok(Number.isSafeInteger(Number(row[3])) && Number(row[3]) <= 1000000);
  const key = `${row[0]}:${row[1]}`;
  assert.equal(cells.has(key), false, 'unique route/date cell');
  cells.add(key);
  const upstream = packet.route_daily_service.find(item => item.service_date === row[0] && item.route_id === row[1]);
  assert.ok(upstream, 'CSV cell exists in qualified packet');
  assert.equal(Number(row[3]), upstream.scheduled_trips);
}
const projectedCsv = `group,amount\n${rows.map(row => `${row[0]},${row[3]}`).join('\n')}\n`;
const engineUrl = new URL('../../../../../examples/successor-workbench/engine.mjs', import.meta.url);
const dependencyNames = [
  'examples/successor-workbench/engine.mjs', 'docs/assets/successor/engine.mjs',
  'examples/build-successor/model.mjs',
  ...['compiler', 'domain', 'integrity', 'templates'].map(name => `examples/build-successor/vendor/agijobs/${name}.mjs`),
];
const repo = new URL('../../../../../', import.meta.url);
const dependencyHashes = Object.fromEntries(await Promise.all(dependencyNames.map(async name => [name, sha256(await readFile(new URL(name, repo)))])));
const sourceHash = sha256(await readFile(engineUrl));
const spec = {
  schema: 'successor-workbench/v1', family: 'public-data',
  name: 'REM seven-day declared trip reconciliation', language: 'en', owner: 'local-owner',
  rights: { dataClass: 'public', source: 'REM GTFS, https://gtfs.gpmmom.ca/gtfs/gtfs.zip; retained 2026-10-26 snapshot', license: 'CC BY 4.0; included __Licence.txt retained in upstream archive' },
  reviewMinutes: 10,
  inputs: { csv: projectedCsv, unit: 'declared scheduled trip instances; not observed boardings' },
};
await mkdir(output, { recursive: true });
await writeFile(new URL('projection.csv', output), projectedCsv);
await writeFile(new URL('mission.json', output), json(spec));
const pack = await run(spec, { sourceHash });
const inspected = await inspectPack(pack);
const observed = pack.result.evidence.groups;
assert.equal(observed.length, 7);
assert.equal(pack.result.summary.rows, 21);
const dailyChecks = packet.daily_service.map(day => {
  const group = observed.find(item => item.group === day.date);
  assert.ok(group, 'every qualified date appears in Workbench output');
  assert.equal(group.count, 3);
  assert.equal(group.total, day.scheduled_trips);
  return { date: day.date, expected: day.scheduled_trips, actual: group.total, passed: true };
});
const expectedTotal = packet.daily_service.reduce((total, day) => total + day.scheduled_trips, 0);
assert.equal(expectedTotal, 2853);
assert.equal(pack.result.summary.total, expectedTotal);
assert.equal(pack.compilation.graph.nodes.length, 7);
assert.equal(pack.compilation.budgetReservations.reservedBaseUnits, '0');
assert.equal(pack.compilation.budgetReservations.limitBaseUnits, '0');
assert.equal(pack.compilation.signatureStatus, 'UNSIGNED_COMMITMENT');
assert.equal(pack.compilation.authorityCreated, 'NONE');
for (const job of pack.compilation.graph.nodes) {
  assert.equal(job.state, 'DRAFT');
  assert.equal(job.budget.limitBaseUnits, '0');
  assert.equal(job.signatureStatus, 'UNSIGNED_COMMITMENT');
}
assert.deepEqual(pack.evaluation.authority, []);
assert.equal(pack.evaluation.admission, 'HOLD');
assert.equal(pack.evaluation.settlement, 'NOT_CONNECTED');
assert.deepEqual(inspected.activeAuthority, []);
assert.deepEqual(inspected.activeProof, []);
await writeFile(new URL('workbench-pack.json', output), json(pack));
await writeFile(new URL('inspection.json', output), json(inspected));
for (const artifact of pack.result.artifacts) await writeFile(new URL(artifact.name, output), artifact.content);
const cpu = process.cpuUsage(cpuStarted);
const acceptance = {
  status: 'PASS', stage: 'Existing SUCCESSOR public-data adapter aggregates the upstream qualified CSV',
  jobCount: 1, routeDateCells: 21, dailyGroups: 7, declaredTripInstances: expectedTotal,
  dailyChecks, independentUpstreamCheck: 'Separate SQLite interpretation, retained in output/independent-check.json',
  sourceHashes, dependencyHashes, wrapperSha256: sha256(await readFile(new URL('./run_workbench.mjs', import.meta.url))),
  engineSourceHash: sourceHash, packDigest: pack.integrityDigest,
  unfundedJobProposals: 7, signatureStatus: 'UNSIGNED_COMMITMENT', authorityCreated: 'NONE', admission: 'HOLD',
  elapsedSeconds: (performance.now() - started) / 1000, cpuSeconds: (cpu.user + cpu.system) / 1000000,
  engineReviewCapacityMinutes: 10, actualHumanReviewMinutes: null,
  scope: 'Exact descriptive totals from one already qualified REM snapshot. Java canonical validation and Python/SQLite feed interpretation were executed separately, not by this adapter. The seven Jobs proposals are inert drafts, not seven paid customer jobs. No live authentication, market execution or settlement.',
};
await writeFile(new URL('acceptance.json', output), json(acceptance));
console.log(json({ status: acceptance.status, total: expectedTotal, dates: dailyChecks, proposals: 7, admission: 'HOLD', output: fileURLToPath(output) }));
