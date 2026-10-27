// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { PRESETS, runSimulation, optimizePolicy, engineeringSample, exportSimulation, importSimulation, createPublicSkillRegistry, DEVELOPMENT_SEEDS } from './engine.mjs';

const near = (a, b) => assert.ok(Math.abs(a - b) < 0.011, `${a} != ${b}`);
const candidate = id => ({ id, originatingMission: 'public-job-001', implementation: 'Public method', scope: 'single-station', rights: 'PUBLIC_EXAMPLE_APACHE_2.0' });
function admitted(registry, id = 'public-method', components = []) {
  registry.create({ ...candidate(id), components });
  registry.evidence(id, { kind: 'PUBLIC_FRESH_FIXTURE', fresh: true, criteria: 'Correct new windows and lower cost', taskFamily: 'unseen-window-fixture', benefit: 900, incrementalCost: 300 });
  registry.assess(id);
  registry.validate(id, { freshPass: true, baseline: 'frontier-beta/1', independentCheck: true, compositionChecked: true });
  return registry.admit(id);
}

test('worked sample actually enumerates a feasible better plan in the declared finite space', () => {
  const sample = engineeringSample();
  assert.equal(sample.objective, 17); assert.equal(sample.baselineObjective, 15);
  assert.equal(sample.checkedSubsets, 32); assert.equal(sample.feasible, true);
  assert.deepEqual(sample.schedule.map(row => row.id), ['boreal', 'cirrus', 'delta']);
  assert.equal(sample.authority.length, 0);
});

test('same configuration replays exactly and model calls remain absent', () => {
  const a = runSimulation({ seed: 42 }), b = runSimulation({ seed: 42 });
  assert.deepEqual(a, b); assert.equal(a.mode, 'SIMULATION'); assert.deepEqual(a.models.executed, []);
  assert.ok(Array.from({ length: 20 }, (_, seed) => runSimulation({ seed }).ledger).some(ledger => JSON.stringify(ledger) !== JSON.stringify(a.ledger)));
});

test('finite price optimization uses declared choices and has no forced discount or investment', () => {
  const selection = optimizePolicy('baseline');
  assert.ok(selection.searchSpace.prices.includes(selection.price));
  assert.equal(selection.searchSpace.policies.length, 4);
  assert.notEqual(selection.price, 21600);
  for (const row of selection.search) if (row.feasible) assert.ok(row.expectedProfit <= selection.expectedProfit);
  const r = runSimulation({ policy: 'beta' });
  assert.ok(r.summary.profit > 0); assert.equal(r.summary.costsB, 0); assert.equal(r.summary.costsC, 0);
  assert.equal(r.retention.decision, 'NOT_RETAINED');
});

test('all three cost accounts reconcile and charge each activity once', () => {
  for (const preset of PRESETS) for (const policy of ['auto', 'beta', 'retain', 'invest', 'bundle']) for (const seed of [0, 1, 42, 77, 812]) {
    const r = runSimulation({ preset: preset.id, policy, seed });
    const rows = Object.values(r.accounts).flat(), s = r.summary;
    assert.equal(new Set(rows.map(row => row.id)).size, rows.length);
    assert.ok(rows.every(row => row.amount >= 0));
    near(rows.reduce((a, row) => a + row.amount, 0), s.costs);
    near(s.collections, s.grossReceipts - s.refunds);
    near(s.profit, s.collections - s.costs);
    near(s.cash, s.seedCapital + s.collections - s.paidCosts);
    near(s.paidCosts + s.obligations, s.costs);
    near(s.availableFunds, Math.max(0, s.cash - s.reserves - s.obligations));
    near(s.qualityLinkedProfit, s.qualityLinkedReceipts - s.costs);
    assert.ok(r.ledger.every(row => row.endCash >= s.reserves));
    assert.ok(r.ledger.every((row, i) => row.day <= 90 && (!i || row.startedDay >= r.ledger[i - 1].day)));
    assert.ok(!r.accounts.B.some(row => row.activity === 'reasoning-learning-development'));
  }
});

test('retention uses only incremental costs and pays assessment for rejected candidates', () => {
  const r = runSimulation({ policy: 'retain' });
  assert.equal(r.retention.decision, 'RETAINED_SIMULATION');
  assert.equal(r.summary.costsB, 1060); assert.equal(r.retention.breakEvenReuse, 2);
  assert.ok(r.ledger.some(row => row.reuseSaving > 0));
  assert.equal(r.ledger[0].reuseSaving, 0);
  const frontier = runSimulation({ preset: 'frontier', policy: 'retain' });
  assert.equal(frontier.retention.decision, 'REJECTED_SIMULATION');
  assert.equal(frontier.summary.costsB, 120); assert.ok(frontier.summary.profit > 0);
  assert.equal(runSimulation({ preset: 'frontier' }).selected.policy, 'beta');
});

