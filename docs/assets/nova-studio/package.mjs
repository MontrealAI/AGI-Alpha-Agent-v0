// SPDX-License-Identifier: Apache-2.0
import {canonicalJSON, hashObject, sealSeed, openSeed} from '../ascension/crypto.mjs';
import {verifyPlan} from './plan.mjs';
import {deploymentDescriptor} from '../ascension-wallet/client.mjs';

export const PACKAGE_SCHEMA = 'agialpha.novaseed.executable-package.v1';
export const KIT_SCHEMA = 'agialpha.novaseed.recovery-kit.v1';
export const MAX_DOCUMENT_BYTES = 250000;
export const MAX_PACKAGE_BYTES = 1000000;
export const MAX_KIT_BYTES = 2000000;
const encoder = new TextEncoder();
const recovered = new Set();
const forbidden = new Set(['__proto__', 'prototype', 'constructor']);
const secret = /^(passphrase|password|private_?key|mnemonic|seed_?phrase|wallet_?secret|api_?key|jwt|authorization|access_?token|refresh_?token)$/i;
const hash = value => /^0x[0-9a-f]{64}$/.test(value);
const fail = message => { throw Error(message); };

function validUnicode(value) {
  for (let i = 0; i < value.length; i++) {
    const n = value.charCodeAt(i);
    if (n >= 0xd800 && n <= 0xdbff) {
      const next = value.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) fail('Malformed Unicode is not accepted.');
    } else if (n >= 0xdc00 && n <= 0xdfff) fail('Malformed Unicode is not accepted.');
  }
  return value;
}

/** Parse bounded JSON without allowing duplicate keys to change the committed interpretation. */
export function parseBoundedJSON(source, {maxBytes = MAX_DOCUMENT_BYTES, maxDepth = 24,
  preserveUnsafeIntegers = false} = {}) {
  if (typeof source !== 'string' || encoder.encode(source).length > maxBytes) fail('JSON exceeds its byte limit.');
  let cursor = 0;
  const whitespace = () => { while (/^[\x20\x09\x0a\x0d]$/.test(source[cursor] || '')) cursor++; };
  function string() {
    const start = cursor++;
    while (cursor < source.length) {
      const character = source[cursor++];
      if (character === '\\') { cursor++; continue; }
      if (character === '"') {
        try { return validUnicode(JSON.parse(source.slice(start, cursor))); }
        catch { fail('Invalid JSON string or Unicode.'); }
      }
    }
    fail('Unterminated JSON string.');
  }
  function value(depth) {
    if (depth > maxDepth) fail('JSON nesting exceeds its limit.');
    whitespace();
    const character = source[cursor];
    if (character === '"') return string();
    if (character === '{' || character === '[') {
      const object = character === '{', result = object ? {} : [], keys = new Set();
      const ending = object ? '}' : ']';
      cursor++; whitespace();
      if (source[cursor] === ending) { cursor++; return result; }
      while (cursor < source.length) {
        if (object) {
          whitespace();
          if (source[cursor] !== '"') fail('Expected a JSON object key.');
          const key = string();
          if (forbidden.has(key) || keys.has(key)) fail('Duplicate or unsafe JSON object key.');
          keys.add(key); whitespace();
          if (source[cursor++] !== ':') fail('Expected a colon after a JSON key.');
          result[key] = value(depth + 1);
        } else result.push(value(depth + 1));
        whitespace();
        const next = source[cursor++];
        if (next === ending) return result;
        if (next !== ',') fail('Expected a JSON separator.');
      }
      fail('Unterminated JSON object or array.');
    }
    for (const [literal, decoded] of [['true', true], ['false', false], ['null', null]]) {
      if (source.startsWith(literal, cursor)) { cursor += literal.length; return decoded; }
    }
    const match = source.slice(cursor).match(/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/);
    if (!match) fail('Invalid JSON value.');
    cursor += match[0].length;
    const number = Number(match[0]);
    if (preserveUnsafeIntegers === true && /^-?(?:0|[1-9][0-9]*)$/.test(match[0]) && !Number.isSafeInteger(number))
      return match[0];
    if (!Number.isFinite(number) || (Number.isInteger(number) && !Number.isSafeInteger(number)))
      fail('JSON numbers must be finite and exact; use decimal strings for large integers.');
    return number;
  }
  const result = value(0); whitespace();
  if (cursor !== source.length) fail('Unexpected data after JSON.');
  return result;
}

