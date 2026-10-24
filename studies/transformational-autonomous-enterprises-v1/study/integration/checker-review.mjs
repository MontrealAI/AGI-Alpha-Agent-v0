// SPDX-License-Identifier: Apache-2.0
// Separate-agent, unscored source review. Does not inspect held-out task files.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const canonical = value => JSON.stringify(value, (_key, v) => v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.keys(v).sort().map(k => [k, v[k]])) : v);
const encode = value => Buffer.from(canonical(value) + '\n');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const outputRoot = path.resolve(process.argv[2] || path.join(root, 'evidence/contracts/checker-review-v1'));
if (fs.existsSync(outputRoot)) throw Error('Fresh review output directory required');
fs.mkdirSync(outputRoot, {recursive: true});
const checkerBytes = fs.readFileSync(path.join(root, 'study/evaluation/checker.mjs'));
const criteriaBytes = fs.readFileSync(path.join(root, 'study/evaluation/criteria.json'));
fs.writeFileSync(path.join(outputRoot, 'checker.mjs'), checkerBytes, {flag: 'wx'});
fs.writeFileSync(path.join(outputRoot, 'criteria.json'), criteriaBytes, {flag: 'wx'});
const {reference, checkArtifact} = await import(pathToFileURL(path.join(outputRoot, 'checker.mjs')).href);
const {solve} = await import('../enterprise/compiler.mjs');
const sourceBefore = Object.fromEntries(fs.readdirSync(path.join(root, 'study/enterprise')).filter(x => x.endsWith('.mjs')).map(x => [x, sha(fs.readFileSync(path.join(root, 'study/enterprise', x)))]));

