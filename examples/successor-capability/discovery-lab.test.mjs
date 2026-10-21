// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_CHARTER, ARTIFACT_KINDS, REPORT_RESERVE_BYTES, validateCharter, parseCharter,
    runCampaign, verifyCampaign, invalidationFor} from './discovery-lab.mjs';
import {canonical} from '../../docs/assets/successor/engine.mjs';
const charter = changes => ({...structuredClone(DEFAULT_CHARTER), ...changes});
const stage = (result, kind) => result.stages.find(record => record.kind === kind);
const base = runCampaign(DEFAULT_CHARTER);

test('one finite campaign constructs all six accepted artifacts and three query families', () => {
    assert.equal(base.state, 'accepted');
    assert.deepEqual(base.stages.map(value => value.kind), ARTIFACT_KINDS);
    assert.ok(base.stages.every(value => value.status === 'accepted' && value.checker.accepted));
    assert.ok(base.queryResults.queriesAfterFreeze);
    assert.ok(base.queryResults.inverseDesign.definite.length);
    assert.equal(base.executionMode, 'free-local-synthetic-replay');
    assert.equal(base.externalExecution, 'unprovisioned');
    assert.deepEqual(base.currencyCaps, {USDC: '0', AGIALPHA: '0'});
    assert.equal(verifyCampaign(DEFAULT_CHARTER, base).verified, true);
    assert.equal(canonical(base), canonical(runCampaign(DEFAULT_CHARTER)));
});

test('charter validation is strict and bounded with duplicate-key/numeric parser rejection', () => {
    for (const changed of [{controls: 5}, {accuracy: 0.5}, {memory: 0}, {intendedUses: Infinity},
        {operations: ['flip-w']}, {faultHypotheses: []}, {checkpoints: ['sterile']}, {extra: true}]) {
        assert.throws(() => validateCharter(charter(changed)));
    }
    assert.throws(() => parseCharter('{"schema":"a","schema":"b"}'));
    assert.throws(() => parseCharter(JSON.stringify(DEFAULT_CHARTER).replace('"accuracy":1', '"accuracy":1.0')));
});

test('charter semantics reject invalid captured controls and budgets masked by property reads', () => {
    for (const key of ['controls', 'budget']) {
        const invalid = charter(key === 'controls' ? {controls: 5}
            : {budget: {...DEFAULT_CHARTER.budget, checking: -1}});
        const input = new Proxy(invalid, {
            get(value, name) { return name === key ? DEFAULT_CHARTER[key] : Reflect.get(value, name); }
        });
        assert.throws(() => validateCharter(input), /Unsupported finite discovery charter/);
    }
});

test('charter validation uses descriptor values without original property reads', () => {
    const expected = charter({}); let reads = 0;
    const trap = {get() { reads++; throw Error('Original charter property was read'); }};
    const input = new Proxy({...expected, budget: new Proxy({...expected.budget}, trap)}, trap);
    assert.deepEqual(validateCharter(input), expected);
    assert.equal(reads, 0);
});

test('charter return retains the validated budget instead of a later JSON property view', () => {
    const expected = charter({}); let scans = 0;
    const budget = new Proxy({...expected.budget}, {
        ownKeys(value) { scans++; return Reflect.ownKeys(value); },
        get(value, key) { return key === 'checking' && scans >= 3 ? -1 : Reflect.get(value, key); }
    });
    const validated = validateCharter({...expected, budget});
    assert.deepEqual(validated, expected);
    assert.equal(scans, 1);
});

test('campaign verification returns resource counts from the frame it checked', () => {
    const input = structuredClone(base), reads = {checking: 0, search: 0};
    input.resources = new Proxy(input.resources, {
        get(value, key) {
            return Object.hasOwn(reads, key) && ++reads[key] > 1 ? -5000 : Reflect.get(value, key);
        }
    });
    const verdict = verifyCampaign(DEFAULT_CHARTER, input);
    assert.equal(verdict.verified, true);
    assert.equal(verdict.checks, base.resources.checking);
    assert.equal(verdict.replaySearch, base.resources.search);
    assert.deepEqual(reads, {checking: 0, search: 0});
});