/** Canonical kit envelope only; the existing capsule hash always uses canonicalJSON/hashObject. */
export function canonicalEnvelope(value, maxBytes = MAX_KIT_BYTES) {
  const seen = new Set();
  function visit(item, depth = 0) {
    if (depth > 24) fail('Document nesting exceeds 24 levels.');
    if (item === null || typeof item === 'boolean') return item;
    if (typeof item === 'string') return validUnicode(item);
    if (typeof item === 'number') {
      if (!Number.isFinite(item) || (Number.isInteger(item) && !Number.isSafeInteger(item)))
        fail('Use exact JSON numbers or integer strings.');
      return item;
    }
    if (!item || typeof item !== 'object' || seen.has(item)) fail('Document must contain acyclic JSON data.');
    seen.add(item);
    let result;
    if (Array.isArray(item)) {
      if (Object.keys(item).length !== item.length || !Array.from({length: item.length}, (_, i) => Object.hasOwn(item, i)).every(Boolean))
        fail('Sparse or extended arrays are not allowed.');
      result = item.map(part => visit(part, depth + 1));
    } else {
      if (![Object.prototype, null].includes(Object.getPrototypeOf(item))) fail('Only plain JSON objects are allowed.');
      result = {};
      for (const key of Object.keys(item).sort()) {
        validUnicode(key);
        if (forbidden.has(key)) fail('Unsafe JSON object key.');
        result[key] = visit(item[key], depth + 1);
      }
    }
    seen.delete(item);
    return result;
  }
  const result = JSON.stringify(visit(value));
  if (encoder.encode(result).length > maxBytes) fail('Document exceeds its byte limit; reduce its content or split the project.');
  return result;
}

export async function byteDigest(bytes) {
  const input = typeof bytes === 'string' ? encoder.encode(bytes) : bytes;
  if (!(input instanceof Uint8Array)) fail('A UTF-8 string or byte array is required.');
  return '0x' + [...new Uint8Array(await crypto.subtle.digest('SHA-256', input))]
    .map(byte => byte.toString(16).padStart(2, '0')).join('');
}

function noSecrets(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key, item] of Object.entries(value)) {
    if (secret.test(key)) fail('Exports cannot contain passphrases, wallet secrets or service credentials.');
    noSecrets(item);
  }
}
function exactKeys(value, fields, label) {
  if (!value || Array.isArray(value) || typeof value !== 'object' || Object.keys(value).length !== fields.length ||
      !fields.every(field => Object.hasOwn(value, field))) fail(`Unsupported ${label} schema.`);
}
function frozen(value) {
  if (value && typeof value === 'object') { for (const item of Object.values(value)) frozen(item); Object.freeze(value); }
  return value;
}
function profileIdentity(profile) {
  if (!profile || typeof profile.profile !== 'string' || !profile.profile.length ||
      !Number.isSafeInteger(profile.chainId) || profile.chainId < 1 ||
      !/^0x[0-9a-fA-F]{40}$/.test(profile.contracts?.Seed?.address)) fail('An exact chain/profile/Seed identity is required.');
  noSecrets(profile);
  return profile;
}
async function commitments(capsule, plan, evidence, profile) {
  const capsuleBytes = canonicalJSON(capsule);
  return {
    capsuleHash: '0x' + await hashObject(capsule), innerCommitment: '0x' + capsule.commitment,
    capsuleByteDigest: await byteDigest(capsuleBytes), planRoot: plan.planRoot,
    evidenceHash: '0x' + await hashObject(evidence), profileHash: '0x' + await hashObject(deploymentDescriptor(profile)),
  };
}

const recoveryIdentity = pkg => [pkg?.commitments?.capsuleHash, pkg?.commitments?.planRoot,
  pkg?.commitments?.profileHash, pkg?.commitments?.evidenceHash].join(':');
export function isRecoveryVerified(pkg) { return !!pkg?.commitments && recovered.has(recoveryIdentity(pkg)); }
export function clearRecoveryState() { recovered.clear(); }

export async function preparePackage({genome, plan, passphrase, evidence, profile}) {
  const exactPlan = verifyPlan(plan);
  profileIdentity(profile);
  if (genome?.schema !== 'agialpha.novaseed.genome.v1') fail('Use the compatible Nova-Seed genome schema.');
  noSecrets(genome); noSecrets(evidence);
  if (!evidence || typeof evidence !== 'object' || Array.isArray(evidence) || !Object.keys(evidence).length)
    fail('Provide public evidence before sealing.');
  const payload = parseBoundedJSON(canonicalJSON({...genome, onchain_plan: exactPlan}));
  // Preserve the established whole-capsule hash limit, including the authenticated header and base64 expansion.
  const plaintextBytes = encoder.encode(canonicalJSON({blind: 'A'.repeat(44), payload})).length;
  if (Math.ceil((plaintextBytes + 16) / 3) * 4 + 700 > MAX_DOCUMENT_BYTES)
    fail('Encrypted package would exceed the compatible 250 KB capsule limit. Shorten text or split the project.');
  const capsule = await sealSeed(payload, passphrase);
  const reopened = await openSeed(capsule, passphrase);
  if (canonicalJSON(reopened) !== canonicalJSON(payload)) fail('Local capsule recovery did not reproduce the exact project.');
  const result = {
    schema: PACKAGE_SCHEMA, capsule, plan: exactPlan, evidence, profile,
    commitments: await commitments(capsule, exactPlan, evidence, profile), recoveryVerified: true,
  };
  const snapshot = parseBoundedJSON(canonicalEnvelope(result, MAX_PACKAGE_BYTES), {maxBytes: MAX_PACKAGE_BYTES});
  recovered.add(recoveryIdentity(snapshot));
  return frozen(snapshot);
}

