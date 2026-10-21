// SPDX-License-Identifier: Apache-2.0
/** Exact finite completion, conservative reuse and deterministic auditable work. No external effects. */
import {CONTRACT_SCHEMA, COMPLETION_SCHEMA, CHECKPOINT_SCHEMA, COMPILER_VERSION,
    CHECKER_VERSION, LIMITS, clone, same, fields, requireValue, integer, validateModel,
    domainMap, cardinality, assignments, lookup, sumCosts, fragment, seal, checkSeal,
    ledger, workTotal, validateLedger} from './model.mjs';
import {verifyContract, verifyDecomposition, verifySelection} from './checker.mjs';

export const ARCHIVE_SCHEMA = 'out-execute-archive/v1';
export const DEFAULT_SELECTION = Object.freeze({maxBoundary: 2, shortlist: null, horizon: 8});
const HISTORY_LIMIT = 16;
const validAttempt = value => typeof value === 'string' && /^[a-zA-Z0-9-]{8,80}$/.test(value);
const trusted = new WeakMap();
const qualifiedCompletions = new WeakMap();
const mark = value => { trusted.set(value, JSON.stringify(value)); return value; };
const trustedNow = value => trusted.get(value) === JSON.stringify(value);
const sourceFields = ['compilerSha256', 'checkerSha256', 'evaluatorVersion'];
function checkSource(source) {
    fields(source, sourceFields);
    requireValue(source.evaluatorVersion === CHECKER_VERSION, 'EVALUATOR_VERSION');
    for (const key of ['compilerSha256', 'checkerSha256']) requireValue(/^[a-f0-9]{64}$/.test(source[key]), 'SOURCE_IDENTITY');
}
function options(input) {
    fields(input, ['maxBoundary', 'shortlist', 'horizon']);
    integer(input.maxBoundary, 0, LIMITS.boundary); integer(input.horizon, 0, 1000);
    requireValue(input.shortlist === null || (Array.isArray(input.shortlist)
        && input.shortlist.length <= 16 && new Set(input.shortlist).size === input.shortlist.length), 'SHORTLIST');
    return clone(input);
}

/** Factor scopes, not a caller's declaration of independence, define private components. */
export function decompose(input, boundary) {
    const model = validateModel(input), ids = model.variables.map(v => v.id);
    requireValue(Array.isArray(boundary) && boundary.length <= LIMITS.boundary
        && new Set(boundary).size === boundary.length && boundary.every(id => ids.includes(id)), 'BOUNDARY');
    boundary = [...boundary].sort();
    const graph = new Map(ids.filter(id => !boundary.includes(id)).map(id => [id, new Set()]));
    for (const factor of model.factors) {
        const local = factor.scope.filter(id => graph.has(id));
        for (const a of local) for (const b of local) if (a !== b) graph.get(a).add(b);
    }
    const groups = [], seen = new Set();
    for (const id of graph.keys()) {
        if (seen.has(id)) continue;
        const todo = [id], group = []; seen.add(id);
        while (todo.length) {
            const current = todo.pop(); group.push(current);
            for (const adjacent of graph.get(current)) if (!seen.has(adjacent)) { seen.add(adjacent); todo.push(adjacent); }
        }
        groups.push(group.sort());
    }
    const modules = groups.map(group => {
        const factors = model.factors.filter(f => f.scope.some(id => group.includes(id)));
        return {id: 'module:' + group.join(','), private: group,
            interface: boundary.filter(id => factors.some(f => f.scope.includes(id))), factorIds: factors.map(f => f.id)};
    });
    const decomposition = {boundary, boundaryFactors: model.factors.filter(f => f.scope.every(id => boundary.includes(id))).map(f => f.id), modules};
    verifyDecomposition(model, decomposition);
    return decomposition;
}

