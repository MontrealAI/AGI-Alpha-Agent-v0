const assert = require('node:assert/strict');
const fs = require('node:fs');
const solc = require('solc');
const { ethers } = require('hardhat');
const policy = require('../scripts/compiler-policy');
const cases=[
 ['reassigned_reference_memory_alias.sol', async c=>[await c.f.staticCall(0,0),await c.f.staticCall(0,1)],[67n,7n]],
 ['reassigned_reference_memory_alias_from_storage_minimal.sol',async c=>[await c.f.staticCall(0,0),await c.f.staticCall(0,1)],[67n,7n]],
 ['reassigned_reference_storage_alias.sol',async c=>{const a=await c.g.staticCall(0,2,0xaaaa,0xbbbb),b=await c.g.staticCall(0,3,0xaaaa,0xbbbb);await (await c.rmw(0,1)).wait();return [a,b,await c.a(1)];},[0xbbbbn,0xaaaan,501n]]
];
describe('SOL-2026-7 compiler workaround on disposable EVM',function(){
 this.timeout(240000);
 it('pins exact compiler and removes only L/E including cleanup',()=>{assert(solc.version().startsWith('0.8.37+commit.f401782d.'));assert.equal(policy.OPTIMIZER_STEPS,policy.DEFAULT_STEPS.replace(/[LE]/g,'')+':'+policy.CLEANUP_STEPS);assert(!/[LE]/.test(policy.OPTIMIZER_STEPS));assert.equal(policy.CLEANUP_STEPS,'fDnTOcmuO');assert.equal(policy.DEFAULT_STEPS,'dfDvulfnTUtnIfxa[r]EscLMVcul[j]Trpeulxa[r]cLvifMCTUca[r]LSsTFOtfDnca[r]IulcscCTUtvifMx[scCTUt]TOntnfDIulvifMjmul[jul]VcTOculjmul');});
 for(const [name,observe,expected] of cases)it(name+' matches upstream semantic expectations with workaround',async()=>{
  const source=fs.readFileSync(require('path').join(__dirname, 'fixtures/SOL-2026-7', name),'utf8');
  const signer=(await ethers.getSigners())[0],results={};
  for(const [label,optimizer] of [['default',{enabled:true,runs:200}],['workaround',policy.OPTIMIZER]]){
   const out=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources:{'C.sol':{content:source}},settings:{optimizer,viaIR:true,evmVersion:'cancun',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}})));
   assert.deepEqual((out.errors||[]).filter(e=>e.severity==='error'),[]);
   const c=out.contracts['C.sol'].C, deployed=await new ethers.ContractFactory(c.abi,'0x'+c.evm.bytecode.object,signer).deploy();await deployed.waitForDeployment();results[label]=await observe(deployed);
  }
  console.log(JSON.stringify({fixture:name,default:results.default.map(String),workaround:results.workaround.map(String),expected:expected.map(String)}));
  assert.deepEqual(results.workaround,expected);
  // Controls expose whether this exact fixture triggers the old compiler under this profile.
  assert.notDeepEqual(results.default,expected);
 });
});
