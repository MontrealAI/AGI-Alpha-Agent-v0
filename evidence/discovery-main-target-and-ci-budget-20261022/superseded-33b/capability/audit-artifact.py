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
    report={'schema':'main-target-original-capability-semantic-custody/v1','run':39724342613,'attempt':1,'event':'pull_request','conclusion':'success','head':'33b19714e1219c812d451e4d736fcb34b722ceff','synthetic':'c0773f99623d7ab8d82f3a978c76b41cd596dfa7','syntheticTree':'b310ec7fe96000668f7be2d1b1866245b255d56b','syntheticOrderedParents':['5a5340a15698165bceb21e252f3bec58d7fd8298','33b19714e1219c812d451e4d736fcb34b722ceff'],'sourceHash':proof['sourceHash'],'dualActualUiExports':{'sameWorkspaceRawBytes':True,'sameMission':True,'sameAllNonCommissionFields':True,'commissionId':req['commission']['id'],'currencies':['USDC6','AGIALPHA18'],'routes':['manager-usdc','jobs-agialpha'],'unsubmittedCaps':['0','0'],'workspaceSha256':proof['workspaceSha256'],'requestShas':[sha(raw(P+'fleet-browser-request.json')),sha(raw(P+'jobs-browser-request.json'))],'journalBindingsExact':True,'campaignDigest':proof['campaignDigest']},'native':{'receipt':proof['receipt'],'gitMetadata':proof['gitMetadata'],'actualOriginalRequestRawBytesExact':True,'originalNativeReceiptRawDigestMatches':True,'authority':'none','totalComplete':False,'historyPrefixExact':True,'eventChainDigestsIndependentlyRecomputed':True,'eventsBefore':len(before['events']),'eventsAfter':len(after['events']),'revisionBefore':before['revision'],'revisionAfter':after['revision'],'all11Refusals':refusals,'docketSections':len(docket['files']),'sectionChecksumsAllExact':True,'reopenDocketByteIdentity':True,'docketSha256':I[P+'fleet-return-docket.json']['sha256'],'sourceScope':proof['scope']},'browser':{'journeyPassed':True,'pageErrors':[],'checks':j['checks'],'fleetChecks':j['fleetLocalReview']['checks'],'aria':aria},'sourceAuthenticationReportSha256':sha((B/'source-page-authentication.json').read_bytes()),'artifactInventorySha256':sha((B/'capability-zip-inventory.json').read_bytes()),'qualificationScope':'SUPERSEDED_33B_ORIGINAL_NONFINAL; not accepted main, exact-main push release, installed service, public operational or economic qualification','noRerunsCancelsDispatchesBrowserOrArtifactExecution':True,'publicWrites':False}
    (B/'semantic-custody.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'source':report['sourceHash'],'dualUi':report['dualActualUiExports'],'nativeSummary':{k:v for k,v in report['native'].items() if k not in ['receipt','all11Refusals']},'aria':aria,'semanticReportSha256':sha((B/'semantic-custody.json').read_bytes())},indent=2))


# Own audit code only. Artifact and repository source are parsed as inert data.
def audit_broader_aria(D,I):
    B=Path('/dev/shm/alpha-33b-main-target-cap-custody');P='accessibility-review/';S=D[P+'summary.json'];cat=D['discovery-continuation/served/sources.json'];sha=lambda b:hashlib.sha256(b).hexdigest()
    assert S['status']=='PASS' and S['source']==cat and S['pageSHA256']==I['discovery-continuation/served/index.html']['sha256']
    harness=next(json.loads(p.read_text()) for p in B.glob('fresh-extra-*.json') if json.loads(p.read_text())['path']=='alpha/tests/browser/test_successor_capability_accessibility.py');assert harness['sha256']==S['harnessSHA256']
    for state in S['states']:
        name=state['state'];axe=D[P+'axe-'+name+'.json'];review=D[P+'review-'+name+'.json'];assert axe['violations']==[] and state['violations']==0 and [x['id'] for x in axe['incomplete']]==state['incompleteRules']==['color-contrast'];assert len(review)==state['reviewedNodes'] and all(isinstance(x.get('resolution'),str) and x['resolution'] for x in review);measured=[x['contrast'] for x in review if 'contrast' in x];assert len(measured)==state['reviewedContrast'] and all(x['minimumRatio']>=x['requiredRatio'] for x in measured) and min(x['minimumRatio'] for x in measured)==state['minimumConservativeContrast']
    keyboard=D[P+'keyboard-report-scroll.json'];assert keyboard['focused'] is True and keyboard['scrollTop']>0 and keyboard['scrollHeight']>keyboard['clientHeight']
    report={'schema':'new-main-target-broader-aria-custody/v1','run':39724342613,'attempt':1,'synthetic':'c0773f99623d7ab8d82f3a978c76b41cd596dfa7','tree':'b310ec7fe96000668f7be2d1b1866245b255d56b','originalStatus':S['status'],'states':S['states'],'keyboardNamedReportScroll':keyboard,'harness':harness,'manualReviewRequired':S['manualReviewRequired'],'scope':S['scope'],'originalMemberBindings':[I[n] for n in I if n.startswith(P) and n.endswith('.json')],'limits':'Original finite hosted reports authenticated without browser launch or artifact/source execution. Original screenshot member hashes authenticated; no independent visual review or universal WCAG claim.'}
    (B/'broader-aria-custody.json').write_text(json.dumps(report,indent=2)+'\n')


def audit_variant_payloads(D,I):
    import copy
    B=Path('/dev/shm/alpha-33b-main-target-cap-custody');P='discovery-continuation/fleet-native/';base=D[P+'wrapper.json'];e=json.loads(base['raw']);receipt=json.loads(e['receiptRaw']);request=json.loads(e['original']);sha=lambda b:hashlib.sha256(b).hexdigest();compact=lambda x:json.dumps(x,ensure_ascii=False,separators=(',',':'));canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'));pretty=lambda x:json.dumps(x,indent=2,ensure_ascii=False);variants={}
    for name in ['executor','runtime','elapsed','memory','outcome']:
        r=copy.deepcopy(receipt);storage=r['resourceUsed']['storageBytes']-len(canon(r).encode())
        if name=='executor':r['executorId']='other-unattested-executor'
        if name=='runtime':r['runtimeDigest']='0'*64
        if name=='elapsed':r['resourceUsed']['elapsedMs']+=3
        if name=='memory':r['resourceUsed']['memoryBytes']+=5
        if name=='outcome':r['state']='inconclusive';r['reasons']=['ELAPSED_REPLAY_CHECK_INCOMPLETE']
        for _ in range(12):r['resourceUsed']['storageBytes']=storage+len(canon(r).encode())
        variants[name]={'raw':compact({**e,'receiptRaw':compact(r)}),'source':base['source']}
    variants['raw-framing']={'raw':pretty(e),'source':base['source']};variants['receipt-framing']={'raw':compact({**e,'receiptRaw':compact(receipt)}),'source':base['source']}
    q=compact(dict(reversed(list(request.items()))));r=copy.deepcopy(receipt);storage=r['resourceUsed']['storageBytes']-len(canon(r).encode());r['requestDigest']=sha(q.encode())
    for _ in range(12):r['resourceUsed']['storageBytes']=storage+len(canon(r).encode())
    variants['request-framing']={'raw':compact({**e,'original':q,'receiptRaw':compact(r)}),'source':base['source']};variants['source-repository']={**base,'source':{**base['source'],'repository':'MontrealAI/AGIJobManager'}};r=copy.deepcopy(receipt);r['authority']='promote';variants['forged-authority']={'raw':compact({**e,'receiptRaw':compact(r)}),'source':base['source']};variants['swapped-mission']={'raw':compact({**e,'original':e['original'].replace(request['missionId'],'capability-00000000-0000-4000-8000-000000000000',1)}),'source':base['source']};rows=[]
    for name,w in variants.items():
        raw=(pretty(w)+'\n').encode();assert w==D[P+name+'.json'] and len(raw)==I[P+name+'.json']['bytes'] and sha(raw)==I[P+name+'.json']['sha256'];rows.append({'variant':name,'bytes':len(raw),'sha256':sha(raw),'originalPayloadByteExact':True})
    report={'schema':'new-main-target-native-variant-payload-authentication/v1','run':39724342613,'synthetic':'c0773f99623d7ab8d82f3a978c76b41cd596dfa7','variants':rows,'all11OriginalPayloadsIndependentlyReconstructed':True,'interpretation':'First five observation changes and framing alternatives intentionally retain semantic receipt identity in the native helper; all11 are refused by the hosted UI after canonical import without docket/history changes. No claim that every equivalent framing is rejected by the native parser.','execution':'Independent inert Python JSON serialization only.'};(B/'native-variant-payload-byte-authentication.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    import io,sys,zipfile,urllib.request,subprocess
    from pathlib import PurePosixPath
    B=Path('/dev/shm/alpha-33b-main-target-cap-custody');sha=lambda b:hashlib.sha256(b).hexdigest();metadata=json.loads((B/'api-capArtifacts-final.json').read_text());a=next(x for x in metadata['artifacts'] if x['name']=='successor-capability-c0773f99623d7ab8d82f3a978c76b41cd596dfa7');assert a['workflow_run']['id']==39724342613 and a['workflow_run']['head_sha']=='33b19714e1219c812d451e4d736fcb34b722ceff'
    data=urllib.request.urlopen(sys.argv[1],timeout=90).read();assert len(data)==a['size_in_bytes'] and sha(data)==a['digest'].removeprefix('sha256:')
    old=json.loads(Path('/dev/shm/alpha-f0-independent-custody/capability-byte-custody.json').read_text());wanted=set(old['retainedSelectedMembers']);canonical=['source.json','exact-checkout.json','discovery-continuation/served/index.html','discovery-continuation/served/sources.json','discovery-continuation/fleet-browser-workspace.json','discovery-continuation/jobs-browser-workspace.json','discovery-continuation/fleet-browser-request.json','discovery-continuation/jobs-browser-request.json','discovery-continuation/browser-native-requests.json','discovery-continuation/journey.json','discovery-continuation/fleet-native/native-proof.json'];D={};I={};retain={}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist();assert len(names)==len(set(names)) and set(canonical).issubset(names)
        for info in z.infolist():
            name=info.filename;p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts and '\\' not in name and info.external_attr>>16&0o170000 != 0o120000;raw=z.read(name);I[name]={'path':name,'bytes':len(raw),'sha256':sha(raw),'crc32':f'{info.CRC:08x}'}
            if (name in wanted or name.startswith('accessibility-review/')) and name.endswith('.json'):D[name]=json.loads(raw)
            if name in canonical:raw.decode('utf8',errors='strict');retain[name]=raw
    byte={'schema':'new-main-target-original-capability-byte-custody/v1','run':39724342613,'attempt':1,'head':'33b19714e1219c812d451e4d736fcb34b722ceff','synthetic':'c0773f99623d7ab8d82f3a978c76b41cd596dfa7','tree':'b310ec7fe96000668f7be2d1b1866245b255d56b','artifactId':a['id'],'artifactName':a['name'],'zipBytes':len(data),'zipSha256':sha(data),'members':len(I),'expandedBytes':sum(x['bytes'] for x in I.values()),'uniqueSafePathsCrcAndMemberHashes':True,'rawZipRetention':'RAMonly; not persisted','retainedRawMembers':canonical,'scope':'Superseded original33b/c077 PR synthetic only; no transfer to24d or accepted-main/release qualification'}
    (B/'byte-custody.json').write_text(json.dumps(byte,indent=2)+'\n');(B/'capability-zip-inventory.json').write_text(json.dumps(list(I.values()),indent=2)+'\n');(B/'canonical-eleven-members.json').write_text(json.dumps([I[n] for n in canonical],indent=2)+'\n')
    for name,raw in retain.items():
        target=B/'selected'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    subprocess.run([sys.executable,'-B',str(B/'authenticate-source.py')],check=True)
    authenticate_semantics(D,I);audit_broader_aria(D,I);audit_variant_payloads(D,I)
    print(json.dumps({'byteCustody':byte,'audit':'COMPLETE','rawMembersRetained':len(retain),'noBrowserArtifactExecutionOrZipPersistence':True},indent=2))


if __name__=='__main__':main()