export function selectBoundary(input, selected = DEFAULT_SELECTION) {
    const model = validateModel(input), config = options(selected), domains = domainMap(model);
    const candidates = [...(config.shortlist ?? model.variables.map(v => v.id))].sort();
    requireValue(candidates.every(id => Object.hasOwn(domains, id)), 'SHORTLIST_VARIABLE');
    let candidateCount = 1, choose = 1;
    for (let k = 1; k <= Math.min(config.maxBoundary, candidates.length); k++) {
        choose = choose * (candidates.length - k + 1) / k; candidateCount += choose;
    }
    requireValue(candidateCount <= LIMITS.candidates, 'BOUNDARY_CANDIDATE_BOUND');
    requireValue(candidateCount * model.factors.reduce((n, f) => n + Math.max(1, f.scope.length ** 2), 0)
        <= LIMITS.selectionScopeVisits, 'BOUNDARY_SCOPE_WORK_BOUND');
    let best = null, inspected = 0, scopeVisits = 0;
    function consider(boundary) {
        requireValue(++inspected <= LIMITS.candidates, 'BOUNDARY_CANDIDATE_BOUND');
        const decomposition = decompose(model, boundary);
        scopeVisits += model.factors.reduce((n, f) => n + Math.max(1, f.scope.length ** 2), 0);
        const sizes = decomposition.modules.map(module => cardinality([...module.interface, ...module.private], domains));
        const bound = sizes.reduce((sum, size) => sum + size, 0)
            + config.horizon * Math.max(0, ...sizes) + (config.horizon + 1) * cardinality(boundary, domains);
        const candidate = {decomposition, proxy: Number.isSafeInteger(bound) ? bound : null};
        if (candidate.proxy !== null && (!best || candidate.proxy < best.proxy
            || candidate.proxy === best.proxy && (boundary.length < best.decomposition.boundary.length
                || boundary.length === best.decomposition.boundary.length
                && JSON.stringify(boundary) < JSON.stringify(best.decomposition.boundary)))) best = candidate;
    }
    function visit(start, prefix) {
        consider(prefix);
        if (prefix.length === config.maxBoundary) return;
        for (let i = start; i < candidates.length; i++) visit(i + 1, [...prefix, candidates[i]]);
    }
    visit(0, []);
    requireValue(best !== null, 'NO_FINITE_DECOMPOSITION');
    const rows = best.decomposition.modules.reduce((n, module) => n + cardinality(module.interface, domains), 0);
    requireValue(rows <= LIMITS.profileRows && best.decomposition.modules.every(module =>
        cardinality([...module.private, ...module.interface], domains) <= LIMITS.localAssignments), 'LOCAL_ENUMERATION_BOUND');
    return {...best, inspected, scopeVisits, policy: config};
}

