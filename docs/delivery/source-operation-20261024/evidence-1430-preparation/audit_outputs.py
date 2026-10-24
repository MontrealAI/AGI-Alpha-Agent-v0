import json,pathlib,hashlib,itertools
r=pathlib.Path(__file__).parent; h=json.loads((r/'history.json').read_text());s=json.loads((r/'status.json').read_text());e=h['evidence'];checks=[];count=0
assert s['state']=='completed' and not s['executor_active'] and not s['authority_granted'] and h['active_authority']==[]
for cid,c in e['campaigns'].items():
 result=c['result'];limit=c['charter']['max_clauses']
 for method,notes in result['results'].items():
  assert len(notes)==len(result['fresh_sources'])
  for doc,n in zip(result['fresh_sources'],notes):
   claims=doc['claims'];by={x['id']:x for x in claims};chosen=set(n['selected']);assert len(chosen)==len(n['selected']) and len(chosen)<=limit and chosen<=by.keys()
   def closure(k):
    return {k}|set().union(*(closure(x) for x in by[k]['depends_on']))
   supported={k for k in chosen if closure(k)<=chosen};weight=sum(by[k]['weight'] for k in supported);total=sum(x['weight'] for x in claims)
   assert set(n['supported_claims'])==supported and set(n['unsupported_claims'])==chosen-supported
   assert n['covered_weight']==weight and n['total_weight']==total and n['score_millionths']==weight*1000000//total
   assert n['text']=='\n'.join(x['text'] for x in claims if x['id'] in chosen)
   assert {(x['id'],x['provenance']) for x in n['references']}=={(x['id'],x['provenance']) for x in claims if x['id'] in chosen}
   if method=='unrestricted-exact-search':
    best=max(sum(by[k]['weight'] for k in sub if closure(k)<=set(sub)) for size in range(limit+1) for sub in itertools.combinations(by,size));assert weight==best
   count+=1
 checks.append({'campaign':cid,'methods':len(result['results']),'decision':result['decision'],'costs':result['costs']})
conf=e['study']['confirmation'];runs=conf['runs'];units={x['unit_id'] for x in runs};ties=[]
for unit in sorted(units):
 rr=[x for x in runs if x['unit_id']==unit];assert len(rr)==3
 assert len({(x['terminal_score_ppm'],x['utility_ppm'],x['search_units'],x['execution_units']) for x in rr})==1
 for x in rr:
  if x['policy'] in ['successor-reuse','conventional-reuse']: assert x['retained_program_tested'] and x['retained_worker_bound']
  else: assert not x['retained_program_tested'] and not x['retained_worker_bound']
 ties.append({'unit':unit,'all_three_tie':True,'score_ppm':rr[0]['terminal_score_ppm'],'search_units_each':rr[0]['search_units'],'execution_units_each':rr[0]['execution_units']})
assert sum(c['result']['costs']['execution_units'] for c in e['campaigns'].values())==s['costs']['execution_units_including_ancestors']==648
assert sum(c['result']['costs']['search_units'] for c in e['campaigns'].values())==s['costs']['search_units_including_ancestors']==378
assert s['retained_capability']['fresh_trials']==6 and s['retained_capability']['fresh_selections']==4
out={'schema':'local-installed-candidate-data-audit/v1','imports_application':False,'status':'PASS','source_history_sha256':hashlib.sha256((r/'history.json').read_bytes()).hexdigest(),'campaigns':len(checks),'independently_checked_note_outputs':count,'all_exact_specialist_outputs_exhaustively_optimal':True,'confirmation_comparators':ties,'retained_capability':s['retained_capability'],'costs':s['costs'],'active_authority_empty':True,'executor_active':False,'scope':'Independent data reconstruction, not institutional independence or new crash/scale/public acceptance','campaign_checks':checks}
(r/'output-audit.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='campaign_checks'},indent=2))
