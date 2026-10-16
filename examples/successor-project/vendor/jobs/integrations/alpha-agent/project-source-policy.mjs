import { canonical, parseBounded } from './vendor/alpha/docs/assets/successor/engine.mjs';

export const SOURCE_SELECTOR_PATH = 'integrations/alpha-agent/project-source-selector.mjs';
export const SOURCE_PATHS = Object.freeze([
  "LICENSE",
  "integrations/alpha-agent/generate-project-source.mjs",
  "integrations/alpha-agent/jobregistry-v2.json",
  "integrations/alpha-agent/project-cli.mjs",
  "integrations/alpha-agent/project-name.mjs",
  "integrations/alpha-agent/project-native-source.mjs",
  "integrations/alpha-agent/project-receipt.cjs",
  "integrations/alpha-agent/project-source-policy.mjs",
  "integrations/alpha-agent/project-transfer.mjs",
  "integrations/alpha-agent/vendor/alpha/LICENSE",
  "integrations/alpha-agent/vendor/alpha/docs/assets/successor/engine.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/alpha-discovery/engine.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/build-successor/model.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/build-successor/vendor/agijobs/LICENSE",
  "integrations/alpha-agent/vendor/alpha/examples/build-successor/vendor/agijobs/compiler.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/build-successor/vendor/agijobs/domain.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/build-successor/vendor/agijobs/integrity.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/build-successor/vendor/agijobs/provenance.json",
  "integrations/alpha-agent/vendor/alpha/examples/build-successor/vendor/agijobs/templates.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/successor-project/engine.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/successor-workbench/engine.mjs",
  "integrations/alpha-agent/vendor/alpha/examples/successor-workbench/mission-record.mjs",
  "integrations/alpha-agent/verify-receipt.cjs",
  "packages/successor-core/src/compiler.mjs",
  "packages/successor-core/src/domain.mjs",
  "packages/successor-core/src/integrity.mjs",
  "packages/successor-core/src/templates.mjs"
]);
export function freezeSource(value) {
  if (value && typeof value === 'object') {
    for (const nested of Object.values(value)) freezeSource(nested);
    Object.freeze(value);
  }
  return value;
}
function fail(ok, code) { if (!ok) throw Object.assign(Error(code), { code }); }
function fields(value, expected) { fail(value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === [...expected].sort().join('|'), 'JOBS_SOURCE_FIELDS'); }
const selectorPolicy = Object.freeze({ path: SOURCE_SELECTOR_PATH, format: 'export-primitive-canonical-json/v1', excludedFromSourceSnapshot: true, reason: 'Generated metadata selecting a previously published immutable code snapshot; excluded to avoid self-reference.' });
export function pendingSourceSelection() {
  return { schema: 'agijobsv0/receiver-source-snapshot/v1', repository: 'MontrealAI/AGIJobsv0', adapterVersion: 'agijobsv0-project-receiver/v1', status: 'pending-source-pin', commit: null, tree: null, selector: selectorPolicy, files: [] };
}
export function readSourceSelection(raw) {
  const value = parseBounded(raw);
  fields(value, ['schema','repository','adapterVersion','status','commit','tree','selector','files']);
  fail(value.schema === 'agijobsv0/receiver-source-snapshot/v1' && value.repository === 'MontrealAI/AGIJobsv0' && value.adapterVersion === 'agijobsv0-project-receiver/v1', 'JOBS_SOURCE_IDENTITY');
  fail(canonical(value.selector) === canonical(selectorPolicy), 'JOBS_SOURCE_SELECTOR_POLICY');
  fail(Array.isArray(value.files), 'JOBS_SOURCE_INVENTORY');
  if (value.status === 'pending-source-pin') {
    fail(value.commit === null && value.tree === null && value.files.length === 0, 'JOBS_SOURCE_PENDING');
  } else {
    fail(value.status === 'pinned' && /^[0-9a-f]{40}$/.test(value.commit) && /^[0-9a-f]{40}$/.test(value.tree), 'JOBS_SOURCE_PIN');
    fail(value.files.length === SOURCE_PATHS.length && value.files.every((file, index) => {
      fields(file, ['path','sha256']);
      return file.path === SOURCE_PATHS[index] && typeof file.sha256 === 'string' && /^[0-9a-f]{64}$/.test(file.sha256);
    }), 'JOBS_SOURCE_INVENTORY');
  }
  return freezeSource(value);
}
export function assertPinnedSelection(value) {
  fail(readSourceSelection(canonical(value)).status === 'pinned', 'JOBS_SOURCE_PIN_REQUIRED');
}
export function renderSourceSelector(value) {
  const checked = readSourceSelection(canonical(value));
  return 'export const RECEIVER_SOURCE_LOCK_JSON = ' + JSON.stringify(canonical(checked)) + ';\n';
}
export function validateSelectorModule(bytes) {
  fail(typeof bytes === 'string', 'JOBS_SOURCE_SELECTOR_BYTES');
  const prefix = 'export const RECEIVER_SOURCE_LOCK_JSON = ', suffix = ';\n';
  fail(bytes.startsWith(prefix) && bytes.endsWith(suffix), 'JOBS_SOURCE_SELECTOR_GRAMMAR');
  let raw;
  try { raw = JSON.parse(bytes.slice(prefix.length, -suffix.length)); } catch { fail(false, 'JOBS_SOURCE_SELECTOR_GRAMMAR'); }
  fail(typeof raw === 'string', 'JOBS_SOURCE_SELECTOR_GRAMMAR');
  const checked = readSourceSelection(raw);
  fail(bytes === renderSourceSelector(checked), 'JOBS_SOURCE_SELECTOR_GRAMMAR');
  return checked;
}
