// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import test from 'node:test';
import * as alpha from './engine.mjs';
import * as project from './project.mjs';
import { canonical, parseBounded } from '../../docs/assets/successor/engine.mjs';
import { constructPlans, validatePlan, executePlan, discoverStrategy, validateResearch,
    strategyExampleMission, resolveDiscrepancies, validateResolution } from './research.mjs';

const sourceHash = 'a'.repeat(64);
const source = () => alpha.createJoinMission({ leftCsv: 'id,value\na,one\na,two\nmissing,L\nmissing,L2',
    rightCsv: 'key,value\na,one\na,three\nother,R\nother,R2', leftKey: 'id', rightKey: 'key' });

test('constructor combines reviewed operators into twenty bounded programs rather than selecting engine strategies', () => {
    const plans = constructPlans({ maxAuxiliaryRows: 64 });
    assert.equal(plans.length, 20);
    assert.equal(new Set(plans.map(plan => JSON.stringify(plan))).size, plans.length);
    assert.ok(plans.some(plan => plan.guard.op === 'uniform_key' && plan.split.buckets === 8));
    assert.ok(plans.some(plan => plan.leaf.maxProduct === 16 && plan.leaf.large.side === 'smaller'));
    assert.ok(plans.every(plan => validatePlan(plan)));
});

test('untrusted programs cannot inject operators, code, unsupported budgets, or extra fields', () => {
    const good = constructPlans()[0];
    for (const mutate of [plan => { plan.leaf.large.op = 'eval'; }, plan => { plan.extra = 'authority'; },
        plan => { plan.guard.op = 'shell'; }, plan => { plan.split.buckets = 1000; },
        plan => { plan.leaf.large.rows = 0; }, plan => { plan.leaf.maxProduct = 2250001; },
        plan => { plan.leaf.maxProduct = -0; }]) {
        const plan = structuredClone(good); mutate(plan); assert.throws(() => validatePlan(plan));
    }
    assert.throws(() => constructPlans({ maxAuxiliaryRows: -1 }));
    assert.throws(() => constructPlans({ maxAuxiliaryRows: -0 }));
});

test('every constructed workflow preserves exact duplicate joins, including hash collisions and Unicode keys', () => {
    const mission = alpha.createJoinMission({ leftCsv: 'id,value\né,A\na,B\na,C\n中,D\nonly,E',
        rightCsv: 'id,value\na,X\né,Y\na,Z\n中,W', leftKey: 'id', rightKey: 'id' });
    const expected = alpha.executeJoin(mission, 'nested_scan').pairs;
    for (const plan of constructPlans({ maxAuxiliaryRows: 2 })) {
        const execution = executePlan(mission, plan);
        assert.deepEqual(execution.pairs, expected);
        assert.equal(execution.correct, true);
        assert.ok(Number.isSafeInteger(execution.metrics.logicalOperations));
    }
});

test('routing work and temporary partition references are metered instead of disappearing from objective', () => {
    const mission = source(), plans = constructPlans({ maxAuxiliaryRows: 2 });
    const direct = executePlan(mission, plans[0]);
    const partitioned = executePlan(mission, plans.find(plan => plan.split.buckets === 4 && plan.guard.op === 'none'));
    assert.equal(direct.metrics.routingTests, 0);
    assert.equal(partitioned.metrics.routingTests, 4 * (mission.left.rows.length + mission.right.rows.length));
    assert.ok(partitioned.metrics.routingCharacters > 0);
    assert.ok(partitioned.metrics.peakAuxiliaryRows >= 2);
});

test('uniform guard preserves the full Cartesian multiplicity for matching constants and no pairs for disjoint constants', () => {
    const plan = constructPlans().find(item => item.guard.op === 'uniform_key' && item.split.buckets === 1);
    for (const [rightKey, count] of [['same', 6], ['different', 0]]) {
        const mission = alpha.createJoinMission({ leftCsv: 'id\nsame\nsame\nsame',
            rightCsv: `id\n${rightKey}\n${rightKey}`, leftKey: 'id', rightKey: 'id' });
        const execution = executePlan(mission, plan);
        assert.equal(execution.pairs.length, count);
        assert.deepEqual(execution.pairs, alpha.executeJoin(mission, 'nested_scan').pairs);
        assert.equal(execution.metrics.keyComparisons, 6);
        assert.equal(execution.metrics.hashInsertions, 0);
        assert.equal(execution.metrics.peakAuxiliaryRows, 0);
    }
});

