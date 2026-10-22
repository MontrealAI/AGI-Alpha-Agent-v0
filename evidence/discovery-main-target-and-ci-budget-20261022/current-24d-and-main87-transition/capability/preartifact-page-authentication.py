from pathlib import Path
import ast,base64,hashlib,json,posixpath,re,subprocess
B=Path('/dev/shm/alpha-24d-main-target-cap-custody');ROOT=Path('/workspace/scratch/32717074a7f1/integration-alpha');LOCAL='f3193c343a54a2ae034261d91ead1bd9f96bb0b6'
sha=lambda v:hashlib.sha256(v).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
fresh=json.loads((B/'fresh41-part-0.json').read_text());raws={r['path']:git('show',LOCAL+':'+r['path']).decode('utf8') for r in fresh}
assert len(fresh)==41 and all(sha(raws[r['path']].encode())==r['sha256'] for r in fresh)
cat={'schema':'successor-capability-source/v1','sourceHash':'644258ac21cc938aff861d02ad728e8f3c9716f6ea78700acc35e4d7400eebf2','sources':{r['path']:r['sha256'] for r in fresh}}
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
page=page.replace('{{SOURCE_HASH}}',source_hash);assert '{{' not in page
served=json.dumps({'schema':'successor-capability-source/v1','sourceHash':source_hash,'sources':cat['sources']},sort_keys=True,indent=2)+'\n'

bindings={r['path']:r for r in json.loads((B/'generated-member-source-bindings.json').read_text())}
for path,value in [('docs/successor/capabilities/index.html',page.encode()),('docs/successor/capabilities/sources.json',served.encode())]:
 row=bindings[path];assert len(value)==row['size'] and hashlib.sha1(f'blob {len(value)}\0'.encode()+value).hexdigest()==row['sha'] and row['mode']=='100644'
report={'schema':'new24d-preartifact-independent-page-byte-authentication/v1','head':'24d58598f896106323f2c120487586bdf5104612','synthetic':'d3ba2c3a4a275d7f2c7619504b703f931b8c4507','tree':'ffa3d663519e713eca31a9840b8bf6816e53e12a','freshImmutableRuntimeSources':len(fresh),'sourceHash':source_hash,'moduleCount':len(names),'page':{'bytes':len(page.encode()),'sha256':sha(page.encode()),'gitBlob':bindings['docs/successor/capabilities/index.html']['sha'],'scriptCsp':csp['SCRIPT'],'styleCsp':csp['STYLE']},'sourcesJson':{'bytes':len(served.encode()),'sha256':sha(served.encode()),'gitBlob':bindings['docs/successor/capabilities/sources.json']['sha']},'freshCommitProofSha256':sha((B/'signed-commit-identities.json').read_bytes()),'freshRootTreeProofSha256':sha((B/'fresh-tree-authentication.json').read_bytes()),'execution':'Owned inert Python text construction/AST literal parsing only. No repository/artifact execution, browser, runtime/install or public writes.','artifactAuthentication':'Pending original39726232038a1; this report makes no hosted-success/accepted-main/release claim.'}
(B/'preartifact-page-byte-authentication.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
