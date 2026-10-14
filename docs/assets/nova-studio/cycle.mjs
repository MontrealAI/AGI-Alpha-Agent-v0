// SPDX-License-Identifier: Apache-2.0
import { verifyPackage, objectHash, hashBytes, strictJSON, profileIdentity } from './package.mjs';
import { uint, address, curve } from '../ascension-wallet/protocol.mjs';
import { unresolved } from '../ascension-wallet/client.mjs';

export const PROJECT_SCHEMA = 'agialpha.nova-studio.project.v1';
export const PRIVATE_KIT_SCHEMA = 'agialpha.nova-studio.private-recovery.v1';
export const PROJECT_RECOVERY_GUIDE = 'This encrypted file preserves private project history, not current authority. Keep its passphrase separately; never use a wallet recovery phrase. Reopen the exact original packages, reconnect your wallet explicitly, refresh chain state, and obtain fresh runtime authorization. Signed historical bytes retain their original trust scope; an embedded key or successful decryption grants no authority. Never repeat an uncertain transaction, auto-run a recovered request, or adopt a recovered candidate without current verification.';
const encoder = new TextEncoder(), MAX_PROJECT_BYTES = 8000000, MAX_RECORD_BYTES = 1500000;
const ITERATIONS = 600000, observations = new WeakMap(), verifiedEvaluations = new WeakMap(), reservoirs = new WeakMap();
const verifiedRights = new WeakMap();
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const DIGEST = /^0x[0-9a-f]{64}$/;
const PROJECT_KEYS = ['schema','projectId','createdAt','title','opportunity','activeCycleId','cycles','guide'];
const CYCLE_KEYS = ['cycleId','ordinal','createdAt','parentCycleId','package','commitments','linkage','publication',
  'seedId','jobIds','journal','privateNotes','signedRecords','assets','evaluations','missions'];
const deniedKeys = new Set(['private_key','privateKey','mnemonic','seedPhrase','passphrase','api_key','apiKey',
  'storageCredential','storage_credential','controller_grant','activeGrant','active_grant','capabilityToken']);
