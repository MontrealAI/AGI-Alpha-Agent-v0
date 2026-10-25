// SPDX-License-Identifier: MIT
// Local inspection only. Imported data cannot select runtime code or grant authority.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { canonical, parseBounded, parseWorkRequest, validateBindings, validateResources,
  BINDING_KEYS, RESOURCE_KEYS, REQUEST_SCHEMA, STAGES, MAX_INPUT_BYTES } from './discovery-lab-contract.mjs';

export const DISCOVERY_LAB_ADMISSION_SCHEMA = 'agijobsv0/discovery-lab-admission/v1';
const ROUTE = 'jobs-agialpha', CURRENCY = 'AGIALPHA18';
const sha = value => createHash('sha256').update(value).digest('hex');
const source = Object.freeze({ adapterSha256:sha(readFileSync(new URL(import.meta.url))),
  contractSha256:sha(readFileSync(new URL('./discovery-lab-contract.mjs', import.meta.url))) });
const same = (a, b) => canonical(a) === canonical(b);
const need = (condition, code) => { if (!condition) throw Object.assign(Error(code), { code }); };
const exact = (value, names) => value && typeof value === 'object' && !Array.isArray(value)
  && Object.keys(value).length === names.length && names.every(name => Object.hasOwn(value, name));
const exhausted = reason => /(?:BUDGET_EXHAUSTED|SEARCH_TRUNCATED|CHECK_INCOMPLETE)$/.test(reason);
function freezeData(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freezeData); Object.freeze(value); }
  return value;
}
const identifier = value => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(value);

export function discoveryLabReceiverCapabilities() {
  return { schema:REQUEST_SCHEMA, stages:[...STAGES], route:ROUTE, currency:CURRENCY,
    executionMode:'synthetic-local', admission:'local-inspection-only',
    externalExecution:'unprovisioned', submission:'unsupported', authority:'none', source:{...source} };
}

function currentContext(request, expectedBindings, expectedCommission) {
  validateBindings(expectedBindings);
  need(same(Object.fromEntries(BINDING_KEYS.map(key => [key, request[key]])), expectedBindings),
    'DISCOVERY_LAB_STALE_BINDINGS');
  need(exact(expectedCommission, ['id', 'branch', 'route']) && identifier(expectedCommission.id)
    && identifier(expectedCommission.branch) && expectedCommission.route === ROUTE,
  'DISCOVERY_LAB_EXPECTED_COMMISSION');
  need(request.commission.route === ROUTE && request.commission.currency === CURRENCY,
    'DISCOVERY_LAB_WRONG_ROUTE');
  need(['id', 'branch', 'route'].every(key => request.commission[key] === expectedCommission[key]),
    'DISCOVERY_LAB_COMMISSION_BINDING');
}

function checkReport(value) {
  value = JSON.parse(canonical(value));
  need(exact(value, ['accepted', 'resourceUsed', 'reasons']) && typeof value.accepted === 'boolean'
    && Array.isArray(value.reasons) && value.reasons.length <= 32
    && value.reasons.every(reason => typeof reason === 'string' && reason.length > 0 && reason.length <= 500)
    && (value.accepted || value.reasons.length > 0)
    && !(value.accepted && value.reasons.some(exhausted)), 'DISCOVERY_LAB_CHECKER_REPORT');
  validateResources(value.resourceUsed);
  return value;
}

// Admission uses 10,000 declared checking units. Byte units count encoded input,
// immutable copies and the serialized receipt; they are not VM heap measurements.
export const DISCOVERY_LAB_ADMISSION_CHECKS = 10_000;
const zeroResources = () => Object.fromEntries(RESOURCE_KEYS.map(key => [key, 0]));
const byteLength = value => Buffer.byteLength(value, 'utf8');
const elapsed = start => Math.max(0, Math.ceil(performance.now() - start));
function initialResources(raw, started) {
  const used = zeroResources(); used.checking = DISCOVERY_LAB_ADMISSION_CHECKS;
  if (typeof raw === 'string' && raw.length > MAX_INPUT_BYTES) {
    // Reject in constant time before any UTF-8 traversal/allocation. The
    // observed logical UTF-16 footprint is explicit; this is not VM heap use.
    used.memoryBytes = 2 * raw.length; used.elapsedMs = elapsed(started);
    throw Object.assign(Error('DISCOVERY_LAB_INPUT_TOO_LARGE'), {code:'DISCOVERY_LAB_INPUT_TOO_LARGE',
      resourceUsed:used, resourceAccounting:'current-failed-attempt-charge',
      resourceMemoryAccounting:'logical-UTF16-code-unit-bytes; UTF8-not-scanned',
      nativeResourceReservation:null, authority:'none'});
  }
  used.memoryBytes = typeof raw === 'string' ? byteLength(raw) : 0;
  return used;
}

