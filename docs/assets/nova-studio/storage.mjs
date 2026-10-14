// SPDX-License-Identifier: Apache-2.0
import {canonicalJSON, hashObject} from '../ascension/crypto.mjs';
import {parseBoundedJSON, byteDigest, verifyPackage, MAX_DOCUMENT_BYTES} from './package.mjs';

export const PUBLICATION_SCHEMA = 'agialpha.novaseed.publication.v1';
export const UPLOAD_ENDPOINT = 'https://uploads.pinata.cloud/v3/files';
export const GATEWAYS = Object.freeze(['https://gateway.pinata.cloud', 'https://ipfs.io']);
export const PUBLIC_DISCLOSURE = 'Public metadata and evidence are readable by anyone. The capsule is encrypted, '
  + 'but committed job specifications become public when routed. A CID identifies content; retention and availability '
  + 'depend on your storage provider. The private recovery kit is not published.';
const encoder = new TextEncoder();
const cidPattern = /^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{20,100})$/;
const fail = message => { throw Error(message); };
const jsonHash = async value => '0x' + await hashObject(value);

export function artifactURI(value, gateway = GATEWAYS[0]) {
  if (!GATEWAYS.includes(gateway)) fail('Choose a supported IPFS gateway.');
  if (typeof value !== 'string' || encoder.encode(value).length > 512) fail('Artifact URI must fit 512 UTF-8 bytes.');
  let cid;
  if (value.startsWith('ipfs://')) cid = value.slice(7);
  else {
    let url;
    try { url = new URL(value); } catch { fail('Use an IPFS CID or supported HTTPS gateway URI.'); }
    if (!GATEWAYS.includes(url.origin) || url.protocol !== 'https:' || url.username || url.password ||
        url.search || url.hash || !url.pathname.startsWith('/ipfs/')) fail('Artifact destination is not an allowed gateway.');
    cid = url.pathname.slice(6);
  }
  if (!cidPattern.test(cid)) fail('Use a complete bare IPFS CID; placeholders, unsafe paths and query credentials are not allowed.');
  return {uri: `ipfs://${cid}`, url: `${gateway}/ipfs/${cid}`, cid};
}

async function boundedResponse(response, maxBytes) {
  if (!response.ok || response.redirected || response.type === 'opaqueredirect') fail('Storage request failed or redirected.');
  const length = response.headers?.get('content-length');
  if (length !== null && length !== undefined && (!/^[0-9]+$/.test(length) || Number(length) > maxBytes))
    fail('Remote artifact exceeds its byte limit.');
  const reader = response.body?.getReader?.();
  if (!reader) {
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.length > maxBytes) fail('Remote artifact exceeds its byte limit.');
    return bytes;
  }
  const chunks = [];
  let lengthSoFar = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      lengthSoFar += value.length;
      if (lengthSoFar > maxBytes) fail('Remote artifact exceeds its byte limit.');
      chunks.push(value);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  const bytes = new Uint8Array(lengthSoFar);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return bytes;
}

