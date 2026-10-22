from pathlib import Path
import ast,base64,hashlib,json,posixpath,re,subprocess
B=Path('/dev/shm/alpha-24d-main-target-cap-custody');ROOT=Path('/workspace/scratch/32717074a7f1/integration-alpha')
sha=lambda v:hashlib.sha256(v).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
rows=[]
for path in B.glob('fresh41-part-*.json'):rows.extend(json.loads(path.read_text()))
LOCAL='f3193c343a54a2ae034261d91ead1bd9f96bb0b6'
raws={r['path']:git('show',LOCAL+':'+r['path']).decode('utf8') for r in rows}
assert all(sha(raws[r['path']].encode())==r['sha256'] for r in rows)
more={}
for path in B.glob('fresh-extra-*.json'):
 row=json.loads(path.read_text());p=row['path']
 if p.startswith('alpha/'):
  value=git('show',LOCAL+':'+p.removeprefix('alpha/')).decode('utf8')
 else:
  value=subprocess.check_output(['git','show','0dd352fdd2b1af00bc8358e0ac7f96682fd6f796:'+row['sourcePath']],cwd='/dev/shm/fleet-return-public0dd').decode('utf8')
 assert sha(value.encode())==row['sha256'];more[p]=value
assert len(raws)==41
source=json.loads((B/'selected/source.json').read_text());checkout=json.loads((B/'selected/exact-checkout.json').read_text());cat=json.loads((B/'selected/discovery-continuation/served/sources.json').read_text());api=json.loads((B/'api-synthetic.json').read_text())
SYN='d3ba2c3a4a275d7f2c7619504b703f931b8c4507';TREE='ffa3d663519e713eca31a9840b8bf6816e53e12a';HEAD='24d58598f896106323f2c120487586bdf5104612';MAIN='5a5340a15698165bceb21e252f3bec58d7fd8298'
assert source['commit']==checkout['commit']==api['sha']==SYN and checkout['tree']==api['tree']['sha']==TREE
assert [p['sha'] for p in api['parents']]==[MAIN,HEAD] and source['trackedDiff']=='' and source['source']==checkout['source']==cat and checkout['files']==cat['sources']
assert json.loads((B/'fresh-tree-authentication.json').read_text())['rootTree']==TREE
rows=[]
for p,h in cat['sources'].items():
 v=raws[p].encode();assert sha(v)==h
 meta=git('ls-tree',LOCAL,'--',p).decode().split('\t',1)[0].split();assert hashlib.sha1(f'blob {len(v)}\0'.encode()+v).hexdigest()==meta[2]
 rows.append({'path':p,'bytes':len(v),'sha256':h,'gitBlob':meta[2],'mode':meta[0]})
source_hash=sha(json.dumps(cat['sources'],sort_keys=True,separators=(',',':')).encode());assert source_hash==cat['sourceHash']
# Read only the fixed literal entry list through AST; never execute generator source.
gen=ast.parse(raws['scripts/generate_successor_capability.py']);module_decl=next(n.value for n in ast.walk(gen) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='modules' for t in n.targets))
assert isinstance(module_decl,ast.Dict)
entries=[]
for key,val in zip(module_decl.keys,module_decl.values):
 assert isinstance(key,ast.Constant) and isinstance(key.value,str) and isinstance(val,ast.Call) and isinstance(val.func,ast.Name) and val.func.id=='visit' and len(val.args)==1
 path=val.args[0];assert isinstance(path,ast.BinOp) and isinstance(path.op,ast.Div) and isinstance(path.left,ast.Name) and path.left.id=='root' and isinstance(path.right,ast.Constant) and isinstance(path.right.value,str)
 entries.append((key.value,path.right.value))
names={};chunks=[]
def visit(path):
 path=posixpath.normpath(path);assert path in raws and not path.startswith('../')
 if path in names:return names[path]
 name=f'capability_module_{len(names)}';names[path]=name;s=raws[path]
 def replace(m):
  binding,location=m.groups();assert location.startswith('.');binding=binding.strip().removeprefix('* as ')
  if binding.startswith('{'):binding=re.sub(r'\b(\w+)\s+as\s+(\w+)\b',r'\1: \2',binding)
  return f'const {binding} = {visit(posixpath.join(posixpath.dirname(path),location))};'
 s=re.sub(r"^import\s+([^;]*?)\s+from\s+['\"]([^'\"]+)['\"];",replace,s,flags=re.M)
 exports=re.findall(r'^export\s+(?:async\s+)?(?:function\s*\*?|class|const)\s+(\w+)',s,flags=re.M);s=re.sub(r'^export\s+','',s,flags=re.M)
 chunks.append(f"const {name}=(()=>{{\n{s}\nreturn {{{','.join(exports)}}};\n}})();");return name