export async function verifyPackage(pkg, {passphrase} = {}) {
  exactKeys(pkg, ['schema', 'capsule', 'plan', 'evidence', 'profile', 'commitments', 'recoveryVerified'], 'executable package');
  if (pkg.schema !== PACKAGE_SCHEMA || typeof pkg.recoveryVerified !== 'boolean') fail('Unsupported executable package.');
  canonicalEnvelope(pkg, MAX_PACKAGE_BYTES); noSecrets(pkg);
  verifyPlan(pkg.plan); profileIdentity(pkg.profile);
  exactKeys(pkg.capsule, ['schema', 'cipher', 'kdf', 'iterations', 'salt', 'iv', 'commitment', 'ciphertext'], 'capsule');
  if (pkg.capsule.schema !== 'agialpha.novaseed.sealed.v1' || pkg.capsule.cipher !== 'AES-256-GCM' ||
      pkg.capsule.kdf !== 'PBKDF2-HMAC-SHA256' || pkg.capsule.iterations !== 600000 ||
      !/^[0-9a-f]{64}$/.test(pkg.capsule.commitment)) fail('Unsupported capsule encryption.');
  for (const [field, size] of [['salt', 16], ['iv', 12], ['ciphertext', null]]) {
    const encoded = pkg.capsule[field];
    if (typeof encoded !== 'string' || encoded.length > 350000 ||
        !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encoded))
      fail('Invalid capsule encoding.');
    const decoded = atob(encoded);
    if (btoa(decoded) !== encoded || (size !== null && decoded.length !== size) ||
        (size === null && (decoded.length < 16 || decoded.length > MAX_DOCUMENT_BYTES + 16)))
      fail('Invalid capsule field length or encoding.');
  }
  if (canonicalJSON(pkg.commitments) !== canonicalJSON(await commitments(pkg.capsule, pkg.plan, pkg.evidence, pkg.profile)))
    fail('Package commitments do not match its exact artifacts or deployment.');
  if (passphrase !== undefined) {
    const payload = await openSeed(pkg.capsule, passphrase);
    if (!payload.onchain_plan || canonicalJSON(verifyPlan(payload.onchain_plan)) !== canonicalJSON(pkg.plan))
      fail('The encrypted capsule does not contain this exact FusionPlan.');
    recovered.add(recoveryIdentity(pkg));
  }
  return pkg;
}

export async function convertLegacyCapsule(original, passphrase, {plan, evidence, profile}) {
  const genome = await openSeed(original, passphrase);
  if (genome.onchain_plan) fail('This capsule already contains a plan. Resume it using its matching package.');
  return {original, package: await preparePackage({genome, plan, passphrase, evidence, profile})};
}

export const RECOVERY_GUIDE = 'Keep this kit private: its exact plan and proofs are plaintext. The capsule remains encrypted. '
  + 'Store its passphrase separately; this is never your wallet recovery phrase. Open Nova Studio, import this kit and '
  + 'decrypt the capsule locally. Verify the deployment and refresh live chain state before continuing. Imported receipts '
  + 'and checksums are untrusted until reconciled; checksums are not signatures. An uncertain transaction must be reconciled '
  + 'before any resend. NFT ownership, capsule possession and campaign authority are distinct. Restoring never signs.';

export async function createRecoveryKit(pkg, {publication = null, ids = {}, receipts = [], journal = null,
  disclosureAccepted = false} = {}) {
  if (disclosureAccepted !== true) fail('Confirm the recovery kit contains your plaintext plan/proofs and must remain private.');
  await verifyPackage(pkg);
  if (!isRecoveryVerified(pkg)) fail('Decrypt and verify this capsule locally before exporting the recovery kit.');
  if (!Array.isArray(receipts) || receipts.length > 100) fail('At most 100 receipt records belong in one recovery kit.');
  const content = {package: pkg, publication, ids, receipts, journal, guide: RECOVERY_GUIDE};
  noSecrets(content);
  const text = canonicalEnvelope(content);
  const kit = {schema: KIT_SCHEMA, checksum: await byteDigest(text), content};
  canonicalEnvelope(kit);
  return kit;
}

export async function restoreRecoveryKit(source, {passphrase} = {}) {
  const kit = typeof source === 'string' ? parseBoundedJSON(source, {maxBytes: MAX_KIT_BYTES}) :
    parseBoundedJSON(canonicalEnvelope(source), {maxBytes: MAX_KIT_BYTES});
  exactKeys(kit, ['schema', 'checksum', 'content'], 'recovery kit');
  if (kit.schema !== KIT_SCHEMA || !hash(kit.checksum) ||
      kit.checksum !== await byteDigest(canonicalEnvelope(kit.content))) fail('Recovery kit checksum failed.');
  exactKeys(kit.content, ['package', 'publication', 'ids', 'receipts', 'journal', 'guide'], 'recovery content');
  noSecrets(kit.content);
  if (kit.content.guide !== RECOVERY_GUIDE || !Array.isArray(kit.content.receipts) || kit.content.receipts.length > 100)
    fail('Invalid recovery guide or receipt list.');
  await verifyPackage(kit.content.package, {passphrase});
  return {...kit.content, recoveryVerified: isRecoveryVerified(kit.content.package), needsLiveReconciliation: true};
}
