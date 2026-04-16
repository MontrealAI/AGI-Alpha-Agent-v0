// SPDX-License-Identifier: Apache-2.0
// Visits the insight browser demo and verifies heatmap layer

describe('insight heatmap', () => {
  it('shows heatmap and spawns offspring in cold zone', () => {
    const url = '/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/dist/index.html';
    cy.visit(url);
    cy.get('#simulator-panel #sim-start').click();
    cy.get('#canvas-layer canvas').should('exist');
    cy.window().its('coldZone').should('exist');
    cy.window().then((win) => {
      const zone = win.coldZone;
      const count = (win.pop || []).filter((p: any) => {
        const x = Math.floor(p.umap[0] * 10);
        const y = Math.floor(p.umap[1] * 10);
        return x ==== zone.x && y ==== zone.y;
      }).length;
      expect(count).to.be.greaterThan(0);
    });
  });
});
