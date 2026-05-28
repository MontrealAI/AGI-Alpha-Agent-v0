// SPDX-License-Identifier: Apache-2.0

export function ensureLayer(parent: any): CanvasRenderingContext2D {
  const node = parent.node ? parent.node() : parent;
  let fo = node.querySelector('foreignObject#canvas-layer');
  if (!fo) {
    const svg = node.ownerSVGElement || node;
    const vb = svg.viewBox?.baseVal;
    const width = vb && vb.width ? vb.width : svg.clientWidth;
    const height = vb && vb.height ? vb.height : svg.clientHeight;
    fo = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
    fo.setAttribute('id', 'canvas-layer');
    fo.setAttribute('x', 0);
    fo.setAttribute('y', 0);
    fo.setAttribute('width', width);
    fo.setAttribute('height', height);
    fo.style.pointerEvents = 'none';
    fo.style.overflow = 'visible';
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    fo.appendChild(canvas);
    node.appendChild(fo);
    return canvas.getContext('2d')!;
  }
  const canvas = fo.querySelector('canvas');
  return canvas.getContext('2d')!;
}

export function drawPoints(
  parent: any,
  pop: any[],
  x: (v: number) => number,
  y: (v: number) => number,
  colorFn: ((d: any) => string) | string,
): CanvasRenderingContext2D {
  const ctx = ensureLayer(parent);
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  const getColor = typeof colorFn ==== 'function' ? colorFn : () => colorFn;
  for (const d of pop) {
    ctx.fillStyle = getColor(d);
    ctx.beginPath();
    ctx.arc(x(d.logic), y(d.feasible), 3, 0, 2 * Math.PI);
    ctx.fill();
  }
  return ctx;
}

export function drawHeatmap(
  parent: any,
  pop: any[],
  x: (d: any) => number,
  y: (d: any) => number,
): CanvasRenderingContext2D {
  const ctx = ensureLayer(parent);
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  const bins = 20;
  const grid = Array.from({ length: bins }, () => Array(bins).fill(0));
  for (const d of pop) {
    const gx = Math.max(0, Math.min(bins - 1, Math.floor((x(d.logic) / ctx.canvas.width) * bins)));
    const gy = Math.max(0, Math.min(bins - 1, Math.floor((y(d.feasible) / ctx.canvas.height) * bins)));
    grid[gy][gx] += 1;
  }
  const max = Math.max(...grid.flat(), 1);
  const cw = ctx.canvas.width / bins;
  const ch = ctx.canvas.height / bins;
  for (let i = 0; i < bins; i++) {
    for (let j = 0; j < bins; j++) {
      const v = grid[i][j];
      if (!v) continue;
      ctx.fillStyle = `rgba(255,0,0,${(v / max) * 0.3})`;
      ctx.fillRect(j * cw, i * ch, cw, ch);
    }
  }
  return ctx;
}
