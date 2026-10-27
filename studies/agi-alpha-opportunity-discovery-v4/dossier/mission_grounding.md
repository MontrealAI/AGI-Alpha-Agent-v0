# Thermal candidate: pre-selection mission-grounding challenge

**Date:** 27 October 2026. **Status:** research-only challenge; no flagship code, physical experiment, engineering certification, or customer inquiry. Six additional search queries and three deep primary sources were used, within the authorized allowance.

## Decision

**This search did not establish two substantive application settings with an unresolved, consequential single-face ambiguity after including the information a competent recipient already possesses. Do not select the thermal candidate as the flagship on the present evidence.**

Two real application settings are grounded below: anisotropic Ga2O3 transistor thermal design and tilted-laminate transverse thermoelectrics. Both have inspectable geometry, material information, and useful engineering questions. They are not two successful opportunity demonstrations. In the first, the most directly inspectable device orientation removes the proposed cross-plane ambiguity. In the second, the published construction and constituent measurements provide the tensor through a cheap established calculation. Artificially withholding that information would manufacture an advantage.

A different-cut Ga2O3 evidence-to-device problem remains a technically coherent **researcher-specified conditional scenario**. It does not presently provide a second demonstrated gap, a consequential feasibility crossing, or a reason to prefer this candidate over the other opportunities. A bounded countermodel and finite-device analysis could still be scientifically useful, but its value must be established rather than assumed.

| Grounding requirement | Ga2O3 transistor | Tilted thermoelectric laminate |
|---|---|---|
| Independently useful mission | Maximum channel temperature / allowable power / substrate choice | Transverse thermopower and choice of thermal boundary arrangement |
| Inspectable application model | Published analytical model and COMSOL comparison | Published transport equations and experimental geometry |
| Material evidence | Measured conductivity tensor from an independent study; temperature-dependent model inputs | Measured constituent transport properties and known layer ratio/tilt |
| Quantity can depend on tensor details | Yes in general; actual orientation and geometry matter | Yes; transverse temperature gradient explicitly depends on off-diagonal conduction |
| Single-face family survives all known information? | Not for the directly sourced (010) measurement/device orientation; possible under a separately supplied different-cut evidence scenario | Not under the published ideal laminate model with known angle and constituent properties |
| Consequential unresolved effect demonstrated here? | No | No |
| Present status | Useful negative control; different-cut scenario requires another grounding step | Useful negative control and prior art; reject as a manufactured metrology gap |

## 1. Ga2O3 MOSFET thermal design

### Original public mission and inspectable model

Jia et al. model maximum channel temperature for Ga2O3 MOSFETs with native or higher-conductivity substrates. Their defaults are a 2 μm gate, 150 μm device length, 300 nm channel, and 500 μm substrate. The model applies gate heating, an isothermal bottom heat sink, and adiabatic remaining surfaces. Cross-plane transport is [010]; lateral transport is [001]. The paper compares an analytical model with COMSOL calculations and considers temperature-dependent conductivity. These are published simulation conditions, not measured performance of a customer device. A useful decision is the allowable dissipated power or substrate configuration under a specified channel-temperature limit. No such customer limit or economic value has been elicited here. [M1]

Klimm et al. independently report laser-flash measurements on oriented crystal slices and give, at 300 K, a crystal-physical tensor with entries λ11 = 12.13, λ22 = 24.26, λ33 = 14.09, and λ13 = −0.992 W m−1 K−1; other off-diagonal entries vanish by monoclinic symmetry. Their Cartesian e2 axis is parallel to crystallographic b. They report approximately ±1° orientation/miscut errors. Their full tensor and its temperature dependence are available evidence, not a hidden answer we may exclude from the expert baseline. The measured specimens and Jia's modeled device are different sources and are not one validated material/device dataset. [M2]

### Why the obvious flagship story fails

For a surface normal to b = [010], place the two other Cartesian directions in the surface plane. The cross-plane coupling vector is then zero by the independently known crystal symmetry. The measured in-plane Schur matrix equals the actual in-plane conductivity block. Consequently, the source theorem's unrestricted two-parameter family contains tensors violating the known symmetry. A method cannot claim useful global countermodels by retaining those inadmissible tensors.

Uncertainty in actual measurements, temperature dependence, orientation, or a new material lot remains an ordinary important engineering issue. It does not restore the unrestricted exact ambiguity automatically. A fair E arm can use the crystal constraint, published tensor, conventional thermal modeling, and extra material measurements when needed.

The Jia boundary model also must not be modified casually. With off-diagonal terms, an insulated boundary means zero **normal heat flux**, not simply zero coordinate derivative. Reusing its diagonal-model boundary expressions in a full-tensor solver would silently change the physical purpose. Any generalization requires a separately verified flux formulation.

### A narrower conditional scenario that is mathematically possible

Suppose a new specimen is available only through a (100)-face surface experiment, with independently registered crystal axes, and the application uses a different orientation. This is a **proposed evidence restriction**, not the actual evidence situation documented by M1–M2. In the crystal-physical coordinates of M2, set a = λ11 > 0, b = λ22 > 0, and s = λ33 − λ13²/a > 0. The family

