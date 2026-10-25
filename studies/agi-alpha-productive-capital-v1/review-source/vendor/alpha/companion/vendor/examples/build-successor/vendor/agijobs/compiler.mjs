import {
  SCHEMA_VERSION,
  SuccessorError,
  requireCondition,
  validateMission,
  validateWorkOrder,
  validateGraph,
  transitionJob,
} from './domain.mjs';
import { cloneJson, digestObject } from './integrity.mjs';
import { createPortfolioJobs } from './templates.mjs';

const EXECUTION_EDGES = new Set(['evidence', 'control', 'challenge']);
export function workOrderPayload(input) {
  const job = validateWorkOrder(input);
  const { digest, sealed, signatureStatus, state, ...immutable } = job;
  return immutable;
}
export async function sealWorkOrder(input) {
  const job = validateWorkOrder(input);
  requireCondition(
    job.state === 'DRAFT',
    'SEAL_STATE_FORBIDDEN',
    'Only a draft may be sealed; material changes require a new draft version'
  );
  return {
    ...job,
    sealed: true,
    signatureStatus: 'UNSIGNED_COMMITMENT',
    digest: await digestObject(
      'successor.work-order.v1',
      workOrderPayload(job)
    ),
  };
}
export async function verifyWorkOrderSeal(input) {
  const job = validateWorkOrder(input);
  return (
    job.sealed === true &&
    job.digest ===
      (await digestObject('successor.work-order.v1', workOrderPayload(job)))
  );
}
export async function transitionSealedJob(current, event, trustedContext = {}) {
  requireCondition(
    await verifyWorkOrderSeal(current),
    'JOB_SEAL_INVALID',
    'The immutable work-order seal is invalid'
  );
  return transitionJob(current, event, { ...trustedContext, sealValid: true });
}
function topologicalOrder(nodes, edges) {
  const indegree = new Map(nodes.map((node) => [node.jobId, 0]));
  const outgoing = new Map(nodes.map((node) => [node.jobId, []]));
  for (const edge of edges.filter((edge) => EXECUTION_EDGES.has(edge.kind))) {
    outgoing.get(edge.from).push(edge.to);
    indegree.set(edge.to, indegree.get(edge.to) + 1);
  }
  const queue = [...indegree]
    .filter(([, count]) => count === 0)
    .map(([key]) => key)
    .sort();
  const order = [];
  const depth = new Map(nodes.map((node) => [node.jobId, 1]));
  while (queue.length) {
    const key = queue.shift();
    order.push(key);
    for (const target of outgoing.get(key)) {
      depth.set(target, Math.max(depth.get(target), depth.get(key) + 1));
      indegree.set(target, indegree.get(target) - 1);
      if (!indegree.get(target)) {
        queue.push(target);
        queue.sort();
      }
    }
  }
  requireCondition(
    order.length === nodes.length,
    'GRAPH_CYCLE',
    'Execution, acceptance and challenge dependencies must be acyclic; use bounded version-producing discovery loops'
  );
  requireCondition(
    Math.max(...depth.values()) <= 64,
    'GRAPH_DEPTH_EXCEEDED',
    'Graph exceeds the supported execution depth'
  );
  return order;
}

