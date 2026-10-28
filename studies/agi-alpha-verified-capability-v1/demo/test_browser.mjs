import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const playwrightModule=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES
  ? pathToFileURL(resolve(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES,'playwright/index.mjs')).href
  : 'playwright';
const {chromium}=await import(playwrightModule);
const HERE=dirname(fileURLToPath(import.meta.url)),reportDir=resolve(HERE,'browser-review');mkdirSync(reportDir,{recursive:true});
const checks=[],errors=[],requests=[];
const check=(name,ok,detail=null)=>{checks.push({name,pass:!!ok,detail});if(!ok)throw Error(name+': '+JSON.stringify(detail));};
const browser=await chromium.launch({headless:true,args:['--no-sandbox'],
  ...(process.env.VERIFIED_CAPABILITY_CHROMIUM?{executablePath:process.env.VERIFIED_CAPABILITY_CHROMIUM}:{})});
try{
  const context=await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  await page.goto(pathToFileURL(resolve(HERE,'index.html')).href,{waitUntil:'load'});
  check('desktop rendered real local evidence',await page.locator('#hero-skill-count').textContent()==='4');
  check('English document language',await page.locator('html').getAttribute('lang')==='en');
  check('live ENS boundary visible',(await page.locator('.fixture').textContent()).includes('NOT RUN'));
  check('desktop no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  const controls=await page.evaluate(()=>window.AGIALPHA_DEMO.data.reuse?.results??[]);
  if(controls.length){
    check('default recorded refusal is current graph revocation',(await page.locator('#refusal-select option:checked').textContent()).includes('revoked-skill'));
    for(let i=0;i<controls.length;i++){
      await page.locator('#refusal-select').selectOption(String(i));
      const output=await page.locator('#refusal-reasons').textContent();
      check(`recorded reuse decision ${controls[i].strategy}/${controls[i].id}`,output.includes(controls[i].result.decision)&&
        (controls[i].result.ok?await page.locator('#refusal-reasons').getAttribute('class')==='proof-result pass':output.includes(controls[i].result.reasons[0])));
    }
    await page.locator('#refusal-select').selectOption(String(controls.findIndex(x=>x.id==='revoked-skill'&&x.strategy==='graph')));
  }
  for(const type of ['skill','edge']){
    const ids=await page.evaluate(t=>(window.AGIALPHA_DEMO.data.catalog.forest.classes[t].records.map(x=>x.record.id)),type);
    for(const id of ids){
      if(type==='skill')await page.locator(`[data-skill="${id}"]`).click();else await page.locator(`[data-select-edge="${id}"]`).click();
      const good=await page.evaluate(()=>window.AGIALPHA_DEMO.verifySelected(false));
      check(`actual WebCrypto inclusion ${type} ${id}`,good===true);
      const bad=await page.evaluate(()=>window.AGIALPHA_DEMO.verifySelected(true));
      check(`tampered record refused ${type} ${id}`,bad===false);
      check(`integrity never claims identity ${type} ${id}`,await page.evaluate(()=>window.lastIntegrityCheck.identityVerified===false));
    }
  }
  const production=await page.evaluate(()=>window.AGIALPHA_DEMO.data.production);
  if(production){
    for(const mission of production.arms.C.per_mission){
      await page.locator('#mission-select').selectOption(mission.id);
      check(`recorded mission ${mission.id}`,(await page.locator('#mission-name').textContent())===mission.id&&
        (await page.locator('#mission-decision').textContent())===mission.decision&&
        await page.locator('#mission-downloads [data-download]').count()===2);
    }
    await page.locator('#mission-select').selectOption(production.arms.C.per_mission[0].id);
  }
  const worlds=await page.evaluate(()=>window.AGIALPHA_DEMO.data.worlds),cells=await page.evaluate(()=>window.AGIALPHA_DEMO.data.market?.cells??[]);
  if(worlds.length){
    check('all registered paired market worlds embedded',worlds.length===1152&&cells.length===48);
    for(const cell of cells){
      await page.locator('#condition-select').selectOption(cell.condition);
      await page.locator('#cost-select').selectOption(cell.costProfile);
      await page.locator('#policy-select').selectOption(cell.policy);
      await page.locator('#seed-select').selectOption('9101');
      const record=JSON.parse(await page.locator('#investment-record').textContent());
      const expected=worlds.find(x=>x.cell===cell.id&&x.seed===9101);
      check(`recorded market cell ${cell.id}`,record.cell===expected.cell&&record.seed===expected.seed&&
        JSON.stringify(record.graph)===JSON.stringify(expected.arms.C));
    }
    await page.locator('#condition-select').selectOption('reference');
    await page.locator('#cost-select').selectOption('reference');
    await page.locator('#policy-select').selectOption('adaptive');
    for(let seed=9101;seed<=9124;seed++){
      await page.locator('#seed-select').selectOption(String(seed));
      const record=JSON.parse(await page.locator('#investment-record').textContent());
      check(`recorded seed ${seed}`,record.seed===seed&&record.cell===worlds.find(x=>x.condition==='reference'&&x.costProfile==='reference'&&x.policy==='adaptive'&&x.seed===seed).cell);
    }
    await page.locator('#seed-select').selectOption('9101');
    await page.locator('#inspect-positive').click();
    const positiveRecord=JSON.parse(await page.locator('#investment-record').textContent());
    check('single favorable individual path remains accessible without promotion',positiveRecord.seed===9110&&
      positiveRecord.cell==='reference__completed-research-replay__low'&&
      (await page.locator('#positive-path-note').textContent()).includes('$10.01')&&
      (await page.locator('#positive-path-note').textContent()).includes('-$1.50')&&
      (await page.locator('#investment-reason').textContent()).includes('despite failing prospective financial admission')&&
      positiveRecord.qualification.conditionalModeledFinancialGatePassed===false);
    await page.locator('#cost-select').selectOption('reference');
    await page.locator('#policy-select').selectOption('adaptive');
    await page.locator('#seed-select').selectOption('9101');
  }
  const keys=await page.evaluate(()=>['catalog','index','costs','production','reuse','market','paper'].filter(k=>window.AGIALPHA_DEMO.embedded.downloads[k]));
  for(const key of keys){
    const [download]=await Promise.all([page.waitForEvent('download'),page.locator(`[data-download="${key}"]`).click()]);
    const raw=readFileSync(await download.path()),hash=createHash('sha256').update(raw).digest('hex');
    const expected=await page.evaluate(k=>window.AGIALPHA_DEMO.embedded.downloads[k].sha256,key);
    check(`download exact source bytes ${key}`,hash===expected,{bytes:raw.length,sha256:hash});
  }
  if(production){
    const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#mission-downloads [data-download]').first().click()]);
    const raw=readFileSync(await download.path()),hash=createHash('sha256').update(raw).digest('hex');
    const expected=await page.evaluate(()=>window.AGIALPHA_DEMO.embedded.downloads[document.querySelector('#mission-downloads [data-download]').dataset.download].sha256);
    check('actual complete mission packet download',hash===expected&&raw[0]===0x50&&raw[1]===0x4b,{bytes:raw.length,sha256:hash});
  }
  await page.locator('#lang-fr').click();
  check('French document language',await page.locator('html').getAttribute('lang')==='fr');
  check('French mission copy',(await page.locator('#mission h2').textContent()).includes('dépendances'));
  check('French no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('#cost-select').selectOption('actual-unknown');
  check('unknown costs remain unknown',(await page.locator('#sensitivity-result').textContent()).includes('inconnu'));
  await page.locator('#cost-select').selectOption('reference');
  await page.locator('#attention-slider').fill('300');await page.locator('#attention-slider').dispatchEvent('input');
  check('hypothetical sensitivity responds',(await page.locator('#attention-value').textContent()).includes('300'));
  await page.locator('#attention-slider').fill('0');await page.locator('#attention-slider').dispatchEvent('input');
  await page.locator('#lang-en').click();
  await page.locator('[data-skill="decision-delivery"]').click();
  await page.evaluate(()=>window.AGIALPHA_DEMO.verifySelected(false));
  await page.evaluate(()=>scrollTo(0,0));
  await page.locator('#live-status').waitFor({state:'hidden',timeout:6000});
  await page.screenshot({path:resolve(reportDir,'desktop-en.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  check('mobile English no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:resolve(reportDir,'mobile-en.png'),fullPage:true});
  await page.locator('#lang-fr').click();
  check('mobile French no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:resolve(reportDir,'mobile-fr.png'),fullPage:true});
  await page.setViewportSize({width:320,height:700});
  check('small mobile French no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  check('no page errors',errors.length===0,errors);check('no external requests',requests.length===0,requests);
  const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}}),p=await nojs.newPage();
  await p.goto(pathToFileURL(resolve(HERE,'index.html')).href);
  check('no-JavaScript evidence boundary visible',(await p.locator('noscript').textContent()).includes('Actual customer receipts are zero'));
  writeFileSync(resolve(reportDir,'checks.json'),JSON.stringify({status:'PASS',checks,errors,externalRequests:requests,
    edition:await page.evaluate(()=>window.AGIALPHA_DEMO.embedded.edition),htmlSHA256:createHash('sha256').update(readFileSync(resolve(HERE,'index.html'))).digest('hex')},null,2)+'\n');
  console.log(JSON.stringify({status:'PASS',checks:checks.length,errors:errors.length,externalRequests:requests.length}));
}catch(e){writeFileSync(resolve(reportDir,'failure.json'),JSON.stringify({status:'FAIL',message:e.message,checks,errors,externalRequests:requests},null,2)+'\n');throw e;}
finally{await browser.close();}