test('constructed uniform-key shortcut earns only a local improvement against competitive feasible joins', async () => {
    const mission = strategyExampleMission();
    const report = await discoverStrategy(mission, { sourceHash, maxAuxiliaryRows: 64, auxiliaryWeight: 0, confirmationSeed: 19 });
    assert.equal(report.decision.state, 'local_improvement');
    assert.equal(report.decision.promoted, true);
    assert.equal(report.frozen.plan.guard.op, 'uniform_key');
    assert.ok(report.confirmation.candidate.objectiveValue < report.confirmation.incumbent.objectiveValue);
    assert.ok(report.confirmation.baselines.filter(record => record.feasible)
        .every(record => record.objectiveValue > report.confirmation.candidate.objectiveValue));
    assert.equal(report.evaluationLedger.development.planExecutions, 27);
    assert.equal(report.evaluationLedger.confirmation.planExecutions, 8);
    assert.equal(report.evaluationLedger.development.independentReferenceComparisons,
        27 * mission.left.rows.length * mission.right.rows.length);
    assert.equal(report.independentlyQualified, false); assert.equal(report.protectedHoldout, false);
    assert.equal(report.confirmation.protected, false); assert.equal(report.externalAuthority, false);
    assert.equal(report.modelUsed, false); assert.equal(report.algorithmNoveltyClaim, false);
    assert.match(report.frozen.commitment, /^[0-9a-f]{64}$/);
    assert.notEqual(report.missionHash, report.confirmation.missionHash);
    assert.equal((await validateResearch(report, mission, { sourceHash })).valid, true);
});

test('two ordinary and strategy-example cycles plus validated learning records round-trip the actual strict project codec', async () => {
    let dossier = project.createProject();
    const records = [];
    for (const mission of [alpha.createSampleMission(), strategyExampleMission()]) {
        const result = await alpha.runJoinExperiment(mission);
        dossier = project.appendCycle(dossier, { mission, result, sourceHash });
        const strategy = await discoverStrategy(mission, { sourceHash, confirmationSeed: 29 });
        const resolution = resolveDiscrepancies(mission, result);
        records.push({ cycleId: dossier.cycles.at(-1).id, strategy, resolution });
    }
    const native = project.serializeProject(dossier);
    assert.equal(project.inspectProject(native).cycles.length, 2);
    const bundle = { schema: 'successor-alpha-learning/v1', project: dossier, records };
    const serialized = canonical(bundle), imported = parseBounded(serialized);
    assert.ok(new TextEncoder().encode(serialized).length < 2000000);
    assert.equal(imported.project.cycles.length, 2);
    for (let index = 0; index < imported.records.length; index += 1) {
        const record = imported.records[index], cycle = imported.project.cycles[index];
        assert.equal((await validateResearch(record.strategy, cycle.mission, { sourceHash })).valid, true);
        assert.equal(validateResolution(record.resolution, cycle.mission, cycle.result).valid, true);
    }
    const final = imported.records.at(-1);
    assert.equal(imported.project.cycles.at(-1).result.reconciliation.matchedPairs, 0);
    assert.equal(final.strategy.decision.state, 'local_improvement');
    assert.equal(final.resolution.actions.length, 2);
    assert.equal(final.resolution.decision.state, 'offer_key_queue');
    assert.equal(final.resolution.coverage.originalOccurrences, 131);
});

test('default ordinary catalog holds the strongest feasible incumbent when construction does not improve work', async () => {
    const report = await discoverStrategy(alpha.createSampleMission(), { sourceHash, confirmationSeed: 81 });
    assert.equal(report.decision.state, 'held');
    assert.equal(report.decision.promoted, false);
    assert.equal(report.decision.retainedPlanHash, report.incumbent.planHash);
    assert.ok(report.baselines.some(record => !record.feasible));
    assert.ok(report.incumbent.feasible);
    assert.equal(report.objective.maxAuxiliaryRows, 64); assert.equal(report.objective.auxiliaryWeight, 0);
});

test('zero auxiliary budget remains executable with an exact index-free baseline', async () => {
    const report = await discoverStrategy(source(), { sourceHash, maxAuxiliaryRows: 0, confirmationSeed: 11 });
    assert.equal(report.incumbent.metrics.peakAuxiliaryRows, 0);
    assert.ok(report.candidates.filter(record => record.feasible).every(record => record.metrics.peakAuxiliaryRows === 0));
    assert.ok(report.baselines.some(record => !record.feasible));
});

test('construction is reproducible for a source, mission, objective and disclosed confirmation seed', async () => {
    const mission = source(), options = { sourceHash, maxAuxiliaryRows: 3, auxiliaryWeight: 2, confirmationSeed: 23 };
    assert.deepEqual(await discoverStrategy(mission, options), await discoverStrategy(mission, options));
});

test('confirmation refuses to reuse the exact development input even when a caller repeats its seed', async () => {
    const mission = alpha.createSampleMission({ seed: 41 });
    const report = await discoverStrategy(mission, { sourceHash, confirmationSeed: 41 });
    assert.notEqual(report.missionHash, report.confirmation.missionHash);
    assert.notEqual(report.confirmation.seed, 41);
    assert.equal((await validateResearch(report, mission, { sourceHash })).valid, true);
});

