// SPDX-License-Identifier: Apache-2.0
// Deterministic dependency-free packaging of the bounded static ESM closure.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, posix } from 'node:path';
import { createHash } from 'node:crypto';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const entry='examples/successor-discoverability/browser.mjs';
const files={};
// This repository closure uses named, namespace or default static imports.
// Fail closed on a dependency outside the repository; no packages are fetched.
const imports=/^(import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|[A-Za-z_$][\w$]*)\s+from\s+)?['"])([^'"]+)(['"]\s*;)/gm;
async function visit(path) {
  if(Object.hasOwn(files,path))return;
  const source=await readFile(resolve(root,path),'utf8');files[path]=source;
  for(const match of source.matchAll(imports)) {
    const spec=match[2];
    if(!spec.startsWith('.'))throw Error('Only repository-local dependencies may be bundled: '+spec);
    const child=posix.normalize(posix.join(posix.dirname(path),spec));
    if(child.startsWith('../'))throw Error('Module escapes repository root');
    await visit(child);
  }
}
await visit(entry);
const sourceManifest=Object.fromEntries(Object.keys(files).sort().map(path=>[path,createHash('sha256').update(files[path]).digest('hex')]));
const sourceHash=createHash('sha256').update(JSON.stringify(sourceManifest)).digest('hex');
const input=JSON.stringify({entry,files,sourceHash,sourceManifest}).replaceAll('<','\\u003c');
const loader='<script type="module">\n'+
'const bundle='+input+';\n'+
'const urls=new Map();\n'+
"function normalize(path){const a=[];for(const p of path.split('/')){if(p==='..')a.pop();else if(p!=='.'&&p)a.push(p);}return a.join('/');}\n"+
'function url(path){\n'+
'  if(urls.has(path))return urls.get(path);\n'+
"  if(!Object.hasOwn(bundle.files,path))throw Error('Unbundled dependency: '+path);\n"+
"  const parent=path.slice(0,path.lastIndexOf('/')+1);\n"+
'  const source=bundle.files[path].replace(new RegExp('+JSON.stringify(imports.source)+',"gm"),\n'+
'    (all,before,spec,after)=>before+url(normalize(parent+spec))+after);\n'+
"  const value=URL.createObjectURL(new Blob([source],{type:'text/javascript'}));urls.set(path,value);return value;\n"+
'}\n'+
'try{const app=await import(url(bundle.entry));await app.boot({sourceHash:bundle.sourceHash,sourceManifest:bundle.sourceManifest});}\n'+
"catch(error){document.getElementById('status').textContent='Unable to initialize: '+error.message;console.error(error);}\n"+
'</script>';
const shell=await readFile(resolve(root,'examples/successor-discoverability/experience-shell.html'),'utf8');
if(!shell.includes('<!--BUNDLE-->'))throw Error('Missing bundle insertion point');
const target=resolve(process.argv[2]||resolve(root,'docs/research/discoverability/index.html'));
if(!target.endsWith('.html'))throw Error('Output must be an HTML file');
await mkdir(dirname(target),{recursive:true});
const html=shell.replace('<!--BUNDLE-->',loader);
await writeFile(target,html);
await writeFile(resolve(dirname(target),'source-closure.json'),JSON.stringify({schema:'discoverability-source-closure/v1',runId:'discoverability-20261022-v1',sourceHash,files:sourceManifest},null,2)+'\n');
console.log(JSON.stringify({output:target,sourceHash,modules:Object.keys(files).length,bytes:Buffer.byteLength(html)}));
