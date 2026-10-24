// SPDX-License-Identifier: Apache-2.0
// Exact-byte gate controls. Test-only artifacts are never scientific outcomes.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const {sha256,canonical,validatePackage,rerunChecker,runLocalLifecycle} = require('./evm-run.cjs');
const root=path.resolve(__dirname,'../..');
const encode=value=>Buffer.from(canonical(value)+'\n');

async function main(){
  const outputRoot=path.resolve(process.argv[2]||path.join(root,'evidence/contracts/tae-prototype'));
  assert(!fs.existsSync(outputRoot),'Fresh output directory required');fs.mkdirSync(outputRoot,{recursive:true});
  const checkerBytes=fs.readFileSync(path.join(root,'study/evaluation/checker.mjs'));
  const criteriaBytes=fs.readFileSync(path.join(root,'study/evaluation/criteria.json'));
  const checkerSha256=sha256(checkerBytes),criteriaSha256=sha256(criteriaBytes);
  for(const [name,bytes] of [['checker.mjs',checkerBytes],['criteria.json',criteriaBytes]])fs.writeFileSync(path.join(outputRoot,name),bytes,{flag:'wx'});
  const {checkArtifact}=await import(pathToFileURL(path.join(outputRoot,'checker.mjs')).href);
  const inputBytes=encode({schema:'tae/mission-v1',missionId:'evm-prototype-only',kind:'bom-demand',graph:{nodes:['assembly','component','spare'],edges:[{from:'assembly',to:'component',weight:3}]},seeds:[{node:'assembly',amount:2}],targets:['component','spare']});
  const artifact={schema:'tae.artifact.v1',missionId:'evm-prototype-only',capabilityHash:sha256('test-only placeholder; no candidate identity claim'),inputHash:sha256(inputBytes),output:{groups:[{group:'component',total:6},{group:'spare',total:0}],total:6},currentProof:null,authority:[]};
  const artifactBytes=encode(artifact);
  const proof=checkArtifact(artifactBytes,inputBytes,criteriaBytes),proofBytes=Buffer.from(JSON.stringify(proof,null,2)+'\n');
  const base={artifactBytes,proofBytes,inputBytes,criteriaBytes,checkerBytes,checkerSha256,criteriaSha256};
  for(const [name,bytes] of [['input.json',inputBytes],['artifact.json',artifactBytes],['proof.json',proofBytes]])fs.writeFileSync(path.join(outputRoot,name),bytes,{flag:'wx'});
  const results=[];
  const test=(name,fn)=>{try{fn();results.push({name,pass:true});}catch(error){results.push({name,pass:false,error:error.message});}};
  const reject=(name,change,pattern)=>test(name,()=>assert.throws(()=>validatePackage({...base,...change}),pattern));
  const proofPatch=change=>Buffer.from(JSON.stringify({...proof,...change})+'\n');
  const artifactPatch=change=>encode({...artifact,...change});
  test('valid-byte-package',()=>assert.equal(validatePackage(base).artifact.missionId,artifact.missionId));
  reject('noncanonical-artifact',{artifactBytes:Buffer.from(JSON.stringify(artifact,null,2)+'\n')},/canonical JSON/);
  reject('artifact-byte-swap',{artifactBytes:Buffer.concat([artifactBytes,Buffer.from('\n')])},/canonical JSON/);
  reject('artifact-hash-substitution',{proofBytes:proofPatch({artifactSha256:'0'.repeat(64)})},/Artifact byte hash/);
  reject('input-byte-substitution',{inputBytes:Buffer.concat([inputBytes,Buffer.from(' ')])},/Input byte hash/);
  reject('mission-substitution',{proofBytes:proofPatch({missionId:'other'})},/Mission identity/);
  reject('capability-substitution',{proofBytes:proofPatch({capabilityHash:'0'.repeat(64)})},/Capability mismatch/);
  reject('criteria-byte-substitution',{criteriaBytes:Buffer.concat([criteriaBytes,Buffer.from(' ')])},/Frozen criteria/);
  reject('checker-byte-substitution',{checkerBytes:Buffer.concat([checkerBytes,Buffer.from('\n')])},/Frozen checker/);
  reject('missing-frozen-checker-anchor',{checkerSha256:undefined},/Independently supplied/);
  reject('rejected-receipt',{proofBytes:proofPatch({accepted:false})},/Rejected or missing/);
  reject('missing-verdict',{proofBytes:proofPatch({accepted:null})},/Rejected or missing/);
  reject('retained-failure',{proofBytes:proofPatch({failures:['SEMANTIC_OUTPUT_MISMATCH']})},/Evaluation failures/);
  reject('inherited-artifact-proof',{artifactBytes:artifactPatch({currentProof:{accepted:true}})},/self-certify/);
  reject('inherited-artifact-authority',{artifactBytes:artifactPatch({authority:['sign']})},/grant authority/);
  reject('receipt-authority',{proofBytes:proofPatch({authority:['sign']})},/grant authority/);
  reject('output-total-invariant',{artifactBytes:artifactPatch({output:{groups:[{group:'component',total:6}],total:7}})},/total invariant/);
  reject('unsafe-output-integer',{artifactBytes:artifactPatch({output:{groups:[{group:'component',total:Number.MAX_SAFE_INTEGER+1}],total:Number.MAX_SAFE_INTEGER+1}})},/Exact integer/);
  const pack=validatePackage(base);
  try{await assert.rejects(runLocalLifecycle(pack,{alphaRoot:path.join(root,'repos/alpha'),checkerRun:{identicalReceipt:true,checkerSha256}}),/Fresh checker execution required/);results.push({name:'forged-checker-run-object',pass:true});}catch(error){results.push({name:'forged-checker-run-object',pass:false,error:error.message});}
  test('fresh-separated-checker-matches-complete-receipt',()=>{const result=rerunChecker(pack,process.execPath);assert(result.identicalReceipt);assert.equal(result.nodeVersion,process.version);});
  const wrongArtifactBytes=artifactPatch({output:{groups:[{group:'component',total:7},{group:'spare',total:0}],total:7}});
  const forgedProof={...checkArtifact(wrongArtifactBytes,inputBytes,criteriaBytes),accepted:true,failures:[]};
  test('self-consistent-hashes-and-accepted-flag-do-not-prove-semantics',()=>{const forgedPack=validatePackage({...base,artifactBytes:wrongArtifactBytes,proofBytes:encode(forgedProof)});assert.throws(()=>rerunChecker(forgedPack,process.execPath));});
  const alteredCounts={...proof,counts:{...proof.counts,referenceSteps:proof.counts.referenceSteps+1}};
  test('entire-receipt-must-match-fresh-checker',()=>{const altered=validatePackage({...base,proofBytes:encode(alteredCounts)});assert.throws(()=>rerunChecker(altered,process.execPath),/Fresh frozen-checker verdict differs/);});
  const report={schema:'tae.byte-gate-tests.v1',mode:'UNSCORED_FIXTURE_ONLY',runtime:process.version,checkerSha256,criteriaSha256,artifactSha256:sha256(artifactBytes),proofSha256:sha256(proofBytes),testCount:results.length,passCount:results.filter(x=>x.pass).length,results,limitations:['Same-controller second implementation, not institutional independence.','Fixture is not an executed enterprise capability or scored scientific result.','No EVM is initialized by these package refusal tests; the separate local lifecycle command performs transactions.']};
  fs.writeFileSync(path.join(outputRoot,'package-test-results.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({outputRoot,testCount:report.testCount,passCount:report.passCount,node:process.execPath,checkerSha256,criteriaSha256}));
  if(report.testCount!==report.passCount)process.exitCode=1;
}
main().catch(error=>{console.error(error);process.exitCode=1;});