test('import verification rejects forged objectives, source identity, plans, hashes, confirmation or promotion', async () => {
    const mission = source();
    const report = await discoverStrategy(mission, { sourceHash, confirmationSeed: 12 });
    for (const mutate of [copy => { copy.objective.maxAuxiliaryRows += 1; },
        copy => { copy.candidates[0].metrics.logicalOperations -= 1; },
        copy => { copy.frozen.plan.leaf.large.op = 'external_execute'; },
        copy => { copy.frozen.commitment = '0'.repeat(64); },
        copy => { copy.confirmation.protected = true; }, copy => { copy.decision.promoted = !copy.decision.promoted; },
        copy => { copy.independentlyQualified = true; }, copy => { copy.externalAuthority = true; }]) {
        const forged = structuredClone(report); mutate(forged);
        await assert.rejects(validateResearch(forged, mission, { sourceHash }));
    }
    await assert.rejects(validateResearch(report, mission, { sourceHash: 'b'.repeat(64) }));
});

test('cancellation between constructions prevents a retained partial result', async () => {
    const controller = new AbortController();
    await assert.rejects(discoverStrategy(source(), { sourceHash, signal: controller.signal,
        onProgress: event => { if (event.stage === 'construction') controller.abort(); } }), /stopped/);
});

test('reframing groups each exact key while covering every unmatched row and conflicting original pair', async () => {
    const mission = source(), experiment = await alpha.runJoinExperiment(mission);
    const report = resolveDiscrepancies(mission, experiment);
    assert.equal(report.actions.length, 3);
    assert.equal(report.burden.pairwiseReviewItems, 7);
    assert.equal(report.burden.groupedActions, 3);
    assert.equal(report.burden.groupingReduction, 4);
    assert.equal(report.contract.changed, true);
    assert.equal(report.decision.state, 'offer_key_queue');
    assert.equal(report.diagnosis.duplicateExceptionKeys, 3);
    assert.equal(report.burden.sameTaskSuperiority, false); assert.equal(report.burden.timeSavedClaim, false);
    const occurrences = report.actions.flatMap(action => action.occurrences);
    assert.deepEqual(new Set(occurrences), new Set(['left:2', 'left:3', 'right:2', 'right:3',
        'conflict:0:1', 'conflict:1:0', 'conflict:1:1']));
    assert.equal(occurrences.length, new Set(occurrences).size);
    assert.equal(report.coverage.complete, true);
    assert.equal(report.automaticallyResolved, false);
    assert.equal(validateResolution(report, mission, experiment).valid, true);
    assert.equal(alpha.parseCsv(report.actionsCsv).rows.length, 3);
});

test('reframing refuses omitted, duplicated, or fabricated underlying evidence', () => {
    const mission = source(), report = resolveDiscrepancies(mission);
    for (const mutate of [copy => { copy.actions.pop(); }, copy => { copy.actions[0].occurrences.push('left:2'); },
        copy => { copy.actions[0].leftRows = [999]; }, copy => { copy.coverage.complete = false; },
        copy => { copy.contract.changed = false; }, copy => { copy.automaticallyResolved = true; },
        copy => { copy.actionsCsv = 'not the data'; }]) {
        const forged = structuredClone(report); mutate(forged);
        assert.throws(() => validateResolution(forged, mission));
    }
});

test('reframing exact-key strings cannot become object properties or spreadsheet formulas', () => {
    const mission = alpha.createJoinMission({ leftCsv: 'id,value\n__proto__,a\n=1+1,b',
        rightCsv: 'id,value\n__proto__,changed\nright,c', leftKey: 'id', rightKey: 'id' });
    const report = resolveDiscrepancies(mission);
    assert.ok(report.actions.some(action => action.key === '__proto__'));
    assert.ok(report.actionsCsv.includes("'=1+1"));
    assert.equal(validateResolution(report, mission).valid, true);
});

test('a catalog without discrepancies yields an empty complete action plan', () => {
    const mission = alpha.createJoinMission({ leftCsv: 'id,value\na,one', rightCsv: 'id,value\na,one', leftKey: 'id', rightKey: 'id' });
    const report = resolveDiscrepancies(mission);
    assert.deepEqual(report.actions, []);
    assert.equal(report.coverage.originalOccurrences, 0);
    assert.equal(report.coverage.complete, true);
    assert.equal(report.decision.state, 'retain_original_review');
    assert.equal(alpha.parseCsv(report.actionsCsv).rows.length, 0);
});

test('distinct exception keys retain the original task instead of declaring regrouping useful', () => {
    const mission = alpha.createJoinMission({ leftCsv: 'id,value\na,left\nb,only', rightCsv: 'id,value\na,right\nc,only',
        leftKey: 'id', rightKey: 'id' });
    const report = resolveDiscrepancies(mission);
    assert.equal(report.burden.pairwiseReviewItems, 3);
    assert.equal(report.burden.groupedActions, 3);
    assert.equal(report.diagnosis.duplicateExceptionKeys, 0);
    assert.equal(report.diagnosis.groupingReducesDecisionItems, false);
    assert.equal(report.decision.state, 'retain_original_review');
    assert.equal(validateResolution(report, mission).valid, true);
});