test('complementary bundle is assessed as a bundle and optional investment is charged separately', () => {
  const r = runSimulation({ policy: 'bundle' });
  assert.equal(r.summary.costsC, 3600); assert.equal(r.summary.costsB, 1060);
  assert.equal(r.accounts.C.length, 1);
  assert.ok(r.selected.allocation.bundleNet > 0);
  assert.ok(r.accounts.A.every(row => row.amount >= 0));
  assert.equal(runSimulation({ policy: 'invest' }).summary.costsC, 0);
});

test('errors retain correction/refusal/refund costs and quality sensitivity never refunds twice', () => {
  let falsePass, refusal, correction;
  for (let seed = 0; seed < 400; seed++) {
    const r = runSimulation({ preset: 'stress', policy: 'beta', seed });
    if (r.summary.falseAcceptances) falsePass ??= r;
    if (r.summary.refused) refusal ??= r;
    if (r.summary.corrected) correction ??= r;
  }
  assert.ok(falsePass); assert.ok(refusal); assert.ok(correction);
  const s = falsePass.summary;
  near(s.refunds, s.falseAcceptances * s.offeredPrice);
  assert.ok(falsePass.accounts.A.some(row => row.activity === 'collection-processing'));
  assert.ok(refusal.accounts.A.some(row => row.activity === 'correction-and-recheck'));
  assert.ok(s.qualityLinkedReceipts <= s.collections);
  near(s.qualityLinkedProfit, s.qualityLinkedReceipts - s.costs);
});

test('finite cash refuses additional jobs before spending reserved or obligated funds', () => {
  const r = runSimulation({ preset: 'stress', policy: 'bundle', price: 1000, seed: 7 });
  assert.ok(r.summary.cashShortfalls > 0);
  assert.ok(r.opportunities.some(row => row.choice === 'cash-refused'));
  assert.ok(r.summary.cash >= r.summary.reserves + r.summary.obligations);
  assert.ok(r.summary.profit < 0);
});

test('imports replay inputs and reject substituted results, malformed and incompatible files', () => {
  const r = runSimulation({ preset: 'stress', seed: 11 });
  const text = exportSimulation(r, 'fr'), restored = importSimulation(text);
  assert.equal(restored.language, 'fr'); assert.deepEqual(restored.result, r);
  assert.throws(() => importSimulation('{'), /INVALID_IMPORT/);
  assert.throws(() => importSimulation('x'.repeat(4097)), /INVALID_IMPORT/);
  assert.throws(() => importSimulation(text.replace('alpha-flywheel-model/1.0.0', 'unknown')), /INCOMPATIBLE_REPLAY/);
  const attack = JSON.parse(text); attack.input.profit = 1000000;
  assert.throws(() => importSimulation(JSON.stringify(attack)), /INVALID_IMPORT/);
  for (const options of [{ preset: 'missing' }, { seed: -1 }, { seed: NaN }, { price: Infinity }, { price: -1 }, { price: 1 }, { policy: 'magic' }]) assert.throws(() => runSimulation(options));
});

test('canonical promotion requires fresh evidence, net assessment and validation', () => {
  const registry = createPublicSkillRegistry();
  registry.create(candidate('public-method'));
  assert.throws(() => registry.admit('public-method'), /ADMISSION_REQUIRED/);
  assert.throws(() => registry.validate('public-method', { freshPass: true }), /FRESH_VALIDATION_REQUIRED/);
  assert.throws(() => registry.evidence('public-method', { fresh: false }), /FRESH_EVIDENCE_REQUIRED/);
  registry.evidence('public-method', { kind: 'PUBLIC_FRESH_FIXTURE', fresh: true, criteria: 'Fresh correctness', taskFamily: 'new', benefit: 400, incrementalCost: 200 });
  registry.assess('public-method');
  registry.validate('public-method', { freshPass: true, baseline: 'frontier-beta/1', independentCheck: true });
  registry.admit('public-method');
  assert.equal(registry.discover().length, 1);
  assert.throws(() => registry.reuse('public-method', { scope: 'single-station' }), /FIXTURE_AUTHORIZATION_REQUIRED/);
  assert.equal(registry.reuse('public-method', { scope: 'single-station', fixtureEligible: true }).mode, 'PUBLIC_FIXTURE_REUSE');
  assert.throws(() => registry.reuse('public-method', { scope: 'other', fixtureEligible: true }), /CURRENT_APPLICABLE_ADMISSION_REQUIRED/);
  assert.throws(() => registry.reuse('public-method', { day: 90, scope: 'single-station', fixtureEligible: true }), /CURRENT_APPLICABLE_ADMISSION_REQUIRED/);
});

