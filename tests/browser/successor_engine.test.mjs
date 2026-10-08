// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {generateKeyPairSync, sign} from 'node:crypto';
import {canonical, digest, parseBounded, validateRequest, newRequest, current, beta, candidate, generateCandidates, workload, discover, freeze, evaluate, renew, verifyNative} from '../../docs/assets/successor/engine.mjs';

test('bounded parser refuses ambiguous, oversized, unsafe or deeply nested input', () => {
    for (const text of ['{"a":1,"a":2}', '{"a":{"z":1,"z":2}}', '1.0', '1e2', '-0', '9007199254740992', '"\\ud800"', '['.repeat(34) + '0' + ']'.repeat(34), '{"x":NaN}', '"'+'a'.repeat(4000000)+'"']) assert.throws(() => parseBounded(text), text.slice(0, 40));
    assert.equal(canonical(parseBounded('{"z":"é🙂","a":[true,null,42]}')), '{"a":[true,null,42],"z":"é🙂"}');
    assert.throws(() => canonical({x: 0.5}));
    assert.throws(() => canonical({é: 1}));
    assert.throws(() => canonical(Array(2)));
});

test('request validation rejects unknown fields and coercions', () => {
    const request = newRequest(); assert.equal(validateRequest(request).mission, 'streaming-metrics-v1');
    assert.deepEqual(validateRequest({request_id:request.request_id}), request);
    assert.throws(() => validateRequest({}));
    for (const patch of [{schema_version: 2}, {seed: '42'}, {seed: true}, {max_events: 20001}, {formation_trials: 7}, {request_id:'BAD'}, {extra: 1}, {language:'unknown'}]) assert.throws(() => validateRequest({...request, ...patch}));
});

test('all generated compositions preserve exact Unicode scalar and rejection semantics', () => {
    const events = [{day:'🙂',service:'__proto__',duration_us:1e9,ok:false},{day:'\ue000',service:'é',duration_us:0,ok:true},{day:'🙂',service:'__proto__',duration_us:2,ok:true}];
    const expected = [{day:'\ue000',service:'é',count:1,total_duration_us:0,max_duration_us:0,error_count:0},{day:'🙂',service:'__proto__',count:2,total_duration_us:1000000002,max_duration_us:1000000000,error_count:1}];
    for (const fn of [current,beta,...generateCandidates(0,12).map(c => e => candidate(e,c))]) {
        assert.deepEqual(fn(events),expected); assert.deepEqual(fn([]),[]);
        for (const patch of [{duration_us:true},{duration_us:-1},{duration_us:1.2},{duration_us:1e9+1},{service:'\udfff'},{day:''},{ok:1},{extra:1}]) assert.throws(() => fn([{...events[0],...patch}]));
        assert.throws(() => fn(Array(20001).fill(events[0])));
    }
    assert.equal(new Set(generateCandidates(5,12).map(canonical)).size,8);
    assert.throws(() => candidate(events,{code:'globalThis.fetch()'}));
    for (const seed of [0,1,42,4294967295]) {
        const e = workload(seed,200,'high');
        for (const c of generateCandidates(seed,8)) assert.deepEqual(candidate(e,c),beta(e));
    }
});

test('real two-generation lifecycle freezes behavior and keeps local claims bounded', async () => {
    const request = newRequest({max_events:128,max_candidates:3,formation_trials:1});
    const discovery = await discover(request); assert.equal(discovery.attempts.length,3);
    const frozen = await freeze(request,discovery,'0'.repeat(64));
    const report = await evaluate(request,frozen); assert.equal(report.correctness,true);
    assert.equal(report.cases.length,6); assert.equal(report.institutional_verdict,'HOLD'); assert.deepEqual(report.authority,[]);
    await assert.rejects(evaluate({...request,seed:1},frozen));
    const corrupt = structuredClone(frozen); corrupt.manifest.grammar.cache_last = !corrupt.manifest.grammar.cache_last;
    await assert.rejects(evaluate(request,corrupt));
    const second = await renew(request,discovery,{engineSourceHash:'0'.repeat(64)}); assert.equal(second.trials.length,1); assert.deepEqual(second.active_proof,[]); assert.deepEqual(second.authority,[]);
    assert.equal(second.trials[0].control_attempts, second.trials[0].treatment_attempts);
});

