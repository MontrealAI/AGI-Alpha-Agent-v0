# SPDX-License-Identifier: Apache-2.0
"""Additional independent fictional controls for complete costs and composition rights."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'beyond_beta/src'))
SOURCES=[ROOT/'beyond_beta/src/graph_lifecycle.py',ROOT/'beyond_beta/src/fixture_factory.py']
before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
from fixture_factory import *
from graph_lifecycle import Refusal, OfflinePrincipal, authority_fixture

def verification_cost_carry():
 g,p=make_fixture_environment();k=g.create(p['creator'],p['writer'],fixture_artifact(),skill_id='failed-verification')
 e=matched_evidence(g,k,[1,1],[100,100]);e['arms']['candidate']['lifecycleCosts']['verification']=10000
 e=bind_cost_ownership(e)
 g.register_evidence(p['writer'],k,e,0);first=g.assess(p['assessor'],k,0)
 try:
  fresh=matched_evidence(g,k,[1,1],[100,100],epoch=1,case_prefix='new-initial')
  second=qualify(g,p,k,fresh,1);g.admit(p['admitter'],k,1)
  observations={'initialQualified':first['qualified'],'initialLowerNetAlpha':first['comparisons'][0]['lowerNetAlphaMicros'],'nextQualified':second['qualified'],'nextLowerNetAlpha':second['comparisons'][0]['lowerNetAlphaMicros'],'stage':g.record(k)['stage']}
  passed=not(not first['qualified'] and second['qualified'])
 except Refusal as ex: observations={'initialQualified':first['qualified'],'refusal':str(ex)};passed=True
 return {'id':'GRAPH-R04','invariant':'Failed first-qualification verification cost cannot disappear when fresh initial evidence is submitted.','invariantHeld':passed,'observations':observations}

def nested_support_cost():
 g,p=make_fixture_environment()
 a=g.create(p['creator'],p['writer'],fixture_artifact(),skill_id='support-a',support_only=True,support_construction_micros=10000)
 da={'key':a,'artifactHash':g.record(a)['descriptor']['artifactHash']}
 b=g.create(p['creator'],p['writer'],fixture_artifact(),skill_id='support-b',support_only=True,support_construction_micros=0,dependencies=[da])
 db={'key':b,'artifactHash':g.record(b)['descriptor']['artifactHash']}
 c=g.create(p['creator'],p['writer'],fixture_artifact('composition'),skill_id='nested-bundle',dependencies=[db])
 try:
  e=matched_evidence(g,c,[1,1],[100,100],construction_micros=0)
  assessed=qualify(g,p,c,e);g.admit(p['admitter'],c,0)
  observations={'qualified':assessed['qualified'],'lowerNetAlpha':assessed['comparisons'][0]['lowerNetAlphaMicros'],'stage':g.record(c)['stage'],'boundSupportCosts':e['composition'].get('supportConstructionMicros'),'trueFictionalSupportCost':10000,'chargedConstruction':e['arms']['candidate']['lifecycleCosts']['construction']};passed=False
 except Refusal as ex:observations={'refusal':str(ex),'trueFictionalSupportCost':10000};passed=True
 return {'id':'GRAPH-R05','invariant':'A bundle includes complete transitive support costs without double counting shared dependencies.','invariantHeld':passed,'observations':observations}

def private_composition_rights():
 g,p=make_fixture_environment(private_ablation=True)
 other=OfflinePrincipal('other.agent.agi.eth');g.authorities[other.name]=authority_fixture(other,['creator','compose','execution','retrieve'])
 a=g.create(p['creator'],p['writer'],fixture_artifact(),skill_id='private-support',shareable=False,support_only=True,support_construction_micros=10)
 dep={'key':a,'artifactHash':g.record(a)['descriptor']['artifactHash']}
 try:
  c=g.create(other,p['writer'],fixture_artifact('composition'),skill_id='other-private-bundle',shareable=False,dependencies=[dep])
  e=matched_evidence(g,c,[1,1],[100,100],construction_micros=10)
  qualify(g,p,c,e);g.admit(p['admitter'],c,0)
  permit=g.authorize_reuse(other,c,mission_for(g,'composition'),0)
  released=g.resolve_reuse(other,permit,0)
  leaked=a in released.get('confinedComponentArtifacts',{})
  observations={'firstCreator':p['creator'].name,'secondCreator':other.name,'componentShareable':False,'foreignPrivateComponentReleased':leaked};passed=not leaked
 except Refusal as ex:observations={'refusal':str(ex)};passed=True
 return {'id':'GRAPH-R06','invariant':'A creator cannot obtain another creator\'s private component through its own private bundle without compose/retrieval authority.','invariantHeld':passed,'observations':observations}

probes=[verification_cost_carry(),nested_support_cost(),private_composition_rights()]
after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
result={'schema':'beyond-beta-independent-graph-review/v1','createdAt':datetime.now(timezone.utc).isoformat(),'evidenceClass':'own-observation-of-fictional-source-controls','sourcesBefore':before,'sourcesAfter':after,'sourceStableDuringProbe':before==after,'scope':'Fictional costs, ephemeral fixture agents and sanitized IR; no economic worlds or private customer material.','probes':probes,'invariantsHeld':sum(p['invariantHeld'] for p in probes),'controls':len(probes)}
dest=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).with_name('graph-review-additional-initial.json')
if dest.exists():raise RuntimeError('Preserve prior record; choose a new path')
dest.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'output':str(dest),'invariantsHeld':result['invariantsHeld'],'controls':len(probes),'sourceStableDuringProbe':result['sourceStableDuringProbe']}))