async function compile(model, module) {
    const domains = domainMap(model), rows = [], factors = model.factors.filter(f => module.factorIds.includes(f.id));
    for (const boundary of assignments(module.interface, domains)) {
        let cost = null, witness = null;
        for (const privateValues of assignments(module.private, domains)) {
            const assignment = Object.fromEntries([...module.interface.map((id, i) => [id, boundary[i]]),
                ...module.private.map((id, i) => [id, privateValues[i]])]);
            const value = sumCosts(factors.map(factor => lookup(factor, assignment, domains)));
            if (value !== null && (cost === null || value < cost)) { cost = value; witness = privateValues; }
        }
        rows.push({boundary, cost, witness});
    }
    return seal({schema: CONTRACT_SCHEMA, compilerVersion: COMPILER_VERSION, checkerVersion: CHECKER_VERSION,
        module: clone(module), model: fragment(model, module), rows});
}
function constructionWork(model, module, work) {
    const visits = cardinality([...module.interface, ...module.private], domainMap(model));
    work.constructionAssignments += visits; work.constructionFactorLookups += visits * module.factorIds.length;
    work.qualificationAssignments += visits; work.qualificationFactorLookups += visits * module.factorIds.length;
}
function basis(model, selection, source, prior) {
    const decomposition = selection.decomposition, retained = [], invalidated = [], contracts = [];
    const sameSource = prior && same(source, prior.source);
    for (const module of decomposition.modules) {
        const old = prior?.contracts.find(contract => contract.module.id === module.id);
        if (sameSource && old && same(old.module, module) && same(old.model, fragment(model, module))) {
            retained.push(module.id); contracts.push(clone(old));
        } else {
            invalidated.push({module: module.id, reason: !prior ? 'initial-construction'
                : !sameSource ? 'source-or-evaluator-changed' : !old ? 'new-or-repartitioned-module'
                    : !same(old.module, module) ? 'scope-or-interface-changed' : 'factor-values-or-domain-changed'});
            contracts.push(null);
        }
    }
    const removed = (prior?.decomposition.modules || []).filter(old => !decomposition.modules.some(m => m.id === old.id)).map(m => m.id);
    return {retained, invalidated, removed, contracts};
}
function auditCost(checked) {
    return {assignments: checked.localAssignments + checked.acceptance.assignments,
        factorLookups: checked.localFactorLookups + checked.acceptance.factorLookups + checked.acceptance.profileLookups,
        inputEntries: checked.completion.model.factors.reduce((n, f) => n + f.costs.length, 0),
        boundaryCandidates: checked.completion.selector.inspected, scopeVisits: checked.completion.selector.scopeVisits, profileComparisons: checked.profileComparisons};
}
function initialWork(model, selection, audit) {
    const work = ledger();
    work.inputEntries = model.factors.reduce((n, f) => n + f.costs.length, 0);
    work.boundaryCandidates = selection.inspected; work.scopeVisits = selection.scopeVisits;
    work.reuseAuditAssignments = audit.assignments; work.reuseAuditFactorLookups = audit.factorLookups;
    work.reuseAuditInputEntries = audit.inputEntries; work.reuseAuditBoundaryCandidates = audit.boundaryCandidates;
    work.reuseAuditScopeVisits = audit.scopeVisits; work.reuseAuditProfileComparisons = audit.profileComparisons;
    return work;
}
function requiredFinalWork(model, decomposition, contracts, canStop, work, feasible = true) {
    const domains = domainMap(model), boundaryCount = cardinality(decomposition.boundary, domains);
    const next = clone(work);
    if (!canStop) {
        next.boundaryAssignments += boundaryCount;
        next.profileLookups += boundaryCount * decomposition.modules.length;
        next.boundaryFactorLookups += boundaryCount * decomposition.boundaryFactors.length;
    }
    next.materializedValues += feasible ? model.variables.length : 0;
    next.outputFactorLookups += feasible ? model.factors.length : 0;
    // A separate acceptance reduction is never concealed by the optimization stopping claim.
    next.acceptanceBoundaryAssignments += boundaryCount;
    next.acceptanceProfileLookups += boundaryCount * decomposition.modules.length;
    next.acceptanceFactorLookups += boundaryCount * decomposition.boundaryFactors.length + (feasible ? model.factors.length : 0);
    return next;
}
function equalProfiles(left, right) {
    return same(left.module.interface, right.module.interface)
        && same(left.model.variables.filter(v => left.module.interface.includes(v.id)),
            right.model.variables.filter(v => right.module.interface.includes(v.id)))
        && same(left.rows.map(({boundary, cost}) => ({boundary, cost})), right.rows.map(({boundary, cost}) => ({boundary, cost})));
}
function stopping(model, decomposition, contracts, source, prior, work) {
    if (!prior || !same(source, prior.source) || !same(decomposition, prior.decomposition)) return false;
    if (!same(model.variables, prior.model.variables)
        || !same(model.factors.filter(f => decomposition.boundaryFactors.includes(f.id)),
            prior.model.factors.filter(f => decomposition.boundaryFactors.includes(f.id)))) return false;
    let equal = true;
    for (const [index, contract] of contracts.entries()) {
        work.profileComparisons += contract.rows.length;
        if (!equalProfiles(contract, prior.contracts[index])) equal = false;
    }
    return equal;
}
function compose(model, decomposition, contracts, priorSelection = null) {
    const domains = domainMap(model);
    let selection = priorSelection ? clone(priorSelection) : {status: 'INFEASIBLE', boundary: null, cost: null};
    if (!priorSelection) {
        for (const values of assignments(decomposition.boundary, domains)) {
            const boundary = Object.fromEntries(decomposition.boundary.map((id, i) => [id, values[i]]));
            const costs = model.factors.filter(f => decomposition.boundaryFactors.includes(f.id)).map(f => lookup(f, boundary, domains));
            for (const contract of contracts) costs.push(contract.rows.find(row => same(row.boundary,
                contract.module.interface.map(id => boundary[id]))).cost);
            const cost = sumCosts(costs);
            if (cost !== null && (selection.cost === null || cost < selection.cost)) selection = {status: 'OPTIMAL', boundary, cost};
        }
    }
    if (selection.cost === null) return {selection, artifact: null};
    const artifact = {...selection.boundary};
    for (const contract of contracts) {
        const row = contract.rows.find(row => same(row.boundary, contract.module.interface.map(id => selection.boundary[id])));
        requireValue(row.witness !== null, 'MISSING_CURRENT_WITNESS');
        contract.module.private.forEach((id, i) => { artifact[id] = row.witness[i]; });
    }
    requireValue(sumCosts(model.factors.map(f => lookup(f, artifact, domains))) === selection.cost, 'CURRENT_OUTPUT_CHECK');
    return {selection, artifact};
}

