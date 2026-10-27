// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [repo, input, output] = process.argv.slice(2);
if (!repo || !input || !output) throw Error('Expected repository, payload and new output directory.');
const source = path.join(repo, 'docs/assets/ascension/crypto.mjs');
const { sealSeed, openSeed, hashObject, canonicalJSON } = await import(pathToFileURL(source));
const payload = JSON.parse(fs.readFileSync(input, 'utf8'));
const passphrase = 'PUBLIC-RESEARCH-FIXTURE-DO-NOT-USE-AS-A-SECRET';
const capsule = await sealSeed(payload, passphrase);
const recovered = await openSeed(capsule, passphrase);
if (canonicalJSON(payload) !== canonicalJSON(recovered)) throw Error('Nova-Seed roundtrip changed payload.');
const refusals = {};
for (const [name, value, key] of [
  ['wrong_passphrase', capsule, 'PUBLIC-WRONG-PASSPHRASE'],
  ['altered_commitment', {...capsule, commitment: '0'.repeat(64)}, passphrase],
]) {
  try { await openSeed(value, key); throw Error('UNEXPECTED_ACCEPTANCE'); }
  catch (error) { if (error.message === 'UNEXPECTED_ACCEPTANCE') throw error; refusals[name] = error.message; }
}
const report = {
  schema: 'agialpha.study.novaseed-roundtrip.v1',
  evidence_class: 'executed_local_existing_cryptographic_component',
  payload_sha256: await hashObject(payload),
  recovered_payload_sha256: await hashObject(recovered),
  roundtrip_equal: true, refusals,
  source: 'docs/assets/ascension/crypto.mjs', node: process.version,
  public_fixture_passphrase: passphrase,
  content_is_public_research: true,
  encryption_is_not_confidential_with_this_public_fixture_passphrase: true,
  nft_minted: false, token_transactions: 0, truth_or_novelty_certified: false,
  randomness: 'Native cryptographic salt, IV and blinding are fresh on each run; verify semantic roundtrip, not ciphertext equality.'
};
for (const [name, value] of Object.entries({'novaseed-sealed.json': capsule, 'novaseed-recovered.json': recovered, 'novaseed-report.json': report})) {
  fs.writeFileSync(path.join(output, name), JSON.stringify(value, null, 2) + '\n', {flag: 'wx'});
}
console.log(JSON.stringify({roundtrip_equal: true, refusals: Object.keys(refusals), payload_sha256: report.payload_sha256}));