const fits = (used, limits) => RESOURCE_KEYS.every(key => used[key] <= limits[key]);
// Every variable field below is an ASCII status/boolean or validated safe integer.
// Their digit lengths let the final timer update preserve exact receipt bytes
// without another expensive full serialization after that measurement.
const vectorDigits = vector => RESOURCE_KEYS.reduce((sum, key) => sum + String(vector[key]).length, 0);
const admissionVariableBytes = result => result.state.length + String(result.checker.withinResourceEnvelope).length
  + vectorDigits(result.resources.receiverUsed) + vectorDigits(result.resources.totalUsed);
function ownedFailure(error) {
  // Never mutate an inspector's frozen/sealed error or invoke diagnostic getters.
  const failure = new Error('DISCOVERY_LAB_INSPECTION_FAILED', {cause:error});
  try {
    for (const [key, limit] of [['message', 512], ['code', 128]]) {
      const descriptor = Object.getOwnPropertyDescriptor(Object(error), key);
      if (descriptor && Object.hasOwn(descriptor, 'value') && typeof descriptor.value === 'string'
          && descriptor.value.length <= limit) failure[key] = descriptor.value;
    }
  } catch { /* Opaque thrown objects remain available only as the cause. */ }
  return failure;
}

function totalResources(receiver, checker = zeroResources(), nativeWall = 0) {
  const exact = Object.fromEntries(RESOURCE_KEYS.map(key => [key, BigInt(receiver[key]) + BigInt(checker[key])]));
  if (RESOURCE_KEYS.some(key => exact[key] > BigInt(Number.MAX_SAFE_INTEGER))) {
    throw Object.assign(Error('DISCOVERY_LAB_RESOURCE_OVERFLOW'), {code:'DISCOVERY_LAB_RESOURCE_OVERFLOW',
      resourceTotalsExact:Object.fromEntries(RESOURCE_KEYS.map(key => [key, exact[key].toString()]))});
  }
  const total = Object.fromEntries(RESOURCE_KEYS.map(key => [key, Number(exact[key])]));
  // Current wall time already includes native execution; never charge it twice.
  const elapsedExact = BigInt(Math.ceil(Math.max(0, receiver.elapsedMs - nativeWall))) + BigInt(checker.elapsedMs);
  need(elapsedExact <= BigInt(Number.MAX_SAFE_INTEGER), 'DISCOVERY_LAB_RESOURCE_OVERFLOW');
  total.elapsedMs = Math.max(receiver.elapsedMs, Number(elapsedExact));
  return total;
}

