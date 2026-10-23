// SPDX-License-Identifier: Apache-2.0
// Independent reimplementation of the selected manuscript's finite scalar model.
import {canonical} from '../successor-capability/discovery-lab-contract.mjs';
const MAX_M = 10, MAX_COST = 1_000_000_000, MAX_RECIPES = 64, MAX_PRODUCERS = 32;
const need = (ok, message) => { if (!ok) throw new TypeError(message); };
const integer = (x, lo = 0, hi = MAX_COST) => Number.isSafeInteger(x) && !Object.is(x, -0) && x >= lo && x <= hi;
const add = (a, b) => { const x = a + b; need(Number.isSafeInteger(x), 'Exact integer accounting overflow.'); return x; };
const contains = (stock, target) => (stock & target) === target;
const popcount = x => { let n = 0; for (; x; x &= x - 1) n++; return n; };
const own = value => JSON.parse(canonical(value));

function exact(value, keys) {
    need(value && !Array.isArray(value) && Object.keys(value).length === keys.length
        && keys.every(key => Object.hasOwn(value, key)), `Expected fields: ${keys.join(', ')}.`);
}
function catalogue(input) {
    const spec = own(input); exact(spec, ['capabilities', 'recipes']);
    need(Array.isArray(spec.capabilities) && spec.capabilities.length <= MAX_M, 'At most ten capabilities admitted.');
    const names = [...spec.capabilities];
    need(names.every(n => typeof n === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,39}$/.test(n))
        && new Set(names).size === names.length, 'Distinct finite capability names required.');
    const mask = list => {
        need(Array.isArray(list) && list.length <= names.length && new Set(list).size === list.length,
            'A stock is a finite set.');
        let bits = 0;
        for (const item of list) {
            const index = names.indexOf(item); need(index >= 0, 'Unknown capability.'); bits |= 1 << index;
        }
        return bits;
    };
    need(Array.isArray(spec.recipes) && spec.recipes.length <= MAX_RECIPES, 'At most 64 recipes admitted.');
    const ids = new Set();
    const recipes = spec.recipes.map(r => {
        exact(r, ['id', 'requires', 'produces', 'cost']);
        need(typeof r.id === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,59}$/.test(r.id) && !ids.has(r.id),
            'Distinct finite recipe ids required.'); ids.add(r.id);
        need(integer(r.cost), 'Recipe charges must be nonnegative safe integers, at most one billion.');
        return {id: r.id, requires: mask(r.requires), produces: mask(r.produces), cost: r.cost};
    });
    return {names, recipes, mask, size: 1 << names.length, spec,
        key: JSON.stringify({capabilities: names, recipes: recipes.map(r => [r.id, r.requires, r.produces, r.cost])})};
}
const stockNames = (m, bits) => m.names.filter((_, i) => bits & (1 << i));
function limits(raw = {}) {
    const o = own(raw); need(o && !Array.isArray(o) && Object.keys(o).every(k => ['maxStates', 'maxExpansions', 'maxElapsedMs'].includes(k)),
        'Unknown completion limit.');
    const result = {maxStates: 1024, maxExpansions: 65_536, maxElapsedMs: 10_000, ...o};
    need(integer(result.maxStates, 0, 1024) && integer(result.maxExpansions, 0, 65_536)
        && integer(result.maxElapsedMs, 0, 60_000), 'Invalid finite completion limits.');
    return result;
}
const now = () => globalThis.performance?.now() ?? Date.now();
function path(m, initial, terminal, parents, total) {
    const reverse = []; let state = terminal;
    while (state !== initial) {
        const p = parents.get(state); need(p && p.previous !== state, 'Missing reconstruction predecessor.');
        reverse.push({recipeId: p.recipe.id, from: stockNames(m, p.previous), to: stockNames(m, state),
            charge: p.recipe.cost}); state = p.previous;
    }
    let cumulative = 0;
    return {initial: stockNames(m, initial), final: stockNames(m, terminal), cost: total,
        steps: reverse.reverse().map(s => ({...s, cumulative: cumulative = add(cumulative, s.charge)}))};
}
function search(m, initial, target, cap) {
    const began = now(), distance = new Map([[initial, 0]]), parents = new Map(), settled = new Set();
    let expansions = 0;
    const incomplete = reason => ({status: 'INCONCLUSIVE', cost: null, reason,
        discoveredStates: distance.size, expandedStates: settled.size, recipeChecks: expansions,
        unreachableCertificate: null, witness: null});
    if (contains(initial, target)) return {status: 'FOUND', cost: 0,
        witness: path(m, initial, initial, parents, 0), discoveredStates: 1, expandedStates: 0, recipeChecks: 0};
    for (;;) {
        let current = null, best = Infinity;
        for (const [s, d] of distance) if (!settled.has(s) && (d < best || d === best && s < current)) {
            current = s; best = d;
        }
        if (current === null) return {status: 'UNREACHABLE', cost: null, witness: null,
            unreachableCertificate: {initial: stockNames(m, initial), target: stockNames(m, target),
                reachable: [...settled].sort((a, b) => a - b).map(s => stockNames(m, s))},
            discoveredStates: distance.size, expandedStates: settled.size, recipeChecks: expansions};
        if (now() - began >= cap.maxElapsedMs) return incomplete('SOFT_ELAPSED_CAP');
        if (settled.size >= cap.maxStates) return incomplete('STATE_CAP');
        settled.add(current);
        if (contains(current, target)) return {status: 'FOUND', cost: best,
            witness: path(m, initial, current, parents, best), discoveredStates: distance.size,
            expandedStates: settled.size, recipeChecks: expansions};
        for (const recipe of m.recipes) {
            if (expansions >= cap.maxExpansions) return incomplete('RECIPE_CHECK_CAP');
            expansions++;
            if (!contains(current, recipe.requires)) continue;
            const next = current | recipe.produces;
            if (next === current) continue;
            const candidate = add(best, recipe.cost);
            if (!distance.has(next)) {
                if (distance.size >= cap.maxStates) return incomplete('STATE_CAP');
                distance.set(next, candidate); parents.set(next, {previous: current, recipe});
            } else if (candidate < distance.get(next)) {
                distance.set(next, candidate); parents.set(next, {previous: current, recipe});
            }
        }
    }
}

