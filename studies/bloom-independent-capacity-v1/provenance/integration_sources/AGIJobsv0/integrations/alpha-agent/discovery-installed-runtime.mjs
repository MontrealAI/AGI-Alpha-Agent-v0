// SPDX-License-Identifier: MIT
// The externally authenticated archive is the trust root; all imported code is captured below.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {types} from 'node:util';
import {parseBounded, canonical} from './discovery-lab-contract.mjs';
import {parseModuleSources, checkDependencyRecords, createModuleBoundary} from './discovery-installed-module-graph-runtime.mjs';

export const INSTALLED_MANIFEST = 'INSTALLED_SOURCE.json';
const MAX_FILE = 2_000_000, MAX_TOTAL = 16_000_000, MAX_FILES = 256, MAX_ARCHIVE = 20_000_000;
const ADAPTER = 'integrations/alpha-agent/discovery-lab-work-request.mjs';
const CONTRACT = 'integrations/alpha-agent/discovery-lab-contract.mjs';
const INSPECTOR = 'examples/successor-capability/discovery-lab-inspector.mjs';
const CATALOG = 'docs/successor/capabilities/sources.json';
const sha = value => createHash('sha256').update(value).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const git = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const nameOK = name => typeof name === 'string' && name && name.length <= 4096
  && /^[A-Za-z0-9_.\/-]+$/.test(name) && !path.posix.isAbsolute(name)
  && name.split('/').every(item => item && item !== '.' && item !== '..' && item !== '.git');
