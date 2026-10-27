// SPDX-License-Identifier: Apache-2.0
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
(async()=>{
 const target=path.resolve(process.argv[2]||path.join(__dirname,'index.html'));
 const dir=process.env.ASE_DEMO_QA_DIR||path.join(os.tmpdir(),'invent_demo_qa');fs.mkdirSync(dir,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.ASE_CHROMIUM_PATH?{executablePath:process.env.ASE_CHROMIUM_PATH}:{})});
 const page=await browser.newPage({viewport:{width:1200,height:850}}),errors=[],network=[],invalid=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{if(/^https?:/.test(route.request().url())){network.push(route.request().url());return route.abort()}return route.continue()});
 await page.goto('file://'+target);
 const commercialAudit=await page.evaluate(()=>{const c=DATA.view?.scenarios?.find(s=>s.id==='central');if(!c)return{present:false};const b=c.policies.optimized_beta,q=b.matched_collected_prices.per_project,sections=[...document.querySelectorAll('main>section')].map(s=>s.id);return{present:true,default_policy:policy,section_order:sections,matched_reference_visible:$('resultLeadRows').textContent.includes(money(q.modeled_human_service_reference.mean)),matched_charge_visible:$('resultLeadRows').textContent.includes(money(q.gross_offered_price.mean)),beta_profit_visible:$('resultLeadRows').textContent.includes(money(b.stats.profit.mean)),operating_surplus_visible:$('commercialCashKpis').textContent.includes(money(b.commercial_cash.endpoints.operating_horizon.metrics.retained_operating_cash_above_seed.mean)),cash_before_emergence:sections.indexOf('capital')<sections.indexOf('paidWork'),optional_after_sharing:sections.indexOf('optionalInvestment')>sections.indexOf('network')}});
 if(commercialAudit.present){assert.equal(commercialAudit.default_policy,'optimized_beta');assert.equal(commercialAudit.matched_reference_visible,true);assert.equal(commercialAudit.matched_charge_visible,true);assert.equal(commercialAudit.beta_profit_visible,true);assert.equal(commercialAudit.operating_surplus_visible,true);assert.equal(commercialAudit.cash_before_emergence,true);assert.equal(commercialAudit.optional_after_sharing,true)}
 for(const fault of ['none','objective','capacity','suboptimal','shared_spec']){
   await page.selectOption('#faultMode',fault);const result=await page.evaluate(()=>latestResult);
   assert.equal(result.independent_check.accepted,fault==='none');
   if(fault==='shared_spec')assert.equal(result.shared_spec_check.accepted,true);
 }
 await page.locator('#infeasibleInstance').click();assert.equal(await page.evaluate(()=>latestResult.candidate),null);await page.locator('#resetInstance').click();
 const traceAudit=await page.evaluate(()=>{
   const cases=DATA.lifecycle?.cases||[];let steps=0,denied=0,assessments=0;const failures=[];
   for(const c of cases){
     $('lifecycleCase').value=c.id;$('lifecycleCase').dispatchEvent(new Event('change'));
     for(let i=0;i<c.steps.length;i++){
       $('lifecycleStep').value=i;$('lifecycleStep').dispatchEvent(new Event('input'));steps++;
       const e=c.steps[i],text=$('traceDecision').textContent;
       if(e.allowed===false){denied++;if(text!==tr('traceDenied'))failures.push(c.id+':denied:'+i)}
       if(e.allowed===true&&text!==tr('traceAllowed'))failures.push(c.id+':allowed:'+i);
       if(e.assessment){assessments++;if(!$('traceAlphaFacts').textContent.includes(money(e.assessment.expected_prospective_net_alpha,2)))failures.push(c.id+':assessment:'+i)}
       if($('traceBefore').textContent!==JSON.stringify(e.before??null,null,2))failures.push(c.id+':before:'+i);
       if($('traceAfter').textContent!==JSON.stringify(e.after??null,null,2))failures.push(c.id+':after:'+i);
     }
   }
   return{cases:cases.length,steps,denied,assessments,failures};
 });assert.deepEqual(traceAudit.failures,[]);
 let paidCaseCount=0,paidReceiptCount=0,fundedIllustrations=0;
 const scenarios=await page.locator('#scenario option').evaluateAll(es=>es.map(e=>e.value));
 const policies=await page.locator('#policy option').evaluateAll(es=>es.map(e=>e.value));
 for(const scenario of scenarios){
   await page.selectOption('#scenario',scenario);
   for(const policy of policies){
     await page.selectOption('#policy',policy);
     const paidAudit=await page.evaluate(()=>{let cases=0,receipts=0;const errors=[];for(const c of paidCases()){$('paidJobCase').value=c.id;$('paidJobCase').dispatchEvent(new Event('change'));cases++;receipts+=(c.receipts||[]).length;if($('receiptRows').children.length!==(c.receipts||[]).length)errors.push(c.id+':missing-rows');if(c.receipt_audit.duplicate_ids)errors.push(c.id+':duplicate-activity');if(c.receipt_audit.source_A_recharged===true)errors.push(c.id+':source-recharged')}return{cases,receipts,errors}});paidCaseCount+=paidAudit.cases;paidReceiptCount+=paidAudit.receipts;assert.deepEqual(paidAudit.errors,[]);
     await page.locator('#priceMonth').evaluate(e=>{e.value=e.max;e.dispatchEvent(new Event('input'))});
     await page.locator('#priceInspect').evaluate(e=>{e.value=e.max;e.dispatchEvent(new Event('input'))});
     await page.locator('#month').evaluate(e=>{e.value=e.max;e.dispatchEvent(new Event('input'))});
     if(await page.locator('#illustrationControl').isVisible()){await page.selectOption('#illustrationChoice','funded');fundedIllustrations++;const fundedAudit=await page.evaluate(()=>{const c=paidCases().find(c=>c.raw_trace?.events?.some(e=>e.kind==='retention_purchase'));if(!c)return null;$('paidJobCase').value=c.id;$('paidJobCase').dispatchEvent(new Event('change'));return{rows:$('receiptRows').children.length,expected:c.receipts.length,duplicate_ids:c.receipt_audit.duplicate_ids,recharged:c.receipt_audit.source_A_recharged}});if(fundedAudit){assert.equal(fundedAudit.rows,fundedAudit.expected);assert.equal(fundedAudit.duplicate_ids,0);assert.notEqual(fundedAudit.recharged,true)}await page.selectOption('#illustrationChoice','median')}
     await page.locator('#economyTraceTab').click();
     const eventCount=await page.evaluate(()=>traceCases()[0]?.steps.length||0);
     if(eventCount)await page.locator('#lifecycleStep').evaluate(e=>{e.value=e.max;e.dispatchEvent(new Event('input'))});
     if(/\b(NaN|undefined|Infinity)\b/.test(await page.locator('body').innerText()))invalid.push(scenario+'/'+policy);
   }
 }
 const sensitivityAudit=await page.evaluate(()=>{const rows=DATA.view?.sensitivity?.cases||[],failures=[];for(const row of rows){const button=[...$('stressRows').querySelectorAll('[data-stress]')].find(e=>e.dataset.stress===row.name);if(!button){failures.push(row.name+':missing');continue}button.click();if(JSON.parse($('stressRaw').textContent).name!==row.name)failures.push(row.name+':selection');if($('stressRows').children.length!==rows.length)failures.push(row.name+':row-loss')}return{cases:rows.length,compound_cases:rows.filter(r=>r.compound).length,failures,complete:DATA.view?.sensitivity?.complete||false}});assert.deepEqual(sensitivityAudit.failures,[]);if(path.basename(target)==='index.html'){assert.equal(sensitivityAudit.complete,true);assert.equal(sensitivityAudit.cases,19)}
 const linkedAudit=await page.evaluate(()=>{const d=linkedTrace();if(!d?.source_job)return{present:false,basis:d?.basis||null};return{present:true,basis:d.basis,scenario:d.scenario,world:d.world,visible:!$('linkedExample').hidden,badge:$('linkedBadge').textContent,expectedBadge:tr(d.basis==='DIRECTED_QA_FIXTURE_NOT_COMMERCIAL_EVIDENCE'?'linkedFixtureBadge':d.basis.startsWith('SELECTED_EXPLORATORY')?'linkedExploratoryBadge':'linkedPrimaryBadge'),primary_hash_matches:d.primary_confirmation_config_sha256===DATA.view.config_sha256,source_A_recharged:d.retention_purchase.source_job_construction_recharged,source_is_true_collected:d.source_job.true_useful_for_analysis_only&&d.source_job.net_customer_receipts_after_refund_obligations>0,fresh_is_useful:d.first_useful_fresh_recipient_job.true_useful_for_analysis_only===true,cash_rows:$('linkedCashRows').children.length,expected_cash_rows:d.monthly_cash_reserve_and_beta.length}});
 if(linkedAudit.present){assert.equal(linkedAudit.visible,true);assert.equal(linkedAudit.badge,linkedAudit.expectedBadge);assert.equal(linkedAudit.primary_hash_matches,true);assert.equal(linkedAudit.source_A_recharged,false);assert.equal(linkedAudit.source_is_true_collected,true);assert.equal(linkedAudit.fresh_is_useful,true);assert.equal(linkedAudit.cash_rows,linkedAudit.expected_cash_rows)}
 const allLinkedAudits=await page.evaluate(()=>{const out=[];for(const option of [...$('linkedChoice').options]){if(option.disabled)continue;$('linkedChoice').value=option.value;$('linkedChoice').dispatchEvent(new Event('change'));const d=linkedTrace();out.push({kind:option.value,basis:d.basis,source_A_recharged:d.retention_purchase.source_job_construction_recharged,fresh_is_useful:d.first_useful_fresh_recipient_job.true_useful_for_analysis_only===true,paired_profit:d.paired_network_minus_beta.net_profit,displayed:$('linkedPaired').textContent.includes(money(d.paired_network_minus_beta.net_profit,2))})}if(DATA.exploratory_trace){$('linkedChoice').value='exploratory';$('linkedChoice').dispatchEvent(new Event('change'))}return out});for(const audit of allLinkedAudits){assert.equal(audit.source_A_recharged,false);assert.equal(audit.fresh_is_useful,true);assert.equal(audit.displayed,true)}
 const diagnosticAudit=await page.evaluate(()=>{const d=DATA.controller_diagnostic;if(!d)return{present:false};return{present:true,worlds:d.worlds,histories:d.manifest.history_count,seed:d.seed,rows:$('diagnosticRows').children.length,audit_status:d.audit_status,unchanged_actual_capability:d.design.actual_capability_cost_demand_tests_and_beta_unchanged,useful_reuse_probability:d.arms.posterior_coherent_network.probability_useful_recipient_use,negative_vs_beta_probability:d.paired.posterior_network_vs_beta_probability_negative,feedback_probability:d.paired.probability_operating_funded_paid_job_feedback,mean_change_visible:$('diagnosticConclusion').textContent.includes(money(d.paired.posterior_vs_frozen_network_net_profit.mean,2))}});if(path.basename(target)==='index.html'){assert.equal(diagnosticAudit.present,true);assert.equal(diagnosticAudit.worlds,100);assert.equal(diagnosticAudit.histories,300);assert.equal(diagnosticAudit.rows,3);assert.equal(diagnosticAudit.audit_status,'PASS');assert.equal(diagnosticAudit.unchanged_actual_capability,true);assert.equal(diagnosticAudit.mean_change_visible,true)}
 if(scenarios.length){
   await page.selectOption('#scenario',scenarios.includes('central')?'central':scenarios[0]);await page.selectOption('#policy','optimized_beta');
   await page.locator('#resultLead').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,'commercial_en.png'),fullPage:false});
   await page.locator('#commercialCashKpis').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,'cash_en.png'),fullPage:false});
   await page.locator('#market').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,'economics_en.png'),fullPage:false});
 }
 if(linkedAudit.present){await page.locator('#linkedExample').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,'receipt_linked_en.png'),fullPage:false})}
 if(traceAudit.cases){await page.locator('#localTraceTab').click();const id=await page.evaluate(()=>DATA.lifecycle.cases[0].id);await page.selectOption('#lifecycleCase',id);await page.locator('#lifecycleStep').evaluate(e=>{e.value=Math.min(2,+e.max);e.dispatchEvent(new Event('input'))});await page.locator('#network').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,'network_en.png'),fullPage:false})}
 await page.locator('#mechanism').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(dir,'mechanism_en.png'),fullPage:false});
 await page.screenshot({path:path.join(dir,'desktop_en.png'),fullPage:false});
 await page.locator('#fr').click();
 if(scenarios.includes('favorable')){await page.selectOption('#scenario','favorable');await page.selectOption('#policy','optimized_network');if(await page.locator('#illustrationControl').isVisible())await page.selectOption('#illustrationChoice','funded')}
 await page.setViewportSize({width:390,height:844});
 const overflow=await page.evaluate(()=>document.body.scrollWidth>innerWidth);
 await page.screenshot({path:path.join(dir,'mobile_fr.png'),fullPage:false});
 const duplicateIds=await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.filter((id,i)=>ids.indexOf(id)!==i)});
 const report={target,commercial_first:commercialAudit,mechanism_fault_modes:5,infeasible_case:true,lifecycle:traceAudit,paid_work_cases_exercised:paidCaseCount,related_receipt_rows_exercised:paidReceiptCount,economic_scenarios:scenarios.length,economic_policies:policies.length,funded_illustrations_exercised:fundedIllustrations,receipt_linked_example:linkedAudit,all_receipt_examples:allLinkedAudits,exploratory_diagnostic:diagnosticAudit,sensitivity:sensitivityAudit,languages:['en','fr'],network_requests:network,errors,invalid_displays:invalid,duplicate_ids:duplicateIds,mobile_horizontal_overflow:overflow,passed:!network.length&&!errors.length&&!invalid.length&&!overflow&&!duplicateIds.length};
 fs.writeFileSync(path.join(__dirname,'qa_report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();if(!report.passed)process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});
