// SPDX-License-Identifier: MIT
// Bounded source capture and installed saved-byte loading. No operation selects executable code.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {canonical,parseBounded} from './discovery-lab-contract.mjs';
import {parseModuleSources,checkDependencyRecords,createModuleBoundary} from './discovery-release-module-closure.mjs';
const CATALOG = 'docs/successor/capabilities/sources.json';
const INSPECTOR = 'examples/successor-capability/discovery-lab-inspector.mjs';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const exact = (value, names) => value && typeof value === 'object' && !Array.isArray(value)
  && Object.keys(value).length === names.length && names.every(name => Object.hasOwn(value, name));
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);

export function boundedSource(file) {
  assert.equal(fs.realpathSync(file), file, 'Source path or ancestor is a symlink');
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const before = fs.fstatSync(fd);
    assert.ok(before.isFile() && before.size <= 2_000_000, 'Source must be a bounded regular file');
    const bytes = Buffer.alloc(before.size + 1); let used = 0;
    while (used < bytes.length) {const n = fs.readSync(fd, bytes, used, bytes.length-used, null); if (!n) break; used += n;}
    const after = fs.fstatSync(fd);
    assert.equal(used, before.size, 'Source grew or was truncated during capture');
    for (const key of ['dev','ino','mode','size','mtimeMs','ctimeMs']) assert.equal(after[key], before[key], 'Source changed during capture');
    return bytes.subarray(0,used);
  } finally {fs.closeSync(fd);}
}

export const decodeUtf8=raw=>new TextDecoder('utf-8',{fatal:true}).decode(raw);

