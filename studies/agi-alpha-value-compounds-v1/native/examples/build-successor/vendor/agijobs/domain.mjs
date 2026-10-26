import { canonicalize, cloneJson } from './integrity.mjs';

export const SCHEMA_VERSION = '1.0.0';
export const JOB_FAMILIES = Object.freeze([
  'constitution',
  'evidence',
  'formation',
  'challenge',
  'verification',
  'admission',
  'renewal',
]);
export const EDGE_KINDS = Object.freeze([
  'evidence',
  'control',
  'challenge',
  'rollback',
  'invalidation',
]);
export const JOB_STATES = Object.freeze([
  'DRAFT',
  'UNDERWRITTEN',
  'AUTHORIZED',
  'EXECUTING',
  'VERIFIED',
  'ACCEPTED',
  'CHRONICLE_ELIGIBLE',
  'REFUSED',
  'FAILED',
  'TIMED_OUT',
  'REPAIR_REQUIRED',
  'ROLLED_BACK',
]);
export class SuccessorError extends Error {
  constructor(code, message, { details = {}, retryable = false } = {}) {
    super(message);
    this.name = 'SuccessorError';
    this.code = code;
    this.details = details;
    this.retryable = retryable;
  }
  toJSON() {
    return {
      code: this.code,
      message: this.message,
      details: this.details,
      retryable: this.retryable,
    };
  }
}
export function requireCondition(condition, code, message, details = {}) {
  if (!condition) throw new SuccessorError(code, message, { details });
}
const fail = (path, message) => {
  throw new SuccessorError('SCHEMA_INVALID', `${path}: ${message}`, {
    details: { path },
  });
};
function object(value, keys, required, path) {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    fail(path, 'expected object');
  for (const key of Object.keys(value))
    if (!keys.includes(key)) fail(`${path}.${key}`, 'unknown field');
  for (const key of required)
    if (!Object.hasOwn(value, key)) fail(`${path}.${key}`, 'required field');
}
const text = (value, path) => {
  if (typeof value !== 'string' || !value.trim() || value.length > 16000)
    fail(path, 'expected nonempty bounded string');
};
const id = (value, path) => {
  text(value, path);
  if (!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$/.test(value))
    fail(path, 'invalid identifier');
};
const list = (value, path, check = text, minimum = 0, maximum = 256) => {
  if (!Array.isArray(value) || value.length < minimum || value.length > maximum)
    fail(path, 'invalid list size');
  value.forEach((entry, i) => check(entry, `${path}[${i}]`));
};
const integer = (value, path, min = 0, max = 1000000000) => {
  if (!Number.isSafeInteger(value) || value < min || value > max)
    fail(path, 'expected bounded integer');
};
const date = (value, path) => {
  if (
    typeof value !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$/.test(value) ||
    !Number.isFinite(Date.parse(value))
  )
    fail(path, 'expected UTC ISO timestamp');
  const normalized = new Date(value).toISOString();
  if (value !== normalized && value !== normalized.replace('.000Z', 'Z'))
    fail(path, 'invalid calendar timestamp');
};
const choice = (value, values, path) => {
  if (!values.includes(value))
    fail(path, `expected one of ${values.join(', ')}`);
};
const unique = (values, path) => {
  if (new Set(values).size !== values.length) fail(path, 'duplicate values');
};
const bool = (value, path) => {
  if (typeof value !== 'boolean') fail(path, 'expected boolean');
};
function json(value) {
  try {
    canonicalize(value);
  } catch (error) {
    throw new SuccessorError('SCHEMA_INVALID', error.message);
  }
}
export function validateBudget(value, path = 'budget', mission = false) {
  const fields = [
    'unit',
    'limitBaseUnits',
    'maxDurationMs',
    'maxRetries',
    ...(mission ? ['maxJobs'] : []),
  ];
  object(value, fields, fields, path);
  id(value.unit, `${path}.unit`);
  if (
    typeof value.limitBaseUnits !== 'string' ||
    !/^(0|[1-9][0-9]{0,29})$/.test(value.limitBaseUnits)
  )
    fail(
      `${path}.limitBaseUnits`,
      'expected canonical unsigned integer string'
    );
  integer(value.maxDurationMs, `${path}.maxDurationMs`, 1, 86400000);
  integer(value.maxRetries, `${path}.maxRetries`, 0, 100);
  if (mission) integer(value.maxJobs, `${path}.maxJobs`, 1, 256);
}
function rollback(value, path) {
  object(
    value,
    ['target', 'available', 'reason'],
    ['target', 'available', 'reason'],
    path
  );
  id(value.target, `${path}.target`);
  bool(value.available, `${path}.available`);
  text(value.reason, `${path}.reason`);
}
function reference(value, path) {
  object(
    value,
    ['id', 'version', 'description'],
    ['id', 'version', 'description'],
    path
  );
  id(value.id, `${path}.id`);
  id(value.version, `${path}.version`);
  text(value.description, `${path}.description`);
}
export function validateMission(input) {
  json(input);
  const fields = [
    'schemaVersion',
    'kind',
    'missionId',
    'institutionId',
    'version',
    'title',
    'principal',
    'beneficiary',
    'objective',
    'incumbent',
    'alternatives',
    'rights',
    'hardGates',
    'criticalFunctions',
    'roles',
    'budget',
    'expiresAt',
    'authorityCeiling',
    'allowedTools',
    'allowedActions',
    'rollback',
    'proofProtocol',
  ];
  object(input, fields, fields, 'mission');
  requireCondition(
    input.schemaVersion === SCHEMA_VERSION,
    'SCHEMA_VERSION_UNSUPPORTED',
    'Unsupported mission schema version'
  );
  choice(input.kind, ['MissionConstitution'], 'mission.kind');
  for (const key of ['missionId', 'institutionId', 'version', 'principal'])
    id(input[key], `mission.${key}`);
  for (const key of ['title', 'beneficiary', 'objective'])
    text(input[key], `mission.${key}`);
  reference(input.incumbent, 'mission.incumbent');
  list(input.alternatives, 'mission.alternatives', reference, 1, 32);
  unique(
    input.alternatives.map((alternative) => alternative.id),
    'mission.alternatives'
  );
  list(
    input.rights,
    'mission.rights',
    (right, path) => {
      object(
        right,
        ['sourceId', 'license', 'dataClass', 'permittedUses', 'expiresAt'],
        ['sourceId', 'license', 'dataClass', 'permittedUses', 'expiresAt'],
        path
      );
      id(right.sourceId, `${path}.sourceId`);
      text(right.license, `${path}.license`);
      choice(
        right.dataClass,
        ['synthetic', 'public-licensed-nonpersonal'],
        `${path}.dataClass`
      );
      list(right.permittedUses, `${path}.permittedUses`, id, 1, 20);
      date(right.expiresAt, `${path}.expiresAt`);
    },
    1,
    256
  );
  unique(
    input.rights.map((right) => right.sourceId),
    'mission.rights'
  );
  list(
    input.hardGates,
    'mission.hardGates',
    (gate, path) => {
      object(
        gate,
        ['id', 'description', 'maxViolations'],
        ['id', 'description', 'maxViolations'],
        path
      );
      id(gate.id, `${path}.id`);
      text(gate.description, `${path}.description`);
      integer(gate.maxViolations, `${path}.maxViolations`, 0, 100);
    },
    1,
    64
  );
  unique(
    input.hardGates.map((gate) => gate.id),
    'mission.hardGates'
  );
  list(input.criticalFunctions, 'mission.criticalFunctions', id, 1, 64);
  unique(input.criticalFunctions, 'mission.criticalFunctions');
  object(
    input.roles,
    ['producer', 'verifier', 'acceptor', 'admitter'],
    ['producer', 'verifier', 'acceptor', 'admitter'],
    'mission.roles'
  );
  for (const [key, value] of Object.entries(input.roles))
    id(value, `mission.roles.${key}`);
  validateBudget(input.budget, 'mission.budget', true);
  date(input.expiresAt, 'mission.expiresAt');
  object(
    input.authorityCeiling,
    ['level', 'permittedActions', 'prohibitedActions', 'externalEffects'],
    ['level', 'permittedActions', 'prohibitedActions', 'externalEffects'],
    'mission.authorityCeiling'
  );
  choice(
    input.authorityCeiling.level,
    ['A0', 'A1', 'A2', 'A3', 'A4'],
    'mission.authorityCeiling.level'
  );
  list(
    input.authorityCeiling.permittedActions,
    'mission.authorityCeiling.permittedActions',
    id,
    1
  );
  list(
    input.authorityCeiling.prohibitedActions,
    'mission.authorityCeiling.prohibitedActions',
    id,
    1
  );
  bool(
    input.authorityCeiling.externalEffects,
    'mission.authorityCeiling.externalEffects'
  );
  list(input.allowedTools, 'mission.allowedTools', id, 1);
  list(input.allowedActions, 'mission.allowedActions', id, 1);
  rollback(input.rollback, 'mission.rollback');
  object(
    input.proofProtocol,
    [
      'id',
      'version',
      'mode',
      'formationOwner',
      'custodian',
      'requiredIndependence',
      'minimumMargin',
      'criticalErrorCeiling',
      'scope',
    ],
    [
      'id',
      'version',
      'mode',
      'formationOwner',
      'custodian',
      'requiredIndependence',
      'minimumMargin',
      'criticalErrorCeiling',
      'scope',
    ],
    'mission.proofProtocol'
  );
  for (const key of ['id', 'version', 'formationOwner', 'custodian'])
    id(input.proofProtocol[key], `mission.proofProtocol.${key}`);
  choice(
    input.proofProtocol.mode,
    ['SYNTHETIC_REHEARSAL', 'INDEPENDENT_REQUEST'],
    'mission.proofProtocol.mode'
  );
  choice(
    input.proofProtocol.requiredIndependence,
    ['I0', 'I1', 'I2', 'I3', 'I4'],
    'mission.proofProtocol.requiredIndependence'
  );
  if (
    !Number.isFinite(input.proofProtocol.minimumMargin) ||
    input.proofProtocol.minimumMargin < 0
  )
    fail('mission.proofProtocol.minimumMargin', 'expected nonnegative number');
  integer(
    input.proofProtocol.criticalErrorCeiling,
    'mission.proofProtocol.criticalErrorCeiling',
    0,
    100
  );
  text(input.proofProtocol.scope, 'mission.proofProtocol.scope');
  return cloneJson(input);
}

