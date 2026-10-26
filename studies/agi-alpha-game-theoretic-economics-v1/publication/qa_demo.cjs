// SPDX-License-Identifier: Apache-2.0
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const {chromium} = require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES + '/playwright');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'review', 'demo-qa');
fs.mkdirSync(output, {recursive:true});
const findings = [], errors = [], externalRequests = [], downloads=[];
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function check(name, condition, detail={}) {
  findings.push({name, pass:!!condition, ...detail});
  if (!condition) throw Error(name);
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.STUDY_CHROMIUM,args:['--no-sandbox','--disable-background-networking']});
  const context=await browser.newContext({viewport:{width:1440,height:1050},acceptDownloads:true});
  await context.route('**/*',route=>{
    if (/^https?:/.test(route.request().url())) {externalRequests.push(route.request().url());return route.abort();}
    return route.continue();
  });
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));
  const file=path.join(root,'deliverables','AGI_ALPHA_Game_Theoretic_Laboratory.html');
  await page.goto('file://'+file); await page.waitForFunction(()=>!!window.currentStudyRun);
  check('Canonical observed collections remain zero',await page.evaluate(()=>window.currentStudyRun.arms.B.canonical.cash.summary.observed.revenue===0));
  check('B and C remain identical under matched economics',await page.evaluate(()=>window.currentStudyRun.causal.B_C_behaviorallyIdentical));
  for(const language of ['en','fr']){
    await page.click('#'+language);
    check('Language '+language,await page.getAttribute('html','lang')===language);
    for(const tab of ['evidence','market','history','sources']){
      await page.click('[data-tab="'+tab+'"]');
      check('No horizontal overflow '+language+' '+tab,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      if(language==='en'||tab==='market')await page.screenshot({path:path.join(output,language+'-'+tab+'.png'),fullPage:true});
    }
  }
  await page.click('#en'); await page.click('[data-tab="evidence"]');
  const expected=JSON.parse(fs.readFileSync(path.join(root,'production','joint-summary.json'))).packets;
  for(const row of expected){
    await page.selectOption('#packetChoice',row.mission_id);
    const pending=page.waitForEvent('download');await page.click('#downloadPacket');const download=await pending;
    const dest=path.join(output,download.suggestedFilename());await download.saveAs(dest);
    const actual=sha(fs.readFileSync(dest));check('Exact executed packet '+row.mission_id,actual===row.sha256);
    downloads.push({filename:download.suggestedFilename(),sha256:actual});
  }
  await page.click('[data-tab="market"]');
  await page.selectOption('#pricing','fixed');
  await page.selectOption('#targetPrice','500');
  check('Fixed target and cost floor visible in actual interface',await page.evaluate(()=>window.currentStudyRun.config.pricingPolicy==='fixed'&&window.currentStudyRun.config.initialPriceCents===500&&window.currentStudyRun.arms.A.histories.prices.every(p=>p.enterpriseCents>=500)));
  await page.selectOption('#basis','adoption-only');
  await page.selectOption('#funding','seed-funded');
  await page.locator('#integration').fill('0');await page.locator('#integration').dispatchEvent('input');
  check('Prospective and seed regimes remain explicit',await page.evaluate(()=>window.currentStudyRun.config.investmentCostBasis==='adoption-only'&&window.currentStudyRun.config.investmentFunding==='seed-funded'&&window.currentStudyRun.config.integrationCents===0));
  await page.selectOption('#preset','reference-assumptions');
  await page.selectOption('#preset','diagnostic-predeclared');
  check('Predeclared diagnostic reproduces actual frozen path',await page.evaluate(()=>window.currentStudyRun.seed===2001&&window.currentStudyRun.arms.B.summary.profitCents===12265&&window.currentStudyRun.arms.B.summary.assetUses===17&&window.currentStudyRun.causal.B_minus_A_profitCents===13656));
  check('Funding ceiling keeps discovery unpriced',await page.evaluate(()=>window.currentFundingView.terminal.fundingCeilingBeforeUnpricedDiscoveryCents===12265&&window.currentFundingView.allInSpendableResourcesIdentified===false&&window.currentFundingView.unpricedIncrementalDiscoveryCostCents===null));
  check('Buyer offers can be inspected in the actual interface',await page.locator('#buyerOffers tr').count()>0);
  check('Reserve control bound to exact eligibility assumption',await page.evaluate(()=>window.currentStudyRun.config.reserveCents===20000&&window.currentStudyRun.arms.B.summary.availableOperatingSurplusCents===-7735));
  await page.selectOption('#preset','continuation-reference');
  check('Predeclared fresh continuation path remains exact',await page.evaluate(()=>window.currentStudyRun.seed===3001&&window.currentStudyRun.arms.B.summary.profitCents===35100&&window.currentStudyRun.arms.B.summary.assetUses===35&&window.currentStudyRun.causal.B_minus_A_profitCents===33821));
  check('Fresh funding is a ceiling before unpriced discovery',await page.evaluate(()=>window.currentFundingView.terminal.fundingCeilingBeforeUnpricedDiscoveryCents===35100&&window.currentFundingView.unpricedIncrementalDiscoveryCostCents===null&&window.currentFundingView.allInSpendableResourcesIdentified===false));
  await page.click('[data-tab="history"]');
  await page.screenshot({path:path.join(output,'en-fresh-history.png'),fullPage:true});
  await page.click('[data-tab="market"]');
  await page.selectOption('#preset','zero-demand');
  check('Zero-demand control in actual interface',await page.evaluate(()=>window.currentStudyRun.arms.B.summary.enterpriseAccepted===0&&window.currentStudyRun.arms.B.summary.grossCollectionsCents===0));
  await page.selectOption('#preset','free-perfect-diy');
  check('Perfect free alternative can reject enterprise',await page.evaluate(()=>window.currentStudyRun.arms.B.summary.enterpriseAccepted===0));
  await page.selectOption('#preset','reference-assumptions');
  await page.locator('#minutes').fill('0');await page.locator('#minutes').dispatchEvent('input');
  check('No benefit prevents adoption in interface',await page.evaluate(()=>window.currentStudyRun.arms.B.summary.investmentWeek===null));
  const pending=page.waitForEvent('download');await page.click('#downloadRun');const runDownload=await pending;
  const dest=path.join(output,runDownload.suggestedFilename());await runDownload.saveAs(dest);
  const saved=JSON.parse(fs.readFileSync(dest));check('Downloaded complete history has actual interface scenario',saved.config.ordinaryFinalizationMinutes===0&&saved.observedCustomerCollectionsCents===undefined&&saved.arms.B.observedCustomerCollectionsCents===0);
  downloads.push({filename:runDownload.suggestedFilename(),sha256:sha(fs.readFileSync(dest))});
  await page.selectOption('#preset','reference-assumptions');
  await page.setViewportSize({width:390,height:844});
  for(const language of ['en','fr']){
    await page.click('#'+language);
    for(const tab of ['evidence','market','history','sources']){
      await page.click('[data-tab="'+tab+'"]');
      check('Mobile no horizontal overflow '+language+' '+tab,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    }
    await page.click('[data-tab="market"]');
    await page.screenshot({path:path.join(output,language+'-mobile.png'),fullPage:true});
  }
  check('No browser errors',errors.length===0,{errors});
  check('No external requests',externalRequests.length===0,{externalRequests});
  await browser.close();
  const result={schema:'game-market-demo-browser-qa/v1',htmlSHA256:sha(fs.readFileSync(file)),findings,downloads,errors,externalRequests,passed:findings.every(x=>x.pass)};
  fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2)+'\n');
  process.stdout.write(JSON.stringify({passed:result.passed,checks:findings.length,downloads:downloads.length})+'\n');
})().catch(e=>{fs.writeFileSync(path.join(output,'failure-'+Date.now()+'.json'),JSON.stringify({error:e.message,findings,errors,externalRequests},null,2));process.stderr.write(e.stack+'\n');process.exit(1)});