/** Prove worktree metadata inactive before the first Git process sees configuration. */
export function guardMainGitConfig(root) {
  const metadata=path.join(root,'.git'),message='Installed Alpha executable, included, transport and redirected configuration is prohibited';
  assert.ok(fs.existsSync(metadata)&&fs.lstatSync(metadata).isDirectory()&&fs.realpathSync(metadata)===metadata,
    'Installed Alpha root is not the actual Git worktree root');
  try {fs.lstatSync(path.join(metadata,'commondir'));assert.fail('Redirected Git metadata is prohibited');}
  catch(error) {if(error.code!=='ENOENT')throw error;}
  const raw=boundedSource(path.join(metadata,'config'));assert.ok(raw.length<=128_000,message);
  const config=decodeUtf8(raw);assert.ok(!config.includes('\0')&&!/\\\r?\n/.test(config),message);
  let section='',gcAutoSeen=false;
  for(const line of config.split(/\r?\n/)) {
    const value=line.trim();if(!value||/^[#;]/.test(value))continue;
    if(value.startsWith('[')) {
      const found=/^\[([A-Za-z0-9.-]+)(?:\s+"[^"]*")?\]\s*(?:[#;].*)?$/.exec(value);
      assert.ok(found,message);section=found[1].toLowerCase();
      assert.ok(['core','remote','branch','extensions','http','gc'].includes(section),message);
      assert.ok(!['core','extensions','gc'].includes(section)||!value.split(']')[0].includes('"'),message);continue;
    }
    const item=/^([A-Za-z][A-Za-z0-9-]*)\s*(?:=\s*(.*))?$/.exec(value);
    assert.ok(item&&section,message);
    const key=item[1].toLowerCase();
    if(section==='gc') {
      assert.ok(key==='auto'&&!gcAutoSeen&&typeof item[2]==='string'&&/^0\s*(?:[#;].*)?$/.test(item[2]),message);
      gcAutoSeen=true;
    }
    assert.ok(!(section==='core'&&['worktree','attributesfile','sshcommand','gitproxy','alternaterefscommand','fsmonitor','hookspath'].includes(key))
      &&!(section==='extensions'&&key==='partialclone')
      &&!(section==='remote'&&['uploadpack','receivepack','promisor','vcs','proxy','proxyauthmethod'].includes(key))
      &&!(section==='http'&&['proxy','proxyauthmethod'].includes(key)),message);
    if(section==='extensions'&&key==='worktreeconfig')
      assert.ok(typeof item[2]==='string'&&/^false\s*(?:[#;].*)?$/i.test(item[2]),message);
  }
  const ignored=path.join(metadata,'config.worktree');
  let present=true;try {fs.lstatSync(ignored);}catch(error) {if(error.code!=='ENOENT')throw error;present=false;}
  if(present)assert.ok(boundedSource(ignored).length<=128_000,message);
}

export function capturePinnedAlpha(root) {
  const started = performance.now();
  assert.ok(path.isAbsolute(root || ''), 'Explicit absolute Alpha checkout is required');
  assert.equal(fs.realpathSync(root),root,'Installed Alpha root must be a real path');
  guardMainGitConfig(root);
  const env = Object.fromEntries(Object.entries(process.env).filter(([key])=>!key.startsWith('GIT_')));
  Object.assign(env,{GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_SYSTEM:'/dev/null',GIT_CONFIG_GLOBAL:'/dev/null',
    GIT_NO_REPLACE_OBJECTS:'1',GIT_OPTIONAL_LOCKS:'0',GIT_TERMINAL_PROMPT:'0',GIT_NO_LAZY_FETCH:'1'});
  const git = (...args)=>execFileSync('git',['--no-replace-objects','--no-pager','-C',root,
    '-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','-c','core.attributesFile=/dev/null',
    '-c','protocol.allow=never',...args],{env,stdio:['ignore','pipe','pipe'],maxBuffer:8_000_000,timeout:30_000});
  assert.equal(fs.realpathSync(git('rev-parse','--show-toplevel').toString().trim()),root,
    'Installed Alpha root is not the actual Git worktree root');
  const localConfig = git('config','--local','--no-includes','--list').toString();
  for(const entry of localConfig.trim().split('\n')) if(entry) assert.ok(
    ['core','remote','branch','extensions','http','gc'].includes(entry.split('.')[0].toLowerCase()),
    'Installed Alpha Git configuration namespace is prohibited');
  assert.doesNotMatch(localConfig,
    /^(filter\.|include\.|includeif\.|protocol\.|core\.(worktree|attributesfile|sshcommand|gitproxy|alternaterefscommand)=|extensions\.(partialclone)(?:=|$)|remote\..*\.(uploadpack|receivepack|promisor|vcs)=)/im,
    'Installed Alpha executable, included, transport and redirected configuration is prohibited');
  const packs = path.join(root,'.git','objects','pack');
  if(fs.existsSync(packs)) assert.ok(!fs.readdirSync(packs).some(name=>name.endsWith('.promisor')),
    'Installed Alpha promisor packs are prohibited');
  const pin = parseBounded(boundedSource(fileURLToPath(new URL('../../config/discovery-release-alpha-source-v1.json',import.meta.url))).toString('utf8'));
  assert.ok(exact(pin,['schema','repository','commit','tree','sourceHash','catalogPath','catalogSha256','files','qualification']));
  assert.equal(pin.schema,'successor/discovery-lab-alpha-source/v1');
  assert.equal(pin.repository,'MontrealAI/AGI-Alpha-Agent-v0'); assert.equal(pin.catalogPath,CATALOG);
  assert.equal(pin.qualification,'PENDING_FINAL_SOURCE_NATIVE_COMPATIBILITY');
  assert.match(pin.commit,/^[a-f0-9]{40}$/);assert.match(pin.tree,/^[a-f0-9]{40}$/);
  assert.ok(hash(pin.sourceHash) && hash(pin.catalogSha256));
  assert.equal(git('rev-parse','HEAD').toString().trim(),pin.commit,'Installed Alpha is not the exact reviewed source');
  assert.equal(git('rev-parse',pin.commit+'^{tree}').toString().trim(),pin.tree);
  assert.equal(git('for-each-ref','--format=%(refname)','refs/replace').toString().trim(),'','Replaced source history is prohibited');
  const graft = git('rev-parse','--git-path','info/grafts').toString().trim();
  assert.equal(fs.existsSync(path.isAbsolute(graft)?graft:path.join(root,graft)),false,'Grafted source history is prohibited');
  const captured = new Map();let sourceBytes = 0;
  const capture = (name,expected) => {
    assert.ok(/^[A-Za-z0-9][A-Za-z0-9_./-]*$/.test(name) && name.split('/').every(part=>part && part!=='.' && part!=='..'));
    assert.ok(hash(expected));
    const committed = git('show',pin.commit+':'+name), current = boundedSource(path.join(root,name));
    assert.ok(committed.equals(current),'Installed source bytes differ: '+name);
    assert.equal(sha(committed),expected,'Source hash differs: '+name);
    sourceBytes += committed.length;assert.ok(sourceBytes<=8_000_000,'Captured source budget exceeded');
    captured.set(name,committed);return committed;
  };
  const catalog = parseBounded(capture(CATALOG,pin.catalogSha256).toString('utf8'));
  assert.ok(exact(catalog,['schema','sourceHash','sources']));assert.equal(catalog.schema,'successor-capability-source/v1');
  assert.equal(sha(canonical(catalog.sources)),pin.sourceHash);assert.equal(catalog.sourceHash,pin.sourceHash);
  assert.ok(exact(pin.files,[...Object.keys(catalog.sources),INSPECTOR]));
  for (const [name,digest] of Object.entries(pin.files)) {
    if(name!==INSPECTOR) assert.equal(digest,catalog.sources[name]);
    capture(name,digest);
  }
  return ownedModules(pin,captured,sourceBytes,started);
}

function ownedModules(pin,captured,sourceBytes,started) {
  const modules = new Map([...captured].filter(([name])=>name.endsWith('.mjs')));
  const helperSource = boundedSource(fileURLToPath(new URL('./discovery-release-module-closure.mjs',import.meta.url)));
  const records = parseModuleSources([...modules].map(([name,bytes])=>({name,source:bytes.toString('utf8')})),helperSource.toString('utf8'));
  checkDependencyRecords(records,new Set(modules.keys()));
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'discovery-native-source-'));let copied=0,boundary;
  const entries = ['discovery-lab','discovery-lab-history','workspace','discovery-lab-contract','discovery-lab-inspector',
    'discovery-lab-receipts','discovery-lab-docket','discovery-lab-evidence-history']
    .map(name=>'examples/successor-capability/'+name+'.mjs');
  try {
    for (const [name,bytes] of modules) {
      const target=path.join(directory,name);fs.mkdirSync(path.dirname(target),{recursive:true,mode:0o700});
      fs.writeFileSync(target,bytes,{flag:'wx',mode:0o600});copied+=bytes.length;
    }
    boundary = createModuleBoundary(directory,modules,entries);
  } catch(error) {boundary?.close();fs.rmSync(directory,{recursive:true,force:true});throw error;}
  return {pin,directory,sources:{modelDigest:pin.files['examples/successor-capability/discovery-lab.mjs'],
    evaluatorDigest:pin.files['examples/successor-capability/discovery-lab-checker.mjs'],sourceDigest:pin.sourceHash},
    load:name=>boundary.importModule('examples/successor-capability/'+name+'.mjs'),
    custody:{sourceFiles:captured.size,sourceBytes,copiedModuleBytes:copied,elapsedMs:Math.ceil(performance.now()-started),
      moduleBoundary:{schema:'manager/discovery-owned-module-boundary/v1',helperSha256:sha(helperSource),
        modules:records.length,staticEdges:records.reduce((sum,row)=>sum+row.requests.length,0),
        loader:'owned-byte-registerHooks',dynamicImports:'captured-map-only',closedTombstone:true,
        parserEvaluation:false,parserProcessResources:'unmeasured within fixed process and input bounds'},
      scope:'Current source capture and Git/SHA checks; encoded bytes, not VM heap. Charged once as cold start.'},
    dispose:()=>{boundary.close();fs.rmSync(directory,{recursive:true,force:true});}};
}

/** Capture a saved release closure. Installed replay never calls Git or an external checkout. */
export function captureSavedAlpha(directory) {
  const started=performance.now();
  assert.ok(path.isAbsolute(directory || ''),'An absolute saved capsule directory is required');
  assert.equal(fs.realpathSync(directory),directory,'Saved capsule root must be real');
  const pin=parseBounded(boundedSource(fileURLToPath(new URL('../../config/discovery-release-alpha-source-v1.json',import.meta.url))).toString());
  assert.ok(exact(pin,['schema','repository','commit','tree','sourceHash','catalogPath','catalogSha256','files','qualification']));
  assert.equal(pin.schema,'successor/discovery-lab-alpha-source/v1');assert.equal(pin.repository,'MontrealAI/AGI-Alpha-Agent-v0');
  assert.equal(pin.catalogPath,CATALOG);assert.match(pin.commit,/^[a-f0-9]{40}$/);assert.match(pin.tree,/^[a-f0-9]{40}$/);
  assert.ok(hash(pin.sourceHash)&&hash(pin.catalogSha256));
  const manifest=parseBounded(boundedSource(path.join(directory,'DISCOVERY_ALPHA_CAPSULE.json')).toString());
  assert.ok(exact(manifest,['schema','repository','commit','tree','sourceHash','catalogPath','catalogSha256','files','authority','externalExecution']));
  assert.equal(manifest.schema,'manager/discovery-alpha-capsule/v1');
  for(const key of ['repository','commit','tree','sourceHash','catalogPath','catalogSha256'])assert.equal(manifest[key],pin[key]);
  assert.equal(manifest.authority,'none');assert.equal(manifest.externalExecution,'unprovisioned');
  assert.equal(pin.qualification,'PENDING_FINAL_SOURCE_NATIVE_COMPATIBILITY');
  const expected={...pin.files,[CATALOG]:pin.catalogSha256,
    LICENSE:'c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4'};
  assert.ok(exact(manifest.files,Object.keys(expected)));
  const observed=[],ancestors=new Set();let entryCount=0;
  for(const name of Object.keys(expected)) {
    assert.ok(/^[A-Za-z0-9][A-Za-z0-9_./-]*$/.test(name)&&name.split('/').every(part=>part&&part!=='.'&&part!=='..'));
    const parts=name.split('/');for(let i=1;i<parts.length;i++)ancestors.add(parts.slice(0,i).join('/'));
  }
  function walk(folder,prefix='') {
    const handle=fs.opendirSync(folder);
    try {let entry;while((entry=handle.readSync())!==null) {
      assert.ok(++entryCount<=600,'Saved capsule directory inventory exceeds its bound');
      assert.ok(!entry.isSymbolicLink(),'Saved capsule must not contain symlinks');
      const name=prefix+entry.name;
      if(entry.isDirectory()) {assert.ok(ancestors.has(name),'Unlisted saved capsule directory');walk(path.join(folder,entry.name),name+'/');}
      else {assert.ok(entry.isFile());observed.push(name);assert.ok(observed.length<=260);}
    }} finally {handle.closeSync();}
  }
  walk(directory);assert.deepEqual(observed.sort(),[...Object.keys(expected),'DISCOVERY_ALPHA_CAPSULE.json'].sort());
  const captured=new Map();let sourceBytes=0;
  for(const [name,digest] of Object.entries(expected)) {
    assert.ok(/^[A-Za-z0-9][A-Za-z0-9_./-]*$/.test(name)&&name.split('/').every(part=>part&&part!=='.'&&part!=='..'));
    assert.ok(hash(digest));const raw=boundedSource(path.join(directory,name)),item=manifest.files[name];
    const mode=fs.statSync(path.join(directory,name)).mode&0o111?'100755':'100644';
    const blob=createHash('sha1').update(Buffer.concat([Buffer.from('blob '+raw.length+'\0'),raw])).digest('hex');
    assert.equal(canonical(item),canonical({mode,blob,sha256:digest,bytes:raw.length}));assert.equal(sha(raw),digest);
    sourceBytes+=raw.length;assert.ok(sourceBytes<=8_000_000);captured.set(name,raw);
  }
  const catalog=parseBounded(captured.get(CATALOG).toString());
  assert.ok(exact(catalog,['schema','sourceHash','sources']));assert.equal(catalog.schema,'successor-capability-source/v1');
  assert.equal(catalog.sourceHash,pin.sourceHash);assert.equal(sha(canonical(catalog.sources)),pin.sourceHash);
  assert.ok(exact(pin.files,[...Object.keys(catalog.sources),INSPECTOR]));
  for(const [name,digest] of Object.entries(catalog.sources))assert.equal(pin.files[name],digest);
  return ownedModules(pin,captured,sourceBytes,started);
}
