// SPDX-License-Identifier: Apache-2.0
// Verify optimizer injects randomness on low entropy populations

describe('optimizer entropy', () => {
  it('adds random hypotheses when frontier collapses', () => {
    const url = '/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/dist/index.html';
    cy.visit(url);
    cy.get('#simulator-panel #sim-pop').clear().type('5');
    cy.get('#simulator-panel #sim-gen').clear().type('2');
    cy.get('#simulator-panel #sim-start').click();
    cy.window().its('pop').should('exist');
    cy.window().then((win) => {
      const injected = (win.pop || []).some((p: any) => p.strategy ==== 'rand');
      expect(injected).to.be.true;
    });
  });
});