export async function compileJobs(
  input,
  { jobs: proposedJobs, edges = [], now = new Date().toISOString() } = {}
) {
  const mission = validateMission(input);
  const instant = Date.parse(now);
  requireCondition(
    Number.isFinite(instant),
    'CLOCK_INVALID',
    'A valid compiler clock is required'
  );
  requireCondition(
    instant < Date.parse(mission.expiresAt),
    'MISSION_EXPIRED',
    'The mission constitution has expired'
  );
  requireCondition(
    new Set([
      mission.roles.producer,
      mission.roles.verifier,
      mission.roles.admitter,
    ]).size === 3,
    'ROLE_CONFLICT',
    'Producer, verifier and admitter must have distinct identities'
  );
  requireCondition(
    mission.roles.producer !== mission.roles.acceptor,
    'ROLE_CONFLICT',
    'A producer cannot accept its own delivered work'
  );
  requireCondition(
    mission.proofProtocol.formationOwner !== mission.proofProtocol.custodian,
    'PROOF_CUSTODY_CONFLICT',
    'Formation and protected proof custody must be separately attributed'
  );
  requireCondition(
    mission.rollback.available,
    'ROLLBACK_UNAVAILABLE',
    'An available rollback or containment route is required'
  );
  if (mission.proofProtocol.mode === 'INDEPENDENT_REQUEST')
    requireCondition(
      ['I3', 'I4'].includes(mission.proofProtocol.requiredIndependence),
      'INDEPENDENCE_INSUFFICIENT',
      'An independently proven request requires I3 or I4 custody; internal rehearsal remains available'
    );
  for (const action of mission.allowedActions)
    requireCondition(
      !mission.authorityCeiling.prohibitedActions.includes(action),
      'ACTION_PROHIBITED',
      'A permitted formation action conflicts with a prohibition',
      { action }
    );
  requireCondition(
    proposedJobs === undefined || Array.isArray(proposedJobs),
    'SCHEMA_INVALID',
    'Jobs must be a bounded array'
  );
  const jobs = (proposedJobs ?? createPortfolioJobs(mission)).map(
    validateWorkOrder
  );
  requireCondition(
    jobs.length <= mission.budget.maxJobs,
    'JOB_LIMIT_EXCEEDED',
    'The graph exceeds its authorized work count'
  );
  const graph = validateGraph({
    schemaVersion: SCHEMA_VERSION,
    kind: 'JobGraph',
    graphId: `${mission.missionId}:graph`,
    missionId: mission.missionId,
    version: mission.version,
    nodes: jobs,
    edges,
    authorityCreated: 'NONE',
  });
  const ids = new Set(jobs.map((job) => job.jobId));
  const rights = new Map(
    mission.rights.map((right) => [right.sourceId, right])
  );
  const edgeKeys = new Set();
  for (const edge of graph.edges) {
    requireCondition(
      ids.has(edge.from) && ids.has(edge.to),
      'REFERENCE_UNRESOLVED',
      'A graph edge references an unknown job',
      edge
    );
    requireCondition(
      edge.from !== edge.to,
      'GRAPH_CYCLE',
      'Self-dependent jobs are not admissible',
      edge
    );
    const key = `${edge.from}|${edge.to}|${edge.kind}`;
    requireCondition(
      !edgeKeys.has(key),
      'EDGE_DUPLICATE',
      'Duplicate graph edge',
      edge
    );
    edgeKeys.add(key);
  }
  const executionOrder = topologicalOrder(jobs, graph.edges);
  let reservation = 0n;
  for (const job of jobs) {
    requireCondition(
      job.missionId === mission.missionId &&
        job.principal === mission.principal,
      'MISSION_BINDING_MISMATCH',
      'Job mission and accountable principal must match the constitution',
      { jobId: job.jobId }
    );
    requireCondition(
      job.state === 'DRAFT',
      'COMPILER_REQUIRES_DRAFT',
      'Compilation cannot grant or replay an existing job lifecycle state'
    );
    requireCondition(
      job.actor !== job.verifier.identity &&
        job.actor !== mission.roles.admitter,
      'ROLE_CONFLICT',
      'A producer cannot verify its own work or hold admission identity',
      { jobId: job.jobId }
    );
    requireCondition(
      job.actor !== job.acceptance.owner,
      'ROLE_CONFLICT',
      'A producing actor cannot accept its own delivered work',
      { jobId: job.jobId }
    );
    requireCondition(
      job.verifier.identity === mission.roles.verifier,
      'VERIFIER_UNAUTHORIZED',
      'Job verifier must be the constituted verifier identity',
      { jobId: job.jobId }
    );
    requireCondition(
      job.acceptance.owner === mission.roles.acceptor,
      'ACCEPTANCE_OWNER_MISMATCH',
      'Acceptance must belong to the constituted owner',
      { jobId: job.jobId }
    );
    requireCondition(
      job.rollback.available,
      'ROLLBACK_UNAVAILABLE',
      'Job has no available rollback or containment route',
      { jobId: job.jobId }
    );
    requireCondition(
      Date.parse(job.expiresAt) > instant &&
        Date.parse(job.expiresAt) <= Date.parse(mission.expiresAt),
      'JOB_EXPIRED',
      'Job expiry must be current and within the mission expiry',
      { jobId: job.jobId }
    );
    requireCondition(
      job.budget.unit === mission.budget.unit,
      'BUDGET_UNIT_MISMATCH',
      'Job and mission budget units differ',
      { jobId: job.jobId }
    );
    requireCondition(
      job.budget.maxRetries <= mission.budget.maxRetries &&
        job.budget.maxDurationMs <= mission.budget.maxDurationMs,
      'BUDGET_LIMIT_EXCEEDED',
      'Job resource limits exceed the mission ceiling',
      { jobId: job.jobId }
    );
    reservation += BigInt(job.budget.limitBaseUnits);
    for (const tool of job.permittedTools)
      requireCondition(
        mission.allowedTools.includes(tool),
        'TOOL_UNSUPPORTED',
        'The mission has not admitted this tool',
        { jobId: job.jobId, tool }
      );
    for (const action of job.permittedActions)
      requireCondition(
        mission.allowedActions.includes(action) &&
          !job.prohibitedActions.includes(action) &&
          !mission.authorityCeiling.prohibitedActions.includes(action),
        'ACTION_PROHIBITED',
        'Action is not within the mission capability mask',
        { jobId: job.jobId, action }
      );
    for (const prohibited of mission.authorityCeiling.prohibitedActions)
      requireCondition(
        job.prohibitedActions.includes(prohibited),
        'PROHIBITION_WEAKENED',
        'Job removes a constitutional prohibition',
        { jobId: job.jobId, prohibited }
      );
    for (const source of job.authorizedInputs) {
      if (rights.has(source)) {
        const right = rights.get(source);
        requireCondition(
          Date.parse(right.expiresAt) > instant &&
            Date.parse(right.expiresAt) >= Date.parse(job.expiresAt),
          'RIGHTS_EXPIRED',
          'Source rights do not cover the job duration',
          { jobId: job.jobId, source }
        );
        requireCondition(
          right.permittedUses.includes('mission-evaluation'),
          'RIGHTS_SCOPE_MISMATCH',
          'Source does not permit mission evaluation',
          { jobId: job.jobId, source }
        );
      } else {
        requireCondition(
          ids.has(source) &&
            graph.edges.some(
              (edge) =>
                edge.from === source &&
                edge.to === job.jobId &&
                edge.kind === 'evidence'
            ),
          'EVIDENCE_PATH_MISSING',
          'Every derived input requires an upstream evidence edge',
          { jobId: job.jobId, source }
        );
      }
    }
    for (const source of job.acceptance.evidenceSources)
      requireCondition(
        job.authorizedInputs.includes(source),
        'ACCEPTANCE_EVIDENCE_UNAVAILABLE',
        'Acceptance cannot depend on an unauthorized or producer-only source',
        { jobId: job.jobId, source }
      );
  }
  requireCondition(
    reservation <= BigInt(mission.budget.limitBaseUnits),
    'BUDGET_EXCEEDED',
    'Aggregate cumulative job budgets exceed the mission budget',
    {
      reservedBaseUnits: reservation.toString(),
      limitBaseUnits: mission.budget.limitBaseUnits,
    }
  );
  const coverage = mission.criticalFunctions.map((functionId) => ({
    functionId,
    jobIds: jobs
      .filter((job) => job.covers.includes(functionId))
      .map((job) => job.jobId),
    status: 'PLANNED_NOT_ACCEPTED',
  }));
  for (const obligation of coverage)
    requireCondition(
      obligation.jobIds.length > 0,
      'CRITICAL_COVERAGE_MISSING',
      'A non-negotiable mission function has no job path',
      { functionId: obligation.functionId }
    );
  const sealedJobs = await Promise.all(jobs.map(sealWorkOrder));
  const sealedGraph = { ...graph, nodes: sealedJobs };
  sealedGraph.digest = await digestObject(
    'successor.job-graph.v1',
    sealedGraph
  );
  const dependencyMap = Object.fromEntries(
    jobs.map((job) => [
      job.jobId,
      graph.edges
        .filter(
          (edge) => edge.to === job.jobId && EXECUTION_EDGES.has(edge.kind)
        )
        .map((edge) => ({ jobId: edge.from, kind: edge.kind })),
    ])
  );
  const invalidationMap = Object.fromEntries(
    [...rights.keys(), ...ids].map((key) => [
      key,
      jobs
        .filter((job) => job.authorizedInputs.includes(key))
        .map((job) => job.jobId),
    ])
  );
  for (const edge of graph.edges.filter((edge) =>
    ['evidence', 'invalidation', 'challenge', 'control'].includes(edge.kind)
  ))
    if (!invalidationMap[edge.from].includes(edge.to))
      invalidationMap[edge.from].push(edge.to);
  return {
    schemaVersion: SCHEMA_VERSION,
    status: 'SEALED',
    mode: mission.proofProtocol.mode,
    constitution: mission,
    graph: sealedGraph,
    executionOrder,
    coverage,
    criticalEvidenceCuts: coverage.map(({ functionId, jobIds }) => ({
      functionId,
      removeJobIds: jobIds,
      exhaustive: false,
    })),
    budgetReservations: {
      unit: mission.budget.unit,
      reservedBaseUnits: reservation.toString(),
      limitBaseUnits: mission.budget.limitBaseUnits,
      includesRetries: true,
    },
    dependencyMap,
    invalidationMap,
    capabilityRequests: jobs.map((job) => ({
      jobId: job.jobId,
      actor: job.actor,
      tools: job.permittedTools,
      actions: job.permittedActions,
      status: 'REQUESTED_NOT_GRANTED',
    })),
    evaluationPlan: cloneJson(mission.proofProtocol),
    authorityCreated: 'NONE',
    signatureStatus: 'UNSIGNED_COMMITMENT',
    digest: await digestObject('successor.constitution.v1', mission),
  };
}

export function invalidationClosure(compilation, sourceIds) {
  const pending = [...sourceIds];
  const seen = new Set();
  while (pending.length) {
    const source = pending.shift();
    if (seen.has(source)) continue;
    seen.add(source);
    pending.push(...(compilation.invalidationMap[source] ?? []));
  }
  return [...seen].sort();
}

export async function diagnoseMission(mission, options) {
  try {
    return await compileJobs(mission, options);
  } catch (error) {
    if (!(error instanceof SuccessorError)) throw error;
    return {
      status: 'REJECTED',
      diagnostics: [error.toJSON()],
      authorityCreated: 'NONE',
    };
  }
}
