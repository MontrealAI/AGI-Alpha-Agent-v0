// SPDX-License-Identifier: Apache-2.0
import {keccak256, toUtf8Bytes} from './vendor/ethers-6.17.0.mjs';
import {canonicalJSON} from '../ascension/crypto.mjs';
import {verifyPlan} from './plan.mjs';

export const MAX_NATIVE_BYTES = 2000000;
const encoder = new TextEncoder();
const forbidden = new Set(['__proto__', 'prototype', 'constructor']);
const requireThat = (condition, message) => { if (!condition) throw Error(message); };
const exactKeys = (value, keys) => value && !Array.isArray(value) && typeof value === 'object' &&
  Object.keys(value).sort().join() === [...keys].sort().join();

function validUnicode(value) {
  for (let index = 0; index < value.length; index++) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(++index);
      requireThat(next >= 0xdc00 && next <= 0xdfff, 'Malformed native Unicode.');
    } else requireThat(code < 0xdc00 || code > 0xdfff, 'Malformed native Unicode.');
  }
  return value;
}

function nativeText(source) {
  if (source instanceof Uint8Array) {
    requireThat(source.length <= MAX_NATIVE_BYTES, 'Native delivery exceeds its 2 MB byte limit.');
    try { return new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(source); }
    catch { throw Error('Native delivery must retain valid original UTF-8 bytes.'); }
  }
  requireThat(typeof source === 'string' && encoder.encode(source).length <= MAX_NATIVE_BYTES,
    'Native delivery exceeds its 2 MB byte limit.');
  return source;
}

/** Native journals use nanosecond integers. Preserve oversized integer lexemes; never round them. */
export function parseNativeJSON(source) {
  source = nativeText(source);
  let cursor = 0;
  const whitespace = () => { while (/^[\x20\x09\x0a\x0d]$/.test(source[cursor] || '')) cursor++; };
  function string() {
    const start = cursor++;
    while (cursor < source.length) {
      const char = source[cursor++];
      if (char === '\\') { cursor++; continue; }
      if (char === '"') {
        try { return validUnicode(JSON.parse(source.slice(start,cursor))); }
        catch { throw Error('Invalid native JSON string or Unicode.'); }
      }
    }
    throw Error('Unterminated native JSON string.');
  }
  function value(depth) {
    requireThat(depth <= 24, 'Native delivery exceeds 24 nesting levels.');
    whitespace();
    const char = source[cursor];
    if (char === '"') return string();
    if (char === '{' || char === '[') {
      const object = char === '{', result = object ? {} : [], keys = new Set(), end = object ? '}' : ']';
      cursor++; whitespace();
      if (source[cursor] === end) { cursor++; return result; }
      while (cursor < source.length) {
        if (object) {
          whitespace(); requireThat(source[cursor] === '"', 'Expected a native JSON object key.');
          const key = string();
          requireThat(!forbidden.has(key) && !keys.has(key), 'Duplicate or unsafe native JSON key.');
          keys.add(key); whitespace();
          requireThat(source[cursor++] === ':', 'Expected a colon after a native JSON key.');
          result[key] = value(depth + 1);
        } else result.push(value(depth + 1));
        whitespace();
        const next = source[cursor++];
        if (next === end) return result;
        requireThat(next === ',', 'Expected a native JSON separator.');
      }
      throw Error('Unterminated native JSON object or array.');
    }
    for (const [literal, decoded] of [['true',true], ['false',false], ['null',null]]) {
      if (source.startsWith(literal,cursor)) { cursor += literal.length; return decoded; }
    }
    const match = source.slice(cursor).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/);
    requireThat(match, 'Invalid native JSON value.');
    cursor += match[0].length;
    const number = Number(match[0]);
    if (/^-?(?:0|[1-9][0-9]*)$/.test(match[0]) && !Number.isSafeInteger(number)) return match[0];
    requireThat(Number.isFinite(number) && !(Number.isInteger(number) && !Number.isSafeInteger(number)),
      'Native JSON numbers must be finite and exact.');
    return number;
  }
  const parsed = value(0); whitespace();
  requireThat(cursor === source.length, 'Unexpected trailing native JSON.');
  return parsed;
}