/** The caller supplies the installed checker and its independently frozen current context. */
async function inspectRequest(raw, options = {}, started = performance.now()) {
  const receiver = initialResources(raw, started);
  let checkerReport = null, nativeWall = 0, nativeInvoked = false, nativeLimits = null;
  try {
    const {expectedBindings, expectedCommission, inspectCampaign} = options;
    const bindingSnapshot = canonical(expectedBindings), commissionSnapshot = canonical(expectedCommission);
    const frozenBindings = freezeData(JSON.parse(bindingSnapshot));
    const frozenCommission = freezeData(JSON.parse(commissionSnapshot));
    receiver.memoryBytes += 2 * (byteLength(bindingSnapshot) + byteLength(commissionSnapshot));
    const contextUnchanged = () => need(canonical(expectedBindings) === bindingSnapshot
      && canonical(expectedCommission) === commissionSnapshot, 'DISCOVERY_LAB_CONTEXT_CHANGED');
    const request = await parseWorkRequest(raw);
    const requestSnapshot = canonical(request);
    receiver.memoryBytes += 2 * byteLength(requestSnapshot);
    contextUnchanged();
    currentContext(request, frozenBindings, frozenCommission);
    need(typeof inspectCampaign === 'function', 'DISCOVERY_LAB_INSPECTOR_REQUIRED');
    let workingBytes = receiver.memoryBytes;
    receiver.memoryBytes = workingBytes;
    receiver.elapsedMs = elapsed(started);
    // JSON escaping can double retained raw bytes; reasons may use control escapes.
    const receiptReservationBytes = 2 * byteLength(raw) + 131_072;
    const reservedReceiver = {...receiver, memoryBytes:workingBytes + byteLength(requestSnapshot) + receiptReservationBytes,
      storageBytes:receiptReservationBytes};
    const reservationAvailable = fits(reservedReceiver, request.resourceLimits);
    if (reservationAvailable) {
      nativeLimits = Object.fromEntries(RESOURCE_KEYS.map(key => [key, request.resourceLimits[key] - reservedReceiver[key]]));
      const checkedRequest = freezeData(JSON.parse(requestSnapshot));
      workingBytes += byteLength(requestSnapshot); receiver.memoryBytes = workingBytes;
      const nativeStarted = performance.now(); nativeInvoked = true;
      try {
        checkerReport = checkReport(await inspectCampaign(checkedRequest.payload,
          freezeData({request:checkedRequest, limits:{...nativeLimits}})));
      } finally { nativeWall = performance.now() - nativeStarted; }
      contextUnchanged();
      need(canonical(request) === requestSnapshot, 'DISCOVERY_LAB_CHECKER_MUTATED_INPUT');
    }
    receiver.elapsedMs = elapsed(started);
    const incomplete = checkerReport && !checkerReport.accepted && checkerReport.reasons.some(exhausted);
    const nativeWithinResourceEnvelope = Boolean(checkerReport && fits(checkerReport.resourceUsed, nativeLimits));
    const result = {schema:DISCOVERY_LAB_ADMISSION_SCHEMA, state:'inconclusive', original:raw, requestSha256:sha(raw),
      bindings:JSON.parse(bindingSnapshot), commission:{...request.commission}, stage:request.stage,
      inputArtifacts:[...request.inputArtifacts], payloadDigest:request.payloadDigest, source:{...source},
      checker:{report:checkerReport, withinResourceEnvelope:false, nativeWithinResourceEnvelope},
      resources:{units:'declared-admission-checks-and-encoded-bytes; elapsedMs measured',
        receiverUsed:{...receiver}, checkerUsed:checkerReport?.resourceUsed || zeroResources(), totalUsed:zeroResources(),
        receiverReservation:reservedReceiver, nativeLimits, reservationAvailable},
      reason:!reservationAvailable ? 'RECEIVER_RESERVATION_UNAVAILABLE' : !nativeWithinResourceEnvelope ? 'NATIVE_RESOURCE_ENVELOPE_EXCEEDED' : null,
      lifecycle:{commission:'DRAFT_NOT_SUBMITTED', reservedBaseUnits:'0', execution:'unprovisioned',
        review:'separate-review-required', settlement:'not-connected'},
      capabilityAcceptance:'not-granted-by-import', authority:'none'};
    // Resolve receipt byte counts after inserting their own bounded integer fields.
    for (let i = 0; i < 8; i++) {
      const bytes = byteLength(JSON.stringify(result));
      if (result.resources.receiverUsed.storageBytes === bytes) break;
      result.resources.receiverUsed.storageBytes = bytes;
      result.resources.receiverUsed.memoryBytes = workingBytes + bytes;
      receiver.storageBytes = bytes; receiver.memoryBytes = workingBytes + bytes;
      result.resources.totalUsed = totalResources(result.resources.receiverUsed, result.resources.checkerUsed, nativeWall);
    }
    receiver.elapsedMs = elapsed(started);
    result.resources.receiverUsed.elapsedMs = receiver.elapsedMs;
    result.resources.totalUsed = totalResources(result.resources.receiverUsed, result.resources.checkerUsed, nativeWall);
    result.checker.withinResourceEnvelope = fits(result.resources.totalUsed, request.resourceLimits);
    result.state = !reservationAvailable || !nativeWithinResourceEnvelope || !result.checker.withinResourceEnvelope || incomplete ? 'inconclusive'
      : checkerReport.accepted ? 'local-checked' : 'local-rejected';
    // State and measured elapsed digits can alter the serialized receipt length.
    let serializedBytes, serializedVariables;
    for (let i = 0; i < 8; i++) {
      serializedVariables = admissionVariableBytes(result);
      const bytes = serializedBytes = byteLength(JSON.stringify(result));
      if (result.resources.receiverUsed.storageBytes === bytes) break;
      result.resources.receiverUsed.storageBytes = bytes;
      result.resources.receiverUsed.memoryBytes = workingBytes + bytes;
      receiver.storageBytes = bytes; receiver.memoryBytes = workingBytes + bytes;
      result.resources.totalUsed = totalResources(result.resources.receiverUsed, result.resources.checkerUsed, nativeWall);
    }
    const settleFinalSample = () => {
      receiver.elapsedMs = elapsed(started);
      result.resources.receiverUsed.elapsedMs = receiver.elapsedMs;
      for (let i = 0; i < 8; i++) {
        result.resources.totalUsed = totalResources(result.resources.receiverUsed, result.resources.checkerUsed, nativeWall);
        result.checker.withinResourceEnvelope = fits(result.resources.totalUsed, request.resourceLimits);
        if (!result.checker.withinResourceEnvelope) result.state = 'inconclusive';
        const bytes = serializedBytes - serializedVariables + admissionVariableBytes(result);
        if (result.resources.receiverUsed.storageBytes === bytes) return;
        result.resources.receiverUsed.storageBytes = receiver.storageBytes = bytes;
        result.resources.receiverUsed.memoryBytes = receiver.memoryBytes = workingBytes + bytes;
      }
      need(false, 'DISCOVERY_LAB_RECEIPT_DID_NOT_CONVERGE');
    };
    // Charge all full JSON serialization and byte-count convergence first, then
    // the bounded scalar reconciliation itself. No full stringify follows.
    settleFinalSample(); settleFinalSample();
    return result;
  } catch (error) {
    const failure = ownedFailure(error);
    receiver.elapsedMs = elapsed(started);
    try { failure.resourceUsed = totalResources(receiver, checkerReport?.resourceUsed || zeroResources(), nativeWall); }
    catch (overflow) {
      failure.resourceUsed = {...receiver};
      failure.checkerResourceUsed = checkerReport?.resourceUsed || zeroResources();
      failure.resourceTotalsExact = overflow.resourceTotalsExact;
    }
    failure.resourceAccounting = failure.resourceTotalsExact ? 'component-charges-retained; total-exceeds-safe-integer-range'
      : nativeInvoked && !checkerReport
      ? 'receiver-charge-retained; native-budget-reservation-unresolved' : 'current-failed-attempt-charge';
    failure.nativeResourceReservation = nativeInvoked && !checkerReport ? nativeLimits : null;
    failure.authority = 'none';
    throw failure;
  }
}

