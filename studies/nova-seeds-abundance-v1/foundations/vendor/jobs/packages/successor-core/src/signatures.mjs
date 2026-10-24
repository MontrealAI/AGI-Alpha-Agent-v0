import {
  generateKeyPairSync,
  createPublicKey,
  createHash,
  sign,
  verify,
} from 'node:crypto';
import { canonicalize, digestObject } from './integrity.mjs';

export class AssuranceError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'AssuranceError';
    this.code = code;
    this.details = details;
  }
}
export function requireAssurance(condition, code, message, details) {
  if (!condition) throw new AssuranceError(code, message, details);
}
export function timestamp(value, name = 'timestamp') {
  const n = typeof value === 'number' ? value : Date.parse(value);
  requireAssurance(
    Number.isSafeInteger(n) &&
      Math.abs(n) <= 8640000000000000 &&
      (typeof value === 'number' ||
        (typeof value === 'string' &&
          /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value) &&
          new Date(n).toISOString() === value)),
    'INVALID_TIME',
    `${name} must be canonical UTC ISO milliseconds or safe integer epoch milliseconds`
  );
  return n;
}
export function digestShape(value) {
  return typeof value === 'string' && /^sha256:[0-9a-f]{64}$/.test(value);
}

// This identity is deliberately fixture-only by default. Production public keys are
// provisioned independently, with private keys held outside the candidate process.
export function generateSigningIdentity({
  keyId,
  organizationId,
  custodyId,
  fixture = true,
} = {}) {
  requireAssurance(
    keyId && organizationId && custodyId,
    'INVALID_IDENTITY',
    'Identity needs key, organization and custody identifiers'
  );
  const keys = generateKeyPairSync('ed25519');
  return {
    keyId,
    organizationId,
    custodyId,
    fixture,
    publicKey: keys.publicKey
      .export({ type: 'spki', format: 'pem' })
      .toString(),
    privateKey: keys.privateKey
      .export({ type: 'pkcs8', format: 'pem' })
      .toString(),
  };
}

export function trustKey(
  identity,
  {
    roles,
    context,
    notBefore,
    expiresAt,
    maxIndependence = 'I0',
    principals = [],
  } = {}
) {
  requireAssurance(
    Array.isArray(roles) && roles.length && context && notBefore && expiresAt,
    'INVALID_TRUST_ROOT',
    'Trust roots require roles, exact context and validity'
  );
  const { keyId, publicKey, organizationId, custodyId, fixture } = identity;
  return {
    keyId,
    publicKey,
    organizationId,
    custodyId,
    fixture,
    roles,
    context,
    notBefore,
    expiresAt,
    maxIndependence,
    principals,
  };
}

export async function signPayload(
  payload,
  { identity, purpose, context, issuedAt = new Date().toISOString() } = {}
) {
  requireAssurance(
    identity?.privateKey && purpose && context,
    'INVALID_SIGNATURE_INPUT',
    'Signer, purpose and context are required'
  );
  validateContext(context);
  timestamp(issuedAt, 'issuedAt');
  requireAssurance(
    !identity.fixture || context.mode === 'fixture',
    'FIXTURE_LIVE_DENIED',
    'Fixture credentials cannot sign live records'
  );
  const body = {
    schemaVersion: 1,
    keyId: identity.keyId,
    purpose,
    context,
    issuedAt,
    payload,
  };
  const signature = sign(
    null,
    Buffer.from(canonicalize(body), 'utf8'),
    identity.privateKey
  ).toString('base64');
  return { ...body, signature };
}

export function validateContext(context) {
  requireAssurance(
    context &&
      Object.keys(context).sort().join(',') ===
        'environment,institutionId,missionId,mode',
    'INVALID_CONTEXT',
    'Signature context must bind institution, mission, environment and mode'
  );
  for (const key of ['institutionId', 'missionId', 'environment'])
    requireAssurance(
      typeof context[key] === 'string' &&
        context[key].length > 0 &&
        context[key].length <= 200,
      'INVALID_CONTEXT',
      `Invalid ${key}`
    );
  requireAssurance(
    ['fixture', 'live'].includes(context.mode),
    'INVALID_CONTEXT',
    'Unsupported signature mode'
  );
}

