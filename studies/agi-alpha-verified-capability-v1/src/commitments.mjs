import {createHash} from 'node:crypto';

export const HASH_SUITE = 'SHA256_RESEARCH_V1';
export const TREE_POLICY = 'SORTED_PAIR_DUPLICATE_LAST_V1';
export const CANONICALIZATION = 'AGI_ALPHA_JSON_SAFE_INTEGER_NFC_V1';
export const RECORD_TYPES = Object.freeze(['skill','edge','evidence','proofbundle','policy','attestation','revocation','supersession','metadata']);
export const ZERO_ROOT = '0'.repeat(64);
const HEX = /^[0-9a-f]{64}$/;
const own = (v,k) => Object.prototype.hasOwnProperty.call(v,k);

export function canonicalize(value) {
  const active = new Set();
  function encode(v) {
    if (v === null || typeof v === 'boolean') return JSON.stringify(v);
    if (typeof v === 'string') {
      if (v !== v.normalize('NFC') || /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(v)) throw new TypeError('NONCANONICAL_STRING');
      return JSON.stringify(v);
    }
    if (typeof v === 'number') {
      if (!Number.isSafeInteger(v) || Object.is(v,-0)) throw new TypeError('SAFE_INTEGER_REQUIRED');
      return String(v);
    }
    if (typeof v !== 'object') throw new TypeError('JSON_VALUE_REQUIRED');
    if (active.has(v)) throw new TypeError('CYCLIC_RECORD');
    active.add(v);
    let out;
    if (Array.isArray(v)) {
      if (Object.getOwnPropertySymbols(v).length || Object.keys(v).length !== v.length || Array.from({length:v.length},(_,i)=>i).some(i=>!own(v,i)||!own(Object.getOwnPropertyDescriptor(v,String(i)),'value'))) throw new TypeError('DENSE_ARRAY_REQUIRED');
      out = '[' + v.map(encode).join(',') + ']';
    } else {
      if (![Object.prototype,null].includes(Object.getPrototypeOf(v))) throw new TypeError('PLAIN_RECORD_REQUIRED');
      const keys = Object.keys(v).sort();
      if (Object.getOwnPropertySymbols(v).length || keys.some(k=>!own(Object.getOwnPropertyDescriptor(v,k),'value'))) throw new TypeError('DATA_PROPERTIES_REQUIRED');
      out = '{' + keys.map(k=>encode(k)+':'+encode(v[k])).join(',') + '}';
    }
    active.delete(v);
    return out;
  }
  return encode(value);
}

export function digest(value, domain='object') {
  if (typeof domain !== 'string' || !domain) throw new TypeError('DOMAIN_REQUIRED');
  return createHash('sha256').update('AGI_ALPHA_COMMITMENT_V1\0').update(canonicalize({domain,value})).digest('hex');
}

export function leafHash(type, record) {
  if (!RECORD_TYPES.includes(type)) throw new TypeError('UNKNOWN_RECORD_TYPE');
  return digest({canonicalization:CANONICALIZATION,hashSuite:HASH_SUITE,schema:`agi-alpha.${type}.v1`,record},`typed-leaf:${type}`);
}

function checkedHash(value) {
  if (typeof value !== 'string' || !HEX.test(value)) throw new TypeError('SHA256_DIGEST_REQUIRED');
  return value;
}

function parent(a,b) {
  checkedHash(a); checkedHash(b);
  return digest(a < b ? [a,b] : [b,a],'merkle-node');
}

export function buildMerkle(leaves) {
  if (!Array.isArray(leaves)) throw new TypeError('LEAF_ARRAY_REQUIRED');
  const sorted = leaves.map(checkedHash).sort();
  if (new Set(sorted).size !== sorted.length) throw new TypeError('DUPLICATE_LEAF');
  const levels = [sorted];
  while (levels.at(-1).length > 1) {
    const prior = levels.at(-1), next = [];
    for (let i=0;i<prior.length;i+=2) next.push(parent(prior[i],prior[i+1] ?? prior[i]));
    levels.push(next);
  }
  return {hashSuite:HASH_SUITE,treePolicy:TREE_POLICY,root:sorted.length ? levels.at(-1)[0] : digest([],'empty-merkle-tree'),count:sorted.length,leaves:sorted,levels};
}

