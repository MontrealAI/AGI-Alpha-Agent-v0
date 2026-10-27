import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
export function requireResearchOnly(q) {
  if (!q || q.schema !== 'agialpha.research-only-qualification.v1' ||
      q.candidate_id !== 'cyclic-depolarizing-quantum-reproduction' ||
      q.status !== 'not-qualified' || q.research_artifact !== true ||
      q.authorization !== 'local-simulation-only') throw Error('Research-only qualification contract missing or escalated');
  for (const k of ['new_discovery','novelty_truth_established','beyond_human_foresight_established','qualified_venture',
    'productive_venture_established','commercial_delivery_established','authorized_transaction','minted','listed',
    'live_identity_asserted','execution_authority'])
    if (q[k] !== false) throw Error('Qualification escalation refused: '+k);
  for (const k of ['sales_count','collected_cash_usd','provider_revenue_usd'])
    if (q[k] !== 0) throw Error('Unobserved commerce refused: '+k);
  return true;
}
export async function verifyResearchOutput(directory) {
  const root=path.resolve(directory);
  const m=JSON.parse(await fs.readFile(path.join(root,'qualification_manifest.json'),'utf8'));
  requireResearchOnly(m.qualification);
  for (const [name,pin] of Object.entries(m.artifact_bindings)) {
    if (path.basename(name)!==name) throw Error('Unsafe artifact name');
    const b=await fs.readFile(path.join(root,name));
    if (b.length!==pin.bytes || createHash('sha256').update(b).digest('hex')!==pin.sha256)
      throw Error('Research artifact bytes changed: '+name);
  }
  const genome=JSON.parse(await fs.readFile(path.join(root,'nova_seed_genome.json'),'utf8'));
  requireResearchOnly(genome.study.qualification);
  if (JSON.stringify(genome.study.qualification)!==JSON.stringify(m.qualification)) throw Error('Seed qualification mismatch');
  const mark=JSON.parse(await fs.readFile(path.join(root,'mark_inspection.json'),'utf8'));
  if(mark.eligible_venture!==false || mark.authorized_transaction!==false || mark.revenue_usd!==0 ||
     mark.status!=='not-qualified-research-inspection') throw Error('MARK eligibility escalation refused');
  const dossier=JSON.parse(await fs.readFile(path.join(root,'insight_dossier.json'),'utf8'));
  if(dossier.economic_value_verified_usd!=='0') throw Error('Native economic value escalation refused');
  return {status:'not-qualified',artifact_bindings_verified:Object.keys(m.artifact_bindings).length,
    research_only:true,commercial_delivery_established:false,authority_granted:false};
}
if (process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) {
  if(process.argv[2]!=='--verify' || !process.argv[3]) throw Error('Usage: node enforce_research_only.mjs --verify OUTPUT_DIR');
  console.log(JSON.stringify(await verifyResearchOutput(process.argv[3])));
}