test('campaign verification rejects invalid captured costs masked by original property reads', () => {
    const input = structuredClone(base);
    input.resources = new Proxy({...input.resources, checking: -1}, {
        get(value, key) { return key === 'checking' ? base.resources.checking : Reflect.get(value, key); }
    });
    assert.throws(() => verifyCampaign(DEFAULT_CHARTER, input), error =>
        /do not reconstruct/.test(error.message) && error.verificationResources.checking === base.resources.checking);
});

test('verified original parent identity reuses only its captured intact frame', () => {
    let armed = false, reads = 0;
    const input = new Proxy(structuredClone(base), {
        get(value, key) {
            if (armed) { reads++; throw Error('Original parent property was read'); }
            return Reflect.get(value, key);
        }
    });
    assert.equal(verifyCampaign(DEFAULT_CHARTER, input).accepted, true);
    armed = true;
    const result = runCampaign(charter({controls: 4, memory: 16, operations: ['flip-z', 'flip-w']}), {parent: input});
    assert.equal(result.state, 'accepted');
    assert.equal(result.reuse.acceptedPredecessorPreserved, true);
    assert.equal(reads, 0);
});

test('measurement raw evidence and exact contrast are generated rather than supplied final answers', () => {
    const p = stage(base, 'learn').program;
    assert.equal(p.queryRows.length, 8);
    assert.equal(p.errorBound, 0);
    assert.ok(p.calibrationRaw.length >= 3);
    assert.deepEqual(p.queryRows[0].interval, [2, 2]);
    assert.equal(p.weights.numerators.reduce((sum, x, i) => sum + x * p.signs[i], 0), p.weights.denominator);
    assert.equal(p.weights.numerators.reduce((sum, x) => sum + x, 0), 0);
    assert.equal(p.weights.numerators.reduce((sum, x, i) => sum + x * p.times[i], 0), 0);
});

test('invalid calibration and changed undeclared drift reject and pause dependents', () => {
    for (const c of [charter({noise: 1, accuracy: 0}), charter({actualDrift: 'quadratic'}),
        charter({observations: ['contrast']})]) {
        const r = runCampaign(c);
        assert.equal(r.state, 'rejected'); assert.equal(stage(r, 'learn').status, 'rejected');
        assert.ok(r.stages.slice(1).every(s => s.status === 'paused'));
        const verified = verifyCampaign(c, r);
        assert.equal(verified.verified, true); assert.equal(verified.accepted, false);
    }
});

test('expanded drift grammar constructs a newly checked quadratic schedule', () => {
    const c = charter({driftScope: 'quadratic', actualDrift: 'quadratic'}), r = runCampaign(c);
    assert.equal(r.state, 'accepted');
    assert.equal(stage(r, 'learn').program.degree, 2);
    assert.equal(stage(r, 'learn').program.times.length, 4);
    assert.notDeepEqual(stage(r, 'learn').program.times, stage(base, 'learn').program.times);
});

test('nonzero noise retains interval ambiguity through downstream query decisions', () => {
    const c = charter({noise: 1, accuracy: 2}), r = runCampaign(c);
    assert.equal(r.state, 'accepted'); assert.ok(stage(r, 'learn').program.errorBound > 0);
    assert.ok(r.queryResults.thresholdScreening.results.some(value => value.outcome === 'ambiguous'));
    assert.equal(r.queryResults.inverseDesign.definite.length, 0);
    assert.ok(r.queryResults.intervals.every(([lo, hi]) => lo < hi));
});

test('representation retirement preserves every answer and canonical update', () => {
    const p = stage(base, 'think').program;
    assert.equal(p.blocks.length, 6); assert.equal(p.encoder.length, 8);
    assert.equal(stage(base, 'think').evidence.retiredLabels, 16);
    for (let mask = 0; mask < 8; mask++) assert.equal(p.updates['flip-z'][p.encoder[mask]], p.encoder[mask ^ 4]);
    const good = runCampaign(charter({memory: 6}));
    assert.equal(good.state, 'accepted');
    assert.equal(stage(good, 'think').status, 'accepted');
    const refined = runCampaign(charter({memory: 6, operations: ['flip-z', 'flip-x']}));
    assert.equal(stage(refined, 'think').status, 'rejected');
    assert.equal(stage(refined, 'think').program.blocks.length, 8);
});

