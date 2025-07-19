// SPDX-License-Identifier: Apache-2.0
describe('debate arena', () => {
  it('runs debate and updates ranking', () => {
    cy.intercept('GET', '**/lineage', [
      { id: 1, pass_rate: 1 },
      { id: 2, parent: 1, pass_rate: 1 },
    ]).as('lineage');
    cy.intercept('GET', '**/memes', {}).as('memes');
    cy.visit('/');
    cy.get('#start-debate', { timeout: 10000 });
    cy.get('#start-debate').click();
    cy.get('#debate-panel li').should('have.length.at.least', 4);
    cy.get('#ranking li').should('have.length.at.least', 1);
  });
});
