import argparse,json,hashlib,random,secrets,time,sys,resource,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion.study import run_stream,REGIMES,ARMS
ROOT=Path(__file__).resolve().parents[1]

def verify():
 freeze=json.loads((ROOT/'protocol/FREEZE.json').read_text());payload={k:freeze[k] for k in ['schema','files','protocol_sha256']}
 if hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=freeze['freeze_sha256']:raise RuntimeError('FREEZE_IDENTITY')
 for name,expected in freeze['files'].items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('FROZEN_SOURCE_CHANGED:'+name)
 return freeze

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--seeds-file');a=p.parse_args();f=verify();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 if a.seeds_file:seeds=json.loads(Path(a.seeds_file).read_text())['seeds'];label='REPRODUCTION_NOT_ADDITIONAL_CONFIRMATION'
 else:
  seeds=[]
  while len(seeds)<24:
   s=secrets.randbits(32)
   if s not in seeds and not 27000<=s<=27200:seeds.append(s)
  label='FIRST_FROZEN_CONFIRMATION'
 if len(seeds)!=24 or len(set(seeds))!=24:raise ValueError('SEED_SCOPE')
 seed_record={'seeds':seeds,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'freeze_sha256':f['freeze_sha256'],'status':label}
 (out/'SEEDS.json').write_text(json.dumps(seed_record,indent=2)+'\n');(out/'trials').mkdir()
 startw=time.perf_counter();startc=time.process_time();r0=resource.getrusage(resource.RUSAGE_CHILDREN);order=random.Random(20261024);summaries=[];launch=[]
 for index,seed in enumerate(seeds):
  regime=REGIMES[index%4];arms=ARMS[:];order.shuffle(arms)
  for arm in arms:
   name=f'{index:02}-{regime["name"]}-{arm}';launch.append(name)
   s=run_stream(seed,regime,arm,out/'trials'/name,f['freeze_sha256']);summaries.append(s)
   (out/'PROGRESS.json').write_text(json.dumps({'completed':len(summaries),'total':168,'last':name,'freeze':f['freeze_sha256']})+'\n')
   print(json.dumps({'completed':len(summaries),'trial':name,'qualified':s['qualified'],'offered':s['offered'],'failure':s.get('failure'),'cpu_ms':s['total_cpu_ms']}),flush=True)
 r1=resource.getrusage(resource.RUSAGE_CHILDREN)
 execution={'status':label,'freeze_sha256':f['freeze_sha256'],'started':seed_record['created_utc'],'finished_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'wall_seconds':time.perf_counter()-startw,'python_cpu_seconds':time.process_time()-startc,'child_cpu_seconds':r1.ru_utime+r1.ru_stime-r0.ru_utime-r0.ru_stime,'trials':len(summaries),'order':launch,'platform':platform.platform(),'python':platform.python_version(),'manual_intermediate_triggers':0,'confirmation_reruns':0,'monetary_cost':None,'notes':'One foreground campaign, exact fixed source. CPU/account/wall measures distinct. All partial failures retained.'}
 (out/'EXECUTION.json').write_text(json.dumps(execution,indent=2)+'\n');(out/'SUMMARIES.json').write_text(json.dumps(summaries,indent=2)+'\n');verify()
if __name__=='__main__':main()
