# SPDX-License-Identifier: Apache-2.0
"""Create a reviewable pre-outcome closure; this cannot approve or run outcomes."""
import datetime, hashlib, json, pathlib

base=pathlib.Path(__file__).resolve().parent
study=base.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=set()
for p in base.iterdir():
    if p.is_file() and p.name not in ['candidate-freeze.json','freeze.json']:
        paths.add(p.relative_to(study).as_posix())
paths.update(['market/production-followup.json','results/independent-followup-audit/summary.json',
 'protocol/asset-B.json','market/transfer-protocol.json','market/transfer-scenarios.json',
 'market/transfer-adapter.mjs','market/market-transfer-core.mjs','market/core-derivation.json',
 'market/inherited/market/src/market.mjs','market/inherited/market/canonical/shadow-ledger.mjs',
 'market/inherited/market/canonical/automated-costs.mjs'])
asset=json.loads((study/'protocol/asset-B.json').read_text())
for f in asset['sourceClosure']:
    assert sha(study/f['path'])==f['sha256'],f['path']
    paths.add(f['path'])
freeze={'schema':'agi-alpha-accepted-ab-diagnostic-freeze/v1',
 'status':'AWAITING_ROOT_APPROVAL_BEFORE_AB_DIAGNOSTIC_OUTCOMES','approvedBy':None,
 'preparedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'protocol':'market/accepted-ab-diagnostic/protocol.json',
 'scenarios':'market/accepted-ab-diagnostic/scenarios.json',
 'production':'market/accepted-ab-diagnostic/production-accepted-ab.json',
 'exactTestedBManifestSHA256':sha(study/'protocol/asset-B.json'),
 'originalThreeArmCampaignStatus':'GATED_UNEXECUTED','marketOutcomesExecuted':False,
 'files':[{'path':p,'sha256':sha(study/p),'bytes':(study/p).stat().st_size} for p in sorted(paths)]}
with (base/'candidate-freeze.json').open('x') as f:json.dump(freeze,f,indent=2);f.write('\n')
print(json.dumps({'status':freeze['status'],'files':len(paths),'candidateFreezeSHA256':sha(base/'candidate-freeze.json')}))