/** Every archived claim is requalified, not made truthful by its content digest. */
const emptyAudit = () => ({assignments: 0, factorLookups: 0, inputEntries: 0, boundaryCandidates: 0, scopeVisits: 0, profileComparisons: 0});
export async function inspectArchive(input) {
    if (input === null) return {archive: null, audit: emptyAudit()};
    const archive = clone(input); fields(archive, ['schema', 'completions']);
    requireValue(archive.schema === ARCHIVE_SCHEMA && Array.isArray(archive.completions)
        && archive.completions.length <= HISTORY_LIMIT
        && new Set(archive.completions.map(item => item.attemptId)).size === archive.completions.length, 'ARCHIVE');
    requireValue(new TextEncoder().encode(JSON.stringify(archive)).length <= LIMITS.bytes, 'ARCHIVE_BYTES');
    let prior = null; const audit = emptyAudit();
    for (const completion of archive.completions) {
        const checked = await inspectCompletion(completion, {prior, historicalAudit: clone(audit)});
        const cost = auditCost(checked); for (const key of Object.keys(audit)) audit[key] += cost[key];
        prior = completion;
    }
    return {archive, audit};
}

export async function startExecution(input, {source, archive = null, selection = DEFAULT_SELECTION,
    budget = LIMITS.totalWork, attemptId = crypto.randomUUID()} = {}) {
    requireValue(validAttempt(attemptId), 'ATTEMPT_ID');
    checkSource(source); integer(budget, 1, LIMITS.totalWork);
    const model = validateModel(input), chosen = selectBoundary(model, selection);
    const rowByteReserve = chosen.decomposition.modules.reduce((total, module) => total
        + cardinality(module.interface, domainMap(model)) * (128 + 8 * (module.interface.length + module.private.length)), 0);
    requireValue(20000 + 3 * new TextEncoder().encode(JSON.stringify(model)).length
        + 3 * new TextEncoder().encode(JSON.stringify(chosen)).length + 2 * rowByteReserve
        + (archive ? new TextEncoder().encode(JSON.stringify(archive)).length : 0) <= LIMITS.bytes, 'COMPLETION_BYTE_RESERVE');
    const checked = await inspectArchive(archive), prior = checked.archive?.completions.at(-1) || null;
    requireValue((checked.archive?.completions.length || 0) < HISTORY_LIMIT, 'HISTORY_FULL');
    requireValue(!checked.archive?.completions.some(item => item.attemptId === attemptId), 'REBOUND_ATTEMPT');
    const plan = basis(model, chosen, source, prior), work = initialWork(model, chosen, checked.audit);
    const checkpoint = {schema: CHECKPOINT_SCHEMA, attemptId, source: clone(source), model, selection: chosen,
        archive: checked.archive || {schema: ARCHIVE_SCHEMA, completions: []}, budget,
        plan: {retained: plan.retained, invalidated: plan.invalidated, removed: plan.removed},
        contracts: plan.contracts, next: 0, work, status: workTotal(work) > budget ? 'INCONCLUSIVE' : 'PAUSED',
        reason: workTotal(work) > budget ? 'ingestion-selection-and-import-audit-exceed-budget' : null, completion: null};
    return mark(checkpoint);
}

