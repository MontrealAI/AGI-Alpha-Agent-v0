// SPDX-License-Identifier: Apache-2.0
import {readFileSync,lstatSync,realpathSync} from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {authenticateAttestation,authorizeRoot} from './authority.mjs';
import {canonicalize,digest,leafHash,verifyProof,graphEpochRoot,RECORD_TYPES,buildForest,validateRootHistory} from './commitments.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const same=(a,b)=>canonicalize(a)===canonicalize(b);
const bytesHash=bytes=>createHash('sha256').update(bytes).digest('hex');
const key=skill=>`${skill.id}@${skill.version}`;
const OWNED_INDEX=Symbol('owned-catalog-index');
const immutable=value=>{if(value&&typeof value==='object'){for(const item of Object.values(value))immutable(item);Object.freeze(value);}return value;};

export function createSelector(catalog,resolver,{strategy='graph'}={}) {
  const started=performance.now(),cpu=process.cpuUsage();
  const owned=immutable(JSON.parse(canonicalize(catalog))),index=indexCatalog(owned,strategy),usage=process.cpuUsage(cpu);
  return Object.freeze({strategy,construction:{elapsed_seconds:(performance.now()-started)/1000,cpu_seconds:(usage.user+usage.system)/1e6},
    select(context,options={}){return selectWorkflow(owned,context,resolver,{...options,strategy,[OWNED_INDEX]:index});}});
}

export function indexCatalog(catalog,strategy='graph') {
  if(!['registry','graph'].includes(strategy)) throw Error('UNKNOWN_SELECTION_STRATEGY');
  const skills=catalog.forest.classes.skill.records.map(x=>x.record);
  if(new Set(skills.map(key)).size!==skills.length) throw Error('DUPLICATE_SKILL_VERSION');
  const byKey=new Map(skills.map(x=>[key(x),x])),outputs=new Map(),adjacency=new Map();
  for(const skill of skills) for(const output of skill.contract.outputs) outputs.set(output,[...(outputs.get(output)||[]),key(skill)]);
  if(strategy==='graph') for(const {record:edge} of catalog.forest.classes.edge.records) adjacency.set(edge.from,[...(adjacency.get(edge.from)||[]),edge]);
  return {strategy,byKey,outputs,adjacency};
}

function fileIdentity(relative,expected,counters) {
  if(typeof relative!=='string'||path.isAbsolute(relative)) return false;
  const full=path.resolve(ROOT,relative);
  if(!full.startsWith(ROOT+path.sep)) return false;
  try {
    if(!realpathSync(full).startsWith(ROOT+path.sep))return false;
    for(let current=full;current!==ROOT;current=path.dirname(current))if(lstatSync(current).isSymbolicLink())return false;
    const raw=readFileSync(full);counters.bytes_hashed+=raw.length;counters.file_reads++;return bytesHash(raw)===expected;
  }
  catch {return false;}
}

