// SPDX-License-Identifier: Apache-2.0
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createWorkbench, example } from '../heritage/alpha/examples/successor-workbench/engine.mjs';
import { validateDocument, evaluate } from '../heritage/alpha/docs/assets/transformational-intelligence/source-understanding.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const hash = value => createHash('sha256').update(value).digest('hex');
const heritage = JSON.parse(readFileSync(path.join(ROOT,'heritage/alpha-source-manifest.json'),'utf8'));
const hasher = createHash('sha256');
for (const item of heritage.files) {
  const bytes = readFileSync(path.join(ROOT,'heritage/alpha',item.path));
  if (hash(bytes) !== item.sha256) throw Error('UPSTREAM_SOURCE_DRIFT:'+item.path);
  hasher.update(item.path).update(bytes);
}
for (const item of ['src/native_packaging.mjs','src/legal_packet.py','src/references.py','src/amendments.py','protocol/scope.json','evaluation/conventional.py']) {
  hasher.update(item).update(readFileSync(path.join(ROOT,item)));
}
const sourceHash = hasher.digest('hex');
const rules = JSON.parse(readFileSync(path.join(ROOT,'protocol/scope.json'),'utf8')).rules;

export function validateProduced(value) {
  if (!value || typeof value !== 'object' || !['B','C1','C','D','T'].includes(value.arm)) throw Error('ARM');
  const {request,packet} = value;
  if (!request || request.source_class !== 'synthetic' || packet?.case_id !== request.case_id) throw Error('REQUEST_BINDING');
  if (typeof request.original_text !== 'string' || typeof request.revised_text !== 'string' || request.original_text.length > 30000 || request.revised_text.length > 30000) throw Error('TEXT_BUDGET');
  if (!Array.isArray(request.amendments) || request.amendments.length > 4) throw Error('AMENDMENT_BUDGET');
  const documents = {original:request.original_text,revised:request.revised_text};
  for (const item of request.amendments) {
    if (!item || typeof item.id !== 'string' || typeof item.text !== 'string' || item.text.length > 8000 || Object.hasOwn(documents,'amendment:'+item.id)) throw Error('AMENDMENT_BINDING');
    documents['amendment:'+item.id] = item.text;
  }
  if (Object.keys(documents).sort().join('|') !== Object.keys(packet.source_hashes || {}).sort().join('|')) throw Error('SOURCE_SET');
  for (const [key,text] of Object.entries(documents)) if (packet.source_hashes[key] !== hash(text)) throw Error('SOURCE_HASH');
  let checked = 0;
  function walk(item,depth=0) {
    if (depth > 32 || ++checked > 30000) throw Error('PACKET_COMPLEXITY');
    if (!item || typeof item !== 'object') return;
    if (['document','start','end','quote'].every(key=>Object.hasOwn(item,key))) {
      if (!Object.hasOwn(documents,item.document) || !Number.isSafeInteger(item.start) || !Number.isSafeInteger(item.end)) throw Error('SOURCE_SPAN');
      const chars = Array.from(documents[item.document]);
      if (item.start < 0 || item.end < item.start || item.end > chars.length || chars.slice(item.start,item.end).join('') !== item.quote) throw Error('SOURCE_SPAN');
    }
    for (const child of Object.values(item)) walk(child,depth+1);
  }
  walk(packet);
  if (!Array.isArray(packet.rule_results) || packet.rule_results.length !== rules.length || new Set(packet.rule_results.map(x=>x.rule_id)).size !== rules.length) throw Error('RULE_COUNT');
  for (const row of packet.rule_results) if (!rules.some(r=>r.id===row.rule_id) || !['pass','deviation','absent','uncertain','out_of_scope'].includes(row.status)) throw Error('RULE_SCHEMA');
  if (packet.professional_acceptance !== 'unknown' || !Array.isArray(packet.proposed_revisions) || packet.proposed_revisions.length) throw Error('LEGAL_ACCEPTANCE_BOUNDARY');
  return documents;
}

