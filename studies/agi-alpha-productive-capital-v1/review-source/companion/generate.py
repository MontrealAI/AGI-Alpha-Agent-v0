# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy,hashlib,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTEXTS={
 'sdk_release':{'title':'SDK release: source inventory, staged rollout and maintainer dossier','simple':['source freeze','package build','unit tests','documentation','compatibility check','release review'],'complex':['source freeze','package build','unit tests','integration tests','URI examples','migration guide','Linux package','macOS package','release review','archive checks','canary plan','handoff']},
 'research_publication':{'title':'Research publication: evidence custody, production schedule and bilingual dossier','simple':['data freeze','analysis','figures','manuscript','citation check','publication review'],'complex':['source freeze','data audit','analysis','figures','manuscript','bibliography','translation','layout','reproduction','archive build','technical review','release handoff']},
 'operations_handoff':{'title':'Operations handoff: component register, dependency plan and operator dossier','simple':['inventory','dependency map','migration plan','backup procedure','acceptance review','handoff'],'complex':['inventory','dependency audit','migration plan','backup procedure','restore plan','access checklist','documentation','staging plan','rollout plan','recovery review','acceptance','handoff']}}

def dump(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

def make_project(context,stratum,seed,project_id):
 rng=random.Random(seed);meta=CONTEXTS[context];labels=meta[stratum];n=8 if stratum=='simple' else 14
 sources=json.loads((ROOT/'data/source_manifest.json').read_text());sources=sources[:n]
 components=[]
 for i,s in enumerate(sources):
  deps=[]
  if i>0 and i%3!=0:deps.append(f'C{i:02d}')
  if i>3 and i%4==0:deps.append(f'C{i-2:02d}')
  if context=='research_publication' and i>2 and i%3==0:deps.append('C01')
  if context=='operations_handoff' and i>3 and i%3==1:deps.append('C03')
  components.append({'id':s['id'],'path':s['path'],'content':(ROOT/'data/sources'/s['local']).read_text(),'source_url':s['url'],'source_sha256':s['sha256'],'deps':sorted(set(deps))})
 jobs=[]
 for i,label in enumerate(labels):
  deps=[]
  if i>0:deps.append(f'J{max(1,i-rng.randrange(0,min(3,i)))}')
  if i>=4 and i%3==0:deps.append('J2')
  jobs.append({'id':f'J{i+1}','duration':rng.randint(1,4),'crew':1 if i%4 else 2,'deps':sorted(set(deps))})
 horizon=80;task={'schema':'release-plan/v1','id':project_id+'-c0','kind':'plan','public_or_synthetic':'synthetic','planning_only':True,'jobs':jobs,'capacity':[3]*horizon,'deadline':65,'release':{f'J{len(jobs)}':2}}
 return {'schema':'productive-project/v1','id':project_id,'title':meta['title'],'context':context,'stratum':stratum,'cycle':0,'data_class':'public-derived-synthetic','synthetic_scope':'Declared component dependencies, work requirements, durations, capacity and revisions are authored synthetic fixtures, not observed repository dependency graph or paid customer jobs. Source bytes are pinned public upstream files.','components':components,'task':task,'job_labels':dict(zip([j['id'] for j in jobs],labels))}

def revised(base,cycle,previous=None):
 p=copy.deepcopy(base);p['cycle']=cycle;p['task']['id']=p['id']+f'-c{cycle}'
 if cycle>=2:
  target=len(p['components'])-4;c=p['components'][target];c['content']+='\n// Productive Capital study synthetic revision: deployment evidence must be refreshed.\n'
  p['task']['jobs'][-3]['duration']+=1
 if cycle>=3:
  c=p['components'][-1]
  if 'C02' not in c['deps']:c['deps'].append('C02');c['deps'].sort()
  if previous is None:raise ValueError('PREDECESSOR_REQUIRED')
  prior=previous['plan']['result'];baseline={j['id']:j['start'] for j in prior['schedule']}
  p['task']['kind']='repair';p['task']['baseline']=baseline;p['task']['locked']={k:v for k,v in baseline.items() if v<3};p['observed_at']=3
  for t in range(10,15):p['task']['capacity'][t]=2
  p['task']['movement_limit']=80
 return p

def generate(out):
 out=Path(out);inventory=[]
 for i,context in enumerate(CONTEXTS):
  for j,stratum in enumerate(['simple','complex']):
   pid=f'P{i+1}{j+1}';seed=2026102500+31*i+17*j;p=make_project(context,stratum,seed,pid)
   dump(out/(pid+'.json'),p);inventory.append({'project_id':pid,'context':context,'stratum':stratum,'seed':seed,'components':len(p['components']),'jobs':len(p['task']['jobs']),'families':['release_assurance','rollout_planning','bilingual_dossier'],'cycles':[0,1,2,3]})
 dump(out/'inventory.json',inventory);return inventory
if __name__=='__main__':
 import sys
 generate(sys.argv[1] if len(sys.argv)>1 else ROOT/'data/confirmation')
