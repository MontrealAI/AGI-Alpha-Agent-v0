/* Independent structural check using the installed Node runtime's own lookup
 * ancestry. This reads JSON only: no locked package is installed or executed. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const zlib = require('node:zlib');
const baseDir = __dirname;
const audit = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(baseDir, 'graph_audit.json.gz'))).toString('utf8'));
const graph = JSON.parse(fs.readFileSync(path.join(baseDir, 'case.json'), 'utf8'));
const projects = [['alpha-web', 'alpha-web-package-lock.json'], ['manager', 'manager-package-lock.json']];
const records = [...audit.resolved_dependency_records, ...audit.unresolved_dependency_records];
const key = row => JSON.stringify([row.project, row.from_lock_path, row.kind, row.requested_name || null]);
const byKey = new Map(records.map(row => [key(row), row]));
if (records.length !== byKey.size) throw Error('duplicate audit declarations');
const checked = new Set();
const expectedEdges = new Set();
let resolved = 0, unresolved = 0, links = 0;
const nid = (project, location) => project + '::' + (location || '<root>');
const check = (project, from, kind, name, selected, metadata) => {
  const recordKey = JSON.stringify([project, from, kind, name]);
  const row = byKey.get(recordKey);
  if (!row || row.resolved_path !== selected) throw Error('resolution mismatch: ' + recordKey);
  if (row.dependent !== nid(project, from) || row.dependency !== (selected === null ? null : nid(project, selected))) throw Error('edge direction/identity mismatch: ' + recordKey);
  if (kind === 'package-declaration') {
    const fields = ['dependencies', 'optionalDependencies', 'peerDependencies', ...(!from ? ['devDependencies'] : [])];
    const constraints = Object.fromEntries(fields.filter(field => Object.hasOwn(metadata[field] || {}, name)).map(field => [field, metadata[field][name]]));
    const sorted = object => JSON.stringify(Object.keys(object).sort().map(key => [key, object[key]]));
    if (sorted(row.constraints) !== sorted(constraints)) throw Error('source declaration changed: ' + recordKey);
    const peerOptional = !!metadata.peerDependenciesMeta?.[name]?.optional;
    const optional = Object.hasOwn(constraints, 'optionalDependencies') || (Object.keys(constraints).length === 1 && Object.hasOwn(constraints, 'peerDependencies') && peerOptional);
    if (row.optional !== optional || row.peer_optional !== peerOptional) throw Error('optionality mismatch: ' + recordKey);
  } else if (row.declared_target !== metadata.resolved) throw Error('link target mismatch');
  checked.add(recordKey);
  if (selected === null) unresolved++;
  else { resolved++; expectedEdges.add(JSON.stringify([nid(project, selected), nid(project, from)])); }
};
for (const [project, filename] of projects) {
  const packages = JSON.parse(fs.readFileSync(path.join(baseDir, 'raw', filename), 'utf8')).packages;
  const root = '/bloom-public-fixture/' + project;
  for (const [from, metadata] of Object.entries(packages)) {
    if (metadata.link) {
      links++;
      check(project, from, 'link', null, Object.hasOwn(packages, metadata.resolved) ? metadata.resolved : null, metadata);
      continue;
    }
    const fields = ['dependencies', 'optionalDependencies', 'peerDependencies', ...(!from ? ['devDependencies'] : [])];
    const names = new Set(fields.flatMap(field => Object.keys(metadata[field] || {})));
    // _nodeModulePaths is used as a local verification reference, not a public
    // production interface. The fixture excludes paths outside the lock root.
    const ancestry = Module._nodeModulePaths(path.posix.join(root, from)).filter(candidate => candidate.startsWith(root + '/'));
    for (const name of names) {
      const locations = ancestry.map(directory => path.posix.relative(root, path.posix.join(directory, name)));
      const selected = locations.find(candidate => Object.hasOwn(packages, candidate)) ?? null;
      check(project, from, 'package-declaration', name, selected, metadata);
    }
  }
}
if (checked.size !== byKey.size) throw Error('audit contains undeclared source entries');
const actualEdges = new Set(graph.edges.map(edge => JSON.stringify(edge)));
if (actualEdges.size !== expectedEdges.size || [...expectedEdges].some(edge => !actualEdges.has(edge))) throw Error('case edge set differs from native-ancestry source reconstruction');
console.log(JSON.stringify({status:'PASS', node:process.version, checked_records:checked.size, resolved_records:resolved, unresolved_records:unresolved, link_records:links, edges:expectedEdges.size, basis:'Native Node _nodeModulePaths ancestry over exact local lock maps; package scripts and imports are not executed.'}));
