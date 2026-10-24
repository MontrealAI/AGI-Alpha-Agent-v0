// SPDX-License-Identifier: Apache-2.0
import {readFileSync, writeFileSync} from 'node:fs';
import {createCipheriv, createDecipheriv, randomBytes, createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';

const sha = x => createHash('sha256').update(x).digest('hex');
export function disclosureControls(payload, context) {
  const raw = Buffer.from(JSON.stringify(payload));
  const aad = Buffer.from(JSON.stringify(context));
  const key = randomBytes(32), nonce = randomBytes(12);
  const t = performance.now(), cpu = process.cpuUsage();
  const enc = createCipheriv('aes-256-gcm', key, nonce);
  enc.setAAD(aad);
  const ciphertext = Buffer.concat([enc.update(raw), enc.final()]);
  const tag = enc.getAuthTag();
  const decrypt = (k, c, a) => {
    const dec = createDecipheriv('aes-256-gcm', k, nonce);
    dec.setAAD(a); dec.setAuthTag(tag);
    return Buffer.concat([dec.update(c), dec.final()]);
  };
  const owner = decrypt(key, ciphertext, aad), competitor = decrypt(key, ciphertext, aad);
  const fails = f => { try { f(); return false; } catch { return true; } };
  const altered = Buffer.from(ciphertext); altered[0] ^= 1;
  const wrongKey = Buffer.from(key); wrongKey[0] ^= 1;
  const checks = {
    authorizedOwnerRoundtrip: owner.equals(raw),
    authorizedCompetitorRoundtrip: competitor.equals(raw),
    equalAuthorizedPlaintext: owner.equals(competitor),
    wrongKeyRejected: fails(() => decrypt(wrongKey, ciphertext, aad)),
    changedCiphertextRejected: fails(() => decrypt(key, altered, aad)),
    changedMissionRejected: fails(() => decrypt(key, ciphertext, Buffer.from(JSON.stringify({...context,missionId:'different'}))))
  };
  const used = process.cpuUsage(cpu);
  let recovered = null, candidates = 0;
  const commitment = sha(Buffer.from('calibration-class:7'));
  for(let i=0;i<16;i++){candidates++;if(sha(Buffer.from('calibration-class:'+i))===commitment){recovered=i;break;}}
  key.fill(0);wrongKey.fill(0);
  return {
    schema:'nova-disclosure-controls/v1',simulation:true,context,
    threatModel:'Synthetic payload; common voluntary recipient permissions. Outsider has ciphertext, nonce, tag, AAD, length and public source. No claim that published reproducible workload is secret. No malicious-authorized-recipient protection.',
    primitive:'Node/OpenSSL AES-256-GCM; fresh random 256-bit ephemeral key and 96-bit nonce; key never persisted',
    checks, passed:Object.values(checks).every(Boolean),
    plaintextSha256:sha(raw), plaintextBytes:raw.length,
    ciphertextSha256:sha(ciphertext),ciphertextBytes:ciphertext.length,nonceHex:nonce.toString('hex'),tagHex:tag.toString('hex'),
    dictionaryAttack:{primitive:'SHA-256, unsalted public low-entropy label',candidateSpace:16,candidatesTested:candidates,recovered,success:recovered===7},
    measured:{wallMilliseconds:performance.now()-t,cpuMicroseconds:used.user+used.system},
    limits:['Hash commitments do not encrypt contents.','Disclosure control grants no productive superiority.','Fresh valid authority is required in each mission.','Authorized plaintext equality is not a confidentiality proof.']
  };
}
if(process.argv[1]?.endsWith('disclosure_controls.mjs')) {
  const payload=JSON.parse(readFileSync(process.argv[2],'utf8'));
  const result=disclosureControls(payload,{institutionId:'nova-writer10-local',missionId:'synthetic-disclosure-test',environment:'local-simulation',mode:'fixture'});
  if(!result.passed)throw Error('Disclosure controls failed');
  const text=JSON.stringify(result,null,2)+'\n';
  if(process.argv[3])writeFileSync(process.argv[3],text);else process.stdout.write(text);
}
