// SPDX-License-Identifier: Apache-2.0
import * as alpha from '../../docs/assets/successor/engine.mjs';
import { compileJobs } from './vendor/agijobs/compiler.mjs';
import { JOB_TEMPLATES, createPortfolioJobs } from './vendor/agijobs/templates.mjs';
import { digestObject } from './vendor/agijobs/integrity.mjs';

export const TOKEN = '0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA';
export const DELIVERABLES = [
  'mission.json: count, sum, maximum duration and error count by day and service; zero incorrect totals.',
  'incumbent.json: exact outputs and observed timings for the existing scan-based implementation.',
  'alternatives.json: compare the deterministic map baseline; record that a frontier comparison is missing.',
  'rights.json: synthetic nonpersonal events only; list code licenses and permitted reuse.',
  'gym.json: version the event generator, malformed-input cases, public partitions and zero-error gate.',
  'teacher.json: disclose that this example uses fixed code and no external model or teaching calls.',
  'failures.json: test empty data, invalid numbers, malformed Unicode and unusual service keys.',
  'candidates.json: preserve all four bounded aggregation configurations and rejected attempts.',
  'experience.json: record seeds, workload sizes and generator version; no protected claims.',
  'candidate.json: freeze the selected grammar and engine SHA-256 before comparative evaluation.',
  'tools.json: allow only the fixed aggregation engine; no arbitrary code, browsing or money movement.',
  'verifier.json: reproduce exact outputs and reject invalid inputs; identify missing independent custody.',
  'security.json: confirm no external requests, keys, personal data or wallet approvals are required.',
  'economics.json: record all observed costs; mark compute price, human review and maintenance unmeasured.',
  'roles.json: separate producer, verifier, acceptance owner and admitter; labels are unauthenticated.',
  'rollback.json: retain the baseline and demonstrate clearing the active candidate without external effects.',
  'evaluation.json: compare the frozen candidate with both baselines on six further public workloads.',
  'review.json: obtain a separately attributable review; this browser leaves independent proof absent.',
  'acceptance.json: require evidence against the frozen terms; all work orders remain DRAFT here.',
  'authority.json: retain HOLD with zero grants until separate, scoped, expiring, revocable admission.',
  'renewal.json: propose the next test and preserve lessons; a successor inherits no proof or authority.',
];

export function missionFor({ name = 'Atlas Ω', budget = '2100', now = new Date().toISOString() } = {}) {
  if (typeof name !== 'string' || !name.trim() || name.length > 48) throw Error('Use a name of 1–48 characters.');
  if (typeof budget !== 'string' || !/^[1-9][0-9]{0,6}$/.test(budget) || BigInt(budget) > 1000000n) {
    throw Error('Use a whole planning allowance from 1 to 1,000,000 AGIALPHA.');
  }
  if (!Number.isFinite(Date.parse(now))) throw Error('A valid clock is required.');
  const expiresAt = new Date(Date.parse(now) + 7 * 86400000).toISOString();
  return {
    schemaVersion: '1.0.0', kind: 'MissionConstitution', missionId: 'streaming-metrics-builder-v1',
    institutionId: 'local-successor-workshop', version: '1', title: name.trim().normalize('NFC'),
    principal: 'example-human-principal', beneficiary: 'Owner of this local synthetic mission',
    objective: 'Produce exact daily service metrics, compare bounded implementations, and prepare reviewable work orders.',
    incumbent: { id: 'alpha-current', version: alpha.VERSION, description: 'Measured scan-based baseline.' },
    alternatives: [{ id: 'alpha-beta', version: alpha.VERSION, description: 'Measured deterministic map baseline; not a frontier AI comparator.' }],
    rights: [{ sourceId: 'synthetic-events', license: 'Apache-2.0 generator; synthetic nonpersonal outputs', dataClass: 'synthetic', permittedUses: ['mission-evaluation', 'fixture-export'], expiresAt }],
    hardGates: [
      { id: 'exact-output', description: 'All grouped counts and durations agree exactly.', maxViolations: 0 },
      { id: 'invalid-input', description: 'Malformed and unsupported records are rejected.', maxViolations: 0 },
      { id: 'no-external-effect', description: 'No network request, live job, payment or authority grant.', maxViolations: 0 },
    ],
    criticalFunctions: JOB_TEMPLATES.map(t => t.coverageKey),
    roles: { producer: 'example-producer', verifier: 'example-verifier', acceptor: 'example-acceptor', admitter: 'example-admitter' },
    budget: { unit: 'AGIALPHA', limitBaseUnits: (BigInt(budget) * 10n ** 18n).toString(), maxDurationMs: 60000, maxRetries: 0, maxJobs: 21 },
    expiresAt,
    authorityCeiling: { level: 'A0', permittedActions: ['inspect-local'], prohibitedActions: ['send-payment', 'post-live-job', 'access-private-data', 'self-admit'], externalEffects: false },
    allowedTools: ['fixed-aggregation-engine'], allowedActions: ['inspect-local'],
    rollback: { target: 'alpha-current', available: true, reason: 'Discard the local candidate and return to the retained fixed baseline.' },
    proofProtocol: { id: 'public-local-rehearsal', version: '1', mode: 'SYNTHETIC_REHEARSAL', formationOwner: 'example-producer', custodian: 'example-verifier', requiredIndependence: 'I0', minimumMargin: 0.05, criticalErrorCeiling: 0, scope: 'Public synthetic cases in one process; no independent proof, mission alpha or operational admission.' },
  };
}

