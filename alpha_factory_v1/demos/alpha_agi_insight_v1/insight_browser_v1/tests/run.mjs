#!/usr/bin/env node
import {spawnSync} from 'child_process';
import {dirname, resolve} from 'path';
import {fileURLToPath} from 'url';

const args = process.argv.slice(2);
const offlineIndex = args.indexOf('--offline');
const offline = offlineIndex !== -1;
if (offline) {
  args.splice(offlineIndex, 1);
  process.env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1';
  if (!process.env.PLAYWRIGHT_BROWSERS_PATH) {
    process.env.PLAYWRIGHT_BROWSERS_PATH = resolve(process.cwd(), 'browsers');
  }
}

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

function run(cmd, options = {}) {
  const res = spawnSync(cmd[0], cmd.slice(1), {stdio: 'inherit', cwd: root, ...options});
  if (res.status) process.exit(res.status);
}

run(['npm', 'run', 'build']);
run(['node', '--loader', 'ts-node/esm', '--test',
  'tests/entropy.test.js',
  'tests/replay_cid.test.js',
  'tests/iframe_worker_cleanup.test.js',
  'tests/onnx_gpu_backend.test.js',
  'tests/error_boundary_limit.test.js',
  'tests/locale_parity.test.js',
  'tests/test_sw_update.js',
  '../../../../tests/taxonomy.test.ts',
  '../../../../tests/memeplex.test.ts'
  ,'../../../../tests/webgl_perf.test.js'
  ,'../../../../tests/gpu_flag.test.js'
]);
run([
  'pytest',
  'tests/test_no_console_errors.py',
  '../../../../tests/test_quickstart_offline.py',
  '../../../../tests/test_evolution_panel_reload.py',
  '../../../../tests/test_sw_offline_reload.py',
  '../../../../tests/test_pwa_update_reload.py'
]);
run(['pytest', 'tests/test_tree_visualization.py'], {env: {...process.env, PLAYWRIGHT_BROWSER: 'firefox'}});
run(['pytest', 'tests/test_tree_visualization.py'], {env: {...process.env, PLAYWRIGHT_BROWSER: 'webkit'}});