test('cancellation stops formation and can be retried without inherited results', async () => {
    const request = newRequest(), controller = new AbortController();
    await assert.rejects(discover(request,{signal:controller.signal,onProgress:()=>controller.abort()}), {name:'AbortError'});
    assert.equal((await discover(request)).attempts.length,request.max_candidates);
});

test('native file return is request-bound; hashes never create authority', async () => {
    const request = newRequest(), request_hash = await digest('request',request);
    const evidence = {request,request_hash,scope:'local-native-rehearsal',result:'HOLD'};
    const envelope = {schema_version:1,kind:'successor-result',request_hash,evidence,evidence_hash:await digest('evidence',evidence),scope:'local-native-rehearsal',signature:null};
    const checked = await verifyNative(request,envelope); assert.equal(checked.authenticity,'unverified'); assert.deepEqual(checked.authority,[]);
    await assert.rejects(verifyNative({...request,seed:request.seed+1},envelope));
    await assert.rejects(verifyNative(request,{...envelope,evidence:{...evidence,result:'PASS'}}));
    const {publicKey, privateKey} = generateKeyPairSync('ed25519');
    const public_key = Buffer.from(publicKey.export({format:'jwk'}).x, 'base64url').toString('hex');
    const validSignature = sign(null, Buffer.from(envelope.evidence_hash, 'hex'), privateKey);
    const signed = {...envelope,signature:{public_key,signature:validSignature.toString('base64')}};
    assert.equal((await verifyNative(request, signed)).authenticity, 'unverified');
    const changed = Buffer.from(validSignature); changed[40] ^= 1;
    await assert.rejects(verifyNative(request,{...signed,signature:{public_key,signature:changed.toString('base64')}}));
    const smallOrder = ['00'.repeat(32), '01'+'00'.repeat(31), 'ec'+'ff'.repeat(30)+'7f', '26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05', 'c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a'];
    for (const encoded of smallOrder) for (const signBit of [0, 128]) {
        const point = Buffer.from(encoded, 'hex'); point[31] |= signBit;
        await assert.rejects(verifyNative(request,{...envelope,signature:{public_key:point.toString('hex'),signature:'A'.repeat(86)+'=='}}));
        const zeroR = Buffer.from(validSignature); point.copy(zeroR, 0);
        await assert.rejects(verifyNative(request,{...signed,signature:{public_key,signature:zeroR.toString('base64')}}));
    }
    for (let seed = 0; seed < 16; seed++) {
        const bound = {...request, seed}, boundHash = await digest('request', bound);
        const payload = {...evidence, request:bound, request_hash:boundHash};
        await assert.rejects(verifyNative(bound,{...envelope,request_hash:boundHash,evidence:payload,evidence_hash:await digest('evidence',payload),signature:{public_key:'0'.repeat(64),signature:'A'.repeat(86)+'=='}}));
    }
    const nonCanonicalS = Buffer.from(validSignature); nonCanonicalS.fill(255, 32);
    await assert.rejects(verifyNative(request,{...signed,signature:{public_key,signature:nonCanonicalS.toString('base64')}}));
    await assert.rejects(verifyNative(request,{...signed,signature:{public_key:'ed'+'ff'.repeat(30)+'7f',signature:validSignature.toString('base64')}}));
    const scopeAttack = {...evidence,scope:'independent-proof'};
    await assert.rejects(verifyNative(request,{...envelope,evidence:scopeAttack,evidence_hash:await digest('evidence',scopeAttack)}));
});

test('Python and JavaScript share checked canonical commitment vectors', async () => {
    const path = new URL('../../alpha_factory_v1/core/runtime/successor/canonical-vectors.json',import.meta.url);
    if (!fs.existsSync(path)) throw Error('Shared Python canonical vectors are required');
    const vectors = JSON.parse(fs.readFileSync(path,'utf8'));
    for (const vector of vectors.vectors ?? vectors) {
        assert.equal(await digest(vector.domain,vector.value),vector.digest ?? vector.sha256);
        if (vector.domain === 'request') assert.equal(canonical(validateRequest({request_id:vector.value.request_id})), vector.canonical);
    }
});
