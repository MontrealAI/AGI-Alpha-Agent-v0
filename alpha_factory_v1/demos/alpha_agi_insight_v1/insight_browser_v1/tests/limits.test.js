// SPDX-License-Identifier: Apache-2.0
import { initControls } from '../src/ui/ControlsPanel.ts';
import { parseHash } from '../src/config/params.ts';

test('values above max are clamped', () => {
  document.body.innerHTML = '<div id="controls"></div>';
  let params = null;
  function onChange(p) { params = p; }
  initControls({ seed: 1, pop: 1, gen: 1, mutations: [], adaptive: false }, onChange);
  const popInput = document.querySelector('#pop');
  const genInput = document.querySelector('#gen');
  popInput.value = '600';
  popInput.dispatchEvent(new Event('change'));
  genInput.value = '700';
  genInput.dispatchEvent(new Event('change'));
  expect(popInput.value).toBe('500');
  expect(genInput.value).toBe('500');
  expect(params.pop).toBe(500);
  expect(params.gen).toBe(500);
});

test('parseHash clamps values above max', () => {
  const params = parseHash('#/p=9999&g=9999');
  expect(params.pop).toBe(500);
  expect(params.gen).toBe(500);
});
