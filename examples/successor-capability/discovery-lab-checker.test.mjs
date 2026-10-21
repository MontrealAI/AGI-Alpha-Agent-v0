// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULT_CHARTER, runCampaign} from './discovery-lab.mjs';
import {checkQueries, checkStage} from './discovery-lab-checker.mjs';

const copy = value => JSON.parse(JSON.stringify(value));
const fixture = edits => {
    const charter = {...copy(DEFAULT_CHARTER), ...edits};
    return {charter, campaign: runCampaign(charter)};
};
const checked = (fixture, index, edit) => {
    const program = copy(fixture.campaign.stages[index].program);
    edit(program);
    return checkStage(fixture.campaign.stages[index].kind, fixture.charter, program,
        fixture.campaign.stages.slice(0, index));
};
const rejects = result => {
    assert.equal(result.accepted, false, result.reason);
    assert.ok(result.checks > 0, 'Failed checking work must remain charged.');
};

test('a separately written checker accepts every complete default stage', () => {
    const {charter, campaign} = fixture({});
    assert.equal(campaign.state, 'accepted');
    campaign.stages.forEach((stage, index) => {
        const result = checkStage(stage.kind, charter, stage.program, campaign.stages.slice(0, index));
        assert.equal(result.accepted, true, result.reason);
        assert.ok(result.checks > 0);
    });
});

test('canonical imports may reorder object keys while every array and semantic obligation stays unchanged', () => {
    const reorder = value => Array.isArray(value) ? value.map(reorder)
        : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).reverse()
            .map(([key, entry]) => [key, reorder(entry)])) : value;
    const data = fixture({});
    for (let index = 0; index < data.campaign.stages.length; index++) {
        const stage = data.campaign.stages[index];
        const result = checkStage(stage.kind, reorder(data.charter), reorder(stage.program),
            reorder(data.campaign.stages.slice(0, index)));
        assert.equal(result.accepted, true, result.reason);
    }
    assert.equal(checkQueries(reorder(data.charter), reorder(data.campaign.stages[5].program),
        reorder(data.campaign.stages[0].program), reorder(data.campaign.queryResults)).accepted, true);
});

test('measurement checking rejects non-cancelling weights, forged raw evidence and narrowed intervals', () => {
    const data = fixture({});
    rejects(checked(data, 0, program => { program.weights.numerators[0] += 1; }));
    rejects(checked(data, 0, program => { program.calibrationRaw[0] += 1; }));
    rejects(checked(data, 0, program => { program.queryRows[7].raw[0] += 1; }));
    rejects(checked(data, 0, program => { program.queryRows[7].interval = [0, 0]; }));
    rejects(checked(data, 0, program => { program.gainInterval.lower += 1; }));
});

test('a noisy interval remains ambiguous and its conservative error cannot be relabeled zero', () => {
    const data = fixture({noise: 1, accuracy: 8});
    assert.equal(data.campaign.stages[0].status, 'accepted');
    assert.ok(data.campaign.stages[0].program.queryRows.some(row => row.interval[0] !== row.interval[1]));
    rejects(checked(data, 0, program => { program.errorBound = 0; }));
    rejects(checked(data, 0, program => {
        program.queryRows[0].interval[1] = program.queryRows[0].interval[0];
    }));
});

test('an answer-preserving static representation is rejected when it cannot execute its next update', () => {
    const data = fixture({operations: ['flip-x']});
    assert.equal(data.campaign.stages[1].status, 'accepted');
    const intervals = data.campaign.stages[0].program.queryRows.map(row => row.interval);
    const labels = [], blocks = [], encoder = [];
    intervals.forEach((interval, mask) => {
        let label = labels.findIndex(value => JSON.stringify(value) === JSON.stringify(interval));
        if (label < 0) { label = labels.length; labels.push(interval); blocks.push([]); }
        encoder.push(label); blocks[label].push(mask);
    });
    const program = {encoder, blocks, decoder: labels,
        updates: {'flip-x': blocks.map(block => encoder[block[0] ^ 1])}};
    const result = checkStage('think', data.charter, program, data.campaign.stages.slice(0, 1));
    rejects(result);
    assert.match(result.reason, /cannot execute this update/);
});