export function validateWorkOrder(input) {
  json(input);
  const required = [
    'schemaVersion',
    'kind',
    'jobId',
    'missionId',
    'version',
    'family',
    'objective',
    'principal',
    'actor',
    'authorizedInputs',
    'evidenceObligation',
    'permittedTools',
    'permittedActions',
    'prohibitedActions',
    'budget',
    'expiresAt',
    'outputSchema',
    'verifier',
    'acceptance',
    'rollback',
    'chronicle',
    'covers',
    'state',
  ];
  object(
    input,
    [...required, 'digest', 'sealed', 'signatureStatus'],
    required,
    'job'
  );
  requireCondition(
    input.schemaVersion === SCHEMA_VERSION,
    'SCHEMA_VERSION_UNSUPPORTED',
    'Unsupported work-order schema version'
  );
  choice(input.kind, ['SealedWorkOrder'], 'job.kind');
  for (const key of ['jobId', 'missionId', 'version', 'principal', 'actor'])
    id(input[key], `job.${key}`);
  choice(input.family, JOB_FAMILIES, 'job.family');
  choice(input.state, JOB_STATES, 'job.state');
  text(input.objective, 'job.objective');
  for (const key of [
    'authorizedInputs',
    'evidenceObligation',
    'permittedTools',
    'permittedActions',
    'prohibitedActions',
    'covers',
  ]) {
    list(input[key], `job.${key}`, id, key === 'covers' ? 0 : 1);
    unique(input[key], `job.${key}`);
  }
  validateBudget(input.budget, 'job.budget');
  date(input.expiresAt, 'job.expiresAt');
  object(
    input.outputSchema,
    ['type', 'required'],
    ['type', 'required'],
    'job.outputSchema'
  );
  choice(input.outputSchema.type, ['object'], 'job.outputSchema.type');
  list(input.outputSchema.required, 'job.outputSchema.required', id, 1);
  object(
    input.verifier,
    ['identity', 'method', 'independence'],
    ['identity', 'method', 'independence'],
    'job.verifier'
  );
  id(input.verifier.identity, 'job.verifier.identity');
  text(input.verifier.method, 'job.verifier.method');
  choice(
    input.verifier.independence,
    ['I0', 'I1', 'I2', 'I3', 'I4'],
    'job.verifier.independence'
  );
  object(
    input.acceptance,
    ['owner', 'predicate', 'evidenceSources'],
    ['owner', 'predicate', 'evidenceSources'],
    'job.acceptance'
  );
  id(input.acceptance.owner, 'job.acceptance.owner');
  text(input.acceptance.predicate, 'job.acceptance.predicate');
  list(
    input.acceptance.evidenceSources,
    'job.acceptance.evidenceSources',
    id,
    1
  );
  rollback(input.rollback, 'job.rollback');
  object(
    input.chronicle,
    ['eligible', 'rights', 'scope', 'expiresAt'],
    ['eligible', 'rights', 'scope', 'expiresAt'],
    'job.chronicle'
  );
  bool(input.chronicle.eligible, 'job.chronicle.eligible');
  text(input.chronicle.rights, 'job.chronicle.rights');
  text(input.chronicle.scope, 'job.chronicle.scope');
  date(input.chronicle.expiresAt, 'job.chronicle.expiresAt');
  if ('sealed' in input) bool(input.sealed, 'job.sealed');
  if ('digest' in input && !/^sha256:[a-f0-9]{64}$/.test(input.digest))
    fail('job.digest', 'expected SHA-256 digest');
  if ('signatureStatus' in input)
    choice(
      input.signatureStatus,
      ['UNSIGNED_COMMITMENT', 'FIXTURE_SIGNED', 'AUTHORIZED_SIGNATURE'],
      'job.signatureStatus'
    );
  return cloneJson(input);
}