export function inclusionProof(tree,index) {
  if (!Number.isSafeInteger(index) || index<0 || index>=tree.count) throw new RangeError('PROOF_INDEX_OUT_OF_RANGE');
  const rebuilt=buildMerkle(tree.leaves);
  if (rebuilt.root!==tree.root || canonicalize(rebuilt.levels)!==canonicalize(tree.levels)) throw new TypeError('MALFORMED_TREE');
  const siblings=[]; let at=index;
  for (const level of tree.levels.slice(0,-1)) { siblings.push(level[at^1] ?? level[at]); at=Math.floor(at/2); }
  return {hashSuite:HASH_SUITE,treePolicy:TREE_POLICY,leafIndex:index,leafCount:tree.count,siblings};
}

export function verifyProof(leaf,proof,root) {
  try {
    checkedHash(leaf); checkedHash(root);
    if (!proof || proof.hashSuite!==HASH_SUITE || proof.treePolicy!==TREE_POLICY || !Array.isArray(proof.siblings)) return false;
    if (!Number.isSafeInteger(proof.leafCount) || proof.leafCount<1 || !Number.isSafeInteger(proof.leafIndex) || proof.leafIndex<0 || proof.leafIndex>=proof.leafCount) return false;
    if (proof.siblings.length!==Math.ceil(Math.log2(proof.leafCount))) return false;
    let computed=leaf;
    for (const sibling of proof.siblings) computed=parent(computed,sibling);
    return computed===root;
  } catch { return false; }
}

export function verifyInclusion(type,record,proof,root) {
  try { return verifyProof(leafHash(type,record),proof,root); } catch { return false; }
}

export function buildForest(recordsByType) {
  if (!recordsByType || Object.keys(recordsByType).some(k=>!RECORD_TYPES.includes(k))) throw new TypeError('UNKNOWN_FOREST_CLASS');
  const classes={};
  for (const type of RECORD_TYPES) {
    const records=recordsByType[type] ?? [];
    if (!Array.isArray(records)) throw new TypeError('RECORD_ARRAY_REQUIRED');
    const hashes=records.map(record=>leafHash(type,record)), tree=buildMerkle(hashes);
    classes[type]={root:tree.root,count:tree.count,records:records.map((record,i)=>({record:JSON.parse(canonicalize(record)),leafHash:hashes[i],proof:inclusionProof(tree,tree.leaves.indexOf(hashes[i]))}))};
  }
  return {schema:'agi-alpha.merkle-forest.v1',hashSuite:HASH_SUITE,treePolicy:TREE_POLICY,canonicalization:CANONICALIZATION,classes};
}

function epochMaterial(packet) {
  const names=['graphId','agent','chainId','registry','epoch','previousRoot','roots','counts','policyDigest','snapshotDigest','proofLevel','hashSuite','treePolicy','canonicalization','schema','mode'];
  const material=Object.fromEntries(names.map(k=>[k,packet[k]]));
  if (material.schema!=='agi-alpha.graph-epoch.v1' || material.mode!=='FIXTURE_ONLY' || material.hashSuite!==HASH_SUITE || material.treePolicy!==TREE_POLICY || material.canonicalization!==CANONICALIZATION) throw new TypeError('UNSUPPORTED_EPOCH_POLICY');
  if (!Number.isSafeInteger(material.epoch) || material.epoch<1 || !Number.isSafeInteger(material.chainId) || material.chainId<1) throw new TypeError('INVALID_EPOCH_CONTEXT');
  for (const k of ['graphId','agent','registry','proofLevel']) if(typeof material[k]!=='string'||!material[k]) throw new TypeError('MISSING_EPOCH_CONTEXT');
  for (const k of ['previousRoot','policyDigest','snapshotDigest']) checkedHash(material[k]);
  if (!material.roots || !material.counts || Object.keys(material.roots).sort().join('|')!==[...RECORD_TYPES].sort().join('|') || Object.keys(material.counts).sort().join('|')!==[...RECORD_TYPES].sort().join('|')) throw new TypeError('INCOMPLETE_TYPED_ROOTS');
  for (const type of RECORD_TYPES) {checkedHash(material.roots[type]); if(!Number.isSafeInteger(material.counts[type])||material.counts[type]<0) throw new TypeError('INVALID_CLASS_COUNT');}
  canonicalize(material);
  return material;
}