test('rejected novelty and duplicate methods remain failure memory, never positive skills', () => {
  const registry = createPublicSkillRegistry();
  for (const [id, benefit, duplicate] of [['uneconomic', 100, false], ['duplicate', 1000, true]]) {
    registry.create(candidate(id));
    registry.evidence(id, { kind: 'PUBLIC_FRESH_FIXTURE', fresh: true, criteria: 'Net new benefit', taskFamily: 'fresh', benefit, incrementalCost: 300, duplicate });
    assert.equal(registry.assess(id).status, 'REJECTED');
    assert.throws(() => registry.admit(id), /ADMISSION_REQUIRED/);
  }
  assert.equal(registry.discover().length, 0); assert.equal(registry.failures().length, 2);
  assert.equal(registry.failures().reduce((n, row) => n + row.assessmentCost, 0), 240);
});

test('baseline changes disable reuse until fresh requalification or ordinary-Beta retirement', () => {
  const registry = createPublicSkillRegistry(); admitted(registry);
  registry.baselineChanged('frontier-beta/2'); assert.equal(registry.discover().length, 0);
  assert.throws(() => registry.reuse('public-method', { scope: 'single-station', fixtureEligible: true }), /CURRENT_APPLICABLE_ADMISSION_REQUIRED/);
  assert.throws(() => registry.revalidate('public-method', { baseline: 'frontier-beta/2', outcome: 'retains', benefit: 600, incrementalCost: 120 }), /FRESH_NET_ADVANTAGE_REQUIRED/);
  registry.revalidate('public-method', { baseline: 'frontier-beta/2', outcome: 'retains', freshPass: true, independentCheck: true, benefit: 600, incrementalCost: 120 });
  assert.equal(registry.discover().length, 1);
  registry.baselineChanged('frontier-beta/3');
  registry.revalidate('public-method', { baseline: 'frontier-beta/3', outcome: 'ordinary-beta' });
  assert.equal(registry.inspect('public-method').status, 'RETIRED');
  assert.throws(() => registry.admit('public-method'), /TERMINAL_SKILL/);
});

test('revoked or retired skill cannot revive from copied history or returned records', () => {
  const registry = createPublicSkillRegistry(); const saved = admitted(registry);
  registry.revoke('public-method'); saved.status = 'ADMITTED';
  const history = registry.history(); history.at(-1).status = 'ADMITTED';
  assert.equal(registry.discover().length, 0); assert.equal(registry.inspect('public-method').status, 'REVOKED');
  assert.throws(() => registry.create(candidate('public-method')), /INVALID_OR_DUPLICATE_CANDIDATE/);
  assert.throws(() => registry.admit('public-method'), /TERMINAL_SKILL/);
  assert.throws(() => registry.reuse('public-method', { scope: 'single-station', fixtureEligible: true }), /CURRENT_APPLICABLE_ADMISSION_REQUIRED/);
  assert.equal(registry.qualification().liveIdentityQualified, false);
});

test('compositions need their own evidence and validation, then follow current component status', () => {
  const registry = createPublicSkillRegistry(); admitted(registry, 'part-one'); admitted(registry, 'part-two');
  registry.create({ ...candidate('composed-method'), components: ['part-one', 'part-two'] });
  registry.evidence('composed-method', { kind: 'PUBLIC_FRESH_FIXTURE', fresh: true, criteria: 'Bundle net effect', taskFamily: 'new-composition', benefit: 900, incrementalCost: 400 });
  registry.assess('composed-method');
  assert.throws(() => registry.validate('composed-method', { freshPass: true, baseline: 'frontier-beta/1', independentCheck: true }), /FRESH_VALIDATION_REQUIRED/);
  registry.validate('composed-method', { freshPass: true, baseline: 'frontier-beta/1', independentCheck: true, compositionChecked: true });
  registry.admit('composed-method'); assert.equal(registry.discover().length, 3);
  registry.revoke('part-one'); assert.equal(registry.discover().length, 1);
  assert.throws(() => registry.reuse('composed-method', { scope: 'single-station', fixtureEligible: true }), /CURRENT_APPLICABLE_ADMISSION_REQUIRED/);
});

