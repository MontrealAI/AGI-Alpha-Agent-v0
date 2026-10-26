// SPDX-License-Identifier: Apache-2.0
// Synthetic UI controls only. This helper never reads study inputs or outcomes.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {dirname,join,resolve} from 'node:path';
import {createRequire} from 'node:module';
import {performance} from 'node:perf_hooks';
import {conditionalPair,repaymentThreshold} from '../market/transfer-adapter.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const out=resolve(process.argv[2]||join(here,'ui-qa-synthetic'));
const moduleRoot=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES||'/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules';
const require=createRequire(import.meta.url);
const {chromium}=require(join(moduleRoot,'playwright'));
const executable=process.env.AGI_ALPHA_QA_BROWSER||'/tmp/agi-alpha-autonomous-work-20261026/browser_runtime/chrome-headless-shell-linux64/chrome-headless-shell';
const data=JSON.parse(await readFile(join(out,'equivalent-unknown.json'),'utf8'));
assert.equal(data.qaSynthetic,true,'Only explicitly synthetic control data is permitted');
const start=performance.now(),cpuStart=process.cpuUsage();
const result={schema:'agi-alpha-transfer-demo-ui-qa/v1',basis:'SYNTHETIC_UI_CONTROLS_ONLY',startedAt:new Date().toISOString(),tests:[],screenshots:[],consoleErrors:[],networkRequests:[],unknownCosts:{authoringUSD:null,modelInferenceUSD:null,toolsUSD:null,attentionUSD:null}};
const sha=x=>createHash('sha256').update(x).digest('hex');
await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:executable,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true,reducedMotion:'reduce'});
await context.route(/^https?:\/\//,async route=>{result.networkRequests.push(route.request().url());await route.abort();});
const page=await context.newPage();
page.setDefaultTimeout(5000);
page.on('pageerror',e=>result.consoleErrors.push(e.message));
page.on('console',m=>{if(m.type()==='error')result.consoleErrors.push(m.text());});
const open=async name=>{await page.goto(pathToFileURL(join(out,name+'.html')).href);await page.waitForFunction(()=>!!window.AGI_ALPHA_DEMO);};
const test=async(name,fn)=>{const at=performance.now();try{await fn();result.tests.push({name,status:'PASS',wallMs:performance.now()-at});}catch(error){result.tests.push({name,status:'FAIL',wallMs:performance.now()-at,error:error.stack});}};
const controls=async values=>{for(const [id,value]of Object.entries(values)){const el=page.locator('#'+id);const details=el.locator('xpath=ancestor::details[1]');if(await details.count()&&await details.getAttribute('open')===null)await details.locator('summary').click();const type=await el.getAttribute('type');if(type==='range')await el.evaluate((n,v)=>{n.value=String(v);n.dispatchEvent(new Event('input',{bubbles:true}));},value);else if(await el.evaluate(n=>n.tagName==='SELECT'))await el.selectOption(String(value));else await el.fill(String(value));}};
const screenshot=async name=>{await page.screenshot({path:join(out,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};

try{
await open('equivalent-unknown');
await test('Synthetic fixture visibly labeled; no injected source script executes',async()=>{
 assert.equal(await page.locator('#qaBanner').isVisible(),true);
 assert.equal(await page.evaluate(()=>globalThis.QA_INJECTION_EXECUTED||globalThis.QA_LINK_EXECUTED||false),false);
 assert.equal(await page.locator('a[href^="javascript:"]').count(),0);
 assert.equal(await page.locator('#heroFinding').textContent(),'SYNTHETIC UI CONTROL');
});
await test('Unknown complete costs remain blank, including explicit null scenario fields',async()=>{
 for(const id of ['costA','costB','costC','buildB','buildC'])assert.equal(await page.locator('#'+id).inputValue(),'');
 const state=await page.evaluate(()=>AGI_ALPHA_DEMO.getState());
 assert.equal(state.marketAudit.status,'COMPLETE_EQUIVALENT_ACCEPTED_WORK');
 assert.equal(state.marketAudit.economicDecision,'IDENTIFICATION_HOLD');
 await page.locator('#runMarket').click();
 assert.match(await page.locator('#marketError').textContent(),/construction and recurring cost/);
 assert.equal(await page.locator('#marketOutput').isVisible(),false);
});
await test('Complete handoff and conditional dispatch remain distinct',async()=>{
 await page.locator('#missionPick').selectOption('1');
 await page.locator('[data-arm="C"]').click();
 assert.match(await page.locator('#missionAccepted').textContent(),/Complete handoff accepted/);
 assert.equal(await page.locator('#unresolvedCount').textContent(),'1');
 assert.equal(await page.locator('#coreAccepted').textContent(),'Fail');
 assert.match(await page.locator('#callList').textContent(),/Dispatch unproved/);
 assert.match(await page.locator('#missionAction').textContent(),/unresolved/);
 await page.locator('#missionPick').selectOption('0');
 for(const arm of 'ABC'){await page.locator('[data-arm="'+arm+'"]').click();assert.match(await page.locator('#missionAction').textContent(),/Hold the update/);}
 assert.match(await page.locator('[data-arm="C"]').textContent(),/^C2/);
 assert.match(await page.locator('#primaryFinding').textContent(),/SYNTHETIC primary-failure/);
});
await test('Exact captured source displays inertly and downloads identical UTF-8 bytes',async()=>{
 await page.locator('#callList button').first().click();
 assert.equal(await page.locator('#sourceDrawer').getAttribute('open'),'');
 assert.equal(await page.locator('#sourcePick').inputValue(),'consumer');
 assert.equal(await page.locator('#sourceCode .highlight').count(),1);
 assert.match(await page.locator('#sourceCode').textContent(),/globalThis.QA_INJECTION_EXECUTED/);
 const event=page.waitForEvent('download');
 await page.locator('#sourceLinks button').click();
 const download=await event,downloadPath=join(out,'downloaded-source.txt');
 await download.saveAs(downloadPath);
 assert.equal(sha(await readFile(downloadPath)),data.missions[0].rawInput.sources.consumer.sha256);
 result.exactSourceSHA256=data.missions[0].rawInput.sources.consumer.sha256;
 const rawEvent=page.waitForEvent('download');await page.locator('#downloadRaw').click();
 const rawDownload=await rawEvent,rawPath=join(out,'downloaded-input.json');await rawDownload.saveAs(rawPath);
 assert.deepEqual(JSON.parse(await readFile(rawPath,'utf8')),data.missions[0].rawInput);
});
const base={costA:8,costB:3,costC:1,buildB:100,buildC:100,maintenance:0.50,buyers:12,cash:1000,reserve:200,price:40,demand:25,integration:10,delay:2,aiPrice:20,aiQuality:90,choiceModel:'deterministic',pricingPolicy:'empirical-grid',financing:'operating-surplus',seed:101};
for(const [name,overrides]of [
 ['baseline-explicit-costs',{}],
 ['delayed-cash-strong-ai',{cash:250,reserve:100,delay:26,price:20,demand:50,integration:100,aiPrice:5,aiQuality:99,seed:102}],
 ['zero-demand',{demand:0,seed:103}],
 ['logit-fixed-price',{choiceModel:'logit',pricingPolicy:'fixed',price:30,delay:4,seed:104}],
 ['seed-funded-price-response',{financing:'seed-funded',pricingPolicy:'cost-pass-through',price:50,seed:105}],
]){
 await test('Exact Node/browser market equality: '+name,async()=>{
   await controls({...base,...overrides});await page.locator('#runMarket').click();
   assert.equal(await page.locator('#marketError').textContent(),'');
   const state=await page.evaluate(()=>AGI_ALPHA_DEMO.getState());
   assert.ok(state.currentPair,'Browser produced no pair');
   const seed=Number(await page.locator('#seed').inputValue());
   const expected=conditionalPair(data.productionMarketRecord,state.currentScenario,seed);
   assert.deepEqual(state.currentPair,expected);
   const serialized=JSON.stringify(state.currentPair);
   result.engineComparisons??=[];
   result.engineComparisons.push({name,seed,exactOutputSHA256:sha(serialized),outputBytes:Buffer.byteLength(serialized)});
   assert.match(await page.locator('#marketOutcome').textContent(),/^C2/);
   assert.match(await page.locator('#marketOutcomeText').textContent(),/No complete commercial Flywheel/);
   assert.match(await page.locator('[data-i18n="buyerAllocation"]').textContent(),/C2/);
 });
}
await test('Finite input validation blocks negative complete cost',async()=>{
 await page.locator('#costC').fill('-1');await page.locator('#runMarket').click();
 assert.match(await page.locator('#marketError').textContent(),/construction and recurring cost/);
 assert.equal(await page.locator('#marketOutput').isVisible(),false);
 await controls(base);await page.locator('#runMarket').click();
});
await test('Independent threshold uses exact engine and grants no financing',async()=>{
 await controls({thresholdBuild:250,thresholdSaving:5,thresholdUpkeep:10});
 const expected=repaymentThreshold({investmentCostCents:25000,incrementalCostPerAcceptedCents:500,maintenanceCents:1000});
 assert.equal(await page.locator('#thresholdValue').textContent(),String(expected.acceptedJobsRequired));
 await controls({thresholdSaving:0});assert.equal(await page.locator('#thresholdValue').textContent(),'∞');
});
for(const [device,width,height]of [['desktop',1440,1000],['tablet',834,1112],['phone',390,844]]){
 for(const language of ['en','fr']){
  await test(device+' '+language+' interaction, layout and preserved evidence',async()=>{
   await page.setViewportSize({width,height});await page.locator(language==='en'?'#langEn':'#langFr').click();
   assert.equal(await page.locator('html').getAttribute('lang'),language);
   const size=await page.evaluate(()=>({innerWidth,scrollWidth:document.documentElement.scrollWidth}));
   assert.ok(size.scrollWidth<=size.innerWidth+1,'Document overflows: '+JSON.stringify(size));
   assert.match(await page.locator('#comparisonRows').textContent(),/C2/);
   assert.equal(await page.locator('#primaryRecord').isVisible(),true);
   await page.evaluate(()=>scrollTo(0,0));await screenshot(device+'-'+language+'-hero');
   await page.locator('#mission').evaluate(n=>scrollTo(0,n.getBoundingClientRect().top+scrollY-92));await screenshot(device+'-'+language+'-mission');
   await page.locator('#marketOutput').evaluate(n=>scrollTo(0,n.getBoundingClientRect().top+scrollY-92));await screenshot(device+'-'+language+'-market');
   await page.locator('#chartMetric').selectOption('earnedAvailableCents');
   assert.match(await page.locator('#cashChart').getAttribute('aria-label'),language==='fr'?/exploitation/:/operations/);
   await page.locator('#chartMetric').selectOption('cashCents');
  });
 }
}
for(const name of ['blocked-complete-handoff','missing-record']){
 await test(name+' blocks market but permits separate arithmetic',async()=>{
  await open(name);
  assert.equal(await page.locator('#runMarket').isDisabled(),true);
  assert.equal(await page.locator('#marketOutput').isVisible(),false);
  await controls({thresholdBuild:50,thresholdSaving:5,thresholdUpkeep:0});
  assert.equal(await page.locator('#thresholdValue').textContent(),'10');
  await page.locator('#langFr').click();assert.equal(await page.locator('#runMarket').isDisabled(),true);
  await screenshot(name+'-fr');
 });
}
await test('Offline execution has no external request or console exception',async()=>{
 assert.deepEqual(result.networkRequests,[]);assert.deepEqual(result.consoleErrors,[]);
});
}finally{
 await context.close();await browser.close();
 const cpu=process.cpuUsage(cpuStart);
 result.resources={nodeProcessCpuSeconds:(cpu.user+cpu.system)/1e6,wallSeconds:(performance.now()-start)/1000,browserChildCpuSeconds:null,completeCostUSD:null};
 result.finishedAt=new Date().toISOString();result.passed=result.tests.filter(x=>x.status==='PASS').length;result.failed=result.tests.filter(x=>x.status==='FAIL').length;
 result.boundary='UI controls and exact engine replay only. Synthetic source/acceptance records are never production evidence, study results, or demand calibration.';
 await writeFile(join(out,'qa-report.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({passed:result.passed,failed:result.failed,failures:result.tests.filter(x=>x.status==='FAIL'),report:join(out,'qa-report.json'),engineComparisons:result.engineComparisons,resources:result.resources},null,2));
 process.exitCode=result.failed?1:0;
}
