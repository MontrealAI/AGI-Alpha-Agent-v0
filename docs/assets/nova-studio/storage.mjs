// SPDX-License-Identifier: Apache-2.0
import { fileBytes, hashBytes, objectHash, strictJSON, verifyPackage } from './package.mjs';
import { canonicalJSON } from '../ascension/crypto.mjs';
export const GATEWAYS = Object.freeze(['https://gateway.pinata.cloud/ipfs/', 'https://ipfs.io/ipfs/']);
const CID = /^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{40,110})$/;
export function artifactURI(uri) {
  if (typeof uri !== 'string' || new TextEncoder().encode(uri).length > 512 || !uri.startsWith('ipfs://') || !CID.test(uri.slice(7)))
    throw Error('Use an immutable ipfs:// CID without a path, query, credentials or placeholder.');
  return uri;
}
async function boundedResponse(response, maximum) {
  if (!response.ok || response.redirected) throw Error('Artifact service did not return a direct successful response.');
  if (Number(response.headers.get('content-length')) > maximum) throw Error('Artifact exceeds its size limit.');
  const reader = response.body?.getReader();
  if (!reader) throw Error('Streaming artifact retrieval is required.');
  const chunks = []; let length = 0;
  while (true) {
    const {done,value} = await reader.read(); if (done) break;
    length += value.length;
    if (length > maximum) { await reader.cancel(); throw Error('Artifact exceeds its size limit.'); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const part of chunks) { bytes.set(part,offset); offset += part.length; }
  return bytes;
}
export class PinataStorage {
  constructor(fetcher = globalThis.fetch) {
    if (typeof fetcher !== 'function') throw Error('A supported storage transport is required.');
    // Native browser fetch requires its Window receiver. Test arrow wrappers must not mask this boundary.
    this.fetcher = fetcher.bind(globalThis);
  }
  async publish(object, name, credential) {
    return this.publishBytes(fileBytes(object),name,credential);
  }
  async publishBytes(bytes, name, credential) {
    if (!(bytes instanceof Uint8Array) || !bytes.length || bytes.length>2000000) throw Error('Publish exact bytes between 1 byte and 2 MB.');
    if (typeof name!=='string' || !/^[A-Za-z0-9._-]{1,100}$/.test(name)) throw Error('Use a simple public artifact filename.');
    if (typeof credential !== 'string' || credential.length < 16 || credential.length > 8000 || /\s/.test(credential))
      throw Error('Enter a session-only Pinata upload token. It is sent only to Pinata.');
    const form = new FormData();
    form.append('network','public');
    form.append('file',new Blob([bytes],{type:'application/json'}),name);
    let value;
    try {
      const endpoint = 'https://uploads.pinata.cloud/v3/files';
      const response = await this.fetcher(endpoint, {
        method:'POST', headers:{Authorization:`Bearer ${credential}`}, body:form,
        redirect:'error', credentials:'omit', referrerPolicy:'no-referrer', signal:AbortSignal.timeout(60000)
      });
      if (response.url && response.url !== endpoint) throw Error('Unexpected upload destination.');
      value = strictJSON(new TextDecoder('utf-8',{fatal:true}).decode(await boundedResponse(response,32000)),32000);
    } catch {
      // Transport and parser errors can echo authorization data. Never propagate provider text.
      throw Error('Storage upload failed. Check the credential, provider availability, CORS and artifact size.');
    }
    return { uri:artifactURI(`ipfs://${value?.data?.cid}`), byteHash:await hashBytes(bytes), size:bytes.length };
  }
  async retrieveBytes(uri, gateway = GATEWAYS[0], maximum = 250001) {
    artifactURI(uri);
    if (!GATEWAYS.includes(gateway)) throw Error('Unreviewed storage gateway.');
    if (!Number.isSafeInteger(maximum) || maximum < 1 || maximum > 2000000) throw Error('Invalid artifact size limit.');
    let bytes;
    try {
      const endpoint = gateway + uri.slice(7);
      const response = await this.fetcher(endpoint, {
        cache:'no-store',redirect:'error',credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(30000)
      });
      if (response.url && response.url !== endpoint) throw Error('Unexpected retrieval destination.');
      bytes = await boundedResponse(response,maximum);
    } catch {
      throw Error('Storage retrieval failed. Check provider availability, CORS and artifact size.');
    }
    return { bytes, byteHash:await hashBytes(bytes) };
  }
  async retrieve(uri, gateway = GATEWAYS[0]) {
    const result=await this.retrieveBytes(uri,gateway);
    return {...result,object:strictJSON(new TextDecoder('utf-8',{fatal:true}).decode(result.bytes),250001)};
  }
}
export function metadataFor(pkg, capsuleURI, evidenceURI) {
  artifactURI(capsuleURI); artifactURI(evidenceURI);
  return { schema:'agialpha.nova-studio.metadata.v1', name:'Nova-Seed executable project',
    description:'Encrypted project with an immutable FusionPlan. Independent review and activation are separate.',
    deployment:pkg.deployment, capsule:{uri:capsuleURI, hash:pkg.capsuleHash, byteHash:pkg.capsuleByteHash},
    plan:{root:pkg.plan.planRoot, jobs:pkg.plan.jobs.length, totalBounty:pkg.plan.totalBounty},
    evidence:{uri:evidenceURI, hash:pkg.evidenceHash}, parent:pkg.parent };
}
export async function verifyPublication(pkg, publication, storage, { independent = false } = {}) {
  await verifyPackage(pkg);
  if (publication?.schema !== 'agialpha.nova-studio.publication.v1') throw Error('Publish and verify project artifacts first.');
  const expected = metadataFor(pkg,publication.capsuleURI,publication.evidenceURI);
  const sets = [[publication.capsuleURI,pkg.capsule],[publication.evidenceURI,pkg.evidence],[publication.metadataURI,expected]];
  for (const gateway of independent ? GATEWAYS : [GATEWAYS[0]]) {
    for (const [uri,object] of sets) {
      const fetched = await storage.retrieve(uri,gateway);
      if (fetched.byteHash !== await hashBytes(fileBytes(object)) || canonicalJSON(fetched.object) !== canonicalJSON(object))
        throw Error('Retrieved artifact differs from the exact published bytes.');
    }
  }
  if (publication.metadataHash !== await objectHash(expected)) throw Error('Metadata commitment changed.');
  return { ...publication, verifiedAt:new Date().toISOString(), independentRetrieval:independent };
}
export async function publishPackage(pkg, storage, credential, checkpoint = () => {}, existing = null) {
  await verifyPackage(pkg);
  const state = { schema:'agialpha.nova-studio.publication.v1', ...(existing || {}) };
  // Retain successful CIDs through interrupted publication; never reseal on retry.
  if (!state.capsuleURI) { state.capsuleURI = (await storage.publish(pkg.capsule,'nova-capsule.json',credential)).uri; checkpoint({...state}); }
  if (!state.evidenceURI) { state.evidenceURI = (await storage.publish(pkg.evidence,'nova-evidence.json',credential)).uri; checkpoint({...state}); }
  const metadata = metadataFor(pkg,state.capsuleURI,state.evidenceURI);
  state.metadataHash = await objectHash(metadata);
  if (!state.metadataURI) { state.metadataURI = (await storage.publish(metadata,'nova-metadata.json',credential)).uri; checkpoint({...state}); }
  return verifyPublication(pkg,state,storage);
}
