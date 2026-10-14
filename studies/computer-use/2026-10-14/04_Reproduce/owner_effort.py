from pathlib import Path
import os,shutil
import json,csv,statistics
from playwright.sync_api import sync_playwright
from browser_acceptance import load
R=Path(__file__).resolve().parents[1];O=R/'03_Evidence';html=(R/'02_Work_Products/MISSION_REPLAY.html').read_text()
brief='Repair Studio Horizon using its new catalogue and capacity rules. Keep every offering, show correct totals on phones, and give me a tested website I can recover. Do not publish it.'
results=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('BROWSER_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox','--disable-dev-shm-usage'])
 for i in range(5):
  for mode in (['familiar-no-profile','retained-profile'] if i%2==0 else ['retained-profile','familiar-no-profile']):
   c,page,_,_=load(b,html);page.locator('#task').select_option('B');page.locator('#brief').fill(brief)
   if mode=='retained-profile':page.locator('#reuse').check()
   else:
    for sel,value in [('languages','bilingual'),('devices','both'),('deliverables','evidence'),('recovery','portable')]:page.locator('#'+sel).select_option(value)
   page.locator('#scope').check();page.locator('#prepare').click();page.locator('#show-evidence').click()
   for key in ['content','numbers','recovery']:page.locator('#check-'+key).check()
   page.locator('#accept').click()
   with page.expect_download() as d:page.locator('#download').click()
   path=O/f'owner_{mode}_{i+1}.json';d.value.save_as(path);data=json.loads(path.read_text());events=data['events']
   results.append({'mode':mode,'replicate':i+1,'actions':len(events),'preferenceEdits':sum(e['element'] in ['languages','devices','deliverables','recovery'] for e in events),'freshScopeApprovals':sum(e['element']=='scope' and e['value'] is True for e in events),'reviewChecks':sum(e['element'].startswith('check-') and e['value'] is True for e in events),'typedBriefCharacters':len(brief),'mechanicalElapsedMs':events[-1]['elapsedMs'],'qualitySource':'03_Evidence/acceptance/B_after.json','qualityPassed':35,'qualityTotal':35})
   if i==0:page.screenshot(path=str(O/f'screenshots/owner_{mode}.png'),full_page=True)
   c.close()
 b.close()
base=statistics.mean(x['actions'] for x in results if x['mode']=='familiar-no-profile');reuse=statistics.mean(x['actions'] for x in results if x['mode']=='retained-profile')
report={'runs':results,'baselineActions':base,'reuseActions':reuse,'reductionFraction':1-reuse/base,'participants':0,'interpretation':'Measured scripted interface operations in this replay only. Both modes have identical Task B quality and fresh permission/review. Fewer clicks do not measure attention, skill or human time.','baselineLimitation':'This UI has four separate preference controls. A well-designed batched preference entry or a different interface could reduce/eliminate the action-count advantage.','timeModel':{'commonBriefAndScopeSeconds':120,'commonArtifactReviewSeconds':180,'commonSaveSeconds':30,'noProfileFourPreferencesSeconds':100,'profileConfirmationSeconds':35,'firstTimePreferenceSetupIncludedInTaskA':True,'humanTimeObserved':False}}
(O/'OWNER_EFFORT.json').write_text(json.dumps(report,indent=2)+'\n')
with (R/'08_Metrics/owner_runs.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
print('Owner actions:',base,'→',reuse,'reduction',round(100*(1-reuse/base),2),'%')