\[
K(r)=\begin{pmatrix}
a&0&r\\
0&b&0\\
r&0&s+r^2/a
\end{pmatrix}
\]

preserves the (100)-face invariants while respecting this monoclinic zero pattern. The [001]-direction component changes with r. Thus different-cut evidence can leave information relevant to a different application unresolved, even though a (010)-face experiment has no corresponding cross-plane null family under that symmetry.

This algebra does **not** demonstrate a consequential difference in the published device's maximum temperature. That requires the full device model with correct boundaries, admissible material/registration uncertainty, and an independent computation. In particular, symmetry, existing multi-direction measurements, fabrication information, and scientifically justified bounds must constrain r. One cannot give it a large arbitrary interval to force a crossing.

For scale only, the M2 room-temperature numbers imply s ≈ 14.009 W m−1 K−1. Setting r from −0.992 to zero within this formal family changes λ33 by about 0.081 W m−1 K−1, roughly 0.58%. This is an algebraic diagnostic, **not** a measured uncertainty interval, device-temperature estimate, or claimed saving. It cautions against assuming large economic consequences from the existence of a null direction.

### Conventional method and concrete next gate

The conventional route uses available tensor data in a verified finite-element thermal model, obtains an appropriately oriented material measurement if necessary, and performs sensitivity/uncertainty analysis against the actual temperature constraint. The cheap analytical model is also a valid screening tool within its assumptions. No autonomous instrument is needed to apply an already-known tensor to an already-supported geometry.

To make this setting a credible candidate, an independently useful new orientation/geometry must be identified, and the available evidence must actually leave a decision-relevant range after all legitimate prior information. The study may explicitly supply a new-lot scenario and computational geometry, but it must then report a constructed scenario, not a public observed metrology failure. In the current search, that additional grounding is unfinished.

## 2. Tilted multilayers for transverse thermoelectric generation

### Original public mission and physical evidence

Ando et al. experimentally study thermal-gradient redirection and transverse thermopower in Co2MnGa/Bi-Sb-Te multilayers. Their slabs are 10 × 8 × 1 mm, with reported layer ratio 0.59 and selected tilt angles. The heater/sink spacing is about 6 mm, with a central thermal-imaging region; the experiment is approximately adiabatic there. The reported constituent conductivities are 18.7, 1.2, and 1.5 W m−1 K−1 for the three listed materials. The paper supplies transport equations and compares measured gradients/thermopower with established laminate calculations. This grounds a useful engineering question: how should boundary arrangement and laminate orientation be chosen for transverse output? It does not establish commercial adoption or an unmet characterization service. [M3]

### A mission quantity really can vary across a formal surface-equivalent family

In a simplified two-dimensional passive thermal block, let the measurement surface have y as its normal. Write a family with fixed positive c and s as

\[
K_y(r)=\begin{pmatrix}s+r^2/c&r\\r&c\end{pmatrix}.
\]

Under a locally adiabatic transverse condition, the ratio of temperature gradients is

\[
\frac{\partial_xT}{\partial_yT}=-\frac{r}{s+r^2/c}.
\]

The quantity varies with r even though the formal same-face invariants remain fixed. This illustrates the connection between measurement equivalence and a potentially useful mission quantity. It is a general mathematical diagnostic, not a reproduction of the experiment or a claim that these family members satisfy the published laminate's full independent information.

### Why this is not an admitted opportunity

The source's known laminate orientation, layer ratio, and constituent measurements supply additional constraints. Under its ideal effective-medium model, these determine the tensor by the conventional arithmetic/harmonic mixing and rotation calculation. The original authors already calculate and measure the relevant transverse gradient. An agent that omits the supplied structure, announces ambiguity, and then “discovers” the known layer angle would be manufacturing a problem.

There is also a measurement-geometry mismatch. The experiment images the broad face while its thermal coupling lies within that plane. The single-face null family concerns couplings between the measured face and its normal; it cannot be invoked by relabeling an in-plane coupling as hidden without changing the evidence geometry. A hypothetical experiment on an edge face is a new acquisition scenario. Homogenization and length scales would also require checking before using an effective tensor in a microscopic thermoreflectance model of these macroscopic layers.

Uncertain interfaces, imperfect construction, nonuniform contacts, or changed boundary conditions could justify additional measurements. This search did not establish an instance where these uncertainties defeat available methods and create a substantial new service opportunity. Adding such unknowns solely to defeat the conventional calculation would not meet the selection standard.

**Decision:** reject as the second qualifying flagship mission. Retain it as a strong prior-art and negative-control case. It is valuable precisely because it forces the instrument to recognize when inexpensive existing structure already resolves the decision.

## 3. What is and is not grounded

The public sources establish real thermal engineering purposes, usable geometries and material measurements, and the importance of respecting symmetry, coordinate conventions, and boundary conditions. They also demonstrate that the original authors and conventional tools already address much of the proposed work.

