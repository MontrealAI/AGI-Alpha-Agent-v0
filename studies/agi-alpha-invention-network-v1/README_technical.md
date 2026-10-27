# A tangible learned capability: a residual-corrected PDE checkpoint

This experiment executes a conventional numerical learning system authored by the research team. It does **not** execute an autonomous frontier-model invention campaign. Its tangible learned object is an orthonormal solution basis whose columns change after actual solved experiences. A transferred basis supplies the next agent's initial solution; a strong ordinary numerical method corrects that solution to the same accuracy required of the baseline.

The beneficiary is a scientific-software engineer commissioning a verified thermal/diffusion calculation component. The deliverable is a reproducible solver, discrete solution fields, independently checked residuals, and an inspectable checkpoint. A synthetic inverse mission asks a second actor to identify anisotropic conductivity from noisy sensors. A further component chooses informative sensor locations. These are computational artifacts; no physical product, customer payment, live authenticated ENS actor or specialist ASI is asserted.

## Reproduce

Python 3.11+ with NumPy, SciPy and threadpoolctl is required. The executed environment is recorded in every result. From this directory:

```bash
python -m unittest -v test_technical.py
python technical.py develop --out technical_dev_reproduction
```

The archived original development directory is `technical_dev`; the revised, final development directory is `technical_dev_final`. Never overwrite an earlier evidence directory. After source, protocol, selection and checkpoint hashes are frozen, the study owner supplies previously unused confirmation seeds:

```bash
python technical.py confirm --development technical_dev_final --out confirmation_example --seed 9187331 --count 64
```

The command above illustrates the interface only; the actual confirmation seed and source freeze are recorded separately by the study owner. Reproduction of the public confirmation is not a new protected confirmation.

## What changes through experience

Agent A's computational mission supplies twelve accepted thermal response fields under twelve specified operating conditions. Twice-reorthogonalized observed fields form a rank-12 initial checkpoint. The Gym exposes a separate 72-case training pool. Its observation reports current approximate-solution residuals, available cases and remaining actions. Each of at most 32 actions requests one accurate training solve, appends its previously unrepresented solution direction and consumes one unit of the finite action budget. This is residual-directed basis enrichment, not model-weight access or more inference calls relabeled as learning.

Four checkpoints, at ranks 20, 28, 36 and 44, are evaluated on a separate development set. Every candidate and its cost remains recorded. Selection prioritizes accepted outputs and raw approximation quality, not financial gain. The selected checkpoint is copied as `artifacts/v2.npy`, its SHA-256 identity is frozen, and no confirmation result can change it. Checkpoints contain only synthetic training-field directions; no confirmation field, test label or inverse truth is shared.

The three sharing forms remain distinct. The source program is an executable workflow. The numeric basis is a trained component compatible with this exact grid/operator family. A service may run the program with the basis, but invoking such a service does not transfer independent specialist intelligence. Production access/admission is outside this numerical script; the existing source-pinned lifecycle adapter is separately scoped and must not pretend to support generic PDE authority.

## Strong ordinary tools and the baseline upgrade

The method suite contains SuperLU sparse direct factorization, incomplete-LU preconditioned GMRES, and a structure-aware sine-transform preconditioned conjugate-gradient solver. Incomplete LU is nonsymmetric and is deliberately paired with GMRES. The sine-transform preconditioner is SPD and is paired with CG. Both learned methods use exactly that same correction solver and accuracy. Thus a learned checkpoint's only special advantage is its retained initial approximation.

The primary ordinary baseline is selected by complete mean development runtime and then frozen. No test-time oracle selects the fastest method for each protected case. Every valid factor reuse is permitted: the inverse mission's sixteen distinct conductivity candidates produce sixteen distinct matrices, so no repeated factorization of an identical operator is hidden from the comparator.

A separate measured numerical upgrade routes low-conductivity/high-contrast inputs to sparse direct factorization and ordinary inputs to spectral PCG, using a fixed input-feature rule determined before confirmation. This tests obsolescence and adaptation of numerical advantage. It is not a measured frontier-model upgrade; frontier-model performance and prices are handled only in explicitly labeled external scenarios.

