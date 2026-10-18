// SPDX-License-Identifier: Apache-2.0
import { createHash } from 'node:crypto';
import { constants } from 'node:fs';
import { open, readFile, lstat, stat, mkdir, writeFile, unlink, rmdir } from 'node:fs/promises';
import { resolve, join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import * as alpha from './engine.mjs';
import * as project from './project.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const usage = `Usage:
  node examples/successor-alpha/cli.mjs --example --out NEW_DIRECTORY
  node examples/successor-alpha/cli.mjs --left left.csv --right right.csv --left-key sku --right-key id --out NEW_DIRECTORY

Use public, licensed-for-this-purpose, or synthetic non-personal catalog records.
Each CSV is limited to 200,000 bytes, 1,500 rows, and 32 columns; output is limited to 10,000 matching pairs.
Output directories must not already exist. No model, credentials, network, payment, or deployment is used.
`;

function parseArgs(argv) {
    const values = Object.create(null);
    const valued = ['--left', '--right', '--left-key', '--right-key', '--out'];
    for (let index = 0; index < argv.length; index += 1) {
        const arg = argv[index];
        if (Object.hasOwn(values, arg)) throw Error(`Repeated option: ${arg}`);
        if (arg === '--help' || arg === '--example') values[arg] = true;
        else if (valued.includes(arg)) {
            const value = argv[++index];
            if (!value || value.startsWith('--')) throw Error(`Missing value for ${arg}.`);
            values[arg] = value;
        } else throw Error(`Unknown option: ${arg}`);
    }
    if (values['--help']) {
        if (Object.keys(values).length !== 1) throw Error('Use --help by itself.');
        return { help: true };
    }
    if (!values['--out']) throw Error('Choose a new output directory with --out.');
    if (values['--example']) {
        if (Object.keys(values).some(key => !['--example', '--out'].includes(key))) {
            throw Error('--example cannot be combined with custom input files or key columns.');
        }
    } else if (valued.some(key => !values[key])) throw Error('Custom inputs need both CSV paths and both key columns.');
    return values;
}

async function requireNewDirectory(path) {
    try { await lstat(path); }
    catch (error) { if (error.code === 'ENOENT') return; throw error; }
    throw Error('The output path already exists. Choose a new directory.');
}

async function readCsv(path) {
    const initial = await stat(path);
    if (!initial.isFile()) throw Error('CSV inputs must be regular local files.');
    if (initial.size > alpha.DEFAULT_LIMITS.maxCsvBytes) throw Error('CSV exceeds 200000 bytes.');
    const file = await open(path, constants.O_RDONLY | constants.O_NONBLOCK);
    try {
        const info = await file.stat();
        if (!info.isFile()) throw Error('CSV inputs must be regular local files.');
        const limit = alpha.DEFAULT_LIMITS.maxCsvBytes;
        if (info.size > limit) throw Error(`CSV exceeds ${limit} bytes.`);
        const data = Buffer.alloc(limit + 1);
        let used = 0;
        while (used < data.length) {
            const { bytesRead } = await file.read(data, used, data.length - used, null);
            if (bytesRead === 0) break;
            used += bytesRead;
        }
        if (used > limit) throw Error(`CSV exceeds ${limit} bytes.`);
        return new TextDecoder('utf-8', { fatal: true }).decode(data.subarray(0, used));
    } finally { await file.close(); }
}

export async function runCli(argv, stdout = process.stdout) {
    const args = parseArgs(argv);
    if (args.help) { stdout.write(usage); return 0; }
    const output = resolve(args['--out']);
    await requireNewDirectory(output);
    const mission = args['--example'] ? alpha.createSampleMission() : alpha.createJoinMission({
        leftCsv: await readCsv(resolve(args['--left'])), rightCsv: await readCsv(resolve(args['--right'])),
        leftKey: args['--left-key'], rightKey: args['--right-key'],
    });
    const result = await alpha.runJoinExperiment(mission);
    const artifacts = alpha.buildArtifacts(mission, result);
    const engineSource = await readFile(join(here, 'engine.mjs'), 'utf8');
    const projectSource = await readFile(join(here, 'project.mjs'), 'utf8');
    const deployment = JSON.parse(await readFile(join(here, 'deployment.json'), 'utf8'));
    project.configure({ engineSource, deployment });
    const sourceHash = createHash('sha256').update(engineSource).update('\n').update(projectSource).digest('hex');
    let dossier = project.createProject({ name: 'My SUCCESSOR Ω', goal: 'Reconcile two public catalogs and retain a reusable method.' });
    dossier = project.appendCycle(dossier, { mission, result, sourceHash });
    const files = {
        'joined.csv': artifacts.joinedCsv, 'unmatched-left.csv': artifacts.unmatchedLeftCsv,
        'unmatched-right.csv': artifacts.unmatchedRightCsv, 'conflicts.csv': artifacts.conflictsCsv,
        'exact-result.json': artifacts.exactJson, 'comparison.json': JSON.stringify(result, null, 2) + '\n',
        'report.html': project.buildReport(mission, result, { name: dossier.name, goal: dossier.goal }),
        'project.json': project.serializeProject(dossier) + '\n',
        'successor-tool.mjs': project.buildCapability(mission, result),
    };
    await mkdir(output, { recursive: false });
    const created = [];
    try {
        for (const [name, content] of Object.entries(files)) {
            const path = join(output, name);
            await writeFile(path, content, { encoding: 'utf8', flag: 'wx' });
            created.push(path);
        }
    } catch (error) {
        for (const path of created) await unlink(path).catch(() => {});
        await rmdir(output).catch(() => {});
        throw error;
    }
    stdout.write(`Catalog reconciliation complete: ${mission.left.rows.length} × ${mission.right.rows.length} source rows, `
        + `${result.reconciliation.matchedPairs} matched pairs, ${result.reconciliation.conflicts.length} conflicting pairs.\n`
        + `Saved ${Object.keys(files).length} artifacts in ${output}\n`
        + 'All four methods passed local exact checking. Independent qualification and economic value remain unestablished.\n');
    return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
    try { process.exitCode = await runCli(process.argv.slice(2)); }
    catch (error) { console.error(`SUCCESSOR Ω: ${error.message}`); process.exitCode = 1; }
}