/** Minimum pure-expense reconstruction to any superset of target. Capped work never proves impossibility. */
export function completion(spec, stock, target, options = {}) {
    const m = catalogue(spec); return search(m, m.mask(own(stock)), m.mask(own(target)), limits(options));
}
function dynamic(m, target, cap) {
    const values = new Array(m.size).fill(Infinity), chosen = new Map();
    const order = Array.from({length: m.size}, (_, i) => i).sort((a, b) => popcount(b) - popcount(a) || b - a);
    const began = now(); let checked = 0, states = 0;
    for (const stock of order) {
        if (states >= cap.maxStates || now() - began >= cap.maxElapsedMs) return {status: 'INCONCLUSIVE', states, checked};
        states++;
        if (contains(stock, target)) { values[stock] = 0; continue; }
        for (const recipe of m.recipes) {
            if (checked >= cap.maxExpansions) return {status: 'INCONCLUSIVE', states, checked};
            checked++;
            if (!contains(stock, recipe.requires)) continue;
            const next = stock | recipe.produces;
            if (next === stock || values[next] === Infinity) continue;
            const cost = add(recipe.cost, values[next]);
            if (cost < values[stock]) { values[stock] = cost; chosen.set(stock, recipe); }
        }
    }
    return {status: 'COMPLETE', states, checked, values, chosen};
}

/** Independent target-specific Bellman recursion, processing larger stocks before smaller stocks. */
export function completionDynamic(spec, stock, target, options = {}) {
    const m = catalogue(spec), initial = m.mask(own(stock)), goal = m.mask(own(target));
    const result = dynamic(m, goal, limits(options));
    if (result.status !== 'COMPLETE') return {status: 'INCONCLUSIVE', cost: null, witness: null,
        reason: 'DYNAMIC_PROGRAM_CAP', evaluatedStates: result.states, recipeChecks: result.checked};
    const cost = result.values[initial];
    if (cost === Infinity) return {status: 'UNREACHABLE', cost: null, witness: null,
        evaluatedStates: result.states, recipeChecks: result.checked};
    const parents = new Map(); let current = initial;
    while (!contains(current, goal)) {
        const recipe = result.chosen.get(current); need(recipe, 'Dynamic reconstruction absent.');
        const next = current | recipe.produces; parents.set(next, {previous: current, recipe}); current = next;
    }
    return {status: 'FOUND', cost, witness: path(m, initial, current, parents, cost),
        evaluatedStates: result.states, recipeChecks: result.checked};
}

