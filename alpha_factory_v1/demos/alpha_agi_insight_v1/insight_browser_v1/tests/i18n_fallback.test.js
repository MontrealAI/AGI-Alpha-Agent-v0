// SPDX-License-Identifier: Apache-2.0
import { initI18n, t } from '../src/ui/i18n.ts';

beforeEach(() => {
  global.fetch = jest.fn(() => Promise.reject(new Error('fail')));
});

test('fallback to english on fetch failure', async () => {
  await initI18n();
  expect(t('seed')).toBe('Seed');
});

test('missing keys use default language', async () => {
  global.fetch = jest.fn(() => Promise.resolve({ json: () => Promise.resolve({}) }));
  localStorage.setItem('lang', 'es');
  await initI18n();
  expect(t('pyodide_failed')).toBe('Pyodide failed to load; using JS only');
});