const graph = {nodes: ['a', 'b', 'c', 'd', 'isolated'], edges: [{from:'a',to:'b',weight:2},{from:'a',to:'c',weight:3},{from:'b',to:'d',weight:5},{from:'c',to:'d',weight:7}]};
const bom = {schema:'tae/mission-v1', missionId:'tiny-bom', kind:'bom-demand', graph, seeds:[{node:'a',amount:2}], targets:['d','b','isolated']};
const reach = {...bom, missionId:'tiny-reach', kind:'remediation-impact', seeds:[{node:'a',amount:1},{node:'isolated',amount:0}], targets:['d','isolated']};
const flat = {schema:'tae/mission-v1',missionId:'tiny-flat',kind:'flat-reduction',rows:[{group:'x',amount:7},{group:'y',amount:3},{group:'x',amount:-9}]};
const semanticCases = [
  ['reconvergent-weighted-paths', bom, {groups:[{group:'b',total:4},{group:'d',total:62},{group:'isolated',total:0}],total:66}],
  ['mixed-boolean-reachability', reach, {groups:[{group:'d',total:1},{group:'isolated',total:0}],total:1}],
  ['signed-flat-reduction', flat, {groups:[{group:'x',total:-2},{group:'y',total:3}],total:1}],
];
const tests = semanticCases.map(([name, mission, expected]) => {const actual=reference(mission); return {name, kind:'manual semantic expectation',pass:actual.accepted && canonical(actual.output)===canonical(expected),mission,expected,actual};});
const refusalCases = [
  ['cycle',{...bom, graph:{nodes:['a','b'],edges:[{from:'a',to:'b',weight:1},{from:'b',to:'a',weight:1}]},targets:['b']},'CYCLE'],
  ['zero-edge-weight',{...bom,graph:{...graph,edges:[{from:'a',to:'b',weight:0}]}},'INVALID_EDGE'],
  ['duplicate-target',{...bom,targets:['b','b']},'INVALID_TARGETS'],
  ['empty-seed-array',{...bom,seeds:[]},'INVALID_SEEDS'],
  ['aggregate-output-ceiling',{...flat,rows:[{group:'x',amount:600000},{group:'y',amount:600000}]},'DELIVERY_RESOURCE_CEILING'],
  ['unknown-edge-endpoint',{...bom,graph:{...graph,edges:[{from:'a',to:'absent',weight:1}]}},'INVALID_EDGE'],
];
for (const [name, mission, reason] of refusalCases) {const actual=reference(mission);tests.push({name,kind:'manual refusal expectation',pass:!actual.accepted&&actual.reason===reason,mission,expectedReason:reason,actual});}
const input = encode(bom);
const validArtifact = {schema:'tae.artifact.v1',missionId:bom.missionId,capabilityHash:'a'.repeat(64),inputHash:sha(input),output:semanticCases[0][2],currentProof:null,authority:[]};
const controls = [
  ['correct-artifact',validArtifact,input,true,null],
  ['null-artifact',null,input,false,'INVALID_OBJECT'],
  ['null-input',validArtifact,encode(null),false,'INVALID_OBJECT'],
  ['invalid-json',validArtifact,Buffer.from('{'),false,'INVALID_JSON'],
  ['wrong-output',{...validArtifact,output:{groups:[{group:'b',total:4},{group:'d',total:63},{group:'isolated',total:0}],total:67}},input,false,'SEMANTIC_OUTPUT_MISMATCH'],
  ['wrong-mission',{...validArtifact,missionId:'other'},input,false,'MISSION_ID'],
  ['wrong-input-hash',{...validArtifact,inputHash:'0'.repeat(64)},input,false,'INPUT_HASH'],
  ['invalid-capability-hash',{...validArtifact,capabilityHash:'none'},input,false,'CAPABILITY_IDENTITY'],
  ['inherited-proof',{...validArtifact,currentProof:{accepted:true}},input,false,'INHERITED_PROOF_OR_AUTHORITY'],
  ['inherited-authority',{...validArtifact,authority:['admin']},input,false,'INHERITED_PROOF_OR_AUTHORITY'],
];
for (const [name, artifact, inputBytes, expectedAcceptance, expectedFailure] of controls) {
  try {const actual=checkArtifact(encode(artifact),inputBytes,criteriaBytes);tests.push({name,kind:'proof negative control',pass:actual.accepted===expectedAcceptance&&(!expectedFailure||actual.failures.includes(expectedFailure)),expectedAcceptance,expectedFailure,actual});}
  catch(error){tests.push({name,kind:'proof negative control',pass:false,error:error.message});}
}
const boundaryMissions = [
  ['mixed-case-order',{...flat,rows:[{group:'a',amount:1},{group:'A',amount:1},{group:'z',amount:1},{group:'Z',amount:1}]}],
  ['broader-candidate-labels',{...flat,rows:[{group:'space label',amount:1}]}],
  ['empty-seeds',{...bom,seeds:[]}],
  ['large-cancelling-flat-input',{...flat,rows:[{group:'x',amount:2000000},{group:'x',amount:-2000000}]}],
  ['aggregate-output-bound',{...flat,rows:[{group:'x',amount:600000},{group:'y',amount:600000}]}],
];
const boundaryFindings=[];
for(const [name,mission] of boundaryMissions){
  const candidate=solve(mission),expected=reference(mission);
  const actual=candidate.rows?{groups:candidate.rows.map(r=>({group:r.group,total:Number(r.amount)})),total:candidate.rows.reduce((s,r)=>s+Number(r.amount),0)}:null;
  boundaryFindings.push({name,mission,candidateStatus:candidate.status,candidateDelivery:candidate.delivery,candidateOutput:actual,reference:expected,acceptanceAligned:(candidate.status==='complete'&&candidate.delivery?.status==='ready')===expected.accepted,outputAligned:!expected.accepted||canonical(actual)===canonical(expected.output)});
}
const sourceAfter=Object.fromEntries(Object.keys(sourceBefore).map(x=>[x,sha(fs.readFileSync(path.join(root,'study/enterprise',x)))]));
const report={schema:'tae.separate-agent-review.v1',scope:'Handcrafted unscored microcases; no held-out bank inspected; same-controller logical review, not institutional independence.',checkerSha256:sha(checkerBytes),criteriaSha256:sha(criteriaBytes),sourceBefore,sourceAfter,sourcesUnchanged:canonical(sourceBefore)===canonical(sourceAfter),runtime:process.version,tests,passCount:tests.filter(x=>x.pass).length,testCount:tests.length,boundaryFindings,notes:['The null-object defect was identified in source review before scoring. The owner added a guard before this review executed; the old checker bytes were not retained by this lane, so no executed original-failure claim is made.','The checker hashes the criteria but implements fixed rules in code. The EVM wrapper must separately enforce frozen criteria and checker hashes.','Boundary characterizations are review findings, not additional held-out scored observations.']};
fs.writeFileSync(path.join(outputRoot,'review.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({outputRoot,checkerSha256:report.checkerSha256,criteriaSha256:report.criteriaSha256,testCount:report.testCount,passCount:report.passCount,boundaryMismatches:boundaryFindings.filter(x=>!x.acceptanceAligned||!x.outputAligned).map(x=>x.name),sourcesUnchanged:report.sourcesUnchanged}));
if(report.passCount!==report.testCount||!report.sourcesUnchanged)process.exitCode=1;