/** Check feasibility of an emitted finite witness, or closure of an unreachable certificate. */
export function checkCompletionWitness(spec, stock, target, candidate) {
    const m = catalogue(spec), initial = m.mask(own(stock)), goal = m.mask(own(target)), r = own(candidate);
    if (r.status === 'FOUND') {
        const w = r.witness; need(w && Array.isArray(w.steps) && w.steps.length <= m.names.length,
            'Finite witness required.');
        need(m.mask(w.initial) === initial && integer(w.cost, 0, Number.MAX_SAFE_INTEGER), 'Witness initial state/cost mismatch.');
        let current = initial, cost = 0;
        for (const step of w.steps) {
            const recipe = m.recipes.find(s => s.id === step.recipeId);
            need(recipe && contains(current, recipe.requires) && m.mask(step.from) === current,
                'Recipe is not executable at the recorded stock.');
            const next = current | recipe.produces; cost = add(cost, recipe.cost);
            need(next !== current && m.mask(step.to) === next && step.charge === recipe.cost && step.cumulative === cost,
                'Recipe charge or stock transition mismatch.'); current = next;
        }
        need(contains(current, goal) && m.mask(w.final) === current && cost === w.cost && cost === r.cost,
            'Witness does not attain its target and stated cost.');
        return {verified: true, scope: 'executable feasibility; minimum checked separately by dynamic programming'};
    }
    need(r.status === 'UNREACHABLE' && r.cost === null && r.unreachableCertificate, 'Complete unreachable certificate required.');
    const c = r.unreachableCertificate, reached = c.reachable.map(s => m.mask(s)), set = new Set(reached);
    need(set.size === reached.length && set.has(initial) && m.mask(c.initial) === initial && m.mask(c.target) === goal,
        'Unreachable certificate initial/target/duplicates mismatch.');
    for (const s of reached) {
        need(!contains(s, goal), 'A reachable stock contains the target.');
        for (const recipe of m.recipes) if (contains(s, recipe.requires)) {
            need(set.has(s | recipe.produces), 'Reachable-set certificate is not closed under recipes.');
        }
    }
    return {verified: true, scope: 'closed reachable set excludes the target'};
}

/** Complete finite table, independently checked by the decreasing-stock recursion. */
export function completionTable(spec, options = {}) {
    const m = catalogue(spec), cap = limits(options);
    need(m.names.length <= 7, 'Full table is limited to seven capabilities.');
    const matrix = Array.from({length: m.size}, () => new Array(m.size));
    let valuesChecked = 0, witnessesChecked = 0;
    for (let target = 0; target < m.size; target++) {
        const reference = dynamic(m, target, cap);
        if (reference.status !== 'COMPLETE') return {status: 'INCONCLUSIVE', valuesChecked, witnessesChecked, matrix: null};
        for (let initial = 0; initial < m.size; initial++) {
            const r = search(m, initial, target, cap);
            if (r.status === 'INCONCLUSIVE') return {status: 'INCONCLUSIVE', valuesChecked, witnessesChecked, matrix: null};
            const expected = reference.values[initial] === Infinity ? null : reference.values[initial];
            need(r.cost === expected, 'Independent reconstruction algorithms disagree.'); valuesChecked++;
            checkCompletionWitness(m.spec, stockNames(m, initial), stockNames(m, target), r); witnessesChecked++;
            matrix[initial][target] = r.cost;
        }
    }
    return {status: 'COMPLETE', matrix, stocks: Array.from({length: m.size}, (_, i) => stockNames(m, i)),
        valuesChecked, witnessesChecked, geometry: qualifyCompletionMap(matrix),
        source: 'independent implementation; not the unavailable manuscript companion'};
}
function mapData(raw) {
    const matrix = own(raw);
    need(Array.isArray(matrix) && matrix.length > 0 && matrix.length <= 128
        && matrix.every(row => Array.isArray(row) && row.length === matrix.length
            && row.every(x => x === null || integer(x, 0, Number.MAX_SAFE_INTEGER))), 'Finite square completion table required.');
    return matrix;
}

