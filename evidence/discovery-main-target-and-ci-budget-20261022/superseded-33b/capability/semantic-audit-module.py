from pathlib import Path
import hashlib,json
def authenticate_semantics(D,I):
    B=Path('/dev/shm/alpha-33b-main-target-cap-custody');P='discovery-continuation/'
    sha=lambda b:hashlib.sha256(b).hexdigest();canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    def raw(name):return (B/'selected'/name).read_bytes()
    def item(name):return D[P+name]
    source=D['source.json'];checkout=D['exact-checkout.json'];j=item('journey.json');journal=item('browser-native-requests.json');before=item('fleet-browser-workspace.json');after=item('fleet-return-workspace.json');req=item('fleet-browser-request.json');agi=item('jobs-browser-request.json');proof=item('fleet-native/native-proof.json');wrapper=item('fleet-native/wrapper.json');native=json.loads(wrapper['raw']);receipt=json.loads(native['receiptRaw']);docket=item('fleet-return-docket.json');reopened=item('fleet-reopened-docket.json')
    assert j['passed'] is True and j['pageErrors']==[] and j['source']==source['source']==checkout['source']
    assert raw(P+'fleet-browser-workspace.json')==raw(P+'jobs-browser-workspace.json')
    assert {k:v for k,v in req.items() if k!='commission'}=={k:v for k,v in agi.items() if k!='commission'}
    assert req['missionId']==agi['missionId']==before['missionId']==after['missionId']==journal['missionId']==proof['missionId']
    assert req['commission']['id']==agi['commission']['id'] and req['commission']['branch']!=agi['commission']['branch']
    for record,route,currency in [(req,'manager-usdc','USDC6'),(agi,'jobs-agialpha','AGIALPHA18')]:assert record['commission']['route']==route and record['commission']['currency']==currency and record['commission']['capBaseUnits']=='0' and record['commission']['status']=='DRAFT_NOT_SUBMITTED'
    assert journal['sourceHash']==proof['sourceHash']==source['source']['sourceHash'] and journal['pageSha256']==j['pageSha256']==sha(raw(P+'served/index.html'))
    assert journal['workspace']['sha256']==journal['workspace']['jobsSha256']==proof['workspaceSha256']==sha(raw(P+'fleet-browser-workspace.json'))
    prefix=[e['digest'] for e in before['events']];assert journal['workspace']['eventPrefix']==prefix and journal['workspace']['head']==prefix[-1] and journal['workspace']['revision']==before['revision']
    assert journal['campaignDigest']==proof['campaignDigest'] and proof['campaignDigest'] in prefix
    for route,name in [('manager-usdc','fleet-browser-request.json'),('jobs-agialpha','jobs-browser-request.json')]:assert journal['requests'][route]['file']==name and journal['requests'][route]['sha256']==sha(raw(P+name))
    assert j['fleetLocalReview']['requestExports']==journal
    assert native['original'].encode()==raw(P+'fleet-browser-request.json') and sha(native['receiptRaw'].encode())==proof['receipt']['nativeReceiptDigest'] and sha(native['original'].encode())==proof['requestSha256']==proof['receipt']['requestDigest']
    for key in ['missionId','revision','stage','payloadDigest','sourceDigest','evaluatorDigest','commission']:assert receipt[key]==req[key],key
    assert receipt['state']==proof['receipt']['state']=='accepted-local-review' and receipt['authority']==proof['receipt']['authority']=='none'
    assert receipt['remoteExecution']=='unprovisioned' and receipt['settlement']=='not-connected' and receipt['organizationalIndependence'] is False and receipt['protectedHoldout'] is False
    assert proof['authority']=='none' and proof['totalComplete'] is False and proof['receipt']['authenticity']=='not-attested' and proof['receipt']['installedRuntime']['provenance']=='unattested-declaration'
    assert after['events'][:len(before['events'])]==before['events'] and len(after['events'])==len(before['events'])+1 and after['revision']==before['revision']+1
    for index,event in enumerate(after['events']):
     assert event['sequence']==index and event['previous']==(None if index==0 else after['events'][index-1]['digest'])
     frame={k:event[k] for k in ['sequence','kind','previous','payload']};frame['missionId']=after['missionId'];assert sha(('successor-omega/v1:capability-event\0'+canonical(frame)).encode())==event['digest'],index
    last=after['events'][-1];assert last['kind']=='lab-evidence-attached' and last['payload']['kind']=='receiver-receipt' and last['payload']['campaignDigest']==proof['campaignDigest'] and last['payload']['record']==wrapper
    variants=['executor','runtime','elapsed','memory','outcome','raw-framing','receipt-framing','request-framing','source-repository','forged-authority','swapped-mission'];assert proof['variants']==variants
    refusals=[]
    for name in variants:
     refused=P+'fleet-refused-'+name+'-docket.json';mutated=P+'fleet-native/'+name+'.json'
     assert I[refused]['sha256']==I[P+'fleet-return-docket.json']['sha256'] and D[refused]==docket and D[mutated]!=wrapper
     assert 'refused-'+name in j['fleetLocalReview']['checks']
     refusals.append({'variant':name,'nativeVariant':I[mutated],'refusedDocket':I[refused],'acceptedDocketByteIdentity':True,'actualUiRefusalCheck':True})
    assert len(docket['files'])==13 and set(docket['checksums'])==set(docket['files']) and reopened==docket and I[P+'fleet-reopened-docket.json']['sha256']==I[P+'fleet-return-docket.json']['sha256']
    for name,text in docket['files'].items():assert sha(text.encode())==docket['checksums'][name],name
    assert j['fleetLocalReview']['docketSha256']==I[P+'fleet-return-docket.json']['sha256']
    aria=[]
    for state in ['continuation-desktop','continuation-mobile']:
     observation=item('accessibility-'+state+'.json');axe=item('contrast-review/axe-'+state+'.json');review=item('contrast-review/review-'+state+'.json')
     assert observation['violations']==0 and axe['violations']==[] and observation['incompleteRules']==['color-contrast'] and [r['id'] for r in axe['incomplete']]==['color-contrast']
     assert len(review)==observation['reviewedNodes'] and all(isinstance(r.get('resolution'),str) and r['resolution'] for r in review)
     measured=[r['contrast'] for r in review if 'contrast' in r];assert all(r['minimumRatio']>=r['requiredRatio'] for r in measured) and len(measured)==observation['reviewedContrast']
     assert min(r['minimumRatio'] for r in measured)==observation['minimumConservativeContrast']
     aria.append({'state':state,'axeViolations':0,'incompleteRules':['color-contrast'],'retainedReviewNodes':len(review),'measuredContrastRows':len(measured),'minimumConservativeContrast':observation['minimumConservativeContrast'],'allRetainedResolutionsPresent':True,'scope':'finite original hosted generated-page observation; no browser execution in this audit'})
    assert all(v['worktreeConfiguration']=='disabled' for v in proof['gitMetadata'].values())
    report={'schema':'main-target-original-capability-semantic-custody/v1','run':39724342613,'attempt':1,'event':'pull_request','conclusion':'success','head':'33b19714e1219c812d451e4d736fcb34b722ceff','synthetic':'c0773f99623d7ab8d82f3a978c76b41cd596dfa7','syntheticTree':'b310ec7fe96000668f7be2d1b1866245b255d56b','syntheticOrderedParents':['5a5340a15698165bceb21e252f3bec58d7fd8298','33b19714e1219c812d451e4d736fcb34b722ceff'],'sourceHash':proof['sourceHash'],'dualActualUiExports':{'sameWorkspaceRawBytes':True,'sameMission':True,'sameAllNonCommissionFields':True,'commissionId':req['commission']['id'],'currencies':['USDC6','AGIALPHA18'],'routes':['manager-usdc','jobs-agialpha'],'unsubmittedCaps':['0','0'],'workspaceSha256':proof['workspaceSha256'],'requestShas':[sha(raw(P+'fleet-browser-request.json')),sha(raw(P+'jobs-browser-request.json'))],'journalBindingsExact':True,'campaignDigest':proof['campaignDigest']},'native':{'receipt':proof['receipt'],'gitMetadata':proof['gitMetadata'],'actualOriginalRequestRawBytesExact':True,'originalNativeReceiptRawDigestMatches':True,'authority':'none','totalComplete':False,'historyPrefixExact':True,'eventChainDigestsIndependentlyRecomputed':True,'eventsBefore':len(before['events']),'eventsAfter':len(after['events']),'revisionBefore':before['revision'],'revisionAfter':after['revision'],'all11Refusals':refusals,'docketSections':len(docket['files']),'sectionChecksumsAllExact':True,'reopenDocketByteIdentity':True,'docketSha256':I[P+'fleet-return-docket.json']['sha256'],'sourceScope':proof['scope']},'browser':{'journeyPassed':True,'pageErrors':[],'checks':j['checks'],'fleetChecks':j['fleetLocalReview']['checks'],'aria':aria},'sourceAuthenticationReportSha256':sha((B/'source-page-authentication.json').read_bytes()),'artifactInventorySha256':sha((B/'capability-zip-inventory.json').read_bytes()),'qualificationScope':'CURRENT_MAIN_TARGET_PR_SYNTHETIC_ONLY; not accepted main, exact-main push release, installed service, public operational or economic qualification','noRerunsCancelsDispatchesBrowserOrArtifactExecution':True,'publicWrites':False}
    (B/'semantic-custody.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'source':report['sourceHash'],'dualUi':report['dualActualUiExports'],'nativeSummary':{k:v for k,v in report['native'].items() if k not in ['receipt','all11Refusals']},'aria':aria,'semanticReportSha256':sha((B/'semantic-custody.json').read_bytes())},indent=2))