export function graphEpochRoot(packet) { return digest(epochMaterial(packet),'graph-epoch'); }

export function verifyEpochInclusion(packet,type,record,proof) {
  try {
    return RECORD_TYPES.includes(type)&&graphEpochRoot(packet)===packet.graphRoot&&proof.leafCount===packet.counts[type]&&verifyInclusion(type,record,proof,packet.roots[type]);
  } catch {return false;}
}

export function buildGraphEpoch({forest,graphId,agent,chainId,registry,epoch,previousRoot=ZERO_ROOT,policyDigest,snapshotDigest,proofLevel='FIXTURE_SCOPED_TECHNICAL'}) {
  if (forest?.schema!=='agi-alpha.merkle-forest.v1' || forest.hashSuite!==HASH_SUITE || forest.treePolicy!==TREE_POLICY || forest.canonicalization!==CANONICALIZATION) throw new TypeError('UNSUPPORTED_FOREST');
  const records=Object.fromEntries(RECORD_TYPES.map(type=>[type,forest.classes?.[type]?.records?.map(item=>item.record)]));
  const recomputed=buildForest(records);
  if (canonicalize(forest)!==canonicalize(recomputed)) throw new TypeError('FOREST_INTEGRITY_MISMATCH');
  const packet={schema:'agi-alpha.graph-epoch.v1',mode:'FIXTURE_ONLY',hashSuite:HASH_SUITE,treePolicy:TREE_POLICY,canonicalization:CANONICALIZATION,graphId,agent,chainId,registry,epoch,previousRoot,roots:Object.fromEntries(RECORD_TYPES.map(t=>[t,forest.classes[t].root])),counts:Object.fromEntries(RECORD_TYPES.map(t=>[t,forest.classes[t].count])),policyDigest,snapshotDigest,proofLevel};
  return {...packet,graphRoot:graphEpochRoot(packet)};
}

export function validateRootHistory(records,{authorizer,initialPreviousRoot=ZERO_ROOT,initialEpoch=1}={}) {
  const reasons=[]; let previousRoot=initialPreviousRoot, epoch=initialEpoch, identity=null;
  if(!Array.isArray(records)||!records.length) return {ok:false,integrityOk:false,authorizationStatus:'NOT_CHECKED',reasons:['EMPTY_ROOT_HISTORY']};
  for(const record of records) {
    try {
      const key=canonicalize([record.graphId,record.agent,record.chainId,record.registry]);
      if(identity!==null&&identity!==key) reasons.push('ROOT_HISTORY_CONTEXT_CHANGED');
      identity=key;
      if(record.previousRoot!==previousRoot||record.epoch!==epoch) reasons.push('ROOT_HISTORY_DISCONTINUITY');
      if(graphEpochRoot(record)!==record.graphRoot) reasons.push('GRAPH_ROOT_MISMATCH');
      if(authorizer && authorizer(record,{expectedPreviousRoot:previousRoot,expectedEpoch:epoch})?.ok!==true) reasons.push('UNAUTHORIZED_ROOT_HISTORY');
      previousRoot=record.graphRoot; epoch++;
    } catch { reasons.push('MALFORMED_ROOT_HISTORY'); }
  }
  const integrityOk=!reasons.some(x=>x!=='UNAUTHORIZED_ROOT_HISTORY');
  if(!authorizer) reasons.push('ROOT_AUTHORIZATION_NOT_CHECKED');
  return {ok:reasons.length===0,integrityOk,authorizationStatus:authorizer?'CHECKED':'NOT_CHECKED',latestRoot:previousRoot,latestEpoch:epoch-1,reasons:[...new Set(reasons)]};
}