export function selectWorkflow(catalog,context,resolver,options={}) {
  const start=performance.now(),cpu=process.cpuUsage(),reasons=[],trace=[],selected=[],validated=new Set();
  const counters={proof_checks:0,attestation_checks:0,root_authority_checks:0,relationship_rows_examined:0,relationship_traversals:0,recipe_members_read:0,file_reads:0,bytes_hashed:0,model_calls:0};
  const strategy=options.strategy||'graph',ablation=options.ablation||null;
  const fail=reason=>{if(!reasons.includes(reason))reasons.push(reason);};
  let index;
  try {
    context=immutable(JSON.parse(canonicalize(context)));
    if(!options[OWNED_INDEX])catalog=immutable(JSON.parse(canonicalize(catalog)));
    if(catalog.schema!=='agi-alpha-validated-skill-catalog/v1'||catalog.mode!=='FIXTURE_ONLY')throw Error('UNSUPPORTED_CATALOG');
    index=options[OWNED_INDEX]||indexCatalog(catalog,strategy);
    const latest=catalog.root;
    if(graphEpochRoot(latest)!==latest.graphRoot)fail('COMMITTED_ROOT_CHANGED');
    if(!context.expectedGraphRoot||context.expectedGraphRoot!==latest.graphRoot||context.expectedEpoch!==latest.epoch||context.expectedPreviousRoot!==latest.previousRoot)fail('UNEXPECTED_CURRENT_ROOT_OR_EPOCH');
    const recomputed=buildForest(Object.fromEntries(RECORD_TYPES.map(type=>[type,catalog.forest.classes[type].records.map(row=>row.record)])));
    if(!same(recomputed,catalog.forest))fail('COMMITTED_STATE_INCOMPLETE_OR_CHANGED');
    const history=validateRootHistory(catalog.history,{authorizer:(record,expected)=>{
      const checked=authorizeRoot(record,{...context,...expected,expectedGraphRoot:record.graphRoot,now:record.issuedAt,currentSnapshotId:record.authoritySnapshotId,intent:'inspect',admissionsVerified:false,lifecycleEvidenceVerified:false},resolver);
      return {ok:checked.historyValid};
    }});
    if(!history.ok||history.latestRoot!==latest.graphRoot||history.latestEpoch!==latest.epoch)fail('AUTHORIZED_ROOT_HISTORY_INVALID');
    trace.push({kind:'history',check:history,scope:'Commitment continuity and historical writer authority; historical technical/economic truth is not inferred.'});
    for(const type of RECORD_TYPES){
      const entry=catalog.forest.classes[type];
      if(entry.root!==latest.roots[type]||entry.count!==latest.counts[type]||entry.records.length!==entry.count)fail('TYPED_ROOT_CONTEXT_MISMATCH');
      for(const row of entry.records){
        counters.proof_checks++;
        if(ablation!=='no-proofs'&&(row.leafHash!==leafHash(type,row.record)||row.proof.leafCount!==entry.count||!verifyProof(row.leafHash,row.proof,entry.root)))fail('INCLUSION_PROOF_INVALID');
      }
    }
    const policy=catalog.forest.classes.policy.records.map(x=>x.record).find(x=>x.id===catalog.policy.id);
    if(!policy||digest(policy,'validation-policy')!==latest.policyDigest||!same(policy,catalog.policy))fail('POLICY_IDENTITY_MISMATCH');
    if(digest(catalog.scope,'tested-scope')!==context.scopeDigest||digest(catalog.environment,'tested-environment')!==context.environmentDigest||digest(catalog.rights,'reuse-rights')!==context.rightsDigest)fail('DESCRIPTIVE_SCOPE_ENVIRONMENT_OR_RIGHTS_CHANGED');
    const records=catalog.forest.classes.evidence.records.map(x=>x.record);
    const admissions=records.filter(x=>x.kind==='technical-admission');
    const dossiers=new Map(records.filter(x=>x.kind==='validation-dossier').map(x=>[x.id,x]));
    const composition=records.find(x=>x.kind==='composition-validation'&&x.id===catalog.composition.id);
    const lifecycle=catalog.forest.classes.revocation.records.map(x=>x.record);
    const supersessions=catalog.forest.classes.supersession.records.map(x=>x.record);
    if(lifecycle.some(x=>x.kind!=='skill-revocation'||x.policyDigest!==latest.policyDigest||!x.reason)||supersessions.some(x=>x.kind!=='skill-supersession'||x.policyDigest!==latest.policyDigest))fail('UNSUPPORTED_LIFECYCLE_RECORD');
    const common={...context,graphId:latest.graphId,chainId:latest.chainId,registry:latest.registry,policyDigest:latest.policyDigest,intent:'reuse',
      revokedSkills:[...(context.revokedSkills||[]),...lifecycle.map(x=>x.targetSkill)],
      supersededSkills:[...(context.supersededSkills||[]),...supersessions.map(x=>x.predecessor)]};
    const authorizeSkill=skill=>{
      const id=key(skill);
      if(validated.has(id))return;
      validated.add(id);
      if(skill.state!=='ADMITTED_FIXTURE_ONLY'||!same(skill.rights,catalog.rights)||!same(skill.knownFailures,catalog.scope.failures))fail('SKILL_STATE_OR_RESTRICTIONS_CHANGED:'+id);
      const admission=admissions.find(x=>x.skill===id&&x.decision==='ADMIT_FIXTURE_ONLY');
      if(!admission||admission.skillBindingDigest!==digest(skill.binding,'skill-binding')||admission.evidenceDigest!==skill.binding.evidenceDigest)fail('TECHNICAL_ADMISSION_MISSING:'+id);
      const dossier=dossiers.get(skill.validationDossier);
      const evidencePresent=dossier&&digest(dossier,'validation-dossier')===skill.binding.evidenceDigest&&dossier.files.every(x=>fileIdentity(x.path,x.sha256,counters));
      if(!evidencePresent)fail('EVIDENCE_UNAVAILABLE:'+id);
      const executable={files:skill.implementation.files,entrypoint:skill.implementation.entrypoint,contract:skill.contract,requires:skill.requires};
      if(!skill.implementation.files.every(x=>fileIdentity(x.path,x.sha256,counters))||digest(executable,'executable-asset')!==skill.binding.implementationDigest)fail('IMPLEMENTATION_IDENTITY_MISMATCH:'+id);
      const dependencyBindings=skill.requires.map(dependency=>index.byKey.has(dependency)?digest(index.byKey.get(dependency).binding,'skill-binding'):'MISSING').sort();
      if(!same(dependencyBindings,skill.binding.dependencyDigests))fail('ATTESTED_DEPENDENCY_BINDING_MISMATCH:'+id);
      if(!dossier?.composition||!composition||!same(dossier.composition,composition))fail('COMPOSITION_DOSSIER_BINDING_MISMATCH:'+id);
      const attestation=catalog.forest.classes.attestation.records.map(x=>x.record).find(x=>x.skill.id===skill.id&&x.skill.version===skill.version);
      counters.attestation_checks++;
      const authContext=ablation==='no-freshness'?{...common,now:150,currentSnapshotId:'fixture-state-100',revokedSkills:[],supersededSkills:[],revokedAttestations:[],evidenceAvailable:true}:{...common,evidenceAvailable:Boolean(evidencePresent)};
      const auth=authenticateAttestation(attestation,skill.binding,authContext,resolver);
      if(ablation!=='no-authority'&&!auth.ok)for(const reason of auth.reasons)fail(reason+':'+id);
      if(skill.binding.scopeDigest!==context.scopeDigest||skill.binding.environmentDigest!==context.environmentDigest||skill.binding.rightsDigest!==context.rightsDigest)fail('MISSION_SCOPE_ENVIRONMENT_OR_RIGHTS_MISMATCH:'+id);
      trace.push({kind:'skill',skill:id,admission:admission?.decision||'REFUSE',authority:auth,why:skill.contract.purpose});
    };
    const visiting=new Set(),visited=new Set();
    const checkRelationship=edge=>{
      if(edge.scopeDigest!==context.scopeDigest||edge.environmentDigest!==context.environmentDigest||edge.policyDigest!==latest.policyDigest||edge.compositionEvidence!==catalog.composition.evidenceDigest||edge.state!=='VALIDATED_FIXTURE_ONLY')fail('RELATIONSHIP_SCOPE_OR_EVIDENCE_INVALID');
      if(edge.relation==='conflicts_with'&&composition?.members?.includes(edge.from)&&composition.members.includes(edge.to))fail('CONFLICTING_DEPENDENCIES');
    };
    const walk=id=>{
      if(visiting.has(id)){fail('COMPOSITION_CYCLE');return;}
      if(visited.has(id))return;
      const skill=index.byKey.get(id);if(!skill){fail('DEPENDENCY_SKILL_MISSING:'+id);return;}
      visiting.add(id);authorizeSkill(skill);
      const relationships=index.adjacency.get(id)||[];counters.relationship_rows_examined+=relationships.length;
      const required=skill.requires||[],found=relationships.filter(x=>x.relation==='depends_on');
      if(ablation!=='no-relationships'){
        if(!same([...required].sort(),found.map(x=>x.to).sort()))fail('COMPOSITION_RELATIONSHIP_INCOMPLETE:'+id);
        for(const edge of relationships)checkRelationship(edge);
      }
      for(const edge of found){counters.relationship_traversals++;walk(edge.to);}
      visiting.delete(id);visited.add(id);selected.push(id);
    };
    const candidates=index.outputs.get(context.output)||[];
    const candidate=candidates.find(id=>id===catalog.targetSkill);
    if(!candidate)fail('NO_SUPPORTED_OUTPUT');
    else if(strategy==='graph')walk(candidate);
    else {
      const relationships=catalog.forest.classes.edge.records.map(row=>row.record),relationKeys=new Set();
      for(const edge of relationships){
        counters.relationship_rows_examined++;const relationKey=[edge.from,edge.to,edge.relation].join('|');
        if(relationKeys.has(relationKey))fail('DUPLICATE_RELATIONSHIP');relationKeys.add(relationKey);
        if(ablation!=='no-relationships')checkRelationship(edge);
      }
      const completed=new Set();
      for(const id of composition?.members||[]){
        counters.recipe_members_read++;const skill=index.byKey.get(id);
        if(!skill){fail('REGISTRY_RECIPE_SKILL_MISSING');continue;}
        if(completed.has(id))fail('REGISTRY_RECIPE_DUPLICATE');
        authorizeSkill(skill);
        for(const dependency of skill.requires){
          if(!completed.has(dependency))fail('REGISTRY_RECIPE_NOT_TOPOLOGICAL');
          if(ablation!=='no-relationships'&&!relationKeys.has([id,dependency,'depends_on'].join('|')))fail('REGISTRY_COMPOSITION_EVIDENCE_MISSING');
        }
        completed.add(id);selected.push(id);
      }
      if(selected.at(-1)!==candidate)fail('REGISTRY_RECIPE_OUTPUT_MISMATCH');
    }
    if(ablation!=='no-relationships'){
      const identities=selected.map(id=>{const skill=index.byKey.get(id);return {skill:id,implementationDigest:skill.binding.implementationDigest,requires:skill.requires};});
      if(!composition||composition.decision!=='PASS_COMBINED_WORKFLOW'||!same([...composition.members].sort(),[...selected].sort())||!same(composition.implementationIdentities,identities)||digest(composition,'composition-validation')!==catalog.composition.evidenceDigest||!composition.files.every(x=>fileIdentity(x.path,x.sha256,counters)))fail('INDEPENDENT_COMPOSITION_VALIDATION_MISSING');
    }
    counters.root_authority_checks++;
    const rootCurrent=ablation==='no-freshness'?{...common,now:150,currentSnapshotId:'fixture-state-100',revokedSkills:[],supersededSkills:[],revokedAttestations:[]}:common;
    const rootAuth=authorizeRoot(latest,{...rootCurrent,expectedEpoch:context.expectedEpoch,expectedPreviousRoot:context.expectedPreviousRoot,expectedGraphRoot:context.expectedGraphRoot,
      admissionsVerified:reasons.length===0,lifecycleEvidenceVerified:!reasons.includes('UNSUPPORTED_LIFECYCLE_RECORD')},resolver);
    if(ablation!=='no-authority'&&!rootAuth.ok)for(const reason of rootAuth.reasons)fail('ROOT_'+reason);
    trace.push({kind:'root',epoch:latest.epoch,root:latest.graphRoot,authorization:rootAuth});
  }catch(error){fail('SELECTION_ERROR:'+error.message);}
  const usage=process.cpuUsage(cpu);
  return {schema:'agi-alpha-skill-selection/v1',strategy,ablation,ok:reasons.length===0,decision:reasons.length?'REFUSE_REUSE':'REUSE_WITHIN_FIXTURE_SCOPE',
    selected:reasons.length?[]:selected,attempted:selected,reasons,trace,counters,elapsed_seconds:(performance.now()-start)/1000,cpu_seconds:(usage.user+usage.system)/1e6,
    fallback:reasons.length?'UNCHANGED_INCUMBENT_AFTER_ITS_OWN_INPUT_VALIDATION':null,mode:'FIXTURE_ONLY',live_identity_enforcement:'NOT_RUN',economic_admission:'UNASSESSED'};
}
