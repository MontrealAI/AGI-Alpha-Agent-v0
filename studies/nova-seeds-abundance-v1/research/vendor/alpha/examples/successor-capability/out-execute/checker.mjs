// SPDX-License-Identifier: Apache-2.0
/** Independent evaluator: explicit tuple maps and a mixed-radix walk, no compiler imports. */
import {CHECKER_VERSION, CONTRACT_SCHEMA, COMPILER_VERSION, LIMITS, validateModel,
    requireValue, fields, same, checkSeal} from './model.mjs';

function walk(variables, visit) {
    const digits = variables.map(() => 0);
    let more = true;
    while (more) {
        const assignment = Object.fromEntries(variables.map((v, i) => [v.id, v.domain[digits[i]]]));
        visit(assignment);
        let i = digits.length - 1;
        while (i >= 0 && ++digits[i] === variables[i].domain.length) { digits[i] = 0; i--; }
        more = i >= 0;
    }
}
function tables(model) {
    const variables = new Map(model.variables.map(variable => [variable.id, variable]));
    return model.factors.map(factor => {
        const rows = new Map(); let index = 0;
        walk(factor.scope.map(id => variables.get(id)), assignment => {
            rows.set(JSON.stringify(factor.scope.map(id => assignment[id])), factor.costs[index++]);
        });
        return {scope: factor.scope, rows};
    });
}
function costAt(prepared, assignment, work) {
    let total = 0, forbidden = false;
    for (const factor of prepared) {
        const key = JSON.stringify(factor.scope.map(id => assignment[id]));
        requireValue(factor.rows.has(key), 'CHECKER_UNDEFINED_TUPLE');
        const value = factor.rows.get(key); work.factorLookups++;
        if (value === null) forbidden = true; else total += value;
    }
    requireValue(Number.isSafeInteger(total), 'CHECKER_COST_OVERFLOW');
    return forbidden ? null : total;
}

/** Checks complete scope ownership separately from the compiler's graph traversal. */
export function verifyDecomposition(input, decomposition) {
    const model = validateModel(input);
    fields(decomposition, ['boundary', 'boundaryFactors', 'modules']);
    const variables = new Set(model.variables.map(v => v.id));
    requireValue(Array.isArray(decomposition.boundary) && decomposition.boundary.length <= LIMITS.boundary
        && new Set(decomposition.boundary).size === decomposition.boundary.length
        && decomposition.boundary.every(id => variables.has(id)), 'CHECKER_BOUNDARY');
    requireValue(Array.isArray(decomposition.modules), 'CHECKER_MODULES');
    const ownership = new Map(decomposition.boundary.map(id => [id, -1]));
    const moduleIds = new Set();
    for (const [i, module] of decomposition.modules.entries()) {
        fields(module, ['id', 'private', 'interface', 'factorIds']);
        requireValue(typeof module.id === 'string' && !moduleIds.has(module.id) && Array.isArray(module.private)
            && module.private.length > 0 && Array.isArray(module.interface)
            && Array.isArray(module.factorIds), 'CHECKER_MODULE');
        moduleIds.add(module.id);
        for (const id of module.private) {
            requireValue(variables.has(id) && !ownership.has(id), 'CHECKER_PRIVATE_PARTITION'); ownership.set(id, i);
        }
    }
    requireValue(ownership.size === variables.size, 'CHECKER_COMPLETE_VARIABLES');
    const expected = decomposition.modules.map(() => []), interfaces = expected.map(() => new Set()), boundaryFactors = [];
    for (const factor of model.factors) {
        const privateOwners = new Set(factor.scope.map(id => ownership.get(id)).filter(owner => owner !== -1));
        requireValue(privateOwners.size <= 1, 'CHECKER_HIDDEN_CROSS_COUPLING');
        if (privateOwners.size === 0) boundaryFactors.push(factor.id);
        else {
            const owner = [...privateOwners][0]; expected[owner].push(factor.id);
            factor.scope.filter(id => ownership.get(id) === -1).forEach(id => interfaces[owner].add(id));
        }
    }
    requireValue(same(boundaryFactors, decomposition.boundaryFactors), 'CHECKER_FACTOR_OWNERSHIP');
    for (const [i, module] of decomposition.modules.entries()) {
        requireValue(same(module.factorIds, expected[i])
            && same(module.interface, decomposition.boundary.filter(id => interfaces[i].has(id))), 'CHECKER_INTERFACE');
    }
    return model;
}