modules={k:visit(p) for k,p in entries};T=lambda p:raws['scripts/templates/successor-capability/'+p]
ds={'modelDigest':cat['sources']['examples/successor-capability/discovery-lab.mjs'],'evaluatorDigest':cat['sources']['examples/successor-capability/discovery-lab-checker.mjs'],'sourceDigest':source_hash}
script="\n(()=>{\n'use strict';\n"+'\n'.join(chunks)+'\n'+'\n'.join(f'const {k}={v};' for k,v in modules.items())
script+=f"\nconst SOURCE_HASH='{source_hash}';\n"+T('app.js')+'\n'+T('out-evolve-app.js')+'\nconst DISCOVERY_SOURCES='+json.dumps(ds,sort_keys=True)+';\n'+T('discovery-lab-app.js')+'\n'+T('discovery-lab-bridge.js')+'\n'
script+='\nconst DEPLOYMENT_INVENTORY='+json.dumps(json.loads(raws['docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.json']),sort_keys=True)+';\n'
rh=cat['sources']['examples/successor-capability/discovery-lab-real-task.mjs'];script+='\nconst REAL_TASK_SOURCES='+json.dumps({'adapterSourceDigest':rh,'checkerSourceDigest':rh},sort_keys=True)+';\n'+T('discovery-lab-continuation.js')+'\n})();\n'
style='\n'+T('style.css')+'\n'+T('discovery-lab.css')+'\n';page=T('index.html').replace('    <section id="out-evolve"',T('discovery-lab.html')+'\n    <section id="out-evolve"',1)
csp={}
for key,value in [('SCRIPT',script),('STYLE',style)]:
 encoded=base64.b64encode(hashlib.sha256(value.encode()).digest()).decode();csp[key]=encoded;page=page.replace('{{'+key+'_HASH}}','sha256-'+encoded).replace('{{'+key+'}}',value)
page=page.replace('{{SOURCE_HASH}}',source_hash);assert '{{' not in page and page.encode()==(B/'selected/discovery-continuation/served/index.html').read_bytes()
served=json.dumps({'schema':'successor-capability-source/v1','sourceHash':source_hash,'sources':cat['sources']},sort_keys=True,indent=2)+'\n';assert served.encode()==(B/'selected/discovery-continuation/served/sources.json').read_bytes()
proof=json.loads((B/'selected/discovery-continuation/fleet-native/native-proof.json').read_text());native_rows=[]
for path,h in (proof['sourceFiles']|{'alpha/'+k:v for k,v in proof['harnessSources'].items()}).items():
 raw=more[path] if path in more else raws[path.removeprefix('alpha/')];assert sha(raw.encode())==h,path
 if path in more:
  if path.startswith('alpha/'):meta=git('ls-tree',LOCAL,'--',path.removeprefix('alpha/')).decode().split('\t',1)[0].split()
  else:meta=subprocess.check_output(['git','ls-tree','0dd352fdd2b1af00bc8358e0ac7f96682fd6f796','--','discovery-lab/'+path.removeprefix('fleet/')],cwd='/dev/shm/fleet-return-public0dd',text=True).split('\t',1)[0].split()
  v=raw.encode();assert hashlib.sha1(f'blob {len(v)}\0'.encode()+v).hexdigest()==meta[2];native_rows.append({'path':path,'sha256':h,'gitBlob':meta[2],'bytes':len(v),'mode':meta[0]})
generated={r['path']:r for r in json.loads((B/'generated-member-source-bindings.json').read_text())}
for path,value in [('docs/successor/capabilities/index.html',page.encode()),('docs/successor/capabilities/sources.json',served.encode())]:
 meta=generated[path];assert len(value)==meta['size'] and hashlib.sha1(f'blob {len(value)}\0'.encode()+value).hexdigest()==meta['sha'] and meta['mode']=='100644'
report={'schema':'main-target-capability-source-page-authentication/v1','head':HEAD,'headTree':'ffa3d663519e713eca31a9840b8bf6816e53e12a','synthetic':SYN,'syntheticOrderedParents':[MAIN,HEAD],'syntheticTree':TREE,'currentMainAtSynthetic':MAIN,'localComponentByteReference':LOCAL,'localReferenceIsNotNewSourceIdentity':True,'runReportedPrBaseMetadata':json.loads((B/'api-capRun-final.json').read_text())['pull_requests'][0]['base']['sha'],'sourceHash':source_hash,'freshImmutablePublicRawReads':len(rows),'sources':rows,'additionalNativeFreshImmutableReads':native_rows,'allExtraFreshImmutableReads':[json.loads(p.read_text()) for p in sorted(B.glob('fresh-extra-*.json'))],'freshRootTreeProofSha256':sha((B/'fresh-tree-authentication.json').read_bytes()),'freshCommitIdentityProofSha256':sha((B/'signed-commit-identities.json').read_bytes()),'nativePublicFleetSource':proof['fleetSource'],'allSourceBlobSizeModeSha256Match':True,'generatorReconstruction':'Independent Python text bundling over immutable Git bytes proven identical to all53 fresh new-synthetic/component raw reads; AST literal module entries only; no repository or artifact execution','moduleCount':len(names),'actualArtifactPage':{'bytes':len(page.encode()),'sha256':sha(page.encode()),'reconstructionExact':True,'scriptCsp':csp['SCRIPT'],'styleCsp':csp['STYLE']},'actualArtifactSourcesJson':{'bytes':len(served.encode()),'sha256':sha(served.encode()),'reconstructionExact':True},'qualificationScope':'CURRENT_24D_PR_SYNTHETIC_ONLY_NONFINAL_NOT_ACCEPTED_MAIN','publicWrites':False}
(B/'source-page-authentication.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sources','additionalNativeFreshImmutableReads']},indent=2))
