/** Portable, JSON-only mission knowledge. Import never evaluates programs or restores permissions. */
import { canonicalize, digestObject } from './integrity.mjs';
const VERSION = '1.0.0';
const KINDS = new Set([
  'constitution',
  'program',
  'jobs',
  'evidence',
  'knowledge',
  'negative-knowledge',
  'candidate',
  'proof-history',
  'chronicle',
  'license',
  'replay-recipe',
]);
const RIGHTS = new Set(['owned', 'licensed', 'reference-only']);
const LIMITS = {
  bytes: 16 * 1024 * 1024,
  artifacts: 128,
  depth: 40,
  nodes: 100000,
  chronicle: 2000,
};
const FORBIDDEN =
  /^(?:privateKey|private_key|secret|secrets|password|apiKey|api_key|accessToken|refreshToken|walletSeed|mnemonic|activeAuthority|productionConnection|protectedCases|protectedLabels|scorerSecret|authorization|bearerToken|secretKey|seedPhrase|clientSecret|credentials|token|access_token|refresh_token)$/i;
function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}
function validateData(value, depth = 0, count = { value: 0 }) {
  if (depth > LIMITS.depth || ++count.value > LIMITS.nodes)
    fail('PACK_LIMIT', 'Mission Pack nesting or item limit exceeded.');
  if (
    typeof value === 'string' &&
    /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/.test(value)
  )
    fail(
      'PACK_SECRET',
      'Private signing material is excluded from Mission Packs.'
    );
  if (value && typeof value === 'object')
    for (const [key, child] of Object.entries(value)) {
      if (FORBIDDEN.test(key))
        fail(
          'PACK_SECRET',
          `Forbidden portable field: ${key}. Export historical references, never permissions or credentials.`
        );
      validateData(child, depth + 1, count);
    }
}
function boundedClone(value) {
  const text = canonicalize(value);
  if (new TextEncoder().encode(text).byteLength > LIMITS.bytes)
    fail('PACK_LIMIT', 'Mission Pack exceeds 16 MiB.');
  const plain = JSON.parse(text);
  validateData(plain);
  return plain;
}
function keys(value, allowed) {
  if (
    !value ||
    typeof value !== 'object' ||
    Array.isArray(value) ||
    Object.keys(value).some((key) => !allowed.includes(key))
  )
    fail('PACK_SCHEMA', 'Unknown Mission Pack field or record type.');
}
function safePath(path) {
  if (
    typeof path !== 'string' ||
    path.length > 200 ||
    !/^[a-zA-Z0-9][a-zA-Z0-9_./-]*$/.test(path) ||
    path.split('/').some((part) => part === '..' || part === '.' || !part) ||
    path.includes(':')
  )
    fail(
      'PACK_PATH',
      'Artifact paths must be safe relative identifiers, without traversal or external links.'
    );
}
function artifactRecord(artifact) {
  keys(artifact, ['path', 'kind', 'rights', 'license', 'content', 'digest']);
  safePath(artifact.path);
  if (!KINDS.has(artifact.kind) || !RIGHTS.has(artifact.rights))
    fail('PACK_RIGHTS', 'Unsupported artifact kind or export rights.');
  if (typeof artifact.license !== 'string' || !artifact.license.trim())
    fail(
      'PACK_RIGHTS',
      'Each exported artifact needs a license or rights statement.'
    );
  if (
    artifact.rights === 'reference-only' &&
    (typeof artifact.content !== 'object' ||
      !artifact.content ||
      Object.keys(artifact.content).some(
        (key) => !['digest', 'description', 'unavailable'].includes(key)
      ) ||
      !/^sha256:[0-9a-f]{64}$/.test(artifact.content.digest))
  )
    fail(
      'PACK_RIGHTS',
      'Reference-only content permits a digest, description and unavailability reason, never embedded restricted content.'
    );
  if (!Object.hasOwn(artifact, 'content'))
    fail('PACK_SCHEMA', 'Artifact content is required.');
  return artifact;
}
export async function createMissionPack({
  institutionId,
  missionId,
  artifacts,
  chronicle = [],
  exclusions = [],
}) {
  const body = boundedClone({
    schemaVersion: VERSION,
    kind: 'MissionPack',
    institutionId,
    missionId,
    artifacts,
    chronicle,
    exclusions,
    restorePolicy: 'KNOWLEDGE_ONLY_NO_AUTHORITY',
  });
  body.artifacts = await Promise.all(
    body.artifacts.map(async (artifact) => ({
      ...artifactRecord(artifact),
      digest: await digestObject(
        'successor.pack.artifact.v1',
        artifact.content
      ),
    }))
  );
  const pack = {
    ...body,
    digest: await digestObject('successor.mission-pack.v1', body),
  };
  await verifyMissionPack(pack);
  return pack;
}
export async function verifyMissionPack(input) {
  const pack = boundedClone(input);
  keys(pack, [
    'schemaVersion',
    'kind',
    'institutionId',
    'missionId',
    'artifacts',
    'chronicle',
    'exclusions',
    'restorePolicy',
    'digest',
  ]);
  if (
    pack.schemaVersion !== VERSION ||
    pack.kind !== 'MissionPack' ||
    pack.restorePolicy !== 'KNOWLEDGE_ONLY_NO_AUTHORITY'
  )
    fail('PACK_VERSION', 'Unsupported Mission Pack or restore policy.');
  for (const name of ['institutionId', 'missionId'])
    if (
      typeof pack[name] !== 'string' ||
      !/^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$/.test(pack[name])
    )
      fail('PACK_SCHEMA', `Invalid ${name}.`);
  if (
    !Array.isArray(pack.artifacts) ||
    pack.artifacts.length > LIMITS.artifacts ||
    !Array.isArray(pack.chronicle) ||
    pack.chronicle.length > LIMITS.chronicle ||
    !Array.isArray(pack.exclusions)
  )
    fail('PACK_LIMIT', 'Invalid or excessive artifact/history count.');
  const paths = new Set();
  for (const artifact of pack.artifacts) {
    artifactRecord(artifact);
    if (paths.has(artifact.path)) fail('PACK_PATH', 'Duplicate artifact path.');
    paths.add(artifact.path);
    if (
      artifact.digest !==
      (await digestObject('successor.pack.artifact.v1', artifact.content))
    )
      fail('PACK_DIGEST', `Artifact integrity mismatch: ${artifact.path}.`);
  }
  const { digest, ...body } = pack;
  if (digest !== (await digestObject('successor.mission-pack.v1', body)))
    fail('PACK_DIGEST', 'Mission Pack manifest was changed.');
  return {
    valid: true,
    digest,
    artifactCount: pack.artifacts.length,
    authenticated: false,
    note: 'Digest integrity is not authenticated provenance or proof.',
  };
}
export async function restoreMissionPack(input) {
  await verifyMissionPack(input);
  const pack = boundedClone(input);
  return {
    institutionId: pack.institutionId,
    missionId: pack.missionId,
    artifacts: pack.artifacts,
    chronicle: pack.chronicle,
    historicalProof: pack.artifacts
      .filter((item) => item.kind === 'proof-history')
      .map((item) => ({ ...item, currency: 'historical-unvalidated' })),
    activeAuthority: [],
    proofCurrency: 'absent',
    restored: true,
    packDigest: pack.digest,
    exclusions: pack.exclusions,
    executionEnabled: false,
  };
}
export async function createSuccessor(restored, { id, supplier }) {
  if (
    !restored?.restored ||
    !/^sha256:[0-9a-f]{64}$/.test(restored.packDigest) ||
    typeof id !== 'string' ||
    !id ||
    typeof supplier !== 'string' ||
    !supplier
  )
    fail(
      'SUCCESSOR_INVALID',
      'Restore a verified pack and declare a new candidate identity and supplier.'
    );
  await verifyMissionPack({
    schemaVersion: VERSION,
    kind: 'MissionPack',
    institutionId: restored.institutionId,
    missionId: restored.missionId,
    artifacts: restored.artifacts,
    chronicle: restored.chronicle,
    exclusions: restored.exclusions,
    restorePolicy: 'KNOWLEDGE_ONLY_NO_AUTHORITY',
    digest: restored.packDigest,
  });
  const manifest = {
    schemaVersion: VERSION,
    id,
    institutionId: restored.institutionId,
    missionId: restored.missionId,
    parentPackDigest: restored.packDigest,
    supplier,
    knowledge: restored.artifacts
      .filter((item) =>
        ['knowledge', 'negative-knowledge', 'program'].includes(item.kind)
      )
      .map((item) => ({
        path: item.path,
        digest: item.digest,
        rights: item.rights,
      })),
    status: 'PROPOSED',
    proofCurrency: 'absent',
    authority: [],
  };
  return {
    ...manifest,
    digest: await digestObject('successor.descendant.v1', manifest),
  };
}
export { LIMITS as PACK_LIMITS };
