// Read-only inspection of archived packs. This adapter cannot execute a job.
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {inspectPack} from '../native/examples/successor-workbench/engine.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=async p=>JSON.parse(await readFile(path.join(ROOT,p),'utf8'));
const campaign=await read('results/confirmation-01/campaign.json');
const rows=[];
for(const row of campaign.rows.filter(row=>row.arm==='B')){
  const relative=path.dirname(row.verification_path);
  const pack=await read(relative+'/pack.json');
  const original=await read(relative+'/inspection.json');
  const adapter={manifest:{id:'full-lock-evidence',version:1,
    en:'Check the complete dependency lock',fr:'Vérifier le verrou complet des dépendances',
    scope:'Exact selected wheel metadata and project requirements; no application runtime qualification.',artifact:'lock-decision.json'},
    validate(input){if(!input||Object.keys(input).sort().join('|')!=='id|jobSha256'||input.id!==row.mission||input.jobSha256!==row.job_sha256)throw Error('REGISTERED_JOB_REQUIRED');},
    execute(){throw Error('AUDIT_MUST_NOT_EXECUTE_PRODUCTION');}};
  let result,error=null;
  try{result=await inspectPack(pack,adapter);}catch(caught){error=String(caught);}
  rows.push({family:row.family,pack_path:relative+'/pack.json',
    pack_sha256:sha(await readFile(path.join(ROOT,relative,'pack.json'))),
    passed:error===null&&JSON.stringify(result)===JSON.stringify(original),error,
    authentication:result?.authentication,activeProof:result?.activeProof,activeAuthority:result?.activeAuthority});
}
const output={schema:'agi-alpha-second-investment-archived-native-inspection/v1',reviewed_at:new Date().toISOString(),
  source_sha256:sha(await readFile(fileURLToPath(import.meta.url))),primary_production_reexecuted:false,
  scope:'Native semantic identity, pack/artifact integrity, release and compilation binding rechecked using unchanged native inspectPack; same native implementation, not independent authentication.',
  rows,passed:rows.length===6&&rows.every(row=>row.passed)};
await writeFile(path.join(ROOT,'review/native-pack-review.json'),JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({passed:output.passed,packs:rows.length,errors:rows.filter(row=>!row.passed)}));