const exact = (value, keys, label) => {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).sort().join() !== [...keys].sort().join()) throw Error(`Unexpected ${label} fields.`);
};
const text = (value, label, max = 8000, empty = false) => {
  if (typeof value !== 'string' || (!empty && !value.trim()) || encoder.encode(value).length > max)
    throw Error(`Invalid ${label}.`);
  return value;
};
const digest = value => { if (!DIGEST.test(value)) throw Error('Use an exact SHA-256 digest.'); return value; };
const uuid = value => { if (!UUID.test(value)) throw Error('Invalid project or cycle identity.'); return value; };
const instant = value => {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime()) || date.toISOString() !== value) throw Error('Use an exact ISO timestamp.');
  return value;
};
const timestamp = now => new Date(now ?? Date.now()).toISOString();
const bytesJSON = value => encoder.encode(JSON.stringify(value));
const clone = value => strictJSON(JSON.stringify(value), MAX_PROJECT_BYTES);
const same = (a,b) => JSON.stringify(a) === JSON.stringify(b);
export async function projectObjectHash(value) {
  const checked = strictJSON(JSON.stringify(value),2000000);
  const canonical = item => Array.isArray(item) ? '['+item.map(canonical).join(',')+']' :
    item && typeof item === 'object' ? '{'+Object.keys(item).sort().map(key=>JSON.stringify(key)+':'+canonical(item[key])).join(',')+'}' :
      JSON.stringify(item);
  const bytes = encoder.encode(canonical(checked));
  if (bytes.length > 2000000) throw Error('Project request exceeds 2 MB.');
  return hashBytes(bytes);
}
const cycleFor = (project,id) => {
  const cycle = project.cycles.find(item => item.cycleId === id);
  if (!cycle) throw Error('Cycle is not part of this project.');
  return cycle;
};
function noCredentials(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key,part] of Object.entries(value)) {
    if (deniedKeys.has(key)) throw Error('Recovery must not contain credentials or active controller grants.');
    noCredentials(part);
  }
}
async function packageIdentity(pkg) {
  await verifyPackage(pkg);
  // The outer package can exceed the legacy canonical object's 250 KB bound.
  // Its already verified commitments completely identify the unchanged v1 parts.
  const packageHash = await objectHash({schema:pkg.schema,deployment:pkg.deployment,capsuleHash:pkg.capsuleHash,
    capsuleByteHash:pkg.capsuleByteHash,planRoot:pkg.plan.planRoot,jobs:pkg.plan.jobs.length,evidenceHash:pkg.evidenceHash,parent:pkg.parent});
  return { packageHash, planRoot:pkg.plan.planRoot, capsuleHash:pkg.capsuleHash,
    evidenceHash:pkg.evidenceHash, deployment:clone(pkg.deployment) };
}
function emptyCycle(ordinal, now, parentCycleId = null) {
  return {cycleId:crypto.randomUUID(),ordinal,createdAt:timestamp(now),parentCycleId,package:null,commitments:null,
    linkage:null,publication:null,seedId:null,jobIds:[],journal:null,privateNotes:'',signedRecords:[],assets:[],
    evaluations:[],missions:[]};
}
export async function createProject(pkg = null, { title = 'My Nova-Seed project', opportunity = {}, now } = {}) {
  text(title,'project title',160);
  const cycle = emptyCycle(1,now);
  const project = {schema:PROJECT_SCHEMA,projectId:crypto.randomUUID(),createdAt:timestamp(now),title,
    opportunity:clone(opportunity),activeCycleId:cycle.cycleId,cycles:[cycle],guide:PROJECT_RECOVERY_GUIDE};
  return pkg ? updateCycle(project,cycle.cycleId,{package:pkg}) : validateProject(project);
}
export async function validateProject(value) {
  const project = clone(value);
  exact(project,PROJECT_KEYS,'project');
  if (project.schema !== PROJECT_SCHEMA) throw Error('Unsupported full-cycle project schema.');
  uuid(project.projectId); instant(project.createdAt); text(project.title,'project title',160);
  if (!project.opportunity || Array.isArray(project.opportunity) || typeof project.opportunity !== 'object')
    throw Error('Invalid opportunity record.');
  text(project.guide,'recovery guide',8000);
  if (!Array.isArray(project.cycles) || project.cycles.length < 1 || project.cycles.length > 32)
    throw Error('A project supports 1–32 complete cycles.');
  const ids = new Set(), allRecords = new Set(), allMissions = new Set(), allSettlements = new Set(), allResults = new Set();
  const missionIds = new Set(), evaluationIds = new Set();
  for (const cycle of project.cycles) {
    exact(cycle,CYCLE_KEYS,'cycle'); uuid(cycle.cycleId); instant(cycle.createdAt);
    if (ids.has(cycle.cycleId) || cycle.ordinal !== ids.size + 1) throw Error('Duplicate or reordered cycle identity.');
    if (cycle.parentCycleId !== null && !ids.has(cycle.parentCycleId)) throw Error('Parent must be an earlier cycle.');
    ids.add(cycle.cycleId); text(cycle.privateNotes,'private notes',32000,true);
    if (cycle.package) {
      if (!same(await packageIdentity(cycle.package),cycle.commitments)) throw Error('Original cycle commitments changed.');
    } else if (cycle.commitments || cycle.seedId || cycle.jobIds.length || cycle.publication) {
      throw Error('Attach the exact original package before its chain associations.');
    }
    if (cycle.seedId !== null && uint(cycle.seedId) === 0n) throw Error('A minted seed ID must be positive.');
    if (!Array.isArray(cycle.jobIds) || cycle.jobIds.length > 128 || new Set(cycle.jobIds).size !== cycle.jobIds.length)
      throw Error('Duplicate or excessive recovered jobs.');
    cycle.jobIds.forEach(id => { if (uint(id) === 0n) throw Error('A job ID must be positive.'); });
    validateLinkage(project,cycle);
    for (const key of ['signedRecords','assets','evaluations','missions'])
      if (!Array.isArray(cycle[key]) || cycle[key].length > 256) throw Error(`Too many ${key}.`);
    for (const record of cycle.signedRecords) {
      exact(record,['recordId','kind','originalText','sha256','trust'],'historical record');
      validateRecordKind(record.kind); text(record.originalText,'original signed bytes',MAX_RECORD_BYTES);
      noCredentials(strictJSON(record.originalText,MAX_RECORD_BYTES));
      if (record.sha256 !== await hashBytes(encoder.encode(record.originalText)) || record.recordId !== record.sha256 ||
          record.trust !== 'historical-unverified' || allRecords.has(record.recordId)) throw Error('Invalid or duplicate historical record.');
      allRecords.add(record.recordId);
    }
    const assetIds = new Set();
    for (const asset of cycle.assets) {
      validateAsset(asset);
      if (assetIds.has(asset.assetId)) throw Error('Duplicate reusable artifact.');
      assetIds.add(asset.assetId);
    }
    for (const evaluation of cycle.evaluations) {
      await validateEvaluation(evaluation);
      if (evaluationIds.has(evaluation.evaluationId)) throw Error('Evaluation IDs must be unique across all project cycles.');
      evaluationIds.add(evaluation.evaluationId);
    }
    const planIndices = new Set();
    for (const mission of cycle.missions) {
      validateMission(mission);
      if (missionIds.has(mission.missionId)) throw Error('Duplicate mission identity.');
      missionIds.add(mission.missionId);
      if (planIndices.has(mission.request.plan_index)) throw Error('A committed plan index has more than one frozen runtime request.');
      planIndices.add(mission.request.plan_index);
      if (mission.request.project_id !== project.projectId || mission.request.cycle_id !== cycle.cycleId ||
          !same(mission.request.plan,cycle.package?.plan) ||
          !Number.isSafeInteger(mission.request.plan_index) || !cycle.package.plan.jobs[mission.request.plan_index] ||
          mission.requestHash !== await projectObjectHash(mission.request) ||
          mission.inputDigest !== await projectObjectHash(mission.request.work_spec.inputs ?? {}) ||
          mission.objectiveDigest !== await projectObjectHash({goal:cycle.package.plan.jobs[mission.request.plan_index].spec.goal}))
        throw Error('Recovered mission identity or request changed.');
      if (mission.runId && allMissions.has(mission.runId)) throw Error('A run cannot satisfy two missions.');
      if (mission.runId) allMissions.add(mission.runId);
      if (mission.settlementId && allSettlements.has(mission.settlementId)) throw Error('Settlement is already attributed.');
      if (mission.settlementId) allSettlements.add(mission.settlementId);
      if (mission.resultDigest && allResults.has(mission.resultDigest)) throw Error('Cached output cannot satisfy a distinct mission.');
      if (mission.resultDigest) allResults.add(mission.resultDigest);
    }
  }
  const records = project.cycles.flatMap(cycle => cycle.signedRecords);
  for (const evaluation of project.cycles.flatMap(cycle => cycle.evaluations)) if (evaluation.evidence) {
    const record = records.find(item => item.recordId === evaluation.evidence.sourceRecordId);
    if (!record || record.kind !== 'evaluation' || record.originalText !== evaluation.evidence.originalReport)
      throw Error('Evaluation source record is absent or differs from its preserved original.');
  }
  if (!ids.has(project.activeCycleId)) throw Error('Active cycle is missing.');
  noCredentials(project);
  return project;
}
function validateLinkage(project,cycle) {
  if (cycle.parentCycleId === null) {
    if (cycle.linkage !== null) throw Error('An initial cycle has no inherited project lineage.');
    return;
  }
  if (!cycle.package) throw Error('A successor must have its own package.');
  const parent = cycleFor(project,cycle.parentCycleId), link = cycle.linkage;
  exact(link,['kind','parentCycleId','parentDeployment','parentSeedId'],'successor linkage');
  if (!parent.package || !parent.seedId || link.parentCycleId !== parent.cycleId ||
      !same(link.parentDeployment,parent.package.deployment) || link.parentSeedId !== parent.seedId)
    throw Error('Successor provenance does not identify the original parent.');
  const sameDeployment = same(parent.package.deployment,cycle.package.deployment);
  if (link.kind === 'same-contract-parent') {
    if (!sameDeployment || cycle.package.parent !== parent.seedId) throw Error('On-chain parent requires the exact same deployment.');
  } else if (link.kind === 'cross-deployment-provenance') {
    if (sameDeployment || cycle.package.parent !== '0') throw Error('Cross-deployment lineage is off-chain, with on-chain parent zero.');
  } else throw Error('Unsupported lineage relationship.');
}
export async function updateCycle(project,cycleId,patch) {
  const next = await validateProject(project), cycle = cycleFor(next,cycleId);
  const allowed = ['package','publication','seedId','jobIds','journal','privateNotes'];
  if (!patch || Object.keys(patch).some(key => !allowed.includes(key))) throw Error('Unsupported cycle update.');
  if (patch.package) {
    const identity = await packageIdentity(patch.package);
    if (cycle.commitments && !same(cycle.commitments,identity)) throw Error('Original package is immutable. Prepare a new cycle.');
    cycle.package = clone(patch.package); cycle.commitments = identity;
  } else if (Object.hasOwn(patch,'package')) throw Error('Cannot erase the original package.');
  for (const key of allowed.filter(key => key !== 'package')) {
    if (!Object.hasOwn(patch,key)) continue;
    if (key === 'seedId' && cycle.seedId && patch.seedId !== cycle.seedId) throw Error('Cannot replace a cycle’s seed identity.');
    if (key === 'jobIds' && cycle.jobIds.some(id => !patch.jobIds?.includes(id))) throw Error('Cannot erase existing job identities.');
    cycle[key] = clone(patch[key]);
  }
  return validateProject(next);
}
export async function addCycle(project,pkg,{parentCycleId = project.activeCycleId,linkage,now} = {}) {
  const next = await validateProject(project), parent = cycleFor(next,parentCycleId);
  if (!parent.package || !parent.seedId) throw Error('Restore the parent package and seed identity before preparing its successor.');
  const identity = await packageIdentity(pkg);
  if (next.cycles.some(cycle => cycle.commitments?.packageHash === identity.packageHash)) throw Error('A successor needs its own package.');
  if (identity.planRoot === parent.commitments.planRoot || identity.evidenceHash === parent.commitments.evidenceHash)
    throw Error('A successor needs a distinct exact plan and evidence.');
  const kind = same(parent.package.deployment,pkg.deployment) ? 'same-contract-parent' : 'cross-deployment-provenance';
  const cycle = emptyCycle(next.cycles.length+1,now,parentCycleId);
  cycle.package = clone(pkg); cycle.commitments = identity;
  cycle.linkage = linkage ? clone(linkage) : {kind,parentCycleId,parentDeployment:clone(parent.package.deployment),parentSeedId:parent.seedId};
  next.cycles.push(cycle); next.activeCycleId = cycle.cycleId;
  return validateProject(next);
}
function validateRecordKind(kind) {
  if (!['runtime-request','runtime-run','delivery','settlement','evaluation','review','artifact','preposting'].includes(kind))
    throw Error('Only historical execution/evidence records belong in recovery; no active grants.');
}
export async function preserveSignedRecord(project,{cycleId = project.activeCycleId,kind,originalText}) {
  validateRecordKind(kind); text(originalText,'original signed bytes',MAX_RECORD_BYTES);
  noCredentials(strictJSON(originalText,MAX_RECORD_BYTES));
  const next = await validateProject(project), cycle = cycleFor(next,cycleId), sha256 = await hashBytes(encoder.encode(originalText));
  for (const other of next.cycles) {
    const existing = other.signedRecords.find(record => record.sha256 === sha256);
    if (existing) {
      if (other.cycleId !== cycleId || existing.kind !== kind) throw Error('Historical bytes are already attributed to another cycle or purpose.');
      return next;
    }
  }
  cycle.signedRecords.push({recordId:sha256,kind,originalText,sha256,trust:'historical-unverified'});
  return validateProject(next);
}
export async function observeCycle(project,cycleId,chain,{now} = {}) {
  const cycle = cycleFor(await validateProject(project),cycleId);
  if (!cycle.package || !cycle.seedId) throw Error('A package and observed seed identity are needed for current chain inspection.');
  if (!same(profileIdentity(chain.client.profile),cycle.package.deployment)) throw Error('Select the cycle’s exact deployment.');
  const epoch = chain.client.epoch, state = await chain.seed(cycle.seedId,cycle.package);
  chain.client.guard(epoch);
  const observation = Object.freeze({projectId:project.projectId,cycleId,observedAt:timestamp(now),
    blockNumber:state.verification.blockNumber,blockHash:state.verification.blockHash});
  observations.set(observation,{projectId:project.projectId,cycleId,packageHash:cycle.commitments.packageHash,
    seedId:cycle.seedId,state,epoch,client:chain.client,observedAt:Date.parse(observation.observedAt)});
  return observation;
}
function currentObservation(project,cycle,observation,{now = Date.now(),maxAgeMs = 120000,currentBlockHash} = {}) {
  const known = observations.get(observation);
  if (!Number.isSafeInteger(maxAgeMs) || maxAgeMs < 0 || maxAgeMs > 300000) throw Error('Observation freshness must be at most five minutes.');
  if (!known || known.projectId !== project.projectId || known.cycleId !== cycle.cycleId ||
      known.packageHash !== cycle.commitments?.packageHash || known.seedId !== cycle.seedId ||
      known.client.epoch !== known.epoch || now < known.observedAt || now-known.observedAt > maxAgeMs ||
      (currentBlockHash && currentBlockHash !== known.state.verification.blockHash)) return null;
  return known.state;
}
export function projectCycleState(project,cycleId = project.activeCycleId,{observation,...context} = {}) {
  const cycle = cycleFor(project,cycleId), state = currentObservation(project,cycle,observation,context);
  const base = {projectId:project.projectId,cycleId,artifacts:cycle.package ? 'committed-local-package' : 'not-prepared',
    publication:cycle.publication ? 'requires-retrieval' : 'not-published',wallet:'not-observed',identity:'not-observed',
    ownership:'not-observed',seedReview:'not-observed',campaign:'not-observed',jobs:'not-observed',
    runtime:'requires-current-authorization',delivery:'not-observed',acceptance:'not-observed',settlement:'not-observed',
    claims:'requires-reconciliation',improvement:'not-adopted',evidence:'historical-only',
    seedId:cycle.seedId,jobIds:[...cycle.jobIds],fresh:false};
  if (!state) return base;
  const who = state.wallet?.account, phase = Number(state.campaign.phase), time = BigInt(state.verification.blockTime);
  return {...base,fresh:true,wallet:who || 'read-only',identity:state.wallet?.admitted ? 'currently-admitted' : 'not-admitted',
    ownership:who && address(who) === address(state.seedOwner) ? 'current-owner' : 'other-owner',
    seedReview:state.green ? 'currently-approved' : state.review && BigInt(state.review.until) <= time ? 'expired' : 'not-approved',
    campaign:['not-opened','funding','active','closed'][phase] || 'unknown',jobs:'refresh-each-assignment',
    evidence:'current-chain-observation',blockNumber:state.verification.blockNumber,blockHash:state.verification.blockHash};
}
const base64 = bytes => {
  let binary = '';
  for (let i=0;i<bytes.length;i+=16384) binary += String.fromCharCode(...bytes.subarray(i,i+16384));
  return btoa(binary);
};
function unbase64(value,length) {
  if (typeof value !== 'string' || value.length > Math.ceil((MAX_PROJECT_BYTES+16)/3)*4 || value.length%4 !== 0 ||
      !/^[A-Za-z0-9+/]*={0,2}$/.test(value)) throw Error('Invalid private recovery encoding.');
  const bytes = Uint8Array.from(atob(value),part => part.charCodeAt(0));
  if ((length !== undefined && bytes.length !== length) || base64(bytes) !== value) throw Error('Invalid private recovery field length.');
  return bytes;
}
async function deriveKey(passphrase,salt,usage) {
  if (typeof passphrase !== 'string' || passphrase.length < 12 || passphrase.length > 256)
    throw Error('Use a private recovery passphrase of 12–256 characters, kept outside the file.');
  const source = await crypto.subtle.importKey('raw',encoder.encode(passphrase),'PBKDF2',false,['deriveKey']);
  return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:ITERATIONS,hash:'SHA-256'},source,
    {name:'AES-GCM',length:256},false,[usage]);
}
function recoveryHeader(kit) {
  return {schema:kit.schema,cipher:kit.cipher,kdf:kit.kdf,iterations:kit.iterations,salt:kit.salt,iv:kit.iv};
}
export async function exportProjectKit(project,passphrase) {
  const snapshot = await validateProject(project), plaintext = bytesJSON(snapshot);
  if (plaintext.length > MAX_PROJECT_BYTES) throw Error('Private recovery exceeds 8 MB. Archive older evidence separately.');
  const header = {schema:PRIVATE_KIT_SCHEMA,cipher:'AES-256-GCM',kdf:'PBKDF2-HMAC-SHA256',iterations:ITERATIONS,
    salt:base64(crypto.getRandomValues(new Uint8Array(16))),iv:base64(crypto.getRandomValues(new Uint8Array(12)))};
  const key = await deriveKey(passphrase,unbase64(header.salt,16),'encrypt');
  const ciphertext = await crypto.subtle.encrypt({name:'AES-GCM',iv:unbase64(header.iv,12),
    additionalData:bytesJSON(header),tagLength:128},key,plaintext);
  return {...header,ciphertext:base64(new Uint8Array(ciphertext))};
}
export async function importProjectKit(raw,passphrase) {
  const kit = strictJSON(raw,Math.ceil((MAX_PROJECT_BYTES+16)/3)*4+2000);
  exact(kit,['schema','cipher','kdf','iterations','salt','iv','ciphertext'],'private recovery');
  if (kit.schema !== PRIVATE_KIT_SCHEMA || kit.cipher !== 'AES-256-GCM' || kit.kdf !== 'PBKDF2-HMAC-SHA256' ||
      kit.iterations !== ITERATIONS) throw Error('Unsupported or changed private recovery header.');
  const header = recoveryHeader(kit), salt = unbase64(header.salt,16), iv = unbase64(header.iv,12), data = unbase64(kit.ciphertext);
  if (data.length < 16 || data.length > MAX_PROJECT_BYTES+16) throw Error('Invalid private recovery size.');
  const key = await deriveKey(passphrase,salt,'decrypt');
  let decoded;
  try {
    const plain = await crypto.subtle.decrypt({name:'AES-GCM',iv,additionalData:bytesJSON(header),tagLength:128},key,data);
    decoded = strictJSON(new TextDecoder('utf-8',{fatal:true}).decode(plain),MAX_PROJECT_BYTES);
  } catch { throw Error('Could not open private recovery. Check the passphrase and file integrity.'); }
  return validateProject(decoded);
}