/** Locate original signed bytes without reserializing Python floats, Unicode keys or large integers. */
function signatureBody(source, envelope) {
  requireThat(source.startsWith('{"body":{'), 'Use the exact compact native delivery without reserializing it.');
  let depth = 0, quoted = false, escaped = false, end = -1;
  for (let index = 8; index < source.length; index++) {
    const char = source[index];
    if (quoted) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') quoted = false;
    } else if (char === '"') quoted = true;
    else {
      requireThat(!/[\x20\x09\x0a\x0d]/.test(char), 'Native delivery formatting changed. Restore the exact original file.');
      if (char === '{' || char === '[') depth++;
      if (char === '}' || char === ']') { depth--; if (depth === 0) { end = index + 1; break; } }
    }
  }
  requireThat(end > 8 && source.slice(end) ===
    `,"publicKey":${JSON.stringify(envelope.publicKey)},"signature":${JSON.stringify(envelope.signature)}}`,
  'Native delivery envelope formatting changed.');
  return source.slice(8,end);
}

export async function verifyNativeDelivery(source, {trustedPublicKey, plan, index} = {}) {
  if (source instanceof Uint8Array)
    requireThat(source.length <= MAX_NATIVE_BYTES, 'Native delivery exceeds its 2 MB byte limit.');
  const originalBytes = source instanceof Uint8Array ? source.slice() : null;
  source = nativeText(originalBytes || source);
  requireThat(typeof trustedPublicKey === 'string' && /^[0-9a-f]{64}$/i.test(trustedPublicKey),
    'Use an independently trusted Ed25519 worker public key.');
  const expected = verifyPlan(plan);
  requireThat(Number.isSafeInteger(index) && index >= 0 && index < expected.jobs.length,
    'Choose the exact routed plan index.');
  const envelope = parseNativeJSON(source);
  requireThat(exactKeys(envelope,['body','publicKey','signature']), 'Unsupported native delivery envelope.');
  requireThat(typeof envelope.publicKey === 'string' && envelope.publicKey.toLowerCase() === trustedPublicKey.toLowerCase(),
    'Native delivery signer differs from the independently trusted key.');
  const signedBody = signatureBody(source,envelope), body = envelope.body;
  requireThat(exactKeys(body,['schema','plan','jobIndex','nativeExport']) &&
    body.schema === 'agialpha.ascension.reviewed-delivery.v1', 'Unsupported native delivery body.');
  verifyPlan(body.plan);
  requireThat(canonicalJSON(body.plan) === canonicalJSON(expected) && body.jobIndex === index,
    'Native delivery belongs to another committed plan or job index.');
  const document = body.nativeExport?.receipt?.body?.document;
  requireThat(document?.state === 'completed' && document?.review?.approved === true &&
    document?.request?.goal === expected.jobs[index].spec.goal,
  'Native delivery must bind a completed, locally approved mission with this exact committed goal.');
  requireThat(typeof envelope.signature === 'string' && /^[A-Za-z0-9+/]{86}==$/.test(envelope.signature),
    'Malformed native Ed25519 signature.');
  const keyBytes = Uint8Array.from(trustedPublicKey.match(/../g),value => parseInt(value,16));
  const key = await crypto.subtle.importKey('raw',keyBytes,{name:'Ed25519'},false,['verify']);
  const signature = Uint8Array.from(atob(envelope.signature),char => char.charCodeAt(0));
  const digest = await crypto.subtle.digest('SHA-256',toUtf8Bytes(signedBody));
  requireThat(await crypto.subtle.verify('Ed25519',key,signature,digest), 'Native delivery signature verification failed.');
  return Object.freeze({resultHash:keccak256(originalBytes || toUtf8Bytes(source)),signer:trustedPublicKey.toLowerCase(),
    planRoot:expected.planRoot,index,signatureVerified:true,connected:false,executionReplayed:false,
    qualification:'Trusted signer and exact plan/index checked. Native verification must replay computation; independent on-chain review remains separate.'});
}