export async function compilePlan(options = {}) {
  const mission = missionFor(options);
  const jobs = createPortfolioJobs(mission).map((job, i) => ({
    ...job,
    objective: `${job.objective} Streaming-metrics deliverable: ${DELIVERABLES[i]}`,
    acceptance: { ...job.acceptance, predicate: `${DELIVERABLES[i]} Preserve failures and missing evidence. Separate review is required.` },
  }));
  const dependencies = [[], [0], [0], [0], [1, 2, 3], [4], [4], [1, 2, 5, 6], [3, 4], [7, 8], [9], [4, 6, 10], [10, 11], [1, 2, 9], [0, 13], [10, 12], [9, 11, 12, 13, 14, 15], [16], [17], [18], [19]];
  const edges = dependencies.flatMap((parents, i) => parents.map(j => ({ from: jobs[j].jobId, to: jobs[i].jobId, kind: 'evidence' })));
  for (const edge of edges) jobs.find(job => job.jobId === edge.to).authorizedInputs.push(edge.from);
  return compileJobs(mission, { jobs, edges, now: options.now });
}

export async function buildPack(options = {}, { signal, onProgress = () => {} } = {}) {
  const now = options.now || new Date().toISOString();
  const request = alpha.newRequest({ max_events: options.events ?? 1000, seed: options.seed ?? 42, max_candidates: 4, language: options.language ?? 'en' });
  if (!/^[0-9a-f]{64}$/.test(options.engineSourceHash || '')) throw Error('Engine source identity is required.');
  onProgress('compile');
  const compilation = await compilePlan({ ...options, now });
  if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
  onProgress('discover');
  const discovery = await alpha.discover(request, { signal });
  const frozen = await alpha.freeze(request, discovery, options.engineSourceHash);
  onProgress('evaluate');
  const evaluation = await alpha.evaluate(request, frozen, { signal });
  const record = {
    schema: 'successor-build-example/v1', createdAt: now, title: compilation.constitution.title,
    scope: 'LOCAL_REHEARSAL', request, compilation, discovery, frozen, evaluation,
    token: { symbol: 'AGIALPHA', chainId: 1, address: TOKEN, decimals: 18 },
    settlement: { status: 'NOT_CONNECTED', transactions: [], spentBaseUnits: '0', allowanceIs: 'ILLUSTRATIVE_NOT_FUNDED' },
    admission: { decision: 'HOLD', independentProof: false, authority: [], specialistASI: false },
    chronicle: [{ kind: 'local-observation', candidateRelease: frozen.release_hash, reusable: 'Configuration hypothesis only; rerun tests.', inheritedProof: false, inheritedAuthority: false }],
  };
  return { ...record, integrityDigest: await digestObject('successor-build-example.v1', record) };
}

export function jobBriefs(pack) {
  return `# ${pack.title} — SUCCESSOR Ω build briefs\n\nLOCAL REHEARSAL. DRAFT work, unsigned commitments, zero funds spent.\nIndependent proof absent. Admission HOLD. No authority is granted.\n\nShared Ethereum mainnet token: ${TOKEN} (AGIALPHA, 18 decimals).\nPlanning allowance only; fees, stakes and gas require separate estimates before commissioning.\n\n` +
    pack.compilation.graph.nodes.map((job, i) => `## ${i + 1}. ${JOB_TEMPLATES[i].title}\n\n${job.objective}\n\nAcceptance: ${job.acceptance.predicate}\n\nPlanning limit (AGIALPHA base units): ${job.budget.limitBaseUnits}\nExpiry: ${job.expiresAt}\nProducer: ${job.actor}\nVerifier: ${job.verifier.identity}\nAcceptance owner: ${job.acceptance.owner}\nRollback: ${job.rollback.target}\nUnsigned commitment: ${job.digest}\n`).join('\n') +
    '\nNext: arrange independent protected evaluation, measure full costs, resolve commissioning, then request a separate human admission decision. Sharing the token does not bridge the two markets.\n';
}