/** Reopen data only. Completed rows independently requalify, and all claimed work must reproduce. */
export async function restoreExecution(input) {
    const saved = clone(input);
    fields(saved, ['schema', 'attemptId', 'source', 'model', 'selection', 'archive', 'budget', 'plan', 'contracts',
        'next', 'work', 'status', 'reason', 'completion']);
    requireValue(saved.schema === CHECKPOINT_SCHEMA && ['PAUSED', 'CANCELLED', 'INCONCLUSIVE', 'COMPLETE'].includes(saved.status), 'CHECKPOINT');
    const fresh = await startExecution(saved.model, {source: saved.source, archive: saved.archive,
        selection: saved.selection.policy, budget: saved.budget, attemptId: saved.attemptId});
    const verificationWork = clone(fresh.work);
    const initialStatus = fresh.status;
    let acceptanceStop = false;
    requireValue(same(saved.selection, fresh.selection) && same(saved.plan, fresh.plan), 'CHECKPOINT_PLAN');
    integer(saved.next, 0, saved.contracts.length);
    requireValue(saved.contracts.length === fresh.contracts.length, 'CHECKPOINT_CONTRACTS');
    for (let i = 0; i < saved.contracts.length; i++) {
        if (fresh.contracts[i] !== null) requireValue(same(saved.contracts[i], fresh.contracts[i]), 'CHECKPOINT_RETAINED');
        else if (i < saved.next) {
            requireValue(saved.contracts[i] !== null, 'CHECKPOINT_MISSING_PROGRESS');
            const checked = await verifyContract(saved.model, saved.selection.decomposition.modules[i], saved.contracts[i]);
            verificationWork.reuseAuditAssignments += checked.assignments;
            verificationWork.reuseAuditFactorLookups += checked.factorLookups;
            constructionWork(saved.model, saved.selection.decomposition.modules[i], fresh.work);
        } else requireValue(saved.contracts[i] === null, 'CHECKPOINT_UNRECORDED_PROGRESS');
    }
    if (saved.status === 'COMPLETE') {
        requireValue(initialStatus === 'PAUSED' && saved.reason === null, 'CHECKPOINT_TERMINAL_REASON');
        requireValue(saved.next === saved.contracts.length && saved.completion !== null, 'CHECKPOINT_COMPLETION');
        const inspected = await inspectCompletion(saved.completion, {prior: fresh.archive.completions.at(-1) || null,
            historicalAudit: {assignments: fresh.work.reuseAuditAssignments, factorLookups: fresh.work.reuseAuditFactorLookups,
                inputEntries: fresh.work.reuseAuditInputEntries, boundaryCandidates: fresh.work.reuseAuditBoundaryCandidates,
                scopeVisits: fresh.work.reuseAuditScopeVisits, profileComparisons: fresh.work.reuseAuditProfileComparisons}});
        const additional = auditCost(inspected);
        verificationWork.reuseAuditAssignments += additional.assignments;
        verificationWork.reuseAuditFactorLookups += additional.factorLookups;
        verificationWork.reuseAuditInputEntries += additional.inputEntries;
        verificationWork.reuseAuditBoundaryCandidates += additional.boundaryCandidates;
        verificationWork.reuseAuditScopeVisits += additional.scopeVisits;
        verificationWork.reuseAuditProfileComparisons += additional.profileComparisons;
        requireValue(same(inspected.completion.contracts, saved.contracts)
            && same(inspected.completion.model, saved.model) && same(inspected.completion.source, saved.source)
            && inspected.completion.budget === saved.budget && inspected.completion.attemptId === saved.attemptId, 'CHECKPOINT_COMPLETION_BINDING');
        fresh.work = saved.completion.work;
    } else {
        requireValue(saved.completion === null, 'UNFINISHED_ACCEPTANCE');
        if (saved.status === 'INCONCLUSIVE' && saved.reason === 'current-acceptance-exceeds-budget') {
            requireValue(initialStatus === 'PAUSED' && workTotal(fresh.work) <= saved.budget, 'CHECKPOINT_REACHABLE_PROGRESS');
            requireValue(saved.next === saved.contracts.length, 'CHECKPOINT_ACCEPTANCE_PROGRESS');
            const beforeComparisons = fresh.work.profileComparisons;
            acceptanceStop = stopping(saved.model, saved.selection.decomposition, saved.contracts, saved.source,
                fresh.archive.completions.at(-1) || null, fresh.work);
            verificationWork.reuseAuditProfileComparisons += fresh.work.profileComparisons - beforeComparisons;
        }
    }
    requireValue(same(saved.work, fresh.work), 'CHECKPOINT_WORK');
    validateLedger(saved.work);
    if (saved.status === 'INCONCLUSIVE') {
        if (saved.reason === 'ingestion-selection-and-import-audit-exceed-budget') {
            requireValue(initialStatus === 'INCONCLUSIVE' && saved.next === 0, 'CHECKPOINT_BUDGET_REASON');
        } else if (saved.reason === 'next-module-exceeds-budget') {
            requireValue(initialStatus === 'PAUSED' && workTotal(fresh.work) <= saved.budget
                && saved.next < saved.contracts.length && saved.contracts[saved.next] === null, 'CHECKPOINT_BUDGET_REASON');
            const proposed = clone(fresh.work);
            constructionWork(saved.model, saved.selection.decomposition.modules[saved.next], proposed);
            requireValue(workTotal(proposed) > saved.budget, 'CHECKPOINT_BUDGET_REASON');
        } else if (saved.reason === 'current-acceptance-exceeds-budget') {
            const required = requiredFinalWork(saved.model, saved.selection.decomposition, saved.contracts, acceptanceStop, fresh.work);
            requireValue(workTotal(required) > saved.budget, 'CHECKPOINT_BUDGET_REASON');
        } else requireValue(false, 'CHECKPOINT_REASON');
    } else if (saved.status !== 'COMPLETE') {
        requireValue(initialStatus === 'PAUSED' && workTotal(fresh.work) <= saved.budget
            && (saved.next < saved.contracts.length || saved.next === 0 && saved.contracts.length === 0), 'CHECKPOINT_REACHABLE_PROGRESS');
        requireValue(saved.reason === (saved.status === 'CANCELLED' ? 'operator-cancelled' : null), 'CHECKPOINT_TERMINAL_REASON');
    }
    return {checkpoint: mark(saved), verificationWork, countedVerificationWork: workTotal(verificationWork),
        scope: 'additional-import-verification-not-in-frozen-completion-cost'};
}

