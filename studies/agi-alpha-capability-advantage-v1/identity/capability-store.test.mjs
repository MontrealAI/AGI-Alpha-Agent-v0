// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, writeFileSync, mkdtempSync, rmSync, symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createCapabilityStore} from './capability-store.mjs';
import {digest, verifyEpochInclusion} from './vendor/commitments.mjs';

const fixture = JSON.parse(readFileSync(new URL('./authority-fixtures.json', import.meta.url)));
const sha = value => createHash('sha256').update(value).digest('hex');
const source = 'export const solve = input => input.reduce((a,b)=>a+b,0);\n';
const verifierSource = 'Research fixture control: independently recompute sums; not a scientific skill claim.\n';

function setup(options = {}) {
  const root = mkdtempSync(path.join(tmpdir(), 'capability-identity-'));
  writeFileSync(path.join(root, 'solver.mjs'), source);
  writeFileSync(path.join(root, 'verifier.txt'), verifierSource);
  writeFileSync(path.join(root, 'evidence.json'), JSON.stringify({inputs:[2,3,5], result:10}));
  writeFileSync(path.join(root, 'composition.json'), JSON.stringify({input:3, first:6, second:36}));
  const file = name => ({path:name, sha256:sha(readFileSync(path.join(root, name)))});
  let validations = 0, compositionChecks = 0;
  async function verifier({binding, evidenceFiles}) {
    validations++;
    const evidence = JSON.parse(evidenceFiles[0].text);
    return {accepted:evidence.inputs.reduce((a,b)=>a+b,0) === evidence.result,
      checks:1, implementationDigest:binding.implementationDigest, evidenceDigest:binding.evidenceDigest, scopeDigest:binding.scopeDigest};
  }
  async function compositionVerifier({bindingDigest, evidenceFiles}) {
    compositionChecks++;
    const e = JSON.parse(evidenceFiles[0].text);
    return {accepted:e.first === e.input * 2 && e.second === e.first ** 2, checks:2, compositionValidated:true, bindingDigest};
  }
  const store = createCapabilityStore({rootDirectory:root, fixture, verifier, compositionVerifier,
    verifierSource:[file('verifier.txt')], compositionVerifierSource:[file('verifier.txt')], ...options});
  const dossier = (id='forward', dependencies=[], version='1') => ({id, version, creator:'creator.agent.agi.eth',
    motivatingJob:'DEVELOPMENT_CONTROL_NOT_PRIMARY', outputs:[id+'-result'], dependencies,
    implementation:{entrypoint:'solver.mjs',files:[file('solver.mjs')]}, evidence:{files:[file('evidence.json')], claimedPass:true},
    scope:{family:'control',limits:['Fixture software controls only']}, environment:{runtime:'node'},
    rights:{license:'Apache-2.0',data:'synthetic'}, expiresAt:500});
  const select = (record, extra={}) => {
    const rootRecord = store.inspect().roots.at(-1);
    return store.select(record.dossier.outputs[0], {scopeDigest:record.binding.scopeDigest,
      environmentDigest:record.binding.environmentDigest, rightsDigest:record.binding.rightsDigest,
      expectedRoot:rootRecord.graphRoot, ...extra});
  };
  const composition = () => ({id:'forward-inverse-composition', target:'inverse@1', members:['forward@1','inverse@1'],
    evidence:{files:[file('composition.json')]}, scope:'Control composition only'});
  return {root, store, dossier, file, select, composition, counts:()=>({validations,compositionChecks}), cleanup:()=>rmSync(root,{recursive:true,force:true})};
}