test('joint realization checks the full independent-input product and all continuous service phases', () => {
    const data = fixture({});
    rejects(checked(data, 2, program => { program.serviceTable[7][3] ^= 1; }));
    rejects(checked(data, 2, program => { program.serviceTable[7][4] ^= 1; }));
    rejects(checked(data, 2, program => { program.compiled.updaters[program.compiled.operations[0]][0] ^= 1; }));
    rejects(checked(data, 2, program => { program.compiled.operations = []; }));
    rejects(checked(data, 2, program => {
        program.compiled.decoder[0][0] += 1;
        for (const row of program.serviceTable) if (row[0] === 0) row[2] += 1;
    }));
    rejects(checked(data, 2, program => { program.transition[1][0].services.pop(); }));
    rejects(checked(data, 2, program => { program.footprint -= 1; }));
    rejects(checked(data, 2, program => { program.vacancy = 'left'; }));
});

test('staging is accepted only through its actual reachable service-preserving route', () => {
    const data = fixture({topology: 'staged'});
    assert.equal(data.campaign.state, 'accepted');
    rejects(checked(data, 2, program => { program.transition.splice(1, 1); }));
    rejects(checked(data, 2, program => { program.staging = false; }));
});

test('conditional policies retain all remaining worlds, checkpoints and branch costs', () => {
    const data = fixture({checkpoints: ['safety', 'sterile']});
    assert.equal(data.campaign.state, 'accepted');
    rejects(checked(data, 3, program => { program.leaves.pop(); }));
    rejects(checked(data, 3, program => { program.leaves[0].worlds.pop(); }));
    rejects(checked(data, 3, program => { program.leaves[0].route = 'L'; }));
    rejects(checked(data, 3, program => { program.leaves[0].checkpoints = ['safety']; }));
    rejects(checked(data, 3, program => { program.leaves[0].visits = program.leaves[0].visits.filter(node => node !== 'sterile'); }));
    rejects(checked(data, 3, program => { program.leaves[0].constructionActions = []; }));
    rejects(checked(data, 3, program => { program.expectedCost.numerator = 0; }));
});

test('completion contracts require every boundary row and a freshly materialized current witness', () => {
    const data = fixture({checkpoints: ['safety', 'sterile']});
    rejects(checked(data, 4, program => { program.profiles.pop(); }));
    rejects(checked(data, 4, program => { program.profiles[0].value += 1; }));
    rejects(checked(data, 4, program => { program.witness = {a: 0, b: 0, c: 0}; }));
    rejects(checked(data, 4, program => { program.bindings.checkpoint = 'safety'; }));
    rejects(checked(data, 4, program => { program.factors[1].table.pop(); }));
    rejects(checked(data, 4, program => { program.bindings.intendedUses -= 1; }));
    rejects(checked(data, 4, program => { program.bindings.workerSlots = 0; }));
    rejects(checked(data, 4, program => {
        const services = program.bindings.compiledServices;
        services.updaters[services.operations[0]][0] ^= 1;
    }));
    rejects(checked(data, 4, program => { program.bindings.residentWords -= 1; }));
    rejects(checked(data, 4, program => { program.installations.actions = ['isolate']; }));
    rejects(checked(data, 4, program => { program.components[0].profiles.pop(); }));
    rejects(checked(data, 4, program => { program.components[1].profiles[0].value += 1; }));
    rejects(checked(data, 4, program => { program.components[1].factorIds.push('prepare'); }));
    rejects(checked(data, 4, program => { program.reuseContracts[0].propagation = 'scalar-cache-hit'; }));
});

test('every modular boundary row is checked even when that checkpoint is not currently requested', () => {
    const data = fixture({});
    assert.equal(data.campaign.stages[4].program.currentBoundary, 0);
    rejects(checked(data, 4, program => { program.components[0].profiles[1].value -= 1; }));
    rejects(checked(data, 4, program => { program.components[1].profiles[1].witness.r = 1; }));
    rejects(checked(data, 4, program => { program.profiles[1].value -= 1; }));
    rejects(checked(data, 4, program => { program.factors.find(factor => factor.id === 'route').scope = ['a', 'r', 'c']; }));
});

test('equal complete module profiles stop propagation while the changed current route is independently rematerialized', () => {
    const first = {...copy(DEFAULT_CHARTER), faultHypotheses: ['clear', 'left']};
    const parent = runCampaign(first);
    const charter = {...first, faultHypotheses: ['clear', 'right']};
    const campaign = runCampaign(charter, {parent}), data = {charter, campaign};
    assert.equal(parent.state, 'accepted');
    assert.equal(campaign.state, 'accepted');
    const before = parent.stages[4].program, after = campaign.stages[4].program;
    assert.deepEqual(after.components.map(component => component.profiles.map(profile => profile.value)),
        before.components.map(component => component.profiles.map(profile => profile.value)));
    assert.ok(after.reuseContracts.every(record => record.completeProfileEqual && record.propagation === 'stopped'));
    assert.equal(after.reuseContracts.find(record => record.component === 'routing').status, 'rebuilt');
    assert.notDeepEqual(after.routeWitness, before.routeWitness);
    assert.equal(checkStage('execute', charter, after, campaign.stages.slice(0, 4)).accepted, true);
    rejects(checked(data, 4, program => { program.routeWitness = copy(before.routeWitness); }));
});

