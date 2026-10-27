import json, math, sys

TOLERANCE=1e-9
MIN_GROUND=0.1
MAX_N=65536
MAX_EDGES=1000000

def finite_number(v):
 return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def inspect(task):
 if not isinstance(task,dict):return 'TASK_SHAPE'
 n=task.get('n')
 if not isinstance(n,int) or isinstance(n,bool) or not 1<=n<=MAX_N:return 'NODE_COUNT_SCOPE'
 if not isinstance(task.get('ground'),list) or len(task['ground'])!=n:return 'GROUND_SHAPE'
 if not isinstance(task.get('rhs'),list) or len(task['rhs'])!=n:return 'RHS_SHAPE'
 if any(not finite_number(g) or g<MIN_GROUND for g in task['ground']):return 'GROUND_SCOPE'
 if any(not finite_number(b) for b in task['rhs']):return 'RHS_NONFINITE'
 edges=task.get('edges')
 if not isinstance(edges,list) or len(edges)>MAX_EDGES:return 'EDGE_LIST_SCOPE'
 for e in edges:
  if not isinstance(e,list) or len(e)!=3:return 'EDGE_SHAPE'
  u,v,w=e
  if any(not isinstance(i,int) or isinstance(i,bool) or i<0 or i>=n for i in [u,v]) or u==v:return 'EDGE_ENDPOINT_SCOPE'
  if not finite_number(w) or w<=0:return 'CONDUCTANCE_SCOPE'
 return None

def check(task,solution):
 reason=inspect(task)
 empty={'valid':False,'scope_valid':reason is None,'max_abs_residual':None,'relative_residual':None,'energy_error':None,'reason':reason,'tolerance':TOLERANCE,'balance_nodes':0,'balance_edges':0}
 if reason:return empty
 n=task['n']
 if not isinstance(solution,list) or len(solution)!=n:return {**empty,'reason':'SOLUTION_SHAPE'}
 if any(not finite_number(v) for v in solution):return {**empty,'reason':'SOLUTION_NONFINITE'}
 try:
  terms=[[task['ground'][i]*solution[i],-task['rhs'][i]] for i in range(n)]
  energy=[task['ground'][i]*solution[i]*solution[i] for i in range(n)]
  for u,v,w in task['edges']:
   delta=solution[u]-solution[v];flow=w*delta
   terms[u].append(flow);terms[v].append(-flow);energy.append(w*delta*delta)
  residuals=[math.fsum(t) for t in terms]
  e=math.fsum(energy);work=math.fsum(task['rhs'][i]*solution[i] for i in range(n))
  maximum=max(map(abs,residuals));relative=maximum/max(1.0,max(map(abs,task['rhs'])))
  energy_error=abs(e-work)/max(1.0,abs(e),abs(work))
  values=[maximum,relative,e,work,energy_error]
  if not all(math.isfinite(v) for v in values):return {**empty,'reason':'ARITHMETIC_NONFINITE'}
 except (OverflowError,ValueError):return {**empty,'reason':'ARITHMETIC_NONFINITE'}
 valid=relative<=TOLERANCE and energy_error<=TOLERANCE
 return {'valid':valid,'scope_valid':True,'max_abs_residual':maximum,'relative_residual':relative,'energy_error':energy_error,'reason':'VERIFIED' if valid else 'RESIDUAL_OR_ENERGY_FAILURE','tolerance':TOLERANCE,'balance_nodes':n,'balance_edges':len(task['edges'])}

def main():
 for line in sys.stdin:
  if not line.strip():continue
  try:
   row=json.loads(line);out=check(row.get('task'),row.get('solution'))
  except (json.JSONDecodeError,AttributeError,TypeError):out={'valid':False,'scope_valid':False,'reason':'REQUEST_SHAPE'}
  print(json.dumps(out,allow_nan=False,separators=(',',':')),flush=True)

if __name__=='__main__':main()
