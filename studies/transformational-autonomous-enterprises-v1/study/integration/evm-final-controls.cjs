// SPDX-License-Identifier: Apache-2.0
// Mutations of the actual joined journey bytes. Never initializes an EVM.
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {sha256,canonical,validatePackage,rerunChecker,runLocalLifecycle}=require('./evm-run.cjs');
const root=path.resolve(__dirname,'../..'),read=p=>fs.readFileSync(path.join(root,p)),encode=v=>Buffer.from(canonical(v)+'\n');
const checkerSha256='7eebf95de7ff0b36ebf0029b3bf441e42a2fb325205723b46afc385beb2105c6';
const criteriaSha256='58dd0ba793d9277e47fdd4e0c336fc6d7b1a9502985fcea7fb117cf47b16aa33';
const manifestSha256='7c25e93b04ed72764824241db825e38b185672625746253bc61abb0318850352';
async function main(){
  const output=path.resolve(process.argv[2]||path.join(root,'evidence/contracts/writer4-negative-controls.json'));
  assert(!fs.existsSync(output),'Fresh output file required');
  const common={checkerBytes:read('study/evaluation/checker.mjs'),criteriaBytes:read('study/evaluation/criteria.json'),manifestBytes:read('study/evaluation/SCORING_FREEZE_V2.json'),checkerSha256,criteriaSha256,manifestSha256};
  const capture=which=>{const prefix='study/results/journey-inputs/'+which+'/';return {...common,artifactBytes:read(prefix+'artifact.json'),proofBytes:read(prefix+'proof.json'),inputBytes:read(prefix+'input.json'),candidateBytes:read(prefix+'candidate.json')};};
  const parent=capture('parent'),successor=capture('successor'),artifact=JSON.parse(parent.artifactBytes),proof=JSON.parse(parent.proofBytes),candidate=JSON.parse(parent.candidateBytes);
  const results=[];
  const test=async(name,body)=>{try{await body();results.push({name,pass:true});}catch(error){results.push({name,pass:false,error:error.message});}};
  const reject=(name,changes,pattern)=>test(name,()=>assert.throws(()=>validatePackage({...parent,...changes}),pattern));
  await test('actual-parent-package-and-fresh-checker',()=>assert(rerunChecker(validatePackage(parent),process.execPath).identicalReceipt));
  await test('actual-successor-package-and-fresh-checker',()=>assert(rerunChecker(validatePackage(successor),process.execPath).identicalReceipt));
  await reject('rejected-verdict',{proofBytes:encode({...proof,accepted:false})},/Rejected or missing/);
  await reject('mutation-of-receipt-artifact-hash',{proofBytes:encode({...proof,artifactSha256:'0'.repeat(64)})},/Artifact byte hash/);
  await reject('cross-mission-replayed-proof',{proofBytes:successor.proofBytes},/Mission identity/);
  await reject('stale-input-bytes',{inputBytes:Buffer.concat([parent.inputBytes,Buffer.from(' ')])},/Input byte hash/);
  await reject('mutated-frozen-source-manifest',{manifestBytes:Buffer.concat([common.manifestBytes,Buffer.from(' ')])},/Frozen source manifest/);
  await reject('wrong-source-anchor',{manifestSha256:'0'.repeat(64)},/Frozen source manifest/);
  await reject('candidate-cross-mission-swap',{candidateBytes:successor.candidateBytes},/Candidate mission/);
  await reject('candidate-source-catalog-substitution',{candidateBytes:encode({...candidate,sources:{...candidate.sources,rootSha256:'0'.repeat(64)}})},/Candidate source inventory/);
  await reject('candidate-capability-substitution',{candidateBytes:encode({...candidate,capability:{...candidate.capability,id:'0'.repeat(64)}})},/Candidate capability/);
  await reject('candidate-inherited-authority',{candidateBytes:encode({...candidate,authority:['sign']})},/deep-equal/);
  await reject('artifact-inherited-proof',{artifactBytes:encode({...artifact,currentProof:{accepted:true}})},/self-certify/);
  await reject('receipt-inherited-authority',{proofBytes:encode({...proof,authority:['settle']})},/grant authority/);
  await test('forged-checker-object-is-not-execution',()=>assert.rejects(runLocalLifecycle(validatePackage(parent),{alphaRoot:path.join(root,'repos/alpha'),checkerRun:{checkerSha256,identicalReceipt:true}}),/Fresh checker execution required/));
  const badArtifact=structuredClone(artifact);badArtifact.output.groups[0].total++;badArtifact.output.total++;
  const badBytes=encode(badArtifact),badCandidate=structuredClone(candidate);badCandidate.rows[0].amount=String(BigInt(badCandidate.rows[0].amount)+1n);
  const lyingProof={...proof,artifactSha256:sha256(badBytes),accepted:true,failures:[]};
  await test('self-consistent-mutated-output-and-lying-accepted-flag-refused',()=>{const pack=validatePackage({...parent,artifactBytes:badBytes,candidateBytes:encode(badCandidate),proofBytes:encode(lyingProof)});assert.throws(()=>rerunChecker(pack,process.execPath));});
  await test('mutated-evaluation-counts-refused-by-full-receipt-comparison',()=>{const pack=validatePackage({...parent,proofBytes:encode({...proof,counts:{...proof.counts,referenceSteps:proof.counts.referenceSteps+1}})});assert.throws(()=>rerunChecker(pack,process.execPath),/Fresh frozen-checker verdict differs/);});
  const report={schema:'tae.actual-byte-gate-controls.v1',scope:'Actual joined parent/successor bytes with explicit negative mutations; no EVM initialized or transactions performed by this script.',runtime:process.version,checkerSha256,criteriaSha256,manifestSha256,runnerSha256:sha256(read('study/integration/evm-run.cjs')),controlSourceSha256:sha256(fs.readFileSync(__filename)),actualParentArtifactSha256:sha256(parent.artifactBytes),actualSuccessorArtifactSha256:sha256(successor.artifactBytes),testCount:results.length,passCount:results.filter(r=>r.pass).length,results};
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({output,testCount:report.testCount,passCount:report.passCount,runnerSha256:report.runnerSha256}));if(report.passCount!==report.testCount)process.exitCode=1;
}
main().catch(error=>{console.error(error);process.exitCode=1;});
