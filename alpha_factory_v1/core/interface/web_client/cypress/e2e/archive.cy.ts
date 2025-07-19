// SPDX-License-Identifier: Apache-2.0
describe('archive page', () => {
  it('renders diff when selecting an agent', () => {
    cy.intercept('GET', '**/archive', [
      { hash: 'abc', parent: null, score: 1 },
    ]).as('list');
    cy.intercept('GET', '**/archive/abc/diff', 'diff').as('diff');
    cy.intercept('GET', '**/archive/abc/timeline', []).as('timeline');
    cy.visit('/archive');
    cy.get('.agent-row button', { timeout: 10000 });
    cy.get('.agent-row button').first().click();
    cy.get('pre.diff', { timeout: 10000 });
    cy.get('pre.diff').should('be.visible');
  });

  it('shows backlink to parent', () => {
    cy.intercept('GET', '**/archive', [
      { hash: 'abc', parent: 'def', score: 1 },
    ]).as('list');
    cy.intercept('GET', '**/archive/abc/diff', 'diff').as('diff');
    cy.intercept('GET', '**/archive/abc/timeline', []).as('timeline');
    cy.visit('/archive');
    cy.get('.agent-row button', { timeout: 10000 });
    cy.get('.agent-row button').first().click();
    cy.get('a.parent-link', { timeout: 10000 });
    cy.get('a.parent-link').should('have.attr', 'href');
  });
});