/** Finite tables are not certified by naming them completion costs: check their triangle explicitly. */
export function qualifyCompletionMap(raw) {
    const matrix = mapData(raw), n = matrix.length; let triples = 0;
    for (let i = 0; i < n; i++) if (matrix[i][i] !== 0) return {status: 'INVALID_REFLEXIVITY', stock: i};
    for (let l = 0; l < n; l++) for (let k = 0; k < n; k++) for (let q = 0; q < n; q++) {
        triples++;
        const direct = matrix[l][q], first = matrix[l][k], second = matrix[k][q];
        if (first === null || second === null) continue;
        const via = add(first, second);
        if (direct === null || direct > via) return {status: 'TRIANGLE_VIOLATION', triplesChecked: triples,
            witness: {L: l, K: k, Q: q, direct, first, second, via}};
    }
    const finite = matrix.every(row => row.every(x => x !== null));
    return {status: finite ? 'QUALIFIED_FINITE' : 'QUALIFIED_EXTENDED', finite, triplesChecked: triples,
        interpretation: finite ? 'Finite reflexive directed triangle verified.' : 'Jointly unavailable targets cannot be subtracted.'};
}
function producers(m, input) {
    const rows = own(input);
    need(Array.isArray(rows) && rows.length > 0 && rows.length <= MAX_PRODUCERS, 'One to 32 complete producers required.');
    const ids = new Set();
    return rows.map(p => {
        exact(p, ['id', 'kappa', 'delta', 'stock']);
        need(typeof p.id === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,59}$/.test(p.id) && !ids.has(p.id),
            'Distinct producer identities required.'); ids.add(p.id);
        need(integer(p.kappa) && integer(p.delta, -MAX_COST) && p.kappa + p.delta >= 0,
            'Reserve-closed integer producer required: kappa >= 0, kappa + delta >= 0.');
        return {...p, bits: m.mask(p.stock)};
    });
}
const publicProducer = p => ({id: p.id, kappa: p.kappa, delta: p.delta, stock: [...p.stock]});
function requirement(m, p, goal, x, cap) {
    const reconstruction = search(m, p.bits, goal, cap);
    if (reconstruction.status !== 'FOUND') return {status: reconstruction.status, capital: null,
        producer: publicProducer(p), reconstruction};
    const capital = Math.max(p.kappa, add(add(x, -p.delta), reconstruction.cost));
    return {status: 'FOUND', capital, producer: publicProducer(p), reconstruction};
}
export function capitalRequirement(spec, producer, target, terminalCash, options = {}) {
    const m = catalogue(spec), p = producers(m, [producer])[0], q = m.mask(own(target));
    need(integer(terminalCash, 0, 1_000_000_000_000), 'Nonnegative integer terminal cash target at most one trillion required.');
    return requirement(m, p, q, terminalCash, limits(options));
}
function envelope(m, family, goal, x, cap) {
    const alternatives = family.map(p => requirement(m, p, goal, x, cap));
    if (alternatives.some(r => r.status === 'INCONCLUSIVE')) return {status: 'INCONCLUSIVE', capital: null, alternatives};
    const feasible = alternatives.filter(r => r.status === 'FOUND');
    if (!feasible.length) return {status: 'UNREACHABLE', capital: null, alternatives};
    const selected = feasible.reduce((a, b) => b.capital < a.capital ? b : a);
    return {status: 'FOUND', capital: selected.capital, producer: selected.producer,
        reconstruction: selected.reconstruction, alternatives,
        interpretation: 'One whole producer is chosen after this target is specified; no pre-target universal controller claim.'};
}
export function portfolioCapital(spec, family, target, terminalCash, options = {}) {
    const m = catalogue(spec), ps = producers(m, family), q = m.mask(own(target));
    need(integer(terminalCash, 0, 1_000_000_000_000), 'Nonnegative integer terminal cash target at most one trillion required.');
    return envelope(m, ps, q, terminalCash, limits(options));
}
function subset(family, raw) {
    const ids = own(raw); need(Array.isArray(ids) && ids.length > 0 && new Set(ids).size === ids.length,
        'A nonempty retained subfamily is required.');
    return ids.map(id => { const p = family.find(p => p.id === id); need(p, 'Retained producer is absent from full family.'); return p; });
}
function pair(m, a, b, cap) {
    const reconstruction = search(m, b.bits, a.bits, cap);
    if (reconstruction.status !== 'FOUND') return {status: reconstruction.status, from: a.id, to: b.id,
        distance: null, reconstruction};
    const distance = Math.max(b.kappa - a.kappa, add(a.delta - b.delta, reconstruction.cost));
    return {status: 'FOUND', from: a.id, to: b.id, distance, reconstruction};
}
function law(m, family, retained, cap) {
    const comparisons = family.map(a => ({producer: a.id, alternatives: retained.map(b => pair(m, a, b, cap))}));
    if (comparisons.some(r => r.alternatives.some(c => c.status === 'INCONCLUSIVE'))) {
        return {status: 'INCONCLUSIVE', loss: null, comparisons};
    }
    let worst = null;
    for (const row of comparisons) {
        const feasible = row.alternatives.filter(c => c.status === 'FOUND');
        if (!feasible.length) {
            const a = family.find(p => p.id === row.producer), x = add(a.kappa, a.delta);
            return {status: 'UNBOUNDED_MISSING_CAPABILITY', loss: null, maximizingProducer: a.id,
                witness: {target: [...a.stock], terminalCash: x,
                    full: envelope(m, family, a.bits, x, cap), retained: envelope(m, retained, a.bits, x, cap)}, comparisons,
                interpretation: 'Retained capital is unavailable while full capital is finite; no infinity subtraction.'};
        }
        row.selected = feasible.reduce((a, b) => b.distance < a.distance ? b : a);
        if (!worst || row.selected.distance > worst.selected.distance) worst = row;
    }
    const a = family.find(p => p.id === worst.producer), x = add(a.kappa, a.delta);
    const full = envelope(m, family, a.bits, x, cap), kept = envelope(m, retained, a.bits, x, cap);
    if (full.status !== 'FOUND' || kept.status !== 'FOUND') return {status: 'INCONCLUSIVE', loss: null, comparisons};
    const loss = worst.selected.distance;
    need(loss >= 0 && kept.capital - full.capital === loss, 'Attaining retention witness mismatch.');
    return {status: 'FINITE', loss, maximizingProducer: a.id,
        witness: {target: [...a.stock], terminalCash: x, full, retained: kept, actualLoss: kept.capital - full.capital},
        comparisons, geometry: 'optional durable stock, nonnegative pure-expense recipes; concatenability follows structurally',
        scope: 'Targets constructible by the full portfolio; jointly unreachable targets are excluded, not subtracted.',
        interpretation: 'Retrospective target-specific portfolio guarantee; retained plans are not acquired capabilities.'};
}
export function retentionLaw(spec, family, retainedIds, options = {}) {
    const m = catalogue(spec), ps = producers(m, family); return law(m, ps, subset(ps, retainedIds), limits(options));
}
export function epsilonCover(spec, family, retainedIds, epsilon, options = {}) {
    need(integer(epsilon), 'Nonnegative integer substitution allowance required.');
    const r = retentionLaw(spec, family, retainedIds, options);
    return {...r, epsilon, covered: r.status === 'FINITE' ? r.loss <= epsilon : r.status === 'INCONCLUSIVE' ? null : false};
}
export function productiveDominance(spec, producer, replacement, options = {}) {
    const m = catalogue(spec), a = producers(m, [producer])[0], b = producers(m, [replacement])[0];
    need(a.id !== b.id || canonical(publicProducer(a)) === canonical(publicProducer(b)), 'One producer id cannot identify incompatible policies.');
    const result = pair(m, a, b, limits(options));
    return {...result, dominates: result.status === 'FOUND' ? result.distance <= 0 : result.status === 'INCONCLUSIVE' ? null : false};
}
export function pruneDominated(spec, family, options = {}) {
    const m = catalogue(spec), ps = producers(m, family), cap = limits(options);
    const pairs = ps.map(a => ps.map(b => pair(m, a, b, cap)));
    if (pairs.some(row => row.some(r => r.status === 'INCONCLUSIVE'))) return {status: 'INCONCLUSIVE', retained: null, pairs};
    const dominates = (i, j) => pairs[i][j].status === 'FOUND' && pairs[i][j].distance <= 0;
    const kept = ps.filter((_, i) => !ps.some((_, j) => i !== j && dominates(i, j)
        && (!dominates(j, i) || j < i)));
    need(kept.length > 0, 'Stable productive pruning cannot delete every producer.');
    const certificates = ps.map((p, i) => {
        const replacement = kept.find(b => dominates(i, ps.indexOf(b)));
        need(replacement, 'No retained domination witness.'); return pairs[i][ps.indexOf(replacement)];
    });
    return {status: 'COMPLETE', retained: kept.map(publicProducer), certificates,
        loss: law(m, ps, kept, cap), rule: 'Strictly dominated producers removed; earliest representative of each equivalence class retained.'};
}
export function substitutionChain(spec, family, chainIds, allowances, options = {}) {
    const m = catalogue(spec), ps = producers(m, family), ids = own(chainIds), eps = own(allowances), cap = limits(options);
    need(Array.isArray(ids) && ids.length >= 2 && ids.length <= MAX_PRODUCERS && Array.isArray(eps)
        && eps.length === ids.length - 1 && eps.every(x => integer(x)), 'Finite linked substitutions and allowances required.');
    const chain = ids.map(id => { const p = ps.find(p => p.id === id); need(p, 'Chain producer absent.'); return p; });
    const steps = []; let cumulativeAllowance = 0;
    for (let i = 0; i < chain.length - 1; i++) {
        const r = pair(m, chain[i], chain[i + 1], cap);
        if (r.status !== 'FOUND') return {status: r.status, cumulativeAllowance: null, steps: [...steps, r]};
        need(r.distance <= eps[i], 'A substitution exceeds its stated allowance.');
        cumulativeAllowance = add(cumulativeAllowance, eps[i]); steps.push({...r, allowance: eps[i], cumulativeAllowance});
    }
    const direct = pair(m, chain[0], chain.at(-1), cap);
    if (direct.status === 'INCONCLUSIVE') return {status: 'INCONCLUSIVE', cumulativeAllowance, steps, direct,
        scope: 'Linked substitutions are complete; the tighter direct replay exhausted its declared cap.'};
    need(direct.status === 'FOUND' && direct.distance <= cumulativeAllowance, 'Substitution triangle witness mismatch.');
    return {status: 'COMPLETE', cumulativeAllowance, steps, direct,
        scope: 'Same fixed catalogue and accounting unit for every linked substitution.'};
}

