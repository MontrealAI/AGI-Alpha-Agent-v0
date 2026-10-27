# A bounded construction that works — and does not pass the novelty gate

This executable probe constructs two-, three- and four-bit hysteretic event recorders. Every allowed internal switching order reaches the same final state, while two externally ordered input pulses leave different memories. The complete finite-model result is positive. The flagship discovery claim is rejected: the construction is ordinary positive-feedback latching, its internal confluence is reproduced exactly by a familiar monotone closure control, and the literature already contains sequential mechanical computation, vectorial path-dependent memory and autonomous event-order recorders.

It is a reusable reference specimen for the AGI ALPHA opportunity search, not evidence of beyond-human foresight, physical fabrication, model superiority, or customer acceptance.

## Reproduce

Only Python 3 standard-library modules are required.

```bash
cd experiments/confluence
python3 study.py
python3 -m unittest -v test_study.py
```

`config.json` was frozen before the first programmatic confirmation at `2026-10-27T19:24:02.667095+00:00`. Its SHA-256 is `dc6897555f3aab38fd42284cb0a8f97c7f950a421494c8123fc413a257166dd0`. `freeze.json` records this. `results.json` records the configuration and source hash. Changing the configuration without an explicit new freeze fails. The design itself was derived by the agent before the freeze, so this is prospective confirmation of a constructed finite model, not a blind discovery comparison.

## Transformation witness

- **Purpose:** infer whether event A preceded event B or B preceded A, from a static readout after both independent input pulses have returned to reference. This two-event interpretation assumes each occurs once. Repeated inputs must retain their true, coarser semantics.
- **Restriction:** independent retained threshold bits record event occurrence but give the same final state for AB and BA.
- **Change:** couple an occurrence latch to an order latch. The second input can activate the order latch only when the earlier occurrence latch is already active.
- **Preserved obligations:** every allowed single-bit update schedule is included; each input is held until settling; there is a common zero reference; repeated inputs and reset are evaluated rather than excluded; final state semantics are checked independently.
- **Acceptance:** distinct AB and BA outcomes, schedule-independent termination, agreement with independent Boolean semantics, successful explicit reset and robust parameter margins.
- **Falsifiers retained:** weak coupling destroys discrimination; an antagonistic example produces different terminal states by update order; an asymmetric feedback example cycles. The checker must report all three.
- **Evidence boundary:** abstract, athermal, settled-state hysterons with dimensionless fields. No physical transducer, manufacturing geometry, aging, thermal noise, dynamic switching, clock, buyer, collection or fabrication is included.

## Exact model

All numeric values below use dimensionless fields; the code multiplies by 100 so nominal calculations use exact integers. Each bit `s_i` is either zero or one. For a held input vector `h`, its effective field is

`H_i(s,h) = h_i + sum_j C_ij s_j`.

A zero bit may switch to one when `H_i >= 1.00`; a one bit may switch to zero when `H_i <= -0.80`. If several bits are unstable, **all possible single-bit update choices** are explored. No priority is used to manufacture determinism.

For the four-bit construction, the state order is `(x,y,z,w)`. Couplings `C_xz=C_zx=0.60` and `C_yw=C_wy=0.60` are the only nonzero terms. The matrix is symmetric and nonnegative. Input A is `(1.20,0,0,0.60)`; B is `(0,1.20,0.60,0)`. Each pulse is followed by zero input. C applies the sum of A and B until settling; R applies `(-2,-2,-2,-2)` until settling, then zero.

The three-bit construction retains `(x,y,z)` and the two-bit construction retains `(x,z)`. The reduced versions are tested as their own models, not treated as physical copies of the four-bit structure.

The independent Boolean oracle for a pulse with flags `a,b` is:

`x' = x or a`

`y' = y or b`

`z' = z or [b and (x or a)]`

`w' = w or [a and (y or b)]`.

R sets all four bits to zero; reduced models project the corresponding bits. This oracle contains no threshold dynamics and is therefore a useful implementation check. It is an analyst-specified control, not a measured human-expert experiment.

### What the four-bit readout means

| Input history since reset | Final readout | Supported interpretation |
|---|---|---|
| None | 0000 | Neither event recorded |
| A | 1000 | A recorded; no B |
| B | 0100 | B recorded; no A |
| AB | 1110 | An A-before-B pair, no B-before-A pair |
| BA | 1101 | A B-before-A pair, no A-before-B pair |
| C | 1111 | Both order flags set under a simultaneous held field |
| ABA or BAB | 1111 | Both directed precedence patterns occurred |
| Any history followed by R | 0000 | Explicit erasure completed |

`C`, `ABA` and `BAB` collide. Therefore the four-bit state does **not** reveal full history or uniquely identify simultaneous events. Arbitrary overlaps of finite-duration physical pulses are outside this settled-input model. Claiming a complete chronology or overlap detector would be task substitution.

## Why all internal orders agree

Under A, B, C and zero reference, no active bit can switch off because fields are nonnegative and the off threshold is negative. Each allowed on-switch can only raise other fields because couplings are nonnegative. Consequently switching is an inflationary, monotone process on a finite Boolean lattice. Any maximal asynchronous sequence reaches the same least fixed point above its starting state. Under R, every active bit is forced off and off-switches can only decrease neighboring fields. This is the familiar monotone/ferromagnetic argument; it is not claimed as a new theorem.

For the symmetric matrix one may also use the coarse discrete energy

`E(s;h) = -sum_i h_i s_i - sum_{i<j} C_ij s_i s_j`.

