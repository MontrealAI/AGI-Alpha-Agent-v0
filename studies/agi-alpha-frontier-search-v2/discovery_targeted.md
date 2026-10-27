# Targeted discovery: measurement instruments

**Decision: no flagship selected from this pass.** Two serious candidates were investigated beyond the occupied coordination, reserve-capacity, diagnostics, and workflow-transfer families. The first is directly anticipated; the second remains an explicit mathematical research question without a constructed new useful capability. These are additive post-freeze exploratory results, not a third controlled discovery arm. No U/E candidate files were inspected.

## 1. Rank-only quantitative diffraction

**Beneficiary and proposed output.** Fragile-sample or transient-imaging operators need quantitative complex-field measurements despite detector-response uncertainty. The proposed connection was to replace numerical detector values with pairwise intensity orderings.

**Documented comparison.** Mroueh (2014) already studies paired one-bit coded diffraction, rank-preserving unknown nonlinear distortion, super-resolution, and blind deconvolution [S1]. The generic proposal therefore lacks substantive novelty. The proposed extra requirement—absolute quantitative amplitude—also fails with ordinal data alone.

**Executed cheap probe.** For an eight-dimensional complex signal and 64 paired measurements, x and 2x produce all identical ordinal bits while physical power differs by a factor of four. This is a finite example of scale invariance, not a new theorem. Normalizing both objects would change the quantitative purpose.

**Smallest worthwhile next experiment.** Specify a new physical observable that resolves the ambiguity under the same dose, exposure, and calibration restrictions; prove injectivity for its stated object class, then compare it with ordinary holographic reference methods. Adding a familiar reference alone is not a novelty claim: reference design already has substantial prior art [S5].

## 2. Irregular-access complex-field reconstruction

**Beneficiary and proposed output.** An imaging operator may be unable to collect a regular scan because positions are physically inaccessible or dose-sensitive. The proposed construction would recover a globally coherent field directly from allowed positions, with explicit assumptions and stability bounds.

**Documented gap.** Phasebook (2025), Question 8.5, asks for Wigner-distribution deconvolution (WDD) on arbitrary sufficiently overlapping scans [S2]. This is a concrete mathematical lead. It does not establish that arbitrary scans are unreconstructible by existing methods. Live WDD is already studied by Bangun et al. [S3]; random probe subsampling and low-dose reconstruction are already studied by Robinson et al. [S4].

**Executed cheap probe.** Six three-pixel scans of a 16-pixel object yield 96 diffraction intensities. Two objects with identical known support and reversed relative phase between disconnected illuminated components yield exactly identical intensities. Their best global-phase-aligned relative difference is sqrt(2). Local overlap inside each component cannot supply the missing relation. This counterexample does not solve or refute the properly conditioned Q8.5.

**Smallest decisive construction.** Derive a finite nonuniform WDD factorization with explicit object, probe, overlap, noise, dose, and position assumptions. Test 16–64-pixel cases against strong iterative reconstruction, inpainting plus reconstruction, and conventional lifted linear algebra with identical information. Require a preserved useful output that the admissible controls cannot deliver. A runtime improvement or an alternate solver alone fails the flagship requirement.

**Decision.** Keep the mathematical lead, but do not build a flagship paper around it yet. No new identity, theorem, or uniquely enabled accepted outcome was constructed in this pass.

## What was established

The executed work consists of two finite identifiability counterexamples and documented novelty exclusions. It establishes neither a physical instrument nor profitable delivery. No numerical Operational Alpha, retained Alpha, buyer demand, or foresight advantage was inferred. A future instrument venture would require human-led R&D comparisons and independently modeled customer value; prior study profits do not transfer.

The successor can inherit source-linked problem statements and executable failure cases. An ordinary library contains the same information, so this inheritance is not evidence of a moat or retained Alpha.

## Reproduction and evidence boundaries

Run `python flagship_round2/discovery_targeted_probe.py`. It uses Python's standard library and seed 20261027, writes `discovery_targeted_probe_results.json`, and asserts the stated ambiguity results. These are post-selection exploratory probes, not protected confirmation cases. Eight search queries and five page opens were used; two queries and one open returned oversized truncated output and were counted without using unseen evidence. Full query and source records are in `discovery_targeted.json`.

## Sources

- **S1.** Y. Mroueh (2014), [Robust Phase Retrieval and Super-Resolution from One Bit Coded Diffraction Patterns](https://arxiv.org/abs/1402.2255), v2.
- **S2.** [Phasebook: a survey of selected open problems in phase retrieval](https://link.springer.com/article/10.1007/s43670-025-00117-0) (2025), section 8.2, Question 8.5.
- **S3.** A. Bangun et al. (2022 preprint; 2023 journal), [Wigner Distribution Deconvolution Adaptation for Live Ptychography Reconstruction](https://arxiv.org/abs/2212.01309).
- **S4.** A. W. Robinson et al. (2023), [Simultaneous High-Speed and Low-Dose 4-D STEM Using Compressive Sensing Techniques](https://arxiv.org/abs/2309.14055), v3.
- **S5.** [Holographic Phase Retrieval and Reference Design](https://arxiv.org/abs/1901.06453) (2019); search-stage source, full article not reviewed in this pass.
- **S6.** [Single-shot hyperspectral wavefront imaging](https://www.nature.com/articles/s41467-025-66847-w) (2026); search-stage rejection of a generic combined instrument, full article not reviewed in this pass.