export async function verifySignedPayload(
  record,
  { trustStore, purpose, role, context, now = Date.now() } = {}
) {
  requireAssurance(
    record &&
      Object.keys(record).sort().join(',') ===
        'context,issuedAt,keyId,payload,purpose,schemaVersion,signature' &&
      record.schemaVersion === 1,
    'INVALID_SIGNATURE_RECORD',
    'Unsupported signed record or unexpected fields'
  );
  validateContext(record.context);
  requireAssurance(
    record.purpose === purpose,
    'SIGNATURE_PURPOSE_MISMATCH',
    'Signature cannot be reused for another purpose'
  );
  requireAssurance(
    context && canonicalize(record.context) === canonicalize(context),
    'CONTEXT_MISMATCH',
    'Signature context does not match this institution, mission, environment or mode'
  );
  requireAssurance(
    trustStore?.schemaVersion === 1 && Array.isArray(trustStore.keys),
    'UNCONFIGURED_TRUST',
    'An operator-provisioned trust store is required'
  );
  const matches = trustStore.keys.filter((k) => k.keyId === record.keyId);
  requireAssurance(
    matches.length === 1,
    'UNKNOWN_SIGNER',
    'Signer is unknown or ambiguous'
  );
  const key = matches[0];
  requireAssurance(
    Array.isArray(key.roles) && key.roles.includes(role),
    'WRONG_SIGNER_ROLE',
    `Signer is not authorized as ${role}`
  );
  requireAssurance(
    key.organizationId && key.custodyId,
    'INVALID_TRUST_ROOT',
    'Trust root lacks accountable organization or custody'
  );
  requireAssurance(
    canonicalize(key.context) === canonicalize(context),
    'TRUST_SCOPE_MISMATCH',
    'Trust key is not provisioned for this exact context'
  );
  requireAssurance(
    !(key.fixture && context.mode !== 'fixture'),
    'FIXTURE_LIVE_DENIED',
    'Fixture trust roots cannot authorize live activity'
  );
  const current = timestamp(now);
  const issued = timestamp(record.issuedAt, 'issuedAt');
  requireAssurance(
    issued <= current &&
      issued >= timestamp(key.notBefore) &&
      current < timestamp(key.expiresAt),
    'SIGNER_EXPIRED',
    'Signer or record is outside its validity window'
  );
  requireAssurance(
    !key.revokedAt || current < timestamp(key.revokedAt),
    'SIGNER_REVOKED',
    'Signer has been revoked'
  );
  requireAssurance(
    typeof record.signature === 'string' &&
      /^[A-Za-z0-9+/]{86}==$/.test(record.signature),
    'INVALID_SIGNATURE',
    'Malformed Ed25519 signature'
  );
  const { signature, ...body } = record;
  let valid = false;
  try {
    const publicKey = createPublicKey(key.publicKey);
    valid =
      publicKey.asymmetricKeyType === 'ed25519' &&
      verify(
        null,
        Buffer.from(canonicalize(body)),
        publicKey,
        Buffer.from(signature, 'base64')
      );
  } catch {
    /* do not expose key material */
  }
  requireAssurance(
    valid,
    'INVALID_SIGNATURE',
    'Signed content integrity failed'
  );
  const fingerprint = createHash('sha256')
    .update(
      createPublicKey(key.publicKey).export({ type: 'spki', format: 'der' })
    )
    .digest('hex');
  for (const other of trustStore.keys) {
    let same = false;
    try {
      same =
        createHash('sha256')
          .update(
            createPublicKey(other.publicKey).export({
              type: 'spki',
              format: 'der',
            })
          )
          .digest('hex') === fingerprint;
    } catch {
      /* unrelated invalid keys cannot establish identity */
    }
    requireAssurance(
      !same ||
        (other.organizationId === key.organizationId &&
          other.custodyId === key.custodyId),
      'ROLE_CONFLICT',
      'The same signing credential cannot be relabeled as independent custody'
    );
  }
  return {
    payload: structuredClone(record.payload),
    key: { ...key, publicKey: undefined, fingerprint },
    digest: await digestObject('successor-signed-record-v1', record),
  };
}
