// SPDX-License-Identifier: Apache-2.0
import {encryptCapsule,decryptCapsule} from './vendor/beyond_beta/graph/crypto_capsule.mjs';
const payload={scope:'synthetic-cryptographic-conformance',bytes:'No customer or evaluation data'};
const binding={candidate:'conformance',version:1};
const {envelope,key}=encryptCapsule(payload,binding);
const controls=[];
const reject=(name,fn)=>{try{fn();controls.push({name,passed:false});}catch(error){controls.push({name,passed:true,reason:error.message});}};
controls.push({name:'actual-aes-gcm-roundtrip',passed:JSON.stringify(decryptCapsule(envelope,key,binding))===JSON.stringify(payload)});
reject('changed-ciphertext-refused',()=>decryptCapsule({...envelope,ciphertext:Buffer.from('changed').toString('base64')},key,binding));
reject('changed-context-refused',()=>decryptCapsule(envelope,key,{...binding,version:2}));
reject('wrong-key-refused',()=>decryptCapsule(envelope,Buffer.alloc(32,42),binding));
process.stdout.write(JSON.stringify({scope:'REAL_LOCAL_ENCRYPTION_CONFORMANCE_ONLY',controls}));
