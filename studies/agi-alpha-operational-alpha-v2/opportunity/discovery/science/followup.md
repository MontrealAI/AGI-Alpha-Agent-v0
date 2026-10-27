# H4 follow-up: an identifiable research question before another optimizer

**Date:** 27 October 2026. **Status:** bounded source investigation; no simulator, fitting campaign, physical experiment or sale.

**Subsequent addendum:** `s3_assessment.md` records a distinct, stronger candidate identified from the published identifiability integration gap: qualification of a reused model for a new requested prediction. It does not revive the rejected biological-discovery claim. After the parent authorized the connector continuation, thirteen source files were recovered and pinned; `h4_source_manifest.json` supersedes the initial asset-retrieval limitations below. The earlier failed attempts and selection reasoning remain preserved.

## Decision and correction to the first dossier

Absence of a paying counterparty or a live experiment is **not by itself** a reason to reject a computational research opportunity. A useful, independently checked experimental plan under explicit model assumptions can be a valid deliverable. The first dossier was too restrictive where it treated those missing observations as automatic flagship disqualifiers. This follow-up preserves that earlier assessment and corrects the selection standard.

Nevertheless, the investigated H4 direction should **not yet be selected as the flagship**. Its broad published biological question already has a substantive answer. The available evidence identifies limitations of the present measurement/model formulation, but does not establish that the proposed extra measurement resolves a specific remaining biological distinction. A small instrument that exposes those limits is defensible research; claiming discovery of a new consequential biological opportunity would require more.

## What the original study actually asked and answered

Blasi and colleagues asked how combinatorial H4 acetylation patterns arise in Drosophila cells. Their reported comparison rejected purely nonspecific and site-specific explanations in favor of motif-dependent rates. The resulting ensemble converged on four pathways; three received validation using separate enzyme-depletion data. [F1]

That is appreciably stronger prior evidence than “a model was fit to steady-state data.” A new edition must not rediscover the general need for motif specificity. The abstract's fourth, unvalidated pathway is a possible lead, but it does not establish that the pathway remains unresolved in 2026, identify its exact mechanistic alternatives, or specify a new discriminating assay. The publisher full text was blocked and the university repository explicitly lacked it. I did not infer details that were unavailable.

## The concrete public computational starting point

The official PEtab Select case `0009` represents a 16-state mass-action network with 32 acetylation and 32 reverse reactions. Its reported dataset has 252 LC–MS observations of 15 motifs. K5K16 was excluded because it fell below the quantification limit. Data are encoded at infinite time, and the shared deacetylation rate is fixed to one. The noise specification is log-normal with a fixed parameter in this formulation. [F2]

The case provides model-space and calibration inputs, an initialization, and an expected selected model. The latter contains seven motif-specific factors plus the basal rate. This is a useful reproducibility input, but handing its favorable initialization or expected result to one arm would contaminate an alleged discovery comparison. [F2]

The 2026 paper makes a reproducibility archive available through DOI **10.5281/zenodo.17185040** and connects PEtab Select to COPASI, Data2Dynamics, PEtab.jl and pyPESTO. Its future-work discussion explicitly identifies identifiability as relevant to model-selection validity. [F3]

## Two information limits that invalidate an easy success story

These are analytical consequences of the stated model, not new biological findings.

### 1. A sixteenth abundance is not automatically a sixteenth independent observation

Let the normalized closed-network state be \(x\), with \(\sum_{i=1}^{16}x_i=1\). If fifteen components are observed without error, then the remaining abundance is fixed by conservation:

\[
x_{\mathrm{K5K16}}=1-\sum_{i\ne\mathrm{K5K16}}x_i.
\]

Directly quantifying the missing motif could improve precision, expose normalization error or help handle censoring. It does **not**, solely by adding another concentration to this closed model, guarantee new structural information. That claim must be tested against a baseline that already uses the conservation constraint and the actual observation/noise model.

### 2. Equilibrium abundance cannot set an absolute reaction clock

For a transition generator \(Q\), a stationary distribution satisfies \(Qx^*=0\). Multiplying all physical rates by any positive scale \(c\) gives \((cQ)x^*=0\) with the same equilibrium, while transient trajectories change from \(e^{Qt}x(0)\) to \(e^{cQt}x(0)\).

Consequently, equilibrium data alone cannot determine physical sampling times. Fixing one rate to one is a normalization, not evidence that its value is one per minute. A credible transient design must obtain a calibrated rate scale, a defensible scale interval, or return a dimensionless plan with that unresolved obligation explicitly attached. Inventing a convenient clock would manufacture feasibility.

These are examples of an instrument producing a useful stop or qualification requirement before expensive exploration. They are not proof that all H4 mechanisms are unidentifiable or that no experiment can distinguish them.

## A smallest defensible instrument, if this direction is continued

**Offer:** an evidence-linked measurement sufficiency and experiment-design packet for the stated H4 model family. Its decision is whether the supplied observations and allowed assay changes can distinguish a *named pair or set of mechanistic alternatives* under a frozen uncertainty and cost envelope. The output may be a robust measurement plan, an exact information-limit witness, or an explicit unresolved obligation.

