// SPDX-License-Identifier: Apache-2.0
import {randomBytes,createCipheriv,createDecipheriv,createHash} from 'node:crypto';
import {owned,contentDigest} from './encoding.mjs';

export function encryptCapsule(payload,binding){
  const clean=owned(payload),aad=Buffer.from(contentDigest(binding,'capsule-associated-binding'));
  const key=randomBytes(32),nonce=randomBytes(12),cipher=createCipheriv('aes-256-gcm',key,nonce);
  cipher.setAAD(aad);const ciphertext=Buffer.concat([cipher.update(JSON.stringify(clean),'utf8'),cipher.final()]);
  const envelope={schema:'beyond-beta.local-encrypted-capsule/v1',algorithm:'AES-256-GCM',
    nonce:nonce.toString('base64'),ciphertext:ciphertext.toString('base64'),tag:cipher.getAuthTag().toString('base64'),
    bindingDigest:aad.toString(),ciphertextSha256:createHash('sha256').update(ciphertext).digest('hex'),
    scope:'REAL_LOCAL_ENCRYPTION_ONLY_NO_ONCHAIN_OR_ZK_PROOF'};
  return {envelope,key};
}
export function decryptCapsule(envelope,key,binding){
  if(envelope?.schema!=='beyond-beta.local-encrypted-capsule/v1'||envelope.algorithm!=='AES-256-GCM')throw Error('UNSUPPORTED_CAPSULE');
  const expected=contentDigest(binding,'capsule-associated-binding');if(envelope.bindingDigest!==expected)throw Error('CAPSULE_CONTEXT_MISMATCH');
  const ciphertext=Buffer.from(envelope.ciphertext,'base64');
  if(createHash('sha256').update(ciphertext).digest('hex')!==envelope.ciphertextSha256)throw Error('CAPSULE_BYTES_CHANGED');
  const decipher=createDecipheriv('aes-256-gcm',key,Buffer.from(envelope.nonce,'base64'));
  decipher.setAAD(Buffer.from(expected));decipher.setAuthTag(Buffer.from(envelope.tag,'base64'));
  return JSON.parse(Buffer.concat([decipher.update(ciphertext),decipher.final()]).toString('utf8'));
}
