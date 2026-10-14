// SPDX-License-Identifier: Apache-2.0
// A deliberately narrow ABI codec. No keys, signing code, dependency CDN or arbitrary calls.
const SPEC = ['string', 'string', 'uint96', 'uint32', 'uint16'];
export const CHAIN = '0x1';
export const TOKEN = '0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA';
export const CONTRACTS = Object.freeze({
  Access: '0x36f8C079fEEBC81c5AF30D71be5017037246a32e',
  Seed: '0xFA4737Ba7cF111EBb0840aA300BC61D84d303449',
  Oracle: '0x06cb4D684628846B048d88CCf8C03c4Cfb74f149',
  Jobs: '0x86f84E173A7a1a4588f4e757552F20f7C58e61E8',
  Mark: '0xa28dA507f7F9AFF8910f1F7cB5d5b8238F5Db625', Token: TOKEN
});
export function uint(value, bits = 256) {
  if (typeof value !== 'string' && typeof value !== 'bigint') throw Error('Use an integer string.');
  if (!/^(0|[1-9][0-9]*)$/.test(String(value))) throw Error('A nonnegative whole number is required.');
  const n = BigInt(value);
  if (n >= (1n << BigInt(bits))) throw Error(`Number exceeds uint${bits}.`);
  return n;
}
export function units(text) {
  if (typeof text !== 'string' || !/^(0|[1-9][0-9]*)(\.[0-9]{1,18})?$/.test(text))
    throw Error('Use a token amount with at most 18 decimal places, without commas or exponents.');
  const [whole, fraction = ''] = text.split('.');
  return uint(String(BigInt(whole) * 10n ** 18n + BigInt(fraction.padEnd(18, '0'))));
}
export function tokens(value) {
  const n = uint(String(value));
  const frac = (n % 10n ** 18n).toString().padStart(18, '0').replace(/0+$/, '');
  return (n / 10n ** 18n).toString() + (frac ? `.${frac}` : '');
}
export function address(value) {
  if (typeof value !== 'string' || !/^0x[0-9a-fA-F]{40}$/.test(value)) throw Error('A full 0x wallet address is required.');
  return value.toLowerCase();
}
export function bytes32(value) {
  if (typeof value !== 'string' || !/^0x[0-9a-fA-F]{64}$/.test(value)) throw Error('A 32-byte 0x hash is required.');
  return value.slice(2).toLowerCase();
}
const word = n => uint(String(n)).toString(16).padStart(64, '0');
const dynamic = t => Array.isArray(t) ? t.some(dynamic) : t === 'string' || t === 'bytes32[]';
const size = t => dynamic(t) ? 32 : Array.isArray(t) ? t.reduce((n, x) => n + size(x), 0) : t === 'address[3]' ? 96 : 32;
export function tuple(types, values) {
  if (!Array.isArray(values) || values.length !== types.length) throw Error('Incorrect argument count.');
  let offset = types.reduce((n, t) => n + size(t), 0), tail = '', head = '';
  types.forEach((t, i) => {
    const encoded = encodeValue(t, values[i]);
    if (dynamic(t)) { head += word(offset); tail += encoded; offset += encoded.length / 2; }
    else head += encoded;
  });
  return head + tail;
}
function encodeValue(type, value) {
  if (Array.isArray(type)) return tuple(type, value);
  if (/^uint(8|16|32|64|96|256)$/.test(type)) return word(uint(value, Number(type.slice(4))));
  if (type === 'address') return address(value).slice(2).padStart(64, '0');
  if (type === 'bytes32') return bytes32(value);
  if (type === 'bool') { if (typeof value !== 'boolean') throw Error('A boolean is required.'); return word(value ? 1 : 0); }
  if (type === 'string') {
    if (typeof value !== 'string' || (value.isWellFormed && !value.isWellFormed())) throw Error('Invalid UTF-8 text.');
    const bytes = new TextEncoder().encode(value);
    if (bytes.length > 512) throw Error('Text exceeds 512 UTF-8 bytes.');
    const hex = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
    return word(bytes.length) + hex.padEnd(Math.ceil(bytes.length / 32) * 64, '0');
  }
  if (type === 'bytes32[]' || type === 'address[3]') {
    if (!Array.isArray(value) || value.length > 128 || (type === 'address[3]' && value.length !== 3))
      throw Error('Invalid array length.');
    return (type === 'bytes32[]' ? word(value.length) : '') + value.map(v => encodeValue(type === 'bytes32[]' ? 'bytes32' : 'address', v)).join('');
  }
  throw Error('Unsupported ABI type.');
}
export function decode(types, data) {
  if (typeof data !== 'string' || !/^0x([0-9a-fA-F]{64})*$/.test(data) || data.length > 200002)
    throw Error('Malformed contract response.');
  const body = data.slice(2);
  const readWord = offset => {
    if (!Number.isSafeInteger(offset) || offset < 0 || offset % 32 || offset * 2 + 64 > body.length)
      throw Error('Malformed ABI offset or length.');
    return body.slice(offset * 2, offset * 2 + 64);
  };
  const values = types.map((type, i) => {
    const hex = readWord(i * 32), n = BigInt(`0x${hex}`);
    if (type === 'string') {
      if (n > BigInt(body.length / 2)) throw Error('Malformed ABI string offset.');
      const offset = Number(n), length = BigInt(`0x${readWord(offset)}`);
      if (length > 512n || offset + 32 + Number(length) > body.length / 2) throw Error('Malformed or oversized ABI string.');
      const bytes = Uint8Array.from(body.slice((offset + 32) * 2, (offset + 32 + Number(length)) * 2).match(/../g) || [], h => parseInt(h, 16));
      return new TextDecoder('utf-8', {fatal:true}).decode(bytes);
    }
    if (type === 'address') { if (n >= 1n << 160n) throw Error('Malformed address.'); return address(`0x${hex.slice(24)}`); }
    if (type === 'bytes32') return `0x${hex.toLowerCase()}`;
    if (type === 'bool') { if (n > 1n) throw Error('Malformed boolean.'); return n === 1n; }
    if (!/^uint(8|16|32|64|96|256)$/.test(type)) throw Error('Unsupported ABI response type.');
    return uint(String(n), Number(type.slice(4)));
  });
  // Reject noncanonical offsets, overlapping tails, padding and trailing bytes.
  if (tuple(types, values) !== body.toLowerCase()) throw Error('Noncanonical contract response.');
  return values;
}
function canonical(t) { return Array.isArray(t) ? `(${t.map(canonical).join(',')})` : t; }
const method = (name, inputs, outputs = []) => ({name, inputs, outputs, signature: `${name}(${inputs.map(canonical).join(',')})`});
export const METHODS = {
  owner: method('owner', [], ['address']), pendingOwner: method('pendingOwner', [], ['address']),
  access: method('access', [], ['address']), seed: method('seed', [], ['address']), oracle: method('oracle', [], ['address']),
  jobsBinding: method('jobs', [], ['address']), mark: method('mark', [], ['address']), marketplace: method('marketplace', [], ['address']),
  token: method('token', [], ['address']), decimals: method('decimals', [], ['uint8']),
  nextId: method('nextId', [], ['uint256']), ownerOf: method('ownerOf', ['uint256'], ['address']),
  creatorOf: method('creatorOf', ['uint256'], ['address']), tokenURI: method('tokenURI', ['uint256'], ['string']),
  genomes: method('genomes', ['uint256'], ['bytes32','bytes32','bytes32','uint256','uint32','address']),
  rounds: method('rounds', ['uint256'], ['uint64','uint64','uint16','uint16','address']),
  quorum: method('quorum', [], ['uint16']), maximumRiskBps: method('maximumRiskBps', [], ['uint16']),
  voted: method('voted', ['uint256','uint64','address'], ['bool']),
  admission: method('admission', ['address'], ['bytes32','uint64']), roots: method('roots', ['uint8'], ['bytes32']),
  child: method('child', ['bytes32','string'], ['bytes32']), ens: method('ens', [], ['address']), wrapper: method('wrapper', [], ['address']),
  ensOwner: method('owner', ['bytes32'], ['address']), wrapperData: method('getData', ['uint256'], ['address','uint32','uint64']),
  reviewWindow: method('REVIEW_WINDOW', [], ['uint32']), validatorBps: method('VALIDATOR_BPS', [], ['uint16']),
  posted: method('posted', ['uint256','uint32'], ['bool']), jobSeed: method('jobSeed', ['uint256'], ['uint256']),
  collected: method('collected', ['uint256'], ['bool']), committees: method('committees', ['uint256','uint256'], ['address']),
  votes: method('votes', ['uint256','address'], ['uint8']), terminal: method('terminal', ['uint256'], ['bool']),
  hashSpec: method('hashSpec', ['uint32',SPEC], ['bytes32']),
  safeTransferFrom: method('safeTransferFrom', ['address','address','uint256']),
  green: method('green', ['uint256'], ['bool']), admitted: method('admitted', ['address'], ['bool']),
  eligible: method('eligible', ['address', 'uint8'], ['bool']), names: method('names', ['address', 'uint8'], ['bytes32']),
  owns: method('owns', ['address', 'bytes32'], ['bool']), plan: method('plan', ['uint256'], ['bytes32', 'uint32']),
  balanceOf: method('balanceOf', ['address'], ['uint256']), allowance: method('allowance', ['address', 'address'], ['uint256']),
  minimumStake: method('minimumStake', [], ['uint256']), stake: method('stake', ['address'], ['uint256']),
  locked: method('locked', ['address'], ['uint256']), lockedUntil: method('lockedUntil', ['address'], ['uint64']),
  isValidator: method('isValidator', ['address'], ['bool']), jobCapacity: method('jobCapacity', ['address'], ['uint32']),
  activeJobs: method('activeJobs', ['address'], ['uint32']), jobAvailability: method('jobAvailability', ['address', 'address'], ['uint64']),
  campaigns: method('campaigns', ['uint256'], ['address','uint96','uint96','uint96','uint32','uint32','uint32','uint32','uint32','uint64','uint64','uint256','uint8','bytes32']),
  lots: method('lots', ['uint256', 'address'], ['uint256']),
  quote: method('quote', ['uint32','uint32','uint96','uint96'], ['uint256']),
  job: method('jobs', ['uint256'], ['address','address','address','uint96','uint96','uint96','uint64','uint64','uint64','uint64','uint32','uint16','uint8','uint8','uint8','bytes32','bytes32','uint256','bool']),
  open: method('open', ['uint256','uint96','uint96','uint32','uint96','uint64','uint32']),
  buy: method('buy', ['uint256','uint32','uint256']), sell: method('sell', ['uint256','uint32','uint256']),
  transferLots: method('transferLots', ['uint256','address','uint32']), bloom: method('bloom', ['uint256']),
  route: method('route', ['uint256','uint32',SPEC,'bytes32[]','uint32','address[3]'], ['uint256']),
  collect: method('collect', ['uint256']), close: method('close', ['uint256']), reclaim: method('reclaim', ['uint256'], ['uint256']),
  approve: method('approve', ['address','uint256'], ['bool']), register: method('register', ['uint8','string']),
  seal: method('seal', ['bytes32','bytes32','uint32','string','uint256','bytes32'], ['uint256']),
  openReview: method('openReview', ['uint256']), attest: method('attest', ['uint256','uint16','bool','bytes32']),
  deposit: method('deposit', ['uint256']), withdraw: method('withdraw', ['uint256']),
  setJobAvailability: method('setJobAvailability', ['address','uint64','uint32']),
  bid: method('bid', ['uint256','uint96','uint32']), award: method('award', ['uint256']),
  submit: method('submit', ['uint256','bytes32','string']), validate: method('validate', ['uint256','bytes32','bool','bytes32']),
  timeout: method('timeout', ['uint256']), claimRefund: method('claimRefund', ['uint256'], ['uint256'])
};
// Generated from these exact signatures; CI cross-checks every selector and codec against ethers.
export const SELECTORS = {
  "owner": "0x8da5cb5b",
  "pendingOwner": "0xe30c3978",
  "access": "0x71907f17",
  "seed": "0x7d94792a",
  "oracle": "0x7dc0d1d0",
  "jobsBinding": "0x7c8fce23",
  "mark": "0x8c0d0c29",
  "marketplace": "0xabc8c7af",
  "token": "0xfc0c546a",
  "decimals": "0x313ce567",
  "nextId": "0x61b8ce8c",
  "ownerOf": "0x6352211e",
  "creatorOf": "0x589a1743",
  "tokenURI": "0xc87b56dd",
  "genomes": "0xc7bebdfd",
  "rounds": "0x8c65c81f",
  "quorum": "0x1703a018",
  "maximumRiskBps": "0xcf2dcc65",
  "voted": "0x1b06d507",
  "admission": "0x51e719cf",
  "roots": "0x17baa7e9",
  "child": "0x6dfc1431",
  "ens": "0x3f15457f",
  "wrapper": "0xac210cc7",
  "ensOwner": "0x02571be3",
  "wrapperData": "0x0178fe3f",
  "reviewWindow": "0x4584712b",
  "validatorBps": "0x49da1a63",
  "posted": "0x52f26410",
  "jobSeed": "0x78efae42",
  "collected": "0x77e840ed",
  "committees": "0x5d7ecce9",
  "votes": "0xd23254b4",
  "terminal": "0x1be1894c",
  "hashSpec": "0x05d0f719",
  "safeTransferFrom": "0x42842e0e",
  "green": "0xb0fa32bf",
  "admitted": "0x0020d939",
  "eligible": "0xe1227718",
  "names": "0x22e305e6",
  "owns": "0x34d85c02",
  "plan": "0xab79205c",
  "balanceOf": "0x70a08231",
  "allowance": "0xdd62ed3e",
  "minimumStake": "0xec5ffac2",
  "stake": "0x26476204",
  "locked": "0xcbf9fe5f",
  "lockedUntil": "0x9bc289f1",
  "isValidator": "0xfacd743b",
  "jobCapacity": "0xa927b4c7",
  "activeJobs": "0xfcf4dd69",
  "jobAvailability": "0x7280f30d",
  "campaigns": "0x141961bc",
  "lots": "0x53e682c2",
  "quote": "0xbf9abbc8",
  "job": "0x180aedf3",
  "open": "0xa782a583",
  "buy": "0x022bf3bd",
  "sell": "0xb3e12e32",
  "transferLots": "0x4adb3553",
  "bloom": "0x44d74492",
  "route": "0x08b07d5f",
  "collect": "0xce3f865f",
  "close": "0x0aebeb4e",
  "reclaim": "0x2dabbeed",
  "approve": "0x095ea7b3",
  "register": "0xd3eb9541",
  "seal": "0x91abd3d5",
  "openReview": "0x92f25df8",
  "attest": "0x34caf5e3",
  "deposit": "0xb6b55f25",
  "withdraw": "0x2e1a7d4d",
  "setJobAvailability": "0x96979b2f",
  "bid": "0x0b50983e",
  "award": "0x0184e952",
  "submit": "0x28db8270",
  "validate": "0x19d5d8ae",
  "timeout": "0x08148f7a",
  "claimRefund": "0x5b7baf64"
};
export function callData(key, values = []) {
  const m = METHODS[key];
  if (!m || !Object.hasOwn(METHODS, key)) throw Error('Unknown method.');
  return SELECTORS[key] + tuple(m.inputs, values);
}
const field = (key, label, kind = 'integer') => ({key, label, kind});
const id = field('id', 'Nova-Seed ID / Identifiant Nova-Seed');
const job = field('job', 'Job ID / Identifiant du travail');
const amount = field('amount', '$AGIALPHA amount / Montant', 'tokens');
const proof = field('evidence', 'Evidence hash / Empreinte des preuves', 'hash');
const action = (contract, methodName, label, risk, fields, note) => ({contract, method: methodName, label, risk, fields, note});
export const ACTIONS = {
  buy: action('Mark','buy','Buy funding lots / Acheter des lots','new',[id,field('count','Lots'),field('maxCost','Maximum $AGIALPHA cost / Coût maximal','tokens')], 'Approve only the bounded spend separately. Bloom can end redemption as soon as the target is reached.'),
  sell: action('Mark','sell','Redeem funding lots / Racheter des lots','recovery',[id,field('count','Lots'),field('minReturn','Minimum $AGIALPHA return / Retour minimal','tokens')], 'Funding phase only; admission or risk expiry does not by itself prevent redemption. The curve price may differ from your purchase price. A competing bloom or close can make this revert.'),
  reclaim: action('Mark','reclaim','Claim remaining capital / Réclamer le solde','recovery',[id], 'Closed campaign only. Returns your proportion of the remaining reserve, not spent funding or a guaranteed original deposit.'),
  collect: action('Mark','collect','Collect job refund into MARK / Rapatrier le remboursement','recovery',[job], 'Anyone may collect a terminal MARK job. The refund goes into the campaign reserve, not to the caller.'),
  close: action('Mark','close','Close eligible campaign / Fermer une campagne','recovery',[id], 'Anyone may close only when contract conditions permit. Closing ends curve redemption; remaining claims become proportional.'),
  open: action('Mark','open','Open campaign / Ouvrir une campagne','new',[id,field('base','First-lot price / Prix initial','tokens'),field('slope','Price rise per lot / Hausse par lot','tokens'),field('maxLots','Maximum lots / Lots maximaux'),field('target','Funding target / Objectif','tokens'),field('fundingEnd','Funding end: Unix seconds / Fin : secondes Unix'),field('duration','Execution period: seconds / Exécution : secondes')], 'Requires the current green seed owner. Funding lasts at most 30 days; the execution window must include auction, delivery and review.'),
  bloom: action('Mark','bloom','Bloom: commit funding / Bloom : engager les fonds','new',[id], 'IRREVERSIBLE PHASE CHANGE. Ends trading and curve redemption immediately. Funds can only pay jobs in the committed plan. No arbitrary treasury withdrawal exists.'),
  transferLots: action('Mark','transferLots','Transfer funding lots / Transférer des lots','new',[id,field('to','Recipient / Destinataire','address'),field('count','Lots')], 'Both participants must be admitted. Funding must still be open and the seed green. Lots are not company shares or a revenue entitlement.'),
  route: action('Mark','route','Route committed job / Publier le travail engagé','new',[id,field('index','Plan job index / Index du travail'),field('spec','Exact FusionPlan specification (JSON; bounty in base units)','spec'),field('proof','Merkle proof: JSON array of 0x hashes','proof'),field('auction','Auction duration: seconds / Enchère : secondes'),field('validators','Three reviewer addresses: JSON array / Trois adresses','committee')], 'The contract checks the indexed plan proof, treasury budget, execution horizon and three available reviewers. This uses AscensionJobMarket, not AGIJobsv0 or AGIJobManager.'),
  approve: action('Token','approve','Set bounded allowance / Autoriser un montant limité','new',[field('spender','Protocol spender / Contrat autorisé','spender'),amount], 'Approval is a separate transaction, not a purchase. Zero revokes the remaining allowance and is allowed during recovery. Never transfer tokens directly to MARK.'),
  register: action('Access','register','Register existing ENS role / Enregistrer un rôle ENS','new',[field('role','Role: 0 business, 1 agent, 2 validator','role'),field('label','Owned subname label only / Libellé du sous-nom','label')], 'Does not create an ENS name or grant admission. Business: *.alpha.agi.eth; agent: *.alpha.agent.agi.eth; validator: *.alpha.club.agi.eth.'),
  seal: action('Seed','seal','Seal Nova-Seed / Sceller un Nova-Seed','new',[field('capsule','Encrypted capsule hash / Empreinte capsule','hash'),field('root','FusionPlan root / Racine FusionPlan','hash'),field('jobs','Committed job count / Nombre de travaux'),field('uri','Metadata URI / URI des métadonnées','uri'),field('parent','Parent seed ID (0 for none) / Parent (0 : aucun)'),proof], 'Keep the encrypted capsule and decryption key separately. The NFT binds hashes; it does not store the work, confer approval or create an autonomous business.'),
  transferSeed: action('Seed','safeTransferFrom','Transfer this seed / Transférer ce seed','new',[field('from','Current owner / Propriétaire actuel','address'),field('to','Recipient / Destinataire','address'),id], 'NFT ownership changes; the capsule passphrase and existing campaign authority do not transfer. Existing approval may become unusable. Contract recipients must support ERC-721.'),
  openReview: action('Oracle','openReview','Open seed review / Ouvrir une revue','new',[id], 'Requires the eligible seed owner; approval is time-limited and does not transfer automatically to a new owner.'),
  attest: action('Oracle','attest','Attest seed risk / Attester le risque','new',[id,field('risk','Risk: basis points / Risque : points de base'),field('approved','Policy approved / Politique approuvée','boolean'),proof], 'Only an eligible staked validator distinct from owner and creator may attest. A hash is not a substitute for actual review.'),
  validatorDeposit: action('Oracle','deposit','Deposit validator stake / Déposer la mise validateur','new',[amount], 'Requires admission and an owned registered validator ENS identity; inspect locking obligations before depositing.'),
  validatorWithdraw: action('Oracle','withdraw','Withdraw unlocked validator stake / Retirer la mise libérée','recovery',[amount], 'The on-chain lockedUntil deadline must have passed. Admission revocation does not itself forbid withdrawal.'),
  availability: action('Oracle','setJobAvailability','Set review availability / Définir la disponibilité','new',[field('business','Business wallet / Portefeuille entreprise','address'),field('until','Available until: Unix seconds (0 revokes) / Fin (0 : retrait)'),field('capacity','Concurrent jobs (0–128) / Capacité')], 'Capacity and expiry are commitments. Revoking future availability does not cancel already-reserved work.'),
  agentDeposit: action('Jobs','deposit','Deposit agent stake / Déposer la mise agent','new',[amount], 'Requires admission and an owned registered agent ENS identity. Each bid reserves its own bond.'),
  agentWithdraw: action('Jobs','withdraw','Withdraw free agent stake / Retirer la mise libre','recovery',[amount], 'Only unreserved stake may be withdrawn. Existing job collateral is not withdrawable.'),
  bid: action('Jobs','bid','Bid on job / Soumissionner','new',[job,field('price','Gross price / Prix brut','tokens'),field('duration','Promised delivery: seconds / Délai promis')], 'Includes the review allocation and payout burn. A bid reserves collateral; missing delivery can slash it.'),
  award: action('Jobs','award','Award ended auction / Attribuer une enchère terminée','obligation',[job], 'Anyone may process an ended auction. The contract selects an eligible bidder or refunds an auction with no admissible winner.'),
  submit: action('Jobs','submit','Deliver result / Livrer un résultat','obligation',[job,field('result','Exact result-file hash / Empreinte du fichier','hash'),field('uri','Result URI / URI du résultat','uri')], 'Only the assigned eligible worker may deliver before its deadline. The work is performed off-chain; keep the exact reviewed bytes.'),
  validate: action('Jobs','validate','Review delivered result / Évaluer le résultat','obligation',[job,field('result','Delivered result hash / Empreinte livrée','hash'),field('approved','Approve result / Approuver','boolean'),proof], 'Real validator vote: may pay or slash. The archived deployment lacks newer rejection-quorum safeguards. Review exact evidence and the deployment difference before voting.'),
  timeout: action('Jobs','timeout','Process expired job / Traiter un travail expiré','obligation',[job], 'Late undelivered work can slash the worker. Missing review quorum refunds escrow without slashing. This is not a generic cancel button.'),
  jobRefund: action('Jobs','claimRefund','Claim direct-job refund / Réclamer un remboursement direct','recovery',[job], 'Only the recorded client can claim. For a MARK-originated job, use Collect: MARK is the client.'),
};
export function parseFields(actionId, values, contracts = CONTRACTS) {
  const a = ACTIONS[actionId];
  if (!Object.hasOwn(ACTIONS, actionId) || !a || values.length !== a.fields.length) throw Error('Unknown action or missing fields.');
  return a.fields.map((f, i) => {
    const v = values[i];
    if (f.kind === 'tokens') return units(v).toString();
    if (f.kind === 'address') return address(v);
    if (f.kind === 'spender') { if (!['Mark','Jobs','Oracle'].includes(v)) throw Error('Choose a protocol spender.'); return address(contracts[v]); }
    if (f.kind === 'hash') { bytes32(v); return v; }
    if (f.kind === 'boolean') { if (!['true','false'].includes(v)) throw Error('Choose true or false.'); return v === 'true'; }
    if (f.kind === 'role') { if (!['0','1','2'].includes(v)) throw Error('Invalid role.'); return v; }
    if (f.kind === 'label') { if (!/^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/.test(v)) throw Error('Use one lowercase ENS label, not a full name.'); return v; }
    if (f.kind === 'uri') { if (!/^(https:\/\/|ipfs:\/\/|ar:\/\/)/.test(v)) throw Error('Use an https, ipfs or ar URI.'); return v; }
    if (['spec','proof','committee'].includes(f.kind)) {
      if (v.length > 16000) throw Error('JSON input too large.');
      const data = JSON.parse(v);
      if (f.kind === 'spec') {
        const keys = ['goal','successMetric','bounty','duration','priceWeight'];
        if (!data || Array.isArray(data) || Object.keys(data).sort().join() !== [...keys].sort().join()) throw Error('Use the exact five-field FusionPlan specification.');
        return keys.map((k, n) => n < 2 ? data[k] : typeof data[k] === 'number' && Number.isSafeInteger(data[k]) ? String(data[k]) : data[k]);
      }
      return data;
    }
    return uint(v).toString();
  });
}
export function isRecovery(actionId, args) {
  return ACTIONS[actionId]?.risk === 'recovery' || (actionId === 'approve' && args[1] === '0') || (actionId === 'availability' && args[1] === '0');
}
export function curve(supply, count, base, slope) {
  const s = uint(String(supply),32), n = uint(String(count),32), b = uint(String(base),96), m = uint(String(slope),96);
  if (s + n > 1000000n) throw Error('Lot bound exceeded.');
  return n * b + m * n * (2n * s + n - (n ? 1n : 0n)) / 2n;
}

