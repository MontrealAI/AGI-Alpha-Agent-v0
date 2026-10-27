// SPDX-License-Identifier: Apache-2.0
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,dirname,basename} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createWorkbench,example} from '../../../upstream/alpha/examples/successor-workbench/engine.mjs';
import {parseSnippet,runComparison} from '../../../upstream/alpha/docs/assets/transformational-intelligence/source-understanding.mjs';

const filePath=resolve(process.argv[2]);
const input=JSON.parse(await readFile(filePath,'utf8'));
const folder=dirname(filePath);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
for(const item of input.files){
  if(item.name!==basename(item.name))throw Error('PATH');
  const bytes=await readFile(resolve(folder,item.name));
  if(sha(bytes)!==item.sha256||bytes.length!==item.bytes)throw Error('ARTIFACT_BINDING');
}
const adapter={
  manifest:{id:'human-market-csv',version:input.generation+1,en:'Clean an export',fr:'Nettoyer un export',
    scope:'Verify and package a source-bound CSV cleanup with exact record dispositions.',artifact:'delivery-manifest.json'},
  validate(value){
    if(value.schema!=='csv-delivery/v1'||!Array.isArray(value.files)||value.files.length<7)throw Error('DELIVERY_SCHEMA');
    if(value.counts.input!==value.counts.clean+value.counts.quarantine+value.counts.duplicates+value.counts.superseded)throw Error('ROW_ACCOUNTING');
    if(value.status!=='COMPLETED')throw Error('INCOMPLETE_DELIVERY');
  },
  async execute(value,checkpoint){
    await checkpoint('verify-file-identities');
    const text=[`The input contains ${value.counts.input} data records.`,
      `Every record has one disposition: ${value.counts.clean} retained, ${value.counts.quarantine} quarantined, ${value.counts.duplicates} exact copies and ${value.counts.superseded} superseded versions.`,
      'The supplied rules determine transformations; missing values and ambiguous conflicts are never guessed.'].join('\n');
    const ti=runComparison(parseSnippet(text,{title:'CSV delivery evidence'}),3);
    return {decision:'LOCAL_DELIVERY_COMPLETE',summary:value.counts,
      evidence:{source:value.source,files:value.files,tiStructuralSummary:ti,professionalAcceptance:'NOT_OBSERVED'},
      artifacts:[{name:'delivery-manifest.json',type:'application/json',content:JSON.stringify(value,null,2)+'\n'},
        {name:'quality-summary.md',type:'text/markdown',content:text+'\n'}],
      limits:['This is a two-stage local workflow: deterministic Python analysis then unchanged portable Workbench verification.',
        'Independent factual acceptance is recorded separately; local completion is not a sale or live authority.',
        'Full CSV artifacts are supplied alongside the bounded pack and verified by their exact hashes.']};
  }
};
const runtime=createWorkbench([adapter]);
const spec={...example(),family:adapter.manifest.id,name:'CSV cleanup',owner:'human-market-research',
  rights:{dataClass:input.data_class,source:input.source.sha256,license:input.data_class==='synthetic'?'CC0-1.0':'See source manifest'},
  reviewMinutes:15,inputs:input};
const pack=await runtime.run(spec,{sourceHash:input.source_code_sha256});
await runtime.inspectPack(pack);
await writeFile(resolve(folder,'workbench-pack.json'),JSON.stringify(pack,null,2)+'\n');
await writeFile(resolve(folder,'ti-summary.json'),JSON.stringify(pack.result.evidence.tiStructuralSummary,null,2)+'\n');
console.log(JSON.stringify({status:'PACKAGED',mission:pack.frozen.missionDigest,admission:pack.evaluation.admission,
  authority:pack.evaluation.authority,settlement:pack.evaluation.settlement,jobCompilation:pack.compilation.schema}));
