// SPDX-License-Identifier: Apache-2.0
/** Fixed, bounded aggregation engines. No generated JavaScript is executed. */
export const VERSION = 'successor-browser-v1';
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === [...keys].sort().join('|');
const integer = (value, low, high) => Number.isSafeInteger(value) && value >= low && value <= high;
function scalar(value) {
    if (typeof value !== 'string') return false;
    for (let i = 0; i < value.length; i++) {
        const c = value.charCodeAt(i);
        if (c >= 0xd800 && c <= 0xdbff) {
            const next = value.charCodeAt(++i);
            if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
        } else if (c >= 0xdc00 && c <= 0xdfff) return false;
    }
    return true;
}
export function canonical(value) {
    let nodes = 0;
    function encode(item, depth = 0) {
        if (++nodes > 100000 || depth > 32) throw Error('JSON complexity exceeds limit');
        if (item === null || typeof item === 'boolean') return JSON.stringify(item);
        if (typeof item === 'string' && scalar(item)) return JSON.stringify(item);
        if (typeof item === 'number' && Number.isSafeInteger(item) && !Object.is(item, -0)) return String(item);
        if (Array.isArray(item)) {
            for (let i = 0; i < item.length; i++) if (!Object.hasOwn(item, i)) throw Error('Sparse arrays are not JSON');
            return '[' + item.map(v => encode(v, depth + 1)).join(',') + ']';
        }
        if (item && typeof item === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(item))) {
            return '{' + Object.keys(item).sort().map(key => {
                if (!/^[\x20-\x7e]+$/.test(key)) throw Error('Object keys must be printable ASCII');
                return JSON.stringify(key) + ':' + encode(item[key], depth + 1);
            }).join(',') + '}';
        }
        throw Error('Unsupported JSON value; integers and Unicode scalars required');
    }
    const result = encode(value);
    if (new TextEncoder().encode(result).length > 2000000) throw Error('Canonical JSON exceeds 2 MB');
    return result;
}
export async function digest(domain, value) {
    if (!/^[a-z][a-z0-9-]{0,63}$/.test(domain)) throw Error('Invalid digest domain');
    const bytes = new TextEncoder().encode('successor-omega/v1:' + domain + '\0' + canonical(value));
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
}
/** Parse untrusted imports before they can allocate large or deeply nested objects. */
export function parseBounded(text) {
    if (typeof text !== 'string' || new TextEncoder().encode(text).length > 2_000_000) throw Error('Import exceeds 2 MB');
    let pos = 0, nodes = 0;
    const ws = () => { while (/[\x20\t\n\r]/.test(text[pos] || '\u0000')) pos++; };
    const string = () => {
        const start = pos++;
        while (pos < text.length) {
            if (text[pos] === '\\') { pos += 2; continue; }
            if (text[pos++] === '"') {
                const value = JSON.parse(text.slice(start, pos));
                if (!scalar(value)) throw Error('Malformed Unicode');
                return value;
            }
        }
        throw Error('Unterminated string');
    };
    function read(depth = 0) {
        if (++nodes > 100000 || depth > 32) throw Error('Import complexity exceeds limit');
        ws();
        if (text[pos] === '"') return string();
        if (text[pos] === '[' || text[pos] === '{') {
            const object = text[pos++] === '{', end = object ? '}' : ']';
            const value = object ? Object.create(null) : [];
            ws(); if (text[pos] === end) { pos++; return value; }
            while (true) {
                ws();
                if (object) {
                    if (text[pos] !== '"') throw Error('Expected object key');
                    const key = string(); ws();
                    if (Object.hasOwn(value, key)) throw Error('Duplicate JSON key');
                    if (text[pos++] !== ':') throw Error('Expected colon');
                    value[key] = read(depth + 1);
                } else value.push(read(depth + 1));
                ws(); const next = text[pos++];
                if (next === end) break;
                if (next !== ',') throw Error('Expected comma');
            }
            return value;
        }
        for (const [token, value] of [['true', true], ['false', false], ['null', null]]) {
            if (text.startsWith(token, pos)) { pos += token.length; return value; }
        }
        const match = /^-?(?:0|[1-9]\d*)(?![\d.eE+-])/.exec(text.slice(pos));
        if (!match) throw Error('Expected integer JSON value');
        pos += match[0].length; const value = Number(match[0]);
        if (!Number.isSafeInteger(value) || Object.is(value, -0)) throw Error('Unsafe integer');
        return value;
    }
    const value = read(); ws();
    if (pos !== text.length) throw Error('Trailing JSON content');
    canonical(value);
    return value;
}
export function validateRequest(request) {
    const keys = ['schema_version', 'kind', 'request_id', 'mission', 'seed', 'max_candidates', 'formation_trials', 'max_events', 'language'];
    if (!request || typeof request !== 'object' || Array.isArray(request) || !Object.hasOwn(request, 'request_id') || Object.keys(request).some(key => !keys.includes(key))) throw Error('Invalid versioned rehearsal request');
    request = {schema_version: 1, kind: 'successor-rehearsal', mission: 'streaming-metrics-v1', seed: 42, max_candidates: 4, formation_trials: 2, max_events: 1000, language: 'en', ...request};
    if (!exact(request, keys) || request.schema_version !== 1 || request.kind !== 'successor-rehearsal' || request.mission !== 'streaming-metrics-v1' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(request.request_id) || !integer(request.seed, 0, 4294967295) || !integer(request.max_candidates, 2, 12) || !integer(request.formation_trials, 1, 6) || !integer(request.max_events, 64, 20000) || !['en', 'fr'].includes(request.language)) throw Error('Invalid versioned rehearsal request');
    return structuredClone(request);
}
export function newRequest(options = {}) {
    return validateRequest({schema_version: 1, kind: 'successor-rehearsal', request_id: crypto.randomUUID(), mission: 'streaming-metrics-v1', seed: 42, max_candidates: 4, formation_trials: 2, max_events: 1000, language: 'en', ...options});
}
function order(a, b) {
    const aa = Array.from(a, c => c.codePointAt(0)), bb = Array.from(b, c => c.codePointAt(0));
    for (let i = 0; i < Math.min(aa.length, bb.length); i++) if (aa[i] !== bb[i]) return aa[i] - bb[i];
    return aa.length - bb.length;
}
const rowOrder = (a, b) => order(a.day, b.day) || order(a.service, b.service);
export function validateEvents(events) {
    if (!Array.isArray(events) || events.length > 20000) throw Error('Event count exceeds mission bound');
    for (const e of events) {
        if (!exact(e, ['day', 'service', 'duration_us', 'ok']) || !scalar(e.day) || !scalar(e.service) || !integer(Array.from(e.day).length, 1, 64) || !integer(Array.from(e.service).length, 1, 64) || !integer(e.duration_us, 0, 1000000000) || typeof e.ok !== 'boolean') throw Error('Malformed aggregation event');
    }
}
const makeRow = e => ({day: e.day, service: e.service, count: 0, total_duration_us: 0, max_duration_us: 0, error_count: 0});
function update(row, e, kind = 'builtin') {
    row.count++; row.total_duration_us += e.duration_us; row.error_count += Number(!e.ok);
    if (kind === 'builtin') row.max_duration_us = Math.max(row.max_duration_us, e.duration_us);
    else if (e.duration_us > row.max_duration_us) row.max_duration_us = e.duration_us;
}
export function current(events) {
    validateEvents(events); const groups = new Map();
    for (const e of events) {
        const key = JSON.stringify([e.day, e.service]);
        if (!groups.has(key)) groups.set(key, makeRow(e));
        update(groups.get(key), e);
    }
    return [...groups.values()].sort(rowOrder);
}
export function beta(events) {
    validateEvents(events); const sorted = [...events].sort(rowOrder), rows = [];
    for (const e of sorted) {
        let row = rows[rows.length - 1];
        if (!row || row.day !== e.day || row.service !== e.service) { row = makeRow(e); rows.push(row); }
        row.count += 1; row.total_duration_us += e.duration_us;
        row.error_count += e.ok ? 0 : 1;
        row.max_duration_us = row.max_duration_us >= e.duration_us ? row.max_duration_us : e.duration_us;
    }
    return rows;
}
export function validateCandidate(c) {
    if (!exact(c, ['version', 'layout', 'cache_last', 'update']) || c.version !== 1 || !['nested', 'tuple'].includes(c.layout) || typeof c.cache_last !== 'boolean' || !['branch', 'builtin'].includes(c.update)) throw Error('Candidate is outside the fixed grammar');
    return c;
}
export function candidate(events, config) {
    validateEvents(events); validateCandidate(config);
    const groups = new Map(), rows = []; let last = null;
    for (const e of events) {
        let row;
        if (config.cache_last && last && e.day === last.day && e.service === last.service) row = last;
        else if (config.layout === 'nested') {
            if (!groups.has(e.day)) groups.set(e.day, new Map());
            const services = groups.get(e.day);
            row = services.get(e.service);
            if (!row) { row = makeRow(e); services.set(e.service, row); rows.push(row); }
        } else {
            const key = JSON.stringify([e.day, e.service]); row = groups.get(key);
            if (!row) { row = makeRow(e); groups.set(key, row); rows.push(row); }
        }
        update(row, e, config.update); last = row;
    }
    return rows.sort(rowOrder);
}
export function generateCandidates(seed, count) {
    if (!integer(count, 2, 12)) throw Error('Candidate count outside bound');
    const out = [];
    // Eight complete compositions; repeated configuration is never represented as a new challenger.
    for (let i = 0; i < Math.min(count, 8); i++) {
        const bits = (i + (seed % 8)) % 8;
        out.push({version: 1, layout: bits & 1 ? 'nested' : 'tuple', cache_last: Boolean(bits & 2), update: bits & 4 ? 'branch' : 'builtin'});
    }
    return out;
}
export function workload(seed, count, mode = 'mixed') {
    let state = seed >>> 0;
    const next = () => (state = (Math.imul(state, 1664525) + 1013904223) >>> 0);
    const names = ['api', 'résumé', '東京', '🙂', '__proto__', '\ue000', '𝄞'];
    return Array.from({length: count}, (_, i) => ({day: 'day-' + (next() % (mode === 'high' ? 97 : 3)), service: mode === 'high' ? names[next() % names.length] + i : names[next() % names.length], duration_us: next() % 1000000001, ok: next() % 5 !== 0}));
}
const pause = () => new Promise(resolve => setTimeout(resolve, 0));
function measured(fn, events) {
    const start = performance.now(); const result = fn(events);
    return {elapsed_ns: Math.max(1, Math.round((performance.now() - start) * 1000000)), rows: result.length, result};
}
function correct(fn) {
    const valid = [[], [{day: '🙂', service: '__proto__', duration_us: 1000000000, ok: false}], workload(12, 64, 'high'), workload(98, 120)];
    if (!valid.every(events => canonical(fn(events)) === canonical(beta(events)))) return false;
    const bad = [[{day: '', service: 'x', duration_us: 1, ok: true}], [{day: 'd', service: 'x', duration_us: true, ok: true}], [{day: 'd', service: 'x', duration_us: 1, ok: 'true'}], [{day: 'd', service: '\ud800', duration_us: 1, ok: true}], [{day: 'd', service: 'x', duration_us: -1, ok: true}]];
    return bad.every(events => { try { fn(events); return false; } catch { return true; } });
}
function abort(signal) { if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError'); }
export async function discover(request, {signal, onProgress = () => {}, preferred = null} = {}) {
    request = validateRequest(request); const configurations = generateCandidates(request.seed, request.max_candidates);
    configurations.sort((a, b) => Number(b.layout === 'nested') - Number(a.layout === 'nested'));
    if (preferred) { validateCandidate(preferred); configurations.sort((a, b) => Number(canonical(b) === canonical(preferred)) - Number(canonical(a) === canonical(preferred))); }
    const events = workload(request.seed, request.max_events), attempts = [];
    const world = {version: 1, prediction: 'nested map reduces tuple-key serialization', uncertainty: 'allocation and sorting may dominate', experiment: 'prioritize nested-map compositions, then test tuple-map alternatives within the same budget', selection_rule: 'minimum measured development elapsed_ns among correct candidates; not final proof'};
    for (const config of configurations) {
        abort(signal); await pause(); abort(signal);
        const fn = values => candidate(values, config), pass = correct(fn), measurement = measured(fn, events);
        const attempt = {config, construction: {operator: 'bounded-grammar-composition', seed: request.seed, parent: VERSION}, artifact_hash: await digest('candidate', config), correctness: pass, elapsed_ns: measurement.elapsed_ns, rows: measurement.rows};
        attempts.push(attempt); onProgress(attempts.length, configurations.length);
    }
    const nested = attempts.filter(a => a.config.layout === 'nested'), tuples = attempts.filter(a => a.config.layout === 'tuple');
    world.observation = {nested_mean_ns: Math.round(nested.reduce((sum, a) => sum + a.elapsed_ns, 0) / (nested.length || 1)), tuple_mean_ns: Math.round(tuples.reduce((sum, a) => sum + a.elapsed_ns, 0) / (tuples.length || 1)), interpretation: 'development observation only; confounded by composition and browser timing'};
    world.falsified_in_this_run = world.observation.nested_mean_ns >= world.observation.tuple_mean_ns;
    const feasible = attempts.filter(a => a.correctness).sort((a, b) => a.elapsed_ns - b.elapsed_ns);
    if (!feasible.length) throw Error('No correct candidate; retain Current');
    return {world, attempts, selected: feasible[0], generation_budget: request.max_candidates, actual_candidates: configurations.length, source: VERSION};
}
export async function freeze(request, discovery, sourceHash) {
    if (!/^[0-9a-f]{64}$/.test(sourceHash)) throw Error('Exact engine source digest required');
    const manifest = {schema_version: 1, request_hash: await digest('request', validateRequest(request)), grammar: discovery.selected.config, candidate_hash: discovery.selected.artifact_hash, engine: VERSION, engine_source_hash: sourceHash, comparators: ['current-one-pass-map-v1', 'beta-sorted-reduction-v1'], protocol: 'browser-local-aggregation-v1', correctness_required: true, minimum_speedup_ppm: 50000, costs: {money: null, review: null, memory: null}, authority: []};
    return {manifest, release_hash: await digest('release', manifest)};
}
export async function evaluate(request, frozen, {signal} = {}) {
    request = validateRequest(request);
    if (frozen.manifest.request_hash !== await digest('request', request) || frozen.release_hash !== await digest('release', frozen.manifest)) throw Error('Frozen release or request changed');
    if (frozen.manifest.candidate_hash !== await digest('candidate', frozen.manifest.grammar) || frozen.manifest.protocol !== 'browser-local-aggregation-v1' || frozen.manifest.minimum_speedup_ppm !== 50000 || frozen.manifest.correctness_required !== true || canonical(frozen.manifest.comparators) !== canonical(['current-one-pass-map-v1', 'beta-sorted-reduction-v1'])) throw Error('Candidate or protocol binding mismatch');
    const config = validateCandidate(frozen.manifest.grammar), fn = e => candidate(e, config), cases = [];
    const correctness = correct(fn);
    for (let i = 0; i < 6; i++) {
        abort(signal); await pause(); abort(signal);
        const events = workload((request.seed + 100003 + i * 907) >>> 0, i < 2 ? 64 : request.max_events, i % 2 ? 'high' : 'mixed');
        const samples = [measured(current, events), measured(beta, events), measured(fn, events)];
        const exact_output = canonical(samples[0].result) === canonical(samples[1].result) && canonical(samples[1].result) === canonical(samples[2].result);
        cases.push({case_index: i, events: events.length, current_ns: samples[0].elapsed_ns, beta_ns: samples[1].elapsed_ns, candidate_ns: samples[2].elapsed_ns, exact_output});
    }
    const totals = {current: 0, beta: 0, candidate: 0};
    for (const c of cases) { totals.current += c.current_ns; totals.beta += c.beta_ns; totals.candidate += c.candidate_ns; }
    const best_comparator = totals.current <= totals.beta ? 'current' : 'beta';
    const hard_gate = correctness && cases.every(c => c.exact_output);
    return {schema_version: 1, scope: 'browser-rehearsal', release_hash: frozen.release_hash, cases, correctness: hard_gate, totals_ns: totals, best_comparator, local_verdict: !hard_gate ? 'FAIL' : totals.candidate >= totals[best_comparator] ? (best_comparator === 'beta' ? 'RETAIN_ALTERNATIVE' : 'RETAIN_INCUMBENT') : totals.candidate / totals[best_comparator] > 0.95 ? 'INSUFFICIENT_MARGIN' : 'LOCAL_SPEEDUP_OBSERVED', institutional_verdict: 'HOLD', missing: ['independent-verifier', 'frontier-comparator', 'measured-peak-memory', 'accepted-realized-economics', 'principal-issued-authority'], authority: [], timing_limitations: 'Single browser process; timer resolution, order, JIT and device load confound timings. Descriptive measurements only.'};
}
export async function renew(request, discovery, {signal, onProgress = () => {}, engineSourceHash = null} = {}) {
    request = validateRequest(request);
    const trials = [];
    for (let i = 0; i < request.formation_trials; i++) {
        abort(signal);
        const next = {...request, seed: (request.seed + 200003 + i * 997) >>> 0};
        const control = await discover(next, {signal}), treatment = await discover(next, {signal, preferred: discovery.selected.config});
        const controlFreeze = await freeze(next, control, engineSourceHash), treatmentFreeze = await freeze(next, treatment, engineSourceHash);
        const controlEvaluation = await evaluate(next, controlFreeze, {signal}), treatmentEvaluation = await evaluate(next, treatmentFreeze, {signal});
        trials.push({trial: i, seed: next.seed, control_attempts: control.attempts.length, treatment_attempts: treatment.attempts.length, control, treatment, control_release: controlFreeze, treatment_release: treatmentFreeze, control_evaluation: controlEvaluation, treatment_evaluation: treatmentEvaluation});
        onProgress(i + 1, request.formation_trials);
    }
    return {generation: 2, active_proof: [], authority: [], memory: {permitted: ['configuration-order-hint'], excluded: ['final-cases', 'proof', 'grants']}, primary_metric: 'construction_attempts', interpretation: 'Descriptive matched trials; equal construction counts do not establish compounding.', trials};
}
export async function verifyNative(request, envelope) {
    request = validateRequest(request);
    if (!exact(envelope, ['schema_version', 'kind', 'request_hash', 'evidence', 'evidence_hash', 'scope', 'signature']) || envelope.schema_version !== 1 || envelope.kind !== 'successor-result' || envelope.scope !== 'local-native-rehearsal') throw Error('Unsupported native evidence envelope');
    if (envelope.request_hash !== await digest('request', request)) throw Error('Native result belongs to a different request');
    if (!envelope.evidence || envelope.evidence.scope !== envelope.scope || envelope.evidence.request_hash !== envelope.request_hash || !exact(envelope.evidence.request, Object.keys(request)) || canonical(envelope.evidence.request) !== canonical(request)) throw Error('Authenticated evidence request or scope mismatch');
    if (envelope.evidence_hash !== await digest('evidence', envelope.evidence)) throw Error('Native evidence digest mismatch');
    if (envelope.signature !== null) {
        const signature = envelope.signature;
        if (!exact(signature, ['public_key', 'signature']) || !/^[0-9a-f]{64}$/.test(signature.public_key) || !/^[A-Za-z0-9+/]{86}==$/.test(signature.signature)) throw Error('Malformed native signature');
        const key = await crypto.subtle.importKey('raw', Uint8Array.from(signature.public_key.match(/../g), x => parseInt(x, 16)), {name: 'Ed25519'}, false, ['verify']);
        const bytes = Uint8Array.from(atob(signature.signature), c => c.charCodeAt(0));
        const data = Uint8Array.from(envelope.evidence_hash.match(/../g), x => parseInt(x, 16));
        if (!await crypto.subtle.verify('Ed25519', key, bytes, data)) throw Error('Invalid native signature');
    }
    return {scope: envelope.scope, integrity: 'request-and-evidence-digests-match', authenticity: 'unverified', authority: [], evidence: envelope.evidence};
}