test('an omitted cross-private interaction invalidates the supplied decomposition', () => {
    const data = fixture({hiddenCoupling: true});
    assert.equal(data.campaign.stages[3].status, 'accepted');
    const result = checkStage('execute', data.charter, data.campaign.stages[4].program,
        data.campaign.stages.slice(0, 4));
    rejects(result);
    assert.match(result.reason, /true current cost system/);
});

test('structural qualification checks semantic construction and every high-order coefficient', () => {
    const data = fixture({});
    rejects(checked(data, 5, program => { program.responseTable[7] += 5; }));
    rejects(checked(data, 5, program => { program.coefficients[7] = 5; }));
    const result = checked(data, 5, program => {
        program.operations = [];
        program.responseTable = [2, 4, 4, 9, 6, 8, 8, 13];
        program.coefficients = [2, 2, 2, 3, 4, 0, 0, 0];
    });
    rejects(result);
    assert.match(result.reason, /installed current execution capability/);
    rejects(checked(data, 5, program => {
        program.operations = program.operations[0] === 'isolate' ? ['reference'] : ['isolate'];
    }));
    rejects(checked(data, 5, program => { program.freezeOrder = 'after-query-evaluation'; }));
});

test('the usage horizon and stricter checkpoint change the actually installed experimentation capability', () => {
    const short = fixture({intendedUses: 1}), long = fixture({intendedUses: 12});
    const sterile = fixture({intendedUses: 12, checkpoints: ['safety', 'sterile']});
    for (const data of [short, long, sterile]) assert.equal(data.campaign.state, 'accepted');
    assert.deepEqual(short.campaign.stages[4].program.installations.actions, ['reference']);
    assert.deepEqual(long.campaign.stages[4].program.installations.actions, ['isolate']);
    assert.deepEqual(sterile.campaign.stages[4].program.installations.actions, ['reference']);
    for (const data of [short, long, sterile]) {
        assert.deepEqual(data.campaign.stages[5].program.operations, data.campaign.stages[4].program.installations.actions);
    }
});

test('a no-operation representation compiles an explicit identity updater with independent decoder input', () => {
    const data = fixture({operations: []});
    assert.equal(data.campaign.state, 'accepted');
    const program = data.campaign.stages[2].program;
    assert.deepEqual(program.compiled.operations, ['identity']);
    assert.deepEqual(program.compiled.updaters.identity, program.compiled.decoder.map((_, index) => index));
    rejects(checked(data, 2, invalid => { invalid.compiled.updaters.identity[0] = 1; }));
});

test('the joint realization preserves every declared operation including later flip-w and mix tables', () => {
    const data = fixture({controls: 4, memory: 16, operations: ['flip-x', 'flip-y', 'flip-z', 'flip-w', 'mix']});
    assert.equal(data.campaign.state, 'accepted');
    assert.deepEqual(data.campaign.stages[2].program.compiled.operations, data.charter.operations);
    assert.equal(data.campaign.stages[2].program.serviceTable[0].length, 4 + data.charter.operations.length);
    for (const operation of ['flip-w', 'mix']) {
        rejects(checked(data, 2, program => {
            program.compiled.updaters[operation][0] ^= 1;
            const column = 4 + program.compiled.operations.indexOf(operation);
            for (const row of program.serviceTable) if (row[1] === 0) row[column] ^= 1;
        }));
        rejects(checked(data, 2, program => {
            const column = 4 + program.compiled.operations.indexOf(operation);
            program.serviceTable[7][column] ^= 1;
        }));
    }
    rejects(checked(data, 2, program => {
        program.compiled.operations.pop(); delete program.compiled.updaters.mix;
        for (const row of program.serviceTable) row.pop();
    }));
});

test('acceptance cannot be inherited from an unchecked, stale or rejected dependency', () => {
    const data = fixture({});
    const inputs = copy(data.campaign.stages.slice(0, 5));
    inputs[0].program.calibrationRaw[0] += 1;
    rejects(checkStage('evolve', data.charter, data.campaign.stages[5].program, inputs));
    inputs[0] = copy(data.campaign.stages[0]); inputs[2].status = 'rejected';
    rejects(checkStage('evolve', data.charter, data.campaign.stages[5].program, inputs));
    rejects(checkStage('evolve', data.charter, data.campaign.stages[5].program, inputs.slice(1)));
});