export async function inspectDiscoveryLabWorkRequest(raw, options = {}) {
  return inspectRequest(raw, options, performance.now());
}

/** Probe unsupported schema/mode explicitly; malformed or stale supported requests still reject. */
export async function receiveDiscoveryLabWorkRequest(raw, options = {}) {
  const started = performance.now(), used = initialResources(raw, started);
  let input;
  try { input = parseBounded(raw); }
  catch (error) { used.elapsedMs = elapsed(started); const failure = ownedFailure(error);
    failure.resourceUsed = used; failure.authority = 'none'; throw failure; }
  const state = input?.schema !== REQUEST_SCHEMA ? 'unsupported'
    : input.executionMode !== 'synthetic-local' ? 'unprovisioned' : null;
  if (!state) { input = null; return inspectRequest(raw, options, started); }
  used.memoryBytes += byteLength(canonical(input)); used.elapsedMs = elapsed(started);
  const result = {state, reason:state === 'unsupported' ? 'DISCOVERY_LAB_UNSUPPORTED_SCHEMA' : 'DISCOVERY_LAB_EXECUTION_UNPROVISIONED',
    requestSha256:sha(raw), resourceUsed:{...used}, authority:'none'};
  let serializedBytes, serializedVariables;
  for (let i = 0; i < 8; i++) {
    serializedVariables = vectorDigits(result.resourceUsed);
    const bytes = serializedBytes = byteLength(JSON.stringify(result));
    if (result.resourceUsed.storageBytes === bytes) break;
    result.resourceUsed.storageBytes = bytes; result.resourceUsed.memoryBytes = used.memoryBytes + bytes;
  }
  const settleFinalSample = () => {
    result.resourceUsed.elapsedMs = elapsed(started);
    for (let i = 0; i < 8; i++) {
      const bytes = serializedBytes - serializedVariables + vectorDigits(result.resourceUsed);
      if (result.resourceUsed.storageBytes === bytes) return;
      result.resourceUsed.storageBytes = bytes; result.resourceUsed.memoryBytes = used.memoryBytes + bytes;
    }
    need(false, 'DISCOVERY_LAB_RECEIPT_DID_NOT_CONVERGE');
  };
  settleFinalSample(); settleFinalSample();
  return result;
}
