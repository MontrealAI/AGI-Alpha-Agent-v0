// SPDX-License-Identifier: Apache-2.0
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createWorkbench, example } from '../heritage/alpha/examples/successor-workbench/engine.mjs';
import { validateDocument, evaluate } from '../heritage/alpha/docs/assets/transformational-intelligence/source-understanding.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const stage = process.argv[2];
const inputPath = process.argv[3];
const outputPath = process.argv[4];
if (!['B','C1','C','D','T'].includes(stage) || !inputPath || !outputPath) throw Error('USAGE: STAGE INPUT OUTPUT');
const input = JSON.parse(readFileSync(inputPath, 'utf8'));
const heritage = JSON.parse(readFileSync(path.join(ROOT,'heritage/alpha-source-manifest.json'),'utf8'));
const sources = ['src/native_adapter.mjs','src/legal_packet.py','src/references.py','src/amendments.py','protocol/scope.json','evaluation/conventional.py'];
const hasher = createHash('sha256');
for (const item of heritage.files) {
  const bytes = readFileSync(path.join(ROOT,'heritage/alpha',item.path));
  if (createHash('sha256').update(bytes).digest('hex') !== item.sha256) throw Error('UPSTREAM_SOURCE_DRIFT:'+item.path);
  hasher.update(item.path).update(bytes);
}
for (const item of sources) hasher.update(item).update(readFileSync(path.join(ROOT,item)));
const sourceHash = hasher.digest('hex');
const python = process.env.CODEX_PRIMARY_RUNTIME_PYTHON || 'python3';
const adapter = {
  manifest: {id:'legal-nda-support',version:1,en:'NDA change-control packet',fr:'Dossier de contrôle des modifications NDA',
    scope:'Synthetic Ontario mutual-NDA mechanical playbook support; qualified legal review required.',artifact:'review-packet.json'},
  validate(value) {
    if (!value || typeof value !== 'object' || value.source_class !== 'synthetic') throw Error('SYNTHETIC_ONLY');
    if (typeof value.original_text !== 'string' || typeof value.revised_text !== 'string' || value.original_text.length > 30000 || value.revised_text.length > 30000) throw Error('TEXT_BUDGET');
    if (!Array.isArray(value.amendments) || value.amendments.length > 4) throw Error('AMENDMENT_BUDGET');
  },
  async execute(value,checkpoint) {
    await checkpoint('intake');
    const isConventional = stage === 'D';
    const args = isConventional ? [path.join(ROOT,'evaluation/conventional.py')] : [path.join(ROOT,'src/legal_packet.py'),'--stage',stage === 'T' ? 'C' : stage];
    const child = spawnSync(python,args,{input:JSON.stringify(value),encoding:'utf8',timeout:45000,maxBuffer:2000000,cwd:ROOT});
    if (child.error || child.status !== 0) throw Error('FIXED_WORKER_FAILED:'+String(child.error || child.stderr).slice(0,500));
    await checkpoint('analysis');
    const raw = JSON.parse(child.stdout);
    const packet = isConventional ? raw : raw.packet;
    if (packet.professional_acceptance !== 'unknown') throw Error('LEGAL_ACCEPTANCE_BOUNDARY');
    const sourcesSeen = new Map();
    for (const rule of packet.rule_results) for (const source of rule.sources || []) {
      const key = [source.document,source.start,source.end].join(':');
      if (!sourcesSeen.has(key) && source.quote.length <= 1500) sourcesSeen.set(key,source);
    }
    const citations = [...sourcesSeen.values()].slice(0,12);
    let structural = {status:'NOT_RUN',reason:'No suitable bounded exact source clauses'};
    if (citations.length) {
      const document = validateDocument({schema_version:1,schema:'source-document/v1',title:value.case_id+' exact packet passages',
        source_url:'https://github.com/MontrealAI/AGI-Alpha-Agent-v0',public_non_personal:true,
        claims:citations.map((source,i)=>({schema_version:1,id:'S'+(i+1),text:source.quote,weight:1,depends_on:[],provenance:[source.document,source.start,source.end].join(':')}))});
      structural = {status:'EXECUTED',scope:'TI exact-extractive structural coverage only; no legal truth or expert verification',
        record:evaluate(document,document.claims.map(c=>c.id)),dependency_annotations:'Not independently legally audited; no graph-value claim'};
    }
    await checkpoint('verification');
    const artifacts = [{name:'review-packet.json',type:'application/json',content:JSON.stringify(packet,null,2)+'\n'},
      {name:'source-context.json',type:'application/json',content:JSON.stringify(structural,null,2)+'\n'}];
    if (!isConventional) artifacts.push({name:'review-packet.html',type:'text/html',content:raw.html});
    else artifacts.push({name:'review-notes.txt',type:'text/plain',content:'Independent conventional packet. All source strings and exceptions are in review-packet.json. Qualified professional acceptance: unknown.\n'});
    return {decision:'COUNSEL_REVIEW_REQUIRED',summary:{caseId:value.case_id,arm:stage,checks:packet.rule_results.length,sourceChanges:packet.changes.length},
      evidence:{packet,structural,transfer:stage==='T'?'Recipient invokes acquired C implementation; no claim of unique capability or independently modified recipient':'none'},
      artifacts,limits:['Synthetic research production; no customer or professional legal acceptance.',
        'No legal advice, negotiations, signatures, filings, credentials, external services or financial transactions.',
        'Native signed-operator Harness and Fleet execution not provisioned or invoked; this uses the unchanged portable Workbench extension API.']};
  },
};
const runtime = createWorkbench([adapter]);
const spec = {...example(),family:adapter.manifest.id,name:input.case_id,owner:'legal-research-unprivileged',
  rights:{dataClass:'synthetic',source:'Independent original synthetic research case '+input.case_id,license:'Apache-2.0'},
  reviewMinutes:30,inputs:input};
const pack = await runtime.run(spec,{sourceHash});
const inspection = await runtime.inspectPack(pack);
if (inspection.authentication !== 'UNAUTHENTICATED_HISTORICAL_IMPORT' || inspection.activeAuthority.length) throw Error('UNEXPECTED_AUTHORITY');
mkdirSync(path.dirname(outputPath),{recursive:true});
writeFileSync(outputPath,JSON.stringify({pack,inspection,runtime:{node:process.version,sourceHash,stage}},null,2)+'\n');
