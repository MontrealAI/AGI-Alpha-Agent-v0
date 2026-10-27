// SPDX-License-Identifier: Apache-2.0
// Convenience adapter for the economic simulator. Every identity/signature below
// is a declared fixture; no ENS lookup, key, wallet or live authority is implied.
import {readFileSync} from 'node:fs';
import {createFixtureResolver,createFixtureAttestation,createFixtureRoot,fixtureNode,eligibleAgent} from '../upstream/graph/authority.mjs';
import {createSkillNetwork,combineComparisonDigest} from './lifecycle.mjs';
import {clone,contentDigest} from './encoding.mjs';

const originalFixture=JSON.parse(readFileSync(new URL('../upstream/graph/authority-fixture.json',import.meta.url),'utf8'));
const HEX=/^[a-f0-9]{64}$/;
const asDigest=(x,domain)=>HEX.test(x??'')?x:contentDigest(x??domain,domain);
const present=x=>x!==undefined;

export function createModeledAuthority(members){
  const fixture=clone(originalFixture),snapshot=clone(fixture.snapshots[0]);
  snapshot.id='network-fixture-state-0';snapshot.blockNumber=0;snapshot.blockHash=contentDigest('local-block-0');
  snapshot.observedAt=0;snapshot.validUntil=1000000;
  for(const agent of new Set([...members,'validator.agent.agi.eth'])){
    if(!eligibleAgent(agent))throw Error('SIMULATED_MEMBERS_MUST_BE_DIRECT_AGENTS');
    const template=clone(snapshot.names['research.agent.agi.eth']);
    const owner=`fixture:${agent}`;template.normalizedName=agent;template.node=fixtureNode(agent);
    template.registryOwner=owner;template.wrapped=false;template.wrapper=null;template.wrappedOwner=null;template.wrapperExpiry=null;
    template.validFrom=0;template.expiresAt=1000000;template.operatorsForAll=[];template.delegations=[];template.renewalManagers=[];
    template.grants={ISSUE_SKILL_ATTESTATION:[owner],COMMIT_GRAPH_ROOT:[owner]};snapshot.names[agent]=template;
  }
  fixture.snapshots=[snapshot];fixture.description='Research-only week-indexed authority fixture derived from the pinned upstream schema; no real ENS ownership or signatures.';
  return fixture;
}

