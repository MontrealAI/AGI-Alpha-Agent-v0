// SPDX-License-Identifier: Apache-2.0
import { consilience, scoreGenome, LogicCritic, FeasibilityCritic, JudgmentDB } from '../src/wasm/critics.ts';

beforeEach(() => {
  indexedDB.deleteDatabase('jest');
  window.recordedPrompts = [];
});

test('scoreGenome mutates prompts when consilience is low', async () => {
  const logic = new LogicCritic([], 'logic');
  const feas = new FeasibilityCritic([], 'feasible');
  logic.score = () => 0;
  feas.score = () => 1;

  const db = new JudgmentDB('jest');
  const result = await scoreGenome('foo', [logic, feas], db, 0.6);
  const expected = consilience({ LogicCritic: 0, FeasibilityCritic: 1 });

  expect(result.cons).toBeCloseTo(expected);
  expect(result.cons).toBeLessThan(0.6);
  expect(logic.prompt).not.toBe('logic');
  expect(feas.prompt).not.toBe('feasible');
  expect(window.recordedPrompts).toEqual([logic.prompt, feas.prompt]);
});
