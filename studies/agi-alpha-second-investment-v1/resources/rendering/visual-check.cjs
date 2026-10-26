// SPDX-License-Identifier: Apache-2.0
const { chromium } = require(process.argv[2]);
const { pathToFileURL } = require('node:url');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const study = process.argv[3];
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport:{width:1360,height:1100}, deviceScaleFactor:1});
  const errors=[]; page.on('pageerror', e => errors.push(String(e)));
  const checks=[];
  for (const name of ['index','cryptography','pyyaml']) {
    await page.goto(pathToFileURL(path.join(study,'deliverables/packets',name+'.html')).href);
    await page.locator('[data-set-language="en"]').click();
    const width = await page.evaluate(() => ({viewport:innerWidth,document:document.documentElement.scrollWidth}));
    if(width.document>width.viewport) throw Error('Horizontal overflow: '+name);
    await page.screenshot({path:path.join(study,'resources/rendering',name+'-desktop.png'),fullPage:true});
    await page.locator('[data-set-language="fr"]').click();
    if(await page.locator('html').getAttribute('lang') !== 'fr') throw Error('French toggle failed');
    checks.push({page:name,desktopOverflow:false,frenchToggle:true});
  }
  await page.setViewportSize({width:390,height:844});
  await page.locator('[data-set-language="both"]').click();
  const width=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
  if(width.document>width.viewport) throw Error('Mobile horizontal overflow');
  await page.screenshot({path:path.join(study,'resources/rendering/pyyaml-mobile.png'),fullPage:true});
  if(errors.length) throw Error(JSON.stringify(errors));
  fs.writeFileSync(path.join(study,'resources/rendering/visual-check.json'),JSON.stringify({checks,mobileWidth:390,
    mobileOverflow:false,browserErrors:errors,method:'Headless Chromium local file rendering; no network or application runtime.'},null,2)+'\n');
  await browser.close();
  console.log(JSON.stringify({passed:true,checks}));
})().catch(error=>{console.error(error);process.exitCode=1});
