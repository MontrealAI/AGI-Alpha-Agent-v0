// SPDX-License-Identifier: Apache-2.0
const viewports: Array<[number, number]> = [
  [375, 667], // mobile
  [768, 1024], // tablet
  [1280, 720], // desktop
];

describe('responsive dashboard', () => {
  viewports.forEach(([w, h]) => {
    it(`renders at ${w}x${h}`, () => {
      cy.viewport(w, h);
      cy.intercept('GET', '**/lineage', [
        { id: 1, pass_rate: 1 },
        { id: 2, parent: 1, pass_rate: 1 },
      ]).as('lineage');
      cy.intercept('GET', '**/memes', {}).as('memes');
      cy.visit('/');
      cy.get('#lineage-tree', { timeout: 10000 });
      cy.get('#lineage-tree').should('be.visible');
    });
  });

  it('loads while offline after first visit', () => {
    cy.intercept('GET', '**/lineage', [
      { id: 1, pass_rate: 1 },
      { id: 2, parent: 1, pass_rate: 1 },
    ]).as('lineage');
    cy.intercept('GET', '**/memes', {}).as('memes');
    cy.visit('/');
    cy.get('#lineage-tree', { timeout: 10000 });
    cy.intercept('GET', '**/*', { forceNetworkError: true }).as('offline');
    cy.reload();
    cy.get('#lineage-tree').should('be.visible');
  });

  it('copies share link', () => {
    cy.intercept('GET', '**/lineage', [
      { id: 1, pass_rate: 1 },
      { id: 2, parent: 1, pass_rate: 1 },
    ]).as('lineage');
    cy.intercept('GET', '**/memes', {}).as('memes');
    cy.visit('/');
    cy.get('button[type="submit"]', { timeout: 10000 });
    cy.window().then((win) => {
      cy.stub(win.navigator, 'clipboard', {
        writeText: cy.stub().as('copy'),
      });
    });
    cy.get('button[type="submit"]').click();
    cy.contains('Share').click();
    cy.get('@copy').should('be.called');
  });
});