test('full independent service input domain and continuous obligations are retained', () => {
    const p = stage(base, 'design').program;
    assert.equal(p.serviceTable.length, p.compiled.decoder.length ** 2);
    assert.deepEqual(p.serviceTable.find(([a, b]) => a === 0 && b === 3), [0, 3, ...p.compiled.decoder[0], ...p.compiled.operations.map(op => p.compiled.updaters[op][3])]);
    for (const phase of p.transition) assert.deepEqual(phase.flatMap(worker => worker.services).sort(), [0, 1, 2]);
    assert.equal(p.vacancy, 'right');
    const wrong = runCampaign(charter({topology: 'wrong'}));
    assert.equal(stage(wrong, 'design').status, 'accepted'); assert.equal(stage(wrong, 'strategise').status, 'rejected');
    const staged = runCampaign(charter({topology: 'staged'}));
    assert.equal(staged.state, 'accepted'); assert.ok(staged.resources.installations > base.resources.installations);
});

test('strategy searches robust residual policies and preserves a competent tied competitor', () => {
    const p = stage(base, 'strategise');
    assert.equal(p.program.observation, 'coarse');
    assert.ok(p.program.leaves.some(leaf => leaf.worlds.length > 1));
    const coarse = p.attempts.find(policy => policy.observation === 'coarse');
    const full = p.attempts.find(policy => policy.observation === 'full');
    assert.deepEqual(coarse.expectedCost, full.expectedCost);
    assert.equal(runCampaign(charter({faultHypotheses: ['clear', 'left']})).stages[3].program.observation, 'none');
    assert.equal(runCampaign(charter({faultHypotheses: ['clear', 'right', 'both']})).stages[3].program.observation, 'full');
});

test('new checkpoints invalidate the route and produce a new current boundary witness', () => {
    const c = charter({checkpoints: ['safety', 'sterile']}), r = runCampaign(c, {parent: base});
    assert.equal(r.state, 'accepted');
    assert.deepEqual(invalidationFor(DEFAULT_CHARTER, c).invalidated, ['strategise', 'execute', 'evolve']);
    assert.ok(stage(r, 'strategise').program.leaves.every(leaf => leaf.checkpoints.includes('sterile')));
    assert.equal(stage(r, 'execute').program.currentBoundary, 1);
    assert.deepEqual(stage(r, 'execute').program.witness, {a: 0, b: 1, r: 0, c: 1});
    assert.deepEqual(stage(r, 'execute').program.reusedFactors, ['prepare', 'reference', 'capacity', 'checkpoint']);
});

test('hidden cross-component coupling is rejected before stale factors can masquerade as accepted work', () => {
    const c = charter({hiddenCoupling: true}), r = runCampaign(c, {parent: base});
    assert.equal(r.state, 'rejected');
    assert.equal(stage(r, 'execute').status, 'rejected');
    assert.match(stage(r, 'execute').reason, /scope|factor|model|cost/i);
    assert.equal(stage(r, 'evolve').status, 'paused');
    assert.equal(base.state, 'accepted');
});

test('complete profiles retain compatible components but materialize and check current witnesses', () => {
    const r = runCampaign(DEFAULT_CHARTER, {parent: base});
    assert.equal(r.state, 'accepted');
    assert.deepEqual(stage(r, 'execute').program.reusedFactors, ['prepare', 'reference', 'capacity', 'route', 'checkpoint']);
    assert.equal(stage(r, 'execute').evidence.currentWitnessMaterialized, true);
    assert.ok(stage(r, 'execute').cost.checking > 0);
    assert.ok(stage(r, 'execute').cost.search < stage(base, 'execute').cost.search);
});

test('full-domain structural qualification chooses by intended uses and preserves cheaper/tied programs', () => {
    const one = runCampaign(charter({intendedUses: 1})), two = runCampaign(charter({intendedUses: 2}));
    assert.deepEqual(stage(one, 'evolve').program.operations, ['reference']);
    assert.deepEqual(stage(base, 'evolve').program.operations, ['isolate']);
    const iso = stage(two, 'evolve').attempts.find(candidate => candidate.operations[0] === 'isolate');
    const ref = stage(two, 'evolve').attempts.find(candidate => candidate.operations[0] === 'reference');
    assert.equal(iso.horizonCost, ref.horizonCost);
    assert.ok(stage(base, 'evolve').program.coefficients.every((value, mask) => mask.toString(2).replaceAll('0', '').length <= 1 || value === 0));
});