// Exact selected event surface; topics and payloads are independently checked against ethers.
export const EVENTS = {
  "SeedSealed": {
    "contract": "Seed",
    "name": "SeedSealed",
    "signature": "SeedSealed(uint256,address,bytes32,bytes32,uint256,bytes32)",
    "topic": "0x071fec114521189fc6ed4a104a32aaeb5ac8c837285831cb0f71415975d4d90f",
    "fields": [
      {
        "name": "seedId",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "creator",
        "type": "address",
        "indexed": true
      },
      {
        "name": "capsuleHash",
        "type": "bytes32",
        "indexed": false
      },
      {
        "name": "planRoot",
        "type": "bytes32",
        "indexed": false
      },
      {
        "name": "parent",
        "type": "uint256",
        "indexed": false
      },
      {
        "name": "evidenceHash",
        "type": "bytes32",
        "indexed": false
      }
    ]
  },
  "Transfer": {
    "contract": "Seed",
    "name": "Transfer",
    "signature": "Transfer(address,address,uint256)",
    "topic": "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
    "fields": [
      {
        "name": "from",
        "type": "address",
        "indexed": true
      },
      {
        "name": "to",
        "type": "address",
        "indexed": true
      },
      {
        "name": "tokenId",
        "type": "uint256",
        "indexed": true
      }
    ]
  },
  "ReviewOpened": {
    "contract": "Oracle",
    "name": "ReviewOpened",
    "signature": "ReviewOpened(uint256,uint64,address,uint64)",
    "topic": "0xdf614c0fae0e5382079ec4c814070feb57041a5e53d8a2d30a2e927bc6031e84",
    "fields": [
      {
        "name": "seedId",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "round",
        "type": "uint64",
        "indexed": false
      },
      {
        "name": "owner",
        "type": "address",
        "indexed": false
      },
      {
        "name": "until",
        "type": "uint64",
        "indexed": false
      }
    ]
  },
  "RiskAttested": {
    "contract": "Oracle",
    "name": "RiskAttested",
    "signature": "RiskAttested(uint256,uint64,address,uint16,bool,bytes32)",
    "topic": "0xb54b5abd90ba8c75c41495b17d61963cc1eeef0db27a187bfe27bed5f4f1ad76",
    "fields": [
      {
        "name": "seedId",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "round",
        "type": "uint64",
        "indexed": false
      },
      {
        "name": "validator",
        "type": "address",
        "indexed": true
      },
      {
        "name": "riskBps",
        "type": "uint16",
        "indexed": false
      },
      {
        "name": "admitted",
        "type": "bool",
        "indexed": false
      },
      {
        "name": "evidenceHash",
        "type": "bytes32",
        "indexed": false
      }
    ]
  },
  "MarketOpened": {
    "contract": "Mark",
    "name": "MarketOpened",
    "signature": "MarketOpened(uint256,address,uint96,uint96,uint96)",
    "topic": "0x0e69fafda6176c23380e5d3126c562149df5ca350d819bc64b13860da9fc36b8",
    "fields": [
      {
        "name": "id",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "business",
        "type": "address",
        "indexed": true
      },
      {
        "name": "base",
        "type": "uint96",
        "indexed": false
      },
      {
        "name": "slope",
        "type": "uint96",
        "indexed": false
      },
      {
        "name": "target",
        "type": "uint96",
        "indexed": false
      }
    ]
  },
  "Traded": {
    "contract": "Mark",
    "name": "Traded",
    "signature": "Traded(uint256,address,bool,uint32,uint256)",
    "topic": "0xf352b585d935f764073aa89aee75c3c6e8742cc87a0b63b105a6cc120273caf0",
    "fields": [
      {
        "name": "id",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "account",
        "type": "address",
        "indexed": true
      },
      {
        "name": "buy",
        "type": "bool",
        "indexed": false
      },
      {
        "name": "lots",
        "type": "uint32",
        "indexed": false
      },
      {
        "name": "value",
        "type": "uint256",
        "indexed": false
      }
    ]
  },
  "Bloomed": {
    "contract": "Mark",
    "name": "Bloomed",
    "signature": "Bloomed(uint256,bytes32,bytes32,uint256)",
    "topic": "0x4f66438a275796623905f12091b6564b1706cb4710a379c14d081fd401609edf",
    "fields": [
      {
        "name": "id",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "businessNode",
        "type": "bytes32",
        "indexed": true
      },
      {
        "name": "planRoot",
        "type": "bytes32",
        "indexed": false
      },
      {
        "name": "funding",
        "type": "uint256",
        "indexed": false
      }
    ]
  },
  "MissionRouted": {
    "contract": "Mark",
    "name": "MissionRouted",
    "signature": "MissionRouted(uint256,uint32,uint256,bytes32)",
    "topic": "0x2c7f1949748bd4f5f3ef4e3eb5150a738e3e49391d7984246412f989c804a43b",
    "fields": [
      {
        "name": "id",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "index",
        "type": "uint32",
        "indexed": true
      },
      {
        "name": "jobId",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "leaf",
        "type": "bytes32",
        "indexed": false
      }
    ]
  },
  "JobPosted": {
    "contract": "Jobs",
    "name": "JobPosted",
    "signature": "JobPosted(uint256,address,bytes32,string,string,uint96,uint64,uint64)",
    "topic": "0x809a57fb2526885051a1a2beafa83e72f73a021bd64a355f0613a5e51abbac3b",
    "fields": [
      {
        "name": "id",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "business",
        "type": "address",
        "indexed": true
      },
      {
        "name": "specHash",
        "type": "bytes32",
        "indexed": false
      },
      {
        "name": "goal",
        "type": "string",
        "indexed": false
      },
      {
        "name": "successMetric",
        "type": "string",
        "indexed": false
      },
      {
        "name": "bounty",
        "type": "uint96",
        "indexed": false
      },
      {
        "name": "auctionEnd",
        "type": "uint64",
        "indexed": false
      },
      {
        "name": "reviewEnd",
        "type": "uint64",
        "indexed": false
      }
    ]
  },
  "Delivered": {
    "contract": "Jobs",
    "name": "Delivered",
    "signature": "Delivered(uint256,bytes32,string)",
    "topic": "0xeae8f9d8b5ed021b3e2e94968390d0146082831b6c475bb8519732612e012c6c",
    "fields": [
      {
        "name": "id",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "resultHash",
        "type": "bytes32",
        "indexed": false
      },
      {
        "name": "resultURI",
        "type": "string",
        "indexed": false
      }
    ]
  },
  "Closed": {
    "contract": "Jobs",
    "name": "Closed",
    "signature": "Closed(uint256,uint8,uint256)",
    "topic": "0x73a30a0c2202c1545037d5087e8f1a1fbe626dae2f48564f290f55ceba7ffcce",
    "fields": [
      {
        "name": "id",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "state",
        "type": "uint8",
        "indexed": false
      },
      {
        "name": "refundable",
        "type": "uint256",
        "indexed": false
      }
    ]
  },
  "Payout": {
    "contract": "Jobs",
    "name": "Payout",
    "signature": "Payout(uint256,address,uint256,uint256)",
    "topic": "0xa5df5a195b51346b41c715be6896ddef8de524059309701b83d22c7e4ec1aa4c",
    "fields": [
      {
        "name": "id",
        "type": "uint256",
        "indexed": true
      },
      {
        "name": "recipient",
        "type": "address",
        "indexed": true
      },
      {
        "name": "gross",
        "type": "uint256",
        "indexed": false
      },
      {
        "name": "burned",
        "type": "uint256",
        "indexed": false
      }
    ]
  }
};
export function decodeEvent(key, log, expectedAddress) {
  const event = EVENTS[key];
  if (!Object.hasOwn(EVENTS,key) || !event || !log || log.removed || address(log.address) !== address(expectedAddress))
    throw Error('Event is missing or emitted by the wrong contract.');
  const indexed = event.fields.filter(f => f.indexed), plain = event.fields.filter(f => !f.indexed);
  if (!Array.isArray(log.topics) || log.topics.length !== indexed.length + 1 || log.topics[0]?.toLowerCase() !== event.topic)
    throw Error('Event signature or indexed fields do not match.');
  const values = new Map(plain.map((field,i) => [field.name,decode(plain.map(f => f.type),log.data)[i]]));
  indexed.forEach((field,i) => values.set(field.name,decode([field.type],log.topics[i+1])[0]));
  return Object.fromEntries(event.fields.map(field => [field.name,values.get(field.name)]));
}
export function protocolIdentity() {
  return JSON.stringify({methods:METHODS,selectors:SELECTORS,events:EVENTS,actions:ACTIONS});
}
