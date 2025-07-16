// SPDX-License-Identifier: Apache-2.0
import simulator from '../src/simulator.ts';
import { initSimulatorPanel } from '../src/ui/SimulatorPanel.ts';

jest.mock('@insight-src/replay.ts', () => ({
  ReplayDB: class {
    async open() {}
    async addFrame() { return 1; }
    async share() { return { data: '{}', cid: '1' }; }
  }
}));

jest.mock('@insight-src/memeplex.ts', () => ({
  mineMemes: () => [],
  saveMemes: async () => {},
}));

jest.mock('../src/ipfs/pinner.ts', () => ({
  pinFiles: async () => null,
}));

jest.mock('../src/render/frontier.ts', () => ({
  renderFrontier: () => {},
}));

jest.mock('../src/utils/cluster.ts', () => ({
  detectColdZone: () => ({ x: 0, y: 0 }),
}));

jest.mock('../src/evaluator_genome.ts', () => ({
  mutateEvaluator: (e) => e,
}));


test('simulator.start updates power panel', async () => {
  const archive = {
    addEvaluator: jest.fn().mockResolvedValue(1),
    add: jest.fn().mockResolvedValue(null),
  };
  const updates = [];
  const power = { update: (e) => updates.push(e) };

  simulator.Simulator.run = function () {
    return (async function* () {
      yield { population: [], fronts: [], gen: 1 };
    })();
  };

  document.body.innerHTML = '';
  await initSimulatorPanel(archive, power);

  const startBtn = document.querySelector('#simulator-panel #sim-start');
  startBtn.click();
  await new Promise((r) => setTimeout(r, 0));

  expect(updates.length).toBeGreaterThan(0);
});
