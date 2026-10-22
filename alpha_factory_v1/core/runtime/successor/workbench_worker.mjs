// SPDX-License-Identifier: Apache-2.0
// Generated; edit examples/successor-workbench/engine.mjs.
const module_1=(()=>{
// SPDX-License-Identifier: Apache-2.0
/** Fixed, bounded aggregation engines. No generated JavaScript is executed. */
const VERSION = 'successor-browser-v1';
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
function canonical(value) {
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
async function digest(domain, value) {
    if (!/^[a-z][a-z0-9-]{0,63}$/.test(domain)) throw Error('Invalid digest domain');
    const bytes = new TextEncoder().encode('successor-omega/v1:' + domain + '\0' + canonical(value));
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
}
/** Parse untrusted imports before they can allocate large or deeply nested objects. */
function parseBounded(text) {
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
function validateRequest(request) {
    const keys = ['schema_version', 'kind', 'request_id', 'mission', 'seed', 'max_candidates', 'formation_trials', 'max_events', 'language'];
    if (!request || typeof request !== 'object' || Array.isArray(request) || !Object.hasOwn(request, 'request_id') || Object.keys(request).some(key => !keys.includes(key))) throw Error('Invalid versioned rehearsal request');
    request = {schema_version: 1, kind: 'successor-rehearsal', mission: 'streaming-metrics-v1', seed: 42, max_candidates: 4, formation_trials: 2, max_events: 1000, language: 'en', ...request};
    if (!exact(request, keys) || request.schema_version !== 1 || request.kind !== 'successor-rehearsal' || request.mission !== 'streaming-metrics-v1' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(request.request_id) || !integer(request.seed, 0, 4294967295) || !integer(request.max_candidates, 2, 12) || !integer(request.formation_trials, 1, 6) || !integer(request.max_events, 64, 20000) || !['en', 'fr'].includes(request.language)) throw Error('Invalid versioned rehearsal request');
    return structuredClone(request);
}
function newRequest(options = {}) {
    return validateRequest({schema_version: 1, kind: 'successor-rehearsal', request_id: crypto.randomUUID(), mission: 'streaming-metrics-v1', seed: 42, max_candidates: 4, formation_trials: 2, max_events: 1000, language: 'en', ...options});
}
function order(a, b) {
    const aa = Array.from(a, c => c.codePointAt(0)), bb = Array.from(b, c => c.codePointAt(0));
    for (let i = 0; i < Math.min(aa.length, bb.length); i++) if (aa[i] !== bb[i]) return aa[i] - bb[i];
    return aa.length - bb.length;
}
const rowOrder = (a, b) => order(a.day, b.day) || order(a.service, b.service);
function validateEvents(events) {
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
function current(events) {
    validateEvents(events); const groups = new Map();
    for (const e of events) {
        const key = JSON.stringify([e.day, e.service]);
        if (!groups.has(key)) groups.set(key, makeRow(e));
        update(groups.get(key), e);
    }
    return [...groups.values()].sort(rowOrder);
}
function beta(events) {
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
function validateCandidate(c) {
    if (!exact(c, ['version', 'layout', 'cache_last', 'update']) || c.version !== 1 || !['nested', 'tuple'].includes(c.layout) || typeof c.cache_last !== 'boolean' || !['branch', 'builtin'].includes(c.update)) throw Error('Candidate is outside the fixed grammar');
    return c;
}
function candidate(events, config) {
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
function generateCandidates(seed, count) {
    if (!integer(count, 2, 12)) throw Error('Candidate count outside bound');
    const out = [];
    // Eight complete compositions; repeated configuration is never represented as a new challenger.
    for (let i = 0; i < Math.min(count, 8); i++) {
        const bits = (i + (seed % 8)) % 8;
        out.push({version: 1, layout: bits & 1 ? 'nested' : 'tuple', cache_last: Boolean(bits & 2), update: bits & 4 ? 'branch' : 'builtin'});
    }
    return out;
}
function workload(seed, count, mode = 'mixed') {
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
async function discover(request, {signal, onProgress = () => {}, preferred = null} = {}) {
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
async function freeze(request, discovery, sourceHash) {
    if (!/^[0-9a-f]{64}$/.test(sourceHash)) throw Error('Exact engine source digest required');
    const manifest = {schema_version: 1, request_hash: await digest('request', validateRequest(request)), grammar: discovery.selected.config, candidate_hash: discovery.selected.artifact_hash, engine: VERSION, engine_source_hash: sourceHash, comparators: ['current-one-pass-map-v1', 'beta-sorted-reduction-v1'], protocol: 'browser-local-aggregation-v1', correctness_required: true, minimum_speedup_ppm: 50000, costs: {money: null, review: null, memory: null}, authority: []};
    return {manifest, release_hash: await digest('release', manifest)};
}
async function evaluate(request, frozen, {signal} = {}) {
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
async function renew(request, discovery, {signal, onProgress = () => {}, engineSourceHash = null} = {}) {
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
// Canonical encoding and low-order rejection supplement WebCrypto verification.
// Mathematical torsion encodings: @noble/curves 1.2.0 src/ed25519.ts ED25519_TORSION_SUBGROUP.
const lowOrderY = new Set([
    '0000000000000000000000000000000000000000000000000000000000000000',
    '0100000000000000000000000000000000000000000000000000000000000000',
    'ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f',
    '26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05',
    'c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a',
]);
const littleEndian = bytes => BigInt('0x' + [...bytes].reverse().map(v => v.toString(16).padStart(2, '0')).join(''));
function validatePointEncoding(bytes) {
    const y = bytes.slice(); y[31] &= 0x7f;
    const hex = [...y].map(v => v.toString(16).padStart(2, '0')).join('');
    if (littleEndian(y) >= (1n << 255n) - 19n || lowOrderY.has(hex)) throw Error('Non-canonical or low-order Ed25519 point');
}
function validateSignatureEncoding(key, signature) {
    validatePointEncoding(key); validatePointEncoding(signature.slice(0, 32));
    if (littleEndian(signature.slice(32)) >= (1n << 252n) + 27742317777372353535851937790883648493n) throw Error('Non-canonical Ed25519 scalar');
}
async function verifyNative(request, envelope) {
    request = validateRequest(request);
    if (!exact(envelope, ['schema_version', 'kind', 'request_hash', 'evidence', 'evidence_hash', 'scope', 'signature']) || envelope.schema_version !== 1 || envelope.kind !== 'successor-result' || envelope.scope !== 'local-native-rehearsal') throw Error('Unsupported native evidence envelope');
    if (envelope.request_hash !== await digest('request', request)) throw Error('Native result belongs to a different request');
    if (!envelope.evidence || envelope.evidence.scope !== envelope.scope || envelope.evidence.request_hash !== envelope.request_hash || !exact(envelope.evidence.request, Object.keys(request)) || canonical(envelope.evidence.request) !== canonical(request)) throw Error('Authenticated evidence request or scope mismatch');
    if (envelope.evidence_hash !== await digest('evidence', envelope.evidence)) throw Error('Native evidence digest mismatch');
    if (envelope.signature !== null) {
        const signature = envelope.signature;
        if (!exact(signature, ['public_key', 'signature']) || !/^[0-9a-f]{64}$/.test(signature.public_key) || !/^[A-Za-z0-9+/]{86}==$/.test(signature.signature)) throw Error('Malformed native signature');
        const publicBytes = Uint8Array.from(signature.public_key.match(/../g), x => parseInt(x, 16));
        const bytes = Uint8Array.from(atob(signature.signature), c => c.charCodeAt(0));
        validateSignatureEncoding(publicBytes, bytes);
        const key = await crypto.subtle.importKey('raw', publicBytes, {name: 'Ed25519'}, false, ['verify']);
        const data = Uint8Array.from(envelope.evidence_hash.match(/../g), x => parseInt(x, 16));
        if (!await crypto.subtle.verify('Ed25519', key, bytes, data)) throw Error('Invalid native signature');
    }
    return {scope: envelope.scope, integrity: 'request-and-evidence-digests-match', authenticity: 'unverified', authority: [], evidence: envelope.evidence};
}

return {VERSION,canonical,digest,parseBounded,validateRequest,newRequest,validateEvents,current,beta,validateCandidate,candidate,generateCandidates,workload,discover,freeze,evaluate,renew,verifyNative};
})();
const module_5=(()=>{
const FORBIDDEN_KEYS = new Set(['__proto__', 'prototype', 'constructor']);

/** Deterministic JSON encoding. Ambiguous or non-JSON values are refused. */
function canonicalize(value) {
  const active = new Set();
  let count = 0;
  const encode = (item, depth) => {
    if (++count > 100000 || depth > 64)
      throw new TypeError('JSON_LIMIT_EXCEEDED');
    if (item === null) return 'null';
    if (typeof item === 'string') {
      if (
        item !== item.normalize('NFC') ||
        /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(
          item
        )
      )
        throw new TypeError('NON_CANONICAL_UNICODE');
      return JSON.stringify(item);
    }
    if (typeof item === 'boolean') return item ? 'true' : 'false';
    if (typeof item === 'number') {
      if (
        !Number.isFinite(item) ||
        Object.is(item, -0) ||
        (Number.isInteger(item) && !Number.isSafeInteger(item))
      )
        throw new TypeError('UNSAFE_NUMBER');
      return JSON.stringify(item);
    }
    if (typeof item !== 'object' || active.has(item))
      throw new TypeError('NON_JSON_VALUE');
    const proto = Object.getPrototypeOf(item);
    if (
      (Array.isArray(item) && proto !== Array.prototype) ||
      (!Array.isArray(item) && proto !== Object.prototype && proto !== null)
    )
      throw new TypeError('NON_JSON_OBJECT');
    active.add(item);
    let encoded;
    if (Object.getOwnPropertySymbols(item).length)
      throw new TypeError('NON_JSON_SYMBOL');
    if (Array.isArray(item)) {
      const names = Object.getOwnPropertyNames(item);
      if (
        names.length !== item.length + 1 ||
        Object.keys(item).length !== item.length
      )
        throw new TypeError('SPARSE_OR_EXTENDED_ARRAY');
      for (let index = 0; index < item.length; index += 1) {
        const descriptor = Object.getOwnPropertyDescriptor(item, String(index));
        if (
          !descriptor ||
          descriptor.get ||
          descriptor.set ||
          !descriptor.enumerable
        )
          throw new TypeError('ACCESSOR_OR_SPARSE_ARRAY');
      }
      encoded = `[${Array.prototype.map
        .call(item, (part) => encode(part, depth + 1))
        .join(',')}]`;
    } else {
      const keys = Object.keys(item).sort();
      for (const key of keys) {
        if (FORBIDDEN_KEYS.has(key) || key !== key.normalize('NFC'))
          throw new TypeError('UNSAFE_OBJECT_KEY');
        if (
          Object.getOwnPropertyDescriptor(item, key)?.get ||
          Object.getOwnPropertyDescriptor(item, key)?.set
        )
          throw new TypeError('ACCESSOR_NOT_ALLOWED');
      }
      encoded = `{${keys
        .map(
          (key) => `${encode(key, depth + 1)}:${encode(item[key], depth + 1)}`
        )
        .join(',')}}`;
    }
    active.delete(item);
    return encoded;
  };
  return encode(value, 0);
}

async function digestBytes(value) {
  const bytes =
    typeof value === 'string' ? new TextEncoder().encode(value) : value;
  if (!(bytes instanceof Uint8Array)) throw new TypeError('BYTES_REQUIRED');
  if (!globalThis.crypto?.subtle) throw new Error('WEBCRYPTO_UNAVAILABLE');
  const digest = new Uint8Array(
    await globalThis.crypto.subtle.digest('SHA-256', bytes)
  );
  return `sha256:${Array.from(digest, (byte) =>
    byte.toString(16).padStart(2, '0')
  ).join('')}`;
}

async function digestObject(domain, object) {
  if (
    typeof domain !== 'string' ||
    !/^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}$/.test(domain)
  )
    throw new TypeError('INVALID_HASH_DOMAIN');
  return digestBytes(
    canonicalize({ hashFormat: 'successor-canonical-json-v1', domain, object })
  );
}

function cloneJson(value) {
  return JSON.parse(canonicalize(value));
}

return {canonicalize,digestBytes,digestObject,cloneJson};
})();
const module_4=(()=>{
const { canonicalize, cloneJson } = module_5;

const SCHEMA_VERSION = '1.0.0';
const JOB_FAMILIES = Object.freeze([
  'constitution',
  'evidence',
  'formation',
  'challenge',
  'verification',
  'admission',
  'renewal',
]);
const EDGE_KINDS = Object.freeze([
  'evidence',
  'control',
  'challenge',
  'rollback',
  'invalidation',
]);
const JOB_STATES = Object.freeze([
  'DRAFT',
  'UNDERWRITTEN',
  'AUTHORIZED',
  'EXECUTING',
  'VERIFIED',
  'ACCEPTED',
  'CHRONICLE_ELIGIBLE',
  'REFUSED',
  'FAILED',
  'TIMED_OUT',
  'REPAIR_REQUIRED',
  'ROLLED_BACK',
]);
class SuccessorError extends Error {
  constructor(code, message, { details = {}, retryable = false } = {}) {
    super(message);
    this.name = 'SuccessorError';
    this.code = code;
    this.details = details;
    this.retryable = retryable;
  }
  toJSON() {
    return {
      code: this.code,
      message: this.message,
      details: this.details,
      retryable: this.retryable,
    };
  }
}
function requireCondition(condition, code, message, details = {}) {
  if (!condition) throw new SuccessorError(code, message, { details });
}
const fail = (path, message) => {
  throw new SuccessorError('SCHEMA_INVALID', `${path}: ${message}`, {
    details: { path },
  });
};
function object(value, keys, required, path) {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    fail(path, 'expected object');
  for (const key of Object.keys(value))
    if (!keys.includes(key)) fail(`${path}.${key}`, 'unknown field');
  for (const key of required)
    if (!Object.hasOwn(value, key)) fail(`${path}.${key}`, 'required field');
}
const text = (value, path) => {
  if (typeof value !== 'string' || !value.trim() || value.length > 16000)
    fail(path, 'expected nonempty bounded string');
};
const id = (value, path) => {
  text(value, path);
  if (!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$/.test(value))
    fail(path, 'invalid identifier');
};
const list = (value, path, check = text, minimum = 0, maximum = 256) => {
  if (!Array.isArray(value) || value.length < minimum || value.length > maximum)
    fail(path, 'invalid list size');
  value.forEach((entry, i) => check(entry, `${path}[${i}]`));
};
const integer = (value, path, min = 0, max = 1000000000) => {
  if (!Number.isSafeInteger(value) || value < min || value > max)
    fail(path, 'expected bounded integer');
};
const date = (value, path) => {
  if (
    typeof value !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$/.test(value) ||
    !Number.isFinite(Date.parse(value))
  )
    fail(path, 'expected UTC ISO timestamp');
  const normalized = new Date(value).toISOString();
  if (value !== normalized && value !== normalized.replace('.000Z', 'Z'))
    fail(path, 'invalid calendar timestamp');
};
const choice = (value, values, path) => {
  if (!values.includes(value))
    fail(path, `expected one of ${values.join(', ')}`);
};
const unique = (values, path) => {
  if (new Set(values).size !== values.length) fail(path, 'duplicate values');
};
const bool = (value, path) => {
  if (typeof value !== 'boolean') fail(path, 'expected boolean');
};
function json(value) {
  try {
    canonicalize(value);
  } catch (error) {
    throw new SuccessorError('SCHEMA_INVALID', error.message);
  }
}
function validateBudget(value, path = 'budget', mission = false) {
  const fields = [
    'unit',
    'limitBaseUnits',
    'maxDurationMs',
    'maxRetries',
    ...(mission ? ['maxJobs'] : []),
  ];
  object(value, fields, fields, path);
  id(value.unit, `${path}.unit`);
  if (
    typeof value.limitBaseUnits !== 'string' ||
    !/^(0|[1-9][0-9]{0,29})$/.test(value.limitBaseUnits)
  )
    fail(
      `${path}.limitBaseUnits`,
      'expected canonical unsigned integer string'
    );
  integer(value.maxDurationMs, `${path}.maxDurationMs`, 1, 86400000);
  integer(value.maxRetries, `${path}.maxRetries`, 0, 100);
  if (mission) integer(value.maxJobs, `${path}.maxJobs`, 1, 256);
}
function rollback(value, path) {
  object(
    value,
    ['target', 'available', 'reason'],
    ['target', 'available', 'reason'],
    path
  );
  id(value.target, `${path}.target`);
  bool(value.available, `${path}.available`);
  text(value.reason, `${path}.reason`);
}
function reference(value, path) {
  object(
    value,
    ['id', 'version', 'description'],
    ['id', 'version', 'description'],
    path
  );
  id(value.id, `${path}.id`);
  id(value.version, `${path}.version`);
  text(value.description, `${path}.description`);
}
function validateMission(input) {
  json(input);
  const fields = [
    'schemaVersion',
    'kind',
    'missionId',
    'institutionId',
    'version',
    'title',
    'principal',
    'beneficiary',
    'objective',
    'incumbent',
    'alternatives',
    'rights',
    'hardGates',
    'criticalFunctions',
    'roles',
    'budget',
    'expiresAt',
    'authorityCeiling',
    'allowedTools',
    'allowedActions',
    'rollback',
    'proofProtocol',
  ];
  object(input, fields, fields, 'mission');
  requireCondition(
    input.schemaVersion === SCHEMA_VERSION,
    'SCHEMA_VERSION_UNSUPPORTED',
    'Unsupported mission schema version'
  );
  choice(input.kind, ['MissionConstitution'], 'mission.kind');
  for (const key of ['missionId', 'institutionId', 'version', 'principal'])
    id(input[key], `mission.${key}`);
  for (const key of ['title', 'beneficiary', 'objective'])
    text(input[key], `mission.${key}`);
  reference(input.incumbent, 'mission.incumbent');
  list(input.alternatives, 'mission.alternatives', reference, 1, 32);
  unique(
    input.alternatives.map((alternative) => alternative.id),
    'mission.alternatives'
  );
  list(
    input.rights,
    'mission.rights',
    (right, path) => {
      object(
        right,
        ['sourceId', 'license', 'dataClass', 'permittedUses', 'expiresAt'],
        ['sourceId', 'license', 'dataClass', 'permittedUses', 'expiresAt'],
        path
      );
      id(right.sourceId, `${path}.sourceId`);
      text(right.license, `${path}.license`);
      choice(
        right.dataClass,
        ['synthetic', 'public-licensed-nonpersonal'],
        `${path}.dataClass`
      );
      list(right.permittedUses, `${path}.permittedUses`, id, 1, 20);
      date(right.expiresAt, `${path}.expiresAt`);
    },
    1,
    256
  );
  unique(
    input.rights.map((right) => right.sourceId),
    'mission.rights'
  );
  list(
    input.hardGates,
    'mission.hardGates',
    (gate, path) => {
      object(
        gate,
        ['id', 'description', 'maxViolations'],
        ['id', 'description', 'maxViolations'],
        path
      );
      id(gate.id, `${path}.id`);
      text(gate.description, `${path}.description`);
      integer(gate.maxViolations, `${path}.maxViolations`, 0, 100);
    },
    1,
    64
  );
  unique(
    input.hardGates.map((gate) => gate.id),
    'mission.hardGates'
  );
  list(input.criticalFunctions, 'mission.criticalFunctions', id, 1, 64);
  unique(input.criticalFunctions, 'mission.criticalFunctions');
  object(
    input.roles,
    ['producer', 'verifier', 'acceptor', 'admitter'],
    ['producer', 'verifier', 'acceptor', 'admitter'],
    'mission.roles'
  );
  for (const [key, value] of Object.entries(input.roles))
    id(value, `mission.roles.${key}`);
  validateBudget(input.budget, 'mission.budget', true);
  date(input.expiresAt, 'mission.expiresAt');
  object(
    input.authorityCeiling,
    ['level', 'permittedActions', 'prohibitedActions', 'externalEffects'],
    ['level', 'permittedActions', 'prohibitedActions', 'externalEffects'],
    'mission.authorityCeiling'
  );
  choice(
    input.authorityCeiling.level,
    ['A0', 'A1', 'A2', 'A3', 'A4'],
    'mission.authorityCeiling.level'
  );
  list(
    input.authorityCeiling.permittedActions,
    'mission.authorityCeiling.permittedActions',
    id,
    1
  );
  list(
    input.authorityCeiling.prohibitedActions,
    'mission.authorityCeiling.prohibitedActions',
    id,
    1
  );
  bool(
    input.authorityCeiling.externalEffects,
    'mission.authorityCeiling.externalEffects'
  );
  list(input.allowedTools, 'mission.allowedTools', id, 1);
  list(input.allowedActions, 'mission.allowedActions', id, 1);
  rollback(input.rollback, 'mission.rollback');
  object(
    input.proofProtocol,
    [
      'id',
      'version',
      'mode',
      'formationOwner',
      'custodian',
      'requiredIndependence',
      'minimumMargin',
      'criticalErrorCeiling',
      'scope',
    ],
    [
      'id',
      'version',
      'mode',
      'formationOwner',
      'custodian',
      'requiredIndependence',
      'minimumMargin',
      'criticalErrorCeiling',
      'scope',
    ],
    'mission.proofProtocol'
  );
  for (const key of ['id', 'version', 'formationOwner', 'custodian'])
    id(input.proofProtocol[key], `mission.proofProtocol.${key}`);
  choice(
    input.proofProtocol.mode,
    ['SYNTHETIC_REHEARSAL', 'INDEPENDENT_REQUEST'],
    'mission.proofProtocol.mode'
  );
  choice(
    input.proofProtocol.requiredIndependence,
    ['I0', 'I1', 'I2', 'I3', 'I4'],
    'mission.proofProtocol.requiredIndependence'
  );
  if (
    !Number.isFinite(input.proofProtocol.minimumMargin) ||
    input.proofProtocol.minimumMargin < 0
  )
    fail('mission.proofProtocol.minimumMargin', 'expected nonnegative number');
  integer(
    input.proofProtocol.criticalErrorCeiling,
    'mission.proofProtocol.criticalErrorCeiling',
    0,
    100
  );
  text(input.proofProtocol.scope, 'mission.proofProtocol.scope');
  return cloneJson(input);
}

function validateWorkOrder(input) {
  json(input);
  const required = [
    'schemaVersion',
    'kind',
    'jobId',
    'missionId',
    'version',
    'family',
    'objective',
    'principal',
    'actor',
    'authorizedInputs',
    'evidenceObligation',
    'permittedTools',
    'permittedActions',
    'prohibitedActions',
    'budget',
    'expiresAt',
    'outputSchema',
    'verifier',
    'acceptance',
    'rollback',
    'chronicle',
    'covers',
    'state',
  ];
  object(
    input,
    [...required, 'digest', 'sealed', 'signatureStatus'],
    required,
    'job'
  );
  requireCondition(
    input.schemaVersion === SCHEMA_VERSION,
    'SCHEMA_VERSION_UNSUPPORTED',
    'Unsupported work-order schema version'
  );
  choice(input.kind, ['SealedWorkOrder'], 'job.kind');
  for (const key of ['jobId', 'missionId', 'version', 'principal', 'actor'])
    id(input[key], `job.${key}`);
  choice(input.family, JOB_FAMILIES, 'job.family');
  choice(input.state, JOB_STATES, 'job.state');
  text(input.objective, 'job.objective');
  for (const key of [
    'authorizedInputs',
    'evidenceObligation',
    'permittedTools',
    'permittedActions',
    'prohibitedActions',
    'covers',
  ]) {
    list(input[key], `job.${key}`, id, key === 'covers' ? 0 : 1);
    unique(input[key], `job.${key}`);
  }
  validateBudget(input.budget, 'job.budget');
  date(input.expiresAt, 'job.expiresAt');
  object(
    input.outputSchema,
    ['type', 'required'],
    ['type', 'required'],
    'job.outputSchema'
  );
  choice(input.outputSchema.type, ['object'], 'job.outputSchema.type');
  list(input.outputSchema.required, 'job.outputSchema.required', id, 1);
  object(
    input.verifier,
    ['identity', 'method', 'independence'],
    ['identity', 'method', 'independence'],
    'job.verifier'
  );
  id(input.verifier.identity, 'job.verifier.identity');
  text(input.verifier.method, 'job.verifier.method');
  choice(
    input.verifier.independence,
    ['I0', 'I1', 'I2', 'I3', 'I4'],
    'job.verifier.independence'
  );
  object(
    input.acceptance,
    ['owner', 'predicate', 'evidenceSources'],
    ['owner', 'predicate', 'evidenceSources'],
    'job.acceptance'
  );
  id(input.acceptance.owner, 'job.acceptance.owner');
  text(input.acceptance.predicate, 'job.acceptance.predicate');
  list(
    input.acceptance.evidenceSources,
    'job.acceptance.evidenceSources',
    id,
    1
  );
  rollback(input.rollback, 'job.rollback');
  object(
    input.chronicle,
    ['eligible', 'rights', 'scope', 'expiresAt'],
    ['eligible', 'rights', 'scope', 'expiresAt'],
    'job.chronicle'
  );
  bool(input.chronicle.eligible, 'job.chronicle.eligible');
  text(input.chronicle.rights, 'job.chronicle.rights');
  text(input.chronicle.scope, 'job.chronicle.scope');
  date(input.chronicle.expiresAt, 'job.chronicle.expiresAt');
  if ('sealed' in input) bool(input.sealed, 'job.sealed');
  if ('digest' in input && !/^sha256:[a-f0-9]{64}$/.test(input.digest))
    fail('job.digest', 'expected SHA-256 digest');
  if ('signatureStatus' in input)
    choice(
      input.signatureStatus,
      ['UNSIGNED_COMMITMENT', 'FIXTURE_SIGNED', 'AUTHORIZED_SIGNATURE'],
      'job.signatureStatus'
    );
  return cloneJson(input);
}

function validateGraph(input) {
  json(input);
  object(
    input,
    [
      'schemaVersion',
      'kind',
      'graphId',
      'missionId',
      'version',
      'nodes',
      'edges',
      'authorityCreated',
      'digest',
    ],
    [
      'schemaVersion',
      'kind',
      'graphId',
      'missionId',
      'version',
      'nodes',
      'edges',
      'authorityCreated',
    ],
    'graph'
  );
  requireCondition(
    input.schemaVersion === SCHEMA_VERSION,
    'SCHEMA_VERSION_UNSUPPORTED',
    'Unsupported graph schema version'
  );
  choice(input.kind, ['JobGraph'], 'graph.kind');
  for (const key of ['graphId', 'missionId', 'version'])
    id(input[key], `graph.${key}`);
  list(input.nodes, 'graph.nodes', validateWorkOrder, 1, 256);
  unique(
    input.nodes.map((node) => node.jobId),
    'graph.nodes'
  );
  list(
    input.edges,
    'graph.edges',
    (edge, path) => {
      object(edge, ['from', 'to', 'kind'], ['from', 'to', 'kind'], path);
      id(edge.from, `${path}.from`);
      id(edge.to, `${path}.to`);
      choice(edge.kind, EDGE_KINDS, `${path}.kind`);
    },
    0,
    2048
  );
  choice(input.authorityCreated, ['NONE'], 'graph.authorityCreated');
  return cloneJson(input);
}

const FORWARD = {
  DRAFT: 'UNDERWRITTEN',
  UNDERWRITTEN: 'AUTHORIZED',
  AUTHORIZED: 'EXECUTING',
  EXECUTING: 'VERIFIED',
  VERIFIED: 'ACCEPTED',
  ACCEPTED: 'CHRONICLE_ELIGIBLE',
};
// Pure reducer: context must originate in a trusted runtime, never request JSON.
function transitionJob(current, event, context = {}) {
  const job = validateWorkOrder(current);
  json(event);
  object(
    event,
    [
      'eventId',
      'expectedState',
      'to',
      'actor',
      'timestamp',
      'evidence',
      'reason',
    ],
    [
      'eventId',
      'expectedState',
      'to',
      'actor',
      'timestamp',
      'evidence',
      'reason',
    ],
    'event'
  );
  id(event.eventId, 'event.eventId');
  id(event.actor, 'event.actor');
  date(event.timestamp, 'event.timestamp');
  text(event.reason, 'event.reason');
  list(event.evidence, 'event.evidence', id, 1);
  requireCondition(
    event.expectedState === job.state,
    'STATE_CONFLICT',
    'The job changed; reload before retrying'
  );
  const exceptional = [
    'REFUSED',
    'FAILED',
    'TIMED_OUT',
    'REPAIR_REQUIRED',
    'ROLLED_BACK',
  ];
  requireCondition(
    FORWARD[job.state] === event.to ||
      (exceptional.includes(event.to) &&
        !['CHRONICLE_ELIGIBLE', ...exceptional].includes(job.state)),
    'TRANSITION_FORBIDDEN',
    'This job transition is not permitted'
  );
  const owner =
    event.to === 'VERIFIED'
      ? job.verifier.identity
      : ['ACCEPTED', 'CHRONICLE_ELIGIBLE'].includes(event.to)
      ? job.acceptance.owner
      : event.to === 'EXECUTING'
      ? job.actor
      : job.principal;
  requireCondition(
    event.actor === owner,
    'ROLE_CONFLICT',
    'The actor cannot authorize this transition'
  );
  if (['AUTHORIZED', 'EXECUTING'].includes(event.to)) {
    requireCondition(
      job.sealed === true && !!job.digest,
      'JOB_UNSEALED',
      'Seal the exact work order before authorization'
    );
    requireCondition(
      context.sealValid === true,
      'JOB_SEAL_UNVERIFIED',
      'The runtime must cryptographically verify the immutable work-order seal'
    );
    requireCondition(
      Date.parse(event.timestamp) < Date.parse(job.expiresAt),
      'JOB_EXPIRED',
      'The work order has expired'
    );
    requireCondition(
      context.preconditionsValid === true,
      'PRECONDITION_UNAVAILABLE',
      'Rights, dependencies and budget must be validated by the runtime'
    );
  }
  if (event.to === 'VERIFIED')
    requireCondition(
      context.verifierVerdict === 'PASS' && context.receiptValid === true,
      'VERIFICATION_REQUIRED',
      'A valid receipt and passing independent verdict are required'
    );
  if (event.to === 'ACCEPTED')
    requireCondition(
      context.acceptanceSatisfied === true,
      'ACCEPTANCE_CRITERIA_UNMET',
      'The runtime must verify the frozen deliverable acceptance predicate'
    );
  if (event.to === 'CHRONICLE_ELIGIBLE')
    requireCondition(
      job.chronicle.eligible && context.rightsCurrent === true,
      'CHRONICLE_INELIGIBLE',
      'Current reuse rights are required'
    );
  return { ...job, state: event.to };
}

return {SCHEMA_VERSION,JOB_FAMILIES,EDGE_KINDS,JOB_STATES,SuccessorError,requireCondition,validateBudget,validateMission,validateWorkOrder,validateGraph,transitionJob};
})();
const module_6=(()=>{
const { SCHEMA_VERSION, validateMission } = module_4;

const JOB_TEMPLATES = Object.freeze(
  [
    [
      'mission-constitution',
      'constitution',
      'Mission Constitution',
      'Freeze objective, beneficiary, accountable principal, hard constraints and prohibitions.',
    ],
    [
      'incumbent-baseline',
      'evidence',
      'Incumbent Baseline',
      'Measure accepted quality, complete cost, risk, time, human burden and authority.',
    ],
    [
      'alternative-set',
      'constitution',
      'Alternative Set',
      'Document the strongest credible frontier, specialist, human, hybrid, software and no-action alternatives.',
    ],
    [
      'rights-data',
      'constitution',
      'Rights and Data Constitution',
      'Establish source provenance, licenses, retention, exclusions and permitted reuse.',
    ],
    [
      'mission-gym',
      'formation',
      'Mission Gym and Benchmark Constitution',
      'Specify states, observations, actions, transitions, rewards, constraints, partitions, verifier and basis risk; freeze representative distribution, protected custody, critical failures and thresholds.',
    ],
    [
      'oracle-teacher',
      'evidence',
      'Oracle and Teacher Study',
      'Declare external teaching signals, hidden-call prohibition and transfer hypothesis.',
    ],
    [
      'failure-taxonomy',
      'challenge',
      'Failure Taxonomy',
      'Classify errors, severity, causes, abstention, adversarial cases and stop conditions.',
    ],
    [
      'architecture-frontier',
      'formation',
      'Architecture Frontier',
      'Form diverse complete candidates and retain non-dominated reserve options.',
    ],
    [
      'experience-formation',
      'formation',
      'Data and Experience Formation',
      'Build rights-cleared examples and simulation experience with explicit quality controls.',
    ],
    [
      'specialist-formation',
      'formation',
      'Specialist Model Formation',
      'Construct or adapt candidate components with exact immutable release identities.',
    ],
    [
      'tools-retrieval',
      'formation',
      'Tool and Retrieval Formation',
      'Build bounded deterministic checks, retrieval, planners, sandboxes and interfaces.',
    ],
    [
      'verifier-formation',
      'verification',
      'Verifier Formation',
      'Calibrate independent evaluation, replay, attacks, hidden ground truth and scoring.',
    ],
    [
      'security-privacy',
      'verification',
      'Security and Privacy Proof',
      'Test credential controls, isolation, threat model, incidents and provider risks.',
    ],
    [
      'complete-economics',
      'evidence',
      'Complete Economics',
      'Count construction, operation, human rescue, maintenance, requalification and unwind.',
    ],
    [
      'human-agency',
      'constitution',
      'Human Burden and Agency',
      'Define reviewer capacity, escalation, contestability and accountable decision rights.',
    ],
    [
      'resilience-rollback',
      'verification',
      'Resilience and Rollback',
      'Prove graceful degradation, kill switch, portability and known-good restoration.',
    ],
    [
      'fresh-evaluation',
      'verification',
      'Protected Fresh Evaluation',
      'Evaluate one frozen challenger on unseen representative work with full intervention costs.',
    ],
    [
      'independent-validation',
      'verification',
      'Independent Validation',
      'Independently examine evidence, limitations, critical errors, basis risk and fit for stated purpose.',
    ],
    [
      'accountable-acceptance',
      'admission',
      'Accountable Acceptance',
      'Record the attributable purpose-specific acceptance decision separately from independent validation and authority admission.',
    ],
    [
      'chronicle-authority',
      'admission',
      'Chronicle and Authority Admission',
      'Record separate knowledge and authority decisions, scope, expiry, monitoring and revocation.',
    ],
    [
      'capital-requalification',
      'renewal',
      'Capital-to-Capacity and Requalification',
      'Allocate verified available value and define next-successor and fresh-transfer triggers.',
    ],
  ].map(([id, family, title, objective]) =>
    Object.freeze({ id, family, title, objective, coverageKey: id })
  )
);

function createPortfolioJobs(input) {
  const mission = validateMission(input);
  return JOB_TEMPLATES.map((template) => ({
    schemaVersion: SCHEMA_VERSION,
    kind: 'SealedWorkOrder',
    jobId: `${mission.missionId}:${template.id}`,
    missionId: mission.missionId,
    version: '1',
    family: template.family,
    objective: template.objective,
    principal: mission.principal,
    actor: mission.roles.producer,
    authorizedInputs: mission.rights.map((right) => right.sourceId),
    evidenceObligation: ['source-lineage', 'complete-cost', 'failure-record'],
    permittedTools: [...mission.allowedTools],
    permittedActions: [...mission.allowedActions],
    prohibitedActions: [...mission.authorityCeiling.prohibitedActions],
    budget: {
      unit: mission.budget.unit,
      limitBaseUnits: (BigInt(mission.budget.limitBaseUnits) / 21n).toString(),
      maxDurationMs: mission.budget.maxDurationMs,
      maxRetries: mission.budget.maxRetries,
    },
    expiresAt: mission.expiresAt,
    outputSchema: {
      type: 'object',
      required: ['evidence', 'findings', 'cost'],
    },
    verifier: {
      identity: mission.roles.verifier,
      method:
        'Independent examination against frozen purpose-specific criteria; template is not executed proof.',
      independence: 'I0',
    },
    acceptance: {
      owner: mission.roles.acceptor,
      predicate: `All ${template.title} obligations have valid traceable evidence and no failed hard gate.`,
      evidenceSources: mission.rights.map((right) => right.sourceId),
    },
    rollback: { ...mission.rollback },
    chronicle: {
      eligible: false,
      rights: 'Requires a separate rights and admission review.',
      scope: mission.objective,
      expiresAt: mission.expiresAt,
    },
    covers: mission.criticalFunctions.includes(template.coverageKey)
      ? [template.coverageKey]
      : [],
    state: 'DRAFT',
  }));
}

return {JOB_TEMPLATES,createPortfolioJobs};
})();
const module_3=(()=>{
const {
  SCHEMA_VERSION,
  SuccessorError,
  requireCondition,
  validateMission,
  validateWorkOrder,
  validateGraph,
  transitionJob,
} = module_4;
const { cloneJson, digestObject } = module_5;
const { createPortfolioJobs } = module_6;

const EXECUTION_EDGES = new Set(['evidence', 'control', 'challenge']);
function workOrderPayload(input) {
  const job = validateWorkOrder(input);
  const { digest, sealed, signatureStatus, state, ...immutable } = job;
  return immutable;
}
async function sealWorkOrder(input) {
  const job = validateWorkOrder(input);
  requireCondition(
    job.state === 'DRAFT',
    'SEAL_STATE_FORBIDDEN',
    'Only a draft may be sealed; material changes require a new draft version'
  );
  return {
    ...job,
    sealed: true,
    signatureStatus: 'UNSIGNED_COMMITMENT',
    digest: await digestObject(
      'successor.work-order.v1',
      workOrderPayload(job)
    ),
  };
}
async function verifyWorkOrderSeal(input) {
  const job = validateWorkOrder(input);
  return (
    job.sealed === true &&
    job.digest ===
      (await digestObject('successor.work-order.v1', workOrderPayload(job)))
  );
}
async function transitionSealedJob(current, event, trustedContext = {}) {
  requireCondition(
    await verifyWorkOrderSeal(current),
    'JOB_SEAL_INVALID',
    'The immutable work-order seal is invalid'
  );
  return transitionJob(current, event, { ...trustedContext, sealValid: true });
}
function topologicalOrder(nodes, edges) {
  const indegree = new Map(nodes.map((node) => [node.jobId, 0]));
  const outgoing = new Map(nodes.map((node) => [node.jobId, []]));
  for (const edge of edges.filter((edge) => EXECUTION_EDGES.has(edge.kind))) {
    outgoing.get(edge.from).push(edge.to);
    indegree.set(edge.to, indegree.get(edge.to) + 1);
  }
  const queue = [...indegree]
    .filter(([, count]) => count === 0)
    .map(([key]) => key)
    .sort();
  const order = [];
  const depth = new Map(nodes.map((node) => [node.jobId, 1]));
  while (queue.length) {
    const key = queue.shift();
    order.push(key);
    for (const target of outgoing.get(key)) {
      depth.set(target, Math.max(depth.get(target), depth.get(key) + 1));
      indegree.set(target, indegree.get(target) - 1);
      if (!indegree.get(target)) {
        queue.push(target);
        queue.sort();
      }
    }
  }
  requireCondition(
    order.length === nodes.length,
    'GRAPH_CYCLE',
    'Execution, acceptance and challenge dependencies must be acyclic; use bounded version-producing discovery loops'
  );
  requireCondition(
    Math.max(...depth.values()) <= 64,
    'GRAPH_DEPTH_EXCEEDED',
    'Graph exceeds the supported execution depth'
  );
  return order;
}

async function compileJobs(
  input,
  { jobs: proposedJobs, edges = [], now = new Date().toISOString() } = {}
) {
  const mission = validateMission(input);
  const instant = Date.parse(now);
  requireCondition(
    Number.isFinite(instant),
    'CLOCK_INVALID',
    'A valid compiler clock is required'
  );
  requireCondition(
    instant < Date.parse(mission.expiresAt),
    'MISSION_EXPIRED',
    'The mission constitution has expired'
  );
  requireCondition(
    new Set([
      mission.roles.producer,
      mission.roles.verifier,
      mission.roles.admitter,
    ]).size === 3,
    'ROLE_CONFLICT',
    'Producer, verifier and admitter must have distinct identities'
  );
  requireCondition(
    mission.roles.producer !== mission.roles.acceptor,
    'ROLE_CONFLICT',
    'A producer cannot accept its own delivered work'
  );
  requireCondition(
    mission.proofProtocol.formationOwner !== mission.proofProtocol.custodian,
    'PROOF_CUSTODY_CONFLICT',
    'Formation and protected proof custody must be separately attributed'
  );
  requireCondition(
    mission.rollback.available,
    'ROLLBACK_UNAVAILABLE',
    'An available rollback or containment route is required'
  );
  if (mission.proofProtocol.mode === 'INDEPENDENT_REQUEST')
    requireCondition(
      ['I3', 'I4'].includes(mission.proofProtocol.requiredIndependence),
      'INDEPENDENCE_INSUFFICIENT',
      'An independently proven request requires I3 or I4 custody; internal rehearsal remains available'
    );
  for (const action of mission.allowedActions)
    requireCondition(
      !mission.authorityCeiling.prohibitedActions.includes(action),
      'ACTION_PROHIBITED',
      'A permitted formation action conflicts with a prohibition',
      { action }
    );
  requireCondition(
    proposedJobs === undefined || Array.isArray(proposedJobs),
    'SCHEMA_INVALID',
    'Jobs must be a bounded array'
  );
  const jobs = (proposedJobs ?? createPortfolioJobs(mission)).map(
    validateWorkOrder
  );
  requireCondition(
    jobs.length <= mission.budget.maxJobs,
    'JOB_LIMIT_EXCEEDED',
    'The graph exceeds its authorized work count'
  );
  const graph = validateGraph({
    schemaVersion: SCHEMA_VERSION,
    kind: 'JobGraph',
    graphId: `${mission.missionId}:graph`,
    missionId: mission.missionId,
    version: mission.version,
    nodes: jobs,
    edges,
    authorityCreated: 'NONE',
  });
  const ids = new Set(jobs.map((job) => job.jobId));
  const rights = new Map(
    mission.rights.map((right) => [right.sourceId, right])
  );
  const edgeKeys = new Set();
  for (const edge of graph.edges) {
    requireCondition(
      ids.has(edge.from) && ids.has(edge.to),
      'REFERENCE_UNRESOLVED',
      'A graph edge references an unknown job',
      edge
    );
    requireCondition(
      edge.from !== edge.to,
      'GRAPH_CYCLE',
      'Self-dependent jobs are not admissible',
      edge
    );
    const key = `${edge.from}|${edge.to}|${edge.kind}`;
    requireCondition(
      !edgeKeys.has(key),
      'EDGE_DUPLICATE',
      'Duplicate graph edge',
      edge
    );
    edgeKeys.add(key);
  }
  const executionOrder = topologicalOrder(jobs, graph.edges);
  let reservation = 0n;
  for (const job of jobs) {
    requireCondition(
      job.missionId === mission.missionId &&
        job.principal === mission.principal,
      'MISSION_BINDING_MISMATCH',
      'Job mission and accountable principal must match the constitution',
      { jobId: job.jobId }
    );
    requireCondition(
      job.state === 'DRAFT',
      'COMPILER_REQUIRES_DRAFT',
      'Compilation cannot grant or replay an existing job lifecycle state'
    );
    requireCondition(
      job.actor !== job.verifier.identity &&
        job.actor !== mission.roles.admitter,
      'ROLE_CONFLICT',
      'A producer cannot verify its own work or hold admission identity',
      { jobId: job.jobId }
    );
    requireCondition(
      job.actor !== job.acceptance.owner,
      'ROLE_CONFLICT',
      'A producing actor cannot accept its own delivered work',
      { jobId: job.jobId }
    );
    requireCondition(
      job.verifier.identity === mission.roles.verifier,
      'VERIFIER_UNAUTHORIZED',
      'Job verifier must be the constituted verifier identity',
      { jobId: job.jobId }
    );
    requireCondition(
      job.acceptance.owner === mission.roles.acceptor,
      'ACCEPTANCE_OWNER_MISMATCH',
      'Acceptance must belong to the constituted owner',
      { jobId: job.jobId }
    );
    requireCondition(
      job.rollback.available,
      'ROLLBACK_UNAVAILABLE',
      'Job has no available rollback or containment route',
      { jobId: job.jobId }
    );
    requireCondition(
      Date.parse(job.expiresAt) > instant &&
        Date.parse(job.expiresAt) <= Date.parse(mission.expiresAt),
      'JOB_EXPIRED',
      'Job expiry must be current and within the mission expiry',
      { jobId: job.jobId }
    );
    requireCondition(
      job.budget.unit === mission.budget.unit,
      'BUDGET_UNIT_MISMATCH',
      'Job and mission budget units differ',
      { jobId: job.jobId }
    );
    requireCondition(
      job.budget.maxRetries <= mission.budget.maxRetries &&
        job.budget.maxDurationMs <= mission.budget.maxDurationMs,
      'BUDGET_LIMIT_EXCEEDED',
      'Job resource limits exceed the mission ceiling',
      { jobId: job.jobId }
    );
    reservation += BigInt(job.budget.limitBaseUnits);
    for (const tool of job.permittedTools)
      requireCondition(
        mission.allowedTools.includes(tool),
        'TOOL_UNSUPPORTED',
        'The mission has not admitted this tool',
        { jobId: job.jobId, tool }
      );
    for (const action of job.permittedActions)
      requireCondition(
        mission.allowedActions.includes(action) &&
          !job.prohibitedActions.includes(action) &&
          !mission.authorityCeiling.prohibitedActions.includes(action),
        'ACTION_PROHIBITED',
        'Action is not within the mission capability mask',
        { jobId: job.jobId, action }
      );
    for (const prohibited of mission.authorityCeiling.prohibitedActions)
      requireCondition(
        job.prohibitedActions.includes(prohibited),
        'PROHIBITION_WEAKENED',
        'Job removes a constitutional prohibition',
        { jobId: job.jobId, prohibited }
      );
    for (const source of job.authorizedInputs) {
      if (rights.has(source)) {
        const right = rights.get(source);
        requireCondition(
          Date.parse(right.expiresAt) > instant &&
            Date.parse(right.expiresAt) >= Date.parse(job.expiresAt),
          'RIGHTS_EXPIRED',
          'Source rights do not cover the job duration',
          { jobId: job.jobId, source }
        );
        requireCondition(
          right.permittedUses.includes('mission-evaluation'),
          'RIGHTS_SCOPE_MISMATCH',
          'Source does not permit mission evaluation',
          { jobId: job.jobId, source }
        );
      } else {
        requireCondition(
          ids.has(source) &&
            graph.edges.some(
              (edge) =>
                edge.from === source &&
                edge.to === job.jobId &&
                edge.kind === 'evidence'
            ),
          'EVIDENCE_PATH_MISSING',
          'Every derived input requires an upstream evidence edge',
          { jobId: job.jobId, source }
        );
      }
    }
    for (const source of job.acceptance.evidenceSources)
      requireCondition(
        job.authorizedInputs.includes(source),
        'ACCEPTANCE_EVIDENCE_UNAVAILABLE',
        'Acceptance cannot depend on an unauthorized or producer-only source',
        { jobId: job.jobId, source }
      );
  }
  requireCondition(
    reservation <= BigInt(mission.budget.limitBaseUnits),
    'BUDGET_EXCEEDED',
    'Aggregate cumulative job budgets exceed the mission budget',
    {
      reservedBaseUnits: reservation.toString(),
      limitBaseUnits: mission.budget.limitBaseUnits,
    }
  );
  const coverage = mission.criticalFunctions.map((functionId) => ({
    functionId,
    jobIds: jobs
      .filter((job) => job.covers.includes(functionId))
      .map((job) => job.jobId),
    status: 'PLANNED_NOT_ACCEPTED',
  }));
  for (const obligation of coverage)
    requireCondition(
      obligation.jobIds.length > 0,
      'CRITICAL_COVERAGE_MISSING',
      'A non-negotiable mission function has no job path',
      { functionId: obligation.functionId }
    );
  const sealedJobs = await Promise.all(jobs.map(sealWorkOrder));
  const sealedGraph = { ...graph, nodes: sealedJobs };
  sealedGraph.digest = await digestObject(
    'successor.job-graph.v1',
    sealedGraph
  );
  const dependencyMap = Object.fromEntries(
    jobs.map((job) => [
      job.jobId,
      graph.edges
        .filter(
          (edge) => edge.to === job.jobId && EXECUTION_EDGES.has(edge.kind)
        )
        .map((edge) => ({ jobId: edge.from, kind: edge.kind })),
    ])
  );
  const invalidationMap = Object.fromEntries(
    [...rights.keys(), ...ids].map((key) => [
      key,
      jobs
        .filter((job) => job.authorizedInputs.includes(key))
        .map((job) => job.jobId),
    ])
  );
  for (const edge of graph.edges.filter((edge) =>
    ['evidence', 'invalidation', 'challenge', 'control'].includes(edge.kind)
  ))
    if (!invalidationMap[edge.from].includes(edge.to))
      invalidationMap[edge.from].push(edge.to);
  return {
    schemaVersion: SCHEMA_VERSION,
    status: 'SEALED',
    mode: mission.proofProtocol.mode,
    constitution: mission,
    graph: sealedGraph,
    executionOrder,
    coverage,
    criticalEvidenceCuts: coverage.map(({ functionId, jobIds }) => ({
      functionId,
      removeJobIds: jobIds,
      exhaustive: false,
    })),
    budgetReservations: {
      unit: mission.budget.unit,
      reservedBaseUnits: reservation.toString(),
      limitBaseUnits: mission.budget.limitBaseUnits,
      includesRetries: true,
    },
    dependencyMap,
    invalidationMap,
    capabilityRequests: jobs.map((job) => ({
      jobId: job.jobId,
      actor: job.actor,
      tools: job.permittedTools,
      actions: job.permittedActions,
      status: 'REQUESTED_NOT_GRANTED',
    })),
    evaluationPlan: cloneJson(mission.proofProtocol),
    authorityCreated: 'NONE',
    signatureStatus: 'UNSIGNED_COMMITMENT',
    digest: await digestObject('successor.constitution.v1', mission),
  };
}

function invalidationClosure(compilation, sourceIds) {
  const pending = [...sourceIds];
  const seen = new Set();
  while (pending.length) {
    const source = pending.shift();
    if (seen.has(source)) continue;
    seen.add(source);
    pending.push(...(compilation.invalidationMap[source] ?? []));
  }
  return [...seen].sort();
}

async function diagnoseMission(mission, options) {
  try {
    return await compileJobs(mission, options);
  } catch (error) {
    if (!(error instanceof SuccessorError)) throw error;
    return {
      status: 'REJECTED',
      diagnostics: [error.toJSON()],
      authorityCreated: 'NONE',
    };
  }
}

return {workOrderPayload,sealWorkOrder,verifyWorkOrderSeal,transitionSealedJob,compileJobs,invalidationClosure,diagnoseMission};
})();
const module_2=(()=>{
// SPDX-License-Identifier: Apache-2.0
const alpha = module_1;
const { compileJobs } = module_3;
const { JOB_TEMPLATES, createPortfolioJobs } = module_6;
const { digestObject } = module_5;

const TOKEN = '0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA';
const DELIVERABLES = [
  'mission.json: count, sum, maximum duration and error count by day and service; zero incorrect totals.',
  'incumbent.json: exact outputs and observed timings for the existing one-pass Map implementation.',
  'alternatives.json: compare the deterministic sort-and-reduce baseline; record that a frontier comparison is missing.',
  'rights.json: synthetic nonpersonal events only; list code licenses and permitted reuse.',
  'gym.json: version the event generator, malformed-input cases, public partitions and zero-error gate.',
  'teacher.json: disclose that this example uses fixed code and no external model or teaching calls.',
  'failures.json: test empty data, invalid numbers, malformed Unicode and unusual service keys.',
  'candidates.json: preserve all four bounded aggregation configurations and rejected attempts.',
  'experience.json: record seeds, workload sizes and generator version; no protected claims.',
  'candidate.json: freeze the selected grammar and engine SHA-256 before comparative evaluation.',
  'tools.json: allow only the fixed aggregation engine; no arbitrary code, browsing or money movement.',
  'verifier.json: reproduce exact outputs and reject invalid inputs; identify missing independent custody.',
  'security.json: confirm no external requests, keys, personal data or wallet approvals are required.',
  'economics.json: record all observed costs; mark compute price, human review and maintenance unmeasured.',
  'roles.json: separate producer, verifier, acceptance owner and admitter; labels are unauthenticated.',
  'rollback.json: retain the baseline and demonstrate clearing the active candidate without external effects.',
  'evaluation.json: compare the frozen candidate with both baselines on six further public workloads.',
  'review.json: obtain a separately attributable review; this browser leaves independent proof absent.',
  'acceptance.json: require evidence against the frozen terms; all work orders remain DRAFT here.',
  'authority.json: retain HOLD with zero grants until separate, scoped, expiring, revocable admission.',
  'renewal.json: propose the next test and preserve lessons; a successor inherits no proof or authority.',
];
const FRENCH_TITLES = [
  'Constitution de mission', 'Référence actuelle', 'Ensemble des alternatives', 'Droits et données',
  'Environnement d’entraînement et protocole comparatif', 'Étude des oracles et des enseignants',
  'Classification des échecs', 'Comparaison des architectures', 'Formation des données et de l’expérience',
  'Formation du modèle spécialisé', 'Outils et recherche documentaire', 'Construction du vérificateur',
  'Sécurité et confidentialité', 'Économie complète', 'Charge humaine et pouvoir de décision',
  'Résilience et retour arrière', 'Évaluation protégée sur données nouvelles', 'Validation indépendante',
  'Acceptation responsable', 'Chronique et admission de l’autorité', 'Capacité financée et requalification',
];
const FRENCH_DELIVERABLES = [
  'mission.json : compter les événements, les erreurs, la durée totale et maximale par jour et service; aucun total incorrect.',
  'incumbent.json : conserver les sorties exactes et les durées de la référence Map en un seul passage.',
  'alternatives.json : comparer la référence déterministe par tri et réduction; signaler l’absence de comparaison avec les meilleures IA.',
  'rights.json : utiliser uniquement des événements fictifs non personnels; préciser les licences et réutilisations permises.',
  'gym.json : versionner le générateur, les entrées mal formées, les jeux publics et le seuil de zéro erreur.',
  'teacher.json : déclarer le code fixe utilisé et l’absence de modèle externe ou d’appel d’enseignement.',
  'failures.json : tester les données vides, nombres invalides, caractères Unicode mal formés et clés de service inhabituelles.',
  'candidates.json : conserver les quatre configurations délimitées et les tentatives rejetées.',
  'experience.json : noter les graines aléatoires, tailles de jeux et version du générateur; aucune preuve protégée.',
  'candidate.json : figer la grammaire retenue et l’empreinte SHA-256 du moteur avant la comparaison.',
  'tools.json : autoriser uniquement le moteur fixe; aucun code arbitraire, navigation ou mouvement de fonds.',
  'verifier.json : reproduire les sorties exactes et rejeter les entrées invalides; signaler l’absence de garde indépendante.',
  'security.json : vérifier l’absence de requêtes externes, clés, données personnelles et autorisations de portefeuille.',
  'economics.json : noter les coûts observés; laisser le prix du calcul, la revue humaine et la maintenance non mesurés.',
  'roles.json : distinguer producteur, vérificateur, responsable de l’acceptation et décideur d’admission; identités non authentifiées.',
  'rollback.json : garder la référence et démontrer l’abandon du candidat actif sans effet externe.',
  'evaluation.json : comparer le candidat figé aux deux références sur six nouveaux jeux publics.',
  'review.json : obtenir une revue attribuable séparément; aucune preuve indépendante n’est créée dans le navigateur.',
  'acceptance.json : exiger des preuves conformes aux termes figés; toutes les tâches restent des brouillons DRAFT.',
  'authority.json : maintenir HOLD et zéro autorisation jusqu’à une admission distincte, limitée, temporaire et révocable.',
  'renewal.json : proposer le prochain test et garder les enseignements; aucun héritage automatique de preuve ou d’autorité.',
];

function missionFor({ name = 'Atlas Ω', budget = '2100', now = new Date().toISOString() } = {}) {
  if (typeof name !== 'string' || !name.trim() || name.length > 48) throw Error('Use a name of 1–48 characters.');
  if (typeof budget !== 'string' || !/^[1-9][0-9]{0,6}$/.test(budget) || BigInt(budget) > 1000000n) {
    throw Error('Use a whole planning allowance from 1 to 1,000,000 AGIALPHA.');
  }
  if (!Number.isFinite(Date.parse(now))) throw Error('A valid clock is required.');
  const expiresAt = new Date(Date.parse(now) + 7 * 86400000).toISOString();
  return {
    schemaVersion: '1.0.0', kind: 'MissionConstitution', missionId: 'streaming-metrics-builder-v1',
    institutionId: 'local-successor-workshop', version: '1', title: name.trim().normalize('NFC'),
    principal: 'example-human-principal', beneficiary: 'Owner of this local synthetic mission',
    objective: 'Produce exact daily service metrics, compare bounded implementations, and prepare reviewable work orders.',
    incumbent: { id: 'alpha-current', version: alpha.VERSION, description: 'Measured one-pass Map baseline.' },
    alternatives: [{ id: 'alpha-beta', version: alpha.VERSION, description: 'Measured deterministic sort-and-reduce baseline; not a frontier AI comparator.' }],
    rights: [{ sourceId: 'synthetic-events', license: 'Apache-2.0 generator; synthetic nonpersonal outputs', dataClass: 'synthetic', permittedUses: ['mission-evaluation', 'fixture-export'], expiresAt }],
    hardGates: [
      { id: 'exact-output', description: 'All grouped counts and durations agree exactly.', maxViolations: 0 },
      { id: 'invalid-input', description: 'Malformed and unsupported records are rejected.', maxViolations: 0 },
      { id: 'no-external-effect', description: 'No network request, live job, payment or authority grant.', maxViolations: 0 },
    ],
    criticalFunctions: JOB_TEMPLATES.map(t => t.coverageKey),
    roles: { producer: 'example-producer', verifier: 'example-verifier', acceptor: 'example-acceptor', admitter: 'example-admitter' },
    budget: { unit: 'AGIALPHA', limitBaseUnits: (BigInt(budget) * 10n ** 18n).toString(), maxDurationMs: 60000, maxRetries: 0, maxJobs: 21 },
    expiresAt,
    authorityCeiling: { level: 'A0', permittedActions: ['inspect-local'], prohibitedActions: ['send-payment', 'post-live-job', 'access-private-data', 'self-admit'], externalEffects: false },
    allowedTools: ['fixed-aggregation-engine'], allowedActions: ['inspect-local'],
    rollback: { target: 'alpha-current', available: true, reason: 'Discard the local candidate and return to the retained fixed baseline.' },
    proofProtocol: { id: 'public-local-rehearsal', version: '1', mode: 'SYNTHETIC_REHEARSAL', formationOwner: 'example-producer', custodian: 'example-verifier', requiredIndependence: 'I0', minimumMargin: 0.05, criticalErrorCeiling: 0, scope: 'Public synthetic cases in one process; no independent proof, mission alpha or operational admission.' },
  };
}

async function compilePlan(options = {}) {
  const mission = missionFor(options);
  const jobs = createPortfolioJobs(mission).map((job, i) => ({
    ...job,
    objective: `${job.objective} Streaming-metrics deliverable: ${DELIVERABLES[i]}`,
    acceptance: { ...job.acceptance, predicate: `${DELIVERABLES[i]} Preserve failures and missing evidence. Separate review is required.` },
  }));
  const dependencies = [[], [0], [0], [0], [1, 2, 3], [4], [4], [1, 2, 5, 6], [3, 4], [7, 8], [9], [4, 6, 10], [10, 11], [1, 2, 9], [0, 13], [10, 12], [9, 11, 12, 13, 14, 15], [16], [17], [18], [19]];
  const edges = dependencies.flatMap((parents, i) => parents.map(j => ({ from: jobs[j].jobId, to: jobs[i].jobId, kind: 'evidence' })));
  for (const edge of edges) jobs.find(job => job.jobId === edge.to).authorizedInputs.push(edge.from);
  return compileJobs(mission, { jobs, edges, now: options.now });
}

async function buildPack(options = {}, { signal, onProgress = () => {} } = {}) {
  const now = options.now || new Date().toISOString();
  const request = alpha.newRequest({ max_events: options.events ?? 1000, seed: options.seed ?? 42, max_candidates: 4, language: options.language ?? 'en' });
  if (!/^[0-9a-f]{64}$/.test(options.engineSourceHash || '')) throw Error('Engine source identity is required.');
  onProgress('compile');
  const compilation = await compilePlan({ ...options, now });
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
  onProgress('discover');
  const discovery = await alpha.discover(request, { signal });
  const frozen = await alpha.freeze(request, discovery, options.engineSourceHash);
  onProgress('evaluate');
  const evaluation = await alpha.evaluate(request, frozen, { signal });
  const record = {
    schema: 'successor-build-example/v1', createdAt: now, title: compilation.constitution.title,
    scope: 'LOCAL_REHEARSAL', request, compilation, discovery, frozen, evaluation,
    token: { symbol: 'AGIALPHA', chainId: 1, address: TOKEN, decimals: 18 },
    settlement: { status: 'NOT_CONNECTED', transactions: [], spentBaseUnits: '0', allowanceIs: 'ILLUSTRATIVE_NOT_FUNDED' },
    admission: { decision: 'HOLD', independentProof: false, authority: [], specialistASI: false },
    chronicle: [{ kind: 'local-observation', candidateRelease: frozen.release_hash, reusable: 'Configuration hypothesis only; rerun tests.', inheritedProof: false, inheritedAuthority: false }],
  };
  return { ...record, integrityDigest: await digestObject('successor-build-example.v1', record) };
}

function jobBriefs(pack) {
  if(pack.request.language==='fr')return `# ${pack.title} — Fiches de construction SUCCESSOR Ω\n\nRÉPÉTITION LOCALE. Brouillons DRAFT, empreintes non signées, zéro dépense.\nPreuve indépendante absente. Admission HOLD. Aucune autorité accordée.\n\nJeton commun sur Ethereum mainnet : ${TOKEN} (AGIALPHA, 18 décimales).\nBudget de planification seulement; frais, mises et gaz à estimer séparément.\n\n` +
    pack.compilation.graph.nodes.map((job,i)=>`## ${i+1}. ${FRENCH_TITLES[i]}\n\n${FRENCH_DELIVERABLES[i]}\n\nTermes canoniques du compilateur (anglais) : ${job.objective}\n\nCritère d’acceptation canonique (anglais) : ${job.acceptance.predicate}\n\nLimite de planification (unités de base AGIALPHA) : ${job.budget.limitBaseUnits}\nExpiration : ${job.expiresAt}\nProducteur : ${job.actor}\nVérificateur : ${job.verifier.identity}\nResponsable de l’acceptation : ${job.acceptance.owner}\nRetour arrière : ${job.rollback.target}\nEmpreinte non signée : ${job.digest}\n`).join('\n') +
    '\nSuite : organiser une évaluation protégée indépendante, mesurer tous les coûts, mettre en service l’intégration puis demander une décision humaine d’admission distincte. Le jeton commun ne relie pas automatiquement les marchés.\n';
  return `# ${pack.title} — SUCCESSOR Ω build briefs\n\nLOCAL REHEARSAL. DRAFT work, unsigned commitments, zero funds spent.\nIndependent proof absent. Admission HOLD. No authority is granted.\n\nShared Ethereum mainnet token: ${TOKEN} (AGIALPHA, 18 decimals).\nPlanning allowance only; fees, stakes and gas require separate estimates before commissioning.\n\n` +
    pack.compilation.graph.nodes.map((job, i) => `## ${i + 1}. ${JOB_TEMPLATES[i].title}\n\n${job.objective}\n\nAcceptance: ${job.acceptance.predicate}\n\nPlanning limit (AGIALPHA base units): ${job.budget.limitBaseUnits}\nExpiry: ${job.expiresAt}\nProducer: ${job.actor}\nVerifier: ${job.verifier.identity}\nAcceptance owner: ${job.acceptance.owner}\nRollback: ${job.rollback.target}\nUnsigned commitment: ${job.digest}\n`).join('\n') +
    '\nNext: arrange independent protected evaluation, measure full costs, resolve commissioning, then request a separate human admission decision. Sharing the token does not bridge the two markets.\n';
}

return {TOKEN,DELIVERABLES,FRENCH_TITLES,FRENCH_DELIVERABLES,missionFor,compilePlan,buildPack,jobBriefs};
})();
const module_0=(()=>{
// SPDX-License-Identifier: Apache-2.0
const { canonical, digest, parseBounded } = module_1;
const { missionFor } = module_2;
const { compileJobs } = module_3;
const { createPortfolioJobs } = module_6;

const VERSION = 'successor-workbench/v1';
const REGISTRY = Object.freeze([
  { id: 'reliability', en: 'Repair a range utility', fr: 'Réparer un utilitaire', artifact: 'repair.patch', scope: 'Closed interval utilities in the documented finite source grammar.' },
  { id: 'performance', en: 'Compare real algorithms', fr: 'Comparer des algorithmes', artifact: 'benchmark.json', scope: 'Exact sorted unique integer values; sort/reduce versus Set/sort.' },
  { id: 'documentation', en: 'Check executable examples', fr: 'Vérifier des exemples exécutables', artifact: 'checked-examples.md', scope: 'Named URI and UTF-8 SDK operations in bounded JSON examples.' },
  { id: 'public-data', en: 'Turn data into a report', fr: 'Transformer des données en rapport', artifact: 'report.html', scope: 'Public or synthetic two-column CSV with exact integer amounts.' },
  { id: 'numerical', en: 'Reproduce a calculation', fr: 'Reproduire un calcul', artifact: 'numerical.json', scope: 'Polynomial integration using exact rational arithmetic and two quadrature rules.' },
]);

const clone = value => parseBounded(canonical(value));
function fields(value, keys, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).sort().join('|') !== [...keys].sort().join('|')) throw Error(`SCHEMA: ${label}`);
}
function integer(value, low, high, label) {
  if (!Number.isSafeInteger(value) || value < low || value > high) throw Error(`BOUNDS: ${label}`);
}
function text(value, maximum, label) {
  if (typeof value !== 'string' || !value.trim() || value.length > maximum) throw Error(`TEXT: ${label}`);
}
function html(value) { return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char])); }
function file(name, type, content) { return { name, type, content }; }
function jsonFile(name, object) { return file(name, 'application/json', JSON.stringify(object, null, 2) + '\n'); }

function example(family = 'reliability') {
  const inputs = {
    reliability: { source: 'export function contains(value, low, high) { return low < value && value < high; }', low: 0, high: 10, cases: [-1, 0, 1, 5, 9, 10, 11] },
    performance: { values: [8, 3, 8, 1, 0, -3, 3, 12, 0, 7], repetitions: 7, repeats: 100 },
    documentation: { markdown: '# URI helper examples\n\n```successor-example\n{"operation":"url-encode","input":"hello world","expected":"hello+world"}\n```\n\n```successor-example\n{"operation":"url-decode","input":"hello%20world","expected":"hello world"}\n```\n' },
    'public-data': { csv: 'group,amount\nResearch,120\nSoftware,85\nResearch,35\nDocumentation,60\nSoftware,-5\n', unit: 'synthetic units' },
    numerical: { coefficients: [0, 0, 1], lower: 0, upper: 3, steps: 12, tolerancePpm: 1 },
  };
  if (!Object.hasOwn(inputs, family)) throw Error('UNSUPPORTED_FAMILY');
  return { schema: VERSION, family, name: 'My SUCCESSOR Ω', language: 'en', owner: 'local-owner',
    rights: { dataClass: 'synthetic', source: 'Included public example', license: 'Apache-2.0' },
    reviewMinutes: 10, inputs: clone(inputs[family]) };
}

function validate(spec, adapter = null) {
  fields(spec, ['schema','family','name','language','owner','rights','reviewMinutes','inputs'], 'mission');
  if (spec.schema !== VERSION || !(REGISTRY.some(item => item.id === spec.family) || adapter?.manifest.id === spec.family)) throw Error('UNSUPPORTED_VERSION_OR_FAMILY');
  text(spec.name, 64, 'name'); text(spec.owner, 128, 'owner');
  if (!['en','fr'].includes(spec.language)) throw Error('LANGUAGE');
  fields(spec.rights, ['dataClass','source','license'], 'rights');
  if (!['public','licensed-nonpersonal','synthetic'].includes(spec.rights.dataClass)) throw Error('INPUT_RIGHTS');
  text(spec.rights.source, 1000, 'source'); text(spec.rights.license, 1000, 'license');
  integer(spec.reviewMinutes, 1, 120, 'review capacity');
  const value = spec.inputs;
  if (adapter) {
    adapter.validate(clone(value));
  } else if (spec.family === 'reliability') {
    fields(value, ['source','low','high','cases'], 'reliability input');
    text(value.source, 2000, 'source'); rangeProgram(value.source);
    integer(value.low, -1000000, 1000000, 'low'); integer(value.high, value.low, 1000000, 'high');
    if (!Array.isArray(value.cases) || value.cases.length < 1 || value.cases.length > 2000) throw Error('CASES');
    value.cases.forEach(n => integer(n, -1000001, 1000001, 'case'));
  } else if (spec.family === 'performance') {
    fields(value, ['values','repetitions','repeats'], 'performance input');
    if (!Array.isArray(value.values) || value.values.length < 1 || value.values.length > 2000) throw Error('VALUES');
    value.values.forEach(n => integer(n, -1000000, 1000000, 'value'));
    integer(value.repetitions, 3, 15, 'repetitions'); integer(value.repeats, 1, 500, 'repeats');
  } else if (spec.family === 'documentation') {
    fields(value, ['markdown'], 'documentation input'); text(value.markdown, 100000, 'markdown');
    const matches = [...value.markdown.matchAll(/```successor-example\s*\n([\s\S]*?)\n```/g)];
    if (!matches.length || matches.length > 40) throw Error('EXAMPLES: use 1–40 successor-example JSON blocks');
    for (const match of matches) validateDocExample(parseBounded(match[1]));
  } else if (spec.family === 'public-data') {
    fields(value, ['csv','unit'], 'data input'); text(value.csv, 100000, 'csv'); text(value.unit, 80, 'unit');
    readRows(value.csv);
  } else {
    fields(value, ['coefficients','lower','upper','steps','tolerancePpm'], 'numerical input');
    if (!Array.isArray(value.coefficients) || !value.coefficients.length || value.coefficients.length > 7) throw Error('COEFFICIENTS');
    value.coefficients.forEach(n => integer(n, -1000, 1000, 'coefficient'));
    integer(value.lower, -100, 99, 'lower'); integer(value.upper, value.lower + 1, 100, 'upper');
    integer(value.steps, 2, 1000, 'steps'); if (value.steps % 2) throw Error('EVEN_STEPS_REQUIRED');
    integer(value.tolerancePpm, 0, 1000000, 'absolute tolerance in millionths');
  }
  canonical(spec);
  return clone(spec);
}

async function semanticIdentity(spec, adapter = null) {
  const { name, language, ...semantic } = validate(spec, adapter);
  return digest('workbench-mission', semantic);
}

function rangeProgram(source) {
  const match = /^\s*export\s+function\s+contains\s*\(\s*value\s*,\s*low\s*,\s*high\s*\)\s*\{\s*return\s+low\s*(<=|<)\s*value\s*&&\s*value\s*(<=|<)\s*high\s*;\s*\}\s*$/.exec(source);
  if (!match) throw Error('SOURCE_GRAMMAR: only the documented bounded contains function is supported');
  return { lower: match[1], upper: match[2], execute: (value, low, high) =>
    (match[1] === '<=' ? low <= value : low < value) && (match[2] === '<=' ? value <= high : value < high) };
}
async function reliability(input, checkpoint) {
  const incumbent = rangeProgram(input.source);
  const cases = [...new Set([...input.cases, input.low - 1, input.low, input.high, input.high + 1])];
  const tests = cases.map(value => ({value, expected: value >= input.low && value <= input.high,
    actual: incumbent.execute(value, input.low, input.high)}));
  const attempts = [];
  for (const lower of ['<','<=']) for (const upper of ['<','<=']) {
    await checkpoint('testing');
    const source = `export function contains(value, low, high) { return low ${lower} value && value ${upper} high; }`;
    const method = rangeProgram(source);
    const failed = cases.filter(value => method.execute(value, input.low, input.high) !== (value >= input.low && value <= input.high));
    attempts.push({source, failed});
  }
  const selected = attempts.find(item => item.failed.length === 0);
  const defects = tests.filter(item => item.expected !== item.actual);
  const candidate = selected.source;
  const originalLines=input.source.trim().split(/\r?\n/);
  const patch = `--- a/contains.mjs\n+++ b/contains.mjs\n@@ -1,${originalLines.length} +1 @@\n${originalLines.map(line=>'-'+line).join('\n')}\n+${candidate}\n`;
  const checks = `// SPDX-License-Identifier: Apache-2.0\nimport assert from 'node:assert/strict';\nimport { contains } from './contains.mjs';\nfor (const c of ${JSON.stringify(tests.map(({value,expected})=>({value,expected})))}) assert.equal(contains(c.value, ${input.low}, ${input.high}), c.expected);\nconsole.log('All ${tests.length} fixed contract checks passed');\n`;
  return { decision: defects.length ? 'REPAIR_PROPOSED' : 'RETAIN_INCUMBENT', summary: {tests: tests.length, defects: defects.length, candidateFailures: 0},
    evidence: {tests, attempts, protectedCases: false, execution: 'Finite source grammar interpreted without eval or arbitrary host execution'},
    artifacts: [file('contains.mjs','text/javascript',candidate+'\n'), file('original.mjs','text/javascript',input.source+'\n'),
      file('check.mjs','text/javascript',checks),file('repair.patch','text/plain',defects.length ? patch : '# No repair needed.\n'),jsonFile('tests.json',tests)],
    limits: ['This adapter supports the declared range utility grammar only; arbitrary repositories need a separately isolated executor.', 'Public contract tests are engineering evidence, not independently protected qualification.'] };
}

async function performanceWork(input, checkpoint) {
  const sortUnique = values => values.slice().sort((a,b)=>a-b).filter((n,i,a)=>i===0 || n!==a[i-1]);
  const setUnique = values => [...new Set(values)].sort((a,b)=>a-b);
  const expected = sortUnique(input.values);
  const samples = { sort: [], set: [] };
  for (let r=0;r<input.repetitions;r++) {
    for (const name of (r%2 ? ['set','sort'] : ['sort','set'])) {
      await checkpoint('benchmarking');
      const fn = name==='sort' ? sortUnique : setUnique;
      const start = globalThis.performance.now(); let actual;
      for (let i=0;i<input.repeats;i++) actual=fn(input.values);
      samples[name].push(Math.max(0,Math.round((globalThis.performance.now()-start)*1000)));
      if (canonical(actual)!==canonical(expected)) throw Error('CRITICAL_CORRECTNESS_FAILURE');
    }
  }
  const median = values => [...values].sort((a,b)=>a-b)[Math.floor(values.length/2)];
  const selected = median(samples.set) < median(samples.sort) ? 'set' : 'sort';
  const report = { samplesMicrosecondsPerBatch: samples, batchRepeats: input.repeats,
    medianMicroseconds: {sort: median(samples.sort),set: median(samples.set)}, selected, output: expected,
    resourceTradeoff: 'Set retains a hash table and a unique-value array; sort copies and sorts all input values. Peak memory is not measured.' };
  return {decision: selected==='sort'?'RETAIN_INCUMBENT':'CANDIDATE_FASTER_IN_THIS_RUN',summary:{inputCount:input.values.length,outputCount:expected.length,correct:true},
    evidence:report,artifacts:[jsonFile('benchmark.json',report),jsonFile('values.json',input.values),
      file('unique.mjs','text/javascript',`// SPDX-License-Identifier: Apache-2.0\nexport const unique = ${selected==='set' ? "values => [...new Set(values)].sort((a,b)=>a-b)" : "values => values.slice().sort((a,b)=>a-b).filter((n,i,a)=>i===0 || n!==a[i-1])"};\n`)],
    limits:['Device/JIT/order effects can dominate small timings. This result does not establish general superiority.', 'Peak memory, monetary cost and human savings are unmeasured.']};
}

function validateDocExample(value) {
  fields(value,['operation','input','expected'],'documentation example');
  if (!['url-encode','url-decode','utf8-bytes'].includes(value.operation)) throw Error('UNSUPPORTED_SDK_OPERATION');
  if (typeof value.input!=='string' || value.input.length>4000 || typeof value.expected!=='string') throw Error('SDK_INPUT');
}
function sdk(value) {
  if(value.operation==='url-encode')return encodeURIComponent(value.input);
  if(value.operation==='url-decode')return decodeURIComponent(value.input);
  return String(new TextEncoder().encode(value.input).length);
}
async function documentation(input, checkpoint) {
  const checks=[]; let offset=0; let repaired='';
  for (const match of input.markdown.matchAll(/```successor-example\s*\n([\s\S]*?)\n```/g)) {
    await checkpoint('checking-examples');
    const value=parseBounded(match[1]); let actual=null,error=null;
    try { actual=sdk(value); } catch { error='INVALID_URI_ENCODING'; }
    checks.push({index:checks.length+1,...value,actual,error,passed:error===null&&actual===value.expected});
    repaired+=input.markdown.slice(offset,match.index)+(error ? match[0] : '```successor-example\n'+JSON.stringify({...value,expected:actual})+'\n```');
    offset=match.index+match[0].length;
  }
  repaired+=input.markdown.slice(offset);
  const failures=checks.filter(c=>!c.passed), errors=checks.filter(c=>c.error);
  return {decision:errors.length?'REPAIR_REQUIRED':failures.length?'DOCUMENTATION_CORRECTION_PROPOSED':'RETAIN_INCUMBENT',
    summary:{examples:checks.length,incorrectExamples:failures.length,invalidInputs:errors.length},evidence:{checks,contract:'URI component encoding/decoding and UTF-8 byte count; actual standard-library execution'},
    artifacts:[file('original-examples.md','text/markdown',input.markdown),file('checked-examples.md','text/markdown',repaired),jsonFile('example-checks.json',checks)],
    limits:['Only the named SDK operations run. Markdown outside the example blocks remains inert.', 'Proposed expected-value corrections require review; original failures remain in the evidence.']};
}

function readRows(csv) {
  const lines=[]; let row=[],cell='',quoted=false,closed=false;
  for(let i=0;i<csv.length;i++) {
    const ch=csv[i];
    if(quoted){if(ch==='"'){if(csv[i+1]==='"'){cell+='"';i++;}else{quoted=false;closed=true;}}else cell+=ch;}
    else if(ch==='"'&&!cell&&!closed)quoted=true;
    else if(ch===','){row.push(cell);cell='';closed=false;}
    else if(ch==='\n'||ch==='\r'){if(ch==='\r'&&csv[i+1]==='\n')i++;row.push(cell);lines.push(row);row=[];cell='';closed=false;}
    else{if(closed||ch==='"')throw Error('CSV_QUOTING');cell+=ch;}
    if(lines.length>2001)throw Error('CSV_ROW_LIMIT');
  }
  if(quoted)throw Error('CSV_UNCLOSED_QUOTE');
  if(row.length||cell||closed){row.push(cell);lines.push(row);}
  if(canonical(lines.shift())!==canonical(['group','amount'])||!lines.length)throw Error('CSV_HEADER: group,amount');
  return lines.map((item,index)=>{
    if(item.length!==2||!item[0].trim()||item[0].length>100||!/^[-]?(0|[1-9][0-9]{0,8})$/.test(item[1]))throw Error(`CSV_ROW: ${index+2}`);
    const amount=Number(item[1]); integer(amount,-1000000,1000000,'amount');
    return {group:item[0],amount};
  });
}
function csvCell(value) { const raw=String(value);return '"'+(/^[=+\-@\t\r]/.test(raw)?"'"+raw:raw).replaceAll('"','""')+'"'; }
async function publicData(input, checkpoint) {
  const rows=readRows(input.csv), groups=new Map();
  for(const row of rows){await checkpoint('analysing');const old=groups.get(row.group)||{group:row.group,count:0,total:0,min:row.amount,max:row.amount};old.count++;old.total+=row.amount;old.min=Math.min(old.min,row.amount);old.max=Math.max(old.max,row.amount);groups.set(row.group,old);}
  const summary=[...groups.values()].sort((a,b)=>a.group<b.group?-1:a.group>b.group?1:0);
  const total=rows.reduce((sum,row)=>sum+row.amount,0);
  if(summary.reduce((sum,row)=>sum+row.total,0)!==total)throw Error('RECONCILIATION_FAILED');
  const report='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SUCCESSOR data report</title><style>body{font:18px system-ui;max-width:60rem;margin:3rem auto;padding:1rem}td,th{padding:.6rem;text-align:left;border-bottom:1px solid #aaa}table{border-collapse:collapse}</style><h1>Public-data report</h1><p>'+html(rows.length)+' rows · '+html(input.unit)+' · exact total '+html(total)+'</p><table><thead><tr><th>Group</th><th>Count</th><th>Total</th><th>Minimum</th><th>Maximum</th></tr></thead><tbody>'+summary.map(row=>'<tr>'+[row.group,row.count,row.total,row.min,row.max].map(v=>'<td>'+html(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table><p>Descriptive results for the supplied data only. Coverage and causal interpretation require review.</p></html>';
  return {decision:'REPORT_READY_FOR_REVIEW',summary:{rows:rows.length,groups:summary.length,total,unit:input.unit},evidence:{groups:summary,reconciled:true},
    artifacts:[file('report.html','text/html',report),file('summary.csv','text/csv','group,count,total,min,max\n'+summary.map(row=>[csvCell(row.group),row.count,row.total,row.min,row.max].join(',')).join('\n')+'\n'),jsonFile('analysis.json',{total,groups:summary})],
    limits:['Exact descriptive arithmetic does not establish population coverage or causality.', 'CSV labels are escaped against formula interpretation; the source remains in the mission specification.']};
}

function fraction(n,d=1n){if(d===0n)throw Error('ZERO_DENOMINATOR');if(d<0n){n=-n;d=-d;}let a=n<0n?-n:n,b=d;while(b){const c=a%b;a=b;b=c;}return [n/(a||1n),d/(a||1n)];}
function add(a,b){return fraction(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);}
function mul(a,b){return fraction(a[0]*b[0],a[1]*b[1]);}
function abs(a){return [a[0]<0n?-a[0]:a[0],a[1]];}
function rationalText(a){return `${a[0]}/${a[1]}`;}
function polynomial(coefficients,x){let result=[0n,1n];for(const c of [...coefficients].reverse())result=add(mul(result,x),[BigInt(c),1n]);return result;}
async function numerical(input,checkpoint){
  const h=fraction(BigInt(input.upper-input.lower),BigInt(input.steps));let trap=[0n,1n],simpson=[0n,1n];
  for(let i=0;i<=input.steps;i++){await checkpoint('integrating');const y=polynomial(input.coefficients,add([BigInt(input.lower),1n],mul(h,[BigInt(i),1n])));trap=add(trap,mul(y,[i===0||i===input.steps?1n:2n,1n]));simpson=add(simpson,mul(y,[i===0||i===input.steps?1n:i%2?4n:2n,1n]));}
  trap=mul(trap,mul(h,[1n,2n]));simpson=mul(simpson,mul(h,[1n,3n]));
  let exact=[0n,1n];input.coefficients.forEach((c,i)=>{const n=BigInt(i+1);exact=add(exact,fraction(BigInt(c)*(BigInt(input.upper)**n-BigInt(input.lower)**n),n));});
  const error=value=>abs(add(value,[-exact[0],exact[1]]));const tolerance=fraction(BigInt(input.tolerancePpm),1000000n);
  const passes=value=>{const e=error(value);return e[0]*tolerance[1]<=tolerance[0]*e[1];};
  const evidence={analytic:rationalText(exact),trapezoid:rationalText(trap),simpson:rationalText(simpson),
    absoluteErrors:{trapezoid:rationalText(error(trap)),simpson:rationalText(error(simpson))},absoluteTolerance:rationalText(tolerance),
    passes:{trapezoid:passes(trap),simpson:passes(simpson)},arithmetic:'Exact reduced BigInt rational numbers; coefficients in increasing powers'};
  return {decision:passes(simpson)?'WITHIN_DECLARED_TOLERANCE':'REPAIR_REQUIRED',summary:{steps:input.steps,degree:input.coefficients.length-1,...evidence.passes},
    evidence,artifacts:[jsonFile('numerical.json',evidence),jsonFile('calculation-input.json',input)],
    limits:['This reconstructs polynomial quadrature under stated assumptions, not an arbitrary scientific paper.', 'Input uncertainty, physical-model validity and external replication are unmeasured.']};
}

const HANDLERS = {reliability,performance:performanceWork,documentation,'public-data':publicData,numerical};

async function plan(spec, now = new Date().toISOString(), adapter = null) {
  const checked=validate(spec,adapter), identity=await semanticIdentity(checked,adapter);
  const mission=missionFor({name:checked.name,budget:'1',now});
  mission.missionId='work-'+identity.slice(0,24); mission.title=checked.name;
  mission.objective=(adapter?.manifest || REGISTRY.find(item=>item.id===checked.family)).scope;
  mission.budget.limitBaseUnits='0';mission.budget.maxJobs=7;
  mission.proofProtocol.minimumMargin=0;
  mission.allowedTools=['fixed-workbench-'+checked.family];
  mission.rights[0].dataClass=checked.rights.dataClass==='synthetic'?'synthetic':'public-licensed-nonpersonal';
  mission.rights[0].license=checked.rights.license;mission.rights[0].sourceId='mission-input';
  const proposed=createPortfolioJobs(mission), grouped=new Map();
  for(const job of proposed){if(!grouped.has(job.family))grouped.set(job.family,[]);grouped.get(job.family).push(job);}
  const jobs=[...grouped.entries()].map(([family,items])=>({...items[0],jobId:mission.missionId+':'+family,
    objective:items.map(item=>item.objective).join(' '),covers:items.flatMap(item=>item.covers),
    acceptance:{...items[0].acceptance,predicate:'Review the exact input, delivered artifacts and retained failures for: '+items.map(item=>item.objective).join(' ')}}));
  const order=['constitution','evidence','formation','challenge','verification','admission','renewal'];
  jobs.sort((a,b)=>order.indexOf(a.family)-order.indexOf(b.family));
  const edges=jobs.slice(1).map((job,i)=>({from:jobs[i].jobId,to:job.jobId,kind:'evidence'}));
  for(const edge of edges)jobs.find(job=>job.jobId===edge.to).authorizedInputs.push(edge.from);
  return compileJobs(mission,{jobs,edges,now});
}

async function run(spec, {sourceHash,signal,onProgress=()=>{},onCheckpoint=async()=>{},clock=()=>globalThis.performance.now(),adapter=null}={}) {
  const input=validate(spec,adapter);
  if(!/^[a-f0-9]{64}$/.test(sourceHash||''))throw Error('SOURCE_IDENTITY_REQUIRED');
  const started=clock();let count=0;
  const checkpoint=async phase=>{
    await onCheckpoint();
    if(signal?.aborted)throw Error('CANCELLED');
    if(clock()-started>60000)throw Error('TIME_BUDGET_EXCEEDED');
    if(count++%25===0){onProgress(phase);await new Promise(resolve=>setTimeout(resolve,0));}
  };
  await checkpoint('planning');
  const missionDigest=await semanticIdentity(input,adapter), createdAt=new Date().toISOString();
  const frozen={schema:VERSION,missionDigest,sourceHash,adapter:input.family,adapterVersion:adapter?.manifest.version || 1,
    model:null,provider:null,authority:[],inputPolicy:input.rights,reviewMinutes:input.reviewMinutes};
  const releaseDigest=await digest('workbench-release',frozen);
  const compilation=await plan(input,createdAt,adapter);
  const result=await (adapter?.execute || HANDLERS[input.family])(input.inputs,checkpoint);
  fields(result,['decision','summary','evidence','artifacts','limits'],'adapter output');
  text(result.decision,128,'decision');
  if(!Array.isArray(result.artifacts)||result.artifacts.length<1||result.artifacts.length>12)throw Error('ARTIFACT_COUNT');
  await checkpoint('verifying');
  const artifacts=await Promise.all(result.artifacts.map(async artifact=>({...artifact,digest:await digest('workbench-artifact',artifact)})));
  const body={schema:VERSION,spec:input,createdAt,frozen,releaseDigest,compilation,result:{...result,artifacts},
    economics:{elapsedMilliseconds:Math.max(0,Math.round(clock()-started)),providerSpendBaseUnits:'0',settlementSpendBaseUnits:'0',
      computeCost:null,humanMinutes:null,reviewCapacityMinutes:input.reviewMinutes,allowanceIs:'UNFUNDED'},
    evaluation:{scope:'PUBLIC_LOCAL_EXECUTION',independentProof:false,admission:'HOLD',authority:[],settlement:'NOT_CONNECTED'},
    chronicle:[{kind:'local-result',decision:result.decision,missionDigest,releaseDigest,inheritedProof:false,inheritedAuthority:false}]};
  const pack={...body,integrityDigest:await digest('workbench-pack',body)};
  await inspectPack(pack,adapter);
  return pack;
}

async function inspectPack(value, adapter = null) {
  fields(value,['schema','spec','createdAt','frozen','releaseDigest','compilation','result','economics','evaluation','chronicle','integrityDigest'],'pack');
  validate(value.spec,adapter);
  const {integrityDigest,...body}=value;
  if(integrityDigest!==await digest('workbench-pack',body))throw Error('PACK_INTEGRITY');
  if(value.frozen.missionDigest!==await semanticIdentity(value.spec,adapter)||value.releaseDigest!==await digest('workbench-release',value.frozen))throw Error('PACK_BINDING');
  if(!Array.isArray(value.result.artifacts)||value.result.artifacts.length>12)throw Error('PACK_ARTIFACTS');
  for(const artifact of value.result.artifacts){fields(artifact,['name','type','content','digest'],'artifact');
    if(['mission.json','evidence.json','READ_ME.txt','lifecycle.json','signed-receipt.json','source-key.txt'].includes(artifact.name)||
       /^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\.|$)/i.test(artifact.name)||artifact.name.endsWith('.'))throw Error('RESERVED_ARTIFACT_NAME');
    if(!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$/.test(artifact.name)||!['text/javascript','text/plain','text/csv','text/html','text/markdown','application/json'].includes(artifact.type)||typeof artifact.content!=='string'||artifact.content.length>200000)throw Error('ARTIFACT_POLICY');
    const {digest:hash,...content}=artifact;if(hash!==await digest('workbench-artifact',content))throw Error('ARTIFACT_INTEGRITY');}
  if(new Set(value.result.artifacts.map(item=>item.name)).size!==value.result.artifacts.length)throw Error('DUPLICATE_ARTIFACT');
  if(canonical(value.compilation)!==canonical(await plan(value.spec,value.createdAt,adapter)))throw Error('JOB_BINDING');
  return {spec:clone(value.spec),history:{missionDigest:value.frozen.missionDigest,releaseDigest:value.releaseDigest,decision:value.result.decision},
    authentication:'UNAUTHENTICATED_HISTORICAL_IMPORT',activeProof:[],activeAuthority:[]};
}

function createWorkbench(adapters = []) {
  const installed = new Map();
  for(const adapter of adapters){
    fields(adapter,['manifest','validate','execute'],'installed adapter');
    const manifest=adapter.manifest;
    fields(manifest,['id','version','en','fr','scope','artifact'],'adapter manifest');
    if(!/^[a-z][a-z0-9-]{1,47}$/.test(manifest.id)||REGISTRY.some(item=>item.id===manifest.id)||installed.has(manifest.id))throw Error('ADAPTER_ID');
    integer(manifest.version,1,1000000,'adapter version');
    for(const key of ['en','fr','scope','artifact'])text(manifest[key],1000,key);
    if(typeof adapter.validate!=='function'||typeof adapter.execute!=='function')throw Error('ADAPTER_INTERFACE');
    installed.set(manifest.id,Object.freeze({...adapter,manifest:Object.freeze(clone(manifest))}));
  }
  const resolve=spec=>installed.get(spec.family)||null;
  return Object.freeze({registry:Object.freeze([...REGISTRY,...[...installed.values()].map(item=>item.manifest)]),
    validate:spec=>validate(spec,resolve(spec)),
    run:(spec,options)=>run(spec,{...options,adapter:resolve(spec)}),
    plan:(spec,now)=>plan(spec,now,resolve(spec)),
    inspectPack:pack=>inspectPack(pack,resolve(pack.spec))});
}

return {VERSION,REGISTRY,example,validate,semanticIdentity,plan,run,inspectPack,createWorkbench};
})();
const module_8=(()=>{
// SPDX-License-Identifier: Apache-2.0
const THERMAL_SCHEMA = 'thermal-witness/v1';
const INHERITED_FOUNDRY_FAILURE = Object.freeze({
  status: 'RETAINED_UNDETECTED_FAILURE',
  release: 'study-foundry-v2-2026-10-22-r1',
  predictedHeatJ: '5175.8646948056885',
  commandFlowCalorimeterHeatJ: '5445.281559253128',
  independentReferenceHeatJ: '5009.6244576737745',
  runtimeRelativeResidual: '0.049477122810963045',
  trueRelativeHeatError: '0.08696402400224054',
  scope: 'Historical simulated result; a new witness run does not rewrite or qualify it.',
});

function fields(value, keys, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('SCHEMA: ' + label);
  const proto = Object.getPrototypeOf(value);
  if (proto !== Object.prototype && proto !== null) throw Error('SCHEMA: ' + label);
  const actual = Reflect.ownKeys(value);
  if (actual.length !== keys.length || actual.some(key => typeof key !== 'string')) throw Error('SCHEMA: ' + label);
  actual.sort();
  const expected = [...keys].sort();
  if (actual.some((key, index) => key !== expected[index])) throw Error('SCHEMA: ' + label);
  for (const key of actual) {
    const d = Object.getOwnPropertyDescriptor(value, key);
    if (!d.enumerable || !Object.hasOwn(d, 'value')) throw Error('DATA_REQUIRED: ' + label);
  }
}
function integer(value, low, high, label) {
  if (!Number.isSafeInteger(value) || Object.is(value, -0) || value < low || value > high) {
    throw Error('BOUNDS: ' + label);
  }
}
function text(value, label) {
  if (typeof value !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9:._-]{0,95}$/.test(value)) {
    throw Error('IDENTITY: ' + label);
  }
}
function decimal(value, label) {
  if (typeof value !== 'string' || !/^(0|[1-9][0-9]{0,23})$/.test(value)) throw Error('DECIMAL: ' + label);
  return BigInt(value);
}
function band(value, maximum, label) {
  fields(value, ['low', 'estimate', 'high'], label);
  integer(value.low, 0, maximum, label);
  integer(value.estimate, value.low, maximum, label);
  integer(value.high, value.estimate, maximum, label);
}
function energyBand(value, label) {
  fields(value, ['low', 'estimate', 'high'], label);
  const a = decimal(value.low, label), b = decimal(value.estimate, label), c = decimal(value.high, label);
  if (a > b || b > c) throw Error('ORDER: ' + label);
}
function witness(value, kinds, label) {
  fields(value, ['sourceId', 'kind'], label);
  text(value.sourceId, label);
  if (!kinds.includes(value.kind)) throw Error('WITNESS: ' + label);
}
function validateThermalInput(input) {
  fields(input, ['schema', 'family', 'measurement', 'policy', 'extension', 'maxWorkUnits'], 'thermal input');
  if (input.schema !== THERMAL_SCHEMA ||
      !['delivered-heat', 'heat-capacity', 'heat-recovery'].includes(input.family)) throw Error('UNSUPPORTED_THERMAL_SCHEMA');
  integer(input.maxWorkUnits, 1, 960, 'work units');
  fields(input.policy, ['maxRelativeErrorPpm', 'minimumHeatMicroJ'], 'fixed policy');
  integer(input.policy.maxRelativeErrorPpm, 1, 50000, 'accuracy policy, at most 5 percent');
  decimal(input.policy.minimumHeatMicroJ, 'minimum heat');
  const m = input.measurement;
  fields(m, ['mode', 'coverage', 'propertyModel', 'commandSourceId', 'volumeWitness', 'temperatureWitness',
    'densityKgPerM3', 'specificHeatJPerKgK', 'windowMs', 'intervals'], 'measurement');
  if (m.mode !== 'SIMULATED_MEASUREMENTS' ||
      !['WHOLE_FLOW_DECLARED_BOUNDS', 'UNKNOWN'].includes(m.coverage) ||
      !['CONSTANT_WITHIN_INTERVAL', 'VARIABLE_OR_UNKNOWN'].includes(m.propertyModel)) throw Error('MEASUREMENT_MODE');
  text(m.commandSourceId, 'command source');
  witness(m.volumeWitness, ['INDEPENDENT_SIMULATED', 'COMMAND_DERIVED', 'ABSENT'], 'volume witness');
  witness(m.temperatureWitness, ['BOUNDED_SIMULATED', 'UNBOUNDED'], 'temperature witness');
  band(m.densityKgPerM3, 5000, 'density');
  band(m.specificHeatJPerKgK, 20000, 'specific heat');
  if (m.densityKgPerM3.low === 0 || m.specificHeatJPerKgK.low === 0) throw Error('POSITIVE_MATERIAL_PROPERTIES');
  integer(m.windowMs, 1, 3600000, 'window');
  if (!Array.isArray(m.intervals) || m.intervals.length < 1 || m.intervals.length > 960 ||
      Reflect.ownKeys(m.intervals).length !== m.intervals.length + 1) throw Error('INTERVAL_COUNT');
  let next = 0;
  for (let i = 0; i < m.intervals.length; i++) {
    const d = Object.getOwnPropertyDescriptor(m.intervals, String(i));
    if (!d || !Object.hasOwn(d, 'value')) throw Error('INTERVAL_DATA_REQUIRED');
    const v = d.value;
    fields(v, ['sequence', 'startMs', 'durationMs', 'commandFlowNLPerMin', 'volumeNL',
      'volumeUncertaintyNL', 'deltaTemperatureUK', 'deltaTemperatureUncertaintyUK'], 'interval');
    integer(v.sequence, i, i, 'sequence');
    integer(v.startMs, next, next, 'contiguous coverage');
    integer(v.durationMs, 1, 60000, 'duration');
    integer(v.commandFlowNLPerMin, 0, 200000000, 'command flow');
    integer(v.volumeNL, 0, 1000000000, 'volume');
    integer(v.volumeUncertaintyNL, 0, v.volumeNL, 'volume uncertainty');
    integer(v.deltaTemperatureUK, -30000000, 30000000, 'differential temperature');
    integer(v.deltaTemperatureUncertaintyUK, 0, 5000000, 'temperature uncertainty');
    next += v.durationMs;
  }
  if (next !== m.windowMs) throw Error('INCOMPLETE_WINDOW');
  const e = input.extension;
  if (input.family === 'delivered-heat') fields(e, [], 'heat extension');
  else {
    fields(e, input.family === 'heat-capacity'
      ? ['sourceId', 'kind', 'temperatureRiseUK', 'lossEnergyMicroJ', 'containerEnergyMicroJ']
      : ['sourceId', 'kind', 'inputEnergyMicroJ', 'storageReleaseMicroJ', 'minimumRecoveryPpm'], 'extension');
    text(e.sourceId, 'extension source');
    if (!['INDEPENDENT_SIMULATED', 'COMMAND_DERIVED', 'ABSENT'].includes(e.kind)) throw Error('EXTENSION_WITNESS');
    if (input.family === 'heat-capacity') {
      band(e.temperatureRiseUK, 100000000, 'sample temperature rise');
      energyBand(e.lossEnergyMicroJ, 'loss energy');
      energyBand(e.containerEnergyMicroJ, 'container energy');
    } else {
      energyBand(e.inputEnergyMicroJ, 'input energy');
      energyBand(e.storageReleaseMicroJ, 'storage release');
      integer(e.minimumRecoveryPpm, 0, 1000000, 'minimum recovery');
    }
  }
  return input;
}
function floor(n, d) { const q = n / d; return n < 0n && n % d !== 0n ? q - 1n : q; }
function ceil(n, d) { return -floor(-n, d); }
function round(n, d) { return n < 0n ? -round(-n, d) : (2n * n + d) / (2n * d); }
function abs(n) { return n < 0n ? -n : n; }
function min(values) { return values.reduce((a, b) => a < b ? a : b); }
function max(values) { return values.reduce((a, b) => a > b ? a : b); }
function rational(n, d) {
  if (d <= 0n) throw Error('NONPOSITIVE_DENOMINATOR');
  let a = abs(n), b = d;
  while (b) { const c = a % b; a = b; b = c; }
  return String(n / (a || 1n)) + '/' + String(d / (a || 1n));
}
function quality(estimate, low, high) {
  const radius = max([abs(estimate - low), abs(high - estimate)]);
  const denominator = low > 0n ? low : high < 0n ? -high : 0n;
  return { radiusMicroJ: String(radius), worstRelativeErrorPpm: denominator === 0n
    ? null : String(ceil(radius * 1000000n, denominator)) };
}
function ratioQuality(lowN, lowD, estimateN, estimateD, highN, highD) {
  if (lowN <= 0n || lowD <= 0n || estimateD <= 0n || highD <= 0n) return null;
  const lowerDeviation = ceil(abs(estimateN * lowD - lowN * estimateD) * 1000000n,
    estimateD * lowN);
  const upperDeviation = ceil(abs(highN * estimateD - estimateN * highD) * lowD * 1000000n,
    highD * estimateD * lowN);
  return String(max([lowerDeviation, upperDeviation]));
}
function ratioBounds(lowN, estimateN, highN, lowD, estimateD, highD) {
  const estimate = estimateD > 0n ? rational(estimateN, estimateD) : null;
  if (lowD <= 0n) return { low: null, estimate, high: null, worstRelativeErrorPpm: null,
    ratioDomain: 'DENOMINATOR_INCLUDES_ZERO' };
  const corners = [[lowN, lowD], [lowN, highD], [highN, lowD], [highN, highD]];
  const compare = (a, b) => a[0] * b[1] - b[0] * a[1];
  const lower = corners.reduce((a, b) => compare(a, b) <= 0n ? a : b);
  const upper = corners.reduce((a, b) => compare(a, b) >= 0n ? a : b);
  return { low: rational(...lower), estimate, high: rational(...upper),
    worstRelativeErrorPpm: ratioQuality(lower[0], lower[1], estimateN, estimateD, upper[0], upper[1]),
    ratioDomain: 'POSITIVE_DENOMINATOR' };
}
function strings(low, estimate, high) {
  return { low: String(low), estimate: String(estimate), high: String(high) };
}
function jsonArtifact(name, value) {
  return { name, type: 'application/json', content: JSON.stringify(value, null, 2) + '\n' };
}
async function executeThermal(supplied, checkpoint) {
  validateThermalInput(supplied);
  const input = JSON.parse(JSON.stringify(supplied));
  validateThermalInput(input);
  if (typeof checkpoint !== 'function') throw Error('CHECKPOINT_REQUIRED');
  const m = input.measurement, rho = m.densityKgPerM3, cp = m.specificHeatJPerKgK;
  let lowNumerator = 0n, estimateNumerator = 0n, highNumerator = 0n, commandNumerator = 0n, work = 0;
  const scale = 1000000000000n;
  for (const v of m.intervals) {
    if (work === input.maxWorkUnits) break;
    await checkpoint('thermal-interval');
    const volumes = [BigInt(v.volumeNL - v.volumeUncertaintyNL), BigInt(v.volumeNL + v.volumeUncertaintyNL)];
    const temperatures = [BigInt(v.deltaTemperatureUK - v.deltaTemperatureUncertaintyUK),
      BigInt(v.deltaTemperatureUK + v.deltaTemperatureUncertaintyUK)];
    const products = [];
    for (const r of [rho.low, rho.high]) for (const c of [cp.low, cp.high]) {
      for (const volume of volumes) for (const temperature of temperatures) {
        products.push(BigInt(r) * BigInt(c) * volume * temperature);
      }
    }
    lowNumerator += min(products); highNumerator += max(products);
    estimateNumerator += BigInt(rho.estimate) * BigInt(cp.estimate) * BigInt(v.volumeNL) * BigInt(v.deltaTemperatureUK);
    commandNumerator += BigInt(rho.estimate) * BigInt(cp.estimate) * BigInt(v.commandFlowNLPerMin)
      * BigInt(v.durationMs) * BigInt(v.deltaTemperatureUK);
    work++;
  }
  const complete = work === m.intervals.length;
  const low = floor(lowNumerator, scale), high = ceil(highNumerator, scale), estimate = round(estimateNumerator, scale);
  const commandEstimate = round(commandNumerator, scale * 60000n);
  const uncertainty = quality(estimate, low, high);
  const observable = m.coverage === 'WHOLE_FLOW_DECLARED_BOUNDS' &&
    m.propertyModel === 'CONSTANT_WITHIN_INTERVAL' &&
    m.volumeWitness.kind === 'INDEPENDENT_SIMULATED' && m.temperatureWitness.kind === 'BOUNDED_SIMULATED' &&
    new Set([m.commandSourceId, m.volumeWitness.sourceId, m.temperatureWitness.sourceId]).size === 3;
  const accurate = uncertainty.worstRelativeErrorPpm !== null &&
    BigInt(uncertainty.worstRelativeErrorPpm) <= BigInt(input.policy.maxRelativeErrorPpm);
  let decision = !complete ? 'WORK_BUDGET_EXHAUSTED' : !observable ? 'OBSERVABILITY_NOT_ESTABLISHED'
    : low <= 0n ? 'POSITIVE_HEAT_NOT_IDENTIFIABLE' : !accurate ? 'UNCERTAINTY_EXCEEDS_POLICY'
      : low < BigInt(input.policy.minimumHeatMicroJ) ? 'HEAT_TARGET_NOT_MET' : 'CONDITIONAL_BOUNDS_MET';
  const quantity = { name: 'delivered heat', unit: 'microjoules', ...strings(low, estimate, high) };
  let downstream = null;
  if (complete && input.family !== 'delivered-heat') {
    const e = input.extension;
    const independent = e.kind === 'INDEPENDENT_SIMULATED' &&
      ![m.commandSourceId, m.volumeWitness.sourceId, m.temperatureWitness.sourceId].includes(e.sourceId);
    if (input.family === 'heat-capacity') {
      const losses = e.lossEnergyMicroJ, container = e.containerEnergyMicroJ, rise = e.temperatureRiseUK;
      const netLow = low - BigInt(losses.high) - BigInt(container.high);
      const netHigh = high - BigInt(losses.low) - BigInt(container.low);
      const netEstimate = estimate - BigInt(losses.estimate) - BigInt(container.estimate);
      downstream = { name: 'single-sample heat capacity', unit: 'joules per kelvin',
        netEnergyMicroJ: strings(netLow, netEstimate, netHigh), temperatureRiseUK: rise,
        ...ratioBounds(netLow, netEstimate, netHigh, BigInt(rise.low), BigInt(rise.estimate), BigInt(rise.high)),
        assumption: 'All residual measured heat enters one sample; losses and container storage are independently bounded.' };
      if (decision === 'CONDITIONAL_BOUNDS_MET') {
        if (!independent) decision = 'ADDITIONAL_INDEPENDENT_WITNESS_REQUIRED';
        else if (rise.low === 0) decision = 'HEAT_CAPACITY_NOT_IDENTIFIABLE';
        else if (netHigh <= 0n) decision = 'ENERGY_BOUNDARY_INCONSISTENT';
        else if (netLow <= 0n) decision = 'ENERGY_BOUNDARY_NOT_RESOLVED';
        else if (downstream.worstRelativeErrorPpm === null ||
          BigInt(downstream.worstRelativeErrorPpm) > BigInt(input.policy.maxRelativeErrorPpm)) {
          decision = 'DOWNSTREAM_UNCERTAINTY_EXCEEDS_POLICY';
        }
      }
    } else {
      const energy = e.inputEnergyMicroJ, storage = e.storageReleaseMicroJ;
      const netLow = low - BigInt(storage.high), netHigh = high - BigInt(storage.low);
      const netEstimate = estimate - BigInt(storage.estimate);
      const denominatorLow = BigInt(energy.low), denominatorHigh = BigInt(energy.high);
      downstream = { name: 'storage-adjusted heat recovery', unit: 'dimensionless',
        netHeatMicroJ: strings(netLow, netEstimate, netHigh),
        inputEnergyMicroJ: energy, minimumRecoveryPpm: e.minimumRecoveryPpm,
        ...ratioBounds(netLow, netEstimate, netHigh, denominatorLow, BigInt(energy.estimate), denominatorHigh),
        assumption: 'The independent input bound covers every energy input; stored-energy release is separately bounded.' };
      if (decision === 'CONDITIONAL_BOUNDS_MET') {
        if (!independent) decision = 'ADDITIONAL_INDEPENDENT_WITNESS_REQUIRED';
        else if (denominatorLow === 0n) decision = 'RECOVERY_RATIO_NOT_IDENTIFIABLE';
        else if (netHigh < 0n || netLow > denominatorHigh) decision = 'ENERGY_BOUNDARY_INCONSISTENT';
        else if (netLow < 0n || netHigh > denominatorLow) decision = 'ENERGY_BOUNDARY_NOT_RESOLVED';
        else if (downstream.worstRelativeErrorPpm === null ||
          BigInt(downstream.worstRelativeErrorPpm) > BigInt(input.policy.maxRelativeErrorPpm)) {
          decision = 'DOWNSTREAM_UNCERTAINTY_EXCEEDS_POLICY';
        } else if (netLow * 1000000n < BigInt(e.minimumRecoveryPpm) * denominatorHigh) decision = 'RECOVERY_TARGET_NOT_MET';
      }
    }
  }
  await checkpoint('thermal-evidence');
  const evidence = {
    schema: THERMAL_SCHEMA, family: input.family, completion: complete ? 'COMPLETE' : 'EXHAUSTED',
    intervalsProcessed: work, intervalsDeclared: m.intervals.length,
    workUnits: work, workUnitDefinition: 'One bounded interval reduction; validation and fixed final arithmetic are outside this counter.',
    coverageMs: m.intervals.slice(0, work).reduce((sum, v) => sum + v.durationMs, 0),
    simulation: true, physicalValidity: 'NOT_ESTABLISHED', independentReview: false,
    witnessIndependence: 'Declared synthetic channel separation, not authenticated metrological or organizational independence.',
    propertyModel: m.propertyModel,
    acquisitionAssumption: 'Density and specific heat are constant within each interval. The temperature bound covers its volume-weighted mean differential; property-temperature covariance is not modeled.',
    observable, quantity, uncertainty, downstream,
    commandOnlyBaseline: { heatMicroJ: String(commandEstimate), errorVsWitnessEstimateMicroJ: String(commandEstimate - estimate),
      canBoundHiddenFlowError: false },
    inheritedFailure: INHERITED_FOUNDRY_FAILURE,
    calculation: 'rho[kg/m3] * cp[J/kg/K] * volume[nL] * deltaT[microK] / 10^12 = microjoules; interval extrema rounded outwards.',
  };
  const proposal = {
    schema: 'thermal-capability-proposal/v1', family: input.family, decision,
    boundedArithmeticAccepted: decision === 'CONDITIONAL_BOUNDS_MET',
    acceptedCapability: false, authority: [], settlement: 'NOT_CONNECTED',
    requires: ['Independent result acceptance', 'Authenticated witness acquisition', 'Actual harness execution and recovery receipt'],
  };
  return { decision, summary: { family: input.family, completion: evidence.completion, intervalsProcessed: work,
    acceptedCapability: false, physicalValidity: 'NOT_ESTABLISHED' }, evidence,
    artifacts: [jsonArtifact('thermal-bounds.json', evidence), jsonArtifact('thermal-capability-proposal.json', proposal)],
    limits: [
      'Executed fixed calorimetry arithmetic over simulated measurement inputs; no physical instrument is controlled.',
      'Bounds assume complete participating-flow coverage, fixed properties within each interval and honest calibration limits. Unmodeled property-temperature covariance or omitted errors can invalidate them.',
      'A command-derived volume cannot observe actuator bias. Different source labels alone do not prove independence.',
      'The historical Foundry failure remains retained; this new computation is not a rerun of the original full study.',
      'A source or packaged-worker result alone does not establish SUCCESSOR harness recovery, independent Fleet acceptance or contract settlement.',
    ] };
}
const thermalWitnessAdapter = Object.freeze({
  manifest: Object.freeze({
    id: 'thermal-witness', version: 1,
    en: 'Construct a witnessed thermal measurement', fr: 'Construire une mesure thermique avec référence',
    scope: 'Bounded simulated whole-flow calorimetry and conditional downstream quantities; no physical or financial authority.',
    artifact: 'thermal-bounds.json',
  }),
  validate: validateThermalInput, execute: executeThermal,
});
function thermalExample(family = 'delivered-heat') {
  const bandOf = n => ({ low: n, estimate: n, high: n });
  const energy = n => bandOf(String(n));
  const extension = family === 'delivered-heat' ? {} : family === 'heat-capacity'
    ? { sourceId: 'sample-reference', kind: 'INDEPENDENT_SIMULATED', temperatureRiseUK: bandOf(10000000),
      lossEnergyMicroJ: energy(800000000), containerEnergyMicroJ: energy(200000000) }
    : { sourceId: 'energy-reference', kind: 'INDEPENDENT_SIMULATED', inputEnergyMicroJ: energy(5000000000),
      storageReleaseMicroJ: energy(200000000), minimumRecoveryPpm: 600000 };
  const input = {
    schema: THERMAL_SCHEMA, family,
    measurement: {
      mode: 'SIMULATED_MEASUREMENTS', coverage: 'WHOLE_FLOW_DECLARED_BOUNDS',
      propertyModel: 'CONSTANT_WITHIN_INTERVAL', commandSourceId: 'controller-telemetry',
      volumeWitness: { sourceId: 'independent-volume', kind: 'INDEPENDENT_SIMULATED' },
      temperatureWitness: { sourceId: 'differential-reference', kind: 'BOUNDED_SIMULATED' },
      densityKgPerM3: bandOf(1000), specificHeatJPerKgK: bandOf(4000), windowMs: 60000,
      intervals: [{ sequence: 0, startMs: 0, durationMs: 60000, commandFlowNLPerMin: 100000000,
        volumeNL: 92000000, volumeUncertaintyNL: 0, deltaTemperatureUK: 10000000, deltaTemperatureUncertaintyUK: 0 }],
    },
    policy: { maxRelativeErrorPpm: 50000, minimumHeatMicroJ: '1000000' }, extension, maxWorkUnits: 960,
  };
  validateThermalInput(input);
  return input;
}

return {THERMAL_SCHEMA,INHERITED_FOUNDRY_FAILURE,validateThermalInput,executeThermal,thermalWitnessAdapter,thermalExample};
})();
const module_7=(()=>{
// SPDX-License-Identifier: Apache-2.0
// Fixed shipped registrations; imported missions cannot install executable adapters.
const core = module_0;
const { thermalWitnessAdapter, thermalExample } = module_8;

const runtime = core.createWorkbench([thermalWitnessAdapter]);
const VERSION = core.VERSION;
const REGISTRY = runtime.registry;
const validate = runtime.validate;
const plan = runtime.plan;
const run = runtime.run;
const inspectPack = runtime.inspectPack;

function example(family = 'reliability') {
  if (family !== 'thermal-witness') return core.example(family);
  return { ...core.example(), family, name: 'Witnessed thermal measurement',
    rights: { dataClass: 'synthetic', source: 'Declared simulated whole-flow fixture', license: 'Apache-2.0' },
    inputs: thermalExample() };
}

return {VERSION,REGISTRY,validate,plan,run,inspectPack,example};
})();
const workbench=module_0,transport=module_1,nativeWorkbench=module_7;
const SOURCE_HASH='f36d67ba20115cd1b42c31abcb9c36c7db0c07732fce309ec1e7274b554776cb';

let raw='';
process.stdin.setEncoding('utf8');
for await (const chunk of process.stdin) {
  raw+=chunk;
  if(Buffer.byteLength(raw)>2000000)throw Error('INPUT_SIZE_LIMIT');
}
const request=transport.parseBounded(raw);
let result;
if(request.operation==='registry')result={schema:nativeWorkbench.VERSION,sourceHash:SOURCE_HASH,families:nativeWorkbench.REGISTRY};
else if(request.operation==='example')result=nativeWorkbench.example(request.family);
else if(request.operation==='run')result=await nativeWorkbench.run(request.spec,{sourceHash:SOURCE_HASH});
else if(request.operation==='plan')result=await nativeWorkbench.plan(request.spec);
else if(request.operation==='inspect')result=await nativeWorkbench.inspectPack(request.pack);
else throw Error('UNKNOWN_OPERATION');
process.stdout.write(transport.canonical(result)+'\n');
