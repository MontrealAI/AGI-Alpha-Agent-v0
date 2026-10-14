// SPDX-License-Identifier: Apache-2.0
// Injected only by acceptance tests. Never shipped by the wallet workspace.
(() => {
  const cfg=window.__markFixtureConfig, A='0x1111111111111111111111111111111111111111';
  const HASH='0x'+'ab'.repeat(32), BLOCK='0x'+'12'.repeat(32), events=new Map();
  const module=()=>import(cfg.origin+'assets/ascension-wallet/protocol.mjs');
  const provider=window.__markFixture={chain:'0x1',account:A,calls:[],sends:0,mode:'success',finalized:true,
    last:JSON.parse(localStorage.getItem('__mark_fixture_tx')||'null'),
    on(event,fn){events.set(event,fn);},removeListener(event){events.delete(event);},emit(event){events.get(event)?.();},
    async request({method,params=[]}) {
      this.calls.push(method);
      if(method==='eth_chainId') return this.chain;
      if(method==='eth_accounts') return this.account?[this.account]:[];
      if(method==='eth_requestAccounts') {this.account=A;return [A];}
      if(method==='eth_getTransactionCount') return '0x0';
      if(method==='eth_getBalance') return '0xde0b6b3a7640000';
      if(method==='eth_getBlockByNumber') return {number:params[0]==='finalized'&&!this.finalized?'0xff':'0x100',hash:this.reorg?'0x'+'99'.repeat(32):BLOCK,timestamp:'0x6ace0000'};
      if(method==='eth_estimateGas') return '0xc350';
      if(method==='eth_getCode') return cfg.codes[params[0].toLowerCase()];
      if(method==='eth_sendTransaction') {
        this.sends++;this.last=params[0];localStorage.setItem('__mark_fixture_tx',JSON.stringify(this.last));
        if(this.mode==='reject') throw {code:4001};
        if(this.mode==='unknown') throw Error('Synthetic transport interruption');
        return HASH;
      }
      if(method==='eth_getTransactionReceipt') return this.noReceipt?null:{transactionHash:params[0],status:this.reverted?'0x0':'0x1',blockHash:BLOCK,blockNumber:'0x100'};
      if(method==='eth_getTransactionByHash') return {hash:params[0],from:this.last.from,to:this.cancelled?A:this.last.to,input:this.cancelled?'0x':this.last.data,nonce:this.last.nonce,chainId:'0x1',value:'0x0',blockHash:BLOCK,blockNumber:'0x100'};
      if(method==='wallet_switchEthereumChain') {this.chain='0x1';this.emit('chainChanged');return null;}
      const {CONTRACTS,METHODS,SELECTORS,tuple}=await module();
      if(method==='eth_call') {
        const key=Object.keys(SELECTORS).find(k=>SELECTORS[k]===params[0].data.slice(0,10));
        const binding={access:'Access',seed:'Seed',oracle:'Oracle',jobsBinding:'Jobs',mark:'Mark',marketplace:'Jobs',token:'Token'}[key];
        if(binding) return '0x'+tuple(['address'],[CONTRACTS[binding]]);
        if(key==='decimals') return '0x'+tuple(['uint8'],['18']);
        if(key==='reclaim') return '0x'+tuple(['uint256'],['100']);
        if(key==='approve') return '0x'+tuple(['bool'],[true]);
        if(['eligible','admitted','green'].includes(key)) return '0x'+tuple(['bool'],[false]);
        if(['nextId','balanceOf','allowance','stake','locked','lockedUntil'].includes(key)) return '0x'+tuple(METHODS[key].outputs,['0']);
        return '0x';
      }
      throw Error('Unexpected synthetic RPC '+method);
    }};
  window.ethereum=provider;
  window.addEventListener('eip6963:requestProvider',()=>window.dispatchEvent(new CustomEvent('eip6963:announceProvider',{
    detail:{provider,info:{name:'<img src=x onerror=alert(1)> Test wallet',icon:'data:image/svg+xml,<svg onload=alert(1)>'}}
  })));
})();
