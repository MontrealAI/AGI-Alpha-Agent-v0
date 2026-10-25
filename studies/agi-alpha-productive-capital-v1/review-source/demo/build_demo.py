# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import base64,hashlib,json,re,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def safe(value):
 return json.dumps(value,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
def build():
 modules={}
 pattern=re.compile(r"(^import\s+[\s\S]*?\s+from\s+)(['\"])([^'\"]+)\2(\s*;)",re.M)
 def visit(path):
  path=path.resolve();relative=path.relative_to(ROOT).as_posix();name='pcap:/'+relative
  if name in modules:return name
  modules[name]=None
  source=path.read_text()
  def replace(m):
   dep=m.group(3)
   if not dep.startswith('.'):raise ValueError('Unexpected external import '+dep)
   target=visit(path.parent/dep)
   return m.group(1)+m.group(2)+target+m.group(2)+m.group(4)
  source=pattern.sub(replace,source)
  modules[name]='data:text/javascript;base64,'+base64.b64encode(source.encode()).decode()
  return name
 visit(ROOT/'companion_v1_1/capability.mjs')
 example=json.loads((ROOT/'demo/example.json').read_text())
 recorded=json.loads((ROOT/'demo/recorded.json').read_text())
 freeze=json.loads((ROOT/'protocol/experiment-v11-FREEZE.json').read_text())
 source=freeze.get('manifest_sha256') or freeze.get('sha256') or hashlib.sha256((ROOT/'protocol/experiment-v11-FREEZE.json').read_bytes()).hexdigest()
 text=(ROOT/'demo/template.html').read_text().replace('__IMPORTMAP__',safe({'imports':modules})).replace('__EXAMPLE__',safe(example)).replace('__RESULTS__',safe(recorded)).replace('__FROZEN_HASH__',source)
 notices='\n\n'.join((ROOT/'LICENSES'/n).read_text() for n in ['Apache-2.0.txt','AGIJobsv0-MIT.txt'])
 text=text.replace('</body>','<template id="third-party-license-notices"><pre>'+html.escape(notices)+'</pre></template></body>')
 out=ROOT/'deliverables/AGI_ALPHA_Productive_Capital_Demo.html';out.parent.mkdir(exist_ok=True);out.write_text(text)
 (ROOT/'demo/BUILD.json').write_text(json.dumps({'entry':'companion_v1_1/capability.mjs','modules':len(modules),'source_binding':source,'output':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size},indent=2)+'\n')
 print(json.dumps({'output':str(out),'modules':len(modules),'bytes':out.stat().st_size}))
if __name__=='__main__':build()
