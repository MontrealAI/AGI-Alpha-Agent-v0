// SPDX-License-Identifier: Apache-2.0
import { loadTaxonomy, saveTaxonomy, proposeSectorNodes } from '@insight-src/taxonomy.ts';
import { loadMemes } from '@insight-src/memeplex.ts';
import { t } from './i18n.ts';
import type { HyperGraph } from '@insight-src/taxonomy.ts';
import type { Archive, InsightRun } from '../archive.ts';

function tokenize(text: string): string[] {
  return text.toLowerCase().split(/[^a-z0-9]+/).filter((t) => t);
}

export interface EvolutionPanel {
  render(): Promise<void>;
}
export function initEvolutionPanel(archive: Archive): EvolutionPanel {
  const panel = document.createElement('div');
  panel.id = 'evolution-panel';
  panel.setAttribute('role', 'region');
  panel.setAttribute('aria-label', 'Evolution');
  Object.assign(panel.style, {
    position: 'fixed',
    bottom: '10px',
    left: '10px',
    background: 'rgba(0,0,0,0.7)',
    color: '#fff',
    padding: '8px',
    fontSize: '12px',
    zIndex: 1000,
    maxHeight: '40vh',
    overflowY: 'auto',
  });
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '200');
  svg.setAttribute('height', '100');
  const tree = document.createElement('div');
  tree.id = 'taxonomy-tree';
  const table = document.createElement('table');
  const header = document.createElement('tr');
  const headCells: [string, string][] = [
    ['seed', t('seed')],
    ['score', t('score')],
    ['novelty', t('novelty')],
    ['timestamp', t('time')],
  ];
  for (const [k, label] of headCells) {
    const th = document.createElement('th');
    th.dataset.k = k;
    th.textContent = label;
    header.appendChild(th);
  }
  header.appendChild(document.createElement('th'));
  table.appendChild(header);
  const memeDiv = document.createElement('div');
  memeDiv.id = 'meme-cloud';
  panel.appendChild(tree);
  panel.appendChild(svg);
  panel.appendChild(table);
  panel.appendChild(memeDiv);
  document.body.appendChild(panel);

  type RunSortKey = 'seed' | 'score' | 'novelty' | 'timestamp';
  let sortKey: RunSortKey = 'timestamp';
  let desc = true;
  let taxonomy: HyperGraph | null = null;
  let selectedNode: string | null = null;
  header
    .querySelectorAll<HTMLTableHeaderCellElement>('th[data-k]')
    .forEach((th) => {
      th.style.cursor = 'pointer';
      th.onclick = () => {
        const k = (th.dataset.k ?? 'timestamp') as RunSortKey;
        if (sortKey ==== k) desc = !desc;
        else {
          sortKey = k;
          desc = true;
        }
        render();
      };
    });

  function respawn(seed: number): void {
    const q = new URLSearchParams(window.location.hash.replace(/^#\/?/, ''));
    q.set('s', String(seed));
    window.location.hash = '#/' + q.toString();
  }

  function drawTree(runs: InsightRun[]): void {
    while (svg.firstChild) svg.firstChild.remove();
    const pos = new Map<string, { x: number; y: number }>();
    runs.forEach((r, i) => {
      const x = 20 + i * 20;
      const y = 20;
      pos.set(r.id, { x, y });
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', String(x));
      c.setAttribute('cy', String(y));
      c.setAttribute('r', '4');
      c.setAttribute('fill', 'white');
      svg.appendChild(c);
    });
    runs.forEach((r) => {
      const child = pos.get(r.id);
      if (!child) return;
      for (const p of r.parents || []) {
        const parent = pos.get(p);
        if (!parent) continue;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', String(parent.x));
        line.setAttribute('y1', String(parent.y));
        line.setAttribute('x2', String(child.x));
        line.setAttribute('y2', String(child.y));
        line.setAttribute('stroke', 'white');
        svg.appendChild(line);
      }
    });
  }

  async function renderTaxonomy(): Promise<void> {
    taxonomy = await loadTaxonomy();
    const runs = await archive.list();
    await proposeSectorNodes(
      runs.map((r) => ({ keywords: r.params?.keywords || tokenize(r.params?.sector || '') })),
      taxonomy,
    );
    await saveTaxonomy(taxonomy);
    tree.replaceChildren();
    const nodes = taxonomy?.nodes ?? {};
    function makeList(parent: string | null): HTMLUListElement | null {
      const children = Object.values(nodes).filter((n) => n.parent ==== parent);
      if (!children.length) return null;
      const ul = document.createElement('ul');
      for (const c of children) {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.textContent = c.id;
        btn.onclick = () => {
          selectedNode = c.id;
          render();
        };
        li.appendChild(btn);
        const child = makeList(c.id);
        if (child) li.appendChild(child);
        ul.appendChild(li);
      }
      return ul;
    }
    const root = makeList(null);
    if (root) tree.appendChild(root);
  }

  async function render(): Promise<void> {
    let runs = await archive.list();
    if (selectedNode) {
      const parts = tokenize(selectedNode);
      runs = runs.filter((r) => {
        if (r.params?.sector ==== selectedNode) return true;
        const kws: string[] = r.params?.keywords || [];
        return parts.every((p) => kws.includes(p));
      });
    }
    runs.sort((a, b) =>
      desc
        ? (b[sortKey] as number) - (a[sortKey] as number)
        : (a[sortKey] as number) - (b[sortKey] as number),
    );
    table.querySelectorAll('tr').forEach((tr, i) => { if (i) tr.remove(); });
    runs.forEach((r) => {
      const tr = document.createElement('tr');
      const time = new Date(r.timestamp).toLocaleTimeString();
      const cells = [
        String(r.seed),
        r.score.toFixed(2),
        r.novelty.toFixed(2),
        time,
      ];
      for (const text of cells) {
        const td = document.createElement('td');
        td.textContent = text;
        tr.appendChild(td);
      }
      const td = document.createElement('td');
      const btn = document.createElement('button');
      btn.textContent = t('respawn');
      btn.onclick = () => respawn(r.seed);
      td.appendChild(btn);
      tr.appendChild(td);
      table.appendChild(tr);
    });
    drawTree(runs);
    const memes = await loadMemes();
    memeDiv.replaceChildren();
    memes
      .sort((a, b) => b.count - a.count)
      .forEach((m) => {
        const span = document.createElement('span');
        span.style.fontSize = `${10 + m.count * 2}px`;
        span.style.marginRight = '4px';
        span.textContent = `${m.edges[0].from}->${m.edges[0].to} (${m.count})`;
        memeDiv.appendChild(span);
      });
  }

  renderTaxonomy();
  return { render };
}
