import { SCHEMA_VERSION, validateMission } from './domain.mjs';

export const JOB_TEMPLATES = Object.freeze(
  [
    [
      'mission-constitution',
      'constitution',
      'Mission Constitution',
      'Freeze objective, beneficiary, accountable principal, hard constraints and prohibitions.',
    ],
    [
      'incumbent-baseline',
      'evidence',
      'Incumbent Baseline',
      'Measure accepted quality, complete cost, risk, time, human burden and authority.',
    ],
    [
      'alternative-set',
      'constitution',
      'Alternative Set',
      'Document the strongest credible frontier, specialist, human, hybrid, software and no-action alternatives.',
    ],
    [
      'rights-data',
      'constitution',
      'Rights and Data Constitution',
      'Establish source provenance, licenses, retention, exclusions and permitted reuse.',
    ],
    [
      'mission-gym',
      'formation',
      'Mission Gym and Benchmark Constitution',
      'Specify states, observations, actions, transitions, rewards, constraints, partitions, verifier and basis risk; freeze representative distribution, protected custody, critical failures and thresholds.',
    ],
    [
      'oracle-teacher',
      'evidence',
      'Oracle and Teacher Study',
      'Declare external teaching signals, hidden-call prohibition and transfer hypothesis.',
    ],
    [
      'failure-taxonomy',
      'challenge',
      'Failure Taxonomy',
      'Classify errors, severity, causes, abstention, adversarial cases and stop conditions.',
    ],
    [
      'architecture-frontier',
      'formation',
      'Architecture Frontier',
      'Form diverse complete candidates and retain non-dominated reserve options.',
    ],
    [
      'experience-formation',
      'formation',
      'Data and Experience Formation',
      'Build rights-cleared examples and simulation experience with explicit quality controls.',
    ],
    [
      'specialist-formation',
      'formation',
      'Specialist Model Formation',
      'Construct or adapt candidate components with exact immutable release identities.',
    ],
    [
      'tools-retrieval',
      'formation',
      'Tool and Retrieval Formation',
      'Build bounded deterministic checks, retrieval, planners, sandboxes and interfaces.',
    ],
    [
      'verifier-formation',
      'verification',
      'Verifier Formation',
      'Calibrate independent evaluation, replay, attacks, hidden ground truth and scoring.',
    ],
    [
      'security-privacy',
      'verification',
      'Security and Privacy Proof',
      'Test credential controls, isolation, threat model, incidents and provider risks.',
    ],
    [
      'complete-economics',
      'evidence',
      'Complete Economics',
      'Count construction, operation, human rescue, maintenance, requalification and unwind.',
    ],
    [
      'human-agency',
      'constitution',
      'Human Burden and Agency',
      'Define reviewer capacity, escalation, contestability and accountable decision rights.',
    ],
    [
      'resilience-rollback',
      'verification',
      'Resilience and Rollback',
      'Prove graceful degradation, kill switch, portability and known-good restoration.',
    ],
    [
      'fresh-evaluation',
      'verification',
      'Protected Fresh Evaluation',
      'Evaluate one frozen challenger on unseen representative work with full intervention costs.',
    ],
    [
      'independent-validation',
      'verification',
      'Independent Validation',
      'Independently examine evidence, limitations, critical errors, basis risk and fit for stated purpose.',
    ],
    [
      'accountable-acceptance',
      'admission',
      'Accountable Acceptance',
      'Record the attributable purpose-specific acceptance decision separately from independent validation and authority admission.',
    ],
    [
      'chronicle-authority',
      'admission',
      'Chronicle and Authority Admission',
      'Record separate knowledge and authority decisions, scope, expiry, monitoring and revocation.',
    ],
    [
      'capital-requalification',
      'renewal',
      'Capital-to-Capacity and Requalification',
      'Allocate verified available value and define next-successor and fresh-transfer triggers.',
    ],
  ].map(([id, family, title, objective]) =>
    Object.freeze({ id, family, title, objective, coverageKey: id })
  )
);

export function createPortfolioJobs(input) {
  const mission = validateMission(input);
  return JOB_TEMPLATES.map((template) => ({
    schemaVersion: SCHEMA_VERSION,
    kind: 'SealedWorkOrder',
    jobId: `${mission.missionId}:${template.id}`,
    missionId: mission.missionId,
    version: '1',
    family: template.family,
    objective: template.objective,
    principal: mission.principal,
    actor: mission.roles.producer,
    authorizedInputs: mission.rights.map((right) => right.sourceId),
    evidenceObligation: ['source-lineage', 'complete-cost', 'failure-record'],
    permittedTools: [...mission.allowedTools],
    permittedActions: [...mission.allowedActions],
    prohibitedActions: [...mission.authorityCeiling.prohibitedActions],
    budget: {
      unit: mission.budget.unit,
      limitBaseUnits: (BigInt(mission.budget.limitBaseUnits) / 21n).toString(),
      maxDurationMs: mission.budget.maxDurationMs,
      maxRetries: mission.budget.maxRetries,
    },
    expiresAt: mission.expiresAt,
    outputSchema: {
      type: 'object',
      required: ['evidence', 'findings', 'cost'],
    },
    verifier: {
      identity: mission.roles.verifier,
      method:
        'Independent examination against frozen purpose-specific criteria; template is not executed proof.',
      independence: 'I0',
    },
    acceptance: {
      owner: mission.roles.acceptor,
      predicate: `All ${template.title} obligations have valid traceable evidence and no failed hard gate.`,
      evidenceSources: mission.rights.map((right) => right.sourceId),
    },
    rollback: { ...mission.rollback },
    chronicle: {
      eligible: false,
      rights: 'Requires a separate rights and admission review.',
      scope: mission.objective,
      expiresAt: mission.expiresAt,
    },
    covers: mission.criticalFunctions.includes(template.coverageKey)
      ? [template.coverageKey]
      : [],
    state: 'DRAFT',
  }));
}