test('stronger successor expands domain and requalifies the old slice without losing obligations', () => {
    const c = charter({controls: 4, memory: 16, operations: ['flip-z', 'flip-w']});
    const r = runCampaign(c, {parent: base});
    assert.equal(r.state, 'accepted'); assert.equal(r.queryResults.intervals.length, 16);
    assert.equal(r.reuse.priorPurposePreservedOnOldSlice, true);
    assert.equal(r.lineage.generation, 2);
    assert.deepEqual(stage(r, 'execute').program.reusedFactors, ['prepare', 'reference', 'capacity', 'route', 'checkpoint']);
    assert.deepEqual(stage(r, 'evolve').program.responseTable.slice(0, 8), stage(base, 'evolve').program.responseTable);
    assert.ok(r.resources.checking > 0);
});

test('three-generation cumulative cost retains all ancestors and charges each increment once', () => {
    const second = runCampaign(DEFAULT_CHARTER, {parent: base});
    const third = runCampaign(DEFAULT_CHARTER, {parent: second});
    assert.equal(third.lineage.generation, 3);
    for (const key of ['acquisitions', 'search', 'checking', 'storageBytes', 'installations']) {
        assert.equal(third.lineage.cumulative[key], base.resources[key] + second.resources[key] + third.resources[key]);
    }
    assert.equal(third.lineage.cumulative.memoryWords, Math.max(base.resources.memoryWords, second.resources.memoryWords, third.resources.memoryWords));
    assert.throws(() => runCampaign(DEFAULT_CHARTER, {parent: {...base, state: 'rejected'}}));
});

test('resource exhaustion is inconclusive with spent work and attempts retained', () => {
    for (const budget of [{...DEFAULT_CHARTER.budget, acquisitions: 10}, {...DEFAULT_CHARTER.budget, search: 5},
        {...DEFAULT_CHARTER.budget, checking: 10}, {...DEFAULT_CHARTER.budget, installations: 0}]) {
        const c = charter({budget}), r = runCampaign(c);
        assert.equal(r.state, 'inconclusive'); assert.ok(r.failure);
        assert.ok(r.resources.search > 0);
        assert.equal(verifyCampaign(c, r).verified, true);
        assert.ok(r.resources.acquisitions <= budget.acquisitions);
        assert.ok(r.resources.search <= budget.search);
        assert.ok(r.resources.checking <= budget.checking);
    }
    const early = runCampaign(charter({budget: {...DEFAULT_CHARTER.budget, storageBytes: REPORT_RESERVE_BYTES - 1}}));
    assert.equal(early.state, 'inconclusive'); assert.equal(early.resources.search, 0);
    assert.equal(early.resourceReservation.status, 'refused-before-work');
});

test('report bytes and per-stage storage charges match the exact canonical output', () => {
    assert.equal(base.resources.storageBytes, new TextEncoder().encode(canonical(base)).length);
    for (const key of Object.keys(base.resources)) {
        assert.equal(base.stages.reduce((total, record) => total + record.cost[key], 0), base.resources[key]);
    }
});

test('forged acceptance, stale programs, costs, intervals and lineage are rejected on import', () => {
    for (const mutate of [r => r.stages[0].program.queryRows[0].interval[0]++, r => r.resources.search--,
        r => r.stages[1].program.updates['flip-z'][0] = 0, r => r.lineage.cumulative.search++,
        r => r.stages[5].program.coefficients[7] = 1, r => r.queryResults.inverseDesign.definite = []]) {
        const forged = structuredClone(base); mutate(forged);
        assert.throws(() => verifyCampaign(DEFAULT_CHARTER, forged));
    }
});

test('direct charter objects cannot execute accessors or smuggle extra array or symbol data', () => {
    let invoked = false;
    const getter = structuredClone(DEFAULT_CHARTER);
    Object.defineProperty(getter, 'controls', {enumerable: true, get() { invoked = true; return 3; }});
    assert.throws(() => validateCharter(getter)); assert.equal(invoked, false);
    const symbol = charter({}); symbol[Symbol('extra')] = true;
    assert.throws(() => validateCharter(symbol));
    const array = charter({}); array.observations.extra = true;
    assert.throws(() => validateCharter(array));
});

