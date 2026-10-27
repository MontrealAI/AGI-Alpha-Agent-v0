// SPDX-License-Identifier: Apache-2.0
import {digest} from '../upstream/graph/commitments.mjs';

// Scientific reports may contain finite decimals. Every JSON type is tagged
// before the unchanged integer-only upstream canonical commitment is used.
export function owned(value){
  let count=0;const active=new Set();
  const copy=(x,depth)=>{
    if(++count>100000||depth>32)throw Error('FRAME_LIMIT');
    if(x===null||typeof x==='boolean')return x;
    if(typeof x==='number'){if(!Number.isFinite(x)||Object.is(x,-0))throw Error('FINITE_NUMBER_REQUIRED');return x;}
    if(typeof x==='string'){if(x!==x.normalize('NFC'))throw Error('NONCANONICAL_STRING');return x;}
    if(typeof x!=='object'||active.has(x))throw Error('JSON_DATA_REQUIRED');
    const array=Array.isArray(x),proto=Object.getPrototypeOf(x),descriptors=Object.getOwnPropertyDescriptors(x);
    if(proto!==(array?Array.prototype:Object.prototype)&&proto!==null)throw Error('PLAIN_DATA_REQUIRED');
    const names=Reflect.ownKeys(descriptors);
    if(names.some(k=>typeof k!=='string'||!Object.hasOwn(descriptors[k],'value')))throw Error('DATA_PROPERTIES_REQUIRED');
    active.add(x);let result;
    if(array){if(names.length!==x.length+1||Array.from({length:x.length},(_,i)=>String(i)).some(k=>!Object.hasOwn(descriptors,k)))throw Error('DENSE_ARRAY_REQUIRED');result=x.map(y=>copy(y,depth+1));}
    else result=Object.fromEntries(names.map(k=>[k,copy(descriptors[k].value,depth+1)]));
    active.delete(x);return result;
  };return copy(value,0);
}
export function contentDigest(value,domain='beyond-beta-content'){
  const tag=x=>x===null?['null']:Array.isArray(x)?['array',x.map(tag)]:typeof x==='object'?
    ['object',Object.keys(x).sort().map(k=>[k,tag(x[k])])]:[typeof x,typeof x==='number'?String(x):x];
  return digest(tag(owned(value)),domain);
}
export const same=(a,b)=>contentDigest(a)===contentDigest(b);
export const clone=owned;
export function requireInteger(x,label){if(!Number.isSafeInteger(x)||x<0)throw Error(`INVALID_${label}`);return x;}
export function freezeDeep(x){if(x&&typeof x==='object'){for(const y of Object.values(x))freezeDeep(y);Object.freeze(x);}return x;}