const adapter = {
  manifest: {id:'legal-nda-support',version:1,en:'Verify an NDA change-control packet',fr:'Vérifier un dossier de modifications NDA',
    scope:'Verify source fidelity and package synthetic Ontario-NDA research analysis; professional correctness unassessed.',artifact:'review-packet.json'},
  validate: validateProduced,
  async execute(value,checkpoint) {
    await checkpoint('intake');
    validateProduced(value);
    await checkpoint('source-verification');
    const packet = value.packet;
    const sourcesSeen = new Map();
    for (const rule of packet.rule_results) for (const source of rule.sources || []) {
      const key = [source.document,source.start,source.end].join(':');
      if (!sourcesSeen.has(key) && source.quote.length <= 1500) sourcesSeen.set(key,source);
    }
    const citations = [...sourcesSeen.values()].slice(0,12);
    let structural = {status:'NOT_RUN',reason:'No suitable bounded exact source clauses'};
    if (citations.length) {
      const document = validateDocument({schema_version:1,schema:'source-document/v1',title:value.request.case_id+' exact packet passages',
        source_url:'https://github.com/MontrealAI/AGI-Alpha-Agent-v0',public_non_personal:true,
        claims:citations.map((source,i)=>({schema_version:1,id:'S'+(i+1),text:source.quote,weight:1,depends_on:[],provenance:[source.document,source.start,source.end].join(':')}))});
      structural = {status:'EXECUTED',scope:'TI exact-extractive structural coverage only; no legal truth or expert verification',
        record:evaluate(document,document.claims.map(c=>c.id)),dependency_annotations:'Not legally audited; no graph-value claim'};
    }
    await checkpoint('packaging');
    return {decision:'COUNSEL_REVIEW_REQUIRED',summary:{caseId:value.request.case_id,arm:value.arm,checks:packet.rule_results.length,sourceChanges:packet.changes.length},
      evidence:{packet,structural,analysisLocation:'Independent local Python stage, before this source-verification Workbench job',
        transfer:value.arm==='T'?'Frozen independent recipient acquired C as an alternative tool; no unique-capability claim':'none'},
      artifacts:[{name:'review-packet.json',type:'application/json',content:JSON.stringify(packet,null,2)+'\n'},
        {name:'source-context.json',type:'application/json',content:JSON.stringify(structural,null,2)+'\n'},
        {name:'review-notes.txt',type:'text/plain',content:'COUNSEL REVIEW REQUIRED / EXAMEN JURIDIQUE REQUIS. Source fidelity is verified, legal correctness is not. Synthetic research input; no client advice or transaction.\n'}],
      limits:['Two-stage local workflow: Python analysis then unchanged portable Alpha Workbench verification/packaging.',
        'Synthetic research production; no customer or qualified professional legal acceptance.',
        'Native signed-operator Harness, Fleet execution and settlement NOT RUN. Authority remains empty.']};
  },
};
const runtime = createWorkbench([adapter]);

export async function packageReview(value) {
  const started = performance.now(), cpu = process.cpuUsage();
  const spec = {...example(),family:adapter.manifest.id,name:value.request.case_id,owner:'legal-research-unprivileged',
    rights:{dataClass:'synthetic',source:'Independent synthetic case '+value.request.case_id,license:'Apache-2.0'},reviewMinutes:30,inputs:value};
  const pack = await runtime.run(spec,{sourceHash});
  const inspection = await runtime.inspectPack(pack);
  if (inspection.authentication !== 'UNAUTHENTICATED_HISTORICAL_IMPORT' || inspection.activeAuthority.length) throw Error('UNEXPECTED_AUTHORITY');
  const usage = process.cpuUsage(cpu);
  return {pack,inspection,runtime:{node:process.version,sourceHash,stage:value.arm,elapsed_seconds:(performance.now()-started)/1000,cpu_seconds:(usage.user+usage.system)/1e6}};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const manifest = JSON.parse(readFileSync(process.argv[2],'utf8'));
  const receipts = [];
  for (const entry of manifest) {
    const value = JSON.parse(readFileSync(path.resolve(ROOT,entry.input),'utf8'));
    const result = await packageReview(value);
    const target = path.resolve(ROOT,entry.output);
    if (!target.startsWith(ROOT+path.sep)) throw Error('OUTPUT_OUTSIDE_STUDY');
    mkdirSync(path.dirname(target),{recursive:true});
    writeFileSync(target,JSON.stringify(result,null,2)+'\n');
    receipts.push({case_id:value.request.case_id,arm:value.arm,output:entry.output,...result.runtime});
  }
  writeFileSync(process.argv[3],JSON.stringify(receipts,null,2)+'\n');
  console.log(JSON.stringify({jobs:receipts.length,output:process.argv[3],sourceHash}));
}
