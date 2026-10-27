// SPDX-License-Identifier: Apache-2.0
// Actual native arithmetic over retained modeled worlds; no cash or receipt API.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync, readdirSync, writeFileSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {projectScenario} from '../vendor/native-accounting/project_scenario.mjs';

const SCRIPT = fileURLToPath(import.meta.url);
const ROOT = resolve(dirname(SCRIPT), '..');
const PROTOCOL = '7cb1683c08090d68cef5e847438446dda8032b67163c5368c2cbdaddce180dcb';
const SCHEMA = 'paid-work-retained-alpha.native-confirmed-projection/v1';
const NATIVE_CATEGORIES = ['delivery', 'business', 'capability', 'maintenance'];
const BOOKS = ['job', 'retention', 'investment', 'common'];
// A reporting partition, not additional expenses or a claim about provider bills.
const MAPPING = {
  automated_intake: ['job', 'delivery'],
  production: ['job', 'delivery'],
  validation: ['job', 'delivery'],
  revalidation: ['job', 'delivery'],
  correction: ['job', 'delivery'],
  packaging: ['job', 'delivery'],
  failed_job_recovery: ['job', 'delivery'],
  refund_and_recovery: ['job', 'delivery'],
  retention_evaluation: ['retention', 'capability'],
  retention_extract_validate_package: ['retention', 'capability'],
  retention_creator_bounty: ['retention', 'capability'],
  skill_maintenance: ['retention', 'maintenance'],
  skill_distribution: ['retention', 'maintenance'],
  skill_revalidation: ['retention', 'maintenance'],
  moving_beta_alpha_reassessment: ['retention', 'maintenance'],
  network_access_overhead: ['retention', 'maintenance'],
  investment_evaluation: ['investment', 'capability'],
  capability_search_build_confirm_migrate: ['investment', 'capability'],
  investment_creator_bounty: ['investment', 'capability'],
  setup: ['common', 'business'],
  infrastructure_access_storage: ['common', 'business']
};

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const stable = value => JSON.stringify(value, (_key, item) =>
  item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);
const sum = values => values.reduce((total, value) => {
  assert(Number.isSafeInteger(total + value), 'Integer accounting total exceeds safe range');
  return total + value;
}, 0);
function minor(value, label) {
  assert(Number.isSafeInteger(value) && value >= 0, `${label}: nonnegative integer cents required`);
  return value;
}
function dollarsToMinor(value, label, {signed = false} = {}) {
  assert(Number.isFinite(value) && (signed || value >= 0), `${label}: invalid dollar amount`);
  const result = Math.round(value * 100);
  assert(Number.isSafeInteger(result) && Math.abs(result - value * 100) < 0.00001,
    `${label}: reported dollars must resolve to cents`);
  return result;
}
const worldKey = row => `${row.scenario}/${row.arm}/${row.seed}`;
const zeroes = keys => Object.fromEntries(keys.map(key => [key, 0]));

