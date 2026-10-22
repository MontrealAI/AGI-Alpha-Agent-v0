// SPDX-License-Identifier: Apache-2.0
/** Bounded data, never generated code. null means an explicitly forbidden tuple. */
import {canonical} from '../constructor.mjs';
import {sha256} from '../capability-package.mjs';

export const MODEL_SCHEMA = 'out-execute-finite-model/v1';
export const CONTRACT_SCHEMA = 'out-execute-boundary-contract/v1';
export const COMPLETION_SCHEMA = 'out-execute-completion/v1';
export const CHECKPOINT_SCHEMA = 'out-execute-checkpoint/v1';
export const COMPILER_VERSION = 'out-execute-finite-compiler/v1';
export const CHECKER_VERSION = 'out-execute-independent-enumeration/v1';
export const SEMANTICS = 'finite-nonnegative-integer-min-sum/v1';
export const LIMITS = Object.freeze({variables: 128, domain: 5, factors: 1024, factorEntries: 4096,
    entries: 100000, bytes: 2000000, boundary: 3, candidates: 512, localAssignments: 100000,
    profileRows: 10000, selectionScopeVisits: 1000000, totalWork: 10000000, fullAssignments: 1000000});
export const clone = value => JSON.parse(canonical(value));
export const same = (a, b) => canonical(a) === canonical(b);
export function requireValue(condition, code) { if (!condition) throw Error(`OUT_EXECUTE_${code}`); }
export function fields(value, names) {
    requireValue(value && typeof value === 'object' && !Array.isArray(value)
        && same(Object.keys(value).sort(), [...names].sort()), 'FIELDS');
}
export function integer(value, min, max) {
    requireValue(Number.isSafeInteger(value) && !Object.is(value, -0) && value >= min && value <= max, 'INTEGER');
}
export function identity(value) {
    requireValue(typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,47}$/.test(value), 'IDENTITY');
}
export function bounded(input) {
    const raw = typeof input === 'string' ? input : canonical(input);
    requireValue(new TextEncoder().encode(raw).length <= LIMITS.bytes, 'BYTES');
    const parsed = typeof input === 'string' ? JSON.parse(input) : input;
    return clone(parsed);
}
export function validateModel(input) {
    const model = bounded(input);
    fields(model, ['schema', 'semantics', 'variables', 'factors']);
    requireValue(model.schema === MODEL_SCHEMA && model.semantics === SEMANTICS, 'MODEL_SEMANTICS');
    requireValue(Array.isArray(model.variables) && model.variables.length > 0
        && model.variables.length <= LIMITS.variables && Array.isArray(model.factors)
        && model.factors.length <= LIMITS.factors, 'MODEL_SIZE');
    const domains = new Map();
    for (const variable of model.variables) {
        fields(variable, ['id', 'domain']); identity(variable.id);
        requireValue(!domains.has(variable.id) && Array.isArray(variable.domain)
            && variable.domain.length > 0 && variable.domain.length <= LIMITS.domain, 'VARIABLE');
        variable.domain.forEach(value => integer(value, 0, 65535));
        requireValue(new Set(variable.domain).size === variable.domain.length, 'DOMAIN');
        domains.set(variable.id, variable.domain);
    }
    const names = new Set(); let entries = 0;
    for (const factor of model.factors) {
        fields(factor, ['id', 'scope', 'costs']); identity(factor.id);
        requireValue(!names.has(factor.id) && Array.isArray(factor.scope)
            && factor.scope.length <= 8 && new Set(factor.scope).size === factor.scope.length
            && factor.scope.every(id => domains.has(id)), 'FACTOR_SCOPE');
        names.add(factor.id);
        const size = factor.scope.reduce((n, id) => n * domains.get(id).length, 1);
        requireValue(size <= LIMITS.factorEntries && Array.isArray(factor.costs)
            && factor.costs.length === size, 'COMPLETE_FACTOR_TABLE');
        factor.costs.forEach(cost => { if (cost !== null) integer(cost, 0, 1000000000); });
        entries += size;
    }
    requireValue(entries <= LIMITS.entries, 'FACTOR_ENTRY_LIMIT');
    // Canonical order does not alter scope order or the corresponding row-major tables.
    model.variables.sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    model.factors.sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    return model;
}
export function domainMap(model) { return Object.fromEntries(model.variables.map(v => [v.id, v.domain])); }
export function cardinality(ids, domains) {
    let result = 1;
    for (const id of ids) { result *= domains[id].length; if (!Number.isSafeInteger(result)) return Infinity; }
    return result;
}
export function* assignments(ids, domains, index = 0, prefix = []) {
    if (index === ids.length) { yield [...prefix]; return; }
    for (const value of domains[ids[index]]) {
        prefix.push(value); yield* assignments(ids, domains, index + 1, prefix); prefix.pop();
    }
}
export function lookup(factor, assignment, domains) {
    let index = 0;
    for (const id of factor.scope) index = index * domains[id].length + domains[id].indexOf(assignment[id]);
    return factor.costs[index];
}
export function sumCosts(costs) {
    if (costs.some(cost => cost === null)) return null;
    const result = costs.reduce((sum, value) => sum + value, 0);
    requireValue(Number.isSafeInteger(result), 'COST_OVERFLOW');
    return result;
}
export function fragment(model, module) {
    const ids = new Set([...module.private, ...module.interface]);
    return {schema: MODEL_SCHEMA, semantics: model.semantics,
        variables: model.variables.filter(v => ids.has(v.id)),
        factors: model.factors.filter(f => module.factorIds.includes(f.id))};
}
export async function seal(body) { return {...body, digest: await sha256(body)}; }
export async function checkSeal(value) {
    const {digest, ...body} = value;
    requireValue(typeof digest === 'string' && digest === await sha256(body), 'DIGEST');
}
export const workKeys = Object.freeze(['inputEntries', 'boundaryCandidates', 'scopeVisits',
    'constructionAssignments', 'constructionFactorLookups', 'qualificationAssignments', 'qualificationFactorLookups',
    'reuseAuditAssignments', 'reuseAuditFactorLookups', 'reuseAuditInputEntries',
    'reuseAuditBoundaryCandidates', 'reuseAuditScopeVisits', 'reuseAuditProfileComparisons', 'boundaryAssignments', 'profileLookups',
    'boundaryFactorLookups', 'outputFactorLookups', 'materializedValues', 'profileComparisons',
    'acceptanceBoundaryAssignments', 'acceptanceProfileLookups', 'acceptanceFactorLookups']);
export function ledger() { return Object.fromEntries(workKeys.map(key => [key, 0])); }
export function workTotal(work) { return workKeys.reduce((sum, key) => sum + work[key], 0); }
export function validateLedger(work) {
    fields(work, workKeys); workKeys.forEach(key => integer(work[key], 0, LIMITS.totalWork * 128));
    return workTotal(work);
}