/** Given actual whole-path resource receipts, select only a jointly feasible path. No scalar theorem is inferred. */
export function resourceWitness(candidates, budget) {
    const paths = own(candidates), caps = own(budget);
    need(Array.isArray(caps) && caps.length > 0 && caps.length <= 8 && caps.every(x => integer(x)), 'Finite resource budget required.');
    need(Array.isArray(paths) && paths.length <= 128, 'Finite actual path receipts required.');
    const seen = new Set();
    const inspected = paths.map(p => {
        exact(p, ['id', 'steps']); need(typeof p.id === 'string' && !seen.has(p.id) && Array.isArray(p.steps)
            && p.steps.length <= 64, 'Distinct finite resource paths required.'); seen.add(p.id);
        const total = new Array(caps.length).fill(0);
        for (const step of p.steps) {
            need(Array.isArray(step) && step.length === caps.length && step.every(x => integer(x)), 'Whole path resource vector required.');
            step.forEach((v, i) => { total[i] = add(total[i], v); });
        }
        return {...p, total, feasible: total.every((v, i) => v <= caps[i])};
    });
    return {status: inspected.some(p => p.feasible) ? 'FEASIBLE_PATH' : 'NO_SUPPLIED_PATH_FITS', budget: caps,
        selected: inspected.find(p => p.feasible) ?? null, paths: inspected,
        scope: 'Checks supplied actual whole-path receipts; does not establish completeness of a multidimensional search.'};
}
export function profileFromTrace(events) {
    const trace = own(events); need(Array.isArray(trace) && trace.length <= 64, 'Finite complete-policy cash trace required.');
    let cash = 0, reserve = 0, kappa = 0;
    const prefixes = trace.map(e => {
        exact(e, ['id', 'cashChange', 'reserveChange']);
        need(typeof e.id === 'string' && integer(e.cashChange, -MAX_COST) && integer(e.reserveChange, -MAX_COST), 'Exact cash/reserve movements required.');
        cash = add(cash, e.cashChange); reserve = add(reserve, e.reserveChange);
        need(reserve >= 0, 'A trace cannot release an absent reserve.'); kappa = Math.max(kappa, reserve - cash, 0);
        return {...e, cumulativeCash: cash, reserve, requiredOpeningCapital: kappa};
    });
    need(reserve === 0, 'Producer must close all represented reserves.');
    return {kappa, delta: cash, prefixes, accountingUnit: 'synthetic cash; hypothetical unobserved receipts'};
}
export function syntheticCapitalExample() {
    const spec = {capabilities: ['F', 'C', 'S'], recipes: [
        {id: 'factory', requires: [], produces: ['F'], cost: 12},
        {id: 'convolution-from-factory', requires: ['F'], produces: ['C'], cost: 3},
        {id: 'solver-from-factory', requires: ['F'], produces: ['S'], cost: 4},
        {id: 'standalone-convolution', requires: [], produces: ['C'], cost: 20},
        {id: 'standalone-solver', requires: [], produces: ['S'], cost: 20}]};
    const a = {id: 'a', kappa: 2, delta: 8, stock: []}, b = {id: 'b', kappa: 5, delta: 4, stock: ['F']};
    const normal = [{id: 'research', cashChange: 7, reserveChange: 0},
        {id: 'factory', cashChange: -12, reserveChange: 0}, {id: 'accepted-output', cashChange: 9, reserveChange: 0}];
    const reserved = [{id: 'research-refundable', cashChange: 7, reserveChange: 7},
        {id: 'factory', cashChange: -12, reserveChange: 0},
        {id: 'accepted-release', cashChange: 9, reserveChange: -7}];
    return {schema: 'autonomous-enterprises-capital-example/v1', spec, producers: [a, b],
        targets: [[['F'], 9], [['C'], 6]].map(([target, cash]) => ({target, terminalCash: cash,
            full: portfolioCapital(spec, [a, b], target, cash), cashOnly: portfolioCapital(spec, [a], target, cash)})),
        retention: retentionLaw(spec, [a, b], ['a']),
        traces: {a: profileFromTrace([{id: 'work', cashChange: -2, reserveChange: 0},
            {id: 'accepted-output', cashChange: 10, reserveChange: 0}]), b: profileFromTrace(normal),
        bRefundable: profileFromTrace(reserved)},
        authority: 'SIMULATED; no customers, collected money, transactions, reserved funds or reusable revenue recipe'};
}
export function capitalControls() {
    const bulk = {capabilities: ['a', 'b', 'c'], recipes: [
        ...['a', 'b', 'c'].map(n => ({id: `buy-${n}`, requires: [], produces: [n], cost: 2})),
        {id: 'buy-ab', requires: [], produces: ['a', 'b'], cost: 2},
        {id: 'buy-bc', requires: [], produces: ['b', 'c'], cost: 2}]};
    const values = [['a', 'b'], ['b', 'c'], ['b'], ['a', 'b', 'c']].map(q => completion(bulk, [], q).cost);
    const invalidMap = [[0, 1, 4], [3, 0, 1], [3, 3, 0]];
    const L = 0, K = 1, Q = 2;
    const pairwiseExpression = Math.max(0, invalidMap[L][K]);
    const actualLoss = invalidMap[L][Q] - Math.min(invalidMap[K][Q], invalidMap[L][Q]);
    return {nonsubmodular: {spec: bulk, values, left: values[0] + values[1], right: values[2] + values[3],
        violatesSubmodularity: values[0] + values[1] < values[2] + values[3], geometry: completionTable(bulk).geometry},
        triangleViolation: {matrix: invalidMap, assessment: qualifyCompletionMap(invalidMap),
            producers: [{id: 'K', kappa: 0, delta: 0, stockIndex: 1}, {id: 'L', kappa: 0, delta: 0, stockIndex: 0}],
            retained: ['L'], targetIndex: Q, terminalCash: 0, pairwiseExpression, actualLoss,
            universalLawInvalid: actualLoss > pairwiseExpression},
        vector: resourceWitness([{id: 'path-one', steps: [[0, 5]]}, {id: 'path-two', steps: [[5, 0]]}], [1, 1])};
}

