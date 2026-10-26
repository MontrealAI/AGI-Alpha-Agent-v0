// SPDX-License-Identifier: Apache-2.0
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {loadFoundations,admitCatalogue} from './admission/bridge.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const foundations=await loadFoundations(resolve(root,'heritage/graph-foundations'));
const started=performance.now(),cpu=process.cpuUsage();
async function descriptors(paths) {
  const rows=[];
  for(const path of paths){const bytes=await readFile(resolve(root,path));rows.push({path,bytes:bytes.length,
    sha256:createHash('sha256').update(bytes).digest('hex')});}
  return rows;
}
const commonInputs=['inputs/discovery-docker-v25.0.0.json','inputs/discovery-docker-v26.0.0.json'];
const sources=['src/schema_inventory.mjs','src/adapter.mjs'];
const fullEvidence=['evidence/acceptance-full.json','outputs/preconfirmation-full/response-dossier.json',...commonInputs];
const incrementalEvidence=['evidence/acceptance-incremental.json','outputs/preconfirmation-incremental/response-dossier.json',...commonInputs];
const catalogue={schema:'agi-alpha.work-discovery-catalogue.v1',mode:'FIXTURE_ONLY',graphId:'response-assurance-study',
  policy:{version:1,eligibleAttesters:'direct *.agent.agi.eth fixture delegates only',jobsValidatorsUnchanged:true,
    requireIndependentTechnicalReplay:true,executionAuthority:[],fixtureTimeIsNotUtc:true},
  environment:{node:process.versions.node,language:'JavaScript',data:'public Swagger2 and scoped OpenAPI JSON'},
  rights:{class:'public-nonpersonal',codeLicense:'Apache-2.0',inputLicense:'Apache-2.0'},
  skills:[{id:'response-index',version:'1',creator:'fixture:discovery-constructor',
    scope:{operation:'GET',statuses:'2xx',media:'application/json',output:'structural response changes with explicit exclusions',
      notClaimed:['live API compatibility','correctness outside enumerated schema subset','operating authority']},
    implementationFiles:await descriptors(sources),evidenceFiles:await descriptors(fullEvidence),
    compositionEvidenceFiles:[],dependencies:[],expiresAt:700},
  {id:'incremental-response-index',version:'1',creator:'fixture:discovery-constructor',
    scope:{operation:'same scoped response index',reuse:'source-bound current-session index; dependency invalidation',
      performance:'must be remeasured per supported workload'},
    implementationFiles:await descriptors(['src/incremental_index.mjs',...sources]),evidenceFiles:await descriptors(incrementalEvidence),
    compositionEvidenceFiles:await descriptors(['evidence/independent-review/schema-independent-qualified-review.txt','evidence/independent-review/schema-independent-qualified-receipt.json','tests/schema-independent.test.mjs']),
    dependencies:['response-index@1'],expiresAt:700}],
  edges:[{from:'response-index@1',to:'incremental-response-index@1',kind:'requires'}]};
const validations=[];
async function verifyEvidence({skill,binding,files}) {
  const receipt=JSON.parse(files.get(skill.evidenceFiles[0].path));
  if(receipt.accepted!==true) throw Error('RECORDED_ACCEPTANCE_REQUIRED');
  const mode=skill.id==='response-index'?'full':'incremental';
  const output=execFileSync('python',[resolve(root,'tests/accept_dossier.py'),
    ...commonInputs.map(path=>resolve(root,path)),resolve(root,`outputs/preconfirmation-${mode}`)],
    {encoding:'utf8',timeout:60000,maxBuffer:2000000});
  const checked=JSON.parse(output);
  if(checked.accepted!==true||checked.changes!==receipt.changes||checked.oldNodes!==receipt.oldNodes||checked.newNodes!==receipt.newNodes)
    throw Error('INDEPENDENT_REPLAY_DISAGREEMENT');
  validations.push({skill:skill.id,technicalReplay:checked});
  return {accepted:true,compositionAccepted:mode==='incremental',validatorId:'independently-authored-python-bfs',
    scopeDigest:binding.scopeDigest,implementationDigest:binding.implementationDigest};
}
const admission=await admitCatalogue({catalogue,foundations,artifactRoot:root,verifyEvidence});
await writeFile(resolve(root,'protocol/catalogue-v2.json'),JSON.stringify(catalogue,null,2)+'\n',{flag:'wx'});
await writeFile(resolve(root,'evidence/admission-v2.json'),JSON.stringify(admission,null,2)+'\n',{flag:'wx'});
const used=process.cpuUsage(cpu);
await writeFile(resolve(root,'evidence/admission-build-v2.json'),JSON.stringify({completedAt:new Date().toISOString(),
  wallSeconds:(performance.now()-started)/1000,selfCpuSeconds:(used.user+used.system)/1e6,validations,
  graphRoot:admission.root.graphRoot,admissionDigest:admission.admissionDigest,
  scope:'Separate bounded research validation before local Workbench use; no native host dispatch or live ENS authentication'},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({graphRoot:admission.root.graphRoot,admissionDigest:admission.admissionDigest,validations:validations.length}));