export function createModeledNetwork({members=['atlas.agent.agi.eth','lyra.agent.agi.eth','orion.agent.agi.eth'],
  betaVersion='frontier-beta-v1',policyVersion='beyond-beta-alpha-policy-v1',scopeDigest,environmentDigest,
  networkId='beyond-beta-research-network-v1',dependencyMap={recourse:['representation','certificate']},
  baselineEquivalenceKeys=[],policy={},protectedEvaluationMaterial=[]}={}){
  const people=clone(members);if(!people.length)throw Error('NETWORK_MEMBERS_REQUIRED');
  const scope=asDigest(scopeDigest,'optimization-prototype-scope-v1'),environment=asDigest(environmentDigest,'modeled-frontier-workflow-environment-v1');
  const fixture=createModeledAuthority(people),resolver=createFixtureResolver(fixture),snapshotId=fixture.snapshots[0].id;
  const network=createSkillNetwork({networkId,policy:{...policy,version:policyVersion},betaVersion,scopeDigest:scope,
    environmentDigest:environment,authorityFixture:fixture,currentSnapshotId:snapshotId,baselineEquivalenceKeys,
    executionAuthorizer:({mission})=>({allowed:mission?.scopeDigest===scope&&mission?.environmentDigest===environment,
      mode:'SIMULATED_MISSION_AUTHORIZATION_ONLY',actualExecution:false})});
  network.protectEvaluationMaterial(protectedEvaluationMaterial);
  const descriptors=new Map(),registered=new Set(),log=[];let nonce=0;
  const signer=agent=>`fixture:${agent}`;
  const mission=()=>({scopeDigest:scope,environmentDigest:environment,betaVersion:network.context().betaVersion,
    action:'USE_MODELED_NONSAFETY_CAPABILITY',mode:'SIMULATED_MISSION_POLICY'});
  const fail=(id,reason,week)=>{
    const message=String(reason);log.push({id,week,event:'adapter-rejection',reason:message});
    try{network.recordFailure({id:`failure:${id}:${log.length}`.slice(0,128),reason:message.slice(0,128),
      evidenceDigest:contentDigest({id,reason:message,week},'modeled-failure-memory')},week);}catch{/* A diagnostic cannot grant or restore authority. */}
    return false;
  };
  function memberProof(agent,week){
    const c=network.context(),binding=network.membershipBinding(agent);
    return createFixtureAttestation(binding,{agent,signer:signer(agent),snapshotId:c.currentSnapshotId,issuedAt:week,
      expiresAt:Math.min(1000000,week+1000),nonce:`member:${nonce++}`,graphId:`${networkId}:membership`},resolver);
  }
  function pinsFor(keys,week){
    const needed=[...new Set(keys.flatMap(k=>dependencyMap[k]??[]))],pins=[];
    for(const required of needed){
      const match=[...descriptors.values()].find(d=>d.keys.includes(required)&&registered.has(d.key)&&network.inspect(d.key,week).eligibility.ok);
      if(match){if(!pins.some(p=>p.id===match.manifest.id&&p.version===match.manifest.version))pins.push({id:match.manifest.id,version:match.manifest.version,digest:match.candidateDigest});}
      else pins.push({id:`missing-prerequisite:${required}`,version:'0',digest:contentDigest(required,'missing-prerequisite')});
    }return pins;
  }
  function assessmentBindings({id,keys,owner=people[0],betaVersion:claimedBeta,comparisonUniverse,week,expiryWeek,assetExpiryWeek=expiryWeek,
    version='1',prerequisitePins,rights,equivalenceKey,privatePayload}={}){
    if(!Array.isArray(keys)||!keys.length||!Number.isSafeInteger(week)||!Number.isSafeInteger(expiryWeek)||expiryWeek<=week)throw Error('INVALID_MODELED_CANDIDATE');
    if(!people.includes(owner))throw Error('UNKNOWN_MODELED_CREATOR');
    const c=network.context();if(claimedBeta!==undefined&&claimedBeta!==c.betaVersion)throw Error('CURRENT_BETA_REQUIRED');
    let d=descriptors.get(id);
    if(!d){
      const ordered=[...new Set(keys)].sort(),pins=prerequisitePins??pinsFor(ordered,c.week);
      const payload=privatePayload??{mode:'MODELED_CAPABILITY_NOT_EMPIRICAL_IMPLEMENTATION',candidateId:id,keys:ordered,
        description:'Conditional reusable workflow in the declared simulation; this capsule is not proof of frontier invention.'};
      const manifest={id,version:String(version),ownerAgent:owner,implementationDigest:contentDigest({id,keys:ordered,constructionVersion:'modeled-construction-v1'},'modeled-implementation'),
        equivalenceKey:equivalenceKey??ordered.join('+'),scopeDigest:scope,environmentDigest:environment,expiresAt:assetExpiryWeek,
        prerequisitePins:clone(pins),components:ordered.length>1?ordered.map(k=>({id:k,implementationDigest:contentDigest({candidateId:id,component:k},'modeled-bundle-component')})):[],
        payloadDigest:contentDigest(payload,'beyond-beta-private-payload'),
        rights:rights??{shareable:true,retrieve:'network',execute:'network',compose:'network',export:false}};
      d={key:`${id}@${manifest.version}`,manifest,keys:ordered,candidateDigest:contentDigest(manifest,'beyond-beta-candidate'),payload};descriptors.set(id,d);
    }else if(d.manifest.ownerAgent!==owner||!keys.every(k=>d.keys.includes(k))||keys.length!==d.keys.length)throw Error('IMMUTABLE_CANDIDATE_CHANGED');
    const external=present(comparisonUniverse)?contentDigest(comparisonUniverse,'modeled-recipient-beta-universe'):null;
    d.preparedComparatorDigest=external;d.preparedWeek=week;
    return {candidateId:id,candidateVersion:d.manifest.version,candidateDigest:d.candidateDigest,betaVersion:c.betaVersion,
      policyVersion:c.policyVersion,scopeDigest:scope,environmentDigest:environment,
      comparisonUniverseDigest:combineComparisonDigest(network.inventoryDigest(d.key),external),
      evaluatedAt:week,expiresAt:Math.min(expiryWeek,d.manifest.expiresAt),prerequisitePins:clone(d.manifest.prerequisitePins)};
  }
  function signTransition(key,action,options,week){
    const p=network.prepareTransition(key,action,options,week),agent=p.command.actor;
    const root=createFixtureRoot(p.packet,{agent,signer:signer(agent),snapshotId:network.context().currentSnapshotId,
      issuedAt:week,expiresAt:week+1000,nonce:`root:${nonce++}`,graphId:p.packet.graphId},resolver);
    return network.commitTransition(p,root,week);
  }
  function process({id,keys,owner=people[0],assessment,evidence,readyWeek,expiryWeek,comparisonUniverse},revalidation=false){
    const week=readyWeek??assessment?.evaluatedAt;
    try{
      const d=descriptors.get(id);if(!d)return fail(id,'ASSESSMENT_BINDINGS_REQUIRED_FIRST',week);
      if(d.manifest.ownerAgent!==owner||!Array.isArray(keys)||keys.length!==d.keys.length||keys.some(k=>!d.keys.includes(k)))return fail(id,'CANDIDATE_CONTEXT_CHANGED',week);
      const currentComparator=present(comparisonUniverse)?contentDigest(comparisonUniverse,'modeled-recipient-beta-universe'):null;
      if(currentComparator!==d.preparedComparatorDigest)return fail(id,'RECIPIENT_BETA_UNIVERSE_CHANGED_OR_NOT_SUPPLIED',week);
      if(week!==assessment?.evaluatedAt||expiryWeek!==undefined&&assessment.expiresAt>expiryWeek)return fail(id,'ASSESSMENT_TIME_BINDING_MISMATCH',week);
      const e={mode:'MODELED',replayAvailable:true,boundaryPass:true,blockedClaimsPresent:false,
        artifactDigest:d.manifest.implementationDigest,replayDigest:assessment.observedPairsDigest,
        provenanceDigest:contentDigest({candidateId:id,betaVersion:assessment.betaVersion,evaluationCostCents:assessment.evaluationCostCents,
          source:'frozen-simulation-paired-probes',actualModelExecutions:0},'modeled-evidence-provenance'),
        empiricalOperationalValidation:false,...(evidence??{})};
      if(!registered.has(d.key)){network.submitCandidate(d.manifest,{privatePayload:d.payload,now:week});registered.add(d.key);network.attachEvidence(d.key,e,week);}
      else if(revalidation){const begin=network.beginRevalidation(d.key,e,week);if(!begin.ok)return fail(id,begin.reasons.join('|'),week);}
      else return fail(id,'EXISTING_VERSION_REQUIRES_EXPLICIT_REVALIDATION',week);
      const assessed=network.recordAssessment(d.key,assessment,week,{declaredComparatorDigest:d.preparedComparatorDigest});
      if(!assessed.ok)return fail(id,assessed.reasons.join('|'),week);
      const bound=network.validationBinding(d.key),validator=people.find(a=>a!==owner)??'validator.agent.agi.eth';
      const attestation=createFixtureAttestation(bound,{agent:validator,signer:signer(validator),snapshotId:network.context().currentSnapshotId,
        issuedAt:week,expiresAt:bound.expiresAt,nonce:`validation:${nonce++}`,graphId:`${networkId}:${owner}`},resolver);
      const validated=network.validate(d.key,[attestation],week);if(!validated.ok)return fail(id,validated.reasons.join('|'),week);
      const admitted=signTransition(d.key,'admit',{},week);if(!admitted.ok)return fail(id,admitted.reasons.join('|'),week);
      log.push({id,week,event:revalidation?'modeled-revalidation-admitted':'modeled-alpha-admitted',key:d.key,
        assessedLowerBoundNetCents:assessment.assessedLowerBoundNetCents,allMembersCanDiscover:true,adoption:'OPTIONAL'});
      return {id,key:d.key,keys:clone(d.keys),status:'ADMITTED',mode:'MODELED_GRAPH_ADMISSION',empiricalOperationalValidation:false,
        graphRoot:admitted.graphRoot,assessedLowerBoundNetCents:assessment.assessedLowerBoundNetCents};
    }catch(error){return fail(id,error.message,week);}
  }
  function available({id,member,week}){
    try{const d=descriptors.get(id);if(!d||!registered.has(d.key)||!people.includes(member))return false;
      return network.requestReuse(d.key,memberProof(member,week),mission(),{right:'execute',dryRun:true},week).ok;
    }catch{return false;}
  }
  function retire(id,reason,week){
    try{const d=descriptors.get(id);if(!d||!registered.has(d.key))return fail(id,'NO_ADMITTED_RECORD_TO_RETIRE',week);
      const result=signTransition(d.key,'retire',{reason:String(reason)},week);if(!result.ok)return fail(id,result.reasons.join('|'),week);
      log.push({id,week,event:'retired',reason});return true;
    }catch(error){return fail(id,error.message,week);}
  }
  return Object.freeze({assessmentBindings,admit:input=>process(input,false),revalidate:input=>Boolean(process(input,true)),available,
    advanceBeta:(version,week,baselineKeys=[])=>network.advanceBeta(version,week,baselineKeys),retire,
    recordFailure:(failure,week)=>network.recordFailure(failure,week),
    protectEvaluationMaterial:values=>network.protectEvaluationMaterial(values),
    snapshot:({includeCiphertext=false}={})=>({...network.snapshot({includeCiphertext}),adapterLog:clone(log),modeledMembers:clone(people),secretKeysExported:false}),
    // Explicit optional adoption. Availability alone never records an actual use.
    reuse:({id,member,week,right='execute'})=>{const d=descriptors.get(id);if(!d)return {ok:false,reasons:['UNKNOWN_CANDIDATE']};
      return network.requestReuse(d.key,memberProof(member,week),mission(),{right},week);},
    discover:({member,week})=>network.discover(memberProof(member,week),mission(),week),
    context:()=>network.context()});
}
