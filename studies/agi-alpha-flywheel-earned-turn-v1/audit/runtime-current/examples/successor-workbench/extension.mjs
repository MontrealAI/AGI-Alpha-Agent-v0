// SPDX-License-Identifier: Apache-2.0
// Installed developer code, not an imported mission or model-generated program.
import { createWorkbench, example } from './engine.mjs';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';

const adapter = {
  manifest: {id:'word-inventory',version:1,en:'Count declared words',fr:'Compter les mots déclarés',
    scope:'Exact case-sensitive counts in a bounded supplied word list.',artifact:'inventory.json'},
  validate(input) {
    if(Object.keys(input).join()!=='words'||!Array.isArray(input.words)||input.words.length>1000||
       input.words.some(word=>typeof word!=='string'||!word||word.length>80))throw Error('WORD_LIST');
  },
  async execute(input,checkpoint) {
    const counts=new Map();
    for(const word of input.words){await checkpoint('counting');counts.set(word,(counts.get(word)||0)+1);}
    const inventory=[...counts].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0).map(([word,count])=>({word,count}));
    return {decision:'REVIEW_REQUIRED',summary:{words:input.words.length,distinct:inventory.length},
      evidence:{inventory,reconciled:inventory.reduce((sum,item)=>sum+item.count,0)===input.words.length},
      artifacts:[{name:'inventory.json',type:'application/json',content:JSON.stringify(inventory,null,2)+'\n'}],
      limits:['Public local execution; no independent verification, market advantage or operating authority.']};
  },
};
const runtime=createWorkbench([adapter]);
const spec={...example(),family:adapter.manifest.id,inputs:{words:['alpha','omega','alpha']}};
const sourceHash=createHash('sha256').update(await readFile(new URL(import.meta.url)))
  .update(await readFile(new URL('./engine.mjs',import.meta.url)))
  .update(await readFile(new URL('../../alpha_factory_v1/core/runtime/successor/workbench_sources.json',import.meta.url))).digest('hex');
const pack=await runtime.run(spec,{sourceHash});
await runtime.inspectPack(pack);
console.log(JSON.stringify(pack,null,2));
