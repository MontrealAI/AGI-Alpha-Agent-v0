# Frozen progressive experience result: retire cohort promotion

Source was public before evaluation: `2ca09dae85f28cf440357de93fecea9c85bd57e9`,
tree `1ab009ec14b361f80cc73d8fd74483f6c96976ef`, parent `e4c99ad326576d884811e6b8eabbc9258e61380c`.
The numerical solver/controls and original adverse evidence are unchanged.

**Decision: RETIRE_COHORT_PROMOTION.** No sample enlargement, retuning or production promotion follows this result.

- 64 unique generated tasks x 12 arms x one timing = **768 independently accepted outputs**.
- **8 feasible tasks; 56 infeasible tasks.** These are not 768 productive deliveries.
- All 32 withheld-stop tasks are infeasible. This tests valid negative certificates on new routes, not a demonstrated productive service on that family.
- Fixed 0/4/8/12 training prefixes, same-history rebuild/reset, frozen-first-four, ordinary cache, matrix cache, native warm start and six HiGHS controls.
- Separate verifier actually denied write/socket probes and imported neither candidate nor builder. Shared author, host and libraries; procedural independence only.
- Wall time 51.737s. All monetary costs/profit and independent demand remain UNKNOWN; no calibrated commercial simulation or scientific confirmation claim.

| Training cases | Retained lifecycle CPU s | Strongest control CPU s | Control |
| --- | --- | --- | --- |
| 0 | 1.487991 | 0.598478 | highs-ds-1 |
| 4 | 1.678959 | 0.641411 | highs-ds-1 |
| 8 | 2.013806 | 0.626458 | highs-0 |
| 12 | 2.494901 | 0.606507 | highs-1 |

Stage 12 retained cost is about **311% higher** than the strongest observed control.
At stages 8 and 12 it also fails to beat the frozen-first-four baseline. Reset is slower than retaining compiled assets, but that causal control does not replace the competent conventional comparison. Extra history did not establish useful after-cost improvement.

Lifecycle scope is history acquisition, asset construction/preparation, current-stage compile/solve/serialization and separate verification. The full measured validation remainder is charged to history-using arms, favoring pre-existing fixed controls; its fixed/recurring scaling remains unestablished. Representation bytes and CPU are multiplied by explicitly illustrative SIM rates in RESULTS.json. Maintenance, operator attention, authoring and complete actual money remain unknown. One timing per small case is not a statistical speed claim.

The existing Journal records three minimal experiment records. The existing CostLedger is incomplete and contains no accepted charges; nine typed cost inputs are unknown and unadmitted. No accounting authority or grants were created. Private journal credentials are not included here.

## Verify and reproduce saved evidence

Trusted seal SHA256: `3bacb09810fa4648a4e440c824fac77f0dcf462202e2438616aafabedff490be`.
The historical failed development logs and current source tests are recorded separately from this frozen trial; replay is not fresh evidence.

From a checkout containing this evidence and the unchanged frozen sources, copy the sealed data and reconstruct the exact original source snapshots without executing them:

```sh
python - <<'PYDATA'
from pathlib import Path
import hashlib, json, shutil, subprocess
source = Path.cwd()
published = source / 'evidence/progressive-experience-20261029/cycle-1'
output = Path('/tmp/NEW-progressive-replay')
expected = '3bacb09810fa4648a4e440c824fac77f0dcf462202e2438616aafabedff490be'
assert hashlib.sha256((published/'seal.json').read_bytes()).hexdigest() == expected
seal = json.loads((published/'seal.json').read_text())
for name, digest in seal.items():
    assert Path(name).name == name
    assert hashlib.sha256((published/name).read_bytes()).hexdigest() == digest
output.mkdir(exist_ok=False)
for name in [*seal, 'seal.json']:
    shutil.copyfile(published/name, output/name)
freeze = json.loads((output/'freeze.json').read_text())
for name, digest in freeze['sources'].items():
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    raw = subprocess.check_output(['git', 'show', '2ca09dae85f28cf440357de93fecea9c85bd57e9:' + name])
    assert hashlib.sha256(raw).hexdigest() == digest
    target = output/'source-snapshot'/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
print(hashlib.sha256((output/'freeze.json').read_bytes()).hexdigest())
PYDATA
python -B -m contrib.retained_experience.progressive_check /tmp/NEW-progressive-replay --freeze-sha256 PRINTED_FREEZE_HASH --historical-sealed-trial
```

The first original source snapshot is retained by its source/run owner; its bytes are independently recoverable from the immutable public source freeze and per-file hashes. Public data excludes duplicate source copies and all private journal secrets. Do not overwrite the trial, its seal or the private journal. No service was started and no production setting needs rollback.

A new numerical run follows [the source quickstart](../../../contrib/retained_experience/PROGRESSIVE.md); it is a different exploratory panel, not a rescue or confirmation of this retired cohort. The next productive decision is to keep the incumbent and require independent operator/cohort/demand evidence or a materially different bottleneck before reopening commercial promotion.

## Subsequent review repair

Configured review reproduced two gaps in the original checker: zeroed delivered costs and a noninteger seed could still pass its audit. The original checker/source freeze and verification receipt remain historical records, not sufficient evidence of those two integrity properties. The updated checker independently regenerates the exact two-per-regime panel from a bounded integer seed, binds every resource cost to its observation's execution measurement and checks cost-family attribution.

The explicit historical audit mode admits only this fixed seal and freeze. It verifies every original source snapshot as inert data and records the executing updated verifier separately. It does not requalify the original producer, change a frozen hash, permit source drift in normal qualification, grant authority or create fresh confirmation. The stronger audit passes the same768outputs and leaves RETIRE_COHORT_PROMOTION unchanged. No replacement panel was generated.

The original v1 runtime dependency versions were not frozen in freeze.json. A subsequently observed, isolated Python3.12 Linuxx86-64 profile reproduces the numerical development fixtures and incomplete accounting behavior; it is not retrospective prospective toolchain qualification. See REPRODUCTION.json and the source quickstart.
