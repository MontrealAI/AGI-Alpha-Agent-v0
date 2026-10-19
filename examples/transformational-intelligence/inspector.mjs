// SPDX-License-Identifier: Apache-2.0
/** Native-compatible inert inspection. This module never grants authority or executes imports. */
import {canonical, digest, parseBounded} from '../../docs/assets/successor/engine.mjs';

export const VERSION = 'transformational-intelligence/v1';
export function assertPublicContent(value) {
    const sensitive = new Set(['apikey', 'privatekey', 'accesstoken', 'refreshtoken', 'clientsecret', 'password', 'passphrase', 'mnemonic', 'seedphrase', 'secret', 'authorization']);
    const pattern = /(?:api[_ -]?key|private[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passphrase|client[_ -]?secret|secret|mnemonic|seed[_ -]?phrase|authorization)["' ]*\s*[:=]\s*["']?[^\s"'},]+|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,})/i;
    const decode = text => {
        for (let i = 0; i < 3; i++) {
            const decoded = text.replace(/\\u([0-9a-f]{4})/gi, (_, code) => String.fromCharCode(parseInt(code, 16)))
                .replace(/(?:%[0-9a-f]{2})+/gi, part => { try { return decodeURIComponent(part); } catch { return part; } });
            if (decoded === text) break;
            text = decoded;
        }
        return text;
    };
    const pending = [[value, 0]]; let nodes = 0;
    while (pending.length) {
        const [item, depth] = pending.pop();
        if (++nodes > 100000 || depth > 32) throw Error('Public input exceeds its structural budget');
        if (Array.isArray(item)) item.forEach(child => pending.push([child, depth + 1]));
        else if (item && typeof item === 'object') for (const [key, child] of Object.entries(item)) {
            if (sensitive.has(decode(key).toLowerCase().replace(/[^a-z0-9]/g, '')) && typeof child === 'string' && child.trim()) throw Error('Public-only input contains a credential-shaped field; remove it before continuing');
            pending.push([child, depth + 1]);
        } else if (typeof item === 'string') {
            const decoded = decode(item);
            if (pattern.test(decoded)) throw Error('Public-only input contains credential-shaped text; remove it before continuing');
            if (/^[\s]*[\[{\"]/.test(decoded)) {
                try { pending.push([parseBounded(decoded), depth + 1]); } catch { /* Malformed embedded data remains inert. */ }
            }
        }
    }
}
const fail = message => { throw Error(message); };
const exact = (v, fields) => v && typeof v === 'object' && !Array.isArray(v)
    && Object.keys(v).sort().join('|') === [...fields].sort().join('|');
const equal = (a, b) => canonical(a) === canonical(b);
const text = (v, n = 2000) => typeof v === 'string' && v.length > 0 && Array.from(v).length <= n;
const integer = (v, lo, hi) => Number.isSafeInteger(v) && !Object.is(v, -0) && v >= lo && v <= hi;
const hash = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const array = (v, lo = 0, hi = 20) => Array.isArray(v) && v.length >= lo && v.length <= hi;
const list = (v, lo = 0, hi = 20) => array(v, lo, hi) && v.every(x => text(x));
const version = v => v.schema_version === 1;
const program = p => exact(p, ['schema_version', 'schema', 'representation', 'production']) && version(p)
    && p.schema === 'selection-program/v1' && ['sequence', 'argument-graph'].includes(p.representation)
    && ['lead', 'weighted', 'audit-after', 'closure-search'].includes(p.production);

function charter(c) {
    if (!exact(c, ['schema_version', 'schema', 'purpose', 'population', 'outcomes', 'constraints', 'permitted_actions',
        'publicOnly', 'budgets', 'payment_route', 'artifact', 'max_clauses']) || !version(c)
        || c.schema !== 'intent-charter/v1' || !text(c.purpose) || !text(c.population, 500)
        || !list(c.outcomes, 1, 12) || !list(c.constraints, 1, 20) || c.publicOnly !== true
        || !array(c.permitted_actions, 0, 4) || new Set(c.permitted_actions).size !== c.permitted_actions.length
        || c.permitted_actions.some(a => !['read-public-source', 'construct-bounded', 'evaluate-local', 'write-artifact'].includes(a))
        || !['none', 'USDC', 'AGIALPHA'].includes(c.payment_route) || c.artifact !== 'fixed-summary'
        || !integer(c.max_clauses, 1, 12)) fail('Invalid intent charter or unauthorized purpose expansion');
    const b = c.budgets;
    if (!exact(b, ['schema_version', 'search_units', 'execution_units', 'money_minor', 'USDCBaseUnits', 'AGIALPHABaseUnits'])
        || !version(b) || !integer(b.search_units, 0, 1000000) || !integer(b.execution_units, 0, 1000000)
        || b.money_minor !== 0 || b.USDCBaseUnits !== '0' || b.AGIALPHABaseUnits !== '0') {
        fail('Version one is a free bounded comparison; currency allowances cannot be inferred');
    }
}

function formulation(f) {
    if (!exact(f, ['schema_version', 'schema', 'representation', 'assumptions', 'information_protocol', 'policy_language',
        'intermediate_objectives']) || !version(f) || f.schema !== 'formulation/v1'
        || !text(f.representation) || !text(f.information_protocol) || f.policy_language !== 'source-clause-selector/v1'
        || !list(f.intermediate_objectives, 1, 20) || !array(f.assumptions, 1, 32)) fail('Invalid formulation');
    for (const a of f.assumptions) {
        if (!exact(a, ['schema_version', 'name', 'kind', 'statement', 'provenance', 'removable']) || !version(a)
            || !text(a.name, 200) || !text(a.statement) || !text(a.provenance) || typeof a.removable !== 'boolean'
            || !['authorized-end', 'hard-constraint', 'environmental-fact', 'uncertain-hypothesis', 'inherited-design'].includes(a.kind)
            || a.removable && ['authorized-end', 'hard-constraint', 'environmental-fact'].includes(a.kind)) fail('Invalid typed assumption');
    }
}

function source(d) {
    if (!exact(d, ['schema_version', 'schema', 'title', 'source_url', 'public_non_personal', 'claims']) || !version(d)
        || d.schema !== 'source-document/v1' || !text(d.title, 500) || !text(d.source_url)
        || d.public_non_personal !== true || !array(d.claims, 1, 12)) fail('Invalid public source document');
    const url = new URL(d.source_url);
    if (url.protocol !== 'https:' || !url.hostname || url.username || url.password || url.hash) fail('Invalid public source provenance');
    const names = new Set(d.claims.map(c => c.id));
    if (names.size !== d.claims.length) fail('Duplicate source claim identity');
    const dependencies = new Map();
    for (const c of d.claims) {
        if (!exact(c, ['schema_version', 'id', 'text', 'weight', 'depends_on', 'provenance']) || !version(c)
            || !/^[A-Za-z0-9_-]{1,40}$/.test(c.id) || !text(c.text, 1500) || !text(c.provenance)
            || !integer(c.weight, 1, 1000) || !array(c.depends_on, 0, 12)
            || new Set(c.depends_on).size !== c.depends_on.length
            || c.depends_on.some(x => !names.has(x) || x === c.id)) fail('Invalid argument dependencies');
        dependencies.set(c.id, new Set(c.depends_on));
    }
    while (dependencies.size) {
        const roots = [...dependencies].filter(([, edges]) => !edges.size).map(([name]) => name);
        if (!roots.length) fail('Cyclic source dependencies');
        for (const root of roots) dependencies.delete(root);
        for (const edges of dependencies.values()) for (const root of roots) edges.delete(root);
    }
}

function instrument(e) {
    const expected = {
        schema: 'evaluation-instrument/v1', name: 'declared-dependency-coverage/v1',
        measurement: 'weight of selected exact clauses whose prerequisite closure is present, in millionths',
        domain: 'supplied acyclic argument representations with at most twelve clauses',
        calibration: {status: 'missing', human_understanding_bound: null},
        authoritative_claim: 'structural coverage only; source truth and reader understanding unestablished',
        hard_requirements: ['exact source clauses', 'fixed clause count', 'no omitted prerequisite for counted value'],
    };
    if (!equal(e, expected)) fail('Imported evaluator is not the supported structural instrument');
}

function transformation(t, c, f) {
    if (!exact(t, ['schema_version', 'schema', 'formulation', 'construction', 'realization', 'witness', 'axes'])
        || !version(t) || t.schema !== 'transformation-package/v1' || !equal(t.formulation, f)
        || !program(t.construction) || t.realization !== 'exact-source-clauses/v1'
        || !list(t.axes, 1, 7) || t.axes.some(a => !['representation', 'information', 'dependency', 'production', 'task-boundary', 'mechanism', 'evaluation'].includes(a))) {
        fail('Invalid executable transformation package');
    }
    const w = t.witness;
    if (!exact(w, ['schema_version', 'purpose', 'inherited_restriction', 'provenance', 'proposed_change', 'prerequisites',
        'fallback', 'outcome_bridge', 'falsifier', 'strong_comparisons', 'frozen_confirmation_evidence',
        'reuse_conditions', 'failure_cases', 'retirement_triggers']) || !version(w) || w.purpose !== c.purpose) fail('Missing purpose-grounded witness');
    for (const k of ['purpose', 'inherited_restriction', 'provenance', 'proposed_change', 'fallback', 'falsifier']) {
        if (!text(w[k], 4000)) fail('Missing witness rationale');
    }
    for (const k of ['prerequisites', 'strong_comparisons', 'reuse_conditions', 'failure_cases', 'retirement_triggers']) {
        if (!list(w[k], 1, 32)) fail('Missing witness evidence scope or failure conditions');
    }
    if (!w.outcome_bridge || typeof w.outcome_bridge !== 'object' || !w.frozen_confirmation_evidence
        || typeof w.frozen_confirmation_evidence !== 'object') fail('Missing bridge or freeze process evidence');
}

const comparators = () => Object.fromEntries([
    ['lead-order', 'sequence', 'lead'], ['audit-after-draft', 'sequence', 'audit-after'],
    ['weighted-without-dependencies', 'sequence', 'weighted'], ['unrestricted-exact-search', 'argument-graph', 'closure-search'],
].map(([name, representation, production]) => [name, {schema_version: 1, schema: 'selection-program/v1', representation, production}]));

function closure(d, selected) {
    const result = new Set(selected), pending = [...selected], claims = new Map(d.claims.map(c => [c.id, c]));
    while (pending.length) for (const dependency of claims.get(pending.pop()).depends_on) {
        if (!result.has(dependency)) { result.add(dependency); pending.push(dependency); }
    }
    return result;
}

function select(d, p, limit, charge) {
    charge(d.claims.length);
    if (p.production === 'lead') return d.claims.slice(0, limit).map(c => c.id);
    const weighted = [...d.claims].sort((a, b) => b.weight - a.weight || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    if (p.production === 'weighted' || p.production === 'closure-search' && p.representation === 'sequence') return weighted.slice(0, limit).map(c => c.id);
    if (p.production === 'audit-after') {
        let chosen = new Set(d.claims.slice(0, limit).map(c => c.id));
        for (const claim of [...d.claims].sort((a, b) => a.weight - b.weight || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))) {
            charge(1); if (closure(d, chosen).size <= limit) break; chosen.delete(claim.id);
        }
        chosen = closure(d, chosen);
        return d.claims.filter(c => chosen.has(c.id)).map(c => c.id);
    }
    let best = {weight: -1, names: []};
    const consider = subset => {
        charge(1);
        const names = subset.map(c => c.id), chosen = new Set(names);
        if ([...closure(d, chosen)].some(x => !chosen.has(x))) return;
        const weight = subset.reduce((sum, c) => sum + c.weight, 0);
        if (weight > best.weight || weight === best.weight && (names.length < best.names.length
            || names.length === best.names.length && names.join('\0') < best.names.join('\0'))) best = {weight, names};
    };
    const combinations = (start, count, subset) => {
        if (count === 0) { consider(subset); return; }
        for (let i = start; i <= d.claims.length - count; i++) combinations(i + 1, count - 1, [...subset, d.claims[i]]);
    };
    for (let n = 0; n <= Math.min(limit, d.claims.length); n++) combinations(0, n, []);
    return best.names;
}

async function execute(d, p, c, charge) {
    const selected = select(d, p, c.max_clauses, charge), chosen = new Set(selected);
    const supported = d.claims.filter(claim => chosen.has(claim.id) && [...closure(d, [claim.id])].every(x => chosen.has(x))).map(c => c.id);
    const covered = d.claims.filter(c => supported.includes(c.id)).reduce((sum, c) => sum + c.weight, 0);
    const total = d.claims.reduce((sum, c) => sum + c.weight, 0);
    return {score_millionths: Math.floor(covered * 1000000 / total), covered_weight: covered, total_weight: total,
        supported_claims: supported, unsupported_claims: [...chosen].filter(x => !supported.includes(x)).sort(), selected,
        text: d.claims.filter(c => chosen.has(c.id)).map(c => c.text).join('\n'),
        references: d.claims.filter(c => chosen.has(c.id)).map(c => ({id: c.id, provenance: c.provenance})),
        program_digest: await digest('ti-program', p), source_digest: await digest('ti-source', d)};
}

async function terminal(r, p, fresh) {
    const controls = comparators(), results = Object.fromEntries(['candidate', ...Object.keys(controls)].map(n => [n, []]));
    let spent = 0, failure = null;
    const charge = units => {
        if (spent + units > r.charter.budgets.execution_units) throw Error('TI budget exhausted');
        spent += units;
    };
    try {
        for (const d of fresh) {
            results.candidate.push(await execute(d, p, r.charter, charge));
            for (const [name, control] of Object.entries(controls)) results[name].push(await execute(d, control, r.charter, charge));
        }
    } catch (e) {
        if (e.message !== 'TI budget exhausted') throw e;
        failure = 'terminal budget exhausted; incomplete evidence cannot support promotion';
    }
    const means = Object.fromEntries(Object.entries(results).map(([name, items]) => [name, items.length !== fresh.length ? null : Math.floor(items.reduce((sum, i) => sum + i.score_millionths, 0) / fresh.length)]));
    const gain = means.candidate === null || means['lead-order'] === null ? null : means.candidate - means['lead-order'];
    return {decision: failure || gain === null || gain <= 0 ? 'retain-incumbent' : 'propose-reuse-pending-independent-review', failure,
        results, means_millionths: means, observed_gain_vs_incumbent: gain,
        beats_unrestricted: means.candidate === null || means['unrestricted-exact-search'] === null ? null : means.candidate > means['unrestricted-exact-search'], execution_units: spent};
}

export async function inspectTransformationEnvelope(raw) {
    const e = typeof raw === 'string' ? parseBounded(raw) : parseBounded(canonical(raw));
    assertPublicContent(e);
    const fields = ['schema', 'campaign_id', 'revision', 'charter', 'charter_digest', 'formulation', 'formulation_digest',
        'evaluation', 'transformation', 'transformation_digest', 'bindings', 'bindings_digest', 'phase', 'authorization',
        'execution', 'review', 'settlement', 'freeze', 'result'];
    if (!exact(e, fields) && !exact(e, [...fields, 'elapsed_ms'])) fail('Unsupported transformation envelope fields');
    if (e.schema !== VERSION || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(e.campaign_id)
        || !integer(e.revision, 0, Number.MAX_SAFE_INTEGER)) fail('Invalid campaign identity or schema');
    charter(e.charter); formulation(e.formulation); transformation(e.transformation, e.charter, e.formulation);
    for (const [key, domain] of [['charter', 'ti-charter'], ['formulation', 'ti-formulation'],
        ['transformation', 'ti-transformation'], ['bindings', 'ti-bindings']]) {
        if (!hash(e[key + '_digest']) || await digest(domain, e[key]) !== e[key + '_digest']) fail('Changed committed ' + key);
    }
    const v = e.evaluation, b = e.bindings;
    if (!exact(v, ['instrument', 'instrument_digest', 'epoch', 'status']) || v.epoch !== 1
        || v.status !== 'local_structural_only' || await digest('ti-instrument', v.instrument) !== v.instrument_digest) fail('Invalid evaluator commitment or claimed authority');
    instrument(v.instrument);
    if (!exact(b, ['request', 'operators', 'instrument', 'engine_sha256', 'provider']) || !equal(b.instrument, v.instrument)
        || !hash(b.engine_sha256) || !equal(b.provider, {kind: 'deterministic-installed-operators', model: 'none', paid_calls: 0})) fail('Incomplete frozen behavior');
    const r = b.request;
    if (!exact(r, ['schema_version', 'campaign_id', 'charter', 'development', 'operator_ids', 'max_candidates', 'configuration'])
        || !version(r) || r.campaign_id !== e.campaign_id || !equal(r.charter, e.charter) || !array(r.development, 1, 8)
        || !list(r.operator_ids, 0, 32) || new Set(r.operator_ids).size !== r.operator_ids.length
        || !integer(r.max_candidates, 1, 32) || !equal(Object.keys(b.operators).sort(), [...r.operator_ids].sort())
        || Object.values(b.operators).some(x => !hash(x)) || !r.configuration || typeof r.configuration !== 'object'
        || Array.isArray(r.configuration) || Object.keys(r.configuration).length > 20
        || Object.entries(r.configuration).some(([k, v]) => k.length > 80 || typeof v !== 'string' || v.length > 500)) fail('Frozen request changed comparison basis');
    r.development.forEach(source);
    if (!equal(e.authorization, {scope: 'local-bounded', binding: null, authority_expansion: false})
        || !equal(e.execution, {status: 'inert-export', artifacts: []}) || !equal(e.review, {status: 'pending', independent: false})
        || !equal(e.settlement, {route: e.charter.payment_route, status: 'unfunded', transaction_prepared: false})) fail('Imported history cannot confer execution, review or settlement authority');
    if (!['queued', 'diagnosed', 'developed', 'frozen', 'completed', 'paused', 'canceled'].includes(e.phase)) fail('Unsupported discovery phase');
    if (e.phase === 'frozen' && e.freeze === null || e.phase === 'completed' && e.result === null) fail('Required terminal or frozen evidence is missing');
    if (e.freeze !== null && !['frozen', 'completed', 'paused', 'canceled'].includes(e.phase)) fail('Finalist evidence cannot precede discovery');
    if (e.freeze !== null) {
        const f = e.freeze;
        if (!exact(f, ['manifest', 'digest', 'journal_predecessor', 'journal_revision'])
            || await digest('ti-finalist-freeze', f.manifest) !== f.digest
            || f.manifest.binding !== e.bindings_digest || !equal(f.manifest.package, e.transformation)
            || !hash(f.journal_predecessor) || !integer(f.journal_revision, 1, e.revision - 1)) fail('Altered frozen finalist');
        const m = f.manifest;
        if (!exact(m, ['binding', 'selected', 'package', 'comparators', 'instrument', 'confirmation', 'claim'])
            || !equal(m.comparators, comparators()) || !equal(m.instrument, v.instrument)
            || !equal(m.selected.program, e.transformation.construction)
            || m.selected.program_digest !== await digest('ti-program', e.transformation.construction)) fail('Changed strong comparisons or executable finalist');
    }
    if (e.result !== null && e.freeze === null) {
        if (e.phase !== 'completed' || !equal(e.result, {decision: 'retain-incumbent', reason: 'no feasible candidate within budget'})) fail('Missing frozen confirmation cannot support improvement');
        return e;
    }
    if (e.result !== null) {
        const result = e.result;
        if (e.phase !== 'completed' || result.freeze_digest !== e.freeze.digest || result.independent_review !== 'pending'
            || result.certified_ceiling_escape !== false || result.reader_understanding !== 'uncalibrated'
            || !array(result.fresh_sources, 1, 8)) fail('Unbound result evidence or unsupported outcome claim');
        result.fresh_sources.forEach(source);
        const seen = new Set(r.development.flatMap(d => d.claims.map(c => c.text)));
        for (const document of result.fresh_sources) {
            const clauses = document.claims.map(c => c.text);
            if (clauses.some(c => seen.has(c))) fail('Reused source clause content');
            clauses.forEach(c => seen.add(c));
        }
        const expected = await terminal(r, e.transformation.construction, result.fresh_sources);
        for (const name of ['decision', 'failure', 'results', 'means_millionths', 'observed_gain_vs_incumbent', 'beats_unrestricted']) {
            if (!Object.hasOwn(result, name) || !equal(result[name], expected[name])) fail('Terminal comparison or structural score cannot be reproduced');
        }
        if (result.costs.execution_units !== expected.execution_units) fail('Terminal costs cannot be reproduced');
        const costs = result.costs;
        if (!exact(costs, ['search_units', 'execution_units', 'paid_calls', 'money_minor', 'human_effort', 'maintenance', 'reuse_horizon'])
            || !integer(costs.search_units, 0, e.charter.budgets.search_units)
            || costs.paid_calls !== 0 || costs.money_minor !== 0 || costs.human_effort !== 'not measured'
            || costs.maintenance !== 'not measured' || costs.reuse_horizon !== 'undeclared; economic break-even not established') fail('Unsupported lifecycle cost or economic claim');
    }
    return e;
}
