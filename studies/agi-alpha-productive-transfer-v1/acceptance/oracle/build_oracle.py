from pathlib import Path
import ast,datetime,hashlib,inspect,json
ROOT=Path(__file__).resolve().parents[1]
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def select(tree,symbol):
 body=tree.body
 for name in symbol.split('.'):
  choices=[n for n in body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
  if len(choices)!=1: raise ValueError((symbol,len(choices)))
  node=choices[0];body=node.body
 return node
def signature(node):
 a=node.args; allpos=a.posonlyargs+a.args; required=len(allpos)-len(a.defaults);p=[]
 for i,n in enumerate(allpos):p.append(inspect.Parameter(n.arg,inspect.Parameter.POSITIONAL_ONLY if i<len(a.posonlyargs) else inspect.Parameter.POSITIONAL_OR_KEYWORD,default=inspect.Parameter.empty if i<required else None))
 if a.vararg:p.append(inspect.Parameter(a.vararg.arg,inspect.Parameter.VAR_POSITIONAL))
 for n,d in zip(a.kwonlyargs,a.kw_defaults):p.append(inspect.Parameter(n.arg,inspect.Parameter.KEYWORD_ONLY,default=inspect.Parameter.empty if d is None else None))
 if a.kwarg:p.append(inspect.Parameter(a.kwarg.arg,inspect.Parameter.VAR_KEYWORD))
 return inspect.Signature(p)
manual={
 'T01':[(43,12,'httpx.URL','httpx/_urls.py','URL.__init__','UNSUPPORTED_RECEIVER'),(45,9,'httpx.Client','httpx/_client.py','Client.__init__','UNSUPPORTED_RECEIVER'),(53,17,'client.stream','httpx/_client.py','Client.stream','UNSUPPORTED_RECEIVER_AND_DECORATOR'),(64,16,'response.raise_for_status','httpx/_models.py','Response.raise_for_status','UNSUPPORTED_RECEIVER'),(65,19,'response.headers.get','httpx/_models.py','Headers.get','UNSUPPORTED_RECEIVER'),(68,29,'response.iter_raw','httpx/_models.py','Response.iter_raw','UNSUPPORTED_RECEIVER')],
 'T02':[(755,8,'super().__init__','httpx/_client.py','Client.__init__','EXPANDED_ARGUMENTS'),(1335,8,'super().__init__','httpx/_client.py','AsyncClient.__init__','EXPANDED_ARGUMENTS')],
 'T03':[(330,52,'linalg.eigh','scipy/linalg/_decomp.py','eigh',None),(335,52,'eigsh','scipy/sparse/linalg/_eigen/arpack/arpack.py','eigsh',None)],
 'T04':[(330,52,'linalg.eigh','scipy/linalg/_decomp.py','eigh',None),(335,52,'eigsh','scipy/sparse/linalg/_eigen/arpack/arpack.py','eigsh',None)],
 'T05':[(176,42,'eigsh','scipy/sparse/linalg/_eigen/arpack/arpack.py','eigsh',None),(192,38,'eigh','scipy/linalg/_decomp.py','eigh',None)],
 'T06':[(259,12,'simpson','scipy/integrate/_quadrature.py','simpson',None)]}
outputs=[]
for tid,entries in manual.items():
 task=json.loads((ROOT/'tasks'/f'{tid}.json').read_text());consumer=task['sources']['consumer'];tree=ast.parse(consumer['text']);scopes=[select(tree,s) for s in task['consumer']['scopeSymbols']];calls=[n for scope in scopes for n in ast.walk(scope) if isinstance(n,ast.Call)];rows=[]
 for line,col,callee,path,symbol,unsupported in entries:
  call=next(n for n in calls if n.lineno==line and n.col_offset==col and ast.unparse(n.func)==callee)
  r={'line':line,'column':col,'callee':callee,'consumer_sha256':consumer['sha256'],'snippet_sha256':hashlib.sha256(ast.get_source_segment(consumer['text'],call).encode()).hexdigest(),'unsupported_reason':unsupported,'targets':{},'independent_argument_acceptance':{}}
  for side in ['before','after']:
   sid=next(s for s in task['providerSides'][side] if task['sources'][s]['path']==path);source=task['sources'][sid];node=select(ast.parse(source['text']),symbol)
   r['targets'][side]={'source':sid,'symbol':symbol,'sha256':source['sha256'],'declaration_line':node.lineno,'declaration_end_line':node.end_lineno,'decorators':[ast.unparse(x) for x in node.decorator_list],'signature':str(signature(node))}
   if unsupported:r['independent_argument_acceptance'][side]=None
   else:
    if node.decorator_list:raise ValueError('unexpected outside-scope decorator')
    if any(isinstance(n,ast.Starred) for n in call.args) or any(n.arg is None for n in call.keywords):raise ValueError('unexpected expanded argument')
    try:signature(node).bind(*([object()]*len(call.args)),**{n.arg:object() for n in call.keywords});ok=True;err=None
    except TypeError as e:ok=False;err=str(e)
    r['independent_argument_acceptance'][side]=ok
    if err:r.setdefault('argument_binding_error',{})[side]=err
  b,a=(r['independent_argument_acceptance'][s] for s in ['before','after'])
  r['expected_core_scope_outcome']='UNRESOLVED' if unsupported else 'BINDING_CONFLICT' if b is True and a is False else 'BINDING_PRESERVED' if b is True and a is True else 'UNRESOLVED'
  r['mapping_scope']='Correct nominal source target under ordinary package imports, no monkeypatching, and relevant branch execution. Original core may keep mappingVerified false for reexports/local imports. This is not proof of successful argument evaluation, full behavior, safety or deployment.'
  rows.append(r)
 selected={(r['line'],r['column'],r['callee']) for r in rows};excluded=[{'line':c.lineno,'column':c.col_offset,'callee':ast.unparse(c.func),'reason':'Not a call into the declared dependency in this scoped source assessment: builtin, own consumer helper, other dependency, or operation on a plain returned value. The super() constructor of a receiver is part of the outer initializer call and is not a separate dependency invocation.'} for c in calls if (c.lineno,c.col_offset,ast.unparse(c.func)) not in selected]
 out={'schema':'alpha-transfer-independent-oracle/v1','id':tid,'canonical_input_sha256':hashlib.sha256(canonical(task)).hexdigest(),'oracle_owner':'separate same-session production-audit agent; not institutionally independent replication','basis':'Manual source inventory and attribution, independently reconstructed Python inspect.Signature contract; no candidate extractor, product creator or target package execution. Original consumer bytes unchanged.','calls':rows,'nondependency_scope_calls':excluded,'complete_call_count':len(rows),'accepted_truthful_assessment':'Exact complete relevant-call inventory, no spurious target relationships, source-bound conditional conclusions, and explicit justified abstention where core cannot decide. Decisive coverage reported separately; complete unresolved packet is not compatibility acceptance.'}
 (ROOT/'oracle'/f'{tid}.json').write_text(json.dumps(out,indent=2)+'\n');outputs.append({'id':tid,'calls':len(rows),'status_counts':{s:sum(r['expected_core_scope_outcome']==s for r in rows) for s in ['BINDING_PRESERVED','BINDING_CONFLICT','UNRESOLVED']}})
(ROOT/'oracle/summary.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tasks':outputs},indent=2)+'\n')
print('six independent oracle records built; labels retained only in sealed-corpus/oracle')
