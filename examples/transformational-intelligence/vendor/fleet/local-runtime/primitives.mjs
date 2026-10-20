// Transport-safe primitives: no registry, filesystem state or module-relative reads.
export {parseStrict,canonical} from '../fleet/successor/vendor/manager/site/assets/successor/safe.mjs';
export const MAX_BYTES=4_000_000;
// A bounded capsule can be JSON-escaped once inside the transport envelope.
export const CAPSULE_ENVELOPE_BYTES=2*MAX_BYTES+1024;
export const need=(ok,code)=>{if(!ok)throw Object.assign(new Error(code),{code});};
export function decodeUTF8(data){try{return new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(data);}catch{need(false,'UTF8_REQUIRED');}}
export function keys(value,allowed,required=allowed){
  need(value&&typeof value==='object'&&!Array.isArray(value),'OBJECT_REQUIRED');
  need(Object.keys(value).every(k=>allowed.includes(k))&&required.every(k=>Object.hasOwn(value,k)),'FIELDS_INVALID');
}
export function uuid(value){need(typeof value==='string'&&/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(value),'IDENTITY_INVALID');return value;}