test('price-policy ranking uses actual reconciled development ledgers and never the replay seed', () => {
  const selected = optimizePolicy('stress');
  assert.deepEqual(selected.searchSpace.scenarioSeeds, DEVELOPMENT_SEEDS);
  const profits = DEVELOPMENT_SEEDS.map(seed => runSimulation({ preset: 'stress', seed, price: selected.price, policy: selected.policy }).summary.profit);
  near(selected.expectedProfit, profits.reduce((total, value) => total + value, 0) / profits.length);
  assert.equal(selected.development.minimumProfit, Math.min(...profits));
  assert.equal(selected.development.lossCount, profits.filter(value => value < 0).length);
  assert.deepEqual(runSimulation({ preset: 'stress', seed: 1 }).selected, runSimulation({ preset: 'stress', seed: 999 }).selected);
});

test('unpaid support is expensed once, remains payable and is excluded from available cash', () => {
  const r = runSimulation({ policy: 'beta' }), s = r.summary;
  const accruals = r.accounts.A.filter(row => row.activity === 'unpaid-support-accrual');
  assert.equal(accruals.length, s.accepted); assert.ok(accruals.every(row => row.cashPaid === false));
  near(accruals.reduce((total, row) => total + row.amount, 0), s.obligations);
  near(s.paidCosts, Object.values(r.accounts).flat().filter(row => row.cashPaid).reduce((total, row) => total + row.amount, 0));
  near(s.profit, s.cash - s.seedCapital - s.obligations);
  near(s.availableFunds, s.cash - s.reserves - s.obligations);
  assert.equal(r.unitEconomics.baseDelivery, 2660);
  near(r.unitEconomics.maximumCompleteDeliveryEnvelope, (2660 + 450) * r.unitEconomics.costMultiplier + s.offeredPrice * 0.029 + 1500 + 150);
});

test('requalification rejects coercion/nonfinite costs and requires fresh current composition validation', () => {
  const registry = createPublicSkillRegistry(); admitted(registry, 'part-one'); admitted(registry, 'part-two');
  admitted(registry, 'composed-method', ['part-one', 'part-two']);
  registry.baselineChanged('frontier-beta/2');
  const valid = { baseline: 'frontier-beta/2', outcome: 'retains', freshPass: true, independentCheck: true, benefit: 600, incrementalCost: 120 };
  for (const invalid of [-1, Infinity, NaN, '120']) assert.throws(() => registry.revalidate('part-one', { ...valid, incrementalCost: invalid }), /INVALID_INCREMENTAL_COST/);
  for (const invalid of [Infinity, NaN, '600']) assert.throws(() => registry.revalidate('part-one', { ...valid, benefit: invalid }), /INVALID_BENEFIT/);
  assert.throws(() => registry.revalidate('composed-method', { ...valid, compositionChecked: true }), /FRESH_NET_ADVANTAGE_REQUIRED/);
  registry.revalidate('part-one', valid); registry.revalidate('part-two', valid);
  assert.throws(() => registry.revalidate('composed-method', valid), /FRESH_NET_ADVANTAGE_REQUIRED/);
  registry.revalidate('composed-method', { ...valid, compositionChecked: true });
  assert.equal(registry.discover().length, 3);
});