An allowed on-switch has energy change `-H_i <= -1.00`, and an allowed off-switch has change `H_i <= -0.80`. At fixed input, every allowed transition therefore strictly decreases this energy. This supplies consistency with dissipative switching and excludes cycles in this finite model. It does **not** supply a continuous elastic energy landscape, activation barriers or a manufactured realization.

External AB and BA are different vector paths. Internal update-order independence at a held field does not imply that distinct input paths must commute. The result does not contradict scalar return-point-memory theory and is not a discovery of its failure.

## Confirmation results

| Check | Two bits | Three bits | Four bits |
|---|---:|---:|---:|
| All initial states × five held fields | 20 | 40 | 80 |
| Cases containing internal races | 1 | 8 | 24 |
| Maximum number of complete update schedules | 2 | 6 | 24 |
| Exhaustive words over A/B/C/R, length 0–6 | 5,461 | 5,461 | 5,461 |
| Fresh seeded random words, length 1–64 | 1,024 | 1,024 | 1,024 |
| Oracle disagreements | 0 | 0 | 0 |
| Nonconfluent nominal cases | 0 | 0 | 0 |
| Disagreements with conventional monotone closure | 0 | 0 | 0 |

The nominal audit includes every binary starting state. The three-bit state `100` under B contains a genuine two-choice race: y and z can switch in either order, both reaching `111`.

The tolerance check uses 512 fresh parameter draws **per dimension**, symmetrically perturbing each present edge and independently perturbing thresholds and nonzero drive terms by at most 0.04. This gives 71,680 all-state/held-field checks, with zero observed disagreements or nonconfluent results. The draws use integer steps of 0.01. These are finite deterministic-model checks, not independent physical trials or estimates of real reliability.

An analytic interval calculation covers the full continuous ±0.04 parameter box for this motif: the minimum margin for a required gated activation is 0.08, for direct activation 0.12, for preventing an isolated low input from activating a bit 0.32, for retention 0.76 and for reset 0.48. These margins assume precisely the specified topology and field abstraction.

## Strong controls and preserved failures

1. **Independent hysterons:** deleting all couplings collapses AB and BA to the same readout in every dimension. Interaction is necessary in this particular construction.
2. **Conventional positive-feedback closure:** simultaneous monotone closure matches the proposed asynchronous transition relation exactly on nominal and perturbed cases. Thus the study supplies no superiority over this conventional control.
3. **Independent semantic oracle:** every enumerated history agrees with the Boolean recurrence above.
4. **Weak-coupling mutation:** reducing each 0.60 edge to 0.35 makes the gated field 0.95, below threshold. AB and BA collapse. This demonstrates a real acceptance boundary.
5. **Antagonistic race:** two bits with coupling −1.20 and held fields `(1.10,1.10)` terminate at either `10` or `01`, depending on which unstable bit flips first. The checker preserves both.
6. **Asymmetric cycle:** an intentionally nonpassive pair with couplings −2.00 and +2.00 cycles through all four states. The checker reports the cycle rather than selecting a favorable endpoint.

The acceptance suite contains eight tests and passes. No E-versus-U numerical attribution or human-search superiority is inferred from these checks.

## Prior-art comparison and disposition

- **Sethna et al., 1993:** no-passing, adiabatic dynamics and return-point memory are established antecedents for ferromagnetic hysteresis. Our confluence argument is an elementary monotone-closure specialization, not a new capability theorem. Primary full text: https://arxiv.org/html/cond-mat/9210018v1 ; published DOI https://doi.org/10.1103/PhysRevLett.70.3347 .
- **Liu et al., PNAS 2024:** coupled mechanical hysterons already implement counting, order-sensitive pattern recognition, multi-character driving alphabets and reset. Their simple serial graphs exclude multiple simultaneously unstable hysterons, but moving outside that restriction does not itself establish novelty. Full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC11145188/ . Their generic switching field is `V_i±(S)=v_i±−sum_j c_ij s_j`; serial geometry restricts `c_ij=−d_j/n` for `i≠j`.
- **Teunisse and van Hecke, 2025:** necessary/sufficient design inequalities and transition-graph realizability are already a systematic inverse-design framework. Our threshold compilation cannot be presented as the first such procedure. Primary record: https://arxiv.org/abs/2404.11344 ; DOI https://doi.org/10.1098/rsos.250753 .
- **Meulblok and van Hecke, July 2026:** vectorial input, path-dependent sequential responses and a graph framework extending scalar drive are prior art. Search retrieved the primary abstract; direct full-text open was unavailable during this probe. https://arxiv.org/abs/2607.11179 . No detailed performance comparison is asserted.
- **Cardelli, 2023:** autonomous event-order recording using pairwise detectors and a final readout already exists in a different physical substrate. It explicitly represents first-occurrence preorders and near-simultaneous events, and discusses finite energy and no overflow. Our recurrent-precedence state is not the same memory semantics, and is weaker for reconstructing first occurrence. Full text: https://link.springer.com/chapter/10.1007/978-981-19-9891-1_17 .

The finite construction is real and useful as a reference. Its novelty evidence is insufficient for flagship selection. The retained artifact is the schedule-complete checker, model, semantics and rejection record. Availability of these materials to a successor is not evidence of independent competence transfer or economic retained Alpha.

## Smallest useful next validation

For physical feasibility, map one two-bit reciprocal motif to a calibrated continuous potential or existing tunable mechanical-hysteron geometry, verify metastable branches and simulate actual ramps and damping before fabrication. For discovery, first specify a valuable history property that the identified mechanical/FSM/event-recorder art cannot already satisfy under the same constraints, then construct against that stronger control. A physical copy of this motif alone would validate feasibility but would not resolve novelty.
