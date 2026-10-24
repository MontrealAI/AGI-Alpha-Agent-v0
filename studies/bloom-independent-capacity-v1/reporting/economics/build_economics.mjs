import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
const study=path.resolve(process.argv[2]||'/workspace/scratch/04fd55a853bd/bloom_study');
const output=path.resolve(process.argv[3]||'/dev/shm/bloom-04fd55a853bd/build/economics');
await fs.mkdir(output,{recursive:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const sources={};
async function load(rel){const b=await fs.readFile(path.join(study,rel));sources[rel]={sha256:sha(b),bytes:b.length};return JSON.parse(b);}
const cols=['row_id','classification','scope','metric','value','unit','additive_cpu_total','contained_in','source_path','source_sha256','source_field','assumed_cpu_usd_per_core_hour','assumed_engineering_hours','assumed_engineer_usd_per_hour','notes'];
const rows=[];
function row(id,classification,scope,metric,value,unit,source,field,notes='',extra={}) {
 const r={row_id:id,classification,scope,metric,value,unit,additive_cpu_total:0,contained_in:'',source_path:source||'',source_sha256:sources[source]?.sha256||'',source_field:field||'',assumed_cpu_usd_per_core_hour:null,assumed_engineering_hours:null,assumed_engineer_usd_per_hour:null,notes,...extra};
 assert(!rows.some(x=>x.row_id===id),'duplicate row '+id);rows.push(r);return r;
}
const campaigns=[['development_v2_smoke','development/v2-smoke',0],['development_v2_rest','development/v2-rest',0],['confirmation','results/confirmation',48],['fresh_reproduction','results/reproduction',24],['confirmation_replay','results/confirmation_replay',0]];
const campaignTotals=[],allPhases={},allCounters={};
let campaignCpu=0,campaignWall=0,auditCpu=0,replacementCpu=0,trialCpu=0;
for(const [id,dir,fresh] of campaigns){
 const src=dir+'/campaign.json',c=await load(src),pid=id+'_cpu';
 campaignCpu+=c.campaign_cpu_ns;campaignWall+=c.campaign_wall_ns;auditCpu+=c.counts.external_audit_cpu_ns;replacementCpu+=c.counts.replacement_cpu_ns;
 row(pid,'measured',id,'campaign_cpu',c.campaign_cpu_ns,'CPU_ns',src,'campaign_cpu_ns','Inclusive process CPU: operational trials, independent external audit, one replacement construction per world and campaign I/O.',{additive_cpu_total:1});
 row(id+'_wall','measured',id,'campaign_wall',c.campaign_wall_ns,'wall_ns',src,'campaign_wall_ns','Elapsed time is never added to CPU.',{contained_in:pid});
 row(id+'_audit','measured_subset',id,'external_research_audit_cpu',c.counts.external_audit_cpu_ns,'CPU_ns',src,'counts.external_audit_cpu_ns','Included in campaign CPU; excluded symmetrically from method latency. Do not add again.',{contained_in:pid});
 row(id+'_replacement','measured_subset',id,'replacement_construction_and_qualification_cpu',c.counts.replacement_cpu_ns,'CPU_ns',src,'counts.replacement_cpu_ns','One actual construction per world, reused by arms. Attributed copies are not additional incurred CPU.',{contained_in:pid});
 row(id+'_trials','measured',id,'trial_records',c.counts.trials,'trial_records',src,'counts.trials','Executions including repetitions and diagnostic arms; not independent worlds.');
 row(id+'_worlds','measured',id,'worlds_executed',c.counts.worlds,'graph_worlds',src,'counts.worlds','Replay repeats confirmation worlds; development is excluded from confirmation.');
 row(id+'_freshworlds','derived_description',id,'fresh_scientific_worlds',fresh,'graph_worlds',src,'case_manifest','Zero for development and replay; sum of this field is 72.');
 row(id+'_rss','measured',id,'process_peak_rss',c.peak_rss_kib,'KiB',src,'peak_rss_kib','Process peak RSS, not artifact payload size; peaks are not additive.');
 row(id+'_bytes','measured',id,'evidence_bytes_before_manifest',c.output_bytes_before_manifest,'bytes',src,'output_bytes_before_manifest','Campaign-end bytes before manifest; not final bundle size.');
 const rawRel=dir+'/records.jsonl.gz',raw=await fs.readFile(path.join(study,rawRel));assert.equal(sha(raw),c.records_sha256);sources[rawRel]={sha256:sha(raw),bytes:raw.length};
 const records=zlib.gunzipSync(raw).toString('utf8').trim().split('\n').map(JSON.parse);assert.equal(records.length,c.counts.trials);
 const phases={},counters={};let rt=0,prod=0,recv=0;
 for(const r of records){
  rt+=r.total_cpu_ns;prod+=r.producer_cpu_ns||0;recv+=r.receiver_cpu_ns||0;
  for(const [name,v] of Object.entries(r.phases||{})){
   if(!phases[name])phases[name]={cpu_ns:0,wall_ns:0,calls:0};if(!allPhases[name])allPhases[name]={cpu_ns:0,wall_ns:0,calls:0};
   for(const k of ['cpu_ns','wall_ns','calls']){phases[name][k]+=v[k];allPhases[name][k]+=v[k];}
  }
  for(const [name,v] of Object.entries(r.counters||{})){counters[name]=(counters[name]||0)+v;allCounters[name]=(allCounters[name]||0)+v;}
 }
 trialCpu+=rt;assert(rt+c.counts.external_audit_cpu_ns+c.counts.replacement_cpu_ns<=c.campaign_cpu_ns);
 row(id+'_operational_trials','measured_subset',id,'sum_all_trial_cpu',rt,'CPU_ns',rawRel,'sum(total_cpu_ns)','All methods, stress, ablations and replicates; included in campaign. Not the primary estimand.',{contained_in:pid});
 row(id+'_producer','measured_subset',id,'sum_available_producer_cpu',prod,'CPU_ns',rawRel,'sum(producer_cpu_ns where present)','Nested within trials; absent for early refusal/error paths.',{contained_in:id+'_operational_trials'});
 row(id+'_receiver','measured_subset',id,'sum_available_receiver_cpu',recv,'CPU_ns',rawRel,'sum(receiver_cpu_ns where present)','Nested within trials; includes reconstruction when needed.',{contained_in:id+'_operational_trials'});
 const residual=c.campaign_cpu_ns-rt-c.counts.external_audit_cpu_ns-c.counts.replacement_cpu_ns;
 row(id+'_residual','derived_subset',id,'campaign_cpu_outside_trial_audit_replacement_timers',residual,'CPU_ns',src,'campaign - sum(trial totals) - audit - replacement','Includes generation, orchestration, compression, writing and timer overhead.',{contained_in:pid});
 for(const [name,v] of Object.entries(phases).sort())for(const k of ['cpu_ns','wall_ns','calls'])row(id+'_phase_'+name+'_'+k,k==='calls'?'measured_counter':'measured_subset',id,'phase_'+name+'_'+k,v[k],k==='cpu_ns'?'CPU_ns':k,rawRel,'sum(phases.'+name+'.'+k+')','Nested phase observation, never additive to campaign CPU; calls are invocations, not instructions or money.',{contained_in:id+'_operational_trials'});
 for(const [name,v] of Object.entries(counters).sort())row(id+'_counter_'+name,'measured_counter',id,name,v,name,rawRel,'sum(counters.'+name+')','Named software work counter; no conversion to money or detector exposures.');
 campaignTotals.push({id,source:src,cpu_ns:c.campaign_cpu_ns,wall_ns:c.campaign_wall_ns,audit_cpu_ns:c.counts.external_audit_cpu_ns,replacement_cpu_ns:c.counts.replacement_cpu_ns,operational_trial_cpu_ns:rt,residual_cpu_ns:residual,trials:c.counts.trials,worlds:c.counts.worlds,fresh_scientific_worlds:fresh});
}
const nativePaths=[['integration_smoke_initial','integration/smoke/native/native_workflow_receipt.json'],['integration_smoke_verified','integration/smoke/native-verified/native_workflow_receipt.json'],['integration_smoke_final','integration/smoke/native-final/native_workflow_receipt.json'],['development_native_demo','development/native-demo-v1/native/native_workflow_receipt.json'],['public_manifest_native_demo','results/public-demo/native/native_workflow_receipt.json']];
const nativeTotals=[];let nativeCpu=0,nativeWall=0;
for(const [id,src] of nativePaths){
 const n=await load(src),pid=id+'_cpu';nativeCpu+=n.total_cpu_ns;nativeWall+=n.total_wall_ns;
 row(pid,'measured',id,'native_journey_cpu',n.total_cpu_ns,'CPU_ns',src,'total_cpu_ns',n.cost_scope,{additive_cpu_total:1});
 row(id+'_wall','measured',id,'native_journey_wall',n.total_wall_ns,'wall_ns',src,'total_wall_ns','Elapsed time; never added to CPU.',{contained_in:pid});
 row(id+'_calls','measured_counter',id,'native_stage_calls',n.resource_ledger.spent.stage_calls,'stage_calls',src,'resource_ledger.spent.stage_calls','Invocation budget units, not CPU instructions, currency or token utility.');
 for(const st of n.stage_receipts)for(const kind of ['stage','handler'])row(id+'_'+kind+'_'+st.stage,'measured_subset',id,'native_'+kind+'_'+st.stage+'_cpu',st[kind+'_cpu_ns'],'CPU_ns',src,'stage_receipts['+st.stage+'].'+kind+'_cpu_ns',kind==='handler'?'Handler time is inside stage/journey time.':'Stage time is inside journey time.',{contained_in:kind==='handler'?id+'_stage_'+st.stage:pid});
 nativeTotals.push({id,source:src,cpu_ns:n.total_cpu_ns,wall_ns:n.total_wall_ns,created_at:n.created_at,status:n.status,cost_scope:n.cost_scope});
}
const initialSource='development/v1/INITIAL_SMOKE.json',initial=await load(initialSource);let initialCpu=0;
for(const o of initial.observations){const ns=Math.round(o.cpu_ms*1e6);initialCpu+=ns;row('initial_smoke_'+o.method,'measured_retained_summary','development_v1','initial_'+o.method+'_trial_cpu',ns,'CPU_ns',initialSource,'observations['+o.method+'].cpu_ms * 1000000',initial.retention_limit,{additive_cpu_total:1});}
const demoSource='results/public-demo/summary.json',demo=await load(demoSource);
for(const [name,v] of Object.entries(demo.kernel_metrics.phases).sort())row('public_demo_kernel_'+name,'measured_subset','public_manifest_native_demo','kernel_'+name+'_cpu',v.cpu_ns,'CPU_ns',demoSource,'kernel_metrics.phases.'+name+'.cpu_ns','Included in native callback/stage/journey time; not another scientific benchmark.',{contained_in:'public_manifest_native_demo_cpu'});
for(const [name,v] of Object.entries(demo.kernel_metrics.counters).sort())row('public_demo_counter_'+name,'measured_counter','public_manifest_native_demo',name,v,name,demoSource,'kernel_metrics.counters.'+name,'Software counter, not currency or detector exposures.');
const sourceReceipt='public_case/source_receipt.json',pub=await load(sourceReceipt),snapshotBytes=pub.files.reduce((a,x)=>a+x.bytes,0),usedBytes=pub.files.filter(x=>pub.graph_sources.includes(x.filename)).reduce((a,x)=>a+x.bytes,0);
row('public_snapshots','measured_source_acquisition','public_fixture','retrieved_pinned_manifest_snapshots',pub.files.length,'files',sourceReceipt,'files.length','Saved snapshots, not total connector/API requests.');
row('public_snapshot_bytes','measured_source_acquisition','public_fixture','retrieved_snapshot_bytes',snapshotBytes,'bytes',sourceReceipt,'sum(files.bytes)','Includes Jobs snapshot retained as source only.');
row('graph_sources','measured_source_acquisition','public_fixture','snapshots_used_for_graph',pub.graph_sources.length,'files',sourceReceipt,'graph_sources.length','Alpha and Manager only; Jobs excluded from graph.');
row('graph_source_bytes','measured_source_acquisition','public_fixture','graph_input_snapshot_bytes',usedBytes,'bytes',sourceReceipt,'sum(bytes of graph_sources)','Subset of all acquired source bytes.');
for(const f of pub.files){const rel='public_case/raw/'+f.filename,b=await fs.readFile(path.join(study,rel));assert.equal(sha(b),f.sha256);assert.equal(b.length,f.bytes);sources[rel]={sha256:sha(b),bytes:b.length};row('source_'+f.filename.replaceAll('.','_'),'measured_source_acquisition','public_fixture','pinned_manifest_bytes',f.bytes,'bytes',rel,'file bytes','Commit '+f.commit+'; '+(pub.graph_sources.includes(f.filename)?'used in graph':'retained source only')+'.');}
const zeroSource='results/confirmation/campaign.json';
for(const [id,metric,unit,field,note] of [
 ['detectors','physical_detector_acquisitions','acquisitions','physical_detector_acquisitions','Zero physical observations; does not erase public source acquisitions.'],
 ['revenue','actual_cash_revenue','USD','cash_revenue','No sales/receipts occurred. Zero revenue does not imply zero cost.'],
 ['offers','firm_offers','offers','firm_offers','No firm customer offer documented.'],
 ['demand','independently_supported_demand','validated_acceptances','independently_supported_demand','Local fixture acceptance is engineering validation, not independent demand.'],
 ['paid','new_explicit_paid_resource_charges','USD','counts.new_paid_resource_charges','No new paid commitment; existing service allocation is unknown.']
])row(id,'observed_zero','study',metric,0,unit,zeroSource,field,note);
row('transactions','observed_zero','study','external_financial_transactions',0,'transactions','protocol/PROTOCOL.md','Budget','No external transaction or settlement was executed.');
for(const [id,metric,unit,note] of [
 ['human','human_authoring_and_review_cost','USD','No time sheet or paid fee; do not substitute zero.'],
 ['service','model_service_or_API_authoring_cost','USD','Local frozen kernels use no model API; surrounding authoring/retrieval service fees were not allocated.'],
 ['hardware','inherited_hardware_and_power_cost','USD','Measured CPU has no observed hardware/power allocation.'],
 ['requests','source_connector_request_count','requests','Three saved snapshots do not establish total request count.'],
 ['integration','integration_labor_and_maintenance_cost','USD','Native CPU receipts do not measure human integration/support work.'],
 ['authoring_cpu','unreceipted_authoring_reporting_analysis_packaging_compute','CPU_ns','No complete timer for authoring, bootstrap analysis/reporting, typesetting, early failed infrastructure or packaging.'],
 ['value','willingness_to_pay_or_value_per_use','USD_per_use','No independently supported valuation or price; no revenue scenario invented.'],
 ['maintenance','future_maintenance_cost','USD','No observed maintenance horizon or cost.']
])row('unknown_'+id,'unknown','study',metric,null,unit,'protocol/PROTOCOL.md','G5 Economics; Measurement and complete accounting',note);
const analyses={},oracle={};
for(const [label,dir] of [['confirmation','results/confirmation'],['fresh_reproduction','results/reproduction'],['confirmation_replay','results/confirmation_replay']]){
 const src=dir+'/analysis.json',a=await load(src);analyses[label]=a;
 for(const [m,t] of Object.entries(a.primary_mean_cpu_seconds))row(label+'_primary_'+m,'measured_estimate',label,m+'_mean_of_world_median_operational_cpu',t,'CPU_seconds_per_world',src,'primary_mean_cpu_seconds.'+m,'Stable stratum; median of three runs/world, then arithmetic mean. Not a campaign subtotal.');
 const p=a.primary_cpu_ns_by_world,mins=p.expert.map((t,i)=>Math.min(t,p.reverse[i])),mean=mins.reduce((x,y)=>x+y,0)/mins.length/1e9,ratio=Math.exp(mins.reduce((x,t,i)=>x+Math.log(p.bloom[i]/t),0)/mins.length);
 oracle[label]={worlds:mins.length,oracle_mean_cpu_seconds:mean,bloom_over_oracle_geometric_mean_ratio:ratio,expert_min_worlds:p.expert.filter((x,i)=>x<=p.reverse[i]).length,reverse_min_worlds:p.expert.filter((x,i)=>x>p.reverse[i]).length,oracle_minus_bloom_mean_cpu_seconds:mean-a.primary_mean_cpu_seconds.bloom,oracle_ns_by_world:mins,classification:'Post-study descriptive completion of a preregistered reporting item; no new interval or hypothesis test. Hindsight minimum is not executable selection; its selection cost is unknown.'};
 row(label+'_oracle_cpu','descriptive_oracle',label,'hindsight_min_conventional_mean_cpu',mean,'CPU_seconds_per_world',src,'mean(min(expert[i],reverse[i]))/1e9',oracle[label].classification);
 row(label+'_oracle_ratio','descriptive_oracle',label,'bloom_over_hindsight_oracle_ratio',ratio,'ratio',src,'exp(mean(log(bloom[i]/min(expert[i],reverse[i]))))',oracle[label].classification);
 for(const [i,s] of a.economics.sensitivity.entries()){
  const extra={assumed_cpu_usd_per_core_hour:s.modeled_cpu_dollars_per_core_hour,assumed_engineering_hours:s.unknown_extra_engineering_hours_scenario,assumed_engineer_usd_per_hour:s.assumed_engineer_dollars_per_hour},prefix=label+'_model_'+i;
  row(prefix+'_fixed','modeled_assumption',label,'additional_fixed_engineering_cost',s.extra_fixed_cost_scenario,'USD',src,'economics.sensitivity['+i+'].extra_fixed_cost_scenario','Assumed additional hours times assumed fee; not observed development spending.',extra);
  row(prefix+'_delta','modeled_conversion',label,'expert_minus_bloom_variable_cpu_cost',s.incremental_cpu_cost_saving_per_world_dollars,'USD_per_world',src,'economics.sensitivity['+i+'].incremental_cpu_cost_saving_per_world_dollars','Equal output quality; expert is best conventional mean. Negative means candidate costs more. No demonstrated demand or margin.',extra);
  row(prefix+'_breakeven','modeled_conditional',label,'uses_to_recover_additional_fixed_cost',s.uses_to_recover_extra_fixed_cost,'uses',src,'economics.sensitivity['+i+'].uses_to_recover_extra_fixed_cost',s.uses_to_recover_extra_fixed_cost===null?'No finite recovery when measured point saving is nonpositive.':'Ceiling(fixed cost/positive point saving); assumes unchanged performance and excludes unknown costs. Not a forecast.',extra);
  if(s.unknown_extra_engineering_hours_scenario===0)for(const [m,v] of Object.entries(s.variable_cost_per_world_dollars))row(prefix+'_variable_'+m,'modeled_conversion',label,m+'_variable_cpu_cost',v,'USD_per_world',src,'economics.sensitivity['+i+'].variable_cost_per_world_dollars.'+m,'Hypothetical tariff, not observed provider price. Full costs remain unknown.',extra);
 }
}
const freeze=await load('protocol/FREEZE.json'),freezeSha=sources['protocol/FREEZE.json'].sha256;assert.equal(freezeSha,'ecd3df2706d034d17a1441c62fd4dba0c7c92f5ea4d22327011bf5e1116bcfbe');
for(const f of freeze.files)assert.equal(sha(await fs.readFile(path.join(study,f.path))),f.sha256);
const pb=await fs.readFile(path.join(study,'protocol/PROTOCOL.md'));sources['protocol/PROTOCOL.md']={sha256:sha(pb),bytes:pb.length};
for(const r of rows)if(r.source_path&&!r.source_sha256)r.source_sha256=sources[r.source_path]?.sha256||'';
const measuredCpu=campaignCpu+nativeCpu+initialCpu;
assert.equal(measuredCpu,54266114933);assert.equal(campaignCpu,47887703197);assert.equal(nativeCpu,6198259305);assert.equal(initialCpu,180152431);
assert.equal(rows.filter(r=>r.additive_cpu_total===1).reduce((a,r)=>a+r.value,0),measuredCpu);
assert.equal(campaignTotals.reduce((n,r)=>n+r.fresh_scientific_worlds,0),72);
const summary={schema:'bloom-post-study-economics/v1',generated_at_utc:new Date().toISOString(),freeze_manifest_sha256:freezeSha,classification:'Derived reporting; frozen science/analysis unchanged',recorded_compute:{campaign_cpu_ns:campaignCpu,native_cpu_ns:nativeCpu,early_summary_cpu_ns:initialCpu,documented_cpu_subtotal_ns:measuredCpu,campaign_wall_ns:campaignWall,native_wall_ns:nativeWall,early_wall_ns:null,external_audit_cpu_ns_included:auditCpu,replacement_cpu_ns_included:replacementCpu,operational_trial_cpu_ns_included:trialCpu},campaigns:campaignTotals,native_runs:nativeTotals,initial_development:initial,scientific_sampling:{confirmation_worlds:48,reproduction_worlds:24,fresh_scientific_worlds:72,fresh_trials:3816,replay_worlds_repeated:48,replay_trials:2544,development_worlds:12,development_v2_trials:636,development_v1_retained_calls:3},phase_sums:allPhases,software_counters:allCounters,public_source_acquisitions:{files:pub.files.length,bytes:snapshotBytes,graph_files:pub.graph_sources.length,graph_bytes:usedBytes,total_request_count:null},oracle,full_monetary_cost_complete:false,proven_commerce:false,actual_revenue_usd:0,external_transactions:0,firm_offers:0,physical_detector_acquisitions:0,independent_customer_acceptance:0,ledger_rows:rows.length,source_files:sources};
await fs.writeFile(path.join(output,'ECONOMICS_SUMMARY.json'),JSON.stringify(summary,null,2)+'\n');
const sec=n=>(n/1e9).toFixed(9),sci=x=>x===null?'Not finite':Number(x).toExponential(8);
const lines=[
'# BLOOM∞ economics and resource ledger','',
'## Verdict','',
'The evidence supports a measured compute subtotal and conditional CPU-price arithmetic. It does not establish positive full-cost margin or competitive commercial advantage. Cash revenue, firm offers, independently supported customer demand and external financial transactions are zero. Human/model/service, hardware and maintenance costs remain unknown rather than zero. The expert policy has the best conventional mean in both fresh scientific sets. Its small confirmation CPU disadvantage reverses on fresh reproduction.','',
'This post-study report reads unchanged frozen evidence. It introduces no new dataset, hypothesis, threshold or inferential test. FREEZE manifest SHA-256: '+freezeSha+'.','',
'## Measured compute and reconciliation','',
'The documented subtotal is **'+sec(measuredCpu)+' CPU seconds**: '+sec(campaignCpu)+' across five measured scientific/development campaigns, '+sec(nativeCpu)+' across five distinct native journeys, and '+sec(initialCpu)+' from three early development calls. This partial resource subtotal excludes unmetered authoring, analysis/reporting, retrieval, publication and service allocation.','',
'| Receipt scope | CPU seconds | Wall seconds | Interpretation |','| --- | ---: | ---: | --- |',
...campaignTotals.map(c=>'| '+c.id+' | '+sec(c.cpu_ns)+' | '+sec(c.wall_ns)+' | '+c.worlds+' worlds; '+c.trials+' records'+(c.id==='confirmation_replay'?'; repeated worlds':'')+' |'),
...nativeTotals.map(n=>'| '+n.id+' | '+sec(n.cpu_ns)+' | '+sec(n.wall_ns)+' | Separate native journey; no additional scientific worlds |'),
'| Initial development v1 | '+sec(initialCpu)+' | Unrecorded | Three calls; full raw returns unavailable |','',
'Native journeys include source checks, journal setup, dispatch, callbacks, acceptance, backup and stopped restoration; receipts exclude final serialization and caller work. Signing material is public test-only fixture material. No external submission or settlement occurred.','',
'Campaign CPU already contains **'+sec(auditCpu)+' s** of external research audit and **'+sec(replacementCpu)+' s** of replacement construction/qualification. Do not add these again. Inclusive operational trial timers sum to **'+sec(trialCpu)+' s** within campaigns. The residual **'+sec(campaignCpu-auditCpu-replacementCpu-trialCpu)+' s** includes generation, orchestration, compression, writing and timer overhead.','',
'Producer, receiver, kernel and native stage/handler timers are nested observations. The CSV contained_in field identifies their parent; only additive_cpu_total=1 rows enter the documented subtotal. Wall time is never added to CPU. Peak RSS is not artifact payload bytes. Archived receipt copies, analysis copies and cumulative-budget fields are not new executions.','',
'The independent research oracle is excluded symmetrically from method latency and included in campaign compute. Operational qualification stays in method timing. Each conventional replacement is built once per world; attribution to several arms is not repeated actual cost. Failed construction attempts, fallback, diagnostic ablations and timed repetitions remain charged inside campaigns.','',
'## Acquisitions and computational work','',
'Physical detector acquisitions: **0**. Public source acquisitions: **3 saved snapshots**, totaling **'+snapshotBytes.toLocaleString('en-US')+' bytes**. Two snapshots ('+usedBytes.toLocaleString('en-US')+' bytes) supply the graph; Jobs is source-only. Saved file counts do not establish total connector/API requests. Request counts and allocated retrieval fees are unknown.','',
'Node visits, edge reads, bit operations, cover transitions, witness checks, constructor attempts and phase calls keep distinct software units. They are never combined into generalized opportunity-cost scores or converted into detector exposures or money. No actual tests are executed. Coverage costs are synthetic duration weights, not measured runtimes, CPU charges, prices or revenue.','',
'## Primary operational comparison','',
'Each mean averages the per-world median of three stable runs. Worlds, not queries or repetitions, are the independent units. These means are not campaign totals.','',
'| Scientific set | BLOOM ms/world | Expert ms/world | Reverse ms/world | Expert minus BLOOM ms/world |','| --- | ---: | ---: | ---: | ---: |',
...Object.entries(analyses).map(([k,a])=>'| '+k+' | '+(a.primary_mean_cpu_seconds.bloom*1000).toFixed(9)+' | '+(a.primary_mean_cpu_seconds.expert*1000).toFixed(9)+' | '+(a.primary_mean_cpu_seconds.reverse*1000).toFixed(9)+' | '+(a.economics.incremental_cpu_seconds_saved_per_world*1000).toFixed(9)+' |'),'',
'Confirmation has a mean 0.106574667 ms CPU reduction against expert. Fresh reproduction has a mean 0.068686250 ms increase. Both practical competitive gates failed. A lower point CPU cost alone does not establish demand, revenue, margin or a reproducible commercial advantage.','',
'### Hypothetical tariff conversion','',
'Frozen sensitivity assumes $0.02, $0.10 and $1.00/core-hour. These are not measured or quoted provider prices. For mean CPU t seconds/world and tariff p, variable CPU cost = t × p / 3600. Negative expert-minus-BLOOM cost means the candidate costs more at equal quality.','',
'| Set | Assumed USD/core-hour | BLOOM USD/world | Expert USD/world | Expert minus BLOOM USD/world |','| --- | ---: | ---: | ---: | ---: |',
...Object.entries(analyses).flatMap(([k,a])=>a.economics.sensitivity.filter(s=>s.unknown_extra_engineering_hours_scenario===0).map(s=>'| '+k+' | '+s.modeled_cpu_dollars_per_core_hour.toFixed(2)+' | '+sci(s.variable_cost_per_world_dollars.bloom)+' | '+sci(s.variable_cost_per_world_dollars.expert)+' | '+sci(s.incremental_cpu_cost_saving_per_world_dollars)+' |')),'',
'### Additional engineering sensitivity','',
'The frozen scenarios assume 0, 1, 8, 40 or 160 unknown additional engineering hours at $100/hour. These are not observed labor or fees. CPU-only recovery is ceil(F / d) for positive point saving d. A nonpositive saving cannot recover a positive fixed cost through repeated uses. A zero-F negative-saving case is still noncompetitive and is not assigned zero recovery uses.','',
'| Additional hours | Assumed fixed cost USD | Confirmation uses at $0.02/core-hour | At $0.10/core-hour | At $1.00/core-hour |','| ---: | ---: | ---: | ---: | ---: |',
...[0,1,8,40,160].map(h=>'| '+h+' | '+h*100+' | '+analyses.confirmation.economics.sensitivity.filter(s=>s.unknown_extra_engineering_hours_scenario===h).map(s=>s.uses_to_recover_extra_fixed_cost===null?'Not finite':s.uses_to_recover_extra_fixed_cost.toLocaleString('en-US')).join(' | ')+' |'),'',
'Fresh reproduction has no positive CPU saving under any tariff, so every recovery count is null/not finite. Confirmation extrapolations assume unchanged performance at enormous volume and exclude unknown costs. They are arithmetic sensitivity, not a sales or scale forecast. Replay timing never replaces original confirmation.','',
'## Opportunity cost, net value and missing inputs','',
'The credible alternative use of a constrained CPU second is the equally equipped expert workload at the same quality. No observed queue, capacity shortage, forgone sale or external price establishes monetary value for this capacity. For N uses, common gross value V, additional fixed cost F and other incremental cost U, candidate-minus-expert modeled net value is N × (C_expert − C_BLOOM) − F − U. Common V cancels. V and material parts of F and U remain unknown. A positive CPU-only difference is not proven positive net value.','',
'Full cost requires attributable human time, model/service fees, hardware and power, acquisition overhead, integration, maintenance/support and incurred validation. Unknown CSV values are blank with classification=unknown. No synthetic balance is cash, predecessor value is not counted twice and no hypothetical successor receipt is added. No $100-to-$10,000 result is claimed.','',
'## Descriptive conventional oracle','',
'The protocol promised an optimistic best-observed conventional bound. Frozen analysis retained paired arrays without deriving that field. This report takes min(expert, reverse) per world after median timing. This hindsight minimum is **not an executable selector**, its selection cost is unknown, and no new interval or threshold test is added.','',
'| Set | Oracle mean CPU ms/world | BLOOM/oracle geometric ratio | Expert chosen | Reverse chosen |','| --- | ---: | ---: | ---: | ---: |',
...Object.entries(oracle).map(([k,o])=>'| '+k+' | '+(o.oracle_mean_cpu_seconds*1000).toFixed(9)+' | '+o.bloom_over_oracle_geometric_mean_ratio.toFixed(12)+' | '+o.expert_min_worlds+' | '+o.reverse_min_worlds+' |'),'',
'Arithmetic cost differences and geometric paired ratios are different summaries. Confirmation has BLOOM/oracle geometric ratio 0.998341958 but slightly higher BLOOM arithmetic mean CPU. Fresh reproduction favors the oracle on both summaries.','',
'## Sampling and file use','',
'There are **72 unique scientific worlds and 3,816 fresh trials** (48 confirmation plus 24 reproduction worlds). The 48-world, 2,544-record replay incurs real compute but adds no independent world. Twelve development worlds, three initial dev101 calls and five native journeys are not extra confirmation.','',
'Read classification, unit, contained_in and additive_cpu_total before aggregating value. Units deliberately differ. Blank means unknown or a mathematically unavailable recovery count, as explained in notes. Summing every numeric cell would be invalid. Source paths are relative to the study root and each source has SHA-256. ECONOMICS_SUMMARY.json contains source identities and derived detail. POST_STUDY_REPORTING_DEVIATIONS.md discloses limitations without changing protocol or results. Original G1-pending analyses remain unchanged; the independent reproduction receipt supplies later closure.',''
];
await fs.writeFile(path.join(output,'ECONOMICS.md'),lines.join('\n'));
const deviations=[
'# Post-study reporting deviations and clarifications','',
'This post-study note preserves frozen protocol, source, cases, analysis and thresholds. It records discrepancies found during manuscript/economics review and makes no new confirmatory claim.','',
'## D1. Missing-edge challenge is stronger than frozen prose','',
'PROTOCOL.md says the challenge removes an edge. Frozen core.py removes every incoming edge to the last app; generate.py ensures source0 has a direct edge to that app and that the first query contains source0. False-safe counts therefore describe an intentionally adversarial all-incoming-edge removal, not random single-edge deletion or ordinary omission prevalence. All methods share the challenge, excluded from in-scope quality and primary timing. Frozen implementation and data remain unchanged.','',
'## D2. Native overhead is outside scientific campaign timers','',
'Protocol prose says separately measured native overhead is included in campaign cost. run_study.py does not invoke the native dispatcher in scientific trials, so campaign.json excludes five separately executed native journeys. This reporting ledger includes their '+sec(nativeCpu)+' CPU seconds in the documented project subtotal and retains the '+sec(campaignCpu)+'-second scientific/development campaign subtotal. No native overhead is silently amortized per query. Primary timing is not the complete seven-stage native runtime.','',
'## D3. Promised descriptive conventional oracle was not derived','',
'Protocol promises an optimistic best-observed conventional bound. Frozen analyze.py exposes paired median arrays and separate references but no per-world minimum. ECONOMICS_SUMMARY.json now derives that descriptive minimum from unchanged arrays. It is not a deployable policy, its selection cost is unknown and no interval, test or threshold is added. Original analyses remain byte-identical.','',
'## D4. Earliest development calls have incomplete raw retention','',
'development/v1/INITIAL_SMOKE.json retains command, seed101, exit, choices and three CPU observations totaling '+sec(initialCpu)+' seconds. Full return values were not serialized. Exact source/generator/reference versions remain. This limitation is disclosed without inventing missing records or promoting development to confirmation. Later version2 trials have full retained raw records.','',
'## D5. Value-per-use sensitivity grid was not specified or run','',
'Protocol prose promises CPU-price, engineering-hour and value-per-use sensitivity. Frozen analysis implements CPU prices and engineering hours but no value-per-use grid. No supported demand/value was obtained. This report discloses the omission instead of inventing willingness to pay after results. Common value cancels in the equal-quality comparative formula; full monetary viability stays incomplete.','',
'## D6. Original G1 status and later evidence closure differ by design','',
'Frozen analyze.py emits PENDING_INDEPENDENT_REPLAY. The later independent receipt closes G1 after exact deterministic case/operator/record/source comparisons. Publication may report the later PASS while linking original pending analyses and the later closure; it must not edit originals retroactively.','',
'## D7. Budget scope excludes unmetered surrounding work','',
'The automatic 1,200-second guard sums completed campaign.json receipts under development/results. It excludes three early summary-only calls, native integration, human/model authoring, analysis/bootstrap/reporting, retrieval and publication. This ledger adds separately metered early/native work to reach '+sec(measuredCpu)+' documented CPU seconds and flags other compute/costs unknown. The guard is a scientific-execution envelope, not a complete project CPU or monetary budget.','',
'## Controls','',
'- Frozen source/manifest hashes remain unchanged.',
'- Original confirmation retains primary timing status; replay timing is separate.',
'- Replayed worlds, native stages and development do not enlarge scientific sample size.',
'- Audit/replacement/nested timers and duplicate archived receipts are not double-counted.',
'- No new cases, threshold, confidence interval or hypothesis test is introduced.',''
];
await fs.writeFile(path.join(output,'POST_STUDY_REPORTING_DEVIATIONS.md'),deviations.join('\n'));
// The initial CSV was authored and checked with Artifact Tool. Default
// reproduction needs only Node standard-library modules and retained receipts.
// Add --artifact-authoring after the two paths to repeat optional workbook QA.
const matrix=[cols,...rows.map(r=>cols.map(k=>r[k]??null))];
let values=matrix;
if(process.argv.includes('--artifact-authoring')){
 const { Workbook }=await import('@oai/artifact-tool');
 const wb=Workbook.create(),sheet=wb.worksheets.add('Economics ledger');
 sheet.getRange('A1:O'+matrix.length).values=matrix;sheet.showGridLines=false;
 sheet.getRange('A1:O'+matrix.length).format.font={name:'Arial',size:10};
 sheet.getRange('A1:O1').format={fill:'#302146',font:{name:'Arial',bold:true,color:'#FFFFFF'},rowHeight:28};
 sheet.getRange('A1:A'+matrix.length).format.columnWidth=40;
 sheet.getRange('B1:C'+matrix.length).format.columnWidth=26;
 sheet.getRange('D1:D'+matrix.length).format.columnWidth=50;
 sheet.getRange('E1:F'+matrix.length).format.columnWidth=19;
 sheet.getRange('G1:O'+matrix.length).format.columnWidth=24;
 sheet.getRange('A2:D'+matrix.length).format.wrapText=true;
 sheet.getRange('A2:F'+matrix.length).format.rowHeight=36;
 sheet.getRange('E2:E'+matrix.length).setNumberFormat('General');
 sheet.freezePanes.freezeRows(1);wb.recalculate();
 const check=await wb.inspect({kind:'table',range:'Economics ledger!A1:F10',include:'values,formulas',tableMaxRows:10,tableMaxCols:6,maxChars:4000});
 await fs.writeFile(path.join(output,'AUTHORING_CHECK.ndjson'),check.ndjson+'\n');
 values=sheet.getRange('A1:O'+matrix.length).values;assert.equal(values.length,matrix.length);
 for(let i=0;i<values.length;i++)for(let j=0;j<cols.length;j++)assert.equal(values[i][j]??null,matrix[i][j]??null);
 try{const preview=await wb.render({sheetName:'Economics ledger',range:'A1:F16',scale:1,format:'png'});await fs.writeFile(path.join(output,'ledger_preview.png'),new Uint8Array(await preview.arrayBuffer()));}
 catch(e){await fs.writeFile(path.join(output,'RENDER_LIMITATION.txt'),String(e)+'\n');}
}
const escapeCSV=x=>{const s=x===null||x===undefined?'':String(x);return /[",\r\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;};
await fs.writeFile(path.join(output,'ECONOMICS_LEDGER.csv'),values.map(r=>r.map(escapeCSV).join(',')).join('\r\n')+'\r\n');
const names=['ECONOMICS_LEDGER.csv','ECONOMICS.md','ECONOMICS_SUMMARY.json','POST_STUDY_REPORTING_DEVIATIONS.md'],manifest={schema:'bloom-economics-files/v1',freeze_manifest_sha256:freezeSha,files:[]};
for(const name of names){const b=await fs.readFile(path.join(output,name));manifest.files.push({path:name,bytes:b.length,sha256:sha(b)});}
await fs.writeFile(path.join(output,'ECONOMICS_MANIFEST.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({output,rows:rows.length,campaign_cpu_seconds:campaignCpu/1e9,native_cpu_seconds:nativeCpu/1e9,initial_cpu_seconds:initialCpu/1e9,documented_cpu_seconds:measuredCpu/1e9,files:manifest.files},null,2));