## Purpose-preserving numerical acceptance

All methods receive identical sources, boundaries, material parameters, discretizations and exact-correction limits. The final independent checker applies a separately coded flux stencil, requiring relative residual at most 2e-8 and research-reference relative field error at most 2e-6. The raw uncorrected checkpoint is also assessed under fixed, weaker approximation thresholds and can fail even when correction succeeds.

For the symmetric positive-definite discrete operator, a lower bound on its smallest eigenvalue is the sum of the directional Dirichlet Laplacian bounds and minimum reaction term. Since the contrast operator is positive semidefinite, the residual norm divided by this bound upper-bounds discrete solution error. The recorded relative bound uses the approximate solution norm minus this error bound in its denominator. These are floating-point numerical bounds; they are not interval-arithmetic proofs, discretization-error estimates or physical validation.

## Transfer and complementary specialist use

Fresh transfer cases vary anisotropy, heterogeneous contrast, reaction, source locations and source shapes. Deliberately shifted cases have sharper sources, much stronger anisotropy and higher contrast. A good initial approximation can become a bad warm start; every resulting extra iteration and runtime stays in the record.

The inverse mission identifies one of sixteen conductivity pairs from noisy fields. It preserves the same candidate grid and source physics for all arms. A conventional greedy sensor procedure maximizes regularized information in six principal response-variation features; it uses candidate fields, not hidden true parameters or noise. This is a known researcher-supplied method, and no global design optimum is claimed.

The primary equally funded competent-generalist comparator includes that same sensor-design procedure. Fixed sensors are an ablation only. The combination must therefore add value beyond ordinary numerical solution plus competent experimental design. Every arm pays the full cost of its sixteen forward solves, sensor selection, inference and residual checks. Reusing the measured forward outputs across benchmark ablations does not erase their allocated cost.

The initial development inverse cases all succeeded with six sensors and 1.8% peak-field noise, revealing an uninformative ceiling. Those original outcomes remain unchanged. Before confirmation, the revised protocol adds a two-sensor/5% noise challenge while preserving the six-sensor control. The paper must report both conditions, including every failure, rather than selecting whichever looks favorable.

## Timing and cost interpretation

BLAS/OpenMP thread counts are fixed to one, numerical paths are warmed on a public input, and paired execution order rotates by case. Each `complete_s` contains matrix/source assembly, solver setup, reduced approximation where used, exact correction and independent residual verification. Recipient checkpoint load/projection setup is recorded by version. Accurate reference solves are extra research assessment and are recorded separately; they are not an operational truth oracle.

Training, checkpoint construction and all candidate assessment are extra costs where not already included in paid-founder work. Research authoring and review labor were not metered and must not silently receive zero cost. Millisecond savings on this small computational benchmark are not evidence of commercial profitability. The economics should report the reuse or evaluation-cost break-even condition, and clearly identify any expensive-simulator scaling as an assumption.

## Files and evidence

- `technical_protocol.json`: prospective method, split, acceptance and budget specification.
- `technical.py`: executable environment, learner, solver suite, inverse missions and cost recorder.
- `test_technical.py`: mathematical and state-transition checks.
- `technical_dev/training.json`: preserved first campaign, including every training action.
- `technical_dev_final/selection.json`: selected artifact hashes, all candidate outcomes and measured campaign costs.
- `technical_dev_final/founder_mission.json`: computational founder receipt and actual thermal fields.
- Confirmation `case_manifest.json` and `ood_case_manifest.json`: exact fresh inputs.
- Confirmation `solutions.npz` and `ood_solutions.npz`: returned numerical fields and assessor references.
- Confirmation `results.json`: all paired observations, failures, component ablations and measured costs.

The experiment can establish conventional technical learning and measurable numerical transfer. A larger checkpoint, a reduced residual or a successful handoff does not alone establish positive net retention value, network-sharing advantage, an expanded commercial frontier or autonomous scientific invention.
