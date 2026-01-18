// SPDX-License-Identifier: Apache-2.0
import * as Plot from '@observablehq/plot';
import { plotCanvas } from './plotCanvas.ts';
import { paretoFront } from '../utils/pareto.ts';
import { depthColor } from './colors.ts';
import { drawHeatmap } from './canvasLayer.ts';

import type { Individual } from '../state/serializer.ts';

const d3 = (globalThis as typeof globalThis & { d3: typeof import('d3') }).d3;

export function renderFrontier(
  container: HTMLElement,
  pop: Individual[],
  onSelect?: (d: Individual, el: SVGCircleElement) => void,
): void {
  const front = paretoFront(pop).sort((a, b) => a.logic - b.logic);

  const maxDepth = pop.reduce((m, d) => Math.max(m, d.depth ?? 0), 0);
  const dotOptions = {
    x: 'logic',
    y: 'feasible',
    r: 3,
    fill: (d: Individual) => depthColor(d.depth ?? 0, maxDepth),
    title: (d: Individual) => `${d.summary ?? ''}\n${d.critic ?? ''}`,
  };

  const marks = [
    Plot.areaY(front, {
      x: 'logic',
      y: 'feasible',
      fill: 'rgba(0,175,255,0.2)',
      stroke: null,
    }),
  ];

  if (pop.length <= 10000) {
    marks.push(Plot.dot(pop, dotOptions));
  }

  const plot = Plot.plot({
    width: 500,
    height: 500,
    x: { domain: [0, 1] },
    y: { domain: [0, 1] },
    marks,
  });

  container.innerHTML = '';
  container.append(plot);
  const svg = plot.querySelector('svg') || plot;
  if (pop.length > 10000) {
    plotCanvas(svg, pop, (d) => d.logic * 500, (d) => (1 - d.feasible) * 500, (d) => depthColor(d.depth ?? 0, maxDepth));
  }
  drawHeatmap(svg, pop, (d) => d.logic * 500, (d) => (1 - d.feasible) * 500);
  if (onSelect) {
    d3
      .select(plot)
      .selectAll<SVGCircleElement, Individual>('circle')
      .on('click', function (_, d) {
        onSelect(d, this);
      });
  }
}
