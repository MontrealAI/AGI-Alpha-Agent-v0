import argparse,json,sys,time,resource
from pathlib import Path
import numpy as np
from scipy.sparse.linalg import cg,LinearOperator
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion.numerical import *
from review.checker import check,inspect
from runtime.workbench_client import WorkbenchClient
from runtime.custody import Custody,CustodyError
ROOT=Path(__file__).resolve().parents[1]
ARMS=['flywheel','conventional_reuse','direct_specialist','parent_rebuilt','equivalent','native_refactor','no_reinvestment']
REGIMES=[{'name':'recurring','side':48,'rank':2,'fresh':12,'restart':False},{'name':'rare','side':48,'rank':2,'fresh':2,'restart':False},{'name':'wide_change','side':48,'rank':32,'fresh':12,'restart':False},{'name':'maintenance','side':64,'rank':2,'fresh':12,'restart':True}]
def cpu_children():
 r=resource.getrusage(resource.RUSAGE_CHILDREN);return 1000*(r.ru_utime+r.ru_stime)
def node_ms(r):
 v=r['node_cpu_us'];return sum(v.values())/1000 if isinstance(v,dict) else v/1000

def _run_stream(seed,regime,arm,out,source_hash='0'*64,audit=None):
 out=Path(out)
 begin_wall=time.perf_counter_ns();begin_cpu=time.process_time_ns();begin_children=cpu_children()
 rows=[];events=[];asset_files={};vectors={};tasks={};state={'factor':None,'update':None,'previous_x':None}
 audit.update({'rows':rows,'events':events,'tasks':tasks,'vectors':vectors})
 base=make_task(seed,regime['side']);A=matrix(base);oid=operator_id(base);setup_cpu=(time.process_time_ns()-begin_cpu)/1e6
 (out/'base.json').write_text(json.dumps(base,separators=(',',':'))+'\n')
 def event(kind,**kw):events.append({'sequence':len(events),'kind':kind,**kw})
 with Custody(out/'custody',source_hash,10000,1000,500,dependencies=DEPENDENCIES,expires_at=time.time()+600,deadline_at=time.time()+300) as custody, WorkbenchClient() as client:
  audit['custody']=custody
  def action(mid,purpose,task,fn,account='service',ceiling=1000):
   control_so_far=(time.process_time_ns()-begin_cpu)/1e6+sum(r['node_cpu_ms'] for r in rows)-sum(r['cpu_ms'] for r in rows)
   if control_so_far>2000:raise CustodyError('EXTERNAL_CONTROL_BUDGET_EXCEEDED')
   start=time.process_time_ns();full_digest=digest(task); input_record={'task_digest':full_digest,'operator_digest':operator_id(task),'mission':mid,'kind':purpose}
   reservation=custody.reserve(mid,account,ceiling,digest(input_record))
   if not reservation['execute']:raise RuntimeError('UNEXPECTED_REUSED_REQUEST')
   got={};state['current_operator_id']=input_record['operator_digest']
   def callback(inputs):
    if inputs!=input_record or digest(task)!=inputs['task_digest']:raise ValueError('FULL_INPUT_BINDING')
    ac=time.process_time_ns();x,details=fn();algcpu=(time.process_time_ns()-ac)/1e6
    cc=time.process_time_ns();checked=check(task,x.tolist()) if x is not None else {'valid':False,'reason':inspect(task) or 'NO_OUTPUT'};checkcpu=(time.process_time_ns()-cc)/1e6
    got.update({'x':x,'details':details,'checker':checked,'algorithm_cpu_ms':algcpu,'checker_cpu_ms':checkcpu})
    return {'valid':bool(checked['valid']),'qualified':bool(checked['valid']),'summary':'Verified network response' if checked['valid'] else 'Refused numerical request','task_digest':full_digest,'solution_digest':digest(x.tolist()) if x is not None else None,'checker':checked,'method':details.get('method'),'parent_calls':details.get('parent_calls',0),'proof':[],'authority':[]}
   dispatched=client.run(mid,purpose,input_record,callback,source_hash)
   if 'x' not in got:got.update({'x':None,'details':{'method':'CALLBACK_FAILED','failure':dispatched.get('callback_failure')},'checker':{'valid':False,'reason':'CALLBACK_FAILED'},'algorithm_cpu_ms':dispatched['callback_cpu_ms'],'checker_cpu_ms':0})
   x=got['x'];valid=bool(got['checker']['valid']);receipt={'valid':valid,'qualified':valid,'source_hash':source_hash,'task_digest':full_digest,'solution_digest':digest(x.tolist()) if x is not None else None,'pack_digest':dispatched['pack']['integrityDigest']}
   (out/(mid+'-pack.json')).write_text(json.dumps(dispatched['pack'],separators=(',',':'))+'\n')
   measured_cpu=(time.process_time_ns()-start)/1e6+node_ms(dispatched)
   terminal=custody.commit(mid,measured_cpu,receipt)
   if not terminal['accepted']:valid=False
   record={'id':mid,'purpose':purpose,'account':account,'valid':valid,'qualified':valid,'input_digest':full_digest,'operator_digest':input_record['operator_digest'],'solution_digest':receipt['solution_digest'],'receipt_digest':digest(receipt),'checker':got['checker'],'details':got['details'],'cpu_ms':measured_cpu,'algorithm_cpu_ms':got['algorithm_cpu_ms'],'checker_cpu_ms':got['checker_cpu_ms'],'node_cpu_ms':node_ms(dispatched),'wall_ms':dispatched['transport_wall_ms'],'reservation_ms':ceiling,'accepted':terminal['accepted']}
   rows.append(record);tasks[mid]=task
   if x is not None:vectors[mid]=x
   if valid:state['previous_x']=x
   return record,x
  def solve(task,mat,method='cg',factor=None,update=None):
   if inspect(task):return None,{'method':'REFUSE_SCOPE','parent_calls':0}
   b=np.asarray(task['rhs']);before=factor.calls if factor else 0
   if update is not None:
    if update.oid!=state['current_operator_id']:raise ValueError('STALE_UPDATE')
    before=update.parent.calls;x=update.solve(b);return x,{'method':'woodbury','parent_calls':update.parent.calls-before,'asset':update.identity,'parent':update.parent.identity}
   if factor is not None:
    if factor.oid!=state['current_operator_id']:raise ValueError('STALE_FACTOR')
    return factor.solve(b),{'method':'retained-factor','parent_calls':factor.calls-before if factor.oid==oid else 0,'factor_calls':factor.calls-before,'asset':factor.identity}
   if method=='factor':
    f=Factor(mat,state['current_operator_id'],'COLAMD');state['new_factor']=f;asset_files['native-current']=f.save(out/('native-'+f.identity+'.npz'))
    return f.solve(b),{'method':'native-refactor','parent_calls':0,'asset':f.identity}
   diagonal=mat.diagonal();x,info=cg(mat,b,x0=state['previous_x'],rtol=1e-11,atol=0,maxiter=4000,M=LinearOperator(mat.shape,matvec=lambda v:v/diagonal))
   if info:raise ValueError('CG_DID_NOT_CONVERGE')
   return x,{'method':'warm-jacobi-cg','parent_calls':0}
  r,x=action('A','Deliver initial response with competent specialist',base,lambda:solve(base,A,method='cg' if arm=='direct_specialist' else 'factor'))
  if not r['valid']:raise RuntimeError('INITIAL_SERVICE_FAILED')
  if arm!='direct_specialist':
   state['factor']=state['new_factor'];asset_files['parent']=asset_files['native-current']
   # The useful first native solve already produced the factors. No redundant builder or second qualification.
   f=state['factor'];custody.retain_asset('parent',f.identity,'A',scope=oid)
   event('PARENT_RETAINED',identity=f.identity,correctness=True,construction='byproduct of accepted first solve',adoption='Declared repeated loads; cheapest native constructor',investment_recovered='UNASSESSED')
  for j in range(1,9):
   tb=with_load(base,seed+1000+j);r,x=action(f'B{j:02}','Fresh load on accepted operator',tb,lambda tb=tb:solve(tb,A,factor=state['factor']))
   if r['valid'] and arm!='no_reinvestment':
    cap=(500000-custody.state['earned_released_us'])/1000;credit=min(50.0,max(0,1000-r['cpu_ms']),cap)
    custody.release_capacity(r['id'],credit,evidence_digest=r['receipt_digest']);event('CAPACITY_RELEASED',mission=r['id'],cpu_ms=credit,origin='unused externally endowed service CPU reservation',incremental_savings_established=False)
  preceding=r;preceding_task=tb;preceding_x=x
  if not preceding['valid']:raise RuntimeError('PREDECESSOR_NOT_ACCEPTED')
  changes=choose_changes(base,preceding_x,regime['rank']);changed=change_task(preceding_task,changes);newA=matrix(changed);new_oid=operator_id(changed)
  event('SUCCESSOR_REQUIREMENT',parent_mission=preceding['id'],parent_receipt=preceding['receipt_digest'],parent_input=preceding['input_digest'],parent_solution=preceding['solution_digest'],changes=changes,selection_rule='largest absolute edge flow in actual accepted B08; stable index tie break')
  calibration=json.loads((ROOT/'development/CALIBRATION.json').read_text())['policy'][f"{regime['side']}:{regime['rank']}"]
  horizon=regime['fresh']+1
  candidate_forecast=1.20*(calibration['update_build_ms']+horizon*calibration['update_use_ms'])
  native_forecast=calibration['native_build_ms']+horizon*calibration['native_use_ms']
  if arm in ['parent_rebuilt','equivalent']:candidate_forecast+=calibration['native_build_ms']
  economically_eligible=candidate_forecast<native_forecast
  diagnostic=arm in ['parent_rebuilt','equivalent']
  use_update=arm in ['flywheel','conventional_reuse','parent_rebuilt','equivalent'] and state['factor'] is not None and (economically_eligible or diagnostic)
  event('PRODUCT_FORECAST',decision='BUILD_LOW_RANK' if use_update else 'RETAIN_NATIVE_ALTERNATIVE',candidate_kernel_cpu_ms=candidate_forecast,native_kernel_cpu_ms=native_forecast,admission='CONSTRUCTION_ABLATION' if diagnostic else 'PROVISIONAL_KERNEL_FORECAST_NOT_PRODUCT_ADMISSION',future_loads=regime['fresh'],rank=regime['rank'],limits='20% development timing margin. Shared checking/dispatch paid by both. Actual full-cost confirmation may reverse forecast. Sunk parent cost retained in investment assessment.')
  if use_update:
   def construct():
    parent=state['factor'];reconstruction=False
    if arm in ['parent_rebuilt','equivalent']:
     parent=Factor(A,oid,'COLAMD' if arm=='parent_rebuilt' else 'MMD_AT_PLUS_A');reconstruction=True
    before=parent.calls;u=Update(parent,base,changes,preceding['receipt_digest'],validated_ids=(oid,new_oid));state['update']=u;state['factor']=parent
    xx=u.solve(changed['rhs']);asset_files['successor']=u.save(out/'successor.npz');asset_files['parent']=parent.save(out/'parent.npz') if reconstruction else asset_files['parent']
    return xx,{'method':'construct-low-rank','asset':u.identity,'parent':parent.identity,'parent_calls':parent.calls-before,'construction_parent_calls':u.construction_parent_calls,'reconstruction':reconstruction,'preceding_receipt':preceding['receipt_digest'],'rank':len(changes),'persisted_bytes':asset_files['successor']['bytes']}
   try:
    rc,xc=action('C','Construct and verify changed-network instrument',changed,construct,'earned',400)
    if not rc['valid']:state['update']=None;use_update=False;event('CANDIDATE_REJECTED',reason='CORRECTNESS_OR_RESOURCE_GATE')
    else:
     if arm=='equivalent':custody.retain_asset('equivalent-parent',state['factor'].identity,'C',scope=oid)
     custody.retain_asset('successor',state['update'].identity,'C',scope=new_oid,parent_digest=state['factor'].identity)
     event('SUCCESSOR_RETAINED',identity=state['update'].identity,correctness=True,adoption='PROVISIONAL_SCOPED_FORECAST',investment_recovered='UNASSESSED')
   except CustodyError as e:
    event('CONSTRUCTION_DEFERRED',reason=str(e));state['update']=None;use_update=False
  if not use_update:
   rc,xc=action('C-FALLBACK' if any(z['id']=='C' for z in rows) else 'C','Changed-network service by competent alternative',changed,lambda:solve(changed,newA,method='cg' if arm=='direct_specialist' else 'factor'))
   if arm!='direct_specialist':state['factor']=state.get('new_factor') if rc['valid'] else None
  for j in range(1,regime['fresh']+1):
   td=with_load(changed,seed+2000+j)
   if regime['restart'] and j==6:
    def restore():
     state['previous_x']=None
     if state['update'] is not None:
      state['factor']=Factor.load(asset_files['parent']['path'],asset_files['parent'],oid);state['update']=Update.load(out/'successor.npz',asset_files['successor'],state['factor'],expected_oid=new_oid)
      return state['update'].solve(td['rhs']),{'method':'restore-portable-parent-and-update','parent_calls':1,'asset':state['update'].identity,'current_proof':'fresh edge checker'}
     if state['factor'] is not None:
      state['factor']=Factor.load(asset_files['native-current']['path'],asset_files['native-current'],new_oid)
      return state['factor'].solve(td['rhs']),{'method':'restore-portable-native-factor','parent_calls':0,'asset':state['factor'].identity,'current_proof':'fresh edge checker'}
     return solve(td,newA)
    rr,_=action('RESTORE','Recover after matched memory eviction',td,restore,'improvement',600);event('RESTORED',valid=rr['valid'],cpu_ms=rr['cpu_ms'],event_scope='matched simulated memory eviction with actual persisted-array reload; OS restart tested separately')
   factor=state['factor'] if arm!='direct_specialist' and state['update'] is None else None
   r,x=action(f'D{j:02}','Fresh changed-network load',td,lambda td=td,factor=factor:solve(td,newA,factor=factor,update=state['update']))
  shifted={**changed,'ground':[.2]*changed['n'],'rhs':with_load(changed,seed+3000)['rhs']};shiftA=matrix(shifted)
  event('REUSE_REFUSED',reason='grounding changed: both retained scopes invalid',previous_operator=new_oid,current_operator=operator_id(shifted))
  action('SHIFT','Changed dependency by direct specialist',shifted,lambda:solve(shifted,shiftA))
  unsupported={**shifted,'edges':[e[:] for e in shifted['edges']]};unsupported['edges'][0][2]=-1
  action('UNSUPPORTED','Refuse nonpositive conductance',unsupported,lambda:solve(unsupported,shiftA))
  custody.stop('FINITE_STREAM_COMPLETE');status=custody.status();startup_wall=client.startup_wall_ms
 np.savez_compressed(out/'solutions.npz',**vectors)
 (out/'tasks.json').write_text(json.dumps(tasks,separators=(',',':'))+'\n');(out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'events.json').write_text(json.dumps(events,indent=2)+'\n');(out/'custody_status.json').write_text(json.dumps(status,indent=2)+'\n')
 total_cpu=(time.process_time_ns()-begin_cpu)/1e6+cpu_children()-begin_children;total_wall=(time.perf_counter_ns()-begin_wall)/1e6
 useful=[r for r in rows if r['id'] not in ['P','RESTORE','UNSUPPORTED']]
 summary={'seed':seed,'regime':regime,'arm':arm,'source_hash':source_hash,'qualified':sum(any(r['qualified'] and (r['id']==mid or mid=='C' and r['id']=='C-FALLBACK') for r in useful) for mid in ['A']+[f'B{j:02}' for j in range(1,9)]+['C']+[f'D{j:02}' for j in range(1,regime['fresh']+1)]+['SHIFT']),'offered':11+regime['fresh'],'scope_refusal':next(r for r in rows if r['id']=='UNSUPPORTED')['checker']['reason'],'total_cpu_ms':total_cpu,'total_wall_ms':total_wall,'charged_action_cpu_ms':sum(r['cpu_ms'] for r in rows),'setup_custody_artifact_io_cpu_ms':total_cpu-sum(r['cpu_ms'] for r in rows),'external_control_cap_ms':2000,'control_budget_exceeded':total_cpu-sum(r['cpu_ms'] for r in rows)>2000,'setup_cpu_ms':setup_cpu,'workbench_startup_wall_ms':startup_wall,'released_service_quota_ms':status['earned_released_us']/1000,'successor_cpu_ms':status['accounts']['earned']['spent_us']/1000,'external_seed_improvement_ms':status['accounts']['improvement']['spent_us']/1000,'account_overrun':any(r.get('status')=='OVERRUN' for r in status['requests'].values()),'parent_calls_in_fresh_successors':sum(r['details'].get('parent_calls',0) for r in rows if r['id'].startswith('D') and r['valid']),'successor_constructed':state['update'] is not None,'asset_files':asset_files,'human_interventions_during_stream':0,'money':'UNMEASURED','full_research_investment_recovered':'UNRESOLVED'}
 summary['storage_bytes']=sum(p.stat().st_size for p in out.rglob('*') if p.is_file());(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

def run_stream(seed,regime,arm,out,source_hash='0'*64):
 Path(out).mkdir(parents=True,exist_ok=False)
 audit={};c=time.process_time_ns();w=time.perf_counter_ns();ch=cpu_children()
 try:return _run_stream(seed,regime,arm,out,source_hash,audit)
 except Exception as error:
  out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=audit.get('rows',[])
  (out/'rows.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'events.json').write_text(json.dumps(audit.get('events',[]),indent=2)+'\n')
  (out/'tasks.json').write_text(json.dumps(audit.get('tasks',{}),separators=(',',':'))+'\n');np.savez_compressed(out/'solutions.npz',**audit.get('vectors',{}))
  status=audit['custody'].status() if audit.get('custody') else {}
  (out/'custody_status.json').write_text(json.dumps(status,indent=2)+'\n')
  offered_ids=['A']+[f'B{j:02}' for j in range(1,9)]+['C']+[f'D{j:02}' for j in range(1,regime['fresh']+1)]+['SHIFT']
  qualified=sum(any(r['qualified'] and (r['id']==mid or mid=='C' and r['id']=='C-FALLBACK') for r in rows) for mid in offered_ids)
  total=(time.process_time_ns()-c)/1e6+cpu_children()-ch
  summary={'seed':seed,'regime':regime,'arm':arm,'source_hash':source_hash,'failure':type(error).__name__+': '+str(error),'qualified':qualified,'offered':len(offered_ids),'total_cpu_ms':total,'total_wall_ms':(time.perf_counter_ns()-w)/1e6,'charged_action_cpu_ms':sum(r['cpu_ms'] for r in rows),'setup_custody_artifact_io_cpu_ms':total-sum(r['cpu_ms'] for r in rows),'external_control_cap_ms':2000,'control_budget_exceeded':total-sum(r['cpu_ms'] for r in rows)>2000,'parent_calls_in_fresh_successors':sum(r['details'].get('parent_calls',0) for r in rows if r['id'].startswith('D') and r['valid']),'successor_constructed':False,'released_service_quota_ms':status.get('earned_released_us',0)/1000,'successor_cpu_ms':status.get('accounts',{}).get('earned',{}).get('spent_us',0)/1000,'scope_refusal':'UNATTEMPTED','storage_bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),'human_interventions_during_stream':0,'money':'UNMEASURED','full_research_investment_recovered':'UNRESOLVED'}
  (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--seed',type=int,default=27101);p.add_argument('--regime',type=int,default=0);p.add_argument('--arms',default=','.join(ARMS));a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False);s=[]
 for arm in a.arms.split(','):
  z=run_stream(a.seed,REGIMES[a.regime],arm,out/arm);s.append(z);print(json.dumps({k:z[k] for k in ['arm','qualified','offered','total_cpu_ms','successor_constructed','parent_calls_in_fresh_successors']}),flush=True)
 (out/'summaries.json').write_text(json.dumps(s,indent=2)+'\n')
if __name__=='__main__':main()