test('only bounded passive data reaches semantic interpretation', () => {
    const data = fixture({});
    let touched = false;
    const accessor = Object.defineProperty({}, 'degree', {enumerable: true, get() { touched = true; return 1; }});
    rejects(checkStage('learn', data.charter, accessor));
    assert.equal(touched, false);
    rejects(checkStage('learn', data.charter, {value: Number.NaN}));
    rejects(checkStage('learn', data.charter, {value: -0}));
    rejects(checkStage('learn', data.charter, Object.create({degree: 1})));
    rejects(checkStage('unknown', data.charter, {}));
});

test('checking stops at its declared work cap and reports truncation instead of rejection', () => {
    const data = fixture({});
    for (const maxChecks of [0, 10, 217]) {
        const result = checkStage('learn', data.charter, data.campaign.stages[0].program, [], {maxChecks});
        assert.equal(result.accepted, false);
        assert.equal(result.inconclusive, true);
        assert.equal(result.checks, maxChecks);
        assert.equal(result.reason, 'checking budget exhausted');
    }
    const complete = checkStage('learn', data.charter, data.campaign.stages[0].program, [], {maxChecks: 218});
    assert.equal(complete.accepted, true);
    assert.equal(complete.checks, 218);
});

test('downstream query checking reconstructs all answers and preserves noisy ambiguity and exact ties', () => {
    for (const edits of [{}, {noise: 1, accuracy: 8}, {controls: 4, memory: 16}]) {
        const data = fixture(edits);
        assert.equal(data.campaign.state, 'accepted');
        const result = checkQueries(data.charter, data.campaign.stages[5].program,
            data.campaign.stages[0].program, data.campaign.queryResults);
        assert.equal(result.accepted, true, result.reason);
        assert.ok(result.checks > 3 * 2 ** data.charter.controls, 'Actual program, uncertainty and query checking must be charged.');
    }
});

test('forged screening, inverse design, constrained selection and query certainty are rejected', () => {
    const data = fixture({noise: 1, accuracy: 8});
    const check = edit => {
        const queries = copy(data.campaign.queryResults);
        edit(queries);
        return checkQueries(data.charter, data.campaign.stages[5].program, data.campaign.stages[0].program, queries);
    };
    rejects(check(queries => { queries.thresholdScreening.results[0].outcome = 'accepted'; }));
    rejects(check(queries => { queries.inverseDesign.definite.push(0); }));
    rejects(check(queries => { queries.inverseDesign.possible.pop(); }));
    rejects(check(queries => { queries.constrainedSelection.candidates.pop(); }));
    rejects(check(queries => { queries.constrainedSelection.suppliedModelOptima = [7]; }));
    rejects(check(queries => { queries.constrainedSelection.uncertainty = 'exact-within-supplied-model'; }));
    rejects(check(queries => { queries.intervals[0][1] = queries.intervals[0][0]; }));
    rejects(check(queries => { queries.queriesAfterFreeze = false; }));
    const exact = fixture({});
    const queries = copy(exact.campaign.queryResults);
    assert.ok(queries.constrainedSelection.candidates.length > 1);
    queries.constrainedSelection.candidates.pop();
    rejects(checkQueries(exact.charter, exact.campaign.stages[5].program, exact.campaign.stages[0].program, queries));
});

test('query checking rechecks the full platform and sensor semantics within its finite work cap', () => {
    const data = fixture({});
    const platform = copy(data.campaign.stages[5].program), sensor = copy(data.campaign.stages[0].program);
    const complete = checkQueries(data.charter, platform, sensor, data.campaign.queryResults);
    assert.equal(complete.accepted, true);
    for (const maxChecks of [0, 10, complete.checks - 1]) {
        const result = checkQueries(data.charter, platform, sensor, data.campaign.queryResults, {maxChecks});
        assert.equal(result.inconclusive, true);
        assert.equal(result.accepted, false);
        assert.equal(result.checks, maxChecks);
    }
    assert.equal(checkQueries(data.charter, platform, sensor, data.campaign.queryResults,
        {maxChecks: complete.checks}).accepted, true);
    platform.responseTable[7] += 5;
    rejects(checkQueries(data.charter, platform, sensor, data.campaign.queryResults));
    platform.responseTable[7] -= 5; sensor.calibrationRaw[0] += 1;
    rejects(checkQueries(data.charter, platform, sensor, data.campaign.queryResults));
});
