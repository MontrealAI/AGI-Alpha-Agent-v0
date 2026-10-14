// SPDX-License-Identifier: Apache-2.0
import { canonicalJSON, hashObject, sealSeed, openSeed } from '../ascension/crypto.mjs';
import { compilePlan, verifyPlan } from './plan.mjs';
import { uint, TOKEN } from '../ascension-wallet/protocol.mjs';
import { deploymentDescriptor } from '../ascension-wallet/client.mjs';
const encoder = new TextEncoder();
export const PACKAGE_SCHEMA = 'agialpha.nova-studio.package.v1';
export const KIT_SCHEMA = 'agialpha.nova-studio.recovery.v1';
export const hashBytes = async bytes => '0x' + Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2,'0')).join('');
export const fileBytes = object => encoder.encode(canonicalJSON(object) + '\n');
export const objectHash = async object => '0x' + await hashObject(object);
export function strictJSON(text, maxBytes = 2000000, { historicalTimestamp = false } = {}) {
  if (typeof text !== 'string' || encoder.encode(text).length > maxBytes) throw Error('Import exceeds its size limit.');
  // Tokenize objects before JSON.parse so duplicate decoded keys cannot disappear.
  const tokens = text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+/g) || [];
  let pos = 0;
  function visit(depth = 0, path = []) {
    if (depth > 24) throw Error('Import exceeds 24 nesting levels.');
    const token = tokens[pos++];
    if (token === '{') {
      const seen = new Set();
      if (tokens[pos] !== '}') do {
        const key = JSON.parse(tokens[pos++]);
        if (typeof key !== 'string' || seen.has(key) || ['__proto__','prototype','constructor'].includes(key))
          throw Error('Duplicate or unsafe JSON key.');
        seen.add(key);
        if (tokens[pos++] !== ':') throw Error('Malformed JSON object.');
        visit(depth + 1, [...path,key]);
        if (tokens[pos] !== ',') break;
        pos++;
      } while (true);
      if (tokens[pos++] !== '}') throw Error('Malformed JSON object.');
    } else if (token === '[') {
      if (tokens[pos] !== ']') do {
        visit(depth + 1, [...path,'[]']);
        if (tokens[pos] !== ',') break;
        pos++;
      } while (true);
      if (tokens[pos++] !== ']') throw Error('Malformed JSON array.');
    } else {
      const value = JSON.parse(token);
      // A signed legacy journal stores nanoseconds as a uint64 JSON number.
      // Preserve that one metadata lexeme as an exact string in the parsed copy;
      // authenticate the original bytes separately, never a rounded reserialization.
      if (historicalTimestamp && path.length===1 && path[0]==='time_ns') {
        if (!/^[1-9][0-9]*$/.test(token) || BigInt(token)>=(1n<<64n)) throw Error('Invalid exact historical timestamp.');
        tokens[pos-1]=JSON.stringify(token);
      } else if (typeof value === 'number' && !Number.isSafeInteger(value))
        throw Error('Use exact integer strings for large values.');
    }
  }
  visit();
  if (pos !== tokens.length) throw Error('Unexpected trailing JSON.');
  return JSON.parse(historicalTimestamp?tokens.join(''):text);
}
export function profileIdentity(profile) {
  return deploymentDescriptor(profile);
}
function legacyProfileIdentity(profile) {
  return { chainId:profile.chainId, profile:profile.profile,
    contracts:{Token:TOKEN.toLowerCase(),...Object.fromEntries(Object.entries(profile.contracts).map(([k,v]) => [k,v.address.toLowerCase()]))} };
}
export function deploymentIdentityStatus(pkg, profile) {
  if (canonicalJSON(pkg?.deployment) === canonicalJSON(profileIdentity(profile))) return 'exact-source';
  if (canonicalJSON(pkg?.deployment) === canonicalJSON(legacyProfileIdentity(profile))) return 'legacy-addresses';
  throw Error('Package belongs to another deployment or source identity.');
}
export async function createPackage({ title, description, jobs, evidence, parent = '0', legacyGenome = null }, passphrase, profile) {
  if (typeof title !== 'string' || !title.trim() || encoder.encode(title).length > 160 ||
      typeof description !== 'string' || encoder.encode(description).length > 12000)
    throw Error('Use a project title up to 160 UTF-8 bytes and a description up to 12 KB.');
  if (typeof evidence !== 'string' || !evidence.trim() || encoder.encode(evidence).length > 8000)
    throw Error('Describe public verification evidence (1–8,000 UTF-8 bytes).');
  const plan = compilePlan(jobs), deployment = profileIdentity(profile);
  const publicEvidence = { schema:'agialpha.nova-studio.evidence.v1', deployment, planRoot:plan.planRoot, description:evidence };
  const evidenceHash = await objectHash(publicEvidence);
  const genome = { ...(legacyGenome || {}), schema:'agialpha.novaseed.genome.v1',
    project:{title,description}, onchain_plan:plan, deployment, evidenceHash, parent:uint(parent).toString() };
  // Budget before encryption includes base64 expansion and the authenticated header.
  if (encoder.encode(canonicalJSON(genome)).length > 180000)
    throw Error('Encrypted package would exceed the compatible 250 KB capsule limit. Shorten job text or split the project.');
  const capsule = await sealSeed(genome, passphrase);
  const reopened = await openSeed(capsule, passphrase);
  if (canonicalJSON(reopened) !== canonicalJSON(genome)) throw Error('Local recovery round trip failed.');
  const result = { schema:PACKAGE_SCHEMA, deployment, capsule, plan, evidence:publicEvidence,
    capsuleHash:await objectHash(capsule), capsuleByteHash:await hashBytes(fileBytes(capsule)),
    evidenceHash, parent:uint(parent).toString() };
  await verifyPackage(result);
  return result;
}
export async function verifyPackage(pkg, profile = null) {
  if (pkg?.schema !== PACKAGE_SCHEMA || !pkg.deployment || !Number.isSafeInteger(pkg.deployment.chainId)) throw Error('Unsupported project package.');
  const keys=['schema','deployment','capsule','plan','evidence','capsuleHash','capsuleByteHash','evidenceHash','parent'];
  if (Object.keys(pkg).sort().join()!==keys.sort().join()) throw Error('Unexpected package fields. Import only the supported public/encrypted schema.');
  // Address-only v1 kits remain readable without rewriting their encrypted or public commitments.
  // A workflow must require exact-source identity before authorizing a new mint.
  if (profile) deploymentIdentityStatus(pkg,profile);
  verifyPlan(pkg.plan); uint(pkg.parent);
  if (pkg.capsule?.schema !== 'agialpha.novaseed.sealed.v1' ||
      await objectHash(pkg.capsule) !== pkg.capsuleHash || await hashBytes(fileBytes(pkg.capsule)) !== pkg.capsuleByteHash ||
      await objectHash(pkg.evidence) !== pkg.evidenceHash || pkg.evidence.planRoot !== pkg.plan.planRoot ||
      canonicalJSON(pkg.evidence.deployment) !== canonicalJSON(pkg.deployment)) throw Error('Package commitments do not match.');
  return pkg;
}
export async function recoverPackage(pkg, passphrase, profile = null) {
  await verifyPackage(pkg, profile);
  const genome = await openSeed(pkg.capsule, passphrase);
  if (canonicalJSON(genome.onchain_plan) !== canonicalJSON(pkg.plan) ||
      canonicalJSON(genome.deployment) !== canonicalJSON(pkg.deployment) ||
      genome.evidenceHash !== pkg.evidenceHash || genome.parent !== pkg.parent)
    throw Error('Encrypted plan and public package disagree.');
  return genome;
}
export const RECOVERY_GUIDE = 'Keep this file private: it includes job specifications, encrypted capsule and public wallet associations. Keep the capsule passphrase separately; never enter a wallet recovery phrase. Import in Nova-Seed Studio, decrypt locally, then refresh canonical chain state. Journal status and checksums are editable recovery aids, not authorization or chain evidence. Investigate unknown submissions in your wallet before any new send. Do not reseal or mint again to repair an uncertain transaction.';
export async function exportKit(pkg, { publication = null, seedId = null, jobIds = [], journal = null } = {}) {
  await verifyPackage(pkg);
  const body = { schema:KIT_SCHEMA, package:pkg, publication, seedId, jobIds, journal, guide:RECOVERY_GUIDE };
  // Kit can exceed the legacy per-object 250 KB limit; checksum exact body JSON bytes.
  const serialized = JSON.stringify(body);
  if (encoder.encode(serialized).length > 1900000) throw Error('Recovery kit exceeds 1.9 MB. Export the journal separately.');
  return { body:JSON.parse(serialized), sha256:await hashBytes(encoder.encode(serialized)) };
}
export async function importKit(text, profile = null) {
  const kit = strictJSON(text);
  if (!kit || Object.keys(kit).sort().join()!=='body,sha256' || !kit.body ||
      Object.keys(kit.body).sort().join()!==['schema','package','publication','seedId','jobIds','journal','guide'].sort().join())
    throw Error('Unexpected recovery kit fields.');
  if (kit?.body?.schema !== KIT_SCHEMA || kit.sha256 !== await hashBytes(encoder.encode(JSON.stringify(kit.body))))
    throw Error('Recovery kit checksum or schema mismatch.');
  await verifyPackage(kit.body.package, profile);
  if (kit.body.seedId !== null) uint(kit.body.seedId);
  if (!Array.isArray(kit.body.jobIds) || kit.body.jobIds.length > 128) throw Error('Invalid recovered jobs.');
  for (const id of kit.body.jobIds) uint(id);
  return kit.body;
}
