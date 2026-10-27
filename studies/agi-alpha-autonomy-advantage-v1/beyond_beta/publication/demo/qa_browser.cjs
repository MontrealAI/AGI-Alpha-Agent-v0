// SPDX-License-Identifier: Apache-2.0
// Normal Chromium sandbox only. A blocked launch is recorded, never bypassed.
const fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
  const record={schema:'beyond-beta-demo-browser-qa/v1',chromiumSandbox:true,securityBypasses:false,status:'NOT_RUN',screenshots:[],checks:[]};
  let browser;
  try{
    browser=await chromium.launch({executablePath:'/workspace/scratch/28e17bbc80e2/browser_cache/chrome-headless-shell-linux64/chrome-headless-shell',headless:true,chromiumSandbox:true,timeout:15000});
    const page=await browser.newPage({viewport:{width:1440,height:1100}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
    await page.locator('h1').filter({hasText:'Paid Work.'}).waitFor();
    await page.screenshot({path:path.join(__dirname,'desktop-en.png'),fullPage:true});record.screenshots.push('desktop-en.png');
    await page.locator('#lang-fr').click();
    await page.locator('h1').filter({hasText:'Travail rémunéré.'}).waitFor();
    await page.screenshot({path:path.join(__dirname,'desktop-fr.png'),fullPage:true});record.screenshots.push('desktop-fr.png');
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(__dirname,'mobile-fr.png'),fullPage:true});record.screenshots.push('mobile-fr.png');
    record.checks.push({name:'No page errors',passed:errors.length===0,errors});
    record.checks.push({name:'Mobile document fits viewport',passed:await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)});
    record.status=record.checks.every(x=>x.passed)?'PASS':'FAIL';
  }catch(e){record.status='BLOCKED';record.reason=String(e.message);}
  finally{if(browser)await browser.close();}
  fs.writeFileSync(path.join(__dirname,'qa-browser.json'),JSON.stringify(record,null,2)+'\n');
  console.log(JSON.stringify({status:record.status,screenshots:record.screenshots,reason:record.reason?.slice(0,1800)}));
})();
