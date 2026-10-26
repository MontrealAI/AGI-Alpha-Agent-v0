import difflib, hashlib, json, pathlib

root=pathlib.Path(__file__).resolve().parent
original=root/'inherited/market/src/market.mjs'
source=original.read_text()
expected='52b7d83b57de1ca1cf43e444cedb3639193c91b2d6816f3ba86f9463dd904f27'
assert hashlib.sha256(original.read_bytes()).hexdigest()==expected
replacements=[
 ("from '../canonical/shadow-ledger.mjs'", "from './inherited/market/canonical/shadow-ledger.mjs'",1),
 ("export const SCHEMA = 'agi-alpha-strategic-market/v1';", "export const SCHEMA = 'agi-alpha-strategic-market-transfer/v1';",1),
 ("  allMoneyIsAssumed:true", "  activeComputeAndToolCents:null, activeMechanicalWallSeconds:null, activeMechanicalCpuSeconds:null,\n  allMoneyIsAssumed:true",1),
 ("assert(['full-history','adoption-only'].includes(c.investmentCostBasis)", "assert(['full-history','adoption-only','prospective-reconstruction'].includes(c.investmentCostBasis)",1),
 ("  assert(c.allMoneyIsAssumed===true", "  for(const k of ['activeComputeAndToolCents','activeMechanicalWallSeconds','activeMechanicalCpuSeconds'])\n    assert(c[k]===null||(typeof c[k]==='number'&&Number.isFinite(c[k])&&c[k]>=0),`Invalid ${k}`);\n  assert(c.activeComputeAndToolCents===null||Number.isSafeInteger(c.activeComputeAndToolCents),'Integer active compute/tool cents required');\n  assert(c.allMoneyIsAssumed===true",1),
 ("selectedRoute:'adopt-existing',selectedProspectiveCostCents:adoption,\n    chargedCents:c.investmentCostBasis==='full-history'&&c.historicalCostTiming==='at-adoption'?history+adoption:adoption", "selectedRoute:c.investmentCostBasis==='prospective-reconstruction'?'reconstruct-tested-asset':'adopt-existing',\n    selectedProspectiveCostCents:c.investmentCostBasis==='prospective-reconstruction'?reconstruct:adoption,\n    chargedCents:(c.investmentCostBasis==='full-history'&&c.historicalCostTiming==='at-adoption')||c.investmentCostBasis==='prospective-reconstruction'?reconstruct:adoption",1),
 ("function unitCost(c,active){return round(providerMinutes(c,active)*c.hourlyProviderCents/60)+c.computeAndToolCents;}", "function unitCost(c,active){return round(providerMinutes(c,active)*c.hourlyProviderCents/60)+\n  (active&&c.activeComputeAndToolCents!==null?c.activeComputeAndToolCents:c.computeAndToolCents);}",1),
 ("function invest(f,week,c,seed,arm,recentAccepted,decisions){", "function invest(f,week,c,seed,arm,recentAccepted,decisions,asset){",1),
 ("asset:ASSETS[arm]", "asset",1),
 ("full,week,ASSETS[arm].sha256", "full,week,asset.sha256",1),
 ("(used.enterprise+1)*c.measuredMechanicalWallSeconds", "(used.enterprise+1)*(enterprise.assetActive&&c.activeMechanicalWallSeconds!==null?c.activeMechanicalWallSeconds:c.measuredMechanicalWallSeconds)",1),
 ("(used.enterprise+1)*c.measuredMechanicalCpuSeconds", "(used.enterprise+1)*(enterprise.assetActive&&c.activeMechanicalCpuSeconds!==null?c.activeMechanicalCpuSeconds:c.measuredMechanicalCpuSeconds)",1),
 ("  const c=validateConfig(supplied),buyers=", "  const asset=arm==='A'?null:(options.asset||ASSETS[arm]);\n  const c=validateConfig(supplied),buyers=",1),
 ("invest(f,week,c,seed,arm,priorAccepted,decisions);", "invest(f,week,c,seed,arm,priorAccepted,decisions,asset);",1),
 ("ASSETS[arm]?.id", "asset?.id",1),
 ("ASSETS[arm]?.sha256", "asset?.sha256",1),
 ("productionEvidence:'Inherited6/6 and new joint-tuple4/4 scoped assessments each arm; no field-reliability estimate inferred.'", "productionEvidence:options.productionEvidence||'Inherited6/6 and new joint-tuple4/4 scoped assessments each arm; no field-reliability estimate inferred.'",1),
]
for before,after,count in replacements:
    actual=source.count(before)
    assert actual==count,(before,actual,count)
    source=source.replace(before,after)
dest=root/'market-transfer-core.mjs'
dest.write_text(source)
(root/'market-transfer-core.patch').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True),source.splitlines(True),fromfile='inherited/market/src/market.mjs',tofile='market-transfer-core.mjs')))
(root/'core-derivation.json').write_text(json.dumps({'schema':'agi-alpha-market-core-adaptation/v1','original_sha256':expected,'adapted_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'source_preserved':True,'canonical_ledger_changed':False,'adaptations':['Explicit exact financed asset descriptor selected by adapter; original producer remains the default for historical replay.','Active source-intake compute/tool and machine-budget inputs support measured workflow resources with conditional prices.','Prospective reconstruction charges the complete explicit bound at investment decision time. This is modeled reconstruction, not retrospective financing of observed authorship.','No added customer demand, review, integration, quality or price premium.','Historical procurement, trust, competition, refunds, reserves, forecasts, cash and canonical ledger mechanics retained.'],'replacement_count':len(replacements)},indent=2)+'\n')
print(dest)
