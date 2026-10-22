"""Summarize exact decoded CI logs; no artifact contents executed."""
from pathlib import Path
import hashlib,json,re
root=Path('/dev/shm/alpha24d-other-original-custody')
for p in root.glob('.temporary-log-*.json'):
    text=json.loads(p.read_bytes())['raw'];raw=text.encode();job=int(p.name.split('-')[2].split('.')[0]);lines=text.splitlines()
    pattern=re.compile(r'"mode":\s*"(?:full|paper)"|d3ba2c3a4a275d7f2c7619504b703f931b8c4507|24d58598f896106323f2c120487586bdf5104612|Artifact ID|Artifact download URL|Artifact .*successfully|SHA256 digest|Final size of the artifact|Upload complete|##\[error\]|Process completed with exit code')
    indexes=set()
    for index,line in enumerate(lines):
        if pattern.search(line):
            indexes.update(range(max(0,index-2),min(len(lines),index+2)))
    selected=[{'line':i+1,'text':lines[i]}for i in sorted(indexes)]
    strong=any('git log -1 --format=%H' in line and index+1<len(lines) and lines[index+1].rstrip().endswith('d3ba2c3a4a275d7f2c7619504b703f931b8c4507')for index,line in enumerate(lines))
    report={'schema':'original-attempt-job-log-observation/v1','jobId':job,'scope':'24d/d3ba attempt1 PR only','decodedLogUtf8Bytes':len(raw),'decodedLogUtf8Sha256':hashlib.sha256(raw).hexdigest(),'sourceCheckoutObserved':any('d3ba2c3a4a275d7f2c7619504b703f931b8c4507'in x['text']for x in selected),'exactCheckoutGitLogResultObserved':strong,'fullScopeJSONOutputObserved':any(re.match(r'^\S+\s+"mode":\s*"full"',line)for line in lines),'originalHeadMentioned':any('24d58598f896106323f2c120487586bdf5104612'in x['text']for x in selected),'selectedSourceUploadErrorLines':selected,'rawLogPersisted':False,'rawLogSource':'GitHub fetch_workflow_job_logs exact decoded response; UTF8 hash after lossless JSON framing'}
    target=root/('job-'+str(job)+'-log-evidence.json');target.write_text(json.dumps(report,indent=2)+'\n');p.unlink();print(json.dumps({'job':job,'bytes':len(raw),'checkout':report['sourceCheckoutObserved'],'selected':len(selected),'reportSha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
