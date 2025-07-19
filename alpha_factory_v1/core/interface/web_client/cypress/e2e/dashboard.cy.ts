// SPDX-License-Identifier: Apache-2.0
describe('dashboard', () => {
  it('loads lineage tree', () => {
    cy.on('window:before:load', (win) => {
      cy.spy(win.console, 'error').as('consoleError');
    });
    cy.intercept('GET', '**/lineage', [
      { id: 1, pass_rate: 1 },
      { id: 2, parent: 1, pass_rate: 1 },
      { id: 3, parent: 1, pass_rate: 1 },
    ]).as('lineage');
    cy.intercept('GET', '**/memes', {}).as('memes');
    cy.visit('/');
    cy.get('#lineage-tree', { timeout: 10000 });
    cy.get('#lineage-tree g.slice').should('have.length.gte', 3);
    cy.get('@consoleError').should('not.be.called');
  });

  it('shows annotation on hover', () => {
    cy.intercept('GET', '**/lineage', [
      { id: 1, pass_rate: 1 },
      { id: 2, parent: 1, pass_rate: 1 },
      { id: 3, parent: 1, pass_rate: 1 },
    ]).as('lineage');
    cy.intercept('GET', '**/memes', {}).as('memes');
    cy.visit('/');
    cy.get('#lineage-tree', { timeout: 10000 });
    cy.get('#lineage-tree g.slice').first().trigger('mouseover');
    cy.get('#lineage-tree .hovertext').should('be.visible');
  });
});
