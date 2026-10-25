// SPDX-License-Identifier: Apache-2.0
// Exact extractive clauses; structural coverage is not truth or reader understanding.
export const SCHEMA = 'source-document/v1';
export const METHODS = ['lead-order', 'weighted-without-dependencies', 'audit-after-draft', 'dependency-graph-before-compression', 'unrestricted-exhaustive'];
export const DEFAULT_DOCUMENT = {
  schema_version: 1, schema: SCHEMA,
  title: 'Evidence and argument: an authored public worked example',
  source_url: 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0',
  public_non_personal: true,
  claims: [
    { schema_version: 1, id: 'C1', text: 'A cryptographic hash binds a record to particular bytes.', weight: 2, depends_on: [], provenance: 'Authored public fixture, clause 1' },
    { schema_version: 1, id: 'C2', text: 'Binding bytes does not establish that the record is true.', weight: 3, depends_on: ['C1'], provenance: 'Authored public fixture, clause 2' },
    { schema_version: 1, id: 'C3', text: 'An independent reviewer must inspect the evidence and the process that produced it.', weight: 5, depends_on: ['C2'], provenance: 'Authored public fixture, clause 3' },
    { schema_version: 1, id: 'C4', text: 'A source summary should preserve the premises needed by each selected conclusion.', weight: 3, depends_on: [], provenance: 'Authored public fixture, clause 4' },
    { schema_version: 1, id: 'C5', text: 'If a summary omits a required premise, its selected conclusion may be unsupported within the summary.', weight: 4, depends_on: ['C4'], provenance: 'Authored public fixture, clause 5' },
    { schema_version: 1, id: 'C6', text: 'A dependency graph can identify which source clauses must accompany a selected conclusion.', weight: 5, depends_on: ['C4', 'C5'], provenance: 'Authored public fixture, clause 6' }
  ]
};
const clone = value => JSON.parse(JSON.stringify(value));
const fieldsMatch = (value, fields) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === fields.sort().join('|');
export function validateDocument(value) {
  if (!fieldsMatch(value, ['schema_version','schema','title','source_url','public_non_personal','claims']) || value.schema_version !== 1 || value.schema !== SCHEMA || value.public_non_personal !== true) throw Error('A public, non-personal source-document/v1 is required.');
  if (typeof value.title !== 'string' || !value.title.trim() || value.title.length > 500) throw Error('Give the source a title of at most 500 characters.');
  if (typeof value.source_url !== 'string' || !value.source_url || value.source_url.length > 2000) throw Error('Source URL must be text of at most 2000 characters.');
  const url = new URL(value.source_url);
  if (url.protocol !== 'https:' || !url.hostname || url.username || url.password || url.hash) throw Error('Use a public HTTPS source URL without credentials or a fragment.');
  if (!Array.isArray(value.claims) || value.claims.length < 1 || value.claims.length > 12) throw Error('Use between 1 and 12 source clauses.');
  const ids = new Set();
  for (const c of value.claims) {
    if (!fieldsMatch(c, ['schema_version','id','text','weight','depends_on','provenance']) || c.schema_version !== 1 || typeof c.id !== 'string' || !/^[A-Za-z0-9_-]{1,40}$/.test(c.id) || ids.has(c.id)) throw Error('Clause IDs must be unique, short names.');
    ids.add(c.id);
    if (typeof c.text !== 'string' || !c.text.trim() || c.text.length > 1500) throw Error('Each source clause needs 1–1500 characters.');
    if (!Number.isSafeInteger(c.weight) || c.weight < 1 || c.weight > 1000) throw Error('Clause importance must be an integer from 1 to 1000.');
    if (!Array.isArray(c.depends_on) || c.depends_on.length > 12 || c.depends_on.some(id => typeof id !== 'string') || new Set(c.depends_on).size !== c.depends_on.length) throw Error('List each prerequisite ID once.');
    if (typeof c.provenance !== 'string' || !c.provenance || c.provenance.length > 2000) throw Error('Each clause needs a source reference.');
  }
  const byId = new Map(value.claims.map(c => [c.id, c]));
  const visiting = new Set(), done = new Set();
  function visit(id) {
    if (visiting.has(id)) throw Error('The dependency graph contains a cycle.');
    if (done.has(id)) return;
    visiting.add(id);
    for (const dependency of byId.get(id).depends_on) {
      if (!ids.has(dependency)) throw Error('A prerequisite refers to an unknown clause.');
      visit(dependency);
    }
    visiting.delete(id); done.add(id);
  }
  for (const id of ids) visit(id);
  return clone(value);
}
export function parseSnippet(text, { title = 'My public source', source_url = 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0' } = {}) {
  if (typeof text !== 'string' || text.length > 16000) throw Error('Source text is limited to 16000 characters.');
  const clauses = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  return validateDocument({ schema_version: 1, schema: SCHEMA, title, source_url, public_non_personal: true,
    claims: clauses.map((text, i) => ({ schema_version: 1, id: `C${i + 1}`, text, weight: 1, depends_on: [], provenance: `User-supplied source, line ${i + 1}` })) });
}
function closure(document, id, seen = new Set()) {
  if (seen.has(id)) return seen;
  seen.add(id);
  for (const dependency of document.claims.find(c => c.id === id).depends_on) closure(document, dependency, seen);
  return seen;
}
export function evaluate(document, selectedIds) {
  const selected = new Set(selectedIds), supported = [], missing = [];
  for (const c of document.claims.filter(c => selected.has(c.id))) {
    const needed = [...closure(document, c.id)].filter(id => !selected.has(id));
    if (needed.length) missing.push({ id: c.id, missing: needed }); else supported.push(c.id);
  }
  return { structural_score: document.claims.filter(c => supported.includes(c.id)).reduce((n, c) => n + c.weight, 0),
    selected: document.claims.filter(c => selected.has(c.id)).map(c => c.id), supported, missing,
    exact_source_clauses: document.claims.filter(c => selected.has(c.id)).map(c => ({ id: c.id, text: c.text, provenance: c.provenance })) };
}
function better(candidate, incumbent) {
  if (!incumbent || candidate.structural_score !== incumbent.structural_score) return !incumbent || candidate.structural_score > incumbent.structural_score;
  if (candidate.selected.length !== incumbent.selected.length) return candidate.selected.length < incumbent.selected.length;
  return candidate.selected.join(',') < incumbent.selected.join(',');
}
export function runComparison(input, maxClauses = 3) {
  const document = validateDocument(input);
  if (!Number.isSafeInteger(maxClauses) || maxClauses < 1 || maxClauses > 3) throw Error('The fixed-summary charter allows one to three clauses.');
  const claims = document.claims, max = Math.min(maxClauses, claims.length);
  const rank = [...claims].sort((a, b) => b.weight - a.weight || claims.indexOf(a) - claims.indexOf(b));
  const lead = evaluate(document, claims.slice(0, max).map(c => c.id));
  const weighted = evaluate(document, rank.slice(0, max).map(c => c.id));
  let repaired = new Set(weighted.selected);
  for (const id of [...repaired]) if ([...closure(document, id)].some(dep => !repaired.has(dep))) repaired.delete(id);
  for (const c of rank) {
    const proposed = new Set([...repaired, ...closure(document, c.id)]);
    if (proposed.size <= max) repaired = proposed;
  }
  const audited = evaluate(document, [...repaired]);
  let graph, unrestricted, examined = 0;
  for (let mask = 0; mask < 2 ** claims.length; mask++) {
    const ids = claims.filter((_, index) => mask & 2 ** index).map(c => c.id);
    if (ids.length > max) continue;
    examined++;
    const scored = evaluate(document, ids);
    if (better(scored, unrestricted)) unrestricted = scored;
    if (!scored.missing.length && better(scored, graph)) graph = scored;
  }
  return { schema_version: 1, schema: 'source-comparison/v1', document,
    charter: { purpose: 'Fixed extractive summary', max_clauses: maxClauses, permissions: ['local-computation'], budget: { model_calls: 0, network_calls: 0, currency_spend: 0 } },
    instrument: { version: 'structural-coverage/v1', calibrated: false, scope: 'User-audited source-clause dependency coverage only; not truth, fidelity beyond the annotation, or reader understanding.' },
    methods: METHODS.map((method, i) => ({ method, ...[lead, weighted, audited, graph, unrestricted][i] })),
    costs: { subsets_examined: examined, bound: 2 ** claims.length, model_calls: 0, network_calls: 0, currency_spend: 0, human_review_minutes: null, setup_minutes: null, maintenance_minutes: null },
    outcome: { status: graph.structural_score > lead.structural_score ? 'structural-improvement-only' : 'no-structural-advantage-over-incumbent', incumbent_retained: true, independent_review: 'pending', certified_ceiling_escape: false, unrestricted_matches: graph.structural_score === unrestricted.structural_score },
    reuse: { prerequisites: ['Public non-personal text', 'A human-audited acyclic prerequisite graph', 'Unchanged fixed-summary charter and structural instrument'], failure_cases: ['Incorrect or incomplete dependencies', 'Importance weights do not reflect the purpose', 'A useful summary needs paraphrase or broader context'], retirement_triggers: ['Source, charter, graph or instrument changes', 'Independent review finds unsupported understanding or accuracy claims'], operating_authority: 'none' } };
}

export function nativeDiscoveryRequest(input, campaignId) {
  const document = validateDocument(input);
  if (typeof campaignId !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(campaignId)) throw Error('A canonical UUID v4 campaign identity is required.');
  return { schema_version: 1, campaign_id: campaignId,
    charter: { schema_version: 1, schema: 'intent-charter/v1',
      purpose: 'Produce a concise source-grounded fixed summary of the supplied public source.',
      population: 'Public source argument clauses; reader understanding is unmeasured.',
      outcomes: ['Three or fewer exact supplied source clauses', 'Make prerequisite qualifications inspectable'],
      constraints: ['Public non-personal input only', 'No paid provider or external execution', 'Preserve the fixed summary artifact'],
      permitted_actions: ['read-public-source', 'construct-bounded', 'evaluate-local', 'write-artifact'],
      publicOnly: true, budgets: { schema_version: 1, search_units: 100000, execution_units: 100000, money_minor: 0, USDCBaseUnits: '0', AGIALPHABaseUnits: '0' },
      payment_route: 'none', artifact: 'fixed-summary', max_clauses: 3 },
    development: [document], operator_ids: ['representation', 'production', 'complementary'], max_candidates: 8,
    configuration: { origin: 'public-source-browser/v1' } };
}