test('actual verifier runs before admission; creator has no implied validation authority', async () => {
  const t=setup(); try {const r=await t.store.admit(t.dossier()); assert.equal(t.counts().validations,1);
    assert.equal(r.creator,'creator.agent.agi.eth'); assert.equal(r.attester,'research.agent.agi.eth');
    assert.equal(r.validationSigner,'fixture:attestation-delegate'); assert.equal(r.liveIdentityEnforcement,'NOT_RUN');
    assert.deepEqual(r.nativeAuthority,[]);} finally {t.cleanup();}
});
test('self asserted PASS with false evidence is refused by independent recomputation', async () => {
  const t=setup(); try {writeFileSync(path.join(t.root,'evidence.json'),JSON.stringify({inputs:[2,3,5],result:11}));
    await assert.rejects(t.store.admit(t.dossier()),/INDEPENDENT_VALIDATION_FAILED/); assert.equal(t.store.inspect().records.length,0);
  } finally {t.cleanup();}
});
test('club and nested names do not acquire graph-attestation eligibility', async () => {
  const t=setup(); try {for(const agent of ['research.club.agi.eth','child.research.agent.agi.eth']) {
    await assert.rejects(t.store.admit(t.dossier(),{agent}),/INELIGIBLE_DIRECT_AGENT/);}}
  finally {t.cleanup();}
});
test('root-only signer cannot attest; attester cannot publish', async () => {
  const t=setup(); try {await assert.rejects(t.store.admit(t.dossier(),{signer:'fixture:root-delegate'}),/ATTESTATION_REFUSED/);
    await t.store.admit(t.dossier()); assert.throws(()=>t.store.publish({signer:'fixture:attestation-delegate'}),/ROOT_PUBLICATION_REFUSED/);
    assert.equal(t.store.publish().root.mode,'FIXTURE_ONLY');} finally {t.cleanup();}
});
test('registry and graph use identical admitted evidence and dependency information', async () => {
  const t=setup(); try {await t.store.admit(t.dossier()); const inverse=await t.store.admit(t.dossier('inverse',['forward@1']));
    await t.store.admitComposition(t.composition()); t.store.publish(); const a=t.select(inverse,{strategy:'registry'}),b=t.select(inverse,{strategy:'graph'});
    assert.equal(a.ok,true); assert.deepEqual(a.selected,b.selected); assert.equal(a.relationshipRows,b.relationshipRows);
    assert.equal(t.counts().compositionChecks,1);} finally {t.cleanup();}
});
test('validated components do not authorize unvalidated composition', async () => {
  const t=setup(); try {await t.store.admit(t.dossier());const inverse=await t.store.admit(t.dossier('inverse',['forward@1']));t.store.publish();
    assert.match(t.select(inverse).reason,/COMPOSITION_NOT_INDEPENDENTLY_VALIDATED/);} finally {t.cleanup();}
});
test('independent composition verifier rejects a false combined workflow', async () => {
  const t=setup(); try {await t.store.admit(t.dossier());await t.store.admit(t.dossier('inverse',['forward@1']));
    writeFileSync(path.join(t.root,'composition.json'),JSON.stringify({input:3,first:6,second:37}));
    await assert.rejects(t.store.admitComposition(t.composition()),/INDEPENDENT_COMPOSITION_VALIDATION_FAILED/);} finally {t.cleanup();}
});
test('composition closure cannot omit a dependency', async () => {
  const t=setup(); try {await t.store.admit(t.dossier());await t.store.admit(t.dossier('inverse',['forward@1']));
    const c=t.composition();c.members=['inverse@1','forward@1'];await assert.rejects(t.store.admitComposition(c),/COMPOSITION_CLOSURE_MISMATCH/);
  } finally {t.cleanup();}
});
test('source mutation prevents reuse even with unchanged Merkle root', async () => {
  const t=setup(); try {const r=await t.store.admit(t.dossier());t.store.publish();writeFileSync(path.join(t.root,'solver.mjs'),source+'broken\n');
    assert.match(t.select(r).reason,/FILE_IDENTITY_CHANGED/);} finally {t.cleanup();}
});
test('evidence mutation prevents reuse despite claimed PASS', async () => {
  const t=setup(); try {const r=await t.store.admit(t.dossier());t.store.publish();writeFileSync(path.join(t.root,'evidence.json'),'{}');
    assert.match(t.select(r).reason,/FILE_IDENTITY_CHANGED/);} finally {t.cleanup();}
});
test('expiry and authority transfer block current reuse, historical roots remain', async () => {
  const t=setup(); try {const r=await t.store.admit(t.dossier());t.store.publish();
    assert.equal(t.select(r,{now:501}).ok,false);assert.equal(t.select(r,{now:250,snapshotId:'fixture-state-200'}).ok,false);
    assert.equal(t.store.inspect().roots.length,1);} finally {t.cleanup();}
});
test('revocation appends history and blocks fresh reuse', async () => {
  const t=setup();try{const r=await t.store.admit(t.dossier());const root1=t.store.publish().root;
    t.store.revoke('forward@1','Independent replay failed after new evidence');const root2=t.store.publish().root;
    assert.equal(root2.previousRoot,root1.graphRoot);assert.equal(t.select(r).ok,false);assert.equal(t.store.inspect().events.length,1);
  }finally{t.cleanup();}
});
test('supersession preserves old evidence and selects current version', async () => {
  const t=setup();try{const old=await t.store.admit(t.dossier());t.store.publish();await t.store.admit(t.dossier('forward',[],'2'));
    t.store.supersede('forward@1','forward@2','New independently validated version');t.store.publish();
    assert.deepEqual(t.select(old).selected,['forward@2']);assert.equal(t.store.inspect().records.length,2);
  }finally{t.cleanup();}
});
test('revalidation reruns actual verifier and cannot rewrite a version', async () => {
  const t=setup();try{const d=t.dossier();await t.store.admit(d);t.store.publish();
    await t.store.admit(d,{revalidation:true});assert.equal(t.counts().validations,2);
    const changed=structuredClone(d);changed.motivatingJob='Different';await assert.rejects(t.store.admit(changed,{revalidation:true}),/REVALIDATION_CANNOT_REWRITE_VERSION/);
  }finally{t.cleanup();}
});
test('dependency absence or incompatible source is refused before admission', async () => {
  const t=setup();try{await assert.rejects(t.store.admit(t.dossier('inverse',['unknown@1'])),/MISSING_SKILL/);
    await t.store.admit(t.dossier());writeFileSync(path.join(t.root,'solver.mjs'),'changed');
    await assert.rejects(t.store.admit(t.dossier('inverse',['forward@1'])),/FILE_IDENTITY_CHANGED/);
  }finally{t.cleanup();}
});
test('wrong root or scope cannot be supplied as trust anchor', async () => {
  const t=setup();try{const r=await t.store.admit(t.dossier());t.store.publish();
    assert.match(t.select(r,{expectedRoot:'0'.repeat(64)}).reason,/TRUSTED_ROOT_REQUIRED/);
    assert.match(t.select(r,{scopeDigest:digest('other','tested-scope')}).reason,/MISSION_SCOPE/);
  }finally{t.cleanup();}
});
test('Merkle membership rejects changed skill and is not execution permission', async () => {
  const t=setup();try{const r=await t.store.admit(t.dossier());const state=t.store.publish();const leaf=state.forest.classes.skill.records[0];
    assert.equal(verifyEpochInclusion(state.root,'skill',leaf.record,leaf.proof),true);leaf.record.creator='changed.agent.agi.eth';
    assert.equal(verifyEpochInclusion(state.root,'skill',leaf.record,leaf.proof),false);
    assert.throws(()=>t.store.authorizeLocalExecution(t.select(r),{missionId:'M1'}),/SEPARATE_LOCAL_EXECUTION/);
  }finally{t.cleanup();}
});
test('separate finite local permission cannot be forged or overdrawn', async () => {
  const t=setup({executionPolicy:{mode:'LOCAL_RESEARCH_ONLY',nativeAuthority:[],allowedSkills:['forward@1'],maxRuns:1,expiresAt:400}});
  try{const r=await t.store.admit(t.dossier());t.store.publish();const selection=t.select(r);
    assert.throws(()=>t.store.authorizeLocalExecution({...selection},{missionId:'M0'}),/CURRENT_SELECTION_REQUIRED/);
    const allowed=t.store.authorizeLocalExecution(selection,{missionId:'M1'});assert.deepEqual(allowed.nativeAuthority,[]);
    assert.throws(()=>t.store.authorizeLocalExecution(selection,{missionId:'M2'}),/EXECUTION_BUDGET_EXHAUSTED/);
  }finally{t.cleanup();}
});
test('symlink and path traversal cannot substitute bound source', async () => {
  const t=setup();try{symlinkSync('/etc/hostname',path.join(t.root,'escape'));const d=t.dossier();d.implementation.files=[t.file('escape')];
    await assert.rejects(t.store.admit(d),/FILE_OUTSIDE_ROOT|SYMLINK_FORBIDDEN/);
  }finally{t.cleanup();}
});
test('descriptive PASS callback with wrong binding is refused', async () => {
  const t=setup({verifier:async()=>({accepted:true,checks:1,implementationDigest:'0'.repeat(64),evidenceDigest:'0'.repeat(64),scopeDigest:'0'.repeat(64)})});
  try{await assert.rejects(t.store.admit(t.dossier()),/VALIDATOR_BINDING_MISMATCH/);}finally{t.cleanup();}
});
