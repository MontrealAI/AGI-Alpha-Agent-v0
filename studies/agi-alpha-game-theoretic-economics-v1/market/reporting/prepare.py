#!/usr/bin/env python3
"""Prepare an output-only copy and custody manifest; never execute a market."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
MARKET = HERE.parent
EXPECTED_CORE = '52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27'
sha = lambda data: hashlib.sha256(data).hexdigest()
source = (MARKET / 'src/market.mjs').read_bytes()
assert sha(source) == EXPECTED_CORE, 'Frozen core has changed'
needle = b'    competitorSummary:Object.fromEntries'
assert source.count(needle) == 1
instrumented = source.replace(needle, b'    competitorAccounts:competitors,\n' + needle, 1)
with (HERE / 'market-expose.mjs').open('xb') as f:
    f.write(instrumented)
diff = ''.join(difflib.unified_diff(source.decode().splitlines(True), instrumented.decode().splitlines(True),
                                 fromfile='src/market.mjs', tofile='reporting/market-expose.mjs'))
with (HERE / 'instrumentation.diff').open('x') as f:
    f.write(diff)

blocks = {}
block_manifest = []
for label, relative in [('exploratory', 'exploratory/run.mjs'), ('policy', 'policy-diagnostic/run.mjs')]:
    runner = (MARKET / relative).read_text()
    start = runner.index('    const capital=paired.arms.B.histories.bills.filter')
    end = runner.index("    appendFileSync(resolve(out,'complete-runs.jsonl.gz')", start)
    blocks[label] = runner[start:end]
    block_manifest.append({'label': label, 'source': relative, 'sourceSHA256': sha(runner.encode()),
                           'startByte': len(runner[:start].encode()), 'endByteExclusive': len(runner[:end].encode()), 'blockSHA256': sha(blocks[label].encode())})
    if label == 'policy':
        price_start = runner.index('const priceRange=')
        price_end = runner.index('\n', price_start) + 1
        blocks['priceRange'] = runner[price_start:price_end]
        block_manifest.append({'label': 'priceRange', 'source': relative, 'sourceSHA256': sha(runner.encode()),
                               'startByte': len(runner[:price_start].encode()), 'endByteExclusive': len(runner[:price_end].encode()),
                               'blockSHA256': sha(blocks['priceRange'].encode())})
annotations = ('// Generated exact postprocessing blocks from frozen runners; no market decisions here.\n'
               + blocks['priceRange']
               + 'export function annotateExploratory(paired){\n' + blocks['exploratory'] + '}\n'
               + 'export function annotatePolicy(paired,config,seed,priorId,prior){\n' + blocks['policy'] + '}\n')
with (HERE / 'annotations.mjs').open('x') as f:
    f.write(annotations)

stages = []
for stage, output, freeze, worlds, runs in [
    ('primary', 'results/primary-01', 'protocol/freeze.json', 2088, 6264),
    ('exploratory', 'exploratory/results-01', 'exploratory/freeze.json', 2472, 7416),
    ('policy-diagnostic', 'policy-diagnostic/results-01', 'policy-diagnostic/freeze.json', 1920, 5760),
]:
    completion = json.loads((MARKET / output / 'completion.json').read_text())
    assert completion['pairedWorlds'] == worlds and completion['enterpriseRuns'] == runs
    archive = MARKET / output / 'complete-runs.jsonl.gz'
    archive_sha = sha(archive.read_bytes())
    assert archive_sha == completion['completeRunsSHA256']
    stages.append({'id': stage, 'originalDirectory': output, 'originalFreeze': freeze,
                   'originalFreezeSHA256': sha((MARKET / freeze).read_bytes()),
                   'originalArchive': str(archive.relative_to(MARKET)),
                   'originalArchiveSHA256': archive_sha, 'pairedWorlds': worlds, 'enterpriseRuns': runs})

files = []
for relative in ['reporting/prepare.py', 'reporting/replay-export.mjs', 'reporting/README.md',
                 'reporting/market-expose.mjs', 'reporting/annotations.mjs', 'reporting/instrumentation.diff',
                 'src/market.mjs', 'canonical/shadow-ledger.mjs', 'canonical/automated-costs.mjs',
                 'src/run.mjs', 'exploratory/run.mjs', 'policy-diagnostic/run.mjs',
                 'exploratory/results-01/outcomes.jsonl']:
    data = (MARKET / relative).read_bytes()
    files.append({'path': relative, 'bytes': len(data), 'sha256': sha(data)})

manifest = {
    'schema': 'agi-alpha-reporting-only-replay-source/v1',
    'preparedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'purpose': 'Posthoc custody completion of competitor accounts for existing frozen worlds; no new scenarios, policies or economic results.',
    'originalCoreSHA256': EXPECTED_CORE,
    'instrumentedCoreSHA256': sha(instrumented),
    'instrumentation': 'Only one property is added to the final simulate return object: competitorAccounts:competitors. No computation, decision, event, RNG key, import or mutation is changed.',
    'originalNativeCompetitorBalanceHistory': 'Preserved exactly, including empty native arrays. Separate weekly balances are reconstructed after simulation from invoice/bill/cash-event dates.',
    'comparison': 'Every original paired JSON byte after removing the added arm property and reproducing exact frozen-runner postprocessing; per-arm SHA256 receipts.',
    'annotationBlocks': block_manifest, 'files': files, 'stages': stages,
    'pairedWorldsToReplay': 6480, 'enterpriseHistoriesToMatch': 19440, 'competitorFirmAccountsToExpose': 38880,
    'newEconomicScenarios': 0, 'observedCustomerCollectionsCents': 0, 'financialAuthority': 'NONE',
}
with (HERE / 'source-manifest.json').open('x') as f:
    json.dump(manifest, f, indent=2); f.write('\n')
print(json.dumps({'manifest': str(HERE/'source-manifest.json'), 'originalCoreSHA256': EXPECTED_CORE,
                  'instrumentedCoreSHA256': sha(instrumented), 'manifestSHA256': sha((HERE/'source-manifest.json').read_bytes())}, indent=2))
