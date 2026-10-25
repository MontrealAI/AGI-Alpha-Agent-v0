// SPDX-License-Identifier: Apache-2.0
import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import * as guide from '../upstream/examples/ti-guide/guide.mjs';
const [inputPath, output, jobId, parentHash=''] = process.argv.slice(2);
const started = performance.now();
const input = JSON.parse(await readFile(inputPath,'utf8'));
const stages=[];
const result=await guide.compute(input, stage=>stages.push({stage,elapsed_ms:performance.now()-started}));
const summary={schema:'work-economics-delivery/v1',job_id:jobId,metrics:result.metrics,decision:'REVIEW_EXCEPTIONS',
  automatic_source_correction:false,new_human_trial:'NOT_RUN',market_comparison:'MODELLED_WITH_SOURCED_BENCHMARKS',fully_allocated_cost:'UNKNOWN',
  source_commit:'f836f06e8351e64db1da770e16e304b5feb01f28',retained_capability_sha256:parentHash||null,
  limitations:['Conflicts require a source-owner decision.','Exact string identifiers; no fuzzy matching, trimming or numeric coercion.',
    'A complete exception package is delivered; source truth and business updates remain human responsibilities.',
    'Human benchmark is market-data-grounded. No newly recruited human trial was run.']};
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const entries=Object.entries(result.metrics).filter(([k,v])=>Number.isSafeInteger(v));
const html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Reconciliation delivery — '+esc(jobId)+'</title><style>body{font:17px system-ui;max-width:65rem;margin:3rem auto;padding:1rem;color:#242135;background:#fbfafc}h1{color:#482082}table{border-collapse:collapse;width:100%}td,th{padding:.65rem;text-align:left;border-bottom:1px solid #ddd}a{color:#56248f}aside{padding:1rem;background:#eee7fa;border-radius:12px}</style><h1>Your reconciliation package</h1><p>'+esc(jobId)+'</p><aside>Conflicts require a source-owner decision.</aside><p>Download the complete records and review grouped exceptions. Duplicate identifiers retain every matching pair. Formula-like CSV cells are prefixed for spreadsheet safety; exact JSON retains original strings.</p><table><thead><tr><th>Measure</th><th>Result</th></tr></thead><tbody>'+entries.map(([k,v])=>'<tr><td>'+esc(k)+'</td><td data-metric="'+k+'">'+v+'</td></tr>').join('')+'</tbody></table><h2>Deliverables</h2><ul>'+['joined.csv','unmatched-left.csv','unmatched-right.csv','conflicts.csv','all-differences.csv','action-plan.csv','exact-result.json','guide-result.json','summary.json'].map(x=>'<li><a href="'+x+'">'+x+'</a></li>').join('')+'</ul><p>Compared columns: '+result.metrics.comparedColumns.map(esc).join(', ')+'.</p><p>Source identities and data-row references are in guide-result.json. Counts are local computed results; no commercial human comparison or fully allocated price is implied.</p></html>';
for(const [name,content] of Object.entries({'guide-result.json':JSON.stringify(result,null,2)+'\n','summary.json':JSON.stringify(summary,null,2)+'\n','all-differences.csv':guide.fullDifferencesCsv(result),'action-plan.csv':guide.actionPlanCsv(result),'summary.html':html,'guide-stages.json':JSON.stringify(stages,null,2)+'\n'})) await writeFile(join(output,name),content,{flag:'wx'});
console.log(JSON.stringify({job_id:jobId,elapsed_ms:performance.now()-started,metrics:result.metrics}));