export async function verifyContract(input, module, contract) {
    const model = validateModel(input);
    fields(contract, ['schema', 'compilerVersion', 'checkerVersion', 'module', 'model', 'rows', 'digest']);
    requireValue(contract.schema === CONTRACT_SCHEMA && contract.compilerVersion === COMPILER_VERSION
        && contract.checkerVersion === CHECKER_VERSION && same(contract.module, module), 'CHECKER_CONTRACT_VERSION');
    const selected = new Set([...module.private, ...module.interface]);
    const expected = {schema: model.schema, semantics: model.semantics,
        variables: model.variables.filter(v => selected.has(v.id)),
        factors: model.factors.filter(f => module.factorIds.includes(f.id))};
    requireValue(same(contract.model, expected), 'CHECKER_CURRENT_INPUT_BINDING');
    const vars = new Map(model.variables.map(variable => [variable.id, variable]));
    const interfaceVariables = module.interface.map(id => vars.get(id));
    const localVariables = [...interfaceVariables, ...module.private.map(id => vars.get(id))];
    const count = localVariables.reduce((n, v) => n * v.domain.length, 1);
    requireValue(count <= LIMITS.localAssignments, 'CHECKER_LOCAL_BOUND');
    const prepared = tables(expected), minima = new Map(), work = {assignments: 0, factorLookups: 0};
    walk(interfaceVariables, assignment => minima.set(JSON.stringify(module.interface.map(id => assignment[id])),
        {boundary: module.interface.map(id => assignment[id]), cost: null, witness: null}));
    walk(localVariables, assignment => {
        work.assignments++;
        const cost = costAt(prepared, assignment, work);
        const key = JSON.stringify(module.interface.map(id => assignment[id])), entry = minima.get(key);
        if (cost !== null && (entry.cost === null || cost < entry.cost)) {
            entry.cost = cost; entry.witness = module.private.map(id => assignment[id]);
        }
    });
    requireValue(Array.isArray(contract.rows) && same(contract.rows, [...minima.values()]), 'CHECKER_ROWS_OR_WITNESS');
    await checkSeal(contract);
    return work;
}

/** Fully independent exhaustive baseline; explicit refusal is not infeasibility. */
export function exhaustive(input) {
    const model = validateModel(input);
    const count = model.variables.reduce((n, v) => n * v.domain.length, 1);
    if (!Number.isSafeInteger(count) || count > LIMITS.fullAssignments) {
        return {status: 'INCONCLUSIVE', reason: 'full-enumeration-bound', artifact: null, work: {assignments: 0, factorLookups: 0}};
    }
    const prepared = tables(model), work = {assignments: 0, factorLookups: 0};
    let best = null, artifact = null;
    walk(model.variables, assignment => {
        work.assignments++;
        const value = costAt(prepared, assignment, work);
        if (value !== null && (best === null || value < best)) { best = value; artifact = assignment; }
    });
    return {status: best === null ? 'INFEASIBLE' : 'OPTIMAL', cost: best, artifact, work};
}

export function verifyArtifact(input, artifact, expectedCost) {
    const model = validateModel(input), work = {assignments: 0, factorLookups: 0};
    requireValue(artifact !== null && typeof artifact === 'object'
        && same(Object.keys(artifact).sort(), model.variables.map(v => v.id).sort()), 'CHECKER_ARTIFACT_COVERAGE');
    for (const variable of model.variables) requireValue(variable.domain.includes(artifact[variable.id]), 'CHECKER_ARTIFACT_DOMAIN');
    const cost = costAt(tables(model), artifact, work);
    requireValue(cost !== null && cost === expectedCost, 'CHECKER_ARTIFACT_COST');
    return work;
}

/** Recompute the exact boundary optimum from qualified tables, independent of composition. */
export function verifySelection(input, decomposition, contracts, selection, artifact) {
    fields(selection, ['status', 'boundary', 'cost']);
    const model = verifyDecomposition(input, decomposition), variables = new Map(model.variables.map(v => [v.id, v]));
    const boundaryTables = tables({...model, factors: model.factors.filter(f => decomposition.boundaryFactors.includes(f.id))});
    let best = null, selected = null;
    const profiles = contracts.map(contract => new Map(contract.rows.map(row => [JSON.stringify(row.boundary), row])));
    const work = {assignments: 0, factorLookups: 0, profileLookups: 0};
    walk(decomposition.boundary.map(id => variables.get(id)), assignment => {
        work.assignments++;
        let total = costAt(boundaryTables, assignment, work), valid = total !== null;
        for (const [i, module] of decomposition.modules.entries()) {
            work.profileLookups++;
            const row = profiles[i].get(JSON.stringify(module.interface.map(id => assignment[id])));
            requireValue(row !== undefined, 'CHECKER_COMPLETE_PROFILE');
            if (row.cost === null) valid = false; else total += row.cost;
        }
        if (valid && (best === null || total < best)) { best = total; selected = assignment; }
    });
    const expectedStatus = best === null ? 'INFEASIBLE' : 'OPTIMAL';
    requireValue(selection.status === expectedStatus && selection.cost === best, 'CHECKER_OPTIMUM');
    if (best === null) requireValue(selection.boundary === null && artifact === null, 'CHECKER_INFEASIBLE_ARTIFACT');
    else {
        // Any minimizing boundary is valid; the constructor uses deterministic domain order.
        requireValue(same(selection.boundary, selected), 'CHECKER_BOUNDARY_SELECTION');
        work.factorLookups += verifyArtifact(model, artifact, best).factorLookups;
    }
    return work;
}
