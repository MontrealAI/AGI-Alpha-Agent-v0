# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib,json,os,sys,threading,traceback
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import expect,sync_playwright
import test_discovery_lab_browser as preserved
SOURCE=Path('/dev/shm/discovery-continuation-current5/served')
WORKSPACE=Path('/dev/shm/discovery-continuation-current5/browser-workspace.json')
NATIVE=Path('/dev/shm/discovery-native-receipt-current5')
mode=sys.argv[1]
OUT=NATIVE/'both-routes-browser' if mode=='import' else NATIVE
OUT.mkdir(exist_ok=True)
assert mode in ['export','import']
server=ThreadingHTTPServer(('127.0.0.1',0),partial(preserved.QuietHandler,directory=str(SOURCE)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch();context=browser.new_context(accept_downloads=True);page=context.new_page();errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)));page.on('dialog',lambda dialog:dialog.accept())
  try:
   response=page.goto(f'http://127.0.0.1:{server.server_port}/index.html');assert response and response.body()==(SOURCE/'index.html').read_bytes()
   page.locator('#public-confirmation').check();page.locator('#lab-public-confirmation').check();page.locator('#import').set_input_files(WORKSPACE)
   expect(page.locator('#status')).to_contain_text('Whole history imported',timeout=120000)
   expect(page.locator('#lab-export-request')).to_be_enabled(timeout=120000)
   if mode=='export':
    page.locator('#lab-route').select_option('USDC');request=preserved.download_json(page,'#lab-export-request',OUT/'manager-browser-draft.json')
    assert request['commission']['route']=='manager-usdc'
    page.locator('#lab-route').select_option('AGIALPHA');jobs=preserved.download_json(page,'#lab-export-request',OUT/'jobs-browser-draft.json')
    assert jobs['commission']['route']=='jobs-agialpha' and request['payloadDigest']==jobs['payloadDigest']
    print(json.dumps({'exported':True,'missionId':request['missionId'],'managerRequest':str(OUT/'manager-browser-draft.json'),'jobsRequest':str(OUT/'jobs-browser-draft.json')}),flush=True)
   else:
    wrappers=[json.loads((NATIVE/name).read_text()) for name in ['manager-wrapper.json','jobs-native-receipt.json']]
    for name in ['manager-wrapper.json','jobs-native-receipt.json']:
     page.locator('#lab-import-receipt').set_input_files(NATIVE/name)
     expect(page.locator('#lab-receipt-status')).to_contain_text('Receiver receipt retained in this mission',timeout=120000)
     identity=page.locator('#identity').inner_text();page.locator('#lab-import-receipt').set_input_files(NATIVE/name)
     expect(page.locator('#lab-receipt-status')).to_contain_text('Receiver receipt rejected:',timeout=120000)
     expect(page.locator('#identity')).to_have_text(identity)
    docket=preserved.download_json(page,'#lab-export-docket',OUT/'browser-native-docket.json')
    record=json.loads(docket['files']['05_agialpha_runs/run.json']);events=[e for e in record['workspace']['events'] if e['kind']=='lab-evidence-attached' and e['payload']['kind']=='receiver-receipt']
    assert len(events)==2 and all(event['payload']['record']['raw']==wrapper['raw'] for event,wrapper in zip(events,wrappers))
    ledger=json.loads(docket['files']['08_cost_ledgers/costs.json']);assert len(ledger['receiverInspectionByRoute'])==2 and ledger['currenciesCombined'] is False
    (OUT/'browser-native-workspace.json').write_text(json.dumps(record['workspace']))
    page.reload();expect(page.locator('#saved')).to_be_enabled(timeout=120000);page.locator('#saved').select_option(json.loads(WORKSPACE.read_text())['missionId']);page.locator('#open').click();expect(page.locator('#status')).to_contain_text('Saved history opened',timeout=120000);expect(page.locator('#lab-export-docket')).to_be_enabled(timeout=120000)
    replay=preserved.download_json(page,'#lab-export-docket',OUT/'browser-native-reloaded-docket.json');assert replay==docket
    assert not errors
    receipt={'passed':True,'mode':'packaged-local-current-source-native-integration','pageSha256':hashlib.sha256((SOURCE/'index.html').read_bytes()).hexdigest(),'sourceHash':json.loads((SOURCE/'sources.json').read_text())['sourceHash'],'checks':['actual-browser-export','actual-public-manager-and-jobs-adapters','actual-current-alpha-inspector','same-mission-both-receipt-import','duplicate-refusal-without-history-change','raw-bytes-preserved','separate-currency-docket-exactly-once-accounting','explicit-reopen-byte-identical-docket'],'pageErrors':errors,'authority':'none','installedReleaseAcceptance':'not-established'}
    (OUT/'journey.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
  except BaseException as error:
   (OUT/(mode+'-failure.json')).write_text(json.dumps({'passed':False,'error':str(error),'traceback':traceback.format_exc(),'futureStatus':page.locator('#lab-future-status').inner_text(),'receiptStatus':page.locator('#lab-receipt-status').inner_text(),'pageErrors':errors},indent=2));page.screenshot(path=str(OUT/(mode+'-failure.png')),full_page=True);raise
  finally:browser.close()
finally:server.shutdown();server.server_close()
