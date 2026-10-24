// SPDX-License-Identifier: Apache-2.0
import { LIMITS, invariant, exactKeys, label, safeInteger, deepFreeze, optionalMeter } from './protocol.mjs';

export const REPRESENTATION_VERSION = 'tae/dag-representation-v1';
export const STRATEGIES = Object.freeze(['kahn-v1', 'dfs-v1']);

export function parseGraph(graph, { meter } = {}) {
  meter = optionalMeter(meter);
  exactKeys(graph, ['nodes', 'edges']);
  invariant(Array.isArray(graph.nodes) && graph.nodes.length > 0 && graph.nodes.length <= LIMITS.nodes, 'NODE_LIMIT', `Graph requires 1..${LIMITS.nodes} nodes.`);
  invariant(Array.isArray(graph.edges) && graph.edges.length <= LIMITS.edges, 'EDGE_LIMIT', `Graph allows at most ${LIMITS.edges} edges.`);
  const nodes = graph.nodes.map(node => { meter.tick('parse-node'); return label(node, 'node'); });
  invariant(new Set(nodes).size === nodes.length, 'DUPLICATE_NODE', 'Nodes must be unique.');
  nodes.sort((a, b) => { meter.tick('compare-node'); return a < b ? -1 : a > b ? 1 : 0; });
  const known = new Set(nodes);
  const edges = graph.edges.map(edge => {
    meter.tick('parse-edge'); exactKeys(edge, ['from', 'to', 'weight']);
    invariant(known.has(edge.from) && known.has(edge.to), 'UNKNOWN_ENDPOINT', 'Every edge endpoint must be a declared node.');
    safeInteger(edge.weight, 'edge weight', { positive: true });
    return { from: edge.from, to: edge.to, weight: edge.weight };
  });
  edges.sort((a, b) => { meter.tick('compare-edge'); return a.from < b.from ? -1 : a.from > b.from ? 1 : a.to < b.to ? -1 : a.to > b.to ? 1 : a.weight < b.weight ? -1 : a.weight > b.weight ? 1 : 0; });
  return deepFreeze({ schema: 'tae/normalized-graph-v1', nodes, edges });
}

export function topologicalOrder(normalized, { meter, strategy = 'kahn-v1' } = {}) {
  meter = optionalMeter(meter);
  invariant(STRATEGIES.includes(strategy), 'UNKNOWN_MODEL', 'Only the declared symbolic Kahn and DFS strategies are supported.');
  invariant(normalized?.schema === 'tae/normalized-graph-v1', 'INVALID_REPRESENTATION', 'topologicalOrder requires parseGraph output.');
  const index = new Map(normalized.nodes.map((node, i) => { meter.tick('index-node'); return [node, i]; }));
  const adjacency = normalized.nodes.map(() => []); const indegree = normalized.nodes.map(() => 0);
  for (const edge of normalized.edges) { meter.tick('index-edge'); adjacency[index.get(edge.from)].push(index.get(edge.to)); indegree[index.get(edge.to)]++; }
  const order = [];
  if (strategy === 'kahn-v1') {
    const queue = [];
    for (let i = 0; i < indegree.length; i++) { meter.tick('scan-indegree'); if (indegree[i] === 0) queue.push(i); }
    for (let head = 0; head < queue.length; head++) { const node = queue[head]; meter.tick('visit-node'); order.push(normalized.nodes[node]); for (const child of adjacency[node]) { meter.tick('visit-edge'); indegree[child]--; if (indegree[child] === 0) queue.push(child); } }
    invariant(order.length === normalized.nodes.length, 'CYCLIC_GRAPH', 'A directed cycle prevents this DAG capability from executing.');
  } else {
    const colors = normalized.nodes.map(() => 0);
    function visit(node) { meter.tick('visit-node'); invariant(colors[node] !== 1, 'CYCLIC_GRAPH', 'A directed cycle prevents this DAG capability from executing.'); if (colors[node] === 2) return; colors[node] = 1; for (const child of adjacency[node]) { meter.tick('visit-edge'); visit(child); } colors[node] = 2; order.push(normalized.nodes[node]); }
    for (let i = 0; i < colors.length; i++) if (!colors[i]) visit(i);
    order.reverse();
  }
  return deepFreeze(order);
}

export function buildRepresentation(graph, { meter, strategy = 'kahn-v1' } = {}) {
  meter = optionalMeter(meter);
  const normalized = parseGraph(graph, { meter });
  const order = topologicalOrder(normalized, { meter, strategy });
  const index = new Map(normalized.nodes.map((node, i) => { meter.tick('index-node'); return [node, i]; }));
  const adjacency = normalized.nodes.map(() => []);
  for (const edge of normalized.edges) { meter.tick('compile-edge'); adjacency[index.get(edge.from)].push({ to: index.get(edge.to), weight: edge.weight }); }
  return deepFreeze({ schema: REPRESENTATION_VERSION, nodes: normalized.nodes, edges: normalized.edges, order, adjacency, strategy });
}

export function bindQuery(representation, query, { meter } = {}) {
  meter = optionalMeter(meter);
  invariant(representation?.schema === REPRESENTATION_VERSION, 'INVALID_REPRESENTATION', 'A compiled DAG representation is required.');
  exactKeys(query, ['seeds', 'targets']);
  invariant(Array.isArray(query.seeds) && query.seeds.length > 0 && query.seeds.length <= LIMITS.nodes, 'SEED_LIMIT', 'Seeds must be a nonempty bounded array.');
  invariant(Array.isArray(query.targets) && query.targets.length > 0 && query.targets.length <= LIMITS.nodes, 'TARGET_LIMIT', 'Targets must be a nonempty bounded array.');
  const known = new Map(representation.nodes.map((node, i) => { meter.tick('query-index-node'); return [node, i]; }));
  const seeds = query.seeds.map(seed => { meter.tick('bind-seed'); exactKeys(seed, ['node', 'amount']); invariant(known.has(seed.node), 'UNKNOWN_SEED', 'Seed node is not in graph.'); safeInteger(seed.amount, 'seed amount', { nonnegative: true }); return { node: seed.node, amount: seed.amount }; });
  const targets = query.targets.map(target => { meter.tick('bind-target'); invariant(known.has(target), 'UNKNOWN_TARGET', 'Target node is not in graph.'); return target; });
  invariant(new Set(targets).size === targets.length, 'DUPLICATE_TARGET', 'Targets must be unique.');
  targets.sort((a, b) => { meter.tick('compare-target'); return a < b ? -1 : a > b ? 1 : 0; });
  return { index: known, seeds, targets };
}
