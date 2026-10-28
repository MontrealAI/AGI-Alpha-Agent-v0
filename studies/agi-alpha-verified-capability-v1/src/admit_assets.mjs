// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,readdirSync,statSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createSelector} from './selection.mjs';
import {createFixtureResolver} from './authority.mjs';
import {sourceManifestHash} from '../market/adapter.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const read=relative=>JSON.parse(readFileSync(path.join(ROOT,relative),'utf8'));
const save=(relative,value)=>{mkdirSync(path.dirname(path.join(ROOT,relative)),{recursive:true});writeFileSync(path.join(ROOT,relative),JSON.stringify(value,null,2)+'\n',{flag:'wx'});};
const tree=directory=>readdirSync(path.join(ROOT,directory)).sort().flatMap(name=>{const relative=directory+'/'+name;return statSync(path.join(ROOT,relative)).isDirectory()?(name==='__pycache__'?[]:tree(relative)):[relative];});
const catalog=read('evidence/catalog/catalog.json'),resolver=createFixtureResolver(read('fixtures/authority.json'));
const common=[...tree('src'),...tree('native'),...tree('production'),'fixtures/authority.json','protocol/acceptance-contract.json','evidence/catalog/catalog.json','evidence/catalog/admission-reverification.json'];
const assets={},admissions=[];
for(const [arm,strategy] of [['B','registry'],['C','graph']]){
  const selected=createSelector(catalog,resolver,{strategy}).select(catalog.context);
  if(!selected.ok||selected.selected.at(-1)!==catalog.targetSkill)throw Error('ASSET_SELECTION_REFUSED:'+arm+':'+selected.reasons.join(','));
  const id=`verified-${strategy}-composition-v1`;
  const descriptor={schema:'agi-alpha-actual-composition-asset/v1',id,selectionStrategy:strategy,entrypoint:'src/production.py',route:'native',targetSkill:catalog.targetSkill,
    graphRoot:catalog.root.graphRoot,skillVersionIdentities:selected.selected,mode:'FIXTURE_ONLY',nativeAuthority:[],originalNativeAdmission:'HOLD',
    construction:'Actual executable selection plus existing source-bound pipeline; existing component construction is inherited and preserved.',
    admissionBasis:'Independent baseline replay, exact typed skill dossiers, scoped agent fixture attestations, tested selector and independently validated combined workflow.',
    economicAdmission:'UNASSESSED',currentUse:'Only the exact bounded metadata offering, then independent verification on every new job.'};
  save(`protocol/asset-${arm}.json`,descriptor);
  const files=[...common,`protocol/asset-${arm}.json`].sort().map(relative=>({path:relative,sha256:sha(readFileSync(path.join(ROOT,relative)))}));
  const manifest=sourceManifestHash(files);
  admissions.push({asset_id:id,decision:'ADMIT',mode:'FIXTURE_ONLY',source_manifest_sha256:manifest,technical_selected_skills:selected.selected,
    selection: selected,graph_root:catalog.root.graphRoot,native_authority:[],native_admission:'HOLD',live_identity_enforcement:'NOT_RUN',economic_admission:'UNASSESSED'});
  assets[arm]={id,files,admission_evidence_path:'evidence/asset-admission.json'};
}
save('evidence/asset-admission.json',{schema:'agi-alpha-asset-admission-projection/v1',admissions,
  scope:'Actual local technical selection/admission projection; it supplements unchanged native HOLD and cannot authorize live operation, spending or settlement.'});
for(const asset of Object.values(assets))asset.admission_evidence_sha256=sha(readFileSync(path.join(ROOT,asset.admission_evidence_path)));
save('market/asset-bindings.json',{schema:'agi-alpha-verified-capability-asset-bindings/v1',assets});
console.log(JSON.stringify({assets:Object.fromEntries(Object.entries(assets).map(([k,a])=>[k,{id:a.id,source_files:a.files.length}]))}));
