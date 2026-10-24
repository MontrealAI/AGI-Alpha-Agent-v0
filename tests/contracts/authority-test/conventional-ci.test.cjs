// SPDX-License-Identifier: Apache-2.0
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {campaign}=require('./conventional-ci-evidence.cjs');
test('CI summaries enforce five unique receipts, no bindings and retained locks',()=>{
 const hashes=Array.from({length:5},(_,i)=>'0x'+String(i+1).repeat(64)),r={status:'awaiting-governor-bindings',creationHashes:hashes,creationEvidence:hashes.map((transactionHash,index)=>({transactionHash,index})),governanceHashes:[],finalAuthorityVerified:false,activationAllowed:false,actorLocksRetained:true,relayCount:5,prompts:2,closes:2};assert.equal(campaign(r).relayCount,5);
 for(const [key,value] of Object.entries({status:'complete',finalAuthorityVerified:true,activationAllowed:true,actorLocksRetained:false,relayCount:6,prompts:1,closes:1,governanceHashes:[hashes[0]],creationHashes:[...hashes.slice(0,4),hashes[0]]}))assert.throws(()=>campaign({...r,[key]:value}));
 const summary=campaign({...r,privateKey:'SENTINEL',preflight:{untrusted:'SENTINEL'}});assert(!JSON.stringify(summary).includes('SENTINEL'));
});
test('workflow keeps old strong campaigns and bounded separate conventional coverage',()=>{
 const w=fs.readFileSync(path.join(__dirname,'../../../.github/workflows/alpha-authority-v2.yml'),'utf8');assert.match(w,/timeout-minutes: 45/);assert.match(w,/conventional-qualification:/);assert.match(w,/timeout-minutes: 15/);assert.match(w,/timeout -k 5s 300s/);assert.match(w,/conventional-creator-local.test.js/);assert.match(w,/conventional-creator.test.cjs/);
 for(const p of ['empty','delegated','marker'])assert(w.includes('ALPHA_NATIVE_PROFILE='+p));assert.match(w,/permissions:\n  contents: read/);assert.doesNotMatch(w,/secrets\.|contents: write|id-token:|continue-on-error|\|\| true/);
});

test('exact actions and shards stay finite behind the trusted paper classifier',()=>{
 const w=fs.readFileSync(path.join(__dirname,'../../../.github/workflows/alpha-authority-v2.yml'),'utf8');
 assert.deepEqual([...w.split('\njobs:\n')[1].matchAll(/^  ([a-z-]+):$/gm)].map(x=>x[1]),['paper-scope','offline-qualification','conventional-qualification']);
 assert.ok(w.includes('  paper-scope:\n    uses: ./.github/workflows/paper-scope.yml\n\n  offline-qualification:'));
 const scopeGate="    if: ${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}\n    needs: paper-scope\n";
 for(const name of ['offline-qualification','conventional-qualification'])assert.ok(w.includes('  '+name+':\n'+scopeGate));
 const sections=w.split('\n  conventional-qualification:\n');assert.equal(sections.length,2);const job=sections[1];
 const actions=[...job.matchAll(/uses: ([^\s]+)/g)].map(x=>x[1]);assert.deepEqual(actions,['actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd','actions/setup-node@53b83947a5a98c8d113130e565377fae1a50d02f','actions/upload-artifact@bbbca2ddaa5d8feaa63e36b76fdaad77386f024f']);
 assert.deepEqual([...job.matchAll(/^          run_check ([a-z-]+) /gm)].map(x=>x[1]),['compile','unit','local']);
 assert.match(job,/ref: \$\{\{ github.event.pull_request.head.sha \|\| github.sha \}\}/);assert.match(job,/persist-credentials: false/);assert.match(job,/node-version: '22\.17\.1'/);assert.match(job,/npm ci --prefix tests\/contracts/);assert.match(job,/dae16bcbc91f745d6e411a7157f381d299e0e74b946f9749e36f82d260894744/);
 assert.match(job,/conventional-ci-evidence.cjs init/);assert.match(job,/conventional-ci-evidence.cjs finish/);assert.match(job,/path: \$\{\{ env.ALPHA_CONVENTIONAL_STATE_DIRECTORY \}\}\/public\//);
 assert.doesNotMatch(w,/pull_request_target|secrets\.|contents: write|id-token:|git push|gh release|npm publish|environment:|--invert|continue-on-error|\|\| true/);
});
