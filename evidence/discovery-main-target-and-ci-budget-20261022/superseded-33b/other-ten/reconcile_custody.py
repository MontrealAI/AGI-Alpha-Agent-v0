"""Small-report reconciliation of original33b workflows; reads inherited records without changing them."""
import datetime,hashlib,json,pathlib,re,sys
OUT=pathlib.Path('/workspace/scratch/32717074a7f1/alpha33b-other-originals-continuation')
OLD=pathlib.Path('/dev/shm/alpha33b-other-original-custody')
HEAD='33b19714e1219c812d451e4d736fcb34b722ceff'; CHECKOUT='c0773f99623d7ab8d82f3a978c76b41cd596dfa7'; TREE='b310ec7fe96000668f7be2d1b1866245b255d56b'
def read(p): return json.loads(p.read_bytes())
def meta(p):
 b=p.read_bytes(); return {'file':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'gitBlob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def stamp(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def upload_digests(lines):
 current=None; result={}
 for line in lines:
  d=re.search(r'SHA256 digest of uploaded artifact is ([0-9a-f]{64})',line)
  if d: current=d.group(1)
  if current:
   for i in re.findall(r'Artifact ID[: ]+(\d+)\b',line): result.setdefault(i,set()).add(current)
 return {k:sorted(v) for k,v in result.items()}
def main(snapshot):
 inherited=read(OLD/'completed-custody.json'); assert meta(OLD/'completed-custody.json')['sha256']=='2d2e992922ea2331857e4aafac6e8db7f7fca929753c9c4f20465fe095e68cd2'
 logs={}
 for p in OLD.glob('*-log*-raw.json'):
  x=read(p); log=x['decodedLog']; data=log.encode('utf-8')
  lines=[l for l in log.splitlines() if re.search(r'HEAD is now at|'+CHECKOUT+r'|Artifact ID[: ]|Digest[: ]|Finalizing artifact upload|Total cost|cost.*(?:USD|USDC)|[0-9]+ (?:passed|failed|skipped)|Process completed with exit code',l,re.I) and not re.search(r'https?://\S*[?&](?:sig|token|X-Amz-|se=|sp=|sv=)',l,re.I)]
  logs[x['jobId']]={'jobId':x['jobId'],'inheritedFullOriginalLog':meta(p),'decodedLogBytes':len(data),'decodedLogSHA256':hashlib.sha256(data).hexdigest(),'observedSyntheticCheckout':CHECKOUT if re.search(r'HEAD is now at c0773f9\b|Z '+CHECKOUT+r'\r?$',log,re.M) else None,'uploadedArtifactIDs':sorted(set(int(i) for i in re.findall(r'Artifact ID[: ]+(\d+)\b',log))),'excerptLines':lines[-160:]}
 for p in OUT.glob('job-*-log-identity.json'):
  x=read(p); x['smallLogIdentityRecord']=meta(p)
  if 'uploadedArtifactIDs' not in x: x['uploadedArtifactIDs']=sorted(set(int(i) for i in re.findall(r'Artifact ID[: ]+(\d+)\b','\n'.join(x['excerptLines']))))
  logs[x['jobId']]=x
 for log in logs.values():
  log['uploadedArtifactDigests']=upload_digests(log['excerptLines'])
  if not log['observedSyntheticCheckout'] and re.search(r'Z '+CHECKOUT+r'\r?$', '\n'.join(log['excerptLines']),re.M):
   log['observedSyntheticCheckout']=CHECKOUT;log['checkoutBindingRecoveredFromExactRetainedExcerpt']=True
 states=read(pathlib.Path(snapshot))['states']; records=[]; used=set()
 handoff=read(OLD/'monitor-handoff-20261022T0526.json')
 for row in handoff['cohort']:
  name=row['name']
  if name in states: s=states[name]; run,jobs,artifacts=s['run'],s['jobs'],s['artifacts']; api={'snapshot':meta(pathlib.Path(snapshot))}
  else:
   run,jobs,artifacts=(read(OLD/(name+'-'+part+'.json')) for part in ('run','jobs','artifacts'));api={part:meta(OLD/(name+'-'+part+'.json')) for part in ('run','jobs','artifacts')}
  assert run['id']==row['id'] and run['head_sha']==HEAD and run['run_attempt']==1 and run['event']=='pull_request'
  assert jobs['total_count']==len(jobs['jobs']) and artifacts['total_count']==len(artifacts['artifacts'])
  jobids={j['id'] for j in jobs['jobs']};assert len(jobids)==len(jobs['jobs'])
  for j in jobs['jobs']: assert j['run_id']==run['id'] and j['head_sha']==HEAD and j['run_attempt']==1
  custody=[]; missing=[]
  for a in artifacts['artifacts']:
   assert a['id'] not in used;used.add(a['id']);assert a['workflow_run']['id']==run['id'] and a['workflow_run']['head_sha']==HEAD and a['expired'] is False
   p=OUT/(str(a['id'])+'-custody.json')
   if not p.exists():p=OLD/(str(a['id'])+'-custody.json')
   if not p.exists():missing.append(a['id']);continue
   c=read(p);assert c['outerBytes']==a['size_in_bytes'] and 'sha256:'+c['outerSha256']==a['digest'] and c['allMembersCRCAndSha256Verified'] and c['allMembersUniqueSafePaths']
   producers=[j for j in jobs['jobs'] if j['id'] in logs and a['id'] in logs[j['id']]['uploadedArtifactIDs']]
   if not producers:
    assert any(j['status']!='completed' for j in jobs['jobs']),('missing terminal producer log',a['id'])
    custody.append({'artifactId':a['id'],'artifactName':a['name'],'outerBytes':c['outerBytes'],'outerSha256':c['outerSha256'],'members':len(c['members']),'allMembersCRCAndSHA256':True,'uniqueSafePaths':True,'custodyRecord':meta(p),'producerJobId':None,'uniqueUploadAndTimeWindowBound':False,'producerBindingPending':True,'reason':'Artifact available while an original job is still active; terminal producer log not yet available'})
    continue
   assert len(producers)==1,('producer binding',a['id'],[j['id'] for j in producers]);j=producers[0];log=logs[j['id']]
   assert j['status']=='completed' and stamp(j['started_at'])<=stamp(a['created_at'])<=stamp(j['completed_at'])
   assert c['outerSha256'] in log['uploadedArtifactDigests'].get(str(a['id']),[]),('upload digest differs',a['id'])
   custody.append({'artifactId':a['id'],'artifactName':a['name'],'outerBytes':c['outerBytes'],'outerSha256':c['outerSha256'],'members':len(c['members']),'allMembersCRCAndSHA256':True,'uniqueSafePaths':True,'custodyRecord':meta(p),'producerJobId':j['id'],'producerJobName':j['name'],'producerConclusion':j['conclusion'],'uniqueUploadAndTimeWindowBound':True,'observedSyntheticCheckout':log['observedSyntheticCheckout'],'decodedProducerLogSHA256':log['decodedLogSHA256']})
  records.append({'name':name,'runId':run['id'],'runAttempt':1,'sourceHead':HEAD,'expectedSyntheticCheckout':CHECKOUT,'tree':TREE,'status':run['status'],'conclusion':run['conclusion'],'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion']} for j in jobs['jobs']],'artifactsExpected':len(artifacts['artifacts']),'artifactCustody':custody,'missingCustodyArtifactIDs':missing,'missingCompletedJobLogIDs':[j['id'] for j in jobs['jobs'] if j['status']=='completed' and j['conclusion']!='skipped' and j['id'] not in logs],'apiRecords':api})
 complete=all(r['status']=='completed' and not r['missingCustodyArtifactIDs'] and not r['missingCompletedJobLogIDs'] for r in records)
 logreport={'scope':'Superseded33b/c077 original PR only','records':list(logs.values()),'inheritedFilesReadOnly':True,'newFullLogsPersisted':False}
 lp=OUT/'reconciled-log-identities.json';lp.write_text(json.dumps(logreport,indent=2)+'\n')
 allc=[c for r in records for c in r['artifactCustody']]
 report={'schema':'successor/original33b-other-ten-custody-progress/v1','observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'SUPERSEDED 33b/c077 PR only. No qualification transfer to current24d, main or release. Capability separately authenticated, excluded here.','sourceHead':HEAD,'actualSyntheticCheckout':CHECKOUT,'sourceTree':TREE,'completed':complete,'assignedRuns':10,'completedRuns':sum(r['status']=='completed' for r in records),'runConclusions':{r['name']:r['conclusion'] for r in records},'actualAuthenticatedArtifacts':len(allc),'actualZIPBytes':sum(c['outerBytes'] for c in allc),'actualZIPMembers':sum(c['members'] for c in allc),'skippedJobs':[j for r in records for j in r['jobs'] if j['conclusion']=='skipped'],'failureOrCancelledJobs':[j for r in records for j in r['jobs'] if j['status']=='completed' and j['conclusion'] not in ('success','skipped')],'records':records,'logIdentityReport':meta(lp),'inheritedReport':meta(OLD/'completed-custody.json'),'sourceAPIRecords':[meta(p) for p in OUT.glob('git-*.json')],'publicWrites':False,'workflowOperations':False,'acceptedMainQualified':False,'current24dQualified':False,'archiveHandling':'All new ZIPs authenticated in RAM; no ZIP files, extraction or execution. Prior9 ZIPs custody inherited with exact report hash and inventory/API/producer-log revalidation.'}
 target=OUT/('other-ten-final-custody.json' if complete else 'other-ten-progress-custody.json')
 target.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'report':meta(target),'completed':complete,'completedRuns':report['completedRuns'],'artifacts':len(allc),'bytes':report['actualZIPBytes'],'members':report['actualZIPMembers'],'missingCustody':{r['name']:r['missingCustodyArtifactIDs'] for r in records if r['missingCustodyArtifactIDs']},'missingLogs':{r['name']:r['missingCompletedJobLogIDs'] for r in records if r['missingCompletedJobLogIDs']},'failedJobs':report['failureOrCancelledJobs'],'skippedJobs':report['skippedJobs']}))
if __name__=='__main__':main(sys.argv[1])
