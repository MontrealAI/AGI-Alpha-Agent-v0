from pathlib import Path
import json,hashlib,datetime
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'source-identities.json').read_text()); byid={r['id']:r for r in rows}
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def src(key):
 r=byid[key];return {k:r[k] for k in ['repository','commit','path','sha256']}|{'text':(ROOT/r['file']).read_text()}
def provider(ref,paths): return [ref+'--'+p.replace('/','__') for p in paths]
httpxpaths=['httpx/__init__.py','httpx/_client.py','httpx/_urls.py','httpx/_models.py']
scipypaths=['scipy/linalg/_decomp.py','scipy/linalg/__init__.py','scipy/sparse/linalg/_eigen/arpack/arpack.py','scipy/sparse/linalg/__init__.py','scipy/sparse/linalg/_eigen/__init__.py','scipy/sparse/linalg/_eigen/arpack/__init__.py']
integratepaths=['scipy/integrate/_quadrature.py','scipy/integrate/__init__.py']
specs=[
 ('T01','alpha','httpx','0.27.2','0.28.1','httpx-before','httpx-after',httpxpaths,['evaluate_agent'],'Assess the source-level HTTPX call contract used by the actual Alpha transfer evaluator; do not execute the evaluator or contact a provider.'),
 ('T02','openai','httpx','0.27.2','0.28.1','httpx-before','httpx-after',httpxpaths,['_DefaultHttpxClient.__init__','_DefaultAsyncHttpxClient.__init__'],'Assess the default synchronous and asynchronous HTTP client initialization bridge in this exact OpenAI SDK source; do not instantiate a client.'),
 ('T03','sklearn-old','scipy','1.9.3','1.10.1','scipy-19','scipy-110',scipypaths,['KernelPCA._fit_transform'],'Assess the exact upstream SciPy argument contracts used for this KernelPCA fit transformation; separate source binding from numerical correctness.'),
 ('T04','sklearn-old','scipy','1.10.1','1.14.1','scipy-110','scipy-after',scipypaths,['KernelPCA._fit_transform'],'Assess the distinct later SciPy transition for the same unchanged KernelPCA component; all relevant calls form one maintenance question.'),
 ('T05','sklearn-new','scipy','1.10.1','1.14.1','scipy-110','scipy-after',scipypaths,['null_space'],'Assess the SciPy calls used by the exact locally-linear-embedding null-space component, including both declared solver branches.'),
 ('T06','statsmodels','scipy','1.10.1','1.14.1','scipy-110','scipy-after',integratepaths,['get_covder2'],'Assess the integration dependency used to compute this spline derivative covariance, including the conditional import alias and source-level limitations.')]
selection=[]
for ident,consumer,pkg,bv,av,b,a,paths,scope,purpose in specs:
 bkeys,akeys=provider(b,paths),provider(a,paths)
 source_keys={k:('b'+str(i)) for i,k in enumerate(bkeys)}|{k:('a'+str(i)) for i,k in enumerate(akeys)}
 sources={'consumer':src('consumer-'+consumer)}|{source_keys[k]:src(k) for k in bkeys+akeys}
 lic=['alpha--LICENSE' if consumer=='alpha' else consumer+'--'+('COPYING' if consumer.startswith('sklearn') else 'LICENSE.txt' if consumer=='statsmodels' else 'LICENSE'),b+'--'+('LICENSE.md' if pkg=='httpx' else 'LICENSE.txt'),a+'--'+('LICENSE.md' if pkg=='httpx' else 'LICENSE.txt')]
 licenses=[{k:byid[n][k] for k in ['repository','commit','path','sha256','bytes','file']} for n in lic]
 task={'schema':'alpha-transfer-raw-task/v1','id':ident,'title':f'{pkg} {bv} to {av}: {consumer} source-contract assessment','purpose':purpose,'dependency':{'package':pkg,'importRoots':[pkg],'before':{'version':bv},'after':{'version':av}},'consumer':{'source':'consumer','scopeSymbols':scope},'sources':sources,'providerSides':{'before':[source_keys[k] for k in bkeys],'after':[source_keys[k] for k in akeys]},'licenseRecords':licenses}
 path=ROOT/'tasks'/f'{ident}.json';path.write_text(json.dumps(task,indent=2,ensure_ascii=False)+'\n')
 selection.append({'id':ident,'path':'tasks/'+path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'canonical_input_sha256':hashlib.sha256(canonical(task)).hexdigest(),'bytes':path.stat().st_size,'source_component':consumer+':'+','.join(scope),'family':pkg,'source_payload_bytes':sum(len(v['text'].encode()) for v in sources.values())})
(ROOT/'task-selection.json').write_text(json.dumps({'schema':'alpha-transfer-task-selection/v1','prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tasks':selection,'units':'Six unique component/transition questions, five unique source components, two dependency families. Multiple calls and two target methods in one component packet are not separate jobs. T03/T04 share a consumer and are clustered.','source_selection':'Purposive structural coverage of real historical maintenance transitions; not a random demand sample or estimate of future defect prevalence. Historical/pretraining exposure remains possible. Selection/oracle owner alone inspected sources before candidate freeze. No candidate sees primary inputs or labels before its source/prompt freeze.'},indent=2)+'\n')
print(json.dumps([{'id':r['id'],'bytes':r['bytes'],'source_payload_bytes':r['source_payload_bytes']} for r in selection],indent=2))
