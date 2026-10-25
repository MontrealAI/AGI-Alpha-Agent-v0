# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse,copy,hashlib,importlib.util,json,os,platform,resource,shutil,statistics,subprocess,sys,time
from pathlib import Path
from generate import ROOT,dump,generate,make_project,revised
from check import check
ARMS=['full_rebuild','flywheel','conventional_cache']
FAMILIES=['release_assurance','rollout_planning','bilingual_dossier']

def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def node(request):
 start=time.perf_counter();cpu=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
 p=subprocess.run([shutil.which('node'),str(ROOT/'companion/cli.mjs')],input=json.dumps(request),capture_output=True,text=True,timeout=30)
 after=resource.getrusage(resource.RUSAGE_CHILDREN);elapsed=(time.perf_counter()-start)*1000
 try:r=json.loads(p.stdout)
 except Exception:raise RuntimeError({'returncode':p.returncode,'stdout':p.stdout[:500],'stderr':p.stderr[:2000]})
 r['process_wall_ms']=elapsed;r['process_cpu_ms']=1000*((time.process_time()-cpu)+(after.ru_utime-before.ru_utime)+(after.ru_stime-before.ru_stime));r['returncode']=p.returncode;r['stderr']=p.stderr
 return r

def task_normal(t):
 t=copy.deepcopy(t);t.pop('id',None);return t

