// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {reserveJob,reserveJobUncached,clearReservationCache,reservationCacheStats} from './workflow.mjs';
clearReservationCache();
for(const complexity of [1,2.4,4])for(const assets of [{},{representation:true},{representation:true,certificate:true},{experiment:true}]){
  const config={tokenMultiplier:2.3,computeMultiplier:1.7,betaResourceFactor:.8,betaBundleAbsorption:.5,maxRetries:2};
  const job={id:'synthetic-cache',complexity,scopeSupported:true};
  const expected=reserveJobUncached(config,job,assets),first=reserveJob(config,job,assets);
  assert.deepEqual(first,expected,'Memoization must preserve every rounded field exactly');
  assert.equal(reserveJob(config,{...job,id:'fresh-different-id'},assets),first,'Identity does not affect blind resources');
  assert.ok(Object.isFrozen(first)&&Object.isFrozen(first.resources)&&Object.isFrozen(first.tokens));
  assert.ok(Object.values(first.roleUsage).every(Object.isFrozen));
  assert.throws(()=>{first.resources.cpuHours=0;},TypeError);
  assert.throws(()=>{first.roleUsage.intake.costCents=0;},TypeError);
}
const mutable={tokenMultiplier:1},job={complexity:1,candidateCount:2};
const before=reserveJob(mutable,job);mutable.tokenMultiplier=2;
const changed=reserveJob(mutable,job);assert.deepEqual(changed,reserveJobUncached(mutable,job));
assert.notEqual(changed.tokens.input,before.tokens.input,'Config mutations cannot reuse stale reservations');
mutable.betaResourceFactor=.5;assert.deepEqual(reserveJob(mutable,job),reserveJobUncached(mutable,job));
delete mutable.betaResourceFactor;assert.deepEqual(reserveJob(mutable,job),reserveJobUncached(mutable,job));
const complex={tokenMultiplier:1,unrelatedNested:{x:1}};
assert.deepEqual(reserveJob(complex,job),reserveJobUncached(complex,job));
assert.ok(reservationCacheStats().bypasses>0);
assert.ok(reservationCacheStats().hits>0);assert.ok(reservationCacheStats().size<=4096);
clearReservationCache();assert.equal(reservationCacheStats().size,0);
console.log('Exact reservation memoization controls passed: equality, mutation invalidation, deep immutability and bounded cache.');
