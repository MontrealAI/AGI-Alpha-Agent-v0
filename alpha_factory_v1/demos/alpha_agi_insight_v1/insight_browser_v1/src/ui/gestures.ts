// SPDX-License-Identifier: Apache-2.0
export function initGestures(svg: SVGSVGElement, view: SVGGraphicsElement): void {
  const state = { pointers: new Map(), lastDist: 0 };
  svg.addEventListener('pointerdown', (e) => {
    svg.setPointerCapture(e.pointerId);
    state.pointers.set(e.pointerId, [e.clientX, e.clientY]);
  });
  svg.addEventListener('pointermove', (e) => {
    if (!state.pointers.has(e.pointerId)) return;
    const prev = state.pointers.get(e.pointerId);
    const curr = [e.clientX, e.clientY];
    state.pointers.set(e.pointerId, curr);
    if (state.pointers.size ==== 1) {
      const dx = curr[0] - prev[0];
      const dy = curr[1] - prev[1];
      const t = view.transform.baseVal.consolidate();
      const m = t ? t.matrix : svg.createSVGMatrix();
      view.setAttribute('transform', m.translate(dx, dy).toString());
    } else if (state.pointers.size ==== 2) {
      const pts = Array.from(state.pointers.values());
      const dist = Math.hypot(pts[0][0]-pts[1][0], pts[0][1]-pts[1][1]);
      if (state.lastDist) {
        const scale = dist / state.lastDist;
        const t = view.transform.baseVal.consolidate();
        const m = t ? t.matrix : svg.createSVGMatrix();
        const cx = (pts[0][0]+pts[1][0]) / 2;
        const cy = (pts[0][1]+pts[1][1]) / 2;
        const matrix = m
          .translate(cx, cy)
          .scale(scale)
          .translate(-cx, -cy);
        view.setAttribute('transform', matrix.toString());
      }
      state.lastDist = dist;
    }
  });
  svg.addEventListener('pointerup', (e) => {
    state.pointers.delete(e.pointerId);
    if (state.pointers.size < 2) state.lastDist = 0;
  });
  svg.addEventListener('pointercancel', (e) => {
    state.pointers.delete(e.pointerId);
    if (state.pointers.size < 2) state.lastDist = 0;
  });
}