/** Public deterministic protocol cases; no manuscript-companion or protected-holdout reproduction claim. */
export function runCapitalConfirmation(options = {}) {
    const input = own(options);
    need(input && !Array.isArray(input) && Object.keys(input).every(k => ['cases', 'seed'].includes(k)), 'Unknown confirmation option.');
    const cases = input.cases ?? 24, seed = input.seed ?? 20261021;
    need(integer(cases, 1, 72) && integer(seed, 0, 0xffffffff), 'One to 72 cases and a 32-bit public seed required.');
    let state = seed >>> 0;
    const draw = n => { state = (Math.imul(1664525, state) + 1013904223) >>> 0; return state % n; };
    const reports = []; let completionValues = 0, capitalTargets = 0, triangleTriples = 0;
    for (let i = 0; i < cases; i++) {
        const m = 3 + i % 3, names = Array.from({length: m}, (_, j) => `K${j}`), stock = bits => names.filter((_, j) => bits & (1 << j));
        const recipes = names.map(n => ({id: `standalone-${n}`, requires: [], produces: [n], cost: 2 + draw(13)}));
        for (let j = 0; j < m + 3; j++) {
            const requires = names.filter(() => draw(100) < 30), produces = names.filter(() => draw(100) < 38);
            if (!produces.length) produces.push(names[draw(m)]);
            recipes.push({id: `extra-${j}`, requires, produces, cost: draw(11)});
        }
        const spec = {capabilities: names, recipes}, table = completionTable(spec);
        need(table.status === 'COMPLETE' && table.geometry.status === 'QUALIFIED_FINITE', 'Generated recipe geometry failed.');
        completionValues += table.valuesChecked; triangleTriples += table.geometry.triplesChecked;
        const family = Array.from({length: 3 + i % 4}, (_, j) => {
            const kappa = draw(11); return {id: `p${j}`, kappa, delta: draw(kappa + 15) - kappa, stock: stock(draw(1 << m))};
        });
        const retained = family.filter(() => draw(2)).map(p => p.id); if (!retained.length) retained.push(family[0].id);
        const cert = retentionLaw(spec, family, retained);
        need(cert.status === 'FINITE', 'Complete fallback catalogue should have finite loss.');
        const fullRows = family.map(p => ({...p, bits: names.reduce((b, n, j) => b | (p.stock.includes(n) ? 1 << j : 0), 0)}));
        const kept = fullRows.filter(p => retained.includes(p.id));
        const xmax = 1 + Math.max(...family.map(p => p.kappa)) + Math.max(...family.map(p => p.delta));
        let scannedLoss = 0;
        for (let q = 0; q < 1 << m; q++) for (let x = 0; x <= xmax; x++) {
            const value = rows => Math.min(...rows.map(p => Math.max(p.kappa, x - p.delta + table.matrix[p.bits][q])));
            scannedLoss = Math.max(scannedLoss, value(kept) - value(fullRows)); capitalTargets++;
        }
        need(scannedLoss === cert.loss, 'Direct target scan disagrees with retention law.');
        for (let k = 0; k < 1 << m; k++) for (let l = 0; l < 1 << m; l++) if (contains(l, k)) {
            for (let q = 0; q < 1 << m; q++) need(table.matrix[l][q] <= table.matrix[k][q], 'Optionality failed.');
        }
        reports.push({case: i, spec, family, retained, completion: table.matrix,
            valuesChecked: table.valuesChecked, scannedLoss, certificate: cert, cashScanMaximum: xmax});
    }
    return {schema: 'autonomous-enterprises-capital-confirmation/v1', source: 'independent reimplementation',
        generator: 'LCG-1664525-1013904223; intentionally different from unavailable companion', seed, cases,
        counts: {catalogues: cases, completionValues, capitalTargets, triangleTriples}, reports,
        scope: 'Small finite synthetic integer models; exact stock enumeration is exponential; public seeded protocol cases.'};
}