The research challenge was to find two consequential settings in which the surface-equivalent class still contains physically admissible models producing meaningfully different decisions. That stricter test was **not met**. There is one conditional different-cut semiconductor scenario worth further investigation, but no independently grounded second gap in this bounded search. This is insufficient to justify presenting the thermal candidate as the study's flagship.

A hybrid computational construction is still possible if the project deliberately chooses a research question about evidence transfer across measurement/application orientations. Its supplied geometries, unknowns, priors, and consequences must be explicit. Such a study would need to earn its contribution through independently checked countermodels, protected fresh missions, and superiority to strong existing practice. It should not inherit credibility merely from the published identifiability theorem.

## Exact primary sources and provenance

1. **M1 — Jia, Hu, Han, Liu, Hao (2021).** *Analytical Model for the Channel Maximum Temperature in Ga2O3 MOSFETs.* Nanoscale Research Letters 16, 29. DOI: https://doi.org/10.1186/s11671-021-03490-6 . Full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC7876208/ . Relevant: Methods, Table 1, boundary equations 1–3, conductivity models 4–5, and numerical comparison. The web reader returned the relevant full-text section; a later repeat encountered a browser-check page. No raw COMSOL project was obtained.

2. **M2 — Klimm, Amgalan, Ganschow, Kwasniewski, Galazka, Bickermann (2023 issue; 2022 online copyright).** *The Thermal Conductivity Tensor of β-Ga2O3 from 300 to 1275 K.* Crystal Research and Technology 58, 2200204. DOI: https://doi.org/10.1002/crat.202200204 . Accessible primary article PDF: https://d-nb.info/1274779782/34 . Five-page article read; its supplemental tables were not separately retrieved. The source explicitly distinguishes Cartesian and crystallographic directions and discusses earlier sign/convention problems. Reuse rights must be checked for commercial artifacts; the article states CC BY-NC.

3. **M3 — Ando, Hirai, Adachi, Uchida (2025).** *Adiabatic transverse thermoelectric conversion enhanced by heat current manipulation in artificially tilted multilayers.* arXiv:2502.01944v1, 4 February 2025; published in Physical Review Applied 23, 064061. Versioned preprint: https://arxiv.org/abs/2502.01944v1 ; PDF: https://arxiv.org/pdf/2502.01944v1 . Relevant: methods, Table I, thermal-gradient relation, measured geometry and model comparison. This workstream read the relevant methods/results and did not independently reproduce the experiments.

Downloaded M2/M3 PDFs and their hashes are recorded in `mission_sources_manifest.json`. The earlier dossier's Wang–Ban source remains the identifiability foundation; it is not counted as a newly discovered application need.

## Search log

Six queries screened: Ga2O3 tensor/device orientation; Ando's tilted-multilayer work; tilted graphite heat spreaders; Klimm's full tensor article; laser-crystal thermal-lensing/off-diagonal conduction; and different-cut Ga2O3 thermal device simulations. Primary-source deep reads were limited to M1–M3. Graphite and laser search hits did not supply a better substantiated unresolved mission within this budget and were not promoted into additional candidates.

**Additive research record:** preserve this negative grounding result with the earlier conditional recommendation. Do not erase it or retroactively describe the earlier dossier as having validated the flagship.

## Scope update: evidence-sufficiency audit rather than design qualification

After the challenge above, the parent narrowed the proposed offering to an **evidence-sufficiency audit before commissioning metrology or making a design commitment**. It would deliver verified countermodels or conditional discrete-model bounds and a feasible acquisition plan, without promising physical design qualification. This changes what a bounded computational edition needs to demonstrate; it does not change the preceding source findings.

Under that narrower scope, **two independently published useful mission types can be grounded**: transistor thermal management and transverse heat-routing/thermoelectric design. They can support explicitly source-inspired synthetic request briefs. The device geometries, unknown new-lot properties, initial measurement coverage, customer thresholds, and procurement limits that are supplied by researchers must be labeled individually. A threshold fixed before simulation is prospectively testable, but is still an assumed threshold rather than evidence of customer willingness to pay or a field qualification criterion.

The cases should include an audit that closes immediately using known symmetry or laminate construction. For the different-cut semiconductor scenario, the audit can test whether existing evidence plus legitimate material constraints suffices, and otherwise produce countermodels. For the laminate scenario, the source's known structure normally resolves the tensor cheaply; the correct result is to use that information, not recommend expensive new characterization. These are two substantive audit purposes, but **not two demonstrated positive structural-ambiguity gaps**.

This narrower study can be credible as a computational construction and selective-delivery experiment if its evidence adapters, countermodels, conditional bounds, fresh transfer, and measurement recommendations are independently checked against strong expert practice. A discrete-model certificate must name the finite model set and must not be described as a global physical guarantee. Existing public measurements must remain available to E and E+; their applicability to a simulated new lot can be uncertain, but their existence cannot be hidden. Field deployment still requires new evidence, accountable acceptance, and the intended authorization.

**Revised limited recommendation:** these sources are sufficient to motivate two mission types for the narrower audit suite. They are insufficient to claim two observed unmet metrology markets or a Blue Sky advance before execution. Treat any positive gain as an outcome to test; retain the original no-go finding for the stronger flagship claim and all negative controls.
