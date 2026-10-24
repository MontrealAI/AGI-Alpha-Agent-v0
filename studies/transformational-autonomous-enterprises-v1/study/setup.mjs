// SPDX-License-Identifier: Apache-2.0
// Reproducible public-source setup. Existing checkouts are verified, never reset.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createHash } from 'node:crypto';
const exec = promisify(execFile);
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const pins = {
  alpha: ['AGI-Alpha-Agent-v0', '9cb90e8c189f146eff7d166e249d9474792c4864'],
  manager: ['AGIJobManager', '3153ac394d37eeecb03e825ecce37559427bc6c3'],
  jobs: ['AGIJobsv0', 'ca6cfb74a36c233e5f04bd591a5e2179299774a1'],
  fleet: ['AGI-Fleet-Linux', '45759fb096faf8988f58ae5ea71248d0f35a97c7']
};
const historicalBuilder = '2478198819227d4414e17fe90a04e8137d543241';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
export async function setup({ checkOnly = false } = {}) {
  if (!/^v24\./.test(process.version) || Number(process.versions.node.split('.')[1]) < 19) throw Error('Use Node 24.19.0 or a later 24.x patch; the recorded experiment used 24.19.0');
  const start = performance.now(), events = [];
  async function command(program, args, cwd, timeout = 180000) {
    console.log([program, ...args].join(' '));
    const began = performance.now();
    try { const result = await exec(program, args, { cwd, timeout, maxBuffer: 8 * 1024 * 1024, env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: process.platform === 'win32' ? 'NUL' : '/dev/null', HARDHAT_NETWORK: 'hardhat' } }); events.push({ program, args, cwd: path.relative(root, cwd), elapsedMs: performance.now() - began, exitCode: 0, stdout: result.stdout, stderr: result.stderr }); return result.stdout.trim(); }
    catch (error) { events.push({ program, args, elapsedMs: performance.now() - began, exitCode: error.code, stdout: error.stdout, stderr: error.stderr }); throw error; }
  }
  const log = path.join(root, 'study', 'setup-attempts');
  if (!checkOnly) fs.mkdirSync(log, { recursive: true });
  try {
    for (const [name, [repo, commit]] of Object.entries(pins)) {
      const directory = path.join(root, 'repos', name);
      if (!fs.existsSync(directory)) {
        if (checkOnly) throw Error(`Missing ${name}: run node study/setup.mjs`);
        fs.mkdirSync(directory, { recursive: true });
        await command('git', ['init', '--quiet'], directory);
        await command('git', ['remote', 'add', 'origin', `https://github.com/MontrealAI/${repo}.git`], directory);
        await command('git', ['fetch', '--depth=1', 'origin', commit], directory);
        await command('git', ['checkout', '--detach', commit], directory);
      }
      const head = await command('git', ['rev-parse', 'HEAD'], directory, 10000);
      if (head !== commit) throw Error(`Existing ${name} checkout differs from the recorded pin; use a fresh companion directory. Nothing was reset.`);
      const changed = await command('git', ['status', '--porcelain', '--untracked-files=no'], directory, 10000);
      if (changed) throw Error(`Existing ${name} has tracked edits; preserve them and use a fresh companion directory.`);
    }
    const manager = path.join(root, 'repos/manager');
    try { await command('git', ['cat-file', '-e', historicalBuilder + '^{commit}'], manager, 10000); }
    catch (error) { if (checkOnly) throw error; await command('git', ['fetch', '--depth=1', 'origin', historicalBuilder], manager); }
    for (const relative of ['repos/fleet/fleet', 'repos/alpha/tests/contracts']) {
      const directory = path.join(root, relative), lock = path.join(directory, 'package-lock.json');
      const fleetRuntimeOnly = relative.includes('/fleet/');
      if (!fs.existsSync(lock)) throw Error(`Missing dependency lock: ${relative}`);
      if (!fs.existsSync(path.join(directory, 'node_modules'))) {
        if (checkOnly) throw Error(`Missing dependencies in ${relative}`);
        await command(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['ci', '--ignore-scripts', '--no-audit', '--no-fund', ...(fleetRuntimeOnly ? ['--omit=dev'] : [])], directory);
      }
      await command(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['ls', '--all', '--omit=optional', ...(fleetRuntimeOnly ? ['--omit=dev'] : []), '--json'], directory, 30000);
      const dependencyLock = JSON.parse(fs.readFileSync(lock));
      const declared = { ...(dependencyLock.packages[''].dependencies ?? {}), ...(fleetRuntimeOnly ? {} : dependencyLock.packages[''].devDependencies ?? {}) };
      for (const name of Object.keys(declared)) {
        const installed = JSON.parse(fs.readFileSync(path.join(directory, 'node_modules', name, 'package.json')));
        if (installed.version !== dependencyLock.packages['node_modules/' + name]?.version) throw Error(`Installed dependency differs from lock: ${name}`);
      }
      await command(process.execPath, ['-e', fleetRuntimeOnly ? "require('ethers'); require('ajv'); console.log('Required Fleet imports available')" : "require('hardhat'); require('ethers'); require('solc'); console.log('Required local EVM imports available')"], directory, 30000);
      events.push({ dependencyLock: path.relative(root, lock), sha256: sha(fs.readFileSync(lock)) });
    }
    const contracts = path.join(root, 'repos/alpha/tests/contracts');
    if (!fs.existsSync(path.join(contracts, 'artifacts/contracts/ascension/AscensionMark.sol/AscensionMark.json'))) {
      if (checkOnly) throw Error('Compile local fixture artifacts with node study/setup.mjs');
      await command(process.execPath, [path.join(contracts, 'node_modules/hardhat/internal/cli/cli.js'), 'compile', '--concurrency', '1'], contracts);
    }
    const report = { schema: 'tae.setup.v1', node: process.version, testedNode: 'v24.19.0', elapsedMs: performance.now() - start, checkOnly, ready: true, pins, events, authority: 'Public source downloads and local dependency compilation only; no external financial endpoint or wallet' };
    if (!checkOnly) fs.writeFileSync(path.join(log, `setup-${Date.now()}.json`), JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
    console.log('Local demonstration is ready. Run node study/server.mjs, then open http://127.0.0.1:8765/study/interface/');
    return report;
  } catch (error) {
    if (!checkOnly) fs.writeFileSync(path.join(log, `failed-${Date.now()}.json`), JSON.stringify({ error: error.message, elapsedMs: performance.now() - start, events }, null, 2) + '\n', { flag: 'wx' });
    throw error;
  }
}
if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  if (process.argv.slice(2).some(arg => arg !== '--check')) throw Error('Usage: node study/setup.mjs [--check]');
  setup({ checkOnly: process.argv.includes('--check') }).catch(error => { console.error(error.message); process.exitCode = 1; });
}
