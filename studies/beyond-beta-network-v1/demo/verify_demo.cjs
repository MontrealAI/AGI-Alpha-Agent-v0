// SPDX-License-Identifier: Apache-2.0
// Focused publication QA: local rendering, controls, responsive layout and offline operation.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright');
(async()=>{
  const draft=process.argv.includes('--draft');
  const executable=process.env.AGI_ALPHA_BROWSER||'/tmp/agi-alpha-autonomous-work-20261026/browser_runtime/chrome-headless-shell-linux64/chrome-headless-shell';
  const browser=await chromium.launch({headless:true,executablePath:executable});
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));
  let network=0;await page.route('http**/*',route=>{network++;return route.abort()});
  await page.goto('file://'+path.resolve(__dirname,'index.html'));
  if(!draft){
    checks.push({check:'frozen_results_loaded',passed:await page.evaluate(()=>window.BeyondBetaDemo.getState().loaded)});
    checks.push({check:'no_unbound_warning',passed:!(await page.locator('#data-warning').isVisible())});
    checks.push({check:'primary_zero_admissions_preserved',passed:await page.evaluate(()=>window.BeyondBetaDemo.getData().scenarios.every(s=>s.worlds===128&&s.policies.every(p=>p.alpha.admitted===0)))});
    checks.push({check:'development_witness_separate_and_negative',passed:await page.evaluate(()=>{const w=window.BeyondBetaDemo.getData().development_witness;return w.stages.length===6&&w.note.en.includes('not a typical outcome or fresh confirmation')&&w.result.en.includes('281,949.96')&&w.result.en.includes('failed economic return')})});
    checks.push({check:'english_pre_tax_label',passed:(await page.locator('[data-i18n="profitMedian"]').textContent()).includes('pre-tax')});
    checks.push({check:'sensitivity_selector_has_visible_default',passed:(await page.locator('#sensitivity-select').inputValue())==='0'&&(await page.locator('#sensitivity-select option:checked').textContent()).length>0});
    checks.push({check:'pricing_is_labeled_network_development',passed:(await page.locator('[data-i18n="pricingTitle"]').textContent()).includes('development')});
  }
  for(const scenario of ['conservative','central','favorable']){
    await page.locator('[data-scenario="'+scenario+'"]').click();
    checks.push({check:'scenario_'+scenario,passed:await page.evaluate(s=>window.BeyondBetaDemo.getState().scenario===s,scenario)});
    checks.push({check:'no_desktop_overflow_'+scenario,passed:await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)});
    if(!draft)checks.push({check:'executed_central_sensitivity_visible_'+scenario,passed:await page.locator('#sensitivity-table tbody tr').count()>=4&&(await page.locator('#sensitivity-note').textContent()).includes('central-policy')});
    if(!draft){
      const options=await page.locator('#policy-select option').evaluateAll(o=>o.map(x=>x.value));
      for(const option of options){
        await page.locator('#policy-select').selectOption(option);
        checks.push({check:'policy_'+scenario+'_'+option,passed:await page.evaluate(p=>window.BeyondBetaDemo.getState().policy===p,option)});
        const phases=await page.locator('#beta-phase option').evaluateAll(o=>o.map(x=>x.value));
        for(const phase of phases){
          await page.locator('#beta-phase').selectOption(phase);
          checks.push({check:'beta_phase_'+scenario+'_'+option+'_'+phase,passed:(await page.locator('#beta-baseline').textContent()).trim().length>0});
        }
        checks.push({check:'abc_accounting_bound_'+scenario+'_'+option,passed:await page.locator('#cost-a').textContent()!=='—'&&await page.locator('#cost-b').textContent()!=='—'&&await page.locator('#cost-c').textContent()!=='—'});
      }
    }
  }
  await page.locator('[data-scenario="central"]').click();
  if(!draft){
    await page.locator('#policy-select').selectOption('enterprise');
    await page.locator('#witness-section summary').click();
    checks.push({check:'development_detail_displays_six_recorded_stages',passed:await page.locator('#witness-stages .origin-step').count()===6});
    await page.locator('#witness-section').screenshot({path:path.join(__dirname,'qa','development-witness-en.png')});
    await page.locator('#witness-section summary').click();
  }
  const prefix=draft?'draft-':'';fs.mkdirSync(path.join(__dirname,'qa'),{recursive:true});
  await page.screenshot({path:path.join(__dirname,'qa',prefix+'desktop.png'),fullPage:!draft});
  const offer=await page.locator('#offer-price').textContent(),cash=await page.locator('#available-cash').textContent();
  await page.locator('#value-slider').evaluate(el=>{el.value='10000';el.dispatchEvent(new Event('input'))});
  checks.push({check:'analytic_threshold_does_not_mutate_frozen_results',passed:offer===await page.locator('#offer-price').textContent()&&cash===await page.locator('#available-cash').textContent()});
  await page.locator('#lang-fr').click();await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(__dirname,'qa',prefix+'mobile-fr.png'),fullPage:!draft});
  checks.push({check:'french_toggle',passed:await page.evaluate(()=>document.documentElement.lang==='fr')});
  if(!draft){
    checks.push({check:'french_pre_tax_label',passed:(await page.locator('[data-i18n="profitMedian"]').textContent()).includes('avant impôt')});
    await page.locator('#witness-section summary').click();
    checks.push({check:'french_development_witness',passed:(await page.locator('#witness-result').textContent()).includes('rendement économique négatif')});
    checks.push({check:'french_witness_no_mobile_overflow',passed:await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)});
    await page.locator('#witness-section').screenshot({path:path.join(__dirname,'qa','development-witness-fr.png')});
    await page.locator('#witness-section summary').click();
  }
  checks.push({check:'french_accounting_labels',passed:(await page.locator('[data-i18n="aTitle"]').textContent()).includes('Travail client')&&(await page.locator('[data-i18n="bTitle"]').textContent()).includes('Conservation')});
  checks.push({check:'no_mobile_overflow',passed:await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)});
  checks.push({check:'cash_svg_labels_inside_viewbox',passed:await page.evaluate(()=>{const svg=document.querySelector('#cash-chart svg');if(!svg)return false;const w=svg.viewBox.baseVal.width;return [...svg.querySelectorAll('text')].every(el=>{const b=el.getBBox();return b.x>=-0.5&&b.x+b.width<=w+0.5})})});
  const groups=await page.locator('#sensitivity-select option').count();
  if(groups){await page.locator('#sensitivity-select').selectOption(String(groups-1));checks.push({check:'sensitivity_control',passed:await page.locator('#sensitivity-table tbody tr').count()>0})}
  checks.push({check:'no_script_errors',passed:!errors.length,errors});
  checks.push({check:'no_network_dependency',passed:network===0,requests:network});
  const result={verifiedUTC:new Date().toISOString(),sourceSHA256:{html:crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'index.html'))).digest('hex'),data:crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,'demo_data.json'))).digest('hex')},scope:draft?'Draft template only, not result verification.':'Local publication rendering/interaction only; no validation of empirical demand or frontier capability.',checks,passed:checks.every(c=>c.passed)};
  fs.writeFileSync(path.join(__dirname,'qa',prefix+'verification.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({passed:result.passed,checks:checks.length,failed:checks.filter(c=>!c.passed),sourceSHA256:result.sourceSHA256}));await browser.close();if(!result.passed)process.exit(1);
})().catch(e=>{console.error(e.message);process.exit(1)});