/** Real public IPFS uploads. The credential lives only in this instance and is never exported. */
export class PinataStorage {
  #token;
  #fetch;
  constructor({token = '', fetchImpl = globalThis.fetch, gateway = GATEWAYS[0]} = {}) {
    if (typeof token !== 'string' || token.length > 8192 || /\s/.test(token)) fail('Invalid storage credential.');
    if (typeof fetchImpl !== 'function' || !GATEWAYS.includes(gateway)) fail('Unsupported storage transport or gateway.');
    this.#token = token; this.#fetch = fetchImpl.bind(globalThis); this.gateway = gateway;
  }
  clearCredentials() { this.#token = ''; }
  async #request(url, options, maxBytes) {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await this.#fetch(url, {...options, mode: 'cors', credentials: 'omit',
        redirect: 'error', cache: 'no-store', referrerPolicy: 'no-referrer', signal: controller.signal});
      if (response.url && new URL(response.url).href !== new URL(url).href) fail('Storage response came from another destination.');
      return await boundedResponse(response, maxBytes);
    } catch {
      // Remote responses and provider error strings can echo credentials; never forward them to the UI or journal.
      fail('Storage upload or retrieval failed. Check the credential, provider availability, CORS and file size.');
    } finally { clearTimeout(timeout); }
  }
  async uploadJSON(value, name = 'artifact.json') {
    if (!this.#token) fail('Enter a session-only Pinata upload credential.');
    if (!/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}\.json$/.test(name)) fail('Use a safe JSON artifact filename.');
    const source = canonicalJSON(value), form = new FormData();
    form.append('file', new Blob([source], {type: 'application/json'}), name);
    form.append('network', 'public'); form.append('name', name);
    const response = await this.#request(UPLOAD_ENDPOINT,
      {method: 'POST', headers: {Authorization: `Bearer ${this.#token}`}, body: form}, 10000);
    const result = parseBoundedJSON(new TextDecoder('utf-8', {fatal: true}).decode(response), {maxBytes: 10000});
    const reference = artifactURI(`ipfs://${result?.data?.cid}`, this.gateway);
    const record = {uri: reference.uri, byteDigest: await byteDigest(source), canonicalHash: await jsonHash(value),
      bytes: encoder.encode(source).length};
    await this.readJSON(record.uri, record);
    return record;
  }
  async readJSON(uri, expected = {}) {
    const reference = artifactURI(uri, this.gateway);
    const bytes = await this.#request(reference.url, {method: 'GET', headers: {Accept: 'application/json'}}, MAX_DOCUMENT_BYTES);
    let source;
    try { source = new TextDecoder('utf-8', {fatal: true}).decode(bytes); }
    catch { fail('Remote JSON has malformed UTF-8.'); }
    const value = parseBoundedJSON(source), digest = await byteDigest(bytes), canonicalHash = await jsonHash(value);
    if ((expected.byteDigest && digest !== expected.byteDigest) ||
        (expected.canonicalHash && canonicalHash !== expected.canonicalHash) ||
        (expected.bytes !== undefined && expected.bytes !== bytes.length)) fail('Retrieved artifact does not match its saved commitments.');
    return {value, uri: reference.uri, byteDigest: digest, canonicalHash, bytes: bytes.length};
  }
}

export function buildMetadata(pkg, {name, description = '', capsule, evidence}) {
  if (typeof name !== 'string' || !name.trim() || encoder.encode(name).length > 120 ||
      typeof description !== 'string' || encoder.encode(description).length > 2000) fail('Provide a public name (120 bytes maximum) and a short description (2000 bytes maximum).');
  return {
    schema: 'agialpha.novaseed.metadata.v1', name, description, chainId: pkg.profile.chainId,
    profile: pkg.profile.profile, profileHash: pkg.commitments.profileHash,
    seedContract: pkg.profile.contracts.Seed.address.toLowerCase(),
    capsule: {uri: artifactURI(capsule.uri).uri, hash: pkg.commitments.capsuleHash,
      byteDigest: capsule.byteDigest, innerCommitment: pkg.commitments.innerCommitment},
    plan: {root: pkg.plan.planRoot, count: pkg.plan.jobs.length, totalBounty: pkg.plan.totalBounty},
    evidence: {uri: artifactURI(evidence.uri).uri, hash: pkg.commitments.evidenceHash, byteDigest: evidence.byteDigest},
    disclosure: PUBLIC_DISCLOSURE,
  };
}

function verifyMetadata(pkg, metadata) {
  const expected = buildMetadata(pkg, {name: metadata?.name, description: metadata?.description,
    capsule: metadata?.capsule || {}, evidence: metadata?.evidence || {}});
  if (canonicalJSON(expected) !== canonicalJSON(metadata) ||
      metadata.capsule.byteDigest !== pkg.commitments.capsuleByteDigest)
    fail('Metadata does not bind this exact capsule, plan, evidence and deployment.');
}

