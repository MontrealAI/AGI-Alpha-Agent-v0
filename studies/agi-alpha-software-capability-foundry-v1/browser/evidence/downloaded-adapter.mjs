// SPDX-License-Identifier: Apache-2.0
import { canonical } from './vendor/alpha/docs/assets/successor/engine.mjs';

const encoder = new TextEncoder();
export async function sha256(value) {
  const bytes = typeof value === 'string' ? encoder.encode(value) : value;
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(n => n.toString(16).padStart(2, '0')).join('');
}
export class OutsideScope extends Error {}
function requireValue(condition, message) { if (!condition) throw new OutsideScope(message); }
export function checkFiles(files) {
  requireValue(Array.isArray(files) && files.length > 0 && files.length <= 128, 'Use between 1 and 128 files.');
  let total = 0;
  const seen = new Set();
  for (const file of files) {
    requireValue(file && typeof file === 'object' && !Array.isArray(file), 'Every file must be an object.');
    requireValue(Object.keys(file).every(key => ['path','mode','text','expected'].includes(key)), 'Unexpected file field.');
    requireValue(typeof file.path === 'string' && file.path.length <= 512 && file.path.length > 0, 'Invalid file path.');
    requireValue(!file.path.startsWith('/') && !/[\\\r\n\u0000]/.test(file.path) && file.path.split('/').every(p => p && p !== '.' && p !== '..'), 'Path is outside the relative-file scope.');
    requireValue(!seen.has(file.path), 'Duplicate path is outside this instrument’s scope.');
    requireValue(['100644','100755'].includes(file.mode), 'Only regular files are supported; links and submodules are refused.');
    requireValue(typeof file.text === 'string', 'This browser instrument accepts UTF-8 text only.');
    if (file.expected !== undefined) requireValue(typeof file.expected === 'string' && /^[a-f0-9]{64}$/.test(file.expected), 'Malformed expected SHA-256.');
    total += encoder.encode(file.text).byteLength;
    requireValue(total <= 1_000_000, 'The local example is limited to 1 MB of text.');
    seen.add(file.path);
  }
}
export async function snapshot(files, checkpoint = async () => {}) {
  checkFiles(files);
  const rows = [];
  for (const file of files) {
    await checkpoint('reading-public-bytes');
    const hash = await sha256(file.text);
    if (file.expected !== undefined && hash !== file.expected) throw new OutsideScope('A supplied source hash does not match its bytes.');
    rows.push({ path:file.path, mode:file.mode, bytes:encoder.encode(file.text).byteLength, sha256:hash });
  }
  rows.sort((a,b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  return { schema:'foundry-text-snapshot/v1', files:rows, digest:await sha256(canonical(rows)) };
}
export function drift(before, after) {
  const old = new Map(before.files.map(row => [row.path,row]));
  const next = new Map(after.files.map(row => [row.path,row]));
  const missing = [], unexpected = [], changed = [], modeChanged = [];
  for (const [name,row] of old) {
    if (!next.has(name)) missing.push(name);
    else {
      const other = next.get(name);
      if (row.sha256 !== other.sha256) changed.push(name);
      if (row.mode !== other.mode) modeChanged.push(name);
    }
  }
  for (const name of next.keys()) if (!old.has(name)) unexpected.push(name);
  return { schema:'foundry-drift-report/v1', before:before.digest, after:after.digest, missing, unexpected, changed, modeChanged, exact:![missing,unexpected,changed,modeChanged].some(list => list.length) };
}
const jsonArtifact = (name,value) => ({name,type:'application/json',content:JSON.stringify(value,null,2)+'\n'});
export function createAdapter(codeHash) {
  if (!/^[a-f0-9]{64}$/.test(codeHash)) throw Error('An exact adapter source identity is required.');
  const instrument = {schema:'foundry-browser-instrument/v1',version:1,codeSha256:codeHash,interface:'snapshot(files, checkpoint)',scope:'At most 128 regular UTF-8 text files, 1 MB total; public or licensed nonpersonal inputs.',construction:'Fixed code authored before this demonstration; not autonomous discovery.'};
  const parentIdentity = async () => sha256(canonical(instrument));
  return {
    manifest:{id:'software-capability-foundry',version:1,en:'Inspect software snapshots',fr:'Vérifier des instantanés logiciels',scope:'Local bounded text-snapshot verification and drift diagnostics. No Git process, native executor, settlement or autonomous research is run by this browser example.',artifact:'snapshot.json'},
    validate(input) {
      if (!input || !['A','B','C','D','custom'].includes(input.stage) || !Array.isArray(input.files)) throw Error('Unsupported Foundry input.');
      if (canonical(input).length > 1_900_000) throw Error('Input exceeds the workbench bound.');
    },
    async execute(input,checkpoint) {
      const instrumentId = await parentIdentity();
      const parentTrace = [];
      const read = async files => {
        if (input.stage !== 'A') {
          requireValue(input.parent === instrumentId, 'The exact previously retained instrument is required.');
          parentTrace.push({instrument:instrumentId,operation:'snapshot',files:files.length,invoked:true});
        }
        return snapshot(files,checkpoint);
      };
      try {
        const first = await read(input.files);
        let result = first;
        if (['C','custom'].includes(input.stage)) {
          requireValue(Array.isArray(input.candidate), 'Candidate files are required.');
          result = drift(first,await read(input.candidate));
        }
        const decision = result.schema === 'foundry-drift-report/v1' ? (result.exact ? 'EXACT_MATCH' : 'DRIFT_LOCALIZED') : 'VERIFIED_SNAPSHOT';
        return {
          decision,
          summary:{stage:input.stage,files:first.files.length,bytes:first.files.reduce((n,row)=>n+row.bytes,0),differences:result.exact === undefined ? 0 : result.missing.length+result.unexpected.length+result.changed.length+result.modeChanged.length,parentInvocations:parentTrace.length},
          evidence:{execution:'LIVE_LOCAL_BROWSER_COMPUTATION',codeSha256:codeHash,instrumentId,parentTrace,output:result,retainedInstrument:instrument,qualification:'Public engineering example, not protected confirmation or production admission.',construction:instrument.construction},
          artifacts:[jsonArtifact('snapshot.json',first),jsonArtifact('local-instrument.json',{...instrument,id:instrumentId}),jsonArtifact('result.json',result),jsonArtifact('parent-trace.json',parentTrace)],
          limits:['This browser example does not run Git or the Python confirmation experiment.','The local instrument and constructor were authored before execution; this run does not demonstrate autonomous discovery.','Complete model, human, integration and maintenance costs are unknown.','Existing workbench proof and authority boundaries remain unchanged.']
        };
      } catch (error) {
        if (!(error instanceof OutsideScope)) throw error;
        const refusal = {stage:input.stage,reason:error.message,behavior:'REFUSE_REUSE',writes:0,externalRequests:0};
        return {decision:'REFUSED_OUT_OF_SCOPE',summary:{stage:input.stage,files:0,bytes:0,differences:0,parentInvocations:parentTrace.length},evidence:{execution:'LIVE_LOCAL_BROWSER_COMPUTATION',codeSha256:codeHash,instrumentId,parentTrace,output:refusal,retainedInstrument:null,qualification:'A bounded refusal, not general safety proof.'},artifacts:[jsonArtifact('refusal.json',refusal)],limits:['No external source was read or executed.','Use a separately reviewed supported reader for other file types.']};
      }
    }
  };
}
