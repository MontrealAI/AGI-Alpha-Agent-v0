// SPDX-License-Identifier: Apache-2.0
// Released evidence UI validation. Exploratory browser scenarios do not replace campaign results.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {dirname,join,resolve} from 'node:path';
import {createRequire} from 'node:module';
import {performance} from 'node:perf_hooks';
import {inspectAcceptedAB,conditionalAB} from '../market/accepted-ab-diagnostic/accepted-ab.mjs';
import {repaymentThreshold} from '../market/transfer-adapter.mjs';

const here=dirname(fileURLToPath(import.meta.url)),study=resolve(here,'..');
const dataFile=resolve(process.argv[2]||join(here,'demo-data.json'));
const htmlFile=resolve(process.argv[3]||join(here,'AGI_ALPHA_Productive_Advantage.html'));
const out=resolve(process.argv[4]||join(here,'ui-qa-final'));
const dataBytes=await readFile(dataFile),data=JSON.parse(dataBytes);
assert.notEqual(data.qaSynthetic,true,'Final QA requires released actual evidence');
assert.ok(data.acceptedABDiagnosticProduction,'Released A/B diagnostic production bridge required');
// This check prevents exploratory runs before the separate protocol is frozen.
const freeze=JSON.parse(await readFile(join(study,'market/accepted-ab-diagnostic/freeze.json'),'utf8'));
assert.ok(freeze&&typeof freeze==='object','Separate A/B freeze required');
const moduleRoot=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES||'/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {chromium}=createRequire(import.meta.url)(join(moduleRoot,'playwright'));
const executable=process.env.AGI_ALPHA_QA_BROWSER||'/tmp/agi-alpha-autonomous-work-20261026/browser_runtime/chrome-headless-shell-linux64/chrome-headless-shell';
const sha=x=>createHash('sha256').update(x).digest('hex');
const canonical=x=>Array.isArray(x)?x.map(canonical):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])])):x;
const canonicalSHA=x=>sha(JSON.stringify(canonical(x)));
const start=performance.now(),cpuStart=process.cpuUsage();
const result={schema:'agi-alpha-transfer-demo-final-ui-qa/v1',basis:'RELEASED_EVIDENCE_PRESENTATION_AND_EXPLORATORY_UI_REPLAY',dataSHA256:sha(dataBytes),htmlSHA256:sha(await readFile(htmlFile)),startedAt:new Date().toISOString(),tests:[],screenshots:[],consoleErrors:[],networkRequests:[],resultDownloads:[],sourceDownloads:[],engineComparisons:[],unknownMonetaryCosts:{authoringUSD:null,inferenceUSD:null,toolsUSD:null,attentionUSD:null}};
await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:executable,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true,reducedMotion:'reduce'});
await context.route(/^https?:\/\//,async route=>{result.networkRequests.push(route.request().url());await route.abort();});
const page=await context.newPage();page.setDefaultTimeout(8000);
page.on('pageerror',e=>result.consoleErrors.push(e.message));
page.on('console',m=>{if(m.type()==='error')result.consoleErrors.push(m.text());});
const test=async(name,fn)=>{const at=performance.now();try{await fn();result.tests.push({name,status:'PASS',wallMs:performance.now()-at});}catch(error){result.tests.push({name,status:'FAIL',wallMs:performance.now()-at,error:error.stack});}};
const controls=async values=>{for(const [id,value]of Object.entries(values)){const el=page.locator('#'+id),details=el.locator('xpath=ancestor::details[1]');if(await details.count()&&await details.getAttribute('open')===null)await details.locator('summary').click();const type=await el.getAttribute('type');if(type==='range')await el.evaluate((n,v)=>{n.value=String(v);n.dispatchEvent(new Event('input',{bubbles:true}));},value);else if(await el.evaluate(n=>n.tagName==='SELECT'))await el.selectOption(String(value));else await el.fill(String(value));}};
const screenshot=async name=>{await page.screenshot({path:join(out,name+'.png'),fullPage:false});result.screenshots.push(name+'.png');};
const saveDownload=async(selector,name)=>{await new Promise(resolve=>setTimeout(resolve,350));const event=page.waitForEvent('download');await page.locator(selector).click();const d=await event,p=join(out,name);await d.saveAs(p);return readFile(p);};
try{
 await page.goto(pathToFileURL(htmlFile).href);await page.waitForFunction(()=>!!window.AGI_ALPHA_DEMO);
 await test('Released data identity and exact source-module identities',async()=>{
  assert.equal(await page.locator('#qaBanner').isVisible(),false);
  assert.equal(canonicalSHA(await page.evaluate(()=>AGI_ALPHA_DEMO.data)),canonicalSHA(data));
  const hashes=await page.evaluate(()=>AGI_ALPHA_DEMO.engine.sourceHashes);
  assert.equal(Object.keys(hashes).length,4);
  for(const [relative,digest]of Object.entries(hashes))assert.equal(sha(await readFile(join(study,relative))),digest,relative);
  result.moduleHashes=hashes;
 });
 await test('Actual four-mission handoffs and preserved primary failure remain separate',async()=>{
  assert.equal(await page.locator('#statMissions').textContent(),'4');
  const counts=await page.locator('#comparisonRows tr td:nth-child(2)').allTextContents();
  assert.deepEqual(counts,['4 / 4','4 / 4','3 / 4']);
  assert.match(await page.locator('#primaryFinding').textContent(),/0\/6 complete handoffs/);
  assert.match(await page.locator('#primaryFinding').textContent(),/SciPy eigvals/);
  assert.match(await page.locator('#heroScope').textContent(),/unknown/);
 });
 for(const [index,m]of data.missions.entries()){
  await test('Exact sealed result downloads: '+m.id,async()=>{
   await page.locator('#missionPick').selectOption(String(index));
   for(const arm of ['A','B','C']){
    await page.locator('[data-arm="'+arm+'"]').click();
    const bytes=await saveDownload('#downloadResult',m.id+'-'+arm+'-result.json');
    const downloaded=JSON.parse(bytes);assert.deepEqual(downloaded,m.arms[arm].sealedResult);
    assert.equal(canonicalSHA(downloaded),m.arms[arm].resultSha256);
    result.resultDownloads.push({mission:m.id,arm,canonicalSHA256:canonicalSHA(downloaded)});
   }
   const raw=JSON.parse(await saveDownload('#downloadRaw',m.id+'-raw.json'));assert.deepEqual(raw,m.rawInput);
  });
  await test('Exact captured source view/download: '+m.id,async()=>{
   await page.locator('#sourceDrawer').evaluate(n=>{n.open=true;});
   const sourceId=m.rawInput.consumer.source,source=m.rawInput.sources[sourceId];
   await page.locator('#sourcePick').selectOption(sourceId);
   assert.match(await page.locator('#sourceIdentity').textContent(),new RegExp(source.sha256));
   const bytes=await saveDownload('#sourceLinks button',m.id+'-source.txt');
   assert.equal(sha(bytes),source.sha256);
   result.sourceDownloads.push({mission:m.id,sourceId,sha256:sha(bytes)});
  });
 }
 await test('C2 F03 complete handoff rejection remains visible',async()=>{
  await page.locator('#missionPick').selectOption('2');await page.locator('[data-arm="C"]').click();
  assert.match(await page.locator('#missionAccepted').textContent(),/not accepted/);
  assert.match(await page.locator('#missionNotes').textContent(),/two NumPy/);
  assert.match(await page.locator('#missionAction').textContent(),/unresolved/);
 });
 await test('Original three-arm gate persists beside a distinct accepted A/B diagnostic',async()=>{
  const state=await page.evaluate(()=>AGI_ALPHA_DEMO.getState());
  assert.notEqual(state.marketAudit.status,'COMPLETE_EQUIVALENT_ACCEPTED_WORK');
  assert.deepEqual(state.diagnosticAudit,inspectAcceptedAB(data.acceptedABDiagnosticProduction));
  assert.equal(state.diagnosticAudit.status,'COMPLETE_AB_ACCEPTED_WORK');
  assert.equal(state.diagnosticAudit.economicDecision,'IDENTIFICATION_HOLD');
  assert.equal(state.marketMode,'accepted-ab');
  assert.equal(await page.locator('#marketGate.blocked').count(),1);
  assert.equal(await page.locator('#diagnosticNotice').isVisible(),true);
  for(const id of ['costFieldB','costFieldC','buildFieldC'])assert.equal(await page.locator('#'+id).isVisible(),false);
  assert.equal(await page.locator('#costLabelA').textContent(),'A = B · USD');
  assert.equal(await page.locator('#financing').isDisabled(),true);
  await page.locator('#marketMode').selectOption('three-arm');assert.equal(await page.locator('#runMarket').isDisabled(),true);
  await controls({thresholdBuild:50,thresholdSaving:5,thresholdUpkeep:0});
  assert.equal(await page.locator('#thresholdValue').textContent(),String(repaymentThreshold({investmentCostCents:5000,incrementalCostPerAcceptedCents:500}).acceptedJobsRequired));
  await page.locator('#marketMode').selectOption('accepted-ab');
 });
 await test('Unknown A/B costs cannot be replaced by zero or omitted',async()=>{
  await controls({costA:'',buildB:''});await page.locator('#runMarket').click();
  assert.match(await page.locator('#marketError').textContent(),/construction and recurring cost/);
  assert.equal(await page.locator('#marketOutput').isVisible(),false);
  await page.locator('#resetMarket').click();
 });
 const base={costA:5,buildB:100,maintenance:0.50,buyers:12,cash:1000,reserve:200,price:20,demand:25,integration:10,delay:2,aiPrice:20,aiQuality:90,choiceModel:'deterministic',pricingPolicy:'fixed',seed:301};
 for(const [name,overrides]of [
  ['released-default-structure',{}],
  ['low-friction-service',{costA:1,price:15,integration:0,demand:50,seed:302}],
  ['delayed-cash-strong-ai',{cash:250,reserve:100,delay:26,price:20,demand:50,integration:100,aiPrice:5,aiQuality:99,seed:303}],
  ['zero-demand',{demand:0,seed:304}],
  ['logit-price-response',{choiceModel:'logit',pricingPolicy:'cost-pass-through',price:30,delay:4,seed:305}],
 ]){
  await test('Full A/B browser output equals exact Node adapter: '+name,async()=>{
   await controls({...base,...overrides});await page.locator('#runMarket').click();
   assert.equal(await page.locator('#marketError').textContent(),'');
   const state=await page.evaluate(()=>AGI_ALPHA_DEMO.getState());assert.ok(state.currentPair);
   const seed=Number(await page.locator('#seed').inputValue());
   const expected=conditionalAB(data.acceptedABDiagnosticProduction,state.currentScenario,seed);
   assert.deepEqual(state.currentPair,expected);
   assert.deepEqual(Object.keys(state.currentPair.arms),['A','B']);
   assert.equal(state.currentScenario.costs.A.completeRecurringCostCents,state.currentScenario.costs.B.completeRecurringCostCents);
   assert.equal(state.currentPair.arms.B.summary.investmentWeek,null);
   assert.equal(state.currentPair.differences.B_minus_A_profitCents,0);
   assert.deepEqual(await page.locator('#marketCards .arm-badge').allTextContents(),['A','B']);
   assert.equal(await page.locator('#cashChart path').count(),2);
   assert.deepEqual(await page.locator('#chartLegend span').allTextContents(),['A','B']);
   assert.match(await page.locator('#marketOutcomeText').textContent(),/C2 is excluded/);
   result.engineComparisons.push({name,seed,outputSHA256:sha(JSON.stringify(state.currentPair)),outputBytes:Buffer.byteLength(JSON.stringify(state.currentPair)),AProfitCents:state.currentPair.arms.A.summary.profitCents,BProfitCents:state.currentPair.arms.B.summary.profitCents,BInvestmentWeek:state.currentPair.arms.B.summary.investmentWeek});
  });
 }
 await controls({...base,costA:1,price:15,integration:0,demand:50,seed:302});await page.locator('#runMarket').click();
 await page.locator('#missionPick').selectOption('0');await page.locator('[data-arm="B"]').click();
 for(const [device,width,height]of [['desktop',1440,1000],['tablet',834,1112],['phone',390,844]])for(const lang of ['en','fr']){
  await test(device+' '+lang+' complete layout and interaction',async()=>{
   await page.setViewportSize({width,height});await page.locator(lang==='en'?'#langEn':'#langFr').click();
   assert.equal(await page.locator('html').getAttribute('lang'),lang);
   const size=await page.evaluate(()=>({innerWidth,scrollWidth:document.documentElement.scrollWidth}));
   assert.ok(size.scrollWidth<=size.innerWidth+1,'Document overflow: '+JSON.stringify(size));
   assert.deepEqual(await page.locator('#marketCards .arm-badge').allTextContents(),['A','B']);
   await page.evaluate(()=>scrollTo(0,0));await screenshot(device+'-'+lang+'-hero');
   await page.locator('#mission').evaluate(n=>scrollTo(0,n.getBoundingClientRect().top+scrollY-92));await screenshot(device+'-'+lang+'-mission');
   await page.locator('#marketOutput').evaluate(n=>scrollTo(0,n.getBoundingClientRect().top+scrollY-92));await screenshot(device+'-'+lang+'-market');
   await page.locator('#chartMetric').selectOption('earnedAvailableCents');assert.equal(await page.locator('#cashChart path').count(),2);
   await page.locator('#chartMetric').selectOption('cashCents');
  });
 }
 await test('Offline execution is free of external requests, console errors and data drift',async()=>{
  assert.deepEqual(result.networkRequests,[]);assert.deepEqual(result.consoleErrors,[]);
  assert.equal(sha(await readFile(dataFile)),result.dataSHA256,'Final data changed during validation');
 });
}finally{
 await context.close();await browser.close();const cpu=process.cpuUsage(cpuStart);
 result.resources={nodeProcessCpuSeconds:(cpu.user+cpu.system)/1e6,wallSeconds:(performance.now()-start)/1000,browserChildCpuSeconds:null,completeCostUSD:null};
 result.finishedAt=new Date().toISOString();result.passed=result.tests.filter(t=>t.status==='PASS').length;result.failed=result.tests.filter(t=>t.status==='FAIL').length;
 result.boundary='UI evidence fidelity and exploratory A/B replay only. The original 166-cell three-arm campaign stays gated; these five scenarios are not registered campaign observations or additional customer missions.';
 await writeFile(join(out,'qa-report.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({passed:result.passed,failed:result.failed,failures:result.tests.filter(x=>x.status==='FAIL'),engineComparisons:result.engineComparisons,report:join(out,'qa-report.json'),resources:result.resources},null,2));
 process.exitCode=result.failed?1:0;
}