export function boundedInstalledBytes(filename, limit = MAX_FILE) {
  assert.equal(fs.realpathSync(filename), path.resolve(filename), 'Installed paths must be direct regular files');
  const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const before = fs.fstatSync(fd, {bigint:true});
    assert.ok(before.isFile() && before.size <= BigInt(limit), 'Installed input exceeds its regular-file bound');
    const result = Buffer.alloc(Number(before.size) + 1); let count = 0;
    while (count < result.length) {const n = fs.readSync(fd,result,count,result.length-count,null);if(!n)break;count+=n;}
    const after = fs.fstatSync(fd,{bigint:true});
    assert.equal(count,Number(before.size),'Installed source size changed during capture');
    for(const key of ['dev','ino','mode','size','mtimeNs','ctimeNs'])assert.equal(after[key],before[key],'Installed source changed during capture');
    return result.subarray(0,count);
  } finally {fs.closeSync(fd);}
}
export function installedNames(root,expectedNames) {
  assert.ok(Array.isArray(expectedNames)&&expectedNames.length<=MAX_FILES+2,'Installed inventory exceeds bound');
  const expected=new Set(expectedNames),directories=new Set();
  assert.equal(expected.size,expectedNames.length,'Duplicate installed inventory member');
  for(const name of expected) {
    assert.ok(nameOK(name),'Unsafe installed member');
    const parts=name.split('/');assert.ok(parts.length<=32,'Installed path depth exceeds bound');
    for(let i=1;i<parts.length;i++)directories.add(parts.slice(0,i).join('/'));
  }
  const names=new Set();let count=0;
  function walk(directory,prefix='') {
    const handle=fs.opendirSync(directory,{bufferSize:32});
    try {
      for(let item=handle.readSync();item;item=handle.readSync()) {
        assert.ok(++count<=expected.size+directories.size,'Installed entry count exceeds bound');
        const name=prefix+item.name;assert.ok(nameOK(name),'Unsafe installed member');
        assert.ok(!item.isSymbolicLink(),'Installed source cannot contain symbolic links');
        if(item.isDirectory()) {
          assert.ok(directories.has(name),'Unexpected installed directory');
          walk(path.join(directory,item.name),name+'/');
        } else {
          assert.ok(item.isFile()&&expected.has(name),'Unexpected installed member');names.add(name);
        }
      }
    } finally {handle.closeSync();}
  }
  walk(root);return names;
}
function runtimeOptions(input) {
  assert.ok(input&&typeof input==='object'&&!Array.isArray(input)&&!types.isProxy(input)
    && [Object.prototype,null].includes(Object.getPrototypeOf(input)));
  const fields=['archiveBytes','archiveSha256','installedRoot','manifestSha256'];
  assert.deepEqual(Reflect.ownKeys(input).sort(),fields,'An independently selected archive and manifest identity is required');
  const values={};
  for(const key of fields) {
    const item=Object.getOwnPropertyDescriptor(input,key);assert.ok(item&&Object.hasOwn(item,'value'),'Runtime options need inert own data');
    if(key==='archiveBytes')assert.ok(Number.isSafeInteger(item.value)&&item.value>0&&item.value<=MAX_ARCHIVE,
      'Independently selected archive bytes must be a bounded positive safe integer');
    else assert.equal(typeof item.value,'string');
    values[key]=item.value;
  }
  assert.ok(hash(values.archiveSha256),'An independently selected archive SHA-256 is required');
  assert.ok(hash(values.manifestSha256),'An independently selected installed-manifest SHA-256 is required');
  return Object.freeze(values);
}
export function installationCapsule(input,custody) {
  const {archiveSha256,archiveBytes,manifestSha256}=runtimeOptions(input);
  const expected={schema:'agijobsv0/discovery-installed-extraction/v1',archiveSha256,archiveBytes,
    installedManifestSha256:manifestSha256,authority:'none',state:'EXTRACTED_INACTIVE_LOCAL_REVIEW_ONLY'};
  assert.ok(custody&&typeof custody==='object'&&!Array.isArray(custody)&&!types.isProxy(custody)
    &&[Object.prototype,null].includes(Object.getPrototypeOf(custody)),'Extraction custody must be inert data');
  assert.deepEqual(Reflect.ownKeys(custody).sort(),Object.keys(expected).sort(),'Extraction custody fields differ');
  for(const [name,value] of Object.entries(expected)) {
    const item=Object.getOwnPropertyDescriptor(custody,name);
    assert.ok(item&&Object.hasOwn(item,'value'),'Extraction custody must contain inert own data');
    assert.equal(item.value,value,'Extraction custody differs from independently selected provenance: '+name);
  }
  return Object.freeze({sha256:archiveSha256,bytes:archiveBytes,manifestSha256});
}
export function captureInstalled(input) {
  const options=runtimeOptions(input),{installedRoot,manifestSha256}=options;
  assert.ok(path.isAbsolute(installedRoot||''),'An explicit installed root is required');
  const root=fs.realpathSync(installedRoot);assert.ok(hash(manifestSha256),'An independently selected installed-manifest SHA-256 is required');
  const manifestBytes=boundedInstalledBytes(path.join(root,INSTALLED_MANIFEST));
  assert.equal(sha(manifestBytes),manifestSha256,'Installed manifest differs from selected archive provenance');
  const manifest=parseBounded(manifestBytes.toString('utf8'));
  assert.equal(manifest.schema,'agijobsv0/discovery-installed/v1');assert.equal(manifest.profile,'jobs-discovery-installed-v1');
  assert.equal(manifest.version,'2.1.0-rc.20');
  assert.equal(manifest.authority,'none');assert.equal(manifest.currencyCapBaseUnits,'0');
  assert.equal(manifest.externalExecution,'unprovisioned');assert.equal(manifest.productionQualified,false);
  assert.ok(git(manifest.jobs?.commit)&&git(manifest.jobs?.tree)&&git(manifest.alpha?.commit)&&git(manifest.alpha?.tree)
    && hash(manifest.alpha?.sourceHash),'Installed source identities are required');
  assert.equal(manifest.alpha.status,'REVIEWED_FINAL_SOURCE');
  const records=manifest.files;assert.ok(records&&typeof records==='object'&&!Array.isArray(records));
  const names=Object.keys(records);assert.ok(names.length>0&&names.length<=MAX_FILES);
  const expectedNames=[...names,INSTALLED_MANIFEST,'INSTALLATION_CUSTODY.json'];
  const actual=installedNames(root,expectedNames);assert.deepEqual([...actual].sort(),expectedNames.sort(),
    'Installed inventory has missing or unexpected inputs');
  const captured=new Map();let total=0;
  for(const name of names) {
    const record=records[name];assert.ok(nameOK(name)&&record&&hash(record.sha256)&&Number.isSafeInteger(record.bytes)
      && record.bytes>=0&&record.bytes<=MAX_FILE&&['100644','100755'].includes(record.mode));
    const raw=boundedInstalledBytes(path.join(root,name));total+=raw.length;assert.ok(total<=MAX_TOTAL);
    assert.equal(raw.length,record.bytes);assert.equal(sha(raw),record.sha256,'Installed source digest changed: '+name);
    assert.equal(Boolean(fs.statSync(path.join(root,name)).mode&0o111),record.mode==='100755','Installed source mode changed: '+name);
    captured.set(name,Buffer.from(raw));
  }
  const own='integrations/alpha-agent/discovery-installed-runtime.mjs';
  assert.equal(sha(boundedInstalledBytes(fileURLToPath(import.meta.url))),records[own]?.sha256,'Runtime bytes differ from installed source');
  assert.equal(sha(captured.get(ADAPTER)),manifest.jobs.adapterSha256);assert.equal(sha(captured.get(CONTRACT)),manifest.jobs.contractSha256);
  const catalog=parseBounded(captured.get('alpha/'+CATALOG).toString('utf8'));
  assert.equal(catalog.schema,'successor-capability-source/v1');assert.equal(catalog.sourceHash,manifest.alpha.sourceHash);
  assert.equal(sha(canonical(catalog.sources)),catalog.sourceHash);assert.equal(Object.keys(catalog.sources).length,41,'Expected complete reviewed Alpha41 source catalog');
  for(const [name,digest] of Object.entries(catalog.sources)) {
    assert.ok(hash(digest)&&captured.has('alpha/'+name));assert.equal(sha(captured.get('alpha/'+name)),digest,'Alpha source catalog differs');
  }
  assert.ok(captured.has('alpha/'+INSPECTOR));assert.equal(sha(captured.get('alpha/'+INSPECTOR)),manifest.alpha.inspectorSha256);
  assert.equal(manifest.jobs.contractSha256,sha(captured.get('alpha/examples/successor-capability/discovery-lab-contract.mjs')),
    'Installed receiver and Alpha contracts differ');
  const deploymentPath='alpha/docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.json';
  assert.ok(captured.has(deploymentPath),'Authoritative deployment compatibility input is missing');
  const deploymentRaw=captured.get(deploymentPath),inventory=parseBounded(deploymentRaw.toString('utf8'));
  assert.equal(inventory.schema,'successor-deployment-compatibility/v1');assert.equal(inventory.chainId,1);
  assert.equal(inventory.routes?.['jobs-agialpha']?.currency,'AGIALPHA18');assert.equal(inventory.tokens?.AGIALPHA18?.decimals,18);
  assert.equal(inventory.authority,'none');
  const deploymentCompatibility={inventorySha256:sha(deploymentRaw),chainId:inventory.chainId,recordDate:inventory.recordDate,
    route:inventory.routes['jobs-agialpha'],token:inventory.tokens.AGIALPHA18,
    recordedOperationallyReady:inventory.operationallyReady,onChainObservation:'NOT_RUN',
    authority:'none',executionApproved:false,scope:'Source-bound repository records; no fresh chain-state confirmation.'};
  const custody=parseBounded(boundedInstalledBytes(path.join(root,'INSTALLATION_CUSTODY.json')).toString('utf8'));
  return {root,manifest,captured,total,deploymentCompatibility,capsule:installationCapsule(options,custody)};
}
export async function openInstalled(input) {
  const options=runtimeOptions(input);
  const started=performance.now();const installed=captureInstalled(options),{manifest,captured}=installed;
  const modules=new Map([...captured].filter(([name])=>name.startsWith('alpha/')&&name.endsWith('.mjs')));
  modules.set('jobs/'+ADAPTER,captured.get(ADAPTER));modules.set('jobs/'+CONTRACT,captured.get(CONTRACT));
  const builtins={['jobs/'+ADAPTER]:['node:crypto','node:fs']};
  const helper=captured.get('integrations/alpha-agent/discovery-installed-module-graph-runtime.mjs').toString('utf8');
  const records=parseModuleSources([...modules].map(([name,raw])=>({name,source:raw.toString('utf8')})),helper);
  checkDependencyRecords(records,new Set(modules.keys()),builtins);
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'jobs-installed-captured-'));
  let boundary;
  try {
    // The actual receiver reads its own source for receipt provenance. The ESM loader
    // still serves only captured buffers, so filesystem changes cannot select code.
    for(const name of ['jobs/'+ADAPTER,'jobs/'+CONTRACT]) {
      const target=path.join(directory,name);fs.mkdirSync(path.dirname(target),{recursive:true,mode:0o700});
      fs.writeFileSync(target,modules.get(name),{flag:'wx',mode:0o600});
    }
    boundary=createModuleBoundary(directory,modules,[...modules.keys()],builtins);
    const receiver=await boundary.importModule('jobs/'+ADAPTER);
    const source={repository:'MontrealAI/AGIJobsv0',commit:manifest.jobs.commit,tree:manifest.jobs.tree,
      adapterSha256:manifest.jobs.adapterSha256,contractSha256:manifest.jobs.contractSha256};
    return {manifest,source,capsule:installed.capsule,deploymentCompatibility:installed.deploymentCompatibility,receiver:receiver.receiveDiscoveryLabWorkRequest,
      sources:{modelDigest:manifest.alpha.files['examples/successor-capability/discovery-lab.mjs'],
        evaluatorDigest:manifest.alpha.files['examples/successor-capability/discovery-lab-checker.mjs'],sourceDigest:manifest.alpha.sourceHash},
      coldSourceCapture:{files:captured.size,bytes:installed.total,elapsedMs:Math.ceil(performance.now()-started),
        scope:'Source bytes and capture/parser/loader wall time; no calibrated VM heap or provider cost.'},
      loadAlpha:name=>{assert.ok(/^[a-z0-9-]+$/.test(name));return boundary.importModule('alpha/examples/successor-capability/'+name+'.mjs');},
      close:()=>{boundary.close();fs.rmSync(directory,{recursive:true,force:true});}};
  } catch(error) {boundary?.close();fs.rmSync(directory,{recursive:true,force:true});throw error;}
}
