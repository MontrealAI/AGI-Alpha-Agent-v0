// SPDX-License-Identifier: Apache-2.0
// A local research adapter on the unchanged SUCCESSOR Workbench API.
import {spawn} from 'node:child_process';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sha = raw => createHash('sha256').update(raw).digest('hex');
const json = (name, value) => ({name, type:'application/json', content:JSON.stringify(value, null, 2) + '\n'});

export async function sourceIdentity() {
  const names = ['src/manual_probe.py', 'src/verify_component.py', 'src/measured_run.py',
    'src/run_pair.py', 'src/package_component.py', 'src/conventional_probe.py',
    'src/conventional_package.py', 'src/delivery.py', 'src/workbench.mjs',
    'protocol/component-contract.json', 'protocol/component-projections.json', 'native/SOURCE.json'];
  const entries = [];
  for (const name of names) entries.push([name, sha(await readFile(path.join(ROOT, name)))]);
  const native = JSON.parse(await readFile(path.join(ROOT, 'native/SOURCE.json'), 'utf8'));
  for (const entry of native.files) {
    const file = path.resolve(ROOT, 'native', entry.path);
    if (!file.startsWith(path.join(ROOT, 'native') + path.sep)) throw Error('NATIVE_SOURCE_PATH');
    const raw = await readFile(file);
    if (raw.length !== entry.bytes || sha(raw) !== entry.sha256) throw Error('NATIVE_SOURCE_IDENTITY');
    entries.push(['native/' + entry.path, sha(raw)]);
  }
  return sha(JSON.stringify(entries));
}

function executeDelivery(jobPath, arm, directory) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.PYTHON_EXECUTABLE || 'python',
      [path.join(ROOT, 'src/delivery.py'), '--job', jobPath, '--arm', arm, '--out', directory],
      {cwd:ROOT, stdio:['ignore', 'pipe', 'pipe'], detached:true});
    let output = '', errors = '', oversized = false;
    const stop = () => { try { process.kill(-child.pid, 'SIGKILL'); } catch {} };
    const timer = setTimeout(() => { stop(); reject(Error('LOCAL_DELIVERY_TIMEOUT_55S')); }, 55000);
    child.stdout.on('data', chunk => {
      output += chunk.toString();
      if (output.length > 200000) { oversized = true; stop(); }
    });
    child.stderr.on('data', chunk => { errors = (errors + chunk.toString()).slice(-8000); });
    child.on('error', error => { clearTimeout(timer); reject(error); });
    child.on('close', code => {
      clearTimeout(timer);
      if (oversized || code !== 0) return reject(Error(`LOCAL_DELIVERY_FAILED ${code}: ${errors}`));
      try { resolve(JSON.parse(output)); } catch (error) { reject(error); }
    });
  });
}

export async function runRegistered(mission, arm, outDirectory, language = 'en', registryRelative = 'protocol/mission-registry.json') {
  const frozenSourceHash = await sourceIdentity();
  const {createWorkbench} = await import('../native/examples/successor-workbench/engine.mjs');
  const registryPath = path.resolve(ROOT, registryRelative);
  if (!registryPath.startsWith(ROOT + path.sep)) throw Error('REGISTRY_PATH');
  const registry = JSON.parse(await readFile(registryPath, 'utf8'));
  if (!Object.hasOwn(registry.missions, mission)) throw Error('REGISTERED_MISSION_REQUIRED');
  if (!['retained', 'conventional'].includes(arm)) throw Error('REGISTERED_BUILDER_REQUIRED');
  const directory = path.resolve(outDirectory);
  await mkdir(directory, {recursive:true});
  const entry = registry.missions[mission];
  const jobPath = path.resolve(ROOT, entry.path);
  if (!jobPath.startsWith(ROOT + path.sep) || sha(await readFile(jobPath)) !== entry.sha256) throw Error('JOB_IDENTITY');
  const adapter = {
    manifest:{id:'component-upgrade-decision', version:2, en:'Assess a component dependency change',
      fr:'Évaluer une mise à jour de dépendances', scope:'Source-bound local request and mission-input component evidence.',
      artifact:'component-decision.json'},
    validate(input) {
      if (!input || Object.keys(input).sort().join('|') !== 'arm|mission' || input.mission !== mission || input.arm !== arm)
        throw Error('REGISTERED_INPUT_REQUIRED');
    },
    async execute(input, checkpoint) {
      await checkpoint('executing-original-consumer-contract');
      const receipt = await executeDelivery(jobPath, input.arm, path.join(directory, 'delivery'));
      const packetPath = path.join(directory, 'delivery/package/decision.json');
      const raw = await readFile(packetPath);
      if (sha(raw) !== receipt.decision_sha256) throw Error('DELIVERED_DECISION_IDENTITY');
      const packet = JSON.parse(raw);
      await checkpoint('independent-component-verification-and-package-integrity');
      return {decision:packet.decision,
        summary:{mission, accepted:receipt.accepted, scope:'COMPONENT_ONLY', casesPerEnvironment:61},
        evidence:{execution:'LOCAL_RESEARCH_ADAPTER', jobSha256:entry.sha256,
          packageDecisionSha256:receipt.decision_sha256, originalImportBridge:true,
          customerAcceptanceObserved:false, runtimeModelCalls:0, operatorAuthority:false},
        artifacts:[json('component-decision.json', packet), json('delivery-resources.json', receipt),
          json('requirement-results.json', JSON.parse(await readFile(path.join(directory, 'delivery/package/requirement-results.json'), 'utf8'))),
          json('complete-package-reference.json', {path:'delivery/package', scope:'Complete local downloadable evidence package',
            manifestSha256:sha(await readFile(path.join(directory, 'delivery/package/artifact-manifest.json')))}),
          {name:'component-lock.patch', type:'text/plain', content:await readFile(path.join(directory, 'delivery/package/proposed-component-lock.patch'), 'utf8')}],
        limits:['Finite source-grounded component assessment; full application qualification remains required.',
          'Local research execution, unauthenticated history, no operator or settlement authority.',
          'Review capacity is an unfunded schema field, not measured attention or cost.',
          'No customer payment; complete money cost and repayment remain unknown.']};
    }
  };
  const workbench = createWorkbench([adapter]);
  const spec = {schema:'successor-workbench/v1', family:adapter.manifest.id,
    name:'AGI ALPHA Component Upgrade Decision', language, owner:'local-research',
    rights:{dataClass:'public', source:'Registered exact public source and wheel identities',
      license:'Respective Apache-2.0, MIT, BSD and PSF-2.0 notices retained in the companion'},
    reviewMinutes:1, inputs:{mission, arm}};
  const pack = await workbench.run(spec, {sourceHash:frozenSourceHash});
  const inspection = await workbench.inspectPack(pack);
  await writeFile(path.join(directory, 'pack.json'), JSON.stringify(pack, null, 2) + '\n');
  await writeFile(path.join(directory, 'inspection.json'), JSON.stringify(inspection, null, 2) + '\n');
  return {pack, inspection};
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [mission, arm, directory, registry] = process.argv.slice(2);
  if (!mission || !arm || !directory) throw Error('Usage: node src/workbench.mjs MISSION ARM OUTPUT_DIRECTORY');
  const result = await runRegistered(mission, arm, directory, 'en', registry);
  console.log(JSON.stringify({decision:result.pack.result.decision,
    elapsedMilliseconds:result.pack.economics.elapsedMilliseconds, inspection:result.inspection.authentication,
    admission:result.pack.evaluation.admission, authority:result.pack.evaluation.authority}));
}
