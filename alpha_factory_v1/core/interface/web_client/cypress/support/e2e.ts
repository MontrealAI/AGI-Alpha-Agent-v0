// SPDX-License-Identifier: Apache-2.0
import '@percy/cypress';

// Ignore service worker registration failures which cause uncaught exceptions
Cypress.on('uncaught:exception', (err) => {
  if (err.message.includes('ServiceWorker')) {
    return false;
  }
});

// Stub the service worker to prevent network errors during tests
beforeEach(() => {
  cy.intercept('GET', '/service-worker.js', { body: '' }).as('sw');
});