export function validateGraph(input) {
  json(input);
  object(
    input,
    [
      'schemaVersion',
      'kind',
      'graphId',
      'missionId',
      'version',
      'nodes',
      'edges',
      'authorityCreated',
      'digest',
    ],
    [
      'schemaVersion',
      'kind',
      'graphId',
      'missionId',
      'version',
      'nodes',
      'edges',
      'authorityCreated',
    ],
    'graph'
  );
  requireCondition(
    input.schemaVersion === SCHEMA_VERSION,
    'SCHEMA_VERSION_UNSUPPORTED',
    'Unsupported graph schema version'
  );
  choice(input.kind, ['JobGraph'], 'graph.kind');
  for (const key of ['graphId', 'missionId', 'version'])
    id(input[key], `graph.${key}`);
  list(input.nodes, 'graph.nodes', validateWorkOrder, 1, 256);
  unique(
    input.nodes.map((node) => node.jobId),
    'graph.nodes'
  );
  list(
    input.edges,
    'graph.edges',
    (edge, path) => {
      object(edge, ['from', 'to', 'kind'], ['from', 'to', 'kind'], path);
      id(edge.from, `${path}.from`);
      id(edge.to, `${path}.to`);
      choice(edge.kind, EDGE_KINDS, `${path}.kind`);
    },
    0,
    2048
  );
  choice(input.authorityCreated, ['NONE'], 'graph.authorityCreated');
  return cloneJson(input);
}

