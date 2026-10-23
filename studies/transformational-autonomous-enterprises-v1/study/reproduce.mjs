// SPDX-License-Identifier: Apache-2.0
// Reproduce into a fresh copy so original scored failures and receipts survive.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
const exec = promisify(execFile);
const study = path.dirname(fileURLToPath(import.meta.url));
if (process.argv.slice(2).some(arg => !['--smoke', '--evaluation'].includes(arg))) throw Error('Usage: node study/reproduce.mjs [--smoke | --evaluation]');
const mode = process.argv.includes('--evaluation') ? 'evaluation' : 'smoke';
const output = path.join(study, 'reproductions', `${mode}-${new Date().toISOString().replace(/[:.]/g, '-')}`);
fs.mkdirSync(output, { recursive: true });
for (const name of ['enterprise', 'evaluation', 'integration']) fs.cpSync(path.join(study, name), path.join(output, name), { recursive: true });
fs.mkdirSync(path.join(output, 'results'), { recursive: true });
const commands = mode === 'smoke' ? [ ['--test', path.join(output, 'enterprise/development.test.mjs')], [path.join(output, 'evaluation/control-tests.mjs')] ] : [ [path.join(output, 'evaluation/run-study.mjs'), path.join(output, 'results/confirmation')], [path.join(output, 'evaluation/run-load.mjs')], [path.join(output, 'evaluation/control-tests.mjs')] ];
const runs = [];
for (const args of commands) {
  const start = performance.now(); console.log(`Running ${path.basename(args.at(0) === '--test' ? args[1] : args[0])} in a fresh evidence directory`);
  try { const result = await exec(process.execPath, args, { cwd: path.dirname(study), timeout: 60000, maxBuffer: 12 * 1024 * 1024 }); fs.writeFileSync(path.join(output, `command-${runs.length + 1}.txt`), result.stdout + result.stderr); runs.push({ args, elapsedMs: performance.now() - start, exitCode: 0 }); }
  catch (error) { fs.writeFileSync(path.join(output, `command-${runs.length + 1}.txt`), (error.stdout ?? '') + (error.stderr ?? '')); runs.push({ args, elapsedMs: performance.now() - start, exitCode: error.code }); fs.writeFileSync(path.join(output, 'reproduction.json'), JSON.stringify({ mode, runs, complete: false }, null, 2)); throw error; }
}
fs.writeFileSync(path.join(output, 'reproduction.json'), JSON.stringify({ mode, runs, complete: true, originalScoredEvidenceUnchanged: true, blindness: 'Reproduction of the published task bank, not a new blind evaluation' }, null, 2));
console.log(`Complete: ${output}`);