function validateAsset(asset) {
  exact(asset,['assetId','digest','kind','source','license','permittedUses','rightsEvidence','review','validUntil','revoked','scope'],
    'reusable artifact');
  text(asset.assetId,'asset ID',160); digest(asset.digest); text(asset.kind,'artifact kind',160);
  text(asset.source,'artifact provenance'); text(asset.license,'license',1000); digest(asset.rightsEvidence);
  text(asset.scope,'artifact scope'); instant(asset.validUntil);
  if (typeof asset.revoked !== 'boolean' || !Array.isArray(asset.permittedUses) || asset.permittedUses.length > 32)
    throw Error('Invalid artifact permissions.');
  asset.permittedUses.forEach(use => text(use,'permitted use',160));
  exact(asset.review,['decision','reviewer','evidenceDigest'],'artifact review');
  if (!['accepted','rejected','unreviewed'].includes(asset.review.decision)) throw Error('Invalid artifact review decision.');
  text(asset.review.reviewer,'reviewer',160); digest(asset.review.evidenceDigest);
}
export async function registerAsset(project,cycleId,asset) {
  validateAsset(asset);
  const next = await validateProject(project), cycle = cycleFor(next,cycleId);
  if (cycle.assets.some(existing => existing.assetId === asset.assetId)) throw Error('Artifact ID is already recorded.');
  cycle.assets.push(clone(asset)); return validateProject(next);
}
export function requireReuseRights(asset,{use = 'successor-input',now = Date.now(),licenseCompatible = false} = {}) {
  validateAsset(asset);
  if (asset.revoked || Date.parse(asset.validUntil) <= now || asset.review.decision !== 'accepted' ||
      !asset.permittedUses.includes(use) || !licenseCompatible)
    throw Error('Reuse requires current rights, compatible licensing and an accepted review for the declared use.');
  return {assetId:asset.assetId,digest:asset.digest,use,rightsEvidence:asset.rightsEvidence,scope:asset.scope};
}
export async function verifyReuseRights(project,cycleId,assetId,verifier,{use = 'successor-input',now = Date.now()} = {}) {
  const checked = await validateProject(project), asset = cycleFor(checked,cycleId).assets.find(item => item.assetId === assetId);
  if (!asset || typeof verifier !== 'function') throw Error('A current source and rights review is required.');
  const result = await verifier(clone(asset),use);
  if (!result || result.valid !== true || result.digest !== asset.digest || result.rightsEvidence !== asset.rightsEvidence ||
      result.licenseCompatible !== true) throw Error('Verifier did not establish the exact artifact’s current reuse rights.');
  text(result.source,'current rights review source');
  requireReuseRights(asset,{use,now,licenseCompatible:true});
  const token = Object.freeze({assetId,source:result.source});
  verifiedRights.set(token,{projectId:project.projectId,cycleId,assetId,digest:asset.digest,rightsEvidence:asset.rightsEvidence,
    use,verifiedAt:now});
  return token;
}
function requireAssetVerification(project,cycleId,asset,token,{use = 'successor-input',now = Date.now()} = {}) {
  const known = verifiedRights.get(token);
  if (!known || known.projectId !== project.projectId || known.cycleId !== cycleId || known.assetId !== asset.assetId ||
      known.digest !== asset.digest || known.rightsEvidence !== asset.rightsEvidence || known.use !== use ||
      now < known.verifiedAt || now-known.verifiedAt > 300000)
    throw Error('Imported rights and review claims require fresh rights verification before reuse.');
  return requireReuseRights(asset,{use,now,licenseCompatible:true});
}
function validateProtocol(protocol) {
  exact(protocol,['baselineDigest','candidateDigest','taskDigest','procedureDigest','resourceBudget','acceptance',
    'heldOut','expectedRunIds','rollbackDigest'],'frozen evaluation protocol');
  for (const key of ['baselineDigest','candidateDigest','taskDigest','procedureDigest','rollbackDigest']) digest(protocol[key]);
  if (protocol.baselineDigest === protocol.candidateDigest) throw Error('Compare distinct baseline and candidate artifacts.');
  for (const key of ['resourceBudget','acceptance']) {
    if (!protocol[key] || typeof protocol[key] !== 'object' || Array.isArray(protocol[key]) || !Object.keys(protocol[key]).length)
      throw Error('Freeze explicit evaluation budgets and acceptance rules.');
  }
  exact(protocol.heldOut,['method','evidenceDigest','tuningExposure'],'held-out protocol');
  text(protocol.heldOut.method,'held-out method'); digest(protocol.heldOut.evidenceDigest);
  if (typeof protocol.heldOut.tuningExposure !== 'boolean') throw Error('Declare evaluation leakage.');
  if (!Array.isArray(protocol.expectedRunIds) || !protocol.expectedRunIds.length || protocol.expectedRunIds.length > 128 ||
      new Set(protocol.expectedRunIds).size !== protocol.expectedRunIds.length) throw Error('Freeze every evaluation run in advance.');
  protocol.expectedRunIds.forEach(id => text(id,'evaluation run ID',160));
}
const evaluationFor = (project,id) => {
  const result = project.cycles.flatMap(cycle => cycle.evaluations).find(item => item.evaluationId === id);
  if (!result) throw Error('Evaluation is not part of this project.');
  return result;
};
const VERDICTS = ['PASS','FAIL','inconclusive','unauthorized','not-run'];
async function validateEvaluation(evaluation) {
  exact(evaluation,['evaluationId','frozenAt','protocol','protocolHash','evidence','decision'],'evaluation');
  uuid(evaluation.evaluationId); instant(evaluation.frozenAt); validateProtocol(evaluation.protocol);
  if (await objectHash(evaluation.protocol) !== evaluation.protocolHash) throw Error('Frozen evaluation criteria changed.');
  if (evaluation.evidence) {
    const evidence = evaluation.evidence;
    exact(evidence,['protocolHash','verdict','sourceRecordId','runIds','leakage','comparableBudgets','qualityRegressed',
      'missingCosts','originalReport','reportHash','effectiveVerdict'],'evaluation evidence');
    if (evidence.protocolHash !== evaluation.protocolHash || !VERDICTS.includes(evidence.verdict) ||
        !VERDICTS.includes(evidence.effectiveVerdict)) throw Error('Evaluation report does not bind its frozen protocol.');
    digest(evidence.sourceRecordId); text(evidence.originalReport,'original evaluation report',MAX_RECORD_BYTES);
    strictJSON(evidence.originalReport,MAX_RECORD_BYTES);
    if (await hashBytes(encoder.encode(evidence.originalReport)) !== evidence.reportHash) throw Error('Original evaluation bytes changed.');
    if (!Array.isArray(evidence.runIds) || new Set(evidence.runIds).size !== evidence.runIds.length ||
        evidence.runIds.some(id => !evaluation.protocol.expectedRunIds.includes(id))) throw Error('Unexpected evaluation run.');
    for (const key of ['leakage','comparableBudgets','qualityRegressed','missingCosts'])
      if (typeof evidence[key] !== 'boolean') throw Error('Declare evaluation limitations explicitly.');
    if (evidence.effectiveVerdict !== effectiveVerdict(evaluation.protocol,evidence)) throw Error('Evaluation limitations cannot be hidden.');
  }
  if (evaluation.decision) {
    exact(evaluation.decision,['decision','reviewer','rationale','recordedAt','reportHash','scope'],'adoption decision');
    if (!['adopt','retain-baseline','reject','defer'].includes(evaluation.decision.decision)) throw Error('Invalid adoption decision.');
    text(evaluation.decision.reviewer,'adoption reviewer',160); text(evaluation.decision.rationale,'adoption rationale');
    instant(evaluation.decision.recordedAt);
    if (evaluation.decision.scope !== 'historical-decision-requires-current-verification' ||
        evaluation.decision.reportHash !== (evaluation.evidence?.reportHash ?? null)) throw Error('Invalid decision evidence.');
    if (evaluation.decision.decision === 'adopt' && evaluation.evidence?.effectiveVerdict !== 'PASS')
      throw Error('A nonpassing candidate cannot be adopted.');
  }
}
function effectiveVerdict(protocol,evidence) {
  if (['unauthorized','not-run','FAIL'].includes(evidence.verdict)) return evidence.verdict;
  if (evidence.qualityRegressed) return 'FAIL';
  if (protocol.heldOut.tuningExposure || evidence.leakage || !evidence.comparableBudgets ||
      evidence.runIds.length !== protocol.expectedRunIds.length) return 'inconclusive';
  // Missing price telemetry does not erase quality evidence, but never proves savings.
  return evidence.verdict;
}
export async function freezeEvaluation(project,cycleId,protocol,{now} = {}) {
  validateProtocol(protocol);
  const next = await validateProject(project), cycle = cycleFor(next,cycleId);
  const protocolHash = await objectHash(protocol);
  if (cycle.evaluations.some(item => item.protocolHash === protocolHash)) throw Error('This comparison is already frozen.');
  cycle.evaluations.push({evaluationId:crypto.randomUUID(),frozenAt:timestamp(now),protocol:clone(protocol),protocolHash,
    evidence:null,decision:null});
  return validateProject(next);
}
export async function recordEvaluation(project,evaluationId,evidence) {
  const next = await validateProject(project), evaluation = evaluationFor(next,evaluationId);
  if (evaluation.evidence) throw Error('Retain every original report. Freeze a new comparison instead of replacing evidence.');
  const reportHash = await hashBytes(encoder.encode(evidence.originalReport));
  const record = next.cycles.flatMap(cycle => cycle.signedRecords).find(item => item.recordId === evidence.sourceRecordId);
  if (!record || record.kind !== 'evaluation' || record.originalText !== evidence.originalReport)
    throw Error('Preserve the exact original evaluation record before attaching its findings.');
  evaluation.evidence = {...clone(evidence),reportHash,effectiveVerdict:effectiveVerdict(evaluation.protocol,evidence)};
  return validateProject(next);
}
export async function verifyEvaluation(project,evaluationId,verifier) {
  const checked = await validateProject(project), evaluation = evaluationFor(checked,evaluationId);
  if (!evaluation.evidence || typeof verifier !== 'function') throw Error('A current separately trusted verifier is required.');
  const verdict = await verifier(clone(evaluation.protocol),evaluation.evidence.originalReport);
  if (!verdict || verdict.valid !== true || verdict.protocolHash !== evaluation.protocolHash ||
      verdict.reportHash !== evaluation.evidence.reportHash || verdict.verdict !== evaluation.evidence.effectiveVerdict)
    throw Error('Verifier did not validate the exact frozen comparison and original report.');
  text(verdict.source,'independently pinned verifier source');
  const token = Object.freeze({evaluationId,source:verdict.source});
  verifiedEvaluations.set(token,{projectId:project.projectId,evaluationId,protocolHash:evaluation.protocolHash,
    reportHash:evaluation.evidence.reportHash,verdict:evaluation.evidence.effectiveVerdict,verifiedAt:Date.now()});
  return token;
}
function requireVerifiedEvaluation(project,evaluation,token,now = Date.now()) {
  const known = verifiedEvaluations.get(token);
  if (!known || known.projectId !== project.projectId || known.evaluationId !== evaluation.evaluationId ||
      known.protocolHash !== evaluation.protocolHash || known.reportHash !== evaluation.evidence?.reportHash ||
      known.verdict !== 'PASS' || now < known.verifiedAt || now-known.verifiedAt > 300000)
    throw Error('Adoption requires fresh verification from a separately trusted source; imported decisions grant no authority.');
}
export async function decideEvaluation(project,evaluationId,{decision,reviewer,rationale,verified,now} = {}) {
  const next = await validateProject(project), evaluation = evaluationFor(next,evaluationId);
  if (evaluation.decision) throw Error('A decision is already preserved; record a new comparison to revise it.');
  if (decision === 'adopt') requireVerifiedEvaluation(next,evaluation,verified,now ?? Date.now());
  evaluation.decision = {decision,reviewer,rationale,recordedAt:timestamp(now),reportHash:evaluation.evidence?.reportHash ?? null,
    scope:'historical-decision-requires-current-verification'};
  return validateProject(next);
}
function validateMission(mission) {
  exact(mission,['missionId','request','requestHash','inputDigest','objectiveDigest','sourceAssetIds','freshConditions',
    'runId','resultDigest','settlementId','authority'],'mission');
  uuid(mission.missionId); digest(mission.requestHash); digest(mission.inputDigest); digest(mission.objectiveDigest);
  exact(mission.request,['schema','project_id','cycle_id','plan','plan_index','work_spec'],'runtime request');
  if (mission.request.schema !== 'agialpha.ascension.studio-work.v1' || mission.authority !== 'requires-new-grant')
    throw Error('A recovered request never contains execution authority.');
  if (!mission.request.work_spec || typeof mission.request.work_spec !== 'object' || Array.isArray(mission.request.work_spec))
    throw Error('A runtime request needs an exact work specification.');
  if (!Array.isArray(mission.sourceAssetIds) || new Set(mission.sourceAssetIds).size !== mission.sourceAssetIds.length)
    throw Error('Invalid mission input artifacts.');
  mission.sourceAssetIds.forEach(id => text(id,'source artifact ID',160)); text(mission.freshConditions,'fresh conditions',8000,true);
  if (mission.runId !== null) text(mission.runId,'runtime run ID',160);
  if (mission.resultDigest !== null) digest(mission.resultDigest);
  if (mission.settlementId !== null) text(mission.settlementId,'settlement identity',256);
}
export async function registerMission(project,cycleId,{request,inputDigest,objectiveDigest,sourceAssetIds = [],
  verifiedAssets = [],freshConditions = '',now}) {
  const next = await validateProject(project), cycle = cycleFor(next,cycleId);
  if (!cycle.package || request.project_id !== next.projectId || request.cycle_id !== cycleId ||
      !same(request.plan,cycle.package.plan) || !Number.isSafeInteger(request.plan_index) || !request.plan.jobs[request.plan_index])
    throw Error('Runtime request must bind the original project, cycle and exact committed plan index.');
  const requestHash = await projectObjectHash(request);
  const existing = cycle.missions.find(item => item.requestHash === requestHash);
  if (existing) {
    if (!same(existing.sourceAssetIds,sourceAssetIds) || existing.freshConditions !== freshConditions)
      throw Error('Cannot relabel the original mission provenance.');
    return next;
  }
  if (cycle.missions.some(item => item.request.plan_index === request.plan_index))
    throw Error('A committed plan index already has its immutable runtime request.');
  for (const id of sourceAssetIds) {
    const sources = next.cycles.flatMap(item => item.assets.filter(asset => asset.assetId === id).map(asset => ({cycle:item,asset})));
    if (sources.length !== 1) throw Error('Reuse source must identify one exact recorded artifact.');
    const source = sources[0], token = verifiedAssets.find(item => verifiedRights.get(item)?.assetId === id);
    requireAssetVerification(next,source.cycle.cycleId,source.asset,token,{now});
  }
  const inputs = await projectObjectHash(request.work_spec.inputs ?? {});
  const objective = await projectObjectHash({goal:request.plan.jobs[request.plan_index].spec.goal});
  if ((inputDigest && inputDigest !== inputs) || (objectiveDigest && objectiveDigest !== objective))
    throw Error('Mission input and objective identities must match the exact request.');
  const mission = {missionId:crypto.randomUUID(),request:clone(request),requestHash,
    inputDigest:inputs,objectiveDigest:objective,
    sourceAssetIds:[...sourceAssetIds],freshConditions,runId:null,resultDigest:null,settlementId:null,authority:'requires-new-grant'};
  const earlier = next.cycles.filter(item => item.ordinal < cycle.ordinal).flatMap(item => item.missions);
  if (earlier.some(item => item.inputDigest === mission.inputDigest && item.objectiveDigest === mission.objectiveDigest) &&
      !freshConditions.trim()) throw Error('A second mission needs distinct inputs/objective or explicitly justified fresh conditions.');
  cycle.missions.push(mission); return validateProject(next);
}
export async function completeMission(project,cycleId,missionId,{runId,resultDigest,settlementId}) {
  text(runId,'runtime run ID',160); digest(resultDigest); text(settlementId,'settlement identity',256);
  const next = await validateProject(project), mission = cycleFor(next,cycleId).missions.find(item => item.missionId === missionId);
  if (!mission) throw Error('Mission is missing.');
  const otherMissions = next.cycles.flatMap(item => item.missions).filter(item => item.missionId !== missionId);
  if (otherMissions.some(item => item.runId === runId || item.resultDigest === resultDigest || item.settlementId === settlementId))
    throw Error('A distinct mission cannot reuse another run, cached result or attributed settlement.');
  if (mission.runId && (!same([mission.runId,mission.resultDigest,mission.settlementId],[runId,resultDigest,settlementId])))
    throw Error('Cannot replace the original mission evidence.');
  Object.assign(mission,{runId,resultDigest,settlementId}); return validateProject(next);
}
export async function prepareSuccessor(project,cycleId,pkg,{assetIds = [],verifiedAssets = [],evaluationId = null,verified,
  now,...options} = {}) {
  const checked = await validateProject(project), parent = cycleFor(checked,cycleId);
  for (const id of assetIds) {
    const asset = parent.assets.find(item => item.assetId === id);
    if (!asset) throw Error('Successor input is not a recorded parent artifact.');
    requireAssetVerification(checked,cycleId,asset,verifiedAssets.find(item => verifiedRights.get(item)?.assetId === id),{now});
  }
  if (evaluationId !== null) {
    const evaluation = parent.evaluations.find(item => item.evaluationId === evaluationId);
    if (!evaluation || evaluation.decision?.decision !== 'adopt') throw Error('Candidate has not been deliberately adopted.');
    requireVerifiedEvaluation(checked,evaluation,verified,now ?? Date.now());
  }
  return addCycle(checked,pkg,{...options,parentCycleId:cycleId,now});
}

