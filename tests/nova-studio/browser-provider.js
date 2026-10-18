// SPDX-License-Identifier: Apache-2.0
// Test-only provider: actual transactions target the disposable local EVM.
const originalFetch=window.fetch.bind(window);
// Leave window.fetch untouched. Playwright intercepts storage network requests
// outside the page so this test exercises the browser's real native receiver.
window.__nova={actor:0,calls:[],sends:0,lastHash:null,loseNext:false,listeners:{},
  pendingReads:[],recentReads:[],nextReadId:0};
window.ethereum={
  on:(event,fn)=>(window.__nova.listeners[event]??=new Set()).add(fn),
  removeListener:(event,fn)=>window.__nova.listeners[event]?.delete(fn),
  request:async({method,params=[]})=>{
    window.__nova.calls.push(method);
    if(method==='eth_accounts'||method==='eth_requestAccounts')return [window.__novaActors[window.__nova.actor]];
    if(method==='wallet_switchEthereumChain')return null;
    // Failure-only fixture diagnostics retain method/timing, never parameters,
    // wallet identities, transaction bytes or response contents. They cannot
    // time out, retry, cancel or otherwise change the original request.
    const fixture=window.__nova,read={id:++fixture.nextReadId,method,startedAt:Date.now()};
    fixture.pendingReads.push(read);
    if(fixture.pendingReads.length>32)fixture.pendingReads.splice(0,fixture.pendingReads.length-32);
    let outcome='completed',errorCode=null;
    try {
      const response=await originalFetch('/rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({method,params})});
      const result=await response.json();if(result.error)throw Object.assign(Error(result.error.message),{code:result.error.code});
      if(method==='eth_sendTransaction'){
        fixture.sends++;fixture.lastHash=result.result;
        if(fixture.loseNext){fixture.loseNext=false;throw Error('Synthetic transport loss AFTER real local broadcast');}
      }
      return result.result;
    } catch(error) {
      outcome='failed';errorCode=Number.isSafeInteger(error?.code)?error.code:null;throw error;
    } finally {
      fixture.pendingReads=fixture.pendingReads.filter(entry=>entry.id!==read.id);
      fixture.recentReads.push({...read,finishedAt:Date.now(),outcome,errorCode});
      if(fixture.recentReads.length>32)fixture.recentReads.splice(0,fixture.recentReads.length-32);
    }
  }
};
window.__chooseNovaActor=i=>{window.__nova.actor=i;for(const fn of window.__nova.listeners.accountsChanged||[])fn([window.__novaActors[i]]);};
