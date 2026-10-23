// SPDX-License-Identifier: Apache-2.0
// Research-only candidate. No signing, promotion, external write, or evaluator API.
import { createHash } from 'node:crypto';
import { performance } from 'node:perf_hooks';

export const LIMITS = Object.freeze({ nodes: 64, edges: 256, flatRows: 2000, labelLength: 48, integerDigits: 4096, outputAbs: '1000000', outputTotalAbs: '1000000', flatInputAbs: 1000000 });
export const DEFAULT_BUDGET = Object.freeze({ operations: 1000000, hashBytes: 10000000, elapsedMs: 10000 });
export class CandidateError extends Error {
  constructor(code, message, details = {}) { super(message); this.name = 'CandidateError'; this.code = code; this.details = details; }
}
export function invariant(condition, code, message, details) {
  if (!condition) throw new CandidateError(code, message, details);
}
export function plain(value) { return value !== null && typeof value === 'object' && !Array.isArray(value) && [Object.prototype, null].includes(Object.getPrototypeOf(value)); }
export function exactKeys(value, required, optional = []) {
  invariant(plain(value), 'INVALID_OBJECT', 'Expected a plain data object.');
  invariant(required.every(key => Object.hasOwn(value, key)), 'MISSING_FIELD', 'Required input field is missing.', { required });
  const allowed = new Set([...required, ...optional]);
  invariant(Object.keys(value).every(key => allowed.has(key)), 'UNKNOWN_FIELD', 'Unexpected input field.', { fields: Object.keys(value).filter(key => !allowed.has(key)) });
}
export function label(value, name = 'label') {
  invariant(typeof value === 'string' && /^[A-Za-z0-9_-]{1,48}$/u.test(value), 'INVALID_LABEL', `${name} must contain 1..${LIMITS.labelLength} ASCII letters, digits, underscores, or hyphens.`);
  return value;
}
export function safeInteger(value, name, { positive = false, nonnegative = false } = {}) {
  invariant(Number.isSafeInteger(value) && (!positive || value > 0) && (!nonnegative || value >= 0), 'INVALID_INTEGER', `${name} must be a safe integer${positive ? ' greater than zero' : nonnegative ? ' at least zero' : ''}.`);
  return value;
}
export function deepFreeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) { Object.freeze(value); for (const entry of Object.values(value)) deepFreeze(entry); }
  return value;
}
export function canonical(value) {
  const seen = new Set();
  function walk(item) {
    if (item === null || typeof item === 'boolean' || typeof item === 'string') return item;
    if (typeof item === 'number') { invariant(Number.isFinite(item), 'NONFINITE_JSON', 'Canonical data cannot contain nonfinite numbers.'); return item; }
    invariant(typeof item === 'object', 'NONDATA_VALUE', 'Canonical data must be JSON-compatible.');
    invariant(!seen.has(item), 'CYCLIC_DATA', 'Canonical data cannot be cyclic.');
    seen.add(item);
    let result;
    if (Array.isArray(item)) result = item.map(walk);
    else { invariant(plain(item), 'NONDATA_OBJECT', 'Canonical data must contain plain objects.'); result = Object.fromEntries(Object.keys(item).sort().map(key => [key, walk(item[key])])); }
    seen.delete(item); return result;
  }
  return JSON.stringify(walk(value));
}
export function sha256Bytes(value) { return createHash('sha256').update(value).digest('hex'); }
export function digest(value) { return sha256Bytes(canonical(value)); }
export function copy(value) { return JSON.parse(canonical(value)); }

export function createMeter(budget = {}, signal = undefined) {
  const limits = { ...DEFAULT_BUDGET, ...budget };
  invariant(Object.keys(budget).every(key => Object.hasOwn(DEFAULT_BUDGET, key)), 'UNKNOWN_BUDGET', 'Unknown budget field.');
  for (const [key, value] of Object.entries(limits)) invariant(Number.isFinite(value) && value >= 0, 'INVALID_BUDGET', `Invalid ${key} budget.`);
  const start = performance.now();
  const counters = { operations: 0, constructionOperations: 0, executionOperations: 0, controlOperations: 0, hashBytes: 0, constructionHashBytes: 0, executionHashBytes: 0, controlHashBytes: 0, operationKinds: {}, stages: {} };
  let phase = 'control'; let stage = 'Identify';
  function check() {
    if (signal?.aborted) throw new CandidateError('INTERRUPTED', 'Candidate execution was interrupted by its caller.');
    if (performance.now() - start > limits.elapsedMs) throw new CandidateError('BUDGET_ELAPSED', 'Elapsed-time ceiling reached.');
  }
  function current() { return counters.stages[stage] ??= { operations: 0, hashBytes: 0 }; }
  return {
    setPhase(next, nextStage) { invariant(['control', 'construction', 'execution'].includes(next), 'BAD_PHASE', 'Unknown instrumentation phase.'); check(); phase = next; stage = nextStage; current(); },
    tick(kind, count = 1) { check(); invariant(Number.isSafeInteger(count) && count >= 0, 'BAD_COUNT', 'Operation count must be a nonnegative integer.'); if (counters.operations + count > limits.operations) throw new CandidateError('BUDGET_OPERATIONS', 'Counted-operation ceiling reached.', { nextKind: kind, nextCount: count }); counters.operations += count; counters[`${phase}Operations`] += count; counters.operationKinds[kind] = (counters.operationKinds[kind] ?? 0) + count; current().operations += count; },
    hash(value, kind = 'canonical-data') { check(); const bytes = typeof value === 'string' || Buffer.isBuffer(value) ? value : canonical(value); const count = Buffer.byteLength(bytes); if (counters.hashBytes + count > limits.hashBytes) throw new CandidateError('BUDGET_HASH_BYTES', 'Hash-byte ceiling reached.', { nextKind: kind, nextBytes: count }); counters.hashBytes += count; counters[`${phase}HashBytes`] += count; current().hashBytes += count; return sha256Bytes(bytes); },
    check,
    snapshot() { return deepFreeze({ ...copy(counters), elapsedMs: performance.now() - start, limits: { ...limits }, units: { operations: 'instrumented events, not CPU instructions or dollars', hashBytes: 'UTF-8/source bytes passed to SHA-256', elapsedMs: 'monotonic wall-clock milliseconds' }, providerCalls: 0, fundsMoved: '0' }); }
  };
}
export function optionalMeter(meter) { return meter ?? createMeter(); }