export async function advanceExecution(input, {modules = 1, cancel = false} = {}) {
    requireValue(trustedNow(input), 'EXPLICIT_RESTORE_REQUIRED');
    const state = clone(input);
    integer(modules, 0, LIMITS.variables);
    if (state.status === 'COMPLETE' || state.status === 'INCONCLUSIVE') return mark(state);
    if (cancel) { state.status = 'CANCELLED'; state.reason = 'operator-cancelled'; return mark(state); }
    state.status = 'PAUSED'; state.reason = null;
    let processed = 0;
    while (state.next < state.contracts.length && processed < modules) {
        const i = state.next, module = state.selection.decomposition.modules[i];
        if (state.contracts[i] === null) {
            const proposed = clone(state.work); constructionWork(state.model, module, proposed);
            if (workTotal(proposed) > state.budget) { state.status = 'INCONCLUSIVE'; state.reason = 'next-module-exceeds-budget'; return mark(state); }
            const contract = await compile(state.model, module);
            await verifyContract(state.model, module, contract);
            state.contracts[i] = contract; state.work = proposed;
        }
        state.next++; processed++;
    }
    if (state.next !== state.contracts.length) return mark(state);
    const prior = state.archive.completions.at(-1) || null, proposed = clone(state.work);
    const semanticStop = stopping(state.model, state.selection.decomposition, state.contracts, state.source, prior, proposed);
    let finalWork = requiredFinalWork(state.model, state.selection.decomposition, state.contracts, semanticStop, proposed);
    if (workTotal(finalWork) > state.budget) { state.work = proposed; state.status = 'INCONCLUSIVE'; state.reason = 'current-acceptance-exceeds-budget'; return mark(state); }
    const result = compose(state.model, state.selection.decomposition, state.contracts, semanticStop ? prior.selection : null);
    await verifySelection(state.model, state.selection.decomposition, state.contracts, result.selection, result.artifact);
    finalWork = requiredFinalWork(state.model, state.selection.decomposition, state.contracts, semanticStop, proposed, result.selection.status === 'OPTIMAL');
    state.work = finalWork;
    state.completion = await seal({schema: COMPLETION_SCHEMA, attemptId: state.attemptId, source: state.source, model: state.model,
        selector: state.selection, decomposition: state.selection.decomposition, contracts: state.contracts,
        selection: result.selection, artifact: result.artifact, change: {...state.plan, rebuilt: state.plan.invalidated.map(v => v.module), semanticStop},
        work: state.work, countedWork: workTotal(state.work), budget: state.budget,
        parentDigest: prior?.digest || null, cumulativeCountedWork: (prior?.cumulativeCountedWork || 0) + workTotal(state.work),
        evidence: {scope: 'supplied-finite-model-only', sourceAuthenticity: 'not-established', authority: [], paymentRoute: 'none',
            excludedCosts: ['wall-clock', 'currency', 'unmodeled physical work', 'host bookkeeping, JSON and hashing instructions']}});
    state.status = 'COMPLETE'; state.reason = null;
    return mark(state);
}