export function projectReservoir(project,cycleId = project.activeCycleId,observation,{reservations = [],...context} = {}) {
  const cycle = cycleFor(project,cycleId), state = currentObservation(project,cycle,observation,context);
  const empty = {projectId:project.projectId,cycleId,fresh:false,account:null,asset:cycle.package?.deployment.contracts.Token ?? null,
    chainId:cycle.package?.deployment.chainId ?? null,walletBalance:null,reserved:null,availableForProposal:'0',
    stake:[],campaign:null,claim:null,ownership:'unknown',costs:{ethGas:null,providerCharges:null,storageCharges:null},
    profit:null,restrictions:['Refresh the exact deployment and wallet. Imported claims are not spendable balances.']};
  if (!state) return empty;
  const known = observations.get(observation), who = state.wallet?.account ? address(state.wallet.account) : null;
  if (!who) return {...empty,fresh:true,restrictions:['Connect the claimant’s wallet explicitly, then refresh.']};
  const balance = uint(String(state.wallet.balance)), campaign = state.campaign, supply = uint(String(campaign.supply));
  const reserve = uint(String(campaign.reserve)), lots = uint(String(state.yourLots ?? 0n)), phase = Number(campaign.phase);
  if (lots > supply) throw Error('Wallet lots exceed observed campaign supply. Refresh the inconsistent observation.');
  if (!Array.isArray(reservations) || reservations.length > 1000) throw Error('Invalid planning reservations.');
  let reserved = 0n; const ids = new Map();
  for (const reservation of reservations) {
    exact(reservation,['reservationId','chainId','asset','owner','amount','projectId','status'],'planning reservation');
    text(reservation.reservationId,'reservation ID',160); uuid(reservation.projectId);
    if (!['planned','pending','uncertain'].includes(reservation.status)) throw Error('Unsupported reservation state.');
    const amount = uint(reservation.amount);
    const key = `${reservation.chainId}:${address(reservation.asset)}:${address(reservation.owner)}:${reservation.reservationId}`;
    if (ids.has(key)) {
      if (!same(ids.get(key),reservation)) throw Error('Conflicting duplicate planning reservation.');
      continue;
    }
    ids.set(key,reservation);
    if (reservation.chainId === cycle.package.deployment.chainId && address(reservation.asset) === address(cycle.package.deployment.contracts.Token) &&
        address(reservation.owner) === who) reserved += amount;
  }
  const restrictions = ['Wallet balance is shared across projects; this view does not allocate it to this project.',
    'Planning reservations are local proposals, not on-chain locks. Reconcile other devices before signing.'];
  const pending = known.client.pending && unresolved(known.client.pending);
  if (pending) restrictions.push('An unresolved wallet intent blocks new financial proposals. Reconcile it in the shared journal.');
  if (reserved > balance) restrictions.push('Planning reservations exceed the current wallet balance. Resolve competing proposals.');
  const available = pending || reserved > balance ? 0n : balance-reserved;
  let claim = null;
  if (lots > 0n) {
    const amount = phase === 3 && supply > 0n ? reserve*lots/supply :
      phase === 1 ? curve(supply-lots,lots,uint(String(campaign.base)),uint(String(campaign.slope))) : null;
    claim = {claimant:who,amount:amount === null ? null : String(amount),lots:String(lots),backing:'campaign-reserve',
      asset:cycle.package.deployment.contracts.Token,spendable:false,kind:phase === 3 ? 'proportional-reclaim' :
        phase === 1 ? 'funding-phase-redemption' : 'contingent-capital-claim',
      nextAction:phase === 3 ? 'reclaim' : phase === 1 ? 'sell' : 'collect-eligible-refunds-and-close-when-permitted'};
  }
  const stake = [{contract:cycle.package.deployment.contracts.Jobs,owner:who,amount:String(state.wallet.stake.Jobs),
    locked:String(state.wallet.stake.agentLocked),kind:'worker-stake',spendable:false},
  {contract:cycle.package.deployment.contracts.Oracle,owner:who,amount:String(state.wallet.stake.Oracle),
    lockedUntil:String(state.wallet.stake.validatorLockedUntil),kind:'reviewer-stake',spendable:false}];
  const result = {...empty,fresh:true,account:who,walletBalance:String(balance),reserved:String(reserved),
    availableForProposal:String(available),stake,campaign:{seedId:cycle.seedId,controller:cycle.package.deployment.contracts.Mark,
      business:address(campaign.business),reserve:String(reserve),phase,supply:String(supply),spendableByBusiness:false,
      use:'Only original committed jobs while active; entitled lot holders use supported exit/claim rules.'},claim,
    ownership:'wallet-owner-only',restrictions,blockNumber:state.verification.blockNumber,blockHash:state.verification.blockHash,
    reconciliation:'current-custody-and-claims; historical flows and external costs remain separate'};
  reservoirs.set(result,{project,cycleId,observation,context,reservations:clone(reservations)});
  return result;
}
export function proposeReinvestment(projection,{sourceOwner,amount,destination,approvalActor,rationale,risk}) {
  const known = reservoirs.get(projection);
  if (!known || !projection.fresh) throw Error('Refresh current owned funds; imported projections grant no spending rights.');
  const current = projectReservoir(known.project,known.cycleId,known.observation,{...known.context,reservations:known.reservations,now:Date.now()});
  if (!current.fresh || address(sourceOwner) !== current.account || address(approvalActor) !== current.account ||
      !uint(amount) || uint(amount) > uint(current.availableForProposal)) throw Error('Proposal exceeds currently observed unencumbered funds owned by its approving actor.');
  exact(destination,['deployment','seedId'],'proposal destination');
  if (!destination.deployment || destination.deployment.chainId !== current.chainId ||
      address(destination.deployment.contracts?.Token) !== address(current.asset) || !uint(destination.seedId))
    throw Error('Select an exact destination campaign for the same native asset and chain. Cross-chain movement is a separate action.');
  text(rationale,'reinvestment rationale'); text(risk,'reinvestment risk');
  return {schema:'agialpha.nova-studio.reinvestment-proposal.v1',projectId:current.projectId,cycleId:current.cycleId,
    sourceOwner:current.account,sourceAccount:current.account,asset:current.asset,chainId:current.chainId,amount,
    protectedObligations:current.reserved,destination:clone(destination),approvalActor:current.account,rationale,risk,
    status:'proposal-only',requiredActions:['Refresh qualified destination, claimant balance and all pending obligations.',
      'Prepare and simulate a separate bounded token approval if needed.','Refresh the quote, then prepare and separately confirm the exact lot purchase.'],
    exactCalls:null,authority:'none; exact calls belong to the existing wallet preparation and confirmation pipeline'};
}
export function reconcileCapital(flows,{owner} = {}) {
  if (!Array.isArray(flows) || flows.length > 10000) throw Error('Invalid capital-flow projection.');
  const who = address(owner), seen = new Map(), totals = new Map();
  for (const flow of flows) {
    exact(flow,['chainId','market','jobId','transactionHash','logIndex','asset','kind','recipient','gross','burned'],
      'observed capital flow');
    if (!Number.isSafeInteger(flow.chainId) || flow.chainId < 1 || !Number.isSafeInteger(flow.logIndex) || flow.logIndex < 0)
      throw Error('Invalid flow identity.');
    uint(flow.jobId); digest(flow.transactionHash); address(flow.market); address(flow.asset); address(flow.recipient);
    if (!['payout','principal-return','refund-to-campaign','stray-transfer'].includes(flow.kind)) throw Error('Unsupported flow category.');
    const gross = uint(flow.gross), burned = uint(flow.burned);
    if (burned > gross || (flow.kind !== 'payout' && burned !== 0n)) throw Error('Burn must fit the exact gross payout.');
    const identity = `${flow.chainId}:${address(flow.market)}:${flow.transactionHash}:${flow.logIndex}`;
    if (seen.has(identity)) {
      if (!same(seen.get(identity),flow)) throw Error('Conflicting duplicate economic observation.');
      continue;
    }
    seen.set(identity,flow);
    const key = `${flow.chainId}:${address(flow.asset)}`;
    const total = totals.get(key) || {chainId:flow.chainId,asset:address(flow.asset),grossPayout:0n,netPayout:0n,burned:0n,
      returnedPrincipal:0n,refundsToCampaign:0n,strayTransfers:0n,otherRecipients:0n};
    if (address(flow.recipient) !== who) total.otherRecipients += gross-burned;
    else if (flow.kind === 'payout') { total.grossPayout += gross; total.burned += burned; total.netPayout += gross-burned; }
    else if (flow.kind === 'principal-return') total.returnedPrincipal += gross;
    else if (flow.kind === 'refund-to-campaign') total.refundsToCampaign += gross;
    else total.strayTransfers += gross;
    totals.set(key,total);
  }
  return {owner:who,uniqueObservations:seen.size,assets:[...totals.values()].map(item =>
    Object.fromEntries(Object.entries(item).map(([key,value]) => [key,typeof value === 'bigint' ? String(value) : value]))),
    spendableIncrease:null,profit:null,authority:'arithmetic-only; verify each original receipt and current custody independently',
    note:'Payouts are recipient-specific. Returned principal and burns are not profit. Backing custody and claims are never added.'};
}
