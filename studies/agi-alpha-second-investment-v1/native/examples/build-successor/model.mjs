// SPDX-License-Identifier: Apache-2.0
import * as alpha from '../../docs/assets/successor/engine.mjs';
import { compileJobs } from './vendor/agijobs/compiler.mjs';
import { JOB_TEMPLATES, createPortfolioJobs } from './vendor/agijobs/templates.mjs';
import { digestObject } from './vendor/agijobs/integrity.mjs';

export const TOKEN = '0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA';
export const DELIVERABLES = [
  'mission.json: count, sum, maximum duration and error count by day and service; zero incorrect totals.',
  'incumbent.json: exact outputs and observed timings for the existing one-pass Map implementation.',
  'alternatives.json: compare the deterministic sort-and-reduce baseline; record that a frontier comparison is missing.',
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
export const FRENCH_TITLES = [
  'Constitution de mission', 'Référence actuelle', 'Ensemble des alternatives', 'Droits et données',
  'Environnement d’entraînement et protocole comparatif', 'Étude des oracles et des enseignants',
  'Classification des échecs', 'Comparaison des architectures', 'Formation des données et de l’expérience',
  'Formation du modèle spécialisé', 'Outils et recherche documentaire', 'Construction du vérificateur',
  'Sécurité et confidentialité', 'Économie complète', 'Charge humaine et pouvoir de décision',
  'Résilience et retour arrière', 'Évaluation protégée sur données nouvelles', 'Validation indépendante',
  'Acceptation responsable', 'Chronique et admission de l’autorité', 'Capacité financée et requalification',
];
export const FRENCH_DELIVERABLES = [
  'mission.json : compter les événements, les erreurs, la durée totale et maximale par jour et service; aucun total incorrect.',
  'incumbent.json : conserver les sorties exactes et les durées de la référence Map en un seul passage.',
  'alternatives.json : comparer la référence déterministe par tri et réduction; signaler l’absence de comparaison avec les meilleures IA.',
  'rights.json : utiliser uniquement des événements fictifs non personnels; préciser les licences et réutilisations permises.',
  'gym.json : versionner le générateur, les entrées mal formées, les jeux publics et le seuil de zéro erreur.',
  'teacher.json : déclarer le code fixe utilisé et l’absence de modèle externe ou d’appel d’enseignement.',
  'failures.json : tester les données vides, nombres invalides, caractères Unicode mal formés et clés de service inhabituelles.',
  'candidates.json : conserver les quatre configurations délimitées et les tentatives rejetées.',
  'experience.json : noter les graines aléatoires, tailles de jeux et version du générateur; aucune preuve protégée.',
  'candidate.json : figer la grammaire retenue et l’empreinte SHA-256 du moteur avant la comparaison.',
  'tools.json : autoriser uniquement le moteur fixe; aucun code arbitraire, navigation ou mouvement de fonds.',
  'verifier.json : reproduire les sorties exactes et rejeter les entrées invalides; signaler l’absence de garde indépendante.',
  'security.json : vérifier l’absence de requêtes externes, clés, données personnelles et autorisations de portefeuille.',
  'economics.json : noter les coûts observés; laisser le prix du calcul, la revue humaine et la maintenance non mesurés.',
  'roles.json : distinguer producteur, vérificateur, responsable de l’acceptation et décideur d’admission; identités non authentifiées.',
  'rollback.json : garder la référence et démontrer l’abandon du candidat actif sans effet externe.',
  'evaluation.json : comparer le candidat figé aux deux références sur six nouveaux jeux publics.',
  'review.json : obtenir une revue attribuable séparément; aucune preuve indépendante n’est créée dans le navigateur.',
  'acceptance.json : exiger des preuves conformes aux termes figés; toutes les tâches restent des brouillons DRAFT.',
  'authority.json : maintenir HOLD et zéro autorisation jusqu’à une admission distincte, limitée, temporaire et révocable.',
  'renewal.json : proposer le prochain test et garder les enseignements; aucun héritage automatique de preuve ou d’autorité.',
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
    incumbent: { id: 'alpha-current', version: alpha.VERSION, description: 'Measured one-pass Map baseline.' },
    alternatives: [{ id: 'alpha-beta', version: alpha.VERSION, description: 'Measured deterministic sort-and-reduce baseline; not a frontier AI comparator.' }],
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
  if(pack.request.language==='fr')return `# ${pack.title} — Fiches de construction SUCCESSOR Ω\n\nRÉPÉTITION LOCALE. Brouillons DRAFT, empreintes non signées, zéro dépense.\nPreuve indépendante absente. Admission HOLD. Aucune autorité accordée.\n\nJeton commun sur Ethereum mainnet : ${TOKEN} (AGIALPHA, 18 décimales).\nBudget de planification seulement; frais, mises et gaz à estimer séparément.\n\n` +
    pack.compilation.graph.nodes.map((job,i)=>`## ${i+1}. ${FRENCH_TITLES[i]}\n\n${FRENCH_DELIVERABLES[i]}\n\nTermes canoniques du compilateur (anglais) : ${job.objective}\n\nCritère d’acceptation canonique (anglais) : ${job.acceptance.predicate}\n\nLimite de planification (unités de base AGIALPHA) : ${job.budget.limitBaseUnits}\nExpiration : ${job.expiresAt}\nProducteur : ${job.actor}\nVérificateur : ${job.verifier.identity}\nResponsable de l’acceptation : ${job.acceptance.owner}\nRetour arrière : ${job.rollback.target}\nEmpreinte non signée : ${job.digest}\n`).join('\n') +
    '\nSuite : organiser une évaluation protégée indépendante, mesurer tous les coûts, mettre en service l’intégration puis demander une décision humaine d’admission distincte. Le jeton commun ne relie pas automatiquement les marchés.\n';
  return `# ${pack.title} — SUCCESSOR Ω build briefs\n\nLOCAL REHEARSAL. DRAFT work, unsigned commitments, zero funds spent.\nIndependent proof absent. Admission HOLD. No authority is granted.\n\nShared Ethereum mainnet token: ${TOKEN} (AGIALPHA, 18 decimals).\nPlanning allowance only; fees, stakes and gas require separate estimates before commissioning.\n\n` +
    pack.compilation.graph.nodes.map((job, i) => `## ${i + 1}. ${JOB_TEMPLATES[i].title}\n\n${job.objective}\n\nAcceptance: ${job.acceptance.predicate}\n\nPlanning limit (AGIALPHA base units): ${job.budget.limitBaseUnits}\nExpiry: ${job.expiresAt}\nProducer: ${job.actor}\nVerifier: ${job.verifier.identity}\nAcceptance owner: ${job.acceptance.owner}\nRollback: ${job.rollback.target}\nUnsigned commitment: ${job.digest}\n`).join('\n') +
    '\nNext: arrange independent protected evaluation, measure full costs, resolve commissioning, then request a separate human admission decision. Sharing the token does not bridge the two markets.\n';
}