function extractSample(sample, path, confirmation) {
  const key = worldKey(sample);
  assert(confirmation, `${key}: missing confirmation record`);
  // Full samples add transaction/detail arrays. Every retained summary field
  // must still match the completed confirmation corpus, not a rerun or edit.
  for (const [field, value] of Object.entries(confirmation)) {
    assert.deepEqual(sample[field], value, `${key}: sample differs from confirmation field ${field}`);
  }
  assert.equal(sample.status.actual_sales, 0);
  assert.equal(sample.status.live_model_calls, 0);
  assert.equal(sample.status.live_ens, false);
  const books = zeroes(BOOKS), nativeCosts = zeroes(NATIVE_CATEGORIES), byCategory = {};
  const bookCategory = Object.fromEntries(BOOKS.map(book => [book, zeroes(NATIVE_CATEGORIES)]));
  const commitments = new Map();
  let accrued = 0, unpaid = 0, paid = 0, collections = 0, seed = 0, seedEvents = 0, expenseRows = 0;
  let lastWeek = -1;
  for (const row of sample.ledger) {
    assert(Number.isInteger(row.week) && row.week >= lastWeek, `${key}: nonchronological ledger`);
    lastWeek = row.week;
    const amount = minor(row.amount_cents, `${key}/${row.kind}`);
    switch (row.kind) {
      case 'seed':
        seedEvents += 1;
        seed += amount;
        break;
      case 'reserve':
        assert(!commitments.has(row.key), `${key}: duplicate live commitment`);
        commitments.set(row.key, amount);
        break;
      case 'release':
        assert.equal(amount, commitments.get(row.key) ?? 0, `${key}: released commitment mismatch`);
        commitments.delete(row.key);
        break;
      case 'collection':
        collections += amount;
        break;
      case 'expense': {
        assert(Object.hasOwn(MAPPING, row.category), `${key}: unmapped expense ${row.category}`);
        const [book, category] = MAPPING[row.category];
        assert.equal(row.book, book, `${key}: source expense book changed`);
        const payment = minor(row.paid_cents, `${key}/expense payment`);
        assert(payment <= amount, `${key}: payment exceeds accrued expense`);
        if (commitments.has(row.key)) {
          const remaining = commitments.get(row.key) - amount;
          assert(remaining >= 0, `${key}: expense exceeds funded commitment`);
          commitments.set(row.key, remaining);
        }
        accrued += amount;
        paid += payment;
        unpaid += amount - payment;
        expenseRows += 1;
        books[book] += amount;
        nativeCosts[category] += amount;
        bookCategory[book][category] += amount;
        byCategory[row.category] = (byCategory[row.category] ?? 0) + amount;
        break;
      }
      default:
        throw Error(`${key}: unsupported source transaction ${row.kind}`);
    }
  }
  for (const value of [accrued, unpaid, paid, collections, seed, ...Object.values(nativeCosts)]) minor(value, key);
  assert.equal(seedEvents, 1, `${key}: expected one source seed record`);
  assert.equal(seed, dollarsToMinor(sample.seed_capital, key));
  assert.equal(collections, dollarsToMinor(sample.collections, key));
  assert.equal(accrued, dollarsToMinor(sample.expenses, key));
  assert.equal(sum(Object.values(books)), accrued);
  assert.equal(sum(Object.values(nativeCosts)), accrued);
  for (const book of BOOKS) assert.equal(books[book], dollarsToMinor(sample.cost_books[book], `${key}/${book}`));
  assert.deepEqual(byCategory, Object.fromEntries(Object.entries(sample.costs)
    .map(([category, value]) => [category, dollarsToMinor(value, `${key}/${category}`)])));
  assert.equal(seed + collections - paid, dollarsToMinor(sample.cash, key), `${key}: source cash identity`);

  const last = sample.weekly.at(-1);
  assert(last && last.week >= lastWeek, `${key}: final weekly snapshot absent`);
  const protectedCash = dollarsToMinor(last.committed, `${key}/ending protected cash`);
  const outstandingCommitments = sum([...commitments.values()]);
  const warrantyReserve = protectedCash - outstandingCommitments;
  const closing = dollarsToMinor(sample.closing_obligations, `${key}/closing obligations`);
  // Unpaid expenses already belong to full accrued cost. Funded commitments
  // belong to closing obligations, so remove them from the separate reserve.
  const unaccruedObligations = closing - unpaid;
  const futureRefunds = unaccruedObligations - outstandingCommitments;
  minor(warrantyReserve, `${key}/noncommitment reserve`);
  minor(unaccruedObligations, `${key}/unaccrued obligations`);
  minor(futureRefunds, `${key}/future refunds`);
  const profit = dollarsToMinor(sample.profit, `${key}/reported surplus`, {signed: true});
  assert.equal(collections - accrued - unaccruedObligations, profit,
    `${key}: terminal accrued-cost reconciliation`);
  assert.equal(Math.max(0, dollarsToMinor(sample.cash, key) - protectedCash - unpaid),
    dollarsToMinor(sample.available_cash, key), `${key}: source available cash reconciliation`);

  const projectionRecord = {
    id: `sample-${sample.scenario}-${sample.arm}-${sample.seed}`,
    acceptance: 'unknown',
    modeledCollectionsMinor: collections,
    costsMinor: nativeCosts,
    reserveMinor: warrantyReserve,
    obligationMinor: unaccruedObligations
  };
  assert(Buffer.byteLength(JSON.stringify(projectionRecord), 'utf8') < 4096,
    `${key}: each native sample record must remain below 4 KiB`);
  return {
    sample: {path, key, scenario: sample.scenario, arm: sample.arm, seed: sample.seed,
      model: sample.model, selectedPolicy: sample.policy.name, sourceExpenseRows: expenseRows,
      projectionUnit: 'One aggregate modeled enterprise world, not one native customer mission'},
    projectionRecord,
    reconciliation: {
      sourceCostBooksMinor: books, nativeCostCategoriesMinor: nativeCosts,
      sourceBookToNativeCategoryMinor: bookCategory, sourceExpenseCategoriesMinor: byCategory,
      accruedCostMinor: accrued, paidExpenseMinor: paid,
      historicalJobLearningMemoMinor: dollarsToMinor(sample.paid_job_learning_cost_memo, key),
      historicalMemoAddedAgain: false,
      modeledCollectionsMinor: collections,
      sourceClosingObligationsMinor: closing,
      sourceProtectedCashMinor: protectedCash,
      sourceAccruedUnpaidExpensesMinor: unpaid,
      sourceOutstandingFundedCommitmentsMinor: outstandingCommitments,
      sourceInferredFutureRefundsMinor: futureRefunds,
      nativeSeparateWarrantyReserveMinor: warrantyReserve,
      nativeUnaccruedObligationsMinor: unaccruedObligations,
      modeledReportedOperatingSurplusMinor: profit,
      expectedNativeAfterReservesMinor: profit - warrantyReserve,
      sourceAvailableCashMinor: dollarsToMinor(sample.available_cash, key),
      nativeCashClaim: false
    }
  };
}

