# Bounded mathematical reframing: affine recurrence

This separate Alpha driver computes the exact final state of

\[
x_{t+1}=(a x_t+b)\bmod m.
\]

The admitted input language fixes one affine map, canonical integer residues, `2 <= m <= 257`, and `0 <= n <= 4096`. It rejects nonlinear terms, time-varying transitions, floating-point inputs, unknown fields and external tool instructions. This is a known elementary reduction implemented as a reproducible example. It makes no novelty, unsolved-problem, general mathematical-discovery or broad intelligence claim.

The driver stores its charter, development attempts, frozen executable program, shared transformation witness, full confirmation results and logical costs in Alpha's existing signed Journal. Its own schema is **`ti-affine-recurrence/v1`**. It is **not** the source-clause selector's `transformational-intelligence/v1` schema, and current native campaign importers must reject it. No arbitrary Python extension, model, network, wallet, payment, native method-library promotion or external authority is added.

## Reproduce a durable campaign

From a prepared Alpha checkout, choose absent paths outside the repository:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m alpha_factory_v1.core.runtime.successor.transformation_math \
  --campaign-id a013d055-8f61-44ec-8a33-99013116e501 \
  --state /ABSOLUTE/PATH/new-affine-journal \
  --output /ABSOLUTE/PATH/new-affine-evidence.json
```

This explicit example command initializes a new journal and approves only the exact free local mathematical comparison it constructs. The general API requires a separate `approve(campaign_id, binding_digest)` call before `freeze` or `confirm` can evaluate any candidate. Keep the private journal directory private; the JSON export does not contain its signing key. Existing state and output files are never overwritten.

The command performs the actual finite search, freezes its selection, then evaluates the entire committed confirmation census. Exported data grants no execution or spending permission. `journal_checkpoint` requires the original journal for signature/chain verification; a portable checksum alone does not authenticate process claims. Use `AffineDiscovery(Journal(state_path))` to inspect or resume the same approved state after a restart. Journal STOP is checked before each bounded pure phase. No mid-phase external action is possible; this driver is not a process watchdog. A process crash rolls back its transaction, so unrecorded physical compute must not be treated as zero cost.

The checked [expected result fixture](expected-results.json) retains the actual deterministic totals, all-case output digest and driver source hash. The tests compare a fresh full campaign to those bytes and separately check the algorithms against direct recurrence and a matrix implementation.

Run the exact mathematical and lifecycle checks with:

```sh
python scripts/check_python_deps.py
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  python -m pytest -q -o addopts='' -p no:cacheprovider \
  tests/runtime/test_transformation_math.py
```

## The actual transformation and argument

The unchanged frame stores one scalar and performs every update. The reframed state stores the affine map itself as a pair `(p,q)` representing `x -> p*x+q mod m`. Composing `(u,v)` after `(p,q)` produces

\[
(up\bmod m,\; uq+v\bmod m).
\]

Expanding `u*(p*x+q)+v` proves the composition identity. Function composition is associative, and `(1,0)` is the identity. In the binary loop, `B^e` composed with `R` equals the original `F^n`. Writing `e=2k+r` gives `(B^2)^k` composed with `(B^r` composed with `R)`, preserving that invariant. At `e=0`, the accumulated map is exactly `F^n`. No division or prime-modulus assumption is used, so zero/non-invertible multipliers and composite moduli are included.

**Status:** the code retains a human-readable algebraic argument and executable computational evidence. It contains no proof-assistant certificate. A separate technical review may assess the argument; neither a signed local journal nor these tests establishes organizational independence. There is no unresolved conjecture asserted as a theorem.

## Controls, ablations and a negative result

All controls use the same complete tasks and exact integer-equality outcome. The algorithm family is installed by the developer; “automated” means bounded enumeration and selection of those methods, not synthesis of the algebraic identity.

| Role | Actual executable mechanism |
| --- | --- |
| Unchanged frame | Direct scalar recurrence iteration |
| Hand-engineered control | Detect the deterministic orbit's tail and cycle, then recover the requested index |
| Automated candidate | Select the exact method with the smallest total logical execution cost on development cases; freeze before confirmation |
| Unrestricted control | Per-case oracle minimum among every actually executed correct method, using already computed outputs transparently |
| Representation-only ablation | Affine-pair representation with one composition per original step; no binary production shortcut |
| Production-only rejection | Scalar binary skipping is outside the closed language; a modulus-period shortcut has an explicit counterexample |

The development set has nine complete cases: moduli `7,13,29`, multiplier `2`, increment `1`, initial value `0`, and horizons `31,127,511`. It selects affine composition at **801** execution units, versus **837** for cycle detection. Confirmation is the entire 864-case Cartesian product:

- modulus in `5,17,31,97`;
- multiplier in `0,1,2,m-1`;
- increment and initial state each in `0,1,m-1`;
- horizon in `0,1,7,31,127,255`.

Development and confirmation contain no identical complete tasks. The finite census is public and reproducible, with its full ordered input digest committed before execution. It is not hidden, IID-sampled or independently held. A subset, reordered list, duplicate, changed case or reused development task cannot count as that confirmation.

| Method | Confirmation execution units | Exact outputs |
| --- | ---: | ---: |
| Direct | 242,496 | 864 / 864 |
| Cycle detection | 30,204 | 864 / 864 |
| Affine composition, frozen automated selection | 43,488 | 864 / 864 |
| Representation only | 365,904 | 864 / 864 |

The automated selection improves execution cost over direct iteration by **199,008** declared units, but costs **13,284 more** than the hand-engineered cycle control. The decision is **`retain-stronger-cycle-control`**. It never beats the unrestricted oracle. The frozen candidate and its unfavorable comparison remain in history; confirmation does not silently switch the candidate to the winner.

Counting development, all confirmation algorithms, selection and oracle comparisons gives **710,779 logical units**, compared with **242,496** for one direct census. The one-census net difference is **−468,283**. Under this cost model, three additional identical workloads would be needed to reach break-even against direct iteration. Exact equality counts as break-even; strictly positive savings can require one further use. This conditional arithmetic grants no reuse authority and does not establish a practical speedup over cycle detection.

One logical unit counts each specified scalar addition, multiplication or modulo operation, plus declared loop/dictionary/search operations. Integers are bounded; this is not a CPU instruction count or bit-complexity claim. The report retains the cost rules and separates search from execution. Parsing, allocation, journal signing/I/O, human review, energy and device costs are excluded or unknown; provider requests are exactly zero. Timing is measured separately by the command and is not evidence of monetary savings.

## Falsifiers and recovery

`m=5,a=2,b=0,x0=1,n=5` gives `x_n=2`. Replacing `n` with `n mod m` gives `1`, so an unsupported period-equals-modulus assumption is false. Cycle detection explicitly retains a nonperiodic tail; the tests also exercise `m=8,a=2,b=0,x0=1` before its fixed point. Small horizons and short cycles can favor the original or hand-engineered method. A zero-horizon development tie keeps direct iteration.

A source, charter, allowance or instrument change invalidates approval and requires a new campaign. A budget-exhausted or mathematically falsified confirmation is terminal, retains charged units and available failed/partial evidence, clears approval, and reports no gain. The same exact terminal input replays history without spending again; it cannot be replaced by a more favorable sample. Normal concurrent/restarted operations execute a phase once. These are local engineering checks, not independent experimental custody or a production qualification.

Original paper files, links, native source-selector behavior, measurement accounting, method-library rules and old campaign records are untouched.
