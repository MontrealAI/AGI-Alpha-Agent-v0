# SPDX-License-Identifier: Apache-2.0
"""Small independent, fictional source controls. Never runs economic worlds."""
from pathlib import Path
import hashlib
import json
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'beyond_beta/src'))
SOURCES = [ROOT/'beyond_beta/src/graph_lifecycle.py', ROOT/'beyond_beta/src/fixture_factory.py']
before_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
from fixture_factory import make_fixture_environment, fixture_artifact, matched_evidence, qualify, mission_for
from graph_lifecycle import Refusal


def initial_cost_carry():
    g,p = make_fixture_environment()
    k = g.create(p['creator'], p['writer'], fixture_artifact(), skill_id='failed-build')
    evidence = matched_evidence(g,k,[1,1],[100,100],construction_micros=10000,allocation_uses=1)
    g.register_evidence(p['writer'],k,evidence,0)
    first = g.assess(p['assessor'],k,0)
    try:
        fresh = matched_evidence(g,k,[1,1],[100,100],epoch=1,case_prefix='fresh-after-failure',revalidation=True,construction_micros=0)
        second = qualify(g,p,k,fresh,1)
        g.admit(p['admitter'],k,1)
        result = {'initialQualified':first['qualified'],'initialLowerNetAlpha':first['comparisons'][0]['lowerNetAlphaMicros'],
                  'nextQualified':second['qualified'],'nextLowerNetAlpha':second['comparisons'][0]['lowerNetAlphaMicros'],
                  'historicalConstruction':g.record(k)['historicalConstructionMicros'],'finalStage':g.record(k)['stage']}
        passed = not (not first['qualified'] and second['qualified'] and result['finalStage']=='ADMITTED')
    except Refusal as exc:
        result = {'initialQualified':first['qualified'],'refusal':str(exc)}
        passed = True
    return {'id':'GRAPH-R01','invariant':'A never-admitted candidate cannot omit failed first-qualification construction by relabeling new evidence revalidation.','invariantHeld':passed,'observations':result}


def same_function_composition():
    g,p = make_fixture_environment()
    parent = g.create(p['creator'],p['writer'],fixture_artifact(),skill_id='parent')
    qualify(g,p,parent,matched_evidence(g,parent,[10,10],[30,30]),0)
    g.admit(p['admitter'],parent,0)
    dep = {'key':parent,'artifactHash':g.record(parent)['descriptor']['artifactHash']}
    child = g.create(p['creator'],p['writer'],fixture_artifact(),dependencies=[dep],epoch=1,skill_id='same-function-composition')
    try:
        qualify(g,p,child,matched_evidence(g,child,[1,1],{'beta':[30,30],'inventory:'+parent:[10,10]},epoch=1,case_prefix='composition-fresh'),1)
        g.admit(p['admitter'],child,1)
        permit = g.authorize_reuse(p['executor'],child,mission_for(g),1)
        result = {'compositionStage':g.record(child)['stage'],'dispatch':'PERMITTED','permitType':permit['payload']['type']}
        passed = True
    except Refusal as exc:
        result = {'compositionStage':g.record(child)['stage'],'dispatch':str(exc)}
        passed = result['compositionStage'] != 'ADMITTED'
    return {'id':'GRAPH-R02','invariant':'A composition does not become immediately unusable solely because its own admission invalidates a dependency.','invariantHeld':passed,'observations':result}


def refused_call_clock():
    g,p = make_fixture_environment()
    try:
        g.create(p['reader'],p['writer'],fixture_artifact(),epoch=9000,skill_id='unauthorized')
        first = 'INCORRECTLY_AUTHORIZED'
    except Refusal as exc:
        first = str(exc)
    try:
        k = g.create(p['creator'],p['writer'],fixture_artifact(),epoch=1,skill_id='authorized')
        after = 'CREATED:'+k
        passed = first != 'INCORRECTLY_AUTHORIZED'
    except Refusal as exc:
        after = str(exc)
        passed = False
    return {'id':'GRAPH-R03','invariant':'An unauthorized refused call cannot advance trusted lifecycle time and deny a later valid call.','invariantHeld':passed,'observations':{'unauthorized':first,'authorizedAfterRefusal':after}}


probes=[initial_cost_carry(),same_function_composition(),refused_call_clock()]
after_hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
result={'schema':'beyond-beta-independent-graph-review/v1','createdAt':datetime.now(timezone.utc).isoformat(),
        'evidenceClass':'own-observation-of-fictional-source-controls','sourcesBefore':before_hashes,'sourcesAfter':after_hashes,
        'sourceStableDuringProbe':before_hashes==after_hashes,
        'scope':'Fictional cost units and fixture identities; no calibrated economic worlds, real capabilities, production identities, or sales.',
        'probes':probes,'invariantsHeld':sum(x['invariantHeld'] for x in probes),'controls':len(probes)}
destination=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).with_name('graph-review-initial.json')
if destination.exists():raise RuntimeError('Preserve old review records; supply a new output path')
destination.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'output':str(destination),'invariantsHeld':result['invariantsHeld'],'controls':len(probes),'sourceStableDuringProbe':result['sourceStableDuringProbe']}))