test('every pending admission stage restarts against changed Beta and can complete a fully fresh admission', () => {
  for (const pendingStatus of ['CANDIDATE', 'EVIDENCE', 'ASSESSED', 'VALIDATED']) {
    const registry = createPublicSkillRegistry(), id = 'pending-method';
    const evidence = { kind: 'PUBLIC_FRESH_FIXTURE', fresh: true, criteria: 'Original baseline criterion', taskFamily: 'original-fixture', benefit: 600, incrementalCost: 200 };
    registry.create(candidate(id));
    if (pendingStatus !== 'CANDIDATE') registry.evidence(id, evidence);
    if (['ASSESSED', 'VALIDATED'].includes(pendingStatus)) registry.assess(id);
    if (pendingStatus === 'VALIDATED') registry.validate(id, { freshPass: true, baseline: 'frontier-beta/1', independentCheck: true });
    const previous = registry.inspect(id), priorHistory = registry.history();
    assert.equal(previous.status, pendingStatus);
    registry.baselineChanged('frontier-beta/2');
    const restarted = registry.inspect(id), audit = registry.history();
    assert.equal(restarted.status, 'CANDIDATE'); assert.equal(restarted.betaBaseline, 'frontier-beta/2');
    assert.equal(restarted.evidence, null); assert.equal(restarted.assessment, null); assert.equal(restarted.validation, null);
    assert.deepEqual(audit.slice(0, priorHistory.length), priorHistory);
    assert.equal(audit.at(-1).event, 'baseline-restarted'); assert.deepEqual(audit.at(-1).previousState, previous);
    audit.at(-1).previousState.status = 'ADMITTED';
    assert.equal(registry.history().at(-1).previousState.status, pendingStatus);
    assert.equal(registry.discover().length, 0);
    assert.throws(() => registry.admit(id), /ADMISSION_REQUIRED/);
    assert.throws(() => registry.assess(id), /EVIDENCE_REQUIRED/);
    assert.throws(() => registry.validate(id, { freshPass: true, baseline: 'frontier-beta/2', independentCheck: true }), /FRESH_VALIDATION_REQUIRED/);
    assert.throws(() => registry.reuse(id, { scope: 'single-station', fixtureEligible: true }), /CURRENT_APPLICABLE_ADMISSION_REQUIRED/);
    registry.evidence(id, { ...evidence, criteria: 'Fresh new-baseline criterion', taskFamily: 'new-baseline-fixture' });
    registry.assess(id);
    assert.throws(() => registry.validate(id, { freshPass: true, baseline: 'frontier-beta/1', independentCheck: true }), /FRESH_VALIDATION_REQUIRED/);
    registry.validate(id, { freshPass: true, baseline: 'frontier-beta/2', independentCheck: true });
    registry.admit(id);
    assert.equal(registry.reuse(id, { scope: 'single-station', baseline: 'frontier-beta/2', fixtureEligible: true }).skill.status, 'ADMITTED');
  }
});

test('model updates preserve rejected failures and terminal records without restarting them', () => {
  const registry = createPublicSkillRegistry();
  registry.create(candidate('rejected-method'));
  registry.evidence('rejected-method', { kind: 'PUBLIC_FRESH_FIXTURE', fresh: true, criteria: 'Net value', taskFamily: 'fresh', benefit: 100, incrementalCost: 200 });
  registry.assess('rejected-method');
  admitted(registry, 'revoked-method'); registry.revoke('revoked-method');
  admitted(registry, 'retired-method'); registry.retire('retired-method');
  admitted(registry, 'replaced-method'); admitted(registry, 'replacement-method'); registry.supersede('replaced-method', 'replacement-method');
  const ids = ['rejected-method', 'revoked-method', 'retired-method', 'replaced-method'];
  const states = ids.map(id => registry.inspect(id)), failures = registry.failures();
  registry.baselineChanged('frontier-beta/2');
  assert.deepEqual(ids.map(id => registry.inspect(id)), states); assert.deepEqual(registry.failures(), failures);
  assert.equal(registry.discover().length, 0);
  for (const id of ids) assert.throws(() => registry.admit(id));
});

test('restarted compositions require new joint validation and current components at validation and admission', () => {
  const registry = createPublicSkillRegistry(); admitted(registry, 'component-method');
  registry.create({ ...candidate('pending-composition'), components: ['component-method'] });
  const evidence = { kind: 'PUBLIC_FRESH_FIXTURE', fresh: true, criteria: 'New joint advantage', taskFamily: 'new-composition', benefit: 600, incrementalCost: 200 };
  registry.evidence('pending-composition', evidence); registry.assess('pending-composition');
  registry.validate('pending-composition', { freshPass: true, baseline: 'frontier-beta/1', independentCheck: true, compositionChecked: true });
  registry.baselineChanged('frontier-beta/2');
  assert.equal(registry.inspect('pending-composition').status, 'CANDIDATE');
  registry.evidence('pending-composition', evidence); registry.assess('pending-composition');
  const validation = { freshPass: true, baseline: 'frontier-beta/2', independentCheck: true, compositionChecked: true };
  assert.throws(() => registry.validate('pending-composition', validation), /FRESH_VALIDATION_REQUIRED/);
  registry.revalidate('component-method', { ...validation, outcome: 'retains', benefit: 600, incrementalCost: 200 });
  assert.throws(() => registry.validate('pending-composition', { ...validation, compositionChecked: false }), /FRESH_VALIDATION_REQUIRED/);
  registry.validate('pending-composition', validation);
  registry.revoke('component-method');
  assert.throws(() => registry.admit('pending-composition'), /ADMISSION_REQUIRED/);
  assert.equal(registry.discover().length, 0);
});
