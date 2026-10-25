# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib,json,re

def check(project,result,previous=None):
 failures=[];checks=0
 def require(condition,label):
  nonlocal checks
  checks+=1
  if not condition:failures.append(label)
 components={c['id']:c for c in project['components']};evidence={c['id']:c for c in result['assurance']['components']}
 require(set(evidence)==set(components),'all source components')
 closure={k:set() for k in components}
 for _ in range(len(components)):
  for k,c in components.items():
   for d in c['deps']:closure[k]|={d}|closure[d]
 expected_changed=[]
 for k,c in components.items():
  e=evidence[k];require(e['path']==c['path'],k+' path');h=hashlib.sha256(c['content'].encode()).hexdigest();old=previous['index'].get(k) if previous else None
  require(e['current_sha256']==h,k+' digest');require(e['source_url']==c['source_url'],k+' source');require(e['original_source_sha256']==c['source_sha256'],k+' original identity')
  require(e['bytes']==len(c['content'].encode()),k+' bytes');require(e['line_count']==len(c['content'].split('\n')),k+' line count');require(set(e['deps'])==set(c['deps']),k+' dependencies');require(set(e['transitive_dependencies'])==closure[k],k+' closure')
  if not old or old['hash']!=h or set(old['deps'])!=set(c['deps']) or old['evidence']['path']!=c['path'] or old['evidence']['source_url']!=c['source_url'] or old['evidence']['original_source_sha256']!=c['source_sha256']:expected_changed.append(k)
 affected={k for k in components if k in expected_changed or closure[k]&set(expected_changed)}
 removed=set(previous['index'])-set(components) if previous else set();require(set(result['impact']['removed'])==removed,'removed source identities')
 require(set(result['impact']['changed'])==set(expected_changed),'changed sources');require(set(result['impact']['invalidated'])==affected,'complete invalidation');require(set(result['impact']['unchanged'])==set(components)-affected,'unchanged exact complement')
 task=project['task'];jobs={j['id']:j for j in task['jobs']};plan=result['plan'];schedule=plan['result']['schedule'];slots={s['id']:s for s in schedule};usage=[0]*len(task['capacity'])
 require(set(slots)==set(jobs) and len(schedule)==len(jobs),'complete schedule');require(plan['task']==task,'plan task binding')
 movement=0
 for k,j in jobs.items():
  s=slots[k];require(type(s['start']) is int and type(s['end']) is int,k+' integer times');require(s['end']==s['start']+j['duration'],k+' duration');require(s['start']>=task.get('release',{}).get(k,0),k+' release');require(0<=s['start']<s['end']<=len(usage),k+' horizon')
  if k in task.get('locked',{}):require(s['start']==task['locked'][k],k+' locked')
  for d in j['deps']:require(slots[d]['end']<=s['start'],k+' precedence '+d)
  for t in range(s['start'],s['end']):usage[t]+=j['crew']
  movement+=abs(s['start']-task.get('baseline',{}).get(k,s['start']))
 require(all(u<=c for u,c in zip(usage,task['capacity'])),'capacity');require(max(s['end'] for s in schedule)==plan['result']['makespan'],'makespan');require(plan['result']['makespan']<=task['deadline'],'deadline');require(plan['result']['movement']==movement,'movement count');require(movement<=task.get('movement_limit',10**9),'movement limit')
 artifacts={a['name']:a['content'] for a in result['pack']['result']['artifacts']};doc=artifacts['release-dossier.html'];co=result['consistency']
 require(json.loads(artifacts['release-assurance.json'])==result['assurance'],'assurance artifact');require(json.loads(artifacts['rollout-plan.json'])==plan,'plan artifact');require(json.loads(artifacts['change-impact.json'])==result['impact'],'impact artifact');require(json.loads(artifacts['consistency.json'])==co,'consistency artifact');require(hashlib.sha256(doc.encode()).hexdigest()==co['dossier_sha256'],'dossier content identity')
 require('Décision' in doc and 'Decision' in doc,'bilingual headings');require(str(plan['result']['makespan']) in doc,'document makespan')
 for k,e in evidence.items():require(e['current_sha256'] in doc and e['source_url'] in doc,k+' document evidence')
 require(co['project_id']==project['id'] and co['cycle']==project['cycle'],'common revision');require(co['locked_starts']==task.get('locked',{}),'lock certificate');require(co['source_keys']=={k:e['dependency_key'] for k,e in evidence.items()},'common source keys');require(co['parent_integrity']==(previous['integrity'] if previous else None),'predecessor binding')
 require([s['stage'] for s in result['trace']]==['Identify','Out-Learn','Out-Think','Out-Design','Out-Strategise','Out-Execute','Out-Evolve'],'seven artifact stages')
 require(previous is None or previous['project_id']==project['id'],'predecessor project identity')
 require(co['assurance_digest']==digest('assurance',result['assurance']),'assurance digest')
 require(co['planning_digest']==digest('planning',plan),'planning digest')
 require(co['impact_digest']==result['impact']['digest'],'impact reference')
 require(result['impact']['digest']==digest('change-impact',{k:v for k,v in result['impact'].items() if k!='digest'}),'impact digest')
 require(result['state']['integrity']==digest('productive-state',{k:v for k,v in result['state'].items() if k!='integrity'}),'retained state digest')
 if result['metrics']['child_calls']:
  require(result['impact']['parent_digest']==result['trace'][-1]['artifact']['parent_call']['output_digest'],'actual parent call binding')
  require(result['state']['child_registry']['child_digest']==result['impact']['child_digest'],'child registry binding')
 keys={}
 for _ in range(len(components)):
  for k,c in components.items():
   if all(d in keys for d in c['deps']):keys[k]=digest('evidence-node',{'id':k,'path':c['path'],'source':hashlib.sha256(c['content'].encode()).hexdigest(),'url':c['source_url'],'source_sha256':c['source_sha256'],'deps':[[d,keys[d]] for d in sorted(c['deps'])]})
 require(keys==co['source_keys'],'source keys recomputed')
 return {'accepted':not failures,'checks':checks,'failures':failures,'family_acceptance':{'release_assurance':not any('schedule' in f for f in failures) and not failures,'rollout_planning':not failures,'bilingual_dossier':not failures},'custody':'Separate Python implementation, same session and task sources; not blinded or organizationally independent.'}

def digest(domain,value):
 body=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))
 return hashlib.sha256(('successor-omega/v1:'+domain+'\0'+body).encode()).hexdigest()
