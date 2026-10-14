// SPDX-License-Identifier: Apache-2.0
// Run after npm ci --prefix tests/contracts. No network, wallet, signing or token movement.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {METHODS, SELECTORS, ACTIONS, callData, decode} from '../../docs/assets/ascension-wallet/protocol.mjs';
const require=createRequire(new URL('../contracts/package.json',import.meta.url));
const {Interface, id, keccak256}=require('ethers');
const archive=new URL('../../deployments/ethereum-mainnet/2026-10-11/',import.meta.url);
const read=name=>JSON.parse(readFileSync(new URL(name,archive),'utf8'));
const compiled=read('compiled-contracts.json'), manifest=read('manifest.json'), runtimes=read('runtime-code.json');
const names={Access:'AscensionAccess',Seed:'NovaSeed',Oracle:'AscensionRiskOracle',Jobs:'AscensionJobMarket',Mark:'AscensionMark'};
const interfaces=Object.fromEntries(Object.entries(names).map(([key,name])=>[key,new Interface(compiled[name].abi)]));
function example(type,n) {
  if(Array.isArray(type)) return type.map(t=>example(t,n));
  if(type==='string') return n%2?'é / public result':'g'.repeat(n);
  if(type==='bytes32') return '0x'+n.toString(16).padStart(2,'0').repeat(32);
  if(type==='address') return '0x'+(n+1).toString(16).padStart(2,'0').repeat(20);
  if(type==='bool') return n%2===0;
  if(type==='address[3]') return [1,2,3].map(v=>example('address',v));
  if(type==='bytes32[]') return Array.from({length:n%5},(_,v)=>example('bytes32',v));
  return String((1n<<BigInt(Number(type.slice(4))))-1n-BigInt(n));
}
for(const [key,m] of Object.entries(METHODS)) test(`ABI/selector differential: ${m.signature}`,()=>{
  assert.equal(SELECTORS[key],id(m.signature).slice(0,10));
  const iface=new Interface([`function ${m.signature}${m.outputs.length?` returns (${m.outputs.join(',')})`:''}`]);
  for(let n=0;n<12;n++) {
    const values=m.inputs.map(t=>example(t,n));
    assert.equal(callData(key,values),iface.encodeFunctionData(m.signature,values));
    if(m.outputs.length) {
      const expected=m.outputs.map(t=>example(t,n));
      const bytes=iface.encodeFunctionResult(m.signature,expected);
      assert.deepEqual(decode(m.outputs,bytes),[...iface.decodeFunctionResult(m.signature,bytes)].map(v=>typeof v==='string'&&v.startsWith('0x')?v.toLowerCase():v));
    }
  }
});
for(const [key,a] of Object.entries(ACTIONS)) test(`action uses exact archived ABI: ${key}`,()=>{
  const m=METHODS[a.method];
  if(a.contract==='Token') return; // External canonical ERC-20, not an archived Ascension source artifact.
  const fragment=interfaces[a.contract].getFunction(m.signature);
  assert.ok(fragment); assert.equal(fragment.selector,SELECTORS[a.method]);
  assert.deepEqual(fragment.outputs.map(v=>v.type),m.outputs);
});
test('every read signature exists in an archived ABI or the canonical ERC20 surface',()=>{
  const external=new Set(['balanceOf','allowance','approve','decimals']);
  for(const [key,m] of Object.entries(METHODS)) {
    if(external.has(key)) continue;
    const found=Object.values(interfaces).map(i=>i.getFunction(m.signature)).find(Boolean);
    assert.ok(found,`Missing ${m.signature}`);assert.deepEqual(found.outputs.map(o=>o.type),m.outputs);
  }
});
test('generated profile matches archived exact-byte SHA256 and Ethereum Keccak hashes',()=>{
  const p=JSON.parse(readFileSync(new URL('../../docs/assets/ascension-wallet/profile.json',import.meta.url),'utf8'));
  assert.equal(p.newExposureEnabled,false);
  for(const [alias,name] of Object.entries(names)) {
    assert.equal(keccak256(runtimes[name]),manifest.contracts[name].runtimeCodeHash);
    assert.equal(createHash('sha256').update(Buffer.from(runtimes[name].slice(2),'hex')).digest('hex'),p.contracts[alias].sha256);
    assert.equal(p.contracts[alias].address,manifest.contracts[name].address);
  }
});
