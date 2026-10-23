import {readFile} from 'node:fs/promises';import {createHash} from 'node:crypto';import {resolve,posix} from 'node:path';
const root='/workspace/scratch/dbacb361adf2/discoverability',sha=b=>createHash('sha256').update(b).digest('hex');
const closure=JSON.parse(await readFile(resolve(root,'docs/research/discoverability/source-closure.json'),'utf8'));
const mismatches=[],actual={};
for(const [p,e] of Object.entries(closure.files)){const b=await readFile(resolve(root,p));actual[p]=sha(b);if(actual[p]!==e)mismatches.push(p);}
for(const p of ['examples/successor-discoverability/run.mjs','examples/successor-discoverability/reference.mjs'])actual[p]=sha(await readFile(resolve(root,p)));
const ordered=Object.fromEntries(Object.entries(actual).sort(([a],[b])=>a.localeCompare(b,'en')));
const seen=new Set(),builtins=new Set(),rx=/^import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|[A-Za-z_$][\w$]*)\s+from\s+)?['"]([^'"]+)['"]\s*;/gm;
async function visit(p){if(seen.has(p))return;seen.add(p);const s=await readFile(resolve(root,p),'utf8');for(const m of s.matchAll(rx)){if(m[1].startsWith('node:')){builtins.add(m[1]);continue;}if(!m[1].startsWith('.'))throw Error('Nonlocal import '+m[1]);await visit(posix.normalize(posix.join(posix.dirname(p),m[1])));}}
await visit('examples/successor-discoverability/run.mjs');await visit('examples/successor-discoverability/browser.mjs');
const missing=[...seen].filter(p=>!Object.hasOwn(actual,p));
const extra=Object.keys(actual).filter(p=>!seen.has(p));
console.log(JSON.stringify({schema:'discoverability-execution-source-review/v1',node:process.version,runSha256:actual['examples/successor-discoverability/run.mjs'],referenceSha256:actual['examples/successor-discoverability/reference.mjs'],browserSha256:actual['examples/successor-discoverability/browser.mjs'],closureMemberCount:Object.keys(closure.files).length,executionSourceMemberCount:Object.keys(actual).length,memberByteMismatches:mismatches,browserClosureRootMatches:sha(JSON.stringify(closure.files))===closure.sourceHash,executionSourceHash:sha(JSON.stringify(ordered)),currentlyReachableModulesMissingFromExecutionManifest:missing,additionalManifestModules:extra,externalRuntimeBuiltins:[...builtins].sort(),scope:'Read-only independent byte and current static import-graph inspection; no 333-mission rerun, no process attestation or source authentication.'},null,2));
if(mismatches.length||missing.length)process.exitCode=1;