def run(out,development=False):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);init_wall=time.perf_counter();init_cpu=time.process_time()
 native=load_module('native',ROOT/'vendor/alpha/companion/specialist.py');repair=load_module('repair',ROOT/'vendor/alpha/native_repair.py')
 initialization={'wall_ms':(time.perf_counter()-init_wall)*1000,'cpu_ms':(time.process_time()-init_cpu)*1000,'scope':'One native dependency import/setup per campaign; code design, provider integration and human review are unmeasured.'}
 if development:bases=[make_project('sdk_release','simple',1729,'DEV01')]
 else:
  inventory=generate(ROOT/'data/confirmation');bases=[json.loads((ROOT/'data/confirmation'/f"{i['project_id']}.json").read_text()) for i in inventory]
 freeze=ROOT/'protocol/experiment-FREEZE.json';binding=hashlib.sha256(freeze.read_bytes()).hexdigest() if freeze.exists() else '0'*64
 records=[];construction=[];raw=out/'records.jsonl';raw.write_text('')
 for base in bases:
  previous={a:None for a in ARMS};children={a:None for a in ARMS}
  for cycle in range(4):
   order=ARMS[cycle%3:]+ARMS[:cycle%3]
   for arm in order:
    project=revised(base,cycle,previous[arm]);stem=f"{base['id']}-c{cycle}-{arm}";directory=out/'missions'/stem;directory.mkdir(parents=True,exist_ok=True)
    dump(directory/'input.json',project)
    if arm=='flywheel' and cycle==2:
     built=node({'operation':'construct','project':project,'previous':previous[arm]});dump(directory/'construction.json',built)
     if not built['ok']:raise RuntimeError(built)
     children[arm]=built['result']['child'];construction.append({'project_id':base['id'],'cycle':cycle,'id':'dependency-repair-v1','parent_id':'evidence-index-v1','binding_digest':children[arm]['digest'],'construction_process_wall_ms':built['process_wall_ms'],'construction_process_cpu_ms':built['process_cpu_ms'],'programming_cost_status':'UNMEASURED; elapsed covers fixed-grammar descriptor binding and index computation only.','construction_class':'Authored algorithm bound to a new accepted predecessor, not autonomous algorithm invention.'})
    total_start=time.perf_counter();total_cpu=time.process_time();before_all=resource.getrusage(resource.RUSAGE_CHILDREN);native_result=None;native_reused=False
    if arm!='full_rebuild' and previous[arm] and task_normal(previous[arm]['plan']['task'])==task_normal(project['task']):native_reused=True
    else:
     try:native_result=(repair if project['task']['kind']=='repair' else native).solve(project['task'],time_limit=2.0)
     except Exception as error:native_result={'schedule':None,'status':'ERROR: '+type(error).__name__+': '+str(error),'wall_ms':(time.perf_counter()-total_start)*1000}
    native_cpu=(time.process_time()-total_cpu)*1000
    r=node({'project':project,'options':{'arm':arm,'previous':previous[arm],'child':children[arm],'nativeResult':native_result,'sourceHash':binding}})
    overall_wall=(time.perf_counter()-total_start)*1000
    check_start=time.perf_counter();checker=check(project,r['result'],previous[arm]) if r['ok'] else {'accepted':False,'checks':0,'failures':[r['error']]}
    checker_wall=(time.perf_counter()-check_start)*1000;whole_wall=overall_wall+checker_wall
    dump(directory/'execution.json',r);dump(directory/'native.json',{'result':native_result,'reused':native_reused,'cost_included':True});dump(directory/'acceptance.json',checker)
    if r['ok']:
     for artifact in r['result']['pack']['result']['artifacts']:(directory/artifact['name']).write_text(artifact['content'])
     dump(directory/'state.json',r['result']['state'])
    metrics=r.get('result',{}).get('metrics',{});after_all=resource.getrusage(resource.RUSAGE_CHILDREN);whole_wall=(time.perf_counter()-total_start)*1000;whole_cpu=1000*(time.process_time()-total_cpu+after_all.ru_utime-before_all.ru_utime+after_all.ru_stime-before_all.ru_stime)
    rec={'project_id':base['id'],'context':base['context'],'stratum':base['stratum'],'cycle':cycle,'slice':'stable' if cycle in [0,1] else 'fresh','arm':arm,'families':FAMILIES,'accepted':checker['accepted'],'family_acceptance':checker.get('family_acceptance',{f:False for f in FAMILIES}),'checks':checker['checks'],'failures':checker['failures'],'wall_ms':whole_wall,'cpu_ms':whole_cpu,'native_cpu_ms':native_cpu,'native_solver_wall_ms':native_result.get('wall_ms') if native_result else 0,'native_status':native_result.get('status') if native_result else 'REUSED_ACCEPTED_PLAN','checker_wall_ms':checker_wall,'process_startup_included':True,'retries':0,'human_interventions':None,'provider_model_calls':0,'source_bytes':metrics.get('source_bytes_read'),'metrics':metrics,'artifact_bytes':sum(len(a['content'].encode()) for a in r.get('result',{}).get('pack',{}).get('result',{}).get('artifacts',[])),'predecessor_integrity':previous[arm]['integrity'] if previous[arm] else None,'retained_integrity':r.get('result',{}).get('state',{}).get('integrity'),'relative_directory':str(directory.relative_to(ROOT))}
    records.append(rec)
    with raw.open('a') as f:f.write(json.dumps(rec)+'\n')
    if checker['accepted']:previous[arm]=r['result']['state']
    else:print('FAILED',stem,checker['failures'],flush=True)
    print(stem,'accepted='+str(checker['accepted']),'wall_ms='+str(round(whole_wall,2)),flush=True)
 guards=[]
 guardbase=copy.deepcopy(bases[0]);guardbase['id']='GUARD';guardbase['task']['id']='GUARD'
 for label in ['cycle','missing_evidence','private_data','too_many_jobs']:
  p=copy.deepcopy(guardbase)
  if label=='cycle':p['components'][0]['deps']=[p['components'][1]['id']]
  elif label=='missing_evidence':p['components'][0]['source_url']=''
  elif label=='private_data':p['data_class']='private'
  else:p['task']['jobs']*=4
  res=node({'operation':'validate','project':p});guards.append({'case':label,'refused':not res['ok'],'error':res.get('error'),'wall_ms':res['process_wall_ms']})
 dump(out/'guards.json',guards)
 summary={'study_id':'agi-alpha-productive-capital-v1','design':'Six project instances, three deliverable families, four cycles and three arms. Repeated runs and family checks are not independent jobs.','execution_scope':'Observed local deterministic research using unchanged pinned Alpha workbench/planner/native specialists; authenticated browser-to-executor NOT RUN.','development':development,'projects':len(bases),'joint_runs':len(records),'family_checks':len(records)*3,'accepted_joint_runs':sum(r['accepted'] for r in records),'source_commit':'f836f06e8351e64db1da770e16e304b5feb01f28','rows':[],'joint_rows':[],'capabilities':construction,'initialization':initialization,'guards':guards,'human_interventions':None,'paid_revenue':None,'measurement_note':'CPU/wall are joint pipeline costs; family rows repeat shared cost and must not be added. Observed zero provider calls describes deterministic pipeline only; upstream engineering/model cost is unmeasured.'}
 for cycle in range(4):
  for arm in ARMS:
   rs=[r for r in records if r['cycle']==cycle and r['arm']==arm]
   row={'cycle':cycle,'arm':arm,'projects':len(rs),'accepted':sum(r['accepted'] for r in rs),'failed':sum(not r['accepted'] for r in rs),'total_wall_ms':sum(r['wall_ms'] for r in rs),'total_cpu_ms':sum(r['cpu_ms'] for r in rs),'median_wall_ms':statistics.median(r['wall_ms'] for r in rs),'work_units':sum(r['metrics'].get('lines_examined',0) for r in rs),'work_unit_definition':'Observed source lines examined for rebuilt evidence cards; not CPU instructions, money or human work.','reused_items':sum(r['metrics'].get('reused_items',0) for r in rs),'built_items':sum(r['metrics'].get('built_items',0) for r in rs),'parent_calls':sum(r['metrics'].get('parent_calls',0) for r in rs),'child_calls':sum(r['metrics'].get('child_calls',0) for r in rs)}
   summary['joint_rows'].append(row)
   for family in FAMILIES:summary['rows'].append({**row,'family':family,'shared_joint_cost':True})
 summary['capability_frontier']={'new_artifact':'Transitive change-impact and cross-artifact consistency certificate tied to accepted predecessor and frozen starts.','same_budget_expansion':'NOT_ESTABLISHED','reason':'Conventional cache and full rebuild provide the same deliverable with the same supported scope. Added interface capability is not proof of previously impractical work becoming feasible.','self_acceleration':'NOT_ESTABLISHED'}
 summary['totals']={'wall_ms':sum(r['wall_ms'] for r in records),'cpu_ms':sum(r['cpu_ms'] for r in records),'assertions':sum(r['checks'] for r in records),'parent_calls':sum(r['metrics'].get('parent_calls',0) for r in records),'child_calls':sum(r['metrics'].get('child_calls',0) for r in records)}
 dump(out/'summary.json',summary);dump(out/'environment.json',{'python':sys.version,'platform':platform.platform(),'node':subprocess.check_output([shutil.which('node'),'--version'],text=True).strip(),'scipy':native.scipy_version,'limits':{'native_seconds_per_call':2.0,'node_process_timeout_seconds':30,'components':18,'planning_jobs':18,'calendar_slots':128},'pid':os.getpid()})
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default=str(ROOT/'outputs'));p.add_argument('--development',action='store_true');args=p.parse_args();run(args.out,args.development)
