"""Read-only original33b artifact verifier. Download ZIP stays in RAM; no extraction or code execution."""
import datetime, hashlib, io, json, pathlib, stat, sys, urllib.request, zipfile, zlib
OUT=pathlib.Path('/workspace/scratch/32717074a7f1/alpha33b-other-originals-continuation')
HEAD='33b19714e1219c812d451e4d736fcb34b722ceff'
CHECKOUT='c0773f99623d7ab8d82f3a978c76b41cd596dfa7'
def run(spec):
 a=spec['artifact']; assert a['workflow_run']['head_sha']==HEAD and a['expired'] is False
 n=a['size_in_bytes']; assert type(n) is int and 0<n<=250_000_000 and a['digest'].startswith('sha256:')
 buf=io.BytesIO(); state=hashlib.sha256(); count=0
 with urllib.request.urlopen(spec['download_url'],timeout=120) as response:
  status=response.status
  while True:
   b=response.read(min(1_000_000,n-count+1))
   if not b: break
   count+=len(b); assert count<=n; state.update(b); buf.write(b)
 assert count==n and 'sha256:'+state.hexdigest()==a['digest']
 buf.seek(0); members=[]; names=set()
 with zipfile.ZipFile(buf) as z:
  infos=z.infolist(); assert len(infos)<=20_000 and sum(i.file_size for i in infos)<=1_500_000_000
  for i in infos:
   name=i.filename; clean=name.rstrip('/') if i.is_dir() else name; p=pathlib.PurePosixPath(clean)
   assert clean and '\\' not in name and '\x00' not in name and not p.is_absolute() and str(p)==clean and '..' not in p.parts and clean not in names
   names.add(clean); kind=stat.S_IFMT(i.external_attr>>16)
   assert not i.flag_bits&1 and kind in ({0,stat.S_IFDIR} if i.is_dir() else {0,stat.S_IFREG})
   h=hashlib.sha256(); size=0; crc=0
   with z.open(i) as f:
    while True:
     b=f.read(1_000_000)
     if not b: break
     size+=len(b); h.update(b); crc=zlib.crc32(b,crc)
   assert size==i.file_size and crc==i.CRC and (not i.is_dir() or size==0)
   members.append({'path':name,'bytes':size,'sha256':h.hexdigest(),'crc32':f'{crc:08x}','compressedBytes':i.compress_size,'directory':i.is_dir(),'unixMode':oct(i.external_attr>>16)})
 r={'schema':'successor/original33b-artifact-ram-custody/v1','observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'SUPERSEDED 33b/c077 PR only; no current24d/accepted-main/release qualification','headCommit':HEAD,'expectedSyntheticCheckout':CHECKOUT,'runId':a['workflow_run']['id'],'runAttempt':1,'artifactId':a['id'],'artifactName':a['name'],'declaredAPISize':n,'declaredAPIDigest':a['digest'],'outerBytes':count,'outerSha256':state.hexdigest(),'downloadHTTPStatus':status,'outerByteIdentityVerified':True,'allMembersCRCAndSha256Verified':True,'allMembersUniqueSafePaths':True,'memberCount':len(members),'members':members,'archiveHandling':'RAM only; URL not retained; no ZIP persisted, extraction or artifact execution'}
 f=OUT/(str(a['id'])+'-custody.json'); b=(json.dumps(r,indent=2)+'\n').encode(); f.write_bytes(b)
 print(json.dumps({'artifactId':a['id'],'bytes':count,'sha256':state.hexdigest(),'members':len(members),'reportPath':str(f),'reportBytes':len(b),'reportSha256':hashlib.sha256(b).hexdigest()}))
if __name__=='__main__': run(json.load(sys.stdin))