const FORWARD = {
  DRAFT: 'UNDERWRITTEN',
  UNDERWRITTEN: 'AUTHORIZED',
  AUTHORIZED: 'EXECUTING',
  EXECUTING: 'VERIFIED',
  VERIFIED: 'ACCEPTED',
  ACCEPTED: 'CHRONICLE_ELIGIBLE',
};
// Pure reducer: context must originate in a trusted runtime, never request JSON.
export function transitionJob(current, event, context = {}) {
  const job = validateWorkOrder(current);
  json(event);
  object(
    event,
    [
      'eventId',
      'expectedState',
      'to',
      'actor',
      'timestamp',
      'evidence',
      'reason',
    ],
    [
      'eventId',
      'expectedState',
      'to',
      'actor',
      'timestamp',
      'evidence',
      'reason',
    ],
    'event'
  );
  id(event.eventId, 'event.eventId');
  id(event.actor, 'event.actor');
  date(event.timestamp, 'event.timestamp');
  text(event.reason, 'event.reason');
  list(event.evidence, 'event.evidence', id, 1);
  requireCondition(
    event.expectedState === job.state,
    'STATE_CONFLICT',
    'The job changed; reload before retrying'
  );
  const exceptional = [
    'REFUSED',
    'FAILED',
    'TIMED_OUT',
    'REPAIR_REQUIRED',
    'ROLLED_BACK',
  ];
  requireCondition(
    FORWARD[job.state] === event.to ||
      (exceptional.includes(event.to) &&
        !['CHRONICLE_ELIGIBLE', ...exceptional].includes(job.state)),
    'TRANSITION_FORBIDDEN',
    'This job transition is not permitted'
  );
  const owner =
    event.to === 'VERIFIED'
      ? job.verifier.identity
      : ['ACCEPTED', 'CHRONICLE_ELIGIBLE'].includes(event.to)
      ? job.acceptance.owner
      : event.to === 'EXECUTING'
      ? job.actor
      : job.principal;
  requireCondition(
    event.actor === owner,
    'ROLE_CONFLICT',
    'The actor cannot authorize this transition'
  );
  if (['AUTHORIZED', 'EXECUTING'].includes(event.to)) {
    requireCondition(
      job.sealed === true && !!job.digest,
      'JOB_UNSEALED',
      'Seal the exact work order before authorization'
    );
    requireCondition(
      context.sealValid === true,
      'JOB_SEAL_UNVERIFIED',
      'The runtime must cryptographically verify the immutable work-order seal'
    );
    requireCondition(
      Date.parse(event.timestamp) < Date.parse(job.expiresAt),
      'JOB_EXPIRED',
      'The work order has expired'
    );
    requireCondition(
      context.preconditionsValid === true,
      'PRECONDITION_UNAVAILABLE',
      'Rights, dependencies and budget must be validated by the runtime'
    );
  }
  if (event.to === 'VERIFIED')
    requireCondition(
      context.verifierVerdict === 'PASS' && context.receiptValid === true,
      'VERIFICATION_REQUIRED',
      'A valid receipt and passing independent verdict are required'
    );
  if (event.to === 'ACCEPTED')
    requireCondition(
      context.acceptanceSatisfied === true,
      'ACCEPTANCE_CRITERIA_UNMET',
      'The runtime must verify the frozen deliverable acceptance predicate'
    );
  if (event.to === 'CHRONICLE_ELIGIBLE')
    requireCondition(
      job.chronicle.eligible && context.rightsCurrent === true,
      'CHRONICLE_INELIGIBLE',
      'Current reuse rights are required'
    );
  return { ...job, state: event.to };
}
