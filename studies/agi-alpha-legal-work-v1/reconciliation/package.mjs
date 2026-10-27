// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createWorkbench,example} from '../heritage/alpha/examples/successor-workbench/engine.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const hash=value=>createHash('sha256').update(value).digest('hex');
const provenance=JSON.parse(readFileSync(path.join(ROOT,'heritage/alpha-source-manifest.json'),'utf8'));
const binding=createHash('sha256');
for(const file of provenance.files){const bytes=readFileSync(path.join(ROOT,'heritage/alpha',file.path));if(hash(bytes)!==file.sha256)throw Error('UPSTREAM_DRIFT');binding.update(bytes);}
for(const file of ['reconciliation/package.mjs','reconciliation/reconcile.py'])binding.update(readFileSync(path.join(ROOT,file)));
const sourceHash=binding.digest('hex');
export function verify(packet){
  if(packet.schema!=='legal-reconciliation/v1'||packet.decision!=='TEXT_RECONCILIATION_ONLY'||packet.professional_acceptance!=='unknown'||packet.legal_or_playbook_conclusions.length||packet.proposed_revisions.length)throw Error('SCOPE');
  if(JSON.stringify(Object.keys(packet.documents).sort())!==JSON.stringify(Object.keys(packet.source_hashes).sort()))throw Error('HASH_SET');
  for(const [key,text] of Object.entries(packet.documents))if(hash(text)!==packet.source_hashes[key])throw Error('HASH');
  const ends={original:0,revised:0},restored={original:'',revised:''};
  for(const operation of packet.operations){
    if(!['equal','replace','delete','insert'].includes(operation.kind))throw Error('KIND');
    for(const key of ['original','revised']){const s=operation[key+'_span'],chars=Array.from(packet.documents[key]);
      if(s.document!==key||!Number.isSafeInteger(s.start)||!Number.isSafeInteger(s.end)||s.start!==ends[key]||s.end<s.start||s.end>chars.length||chars.slice(s.start,s.end).join('')!==s.quote)throw Error('SPAN');
      restored[key]+=s.quote;ends[key]=s.end;
    }
    const before=operation.original_span.quote,after=operation.revised_span.quote;
    if(operation.kind==='equal'&&(before!==after||!before))throw Error('FALSE_EQUAL');
    if(operation.kind==='replace'&&(!before||!after||before===after))throw Error('FALSE_REPLACE');
    if(operation.kind==='insert'&&(before||!after))throw Error('FALSE_INSERT');
    if(operation.kind==='delete'&&(after||!before))throw Error('FALSE_DELETE');
  }
  if(restored.original!==packet.documents.original||restored.revised!==packet.documents.revised)throw Error('RECONSTRUCTION');
  const amendments=Object.keys(packet.documents).filter(k=>k.startsWith('amendment:')).sort();
  if(amendments.join('|')!==packet.amendments.map(a=>a.document).sort().join('|'))throw Error('AMENDMENT_SET');
  for(const amendment of packet.amendments)if(amendment.quote!==packet.documents[amendment.document]||amendment.effect!=='NOT_INTERPRETED')throw Error('AMENDMENT_CHANGED');
}
const adapter={manifest:{id:'legal-text-reconciliation',version:1,en:'Reconcile exact contract text',fr:'Rapprocher les textes exacts',scope:'Source-bound plain-text change-control only; legal meaning and professional acceptance unassessed.',artifact:'reconciliation.json'},
  validate:verify,async execute(packet,checkpoint){await checkpoint('checking-source-conservation');verify(packet);return {decision:'TEXT_RECONCILIATION_ONLY',summary:{caseId:packet.case_id,operations:packet.operations.length,amendments:packet.amendments.length},evidence:{sourceHashes:packet.source_hashes,professionalAcceptance:'unknown'},artifacts:[{name:'reconciliation.json',type:'application/json',content:JSON.stringify(packet,null,2)+'\n'}],limits:packet.limits};}};
const runtime=createWorkbench([adapter]);
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const entries=JSON.parse(readFileSync(process.argv[2],'utf8')),receipts=[];
  for(const entry of entries){const started=performance.now(),cpu=process.cpuUsage(),packet=JSON.parse(readFileSync(path.join(ROOT,entry.input),'utf8'));
    const spec={...example(),family:adapter.manifest.id,name:packet.case_id,owner:'legal-research-unprivileged',rights:{dataClass:'synthetic',source:'Fresh synthetic text reconciliation '+packet.case_id,license:'Apache-2.0'},reviewMinutes:30,inputs:packet};
    const result=await runtime.run(spec,{sourceHash}),inspection=await runtime.inspectPack(result);
    writeFileSync(path.join(ROOT,entry.output),JSON.stringify({pack:result,inspection},null,2)+'\n');
    const usage=process.cpuUsage(cpu);receipts.push({case_id:packet.case_id,method:packet.method,elapsed_seconds:(performance.now()-started)/1000,cpu_seconds:(usage.user+usage.system)/1e6});
  }
  writeFileSync(process.argv[3],JSON.stringify({sourceHash,records:receipts},null,2)+'\n');console.log(JSON.stringify({jobs:receipts.length,sourceHash}));
}
