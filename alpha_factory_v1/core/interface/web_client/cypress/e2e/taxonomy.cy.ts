// SPDX-License-Identifier: Apache-2.0

describe('taxonomy persistence', () => {
  it('restores taxonomy tree after reload', () => {
    cy.intercept('GET', '**/api/lineage', [
      { id: 1, pass_rate: 1 },
      { id: 2, parent: 1, pass_rate: 1 },
    ]).as('lineage');
    cy.intercept('GET', '**/api/memes', {}).as('memes');
    cy.visit('/', {
      onBeforeLoad(win) {
        const req = win.indexedDB.open('sectorTaxonomy', 1);
        req.onupgradeneeded = () => {
          req.result.createObjectStore('nodes');
        };
        req.onsuccess = () => {
          const tx = req.result.transaction('nodes', 'readwrite');
          tx.objectStore('nodes').put({ id: 'foo', parent: null }, 'foo');
          tx.oncomplete = () => {};
        };
      },
    });
    cy.get('#taxonomy-tree', { timeout: 10000 });
    cy.get('#taxonomy-tree button').contains('foo');
    cy.reload();
    cy.get('#taxonomy-tree button').contains('foo');
  });
});