export async function publishPackage(pkg, {adapter, name, description = '', disclosureAccepted = false}) {
  if (disclosureAccepted !== true) fail('Review and confirm the public metadata and evidence before uploading.');
  await verifyPackage(pkg);
  if (!adapter?.uploadJSON || !adapter?.readJSON) fail('Select an artifact storage adapter.');
  const capsule = await adapter.uploadJSON(pkg.capsule, 'nova-capsule.json');
  const evidence = await adapter.uploadJSON(pkg.evidence, 'nova-evidence.json');
  const metadata = buildMetadata(pkg, {name, description, capsule, evidence});
  const record = await adapter.uploadJSON(metadata, 'nova-metadata.json');
  return verifyPublication(pkg, {
    schema: PUBLICATION_SCHEMA, metadataURI: record.uri, capsuleURI: capsule.uri, evidenceURI: evidence.uri,
    metadata, artifacts: {capsule, evidence, metadata: record}, verifiedAt: new Date().toISOString(),
  }, {adapter});
}

export async function verifyPublication(pkg, publication, {adapter = new PinataStorage()} = {}) {
  await verifyPackage(pkg);
  if (!publication || publication.schema !== PUBLICATION_SCHEMA || !publication.artifacts)
    fail('Import a complete verified publication record.');
  verifyMetadata(pkg, publication.metadata);
  for (const [name, uri] of [['capsule', publication.capsuleURI], ['evidence', publication.evidenceURI],
    ['metadata', publication.metadataURI]]) {
    if (artifactURI(uri).uri !== publication.artifacts[name]?.uri) fail('Publication URI association mismatch.');
  }
  if (publication.capsuleURI !== publication.metadata.capsule.uri ||
      publication.evidenceURI !== publication.metadata.evidence.uri) fail('Metadata artifact references do not match publication.');
  const [capsule, evidence, metadata] = await Promise.all([
    adapter.readJSON(publication.capsuleURI, publication.artifacts.capsule),
    adapter.readJSON(publication.evidenceURI, publication.artifacts.evidence),
    adapter.readJSON(publication.metadataURI, publication.artifacts.metadata),
  ]);
  if (canonicalJSON(capsule.value) !== canonicalJSON(pkg.capsule) ||
      canonicalJSON(evidence.value) !== canonicalJSON(pkg.evidence) ||
      canonicalJSON(metadata.value) !== canonicalJSON(publication.metadata) ||
      capsule.byteDigest !== pkg.commitments.capsuleByteDigest ||
      evidence.byteDigest !== publication.metadata.evidence.byteDigest)
    fail('Published content changed or belongs to another package.');
  return {...publication, verifiedAt: new Date().toISOString()};
}

export async function importPublication(pkg, metadataURI, {adapter = new PinataStorage()} = {}) {
  await verifyPackage(pkg);
  const metadata = await adapter.readJSON(metadataURI);
  verifyMetadata(pkg, metadata.value);
  const capsule = await adapter.readJSON(metadata.value.capsule.uri,
    {canonicalHash: pkg.commitments.capsuleHash, byteDigest: metadata.value.capsule.byteDigest});
  const evidence = await adapter.readJSON(metadata.value.evidence.uri,
    {canonicalHash: pkg.commitments.evidenceHash, byteDigest: metadata.value.evidence.byteDigest});
  const record = ({value: ignored, ...artifact}) => artifact;
  return verifyPublication(pkg, {
    schema: PUBLICATION_SCHEMA, metadataURI: metadata.uri, capsuleURI: capsule.uri, evidenceURI: evidence.uri,
    metadata: metadata.value, artifacts: {capsule: record(capsule), evidence: record(evidence), metadata: record(metadata)},
    verifiedAt: new Date().toISOString(),
  }, {adapter});
}