export async function inspectCompletion(input, {prior = null, historicalAudit = emptyAudit()} = {}) {
    const completion = clone(input);
    fields(completion, ['schema', 'attemptId', 'source', 'model', 'selector', 'decomposition', 'contracts', 'selection', 'artifact',
        'change', 'work', 'countedWork', 'budget', 'parentDigest', 'cumulativeCountedWork', 'evidence', 'digest']);
    requireValue(completion.schema === COMPLETION_SCHEMA && validAttempt(completion.attemptId), 'COMPLETION_VERSION'); checkSource(completion.source);
    integer(completion.budget, 1, LIMITS.totalWork);
    const model = validateModel(completion.model), chosen = selectBoundary(model, completion.selector.policy);
    requireValue(same(chosen, completion.selector) && same(chosen.decomposition, completion.decomposition), 'COMPLETION_DECOMPOSITION');
    requireValue(completion.parentDigest === (prior?.digest || null), 'MISSING_OR_WRONG_ANCESTOR');
    if (prior) requireValue(qualifiedCompletions.get(prior) === JSON.stringify(prior), 'ANCESTOR_NOT_INDEPENDENTLY_CHECKED');
    const plan = basis(model, chosen, completion.source, prior);
    const work = initialWork(model, chosen, historicalAudit); let localAssignments = 0, localFactorLookups = 0;
    requireValue(Array.isArray(completion.contracts) && completion.contracts.length === chosen.decomposition.modules.length, 'COMPLETION_PROFILE_VECTOR');
    for (const [i, module] of chosen.decomposition.modules.entries()) {
        const audit = await verifyContract(model, module, completion.contracts[i]);
        localAssignments += audit.assignments; localFactorLookups += audit.factorLookups;
        if (plan.contracts[i] === null) constructionWork(model, module, work);
        else requireValue(same(plan.contracts[i], completion.contracts[i]), 'COMPLETION_REUSED_PROFILE');
    }
    const semanticStop = stopping(model, chosen.decomposition, completion.contracts, completion.source, prior, work);
    const finalWork = requiredFinalWork(model, chosen.decomposition, completion.contracts, semanticStop, work, completion.selection.status === 'OPTIMAL');
    requireValue(same(completion.change, {retained: plan.retained, invalidated: plan.invalidated, removed: plan.removed,
        rebuilt: plan.invalidated.map(v => v.module), semanticStop}), 'COMPLETION_CHANGE_ACCOUNT');
    requireValue(same(completion.work, finalWork) && completion.countedWork === workTotal(finalWork)
        && completion.countedWork <= completion.budget
        && completion.cumulativeCountedWork === (prior?.cumulativeCountedWork || 0) + completion.countedWork, 'COMPLETION_COST_ACCOUNT');
    requireValue(same(completion.evidence, {scope: 'supplied-finite-model-only', sourceAuthenticity: 'not-established', authority: [], paymentRoute: 'none',
        excludedCosts: ['wall-clock', 'currency', 'unmodeled physical work', 'host bookkeeping, JSON and hashing instructions']}), 'COMPLETION_AUTHORITY');
    const acceptance = verifySelection(model, chosen.decomposition, completion.contracts, completion.selection, completion.artifact);
    await checkSeal(completion);
    qualifiedCompletions.set(input, JSON.stringify(input));
    qualifiedCompletions.set(completion, JSON.stringify(completion));
    return {completion, localAssignments, localFactorLookups, profileComparisons: work.profileComparisons, acceptance};
}

export async function retainCompletion(input) {
    requireValue(trustedNow(input), 'EXPLICIT_RESTORE_REQUIRED');
    const state = input;
    requireValue(state.status === 'COMPLETE', 'UNFINISHED_ACCEPTANCE');
    const archive = {schema: ARCHIVE_SCHEMA, completions: [...state.archive.completions, state.completion]};
    requireValue(new TextEncoder().encode(JSON.stringify(archive)).length <= LIMITS.bytes, 'ARCHIVE_BYTES');
    return clone(archive);
}

export async function execute(model, options = {}) {
    let state = await startExecution(model, options);
    while (state.status === 'PAUSED') state = await advanceExecution(state, {modules: LIMITS.variables});
    return state;
}
