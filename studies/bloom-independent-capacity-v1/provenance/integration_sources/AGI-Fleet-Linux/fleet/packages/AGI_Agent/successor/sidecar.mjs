import fs from 'node:fs';
import {validateReceiptBinding} from './receipt.mjs';
import {validateSidecarProject} from './project.mjs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fail,keys,parseStrict,canonical} from './vendor/manager/site/assets/successor/safe.mjs';
import {inspectCapsule,restoreCapsule,exportCapsule} from './vendor/manager/site/assets/successor/model.mjs';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const LIMIT=192*1024*1024,FILE_LIMIT=96*1024*1024;
function safe(name){const packed=typeof name==='string'&&name.startsWith('artifacts/');fail(typeof name==='string'&&name.length<=(packed?250:240)&&/^[A-Za-z0-9][A-Za-z0-9_.\/-]*$/.test(name)&&name.split('/').length<=(packed?13:12)&&name.split('/').every(p=>p&&p!=='.'&&p!=='..'&&!p.startsWith('.')),'FLEET_ARTIFACT_PATH');return name;}
function directory(p){const s=fs.lstatSync(p);fail(s.isDirectory()&&!s.isSymbolicLink(),'FLEET_SIDECAR_PATH');}
function checkedFile(root,name){safe(name);directory(root);let p=root;for(const part of name.split('/').slice(0,-1)){p=path.join(p,part);directory(p);}return path.join(root,name);}
function bytes(file,max){const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);try{const s=fs.fstatSync(fd);fail(s.isFile()&&s.nlink===1&&s.size<=max,'FLEET_SIDECAR_FILE');const b=fs.readFileSync(fd);fail(b.length===s.size,'FLEET_SIDECAR_CHANGED');return b;}finally{fs.closeSync(fd);}}
export async function inspectSidecar(root){
  const manifest=parseStrict(bytes(checkedFile(root,'manifest.json'),100000).toString(),100000);
  keys(manifest,['schema','files','totalBytes','walletBackup','authority','sha256'],'FLEET_SIDECAR_FIELDS');
  const {sha256,...body}=manifest;fail(manifest.schema==='agi-fleet/successor-sidecar/v1'&&sha256===hash(canonical(body))&&manifest.authority==='none'&&manifest.walletBackup==='excluded','FLEET_SIDECAR_MANIFEST');
  fail(Array.isArray(manifest.files)&&manifest.files.length>0&&manifest.files.length<=68,'FLEET_SIDECAR_COUNT');
  let total=0;const seen=new Set();
  for(const entry of manifest.files){keys(entry,['path','bytes','sha256','mediaType','role'],'FLEET_SIDECAR_ENTRY');safe(entry.path);fail(!seen.has(entry.path.toLowerCase()),'FLEET_SIDECAR_DUPLICATE');seen.add(entry.path.toLowerCase());fail(Number.isSafeInteger(entry.bytes)&&entry.bytes>=0&&entry.bytes<=FILE_LIMIT&&/^[a-f0-9]{64}$/.test(entry.sha256),'FLEET_SIDECAR_LIMIT');total+=entry.bytes;fail(total<=LIMIT,'FLEET_SIDECAR_LIMIT');
    const file=checkedFile(root,entry.path),fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);try{const st=fs.fstatSync(fd);fail(st.isFile()&&st.nlink===1&&st.size===entry.bytes,'FLEET_SIDECAR_MISSING');const digest=crypto.createHash('sha256'),buffer=Buffer.alloc(1024*1024);let count=0,n;while((n=fs.readSync(fd,buffer,0,buffer.length,null))>0){count+=n;fail(count<=entry.bytes,'FLEET_SIDECAR_CHANGED');digest.update(buffer.subarray(0,n));}fail(count===entry.bytes&&digest.digest('hex')===entry.sha256,'FLEET_SIDECAR_CHANGED');}finally{fs.closeSync(fd);}}
  fail(total===manifest.totalBytes,'FLEET_SIDECAR_LIMIT');
  const actual=[];function walk(dir,prefix=''){for(const e of fs.readdirSync(dir,{withFileTypes:true})){fail(!e.isSymbolicLink(),'FLEET_SIDECAR_PATH');const name=prefix+e.name;if(e.isDirectory())walk(path.join(dir,e.name),name+'/');else actual.push(name);}}
  walk(root);fail(actual.length===manifest.files.length+1&&actual.every(n=>n==='manifest.json'||seen.has(n.toLowerCase())),'FLEET_SIDECAR_EXTRA');
  const core=[['capsule.json','portable-project'],['handoff.json','exact-review-handoff'],['receipt.json','historical-evidence']];
  for(const [name,role] of core){const entry=manifest.files.find(f=>f.path===name);fail(entry&&entry.mediaType==='application/json'&&entry.role===role,'FLEET_SIDECAR_CORE');}
  const handoff=parseStrict(bytes(checkedFile(root,'handoff.json'),FILE_LIMIT).toString(),FILE_LIMIT);
  await validateReceiptBinding(handoff,parseStrict(bytes(checkedFile(root,'receipt.json'),1000000).toString(),1000000),'node');
  // Integrity inspection does not execute a job or grant qualification. Bind the
  // exact decoded delivery bytes to every sidecar artifact, including its metadata.
  const bundle=parseStrict(handoff.delivery,FILE_LIMIT),outputs=handoff.specification.outputs;
  keys(bundle,['schema','specHash','files'],'FLEET_SIDECAR_DELIVERY');
  fail(bundle.schema===(handoff.specification.profile==='computer-work/v2'?'agi-work-bundle/v2':'agi-work-bundle/v1')&&bundle.specHash===handoff.specHash&&Array.isArray(bundle.files)&&Array.isArray(outputs)&&bundle.files.length>0&&bundle.files.length===outputs.length&&manifest.files.length===core.length+bundle.files.length,'FLEET_SIDECAR_DELIVERY');
  const names=new Set(),files=new Map();
  for(let i=0;i<bundle.files.length;i++){
    const f=bundle.files[i],output=outputs[i];keys(f,['name','mediaType','bytes','sha256','content'],'FLEET_SIDECAR_DELIVERY');safe(f.name);
    fail(!names.has(f.name.toLowerCase()),'FLEET_SIDECAR_DUPLICATE');names.add(f.name.toLowerCase());
    fail(f.name===output.name&&f.mediaType===output.mediaType&&Number.isSafeInteger(f.bytes)&&f.bytes>0&&f.bytes<=output.maxBytes&&f.bytes<=FILE_LIMIT&&typeof f.content==='string'&&f.content.length<=4*Math.ceil(f.bytes/3),'FLEET_SIDECAR_DELIVERY');
    const decoded=Buffer.from(f.content,'base64');fail(decoded.length===f.bytes&&decoded.toString('base64')===f.content&&hash(decoded)===f.sha256,'FLEET_SIDECAR_DELIVERY');
    const row=manifest.files.find(r=>r.path==='artifacts/'+f.name);fail(row&&row.role==='deliverable'&&row.mediaType===f.mediaType&&row.bytes===f.bytes&&row.sha256===f.sha256,'FLEET_SIDECAR_DELIVERY');
    files.set(f.name,decoded);
  }
  await validateSidecarProject(bytes(checkedFile(root,'capsule.json'),4000000).toString(),handoff,files);
  return manifest;
}
export async function exportSidecar(destination,capsule,handoff,receipt,studioAPI){
  studioAPI.validateHandoff(handoff);await validateReceiptBinding(handoff,receipt,'node');
  const {files}=studioAPI.validateBundle(handoff.specification,Buffer.from(handoff.delivery));
  await validateSidecarProject(capsule,handoff,files);
  fail(!fs.existsSync(destination),'OUTPUT_EXISTS');directory(path.dirname(path.resolve(destination)));
  const temporary=path.resolve(destination)+'.partial-'+crypto.randomUUID();fs.mkdirSync(temporary,{mode:0o700});const rows=[];
  try{function write(name,content,mediaType,role){safe(name);const data=Buffer.isBuffer(content)?content:Buffer.from(content);fail(data.length<=FILE_LIMIT,'FLEET_SIDECAR_LIMIT');const p=path.join(temporary,name);fs.mkdirSync(path.dirname(p),{recursive:true,mode:0o700});fs.writeFileSync(p,data,{flag:'wx',mode:0o600});rows.push({path:name,bytes:data.length,sha256:hash(data),mediaType,role});}
    write('capsule.json',capsule,'application/json','portable-project');write('handoff.json',canonical(handoff),'application/json','exact-review-handoff');write('receipt.json',canonical(receipt),'application/json','historical-evidence');
    for(const [name,data] of files)write('artifacts/'+name,data,handoff.specification.outputs.find(f=>f.name===name).mediaType,'deliverable');
    const body={schema:'agi-fleet/successor-sidecar/v1',files:rows,totalBytes:rows.reduce((s,r)=>s+r.bytes,0),walletBackup:'excluded',authority:'none'};
    fs.writeFileSync(path.join(temporary,'manifest.json'),canonical({...body,sha256:hash(canonical(body))})+'\n',{flag:'wx',mode:0o600});await inspectSidecar(temporary);fs.renameSync(temporary,destination);return inspectSidecar(destination);
  }catch(error){fs.rmSync(temporary,{recursive:true,force:true});throw error;}
}
export async function restoreSidecar(source,destination,confirmed){
  const manifest=await inspectSidecar(source),raw=bytes(checkedFile(source,'capsule.json'),4000000).toString();const inspected=await inspectCapsule(raw);
  if(confirmed!==true)return {manifest,summary:inspected.summary,requiresConfirmation:true,authority:'none'};
  fail(!fs.existsSync(destination),'OUTPUT_EXISTS');const temporary=path.resolve(destination)+'.partial-'+crypto.randomUUID();fs.mkdirSync(temporary,{mode:0o700});const original=path.join(temporary,'original-pack');fs.mkdirSync(original,{mode:0o700});
  try{for(const row of manifest.files){const target=path.join(original,row.path);fs.mkdirSync(path.dirname(target),{recursive:true,mode:0o700});fs.copyFileSync(checkedFile(source,row.path),target,fs.constants.COPYFILE_EXCL);}fs.copyFileSync(checkedFile(source,'manifest.json'),path.join(original,'manifest.json'),fs.constants.COPYFILE_EXCL);await inspectSidecar(original);
    const saved=await inspectCapsule(bytes(checkedFile(original,'capsule.json'),4000000).toString());
    const restored=await exportCapsule(await restoreCapsule(saved,true),saved.capsule.payload.sourceManifest);
    fs.writeFileSync(path.join(temporary,'RESTORED-CAPSULE.json'),restored,{flag:'wx',mode:0o600});
    fs.renameSync(temporary,destination);return {directory:destination,capsule:'RESTORED-CAPSULE.json',authority:'none',qualification:'NOT_RUN',originalPackUnchanged:true};
  }catch(error){fs.rmSync(temporary,{recursive:true,force:true});throw error;}
}
