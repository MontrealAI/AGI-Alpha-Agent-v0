// SPDX-License-Identifier: Apache-2.0
// Test-only provider: actual transactions target the disposable local EVM.
const originalFetch=window.fetch.bind(window);
window.fetch=(url,options)=>{
  const target=String(url);
  if(target==='https://uploads.pinata.cloud/v3/files')return originalFetch('/upload',options);
  if(target.startsWith('https://gateway.pinata.cloud/ipfs/')||target.startsWith('https://ipfs.io/ipfs/'))
    return originalFetch('/ipfs/'+target.split('/').at(-1),options);
  return originalFetch(url,options);
};
window.__nova={actor:0,calls:[],sends:0,lastHash:null,loseNext:false,listeners:{}};
window.ethereum={
  on:(event,fn)=>(window.__nova.listeners[event]??=new Set()).add(fn),
  removeListener:(event,fn)=>window.__nova.listeners[event]?.delete(fn),
  request:async({method,params=[]})=>{
    window.__nova.calls.push(method);
    if(method==='eth_accounts'||method==='eth_requestAccounts')return [window.__novaActors[window.__nova.actor]];
    if(method==='wallet_switchEthereumChain')return null;
    const response=await originalFetch('/rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({method,params})});
    const result=await response.json();if(result.error)throw Object.assign(Error(result.error.message),{code:result.error.code});
    if(method==='eth_sendTransaction'){
      window.__nova.sends++;window.__nova.lastHash=result.result;
      if(window.__nova.loseNext){window.__nova.loseNext=false;throw Error('Synthetic transport loss AFTER real local broadcast');}
    }
    return result.result;
  }
};
window.__chooseNovaActor=i=>{window.__nova.actor=i;for(const fn of window.__nova.listeners.accountsChanged||[])fn([window.__novaActors[i]]);};