test('an imported parent needs fresh verified custody and forged parent costs cannot enter lineage', () => {
    const imported = structuredClone(base);
    assert.throws(() => runCampaign(DEFAULT_CHARTER, {parent: imported}), /Verify the intact parent/);
    verifyCampaign(DEFAULT_CHARTER, imported);
    assert.equal(runCampaign(DEFAULT_CHARTER, {parent: imported}).state, 'accepted');
    imported.lineage.cumulative.search--;
    assert.throws(() => runCampaign(DEFAULT_CHARTER, {parent: imported}), /Verify the intact parent/);
});

test('external inspection limits refuse conservatively before replay and failed replay retains its work', () => {
    const result = verifyCampaign(DEFAULT_CHARTER, base, {limits: {...DEFAULT_CHARTER.budget, search: 1}});
    assert.equal(result.verified, false); assert.equal(result.state, 'CHECK_INCOMPLETE');
    assert.equal(result.verificationResources.search, 0);
    const forged = structuredClone(base); forged.resources.search++;
    assert.throws(() => verifyCampaign(DEFAULT_CHARTER, forged), error => error.verificationResources.search === base.resources.search);
});

test('a claimed stronger successor cannot silently discard an old required operation', () => {
    const c = charter({controls: 4, memory: 16, operations: ['flip-w']});
    const result = runCampaign(c, {parent: base});
    assert.equal(result.state, 'rejected');
    assert.match(result.failure, /predecessor purpose/);
    assert.equal(result.queryResults, null);
    assert.equal(base.state, 'accepted');
});


test('complete-profile equality stops upstream optimization while changed executable route witnesses are rebuilt', () => {
    const firstCharter = charter({faultHypotheses: ['clear', 'left']});
    const first = runCampaign(firstCharter);
    const secondCharter = charter({faultHypotheses: ['clear', 'right']});
    const second = runCampaign(secondCharter, {parent: first});
    assert.equal(first.state, 'accepted'); assert.equal(second.state, 'accepted');
    const old = stage(first, 'execute'), current = stage(second, 'execute');
    assert.deepEqual(current.program.components.map(c => c.profiles.map(p => p.value)), old.program.components.map(c => c.profiles.map(p => p.value)));
    const routing = current.program.reuseContracts.find(c => c.component === 'routing');
    assert.equal(routing.status, 'rebuilt'); assert.equal(routing.completeProfileEqual, true);
    assert.equal(routing.propagation, 'stopped');
    assert.equal(current.evidence.completeProfilePropagationStopped, true);
    assert.equal(old.program.routeWitness.leaves[0].route, 'R');
    assert.equal(current.program.routeWitness.leaves[0].route, 'L');
    assert.equal(current.evidence.currentWitnessMaterialized, true);
    assert.ok(current.cost.checking > 0);
    const forged = structuredClone(second); stage(forged, 'execute').program.routeWitness = old.program.routeWitness;
    assert.throws(() => verifyCampaign(secondCharter, forged, {parent: first}));
});

test('a changed factor denominator rebuilds affected contracts instead of copying stale scaled costs', () => {
    const c = charter({faultHypotheses: ['clear', 'right', 'both']});
    const result = runCampaign(c, {parent: base});
    assert.equal(result.state, 'accepted');
    assert.equal(stage(result, 'execute').program.bindings.denominator, 3);
    assert.ok(!stage(result, 'execute').program.reusedFactors.includes('prepare'));
});

test('joint calibration and use search changes the actual measurement program with the use horizon', () => {
    const short = runCampaign(charter({noise: 1, accuracy: 4, intendedUses: 1}));
    const long = runCampaign(charter({noise: 1, accuracy: 4, intendedUses: 12}));
    assert.equal(short.state, 'accepted'); assert.equal(long.state, 'accepted');
    assert.deepEqual(stage(short, 'learn').program.signs, [1, -1, 1]);
    assert.equal(stage(short, 'learn').program.referenceAmplitude, 4);
    assert.deepEqual(stage(long, 'learn').program.signs, [1, 1, -1]);
    assert.equal(stage(long, 'learn').program.referenceAmplitude, 16);
    assert.ok(short.queryResults.thresholdScreening.results.some(result => result.outcome === 'ambiguous'));
    assert.ok(long.queryResults.thresholdScreening.results.some(result => result.outcome === 'ambiguous'));
});
