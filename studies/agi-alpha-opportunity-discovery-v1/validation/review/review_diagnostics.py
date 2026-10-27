from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import math
import sys

base=Path('/workspace/scratch/9738c9c6b885/alpha-research/studies/agi-alpha-opportunity-discovery-v1')
sys.path.insert(0,str(base/'instrument'))
from continuity import process,load_packet,reml,digest

p=json.loads((base/'results/confirmation-v1/raudenbush1985-packet.json').read_text())
m=json.loads((base/'results/confirmation-v1/raudenbush1985-mission.json').read_text())
checks=[]
def record(name,result,expected,scope):
 checks.append({'name':name,'result':result,'expected':expected,'observed_match':result['status']==expected,'scope':scope})

altered=copy.deepcopy(p)
altered['rows'][0]['yi']+=1
record('packet_edit_with_original_mission',process(altered,m,{'kind':'no_change'}),'hold','Digest binds the supplied packet when original mission receipt is retained.')
changed=copy.deepcopy(m)
changed['purpose']['outcome']='Crop physical yield kg/ha'
record('purpose_changed',process(p,changed,{'kind':'no_change'}),'hold','New mission purpose cannot inherit old purpose digest.')
changed=copy.deepcopy(m)
changed['execute_authorized']='true'
record('authority_string_is_not_boolean_true',process(p,changed,{'kind':'no_change'}),'hold','Typed local authority flag is checked; this is not live authentication.')
record('missing_event_kind',process(p,m,{}),'hold','Missing event kind fails closed with no numerical result.')
event={'kind':'corrected_estimate','row_ids':['1'],'scope_confirmed':True,'replacement':{'yi':.1,'vi':.02}}
changed=copy.deepcopy(event)
changed['source_id']='contradictory:unknown-source'
record('unverified_extra_source_identity',process(p,m,changed),'recomputed','Observed limitation: event source_id is not validated on corrected_estimate; event typing and scoped evidence are trusted upstream.')
changed=copy.deepcopy(event)
changed['covariance']={'1,2':.01}
changed['dependence_disclosed']=True
record('unsupported_covariance_in_extra_event_fields',process(p,m,changed),'recomputed','Observed limitation: unexpected covariance fields are ignored; the independent-row model remains unchanged. Explicit overlap_disclosed kind is required to hold.')
record('explicit_overlap_event',process(p,m,{'kind':'overlap_disclosed'}),'hold','Known dependency event kind requests a different dependence model.')
withdraw={'kind':'withdrawal','row_ids':['2'],'scope_confirmed':True}
sequence=[process(p,m,e) for e in [withdraw,event]]
checks.append({'name':'two_events_are_independent_not_cumulative','first_k':sequence[0]['numeric_result']['k'],'second_k':sequence[1]['numeric_result']['k'],'observed_match':sequence[0]['numeric_result']['k']==18 and sequence[1]['numeric_result']['k']==19,'scope':'The main CLI uses the original packet for every event. These are independent one-event fixtures, not a cumulative event ledger.'})
raw=(base/'data/sources/metadat/dat.raudenbush1985.csv').read_bytes()
try:
 load_packet(raw+b'\n',p['contract']['mapping'])
 checks.append({'name':'changed_raw_bytes','observed_match':False})
except ValueError as e:
 checks.append({'name':'changed_raw_bytes','observed_match':True,'exception':str(e),'scope':'load_packet detects source byte drift when invoked; process does not poll or refetch source.'})
analytic=[]
for name,ys,v in [('equal_variance_positive_heterogeneity',[-1.,0.,1.],.1),('zero_heterogeneity_boundary',[1.,1.,1.],.2)]:
 rows=[{'id':str(i),'yi':y,'vi':v,'active':True} for i,y in enumerate(ys)]
 fit=reml(rows)
 mean=sum(ys)/len(ys)
 tau=max(0,sum((y-mean)**2 for y in ys)/(len(ys)-1)-v)
 se=math.sqrt((v+tau)/len(ys))
 analytic.append({'name':name,'actual':fit,'analytic':{'estimate':mean,'tau2':tau,'se':se},'passed':abs(fit['estimate']-mean)<1e-8 and abs(fit['tau2']-tau)<1e-6 and abs(fit['se']-se)<1e-6})
frozen=[]
for fname in ['construction-freeze-v1.json','confirmation-freeze-v1.json']:
 for row in json.loads((base/'protocol'/fname).read_text())['files']:
  got=hashlib.sha256((base/row['path']).read_bytes()).hexdigest()
  frozen.append({'freeze':fname,'path':row['path'],'expected':row['sha256'],'observed':got,'unchanged':got==row['sha256']})
result={'schema':'independent-review-diagnostics/v1','date':'2026-10-27','frozen_source_unchanged':all(x['unchanged'] for x in frozen),'freeze_checks':frozen,'diagnostics':checks,'analytic_reml_checks':analytic,'status_note':'Observed limitations are reported without changing frozen code/results. Diagnostic recomputation is not commercial or scientific acceptance.'}
out=Path('/workspace/scratch/9738c9c6b885/discovery_science/independent_review_diagnostics.json')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'path':str(out),'frozen_source_unchanged':result['frozen_source_unchanged'],'diagnostic_count':len(checks),'analytic_passes':sum(x['passed'] for x in analytic),'diagnostics':[{'name':c['name'],'matched':c['observed_match']} for c in checks]},indent=2))
