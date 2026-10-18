// SPDX-License-Identifier: Apache-2.0
// Bounded CI summaries only. Raw logs and synthetic session journals stay private.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {reviewedRevision}=require('../scripts/authority-revision');
const digest=x=>crypto.createHash('sha256').update(x).digest('hex');
function campaign(record){
 assert.equal(record.status,'awaiting-governor-bindings');assert.equal(record.creationHashes.length,5);assert.equal(new Set(record.creationHashes).size,5);assert.equal(record.creationEvidence.length,5);
 for(const [index,proof] of record.creationEvidence.entries()){assert.equal(proof.index,index);assert.equal(proof.transactionHash,record.creationHashes[index]);assert.match(proof.transactionHash,/^0x[0-9a-f]{64}$/);}
 assert.deepEqual(record.governanceHashes,[]);assert.equal(record.finalAuthorityVerified,false);assert.equal(record.activationAllowed,false);assert.equal(record.actorLocksRetained,true);assert.equal(record.relayCount,5);assert.equal(record.prompts,2);assert.equal(record.closes,2);
 return {creator:record.creator,governor:record.governor,addresses:record.addresses,creationHashes:record.creationHashes,creationEvidence:record.creationEvidence,relayCount:5,prompts:2,closes:2,actorLocksRetained:true,finalAuthorityVerified:false,activationAllowed:false};
}
function main(){
 const directory=process.env.ALPHA_CONVENTIONAL_STATE_DIRECTORY;assert(directory&&path.isAbsolute(directory));const root=path.resolve(__dirname,'../../..');assert(!directory.startsWith(root+path.sep));
 const revision=reviewedRevision();assert.equal(revision.commit,process.env.ALPHA_EXPECTED_HEAD_SHA);
 if(process.argv[2]==='init'){fs.mkdirSync(directory,{mode:0o700});for(const n of ['public','logs'])fs.mkdirSync(path.join(directory,n),{mode:0o700});fs.writeFileSync(path.join(directory,'source.json'),JSON.stringify(revision),{flag:'wx'});return;}
 assert.equal(process.argv[2],'finish');assert.deepEqual(revision,JSON.parse(fs.readFileSync(path.join(directory,'source.json'))));
 const checks=Object.fromEntries(['compile','unit','local'].map(label=>{const log=path.join(directory,'logs',label+'.log'),exit=path.join(directory,'logs',label+'.exit');return [label,{exitCode:fs.existsSync(exit)?Number(fs.readFileSync(exit,'utf8').trim()):null,logSha256:fs.existsSync(log)?digest(fs.readFileSync(log)):null}];}));
 const passed=Object.values(checks).every(x=>x.exitCode===0);const campaigns={};if(passed)for(const mode of ['empty','marker'])campaigns[mode]=campaign(JSON.parse(fs.readFileSync(path.join(directory,'campaign-'+mode,'public-result.json'))));
 const report={schema:'agialpha.conventional-ci.v1',source:revision,checks,passed,campaigns,scope:'Exact-head functional execution using fixed synthetic keys, mock dependencies and latest-as-finalized; no real-account, Ledger, consensus or global-authority qualification',finalAuthorityVerified:false,activationAllowed:false};
 fs.writeFileSync(path.join(directory,'public','result.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});assert(passed,'Conventional CI checks failed or did not run');
}
module.exports={campaign};if(require.main===module)try{main();}catch{console.error('Conventional CI evidence incomplete; inspect private runner logs.');process.exitCode=1;}
