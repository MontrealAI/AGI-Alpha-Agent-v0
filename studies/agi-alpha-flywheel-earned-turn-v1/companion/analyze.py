import argparse,json,collections
from pathlib import Path
import numpy as np

def analyze(root):
 rows=[json.loads(p.read_text()) for p in sorted(Path(root).glob('trials/*/summary.json'))]
 by={a:sorted([r for r in rows if r['arm']==a],key=lambda r:(r['regime']['name'],r['seed'])) for a in sorted({r['arm'] for r in rows})}
 summary={a:{'trials':len(v),'qualified':sum(r['qualified'] for r in v),'offered':sum(r['offered'] for r in v),'mean_cpu_ms':float(np.mean([r['total_cpu_ms'] for r in v])),'total_cpu_ms':sum(r['total_cpu_ms'] for r in v),'total_wall_ms':sum(r['total_wall_ms'] for r in v),'parent_using_qualified_fresh':sum(r['parent_calls_in_fresh_successors'] for r in v),'successors':sum(r['successor_constructed'] for r in v),'released_ms':sum(r['released_service_quota_ms'] for r in v),'construction_debits_ms':sum(r['successor_cpu_ms'] for r in v),'failures':sum('failure' in r for r in v),'control_violations':sum(r.get('control_budget_exceeded',False) for r in v),'storage_bytes':sum(r['storage_bytes'] for r in v)} for a,v in by.items()}
 fly=by['flywheel'];keys=[(r['regime']['name'],r['seed']) for r in fly]
 rng=np.random.default_rng(20261025);strata=[[i for i,k in enumerate(keys) if k[0]==g] for g in sorted({k[0] for k in keys})]
 draws=np.concatenate([rng.choice(s,size=(10000,len(s)),replace=True) for s in strata],axis=1)
 fv=np.array([r['total_cpu_ms'] for r in fly]);comparisons={}
 for a,v in by.items():
  assert [(r['regime']['name'],r['seed']) for r in v]==keys
  av=np.array([r['total_cpu_ms'] for r in v]);dist=fv[draws].mean(axis=1)/av[draws].mean(axis=1)
  comparisons[a]={'cpu_ratio':float(fv.mean()/av.mean()),'ci95':np.quantile(dist,[.025,.975]).tolist(),'interpretation':'descriptive except native_refactor primary and conventional guard'}
 primary=comparisons['native_refactor']['ci95'][1]<.95;guard=comparisons['conventional_reuse']['ci95'][1]<1.10
 all_trials_clean=all(not r.get('failure') and not r.get('control_budget_exceeded') and not r.get('account_overrun') for r in rows)
 quality=all_trials_clean and all(summary[a]['qualified']==summary[a]['offered'] and not summary[a]['failures'] and not summary[a]['control_violations'] for a in ['flywheel','native_refactor','conventional_reuse'])
 result={'schema':'earned-turn-analysis/v1','arms':summary,'comparisons':comparisons,'primary_gate':primary,'conventional_noninferiority_guard':guard,'quality_resource_gate':quality,'product_admission':'ACCEPT_SCOPED_RESEARCH_PRODUCT' if primary and guard and quality else 'HOLD','full_investment_recovery':'UNRESOLVED','acceleration':'NOT_TESTED','commercial_growth':'NOT_MEASURED','regimes':{}}
 for g in sorted({r['regime']['name'] for r in rows}):
  result['regimes'][g]={a:{'cpu_ms':float(np.mean([r['total_cpu_ms'] for r in v if r['regime']['name']==g])),'qualified':sum(r['qualified'] for r in v if r['regime']['name']==g),'offered':sum(r['offered'] for r in v if r['regime']['name']==g)} for a,v in by.items()}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--out');a=p.parse_args();r=analyze(a.root);text=json.dumps(r,indent=2)+'\n'
 if a.out:Path(a.out).write_text(text)
 print(text)