export function projectConfirmedSamples(root = ROOT) {
  const sourceFiles = {};
  function readSource(name) {
    const bytes = readFileSync(join(root, name));
    assert(bytes.byteLength <= 64 * 1024 * 1024, `${name}: source exceeds 64 MiB analysis bound`);
    sourceFiles[name] = {sha256: sha(bytes), bytes: bytes.byteLength};
    return bytes;
  }
  const parseSource = name => JSON.parse(readSource(name).toString('utf8'));
  const freeze = parseSource('results/protocol_freeze.json');
  assert.equal(sourceFiles['results/protocol_freeze.json'].sha256, PROTOCOL, 'Unexpected scientific protocol');
  for (const [name, expected] of Object.entries(freeze.source_hashes)) {
    assert.equal(sha(readSource(name)), expected, `Frozen source changed: ${name}`);
  }
  const foundations = parseSource('sources/foundation_manifest.json');
  for (const record of foundations.vendored_source.files) {
    assert.equal(sha(readSource(record.path)), record.sha256, `Canonical native file changed: ${record.path}`);
  }
  const adapter = foundations.new_research_code.find(row => row.path.endsWith('/project_scenario.mjs'));
  assert(adapter, 'Pinned native projection adapter identity absent');
  assert.equal(sha(readSource(adapter.path)), adapter.sha256, 'Existing native projection adapter changed');
  readSource(relative(ROOT, SCRIPT));
  const selected = parseSource('results/selected_policies.json');
  assert.equal(selected.protocol_sha256, PROTOCOL);
  const confirmationText = readSource('results/confirmation_runs.jsonl').toString('utf8');
  assert(confirmationText.endsWith('\n'), 'Incomplete confirmation corpus');
  const confirmations = new Map();
  for (const line of confirmationText.trimEnd().split('\n')) {
    const row = JSON.parse(line), key = worldKey(row);
    assert(!confirmations.has(key), `Duplicate confirmation identity: ${key}`);
    confirmations.set(key, row);
  }
  assert.equal(confirmations.size,
    Object.keys(freeze.scenarios).length * freeze.arms.length * freeze.confirmation_seeds.length,
    'Complete predeclared confirmation corpus required');
  const seed = freeze.confirmation_seeds[0];
  const expectedFiles = Object.keys(freeze.scenarios).flatMap(scenario =>
    freeze.arms.map(arm => `${scenario}-${arm}.json`)).sort();
  assert.equal(expectedFiles.length, 12, 'Expected twelve predeclared sample worlds');
  assert.deepEqual(readdirSync(join(root, 'results/samples')).filter(name => name.endsWith('.json')).sort(),
    expectedFiles, 'Sample directory differs from predeclared scenario/arm matrix');
  const samples = expectedFiles.map(name => {
    const path = `results/samples/${name}`, sample = parseSource(path);
    assert.equal(sample.seed, seed, `${path}: not the first predeclared confirmation seed`);
    assert.equal(`${sample.scenario}-${sample.arm}.json`, name);
    assert.equal(sample.policy.name, selected.policies[sample.scenario].name,
      `${path}: sample uses a different selected policy`);
    return extractSample(sample, path, confirmations.get(worldKey(sample)));
  });
  const serialized = JSON.stringify(samples.map(row => row.projectionRecord));
  assert(serialized.length <= 250000, 'Native serialized-input bound exceeded');
  const native = projectScenario(serialized); // Calls unchanged canonical replayLedger.
  const totalCost = sum(samples.map(row => row.reconciliation.accruedCostMinor));
  const expectedCategories = Object.fromEntries(NATIVE_CATEGORIES.map(category => [category,
    sum(samples.map(row => row.projectionRecord.costsMinor[category]))]));
  assert.equal(native.summary.scenario.fullCost, totalCost, 'Native aggregate full cost differs from source expenses');
  assert.equal(native.summary.reinvestmentBps, 0, 'Native automatic reinvestment default changed');
  assert.equal(native.summary.missions.length, 12);
  for (const [field, value] of Object.entries(native.summary.observed)) {
    assert.equal(value, null, `Observed ${field} must remain unknown`);
  }
  assert.equal(native.summary.scenario.availableSurplus, null, 'Aggregate-world acceptance must remain unknown');
  assert.equal(native.summary.scenario.eligibleInvestment, null,
    'Projection cannot manufacture investment eligibility');
  for (const record of samples) {
    const id = record.projectionRecord.id, expected = record.reconciliation;
    const mission = native.summary.missions.find(row => row.missionId === id);
    assert(mission, `${id}: native summary missing`);
    assert.equal(mission.acceptance, 'unknown');
    assert.equal(mission.assumedPrice, expected.modeledCollectionsMinor);
    assert.equal(mission.scenario.fullCost, expected.accruedCostMinor);
    assert.equal(mission.scenario.reserve, expected.nativeSeparateWarrantyReserveMinor);
    assert.equal(mission.scenario.unpaidObligations, expected.nativeUnaccruedObligationsMinor);
    assert.equal(mission.scenario.afterReserves, expected.expectedNativeAfterReservesMinor);
    const receipt = native.ledger.events.find(row => row.missionId === id &&
      row.type === 'revenue' && row.category === 'collected');
    assert.deepEqual([receipt.amountMinor, receipt.basis], [null, 'unknown']);
    const price = native.ledger.events.find(row => row.missionId === id &&
      row.type === 'revenue' && row.category === 'price');
    assert.deepEqual([price.amountMinor, price.basis], [expected.modeledCollectionsMinor, 'assumed']);
    record.nativeSummary = mission;
  }
  assert.equal(native.summary.scenario.reserve,
    sum(samples.map(row => row.projectionRecord.reserveMinor)));
  assert.equal(native.summary.scenario.unpaidObligations,
    sum(samples.map(row => row.projectionRecord.obligationMinor)));
  for (const [name, before] of Object.entries(sourceFiles)) {
    assert.equal(sha(readFileSync(join(root, name))), before.sha256, `Source changed during projection: ${name}`);
  }
  return {
    schema: SCHEMA,
    evidenceKind: 'ACTUAL local native-arithmetic execution over completed SIMULATED confirmation samples',
    runtime: process.version,
    protocolSha256: PROTOCOL,
    sourceFiles,
    nativeSource: {repository: foundations.vendored_source.repository,
      commit: foundations.vendored_source.commit, entryPoint: adapter.path,
      canonicalArithmetic: 'vendor/native-accounting/shadow-ledger.mjs#replayLedger',
      vendorAndExistingAdapterUnchanged: true, upstreamReleaseQualification: false},
    selection: {sampleCount: samples.length, seed, scenarios: Object.keys(freeze.scenarios).sort(),
      arms: freeze.arms, rule: 'First predeclared confirmation seed, every primary scenario and arm',
      matchedCompletedConfirmationRows: samples.length, completedConfirmationRows: confirmations.size},
    mapping: Object.fromEntries(Object.entries(MAPPING).map(([name, [book, category]]) =>
      [name, {sourceBook: book, nativeCategory: category}])),
    accountingRules: [
      'Every accrued expense row enters exactly one native category. Historical learning memos are not extra costs.',
      'A delivery maps to delivery; initial B retention and optional C map to capability; ' +
        'B upkeep maps to maintenance.',
      'Common setup and infrastructure map to business. This presentation changes no source expense or cash event.',
      'Modeled collections are supplied only as assumed-price events; observed collected receipts remain unknown.',
      'Each record is an aggregate modeled world, so native acceptance and investment eligibility remain unknown.',
      'Accrued unpaid expenses remain in full cost, not a second obligation deduction.',
      'All outstanding funded commitments, including A/B/C commitments, enter unaccrued closing obligations once.',
      'The native unpaidObligations field carries those unaccrued amounts, ' +
        'not another charge for accrued unpaid costs.',
      'Separate reserve excludes those commitments and preserves the remaining warranty/protected-cash reserve.',
      'Original closing obligations and protected cash are preserved with their full decomposition in each sidecar.',
      'Totals across scenarios and counterfactual arms are arithmetic checksums, not one investable enterprise.'
    ],
    boundedInput: {records: samples.length, serializedCharacters: serialized.length,
      sha256: sha(serialized), maximumCharacters: 250000, eachRecordBelowBytes: 4096},
    assertions: {
      frozenScientificSourcesUnchanged: true, canonicalNativeSourceHashesMatch: true,
      completeSampleMatrixAndConfirmationMatch: true, fullSourceCostBooksPartitionAllExpenses: true,
      nativeCostsMatchSourcePerSampleAndAggregate: true, originalClosingComponentsPreservedWithoutDoubleCharge: true,
      modeledCollectionsRemainAssumedPrice: true, observedFinancialFieldsRemainUnknown: true,
      nativeAutomaticReinvestmentBps: 0, allSourceHashesUnchangedDuringExecution: true
    },
    aggregateArithmeticChecksum: {costCategoriesMinor: expectedCategories, sourceAccruedCostsMinor: totalCost,
      nativeFullCostMinor: native.summary.scenario.fullCost,
      differenceMinor: native.summary.scenario.fullCost - totalCost,
      expenseRowsMappedOnce: sum(samples.map(row => row.sample.sourceExpenseRows)),
      scope: 'Sum over twelve alternative simulated worlds; not a pooled operating account or cash claim'},
    samples,
    nativeProjection: native,
    actualActivity: {nativeMissions: 0, realizedCollections: 0, transactions: 0, deployments: 0,
      liveEnsEnforcement: false, productionAuthorityGranted: false},
    limitations: [
      'This is actual reuse of canonical arithmetic on recorded simulated data, not native service integration.',
      'The native scenario revenue label is supplied assumed-price arithmetic, not observed revenue or a quoted offer.',
      'The independent simulator retains responsibility for cash chronology, reservations, ' +
        'buyer outcomes and policies.',
      'This projection runs no new economic worlds, changes no confirmation outcome and grants no spending permission.',
      'The twelve sample worlds are coupled scenario/arm examples and do not replace ' +
        'the complete confirmation analysis.',
      'Local Node execution does not qualify the upstream installed, hosted or production release environment.'
    ]
  };
}

function main() {
  const args = process.argv.slice(2);
  assert(args.length === 0 || (args.length === 2 && ['--out', '--verify'].includes(args[0])),
    'Usage: node analysis/project_confirmed_accounting.mjs [--out FILE | --verify FILE]');
  const output = resolve(args[1] ?? join(ROOT, 'evidence/native_confirmed_projection.json'));
  const result = projectConfirmedSamples();
  if (args[0] === '--verify') {
    assert.equal(stable(result), stable(JSON.parse(readFileSync(output, 'utf8'))),
      'Retained native confirmed projection does not replay exactly');
  } else {
    writeFileSync(output, JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
  }
  process.stdout.write(JSON.stringify({output, verified: args[0] === '--verify', samples: result.samples.length,
    costDifferenceMinor: result.aggregateArithmeticChecksum.differenceMinor,
    fullCostChecksumMinor: result.aggregateArithmeticChecksum.nativeFullCostMinor,
    observedRevenue: result.nativeProjection.summary.observed.revenue,
    observedSurplus: result.nativeProjection.summary.observed.availableSurplus}) + '\n');
}

if (process.argv[1] && resolve(process.argv[1]) === SCRIPT) main();
