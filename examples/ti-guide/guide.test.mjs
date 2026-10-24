// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import * as guide from './guide.mjs';

test('the sample computes real conflicts and retains each original exception in one group', async () => {
    const result = await guide.compute(guide.SAMPLE);
    assert.equal(result.metrics.leftRows, 6); assert.equal(result.metrics.rightRows, 4);
    assert.equal(result.metrics.unmatchedKeys, 2); assert.equal(result.metrics.conflictingPairs, 4);
    assert.equal(result.metrics.actionGroups, 4); assert.equal(result.metrics.evidenceReferences, 6);
    assert.equal(result.differences.length, 6);
    const refs = result.resolution.actions.flatMap(x => x.occurrences);
    assert.equal(new Set(refs).size, refs.length);
    assert.deepEqual(new Set(refs),new Set(result.differences.map(x => x.occurrence)));
    assert.equal(result.limitations.timeSavedMeasured,false); assert.equal(result.resolution.automaticallyResolved,false);
});
test('duplicates retain the cartesian pairs, every conflicting field and unexamined columns', async () => {
    const input = {leftCsv:'id,a,b,left-only\nX,1,2,z\nX,3,4,y\n',rightCsv:'key,a,b,right-only\nX,5,6,q\nX,7,8,r\n',leftKey:'id',rightKey:'key'};
    const result=await guide.compute(input);
    assert.equal(result.metrics.matchedPairs,4); assert.equal(result.metrics.conflictingPairs,4);
    assert.equal(result.metrics.fieldDifferences,8); assert.equal(result.metrics.evidenceReferences,4);
    assert.equal(result.metrics.actionGroups,1); assert.equal(new Set(result.differences.map(x=>x.id)).size,8);
    assert.deepEqual(result.metrics.unsharedLeft,['left-only']); assert.deepEqual(result.metrics.unsharedRight,['right-only']);
});
test('separate exceptions and equal lists do not invent a grouping improvement', async () => {
    for (const [a,b,expected] of [['id,v\nA,1\n','id,v\nA,1\n',0],['id,v\nA,1\n','id,v\nB,2\n',2]]) {
        const result=await guide.compute({leftCsv:a,rightCsv:b,leftKey:'id',rightKey:'id'});
        assert.equal(result.metrics.actionGroups,expected);assert.equal(result.resolution.diagnosis.groupingReducesDecisionItems,false);
    }
});
test('saved records recheck exact inputs, settings, results and limitations without inheriting authority', async () => {
    const result=await guide.compute(guide.SAMPLE);
    const saved=guide.makeWorkspace(guide.SAMPLE,result,{approach:'original',sourceHash:'frozen',runId:'run-1',createdAt:'2026-10-24T12:00:00Z',language:'fr'});
    assert.deepEqual(await guide.restoreWorkspace(JSON.stringify(saved),'frozen'),saved);
    for(const alter of [x=>x.result.metrics.actionGroups++,x=>x.input.leftCsv+='MUG,Other,99\n',x=>x.authority='approved',x=>x.approach='hidden',x=>x.sourceHash='changed',x=>x.limitations.timeSavedMeasured=true,x=>x.result.resolution.actions[0].occurrences=[]]) {
        const copy=structuredClone(saved);alter(copy);await assert.rejects(()=>guide.restoreWorkspace(JSON.stringify(copy),'frozen'));
    }
    const changed=await guide.compute({...guide.SAMPLE,rightCsv:'item,name,price\nMUG,Stoneware mug,12\n'});
    assert.notDeepEqual(changed.metrics,result.metrics);assert.notEqual(changed.rightIdentity.sha256,result.rightIdentity.sha256);
});
test('formula and HTML payloads stay inert and every CSV export neutralizes formula starters', async () => {
    const data={leftCsv:'id,value\n=SUM(1),<img src=x onerror=alert(1)>\n',rightCsv:'id,value\n=SUM(1),@evil\n',leftKey:'id',rightKey:'id'};
    const result=await guide.compute(data), csv=guide.fullDifferencesCsv(result);
    assert.match(csv,/'=SUM\(1\)/);assert.match(csv,/'@evil/);assert.match(guide.actionPlanCsv(result),/'=SUM\(1\)/);
    assert.equal(result.differences[0].leftValue,'<img src=x onerror=alert(1)>');
    for(const value of ['=a',' +x','\t-a','@x','-3','\n=x'])assert.match(guide.safeCsv([[value]]),/^"'/);
});
test('invalid identifiers, malformed CSV and bounded resources refuse rather than fabricate results', async () => {
    for(const change of [{leftKey:'missing'},{leftCsv:'id,id\nA,B'},{leftCsv:'item,name\nA'},{leftCsv:'item,name\nA,"oops'},{leftCsv:'item,name\n,blank'},{leftCsv:'item\n'+('X\n'.repeat(1501))},{leftCsv:'item\n'+'x'.repeat(200001)}]) {
        await assert.rejects(()=>guide.compute({...guide.SAMPLE,...change}));
    }
    const many='id\n'+'X\n'.repeat(101);
    await assert.rejects(()=>guide.compute({leftCsv:many,rightCsv:many,leftKey:'id',rightKey:'id'}),/10000/);
    const wide = 'id,value\n' + ('X,'+'a'.repeat(4000)+'\n').repeat(45);
    const short = 'id,value\n' + 'X,b\n'.repeat(45);
    await assert.rejects(()=>guide.compute({leftCsv:wide,rightCsv:short,leftKey:'id',rightKey:'id'}),/evidence exceeds/);
});