The instrument should not begin with arbitrary synthetic competing networks. It should recover the original ensemble or another independently justified set of plausible alternatives from the public study and its data, identify which biologically relevant prediction differs, and verify that the alternatives remain acceptable after competent calibration and identifiability analysis. Numerical AIC ties alone are insufficient evidence of a meaningful biological distinction.

Candidate changes to assess, without assuming benefit, are:

1. **Improved quantification of the censored motif.** Accept only a precision or decision benefit that survives a baseline using normalization and a proper censoring/noise treatment. Do not count it as a new independent dimension by construction.
2. **A calibrated time-course observation.** Retain the original LC–MS meaning of each observable; supply a physically supported clock, sampling envelope and achievable noise. A plan conditional on a scale interval is legitimate; a plan with invented physical times is not.
3. **A specified enzyme perturbation.** Reuse the original depletion evidence as existing knowledge. An additional perturbation must identify its intervention-to-rate mapping and uncertainty. Changing arbitrary model rates is not automatically an available biological action.

### Fair baselines and causal separation

The baseline must have PEtab-compatible calibration, existing model-selection algorithms, conservation constraints, structural/practical identifiability checks, and established uncertainty-aware experimental-design methods. No new solver is required for Operational Alpha: a better source-to-model-to-assay workflow could count if it helps a fresh recipient produce more accepted plans at matched resources.

To separate representation value from discovery-process value, give the successful model/observation formulation to the original solver and repeat the fresh mission. If the difference disappears, report the value of the supplied structure. Compare an executable retained workflow with an ordinary library containing the same artifacts and permissions before attributing any benefit to graph organization.

### Prospective acceptance

Before comparing U, E and E+, freeze the named scientific distinction; admissible model alternatives; observation semantics; uncertainty set; assay menu; total resource budget; required error control; time horizon; and criteria for justified abstention. Independent checks should confirm mass conservation, positivity, units, clock treatment and absence of target-answer leakage. A claim of discrimination must survive fresh parameter/noise cases drawn from the declared uncertainty envelope and competent conventional alternatives.

Those generated cases test conditional computational performance. They do not establish biological truth. A delivered plan can still be useful without a wet experiment if its assumptions, feasibility obligations and scope are explicit.

## Commercial arrangement at this stage

The candidate sale is the bounded design/qualification packet, rather than a guaranteed biological result. Its H reference should be a matched expert modeling service, estimated transparently until quotes exist. A price hypothesis may be tested in the enterprise model without pretending it is observed willingness to pay.

A joint commissioning arrangement would be relevant only if separate prospective projects require the same adapter or measurement representation. Participant need and technical compatibility must be established independently of the constructed shared core. Each buyer may commission privately, use the existing tools, defer, or decline. An accepted design milestone can trigger payment, while unresolved data rights or physical parameters prevent progression to the next milestone. The seller must fund initial work and support obligations; a refundable advance is not earned profit.

No participating laboratory, budget or price was established in this follow-up. That limits the commercial claim, but it does not invalidate a transparently scoped computational experiment.

## Asset and rights readiness

The exact DOI and documented case paths are in `followup_manifest.json`. The PEtab Select repository showed a BSD-3-Clause root license during the initial exploration. That does not by itself settle all underlying scientific data or original-paper rights. The immutable Zenodo archive, original supplementary material and exact repository commit were **not successfully retrieved** in this follow-up. They must be pinned and inspected before implementation or redistribution. Mutable `main` and `stable` references are not source freezes.

The bounded retrieval used six new search queries, seven web-open attempts and one failed Git retrieval. No protected access was attempted and no permission boundary was bypassed. Failed attempts are preserved.

## Recommendation

Keep H4 as a concrete **measurement-sufficiency scoping candidate**, not the flagship. Continue only if the public original ensemble or later literature establishes a named, consequential remaining mechanistic distinction and enough physical constraints for a noninvented experiment-design envelope. Otherwise retain the conservation/clock witnesses as general verification lessons and stop this direction. A live sale or wet experiment is optional for that next computational step; a real scientific purpose and honest acceptance are not optional.

### Sources

- **F1:** Blasi et al., 2016, DOI https://doi.org/10.1016/j.cels.2016.01.002 ; accessible primary abstract at https://epub.ub.uni-muenchen.de/44042/ . Original full text was not available in the retrieved repository.
- **F2:** Official case documentation, https://petab-select.readthedocs.io/en/stable/examples/test_case_0009.html . Mutable version; informative but not a frozen artifact.
- **F3:** Pathirana et al., 2026, https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1014774 ; reproducibility archive identified as https://doi.org/10.5281/zenodo.17185040 . Archive retrieval failed here.
- **F4:** Existing experimental-design methods: https://arxiv.org/html/2506.11311v1 . Prior source from the first exploration; no new query was charged for it.
