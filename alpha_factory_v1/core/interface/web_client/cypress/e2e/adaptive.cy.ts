// SPDX-License-Identifier: Apache-2.0
describe('adaptive toggle', () => {
  it('toggles body attribute', () => {
    cy.intercept('GET', '**/api/lineage', [
      { id: 1, pass_rate: 1 },
      { id: 2, parent: 1, pass_rate: 1 },
    ]).as('lineage');
    cy.intercept('GET', '**/api/memes', {}).as('memes');
    cy.visit('/');
    cy.get('#adaptive', { timeout: 10000 }).check();
    cy.get('body').should('have.attr', 'data-adaptive', 'true');
    cy.get('#adaptive').uncheck();
    cy.get('body').should('not.have.attr', 'data-adaptive');
  });
});
