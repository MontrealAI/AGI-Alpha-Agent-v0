// SPDX-License-Identifier: Apache-2.0
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {createWorkbench,example} from '../../../examples/successor-workbench/engine.mjs';
import {createAdapter} from './adapter.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const [oldPath,newPath,output,mode='full']=process.argv.slice(2);
if(!oldPath||!newPath||!output) throw Error('usage: node run_service.mjs old.json new.json output-directory [full|incremental]');
const start=performance.now(),cpu=process.cpuUsage();
const paths=['src/schema_inventory.mjs','src/incremental_index.mjs','src/adapter.mjs','src/run_service.mjs',
  '../../examples/successor-workbench/engine.mjs','../../docs/assets/successor/engine.mjs',
  '../../examples/build-successor/model.mjs','../../examples/build-successor/vendor/agijobs/compiler.mjs',
  '../../examples/build-successor/vendor/agijobs/templates.mjs'];
const manifest=[];
for(const path of paths) {const bytes=await readFile(resolve(root,path));manifest.push({path,bytes:bytes.length,
  sha256:createHash('sha256').update(bytes).digest('hex')});}
const sourceHash=createHash('sha256').update(JSON.stringify(manifest)).digest('hex');
const adapter=createAdapter(mode),runtime=createWorkbench([adapter]);
const spec={...example(),family:adapter.manifest.id,name:'API response assurance',owner:'research-fixture.agent.agi.eth',
  rights:{dataClass:'public',source:'Pinned public Moby API specification; source IDs retained in input manifest',license:'Apache-2.0'},
  inputs:{oldSpec:await readFile(oldPath,'utf8'),newSpec:await readFile(newPath,'utf8'),source:`${oldPath} -> ${newPath}`}};
const pack=await runtime.run(spec,{sourceHash});
const imported=await runtime.inspectPack(pack);
await mkdir(output,{recursive:true});
for(const artifact of pack.result.artifacts) await writeFile(resolve(output,artifact.name),artifact.content);
await writeFile(resolve(output,'workbench-pack.json'),JSON.stringify(pack)+'\n');
const used=process.cpuUsage(cpu);
const measurement={mode,wallSeconds:(performance.now()-start)/1000,cpuSeconds:(used.user+used.system)/1e6,
  maxRssKiB:process.resourceUsage().maxRSS,sourceHash,sourceManifest:manifest,summary:pack.result.summary,
  imported,scope:pack.evaluation,actualCompleteMonetaryCost:null,humanAttentionSeconds:null};
await writeFile(resolve(output,'measurement.json'),JSON.stringify(measurement,null,2)+'\n');
console.log(JSON.stringify({output,measurement}));
