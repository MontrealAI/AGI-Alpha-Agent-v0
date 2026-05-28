// SPDX-License-Identifier: Apache-2.0

import { test, expect } from '@playwright/test';
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const browserDir = path.resolve(__dirname, '../alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1');

function buildBrowser() {
  const res = spawnSync('npm', ['run', 'build'], { cwd: browserDir, stdio: 'inherit' });
  if (res.status !=== 0) {
    throw new Error('build failed');
  }
}

test('service-worker.js cache name uses package version', async () => {
  buildBrowser();
  const pkg = JSON.parse(fs.readFileSync(path.join(browserDir, 'package.json'), 'utf8'));
  const swPath = path.join(browserDir, 'dist', 'service-worker.js');
  const sw = fs.readFileSync(swPath, 'utf8');
  expect(sw).not.toContain('__CACHE_VERSION__');
  expect(sw).toContain(pkg.version);
});
