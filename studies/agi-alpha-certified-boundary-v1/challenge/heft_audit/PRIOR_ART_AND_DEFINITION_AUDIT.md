# Independent conventional challenge: one-dimensional IRDCS heft

Audit date: 2026-10-27. Workstream: `/root/conventional_challenge`.

## Conclusion and its limits

The proposed certificate addresses the lower-heft question in Gerry Myerson's MathOverflow answer 499017 without changing the useful mathematical requirements. The retrieved current answer, last edited 17 August 2026, still explicitly asks whether a cover with heft below 0.98 exists. Its August updates settle separate questions: divisibility of all moduli by four, and examples with heft exceeding 1.07. Neither update settles the lower-heft question.

The strongest general one-dimensional lower bound located in the primary sources inspected is **h > sqrt(8)-2 > 0.828**, Emanuel's 2011 thesis, Appendix C, Theorem C.1, printed page 215. The main-text lower bound on printed pages 26–29 tends to 0.75 and is superseded by Appendix C. A valid universal bound above 0.98 would therefore improve the inspected primary result and answer Myerson's explicit lower-threshold question. This bounded literature search cannot establish universal priority or absence of unpublished work. The result should be described as a computer-assisted theorem submitted for research review, with novelty scoped to the cited literature and public problem statement.

The revised polynomial certificate is consistent with the primary definition. Manual algebraic review found no normalization, domain, or sum-direction error. Exact independent certificate checking was performed by the separate lineage workstream, whose results must be cited as that workstream's execution rather than attributed to this literature auditor. This audit did not independently rerun the complete symbolic certificate.

## Primary definitions

Myerson's answer defines a cover of length n by congruences x = a_i (mod m_i), with strictly increasing positive moduli, that partition all integers 1 through n exactly once, and each congruence must contain at least two of those integers. The heft is the sum of reciprocals of the moduli. The classes are full residue classes intersected with [1,n], not arbitrary truncated arithmetic progressions. This distinction is essential for the certificate's end-point constraints.

The same definition appears in Emanuel, *Odd incongruent restricted disjoint covering systems*, INTEGERS 12A (2012), #A8, Definition 1, page 1. The 2009 Myerson–Poon–Simpson publisher abstract independently confirms exact partition and at least two hits; the publisher full text was unavailable in this audit. The 2011 thesis supplies complete primary proofs and bounds.

Distinct moduli are required by the question, but the proposed dual argument does not use distinctness; proving a lower bound for the larger class of full-residue-class partitions also proves it for IRDCS. Repeated moduli cannot be used to disqualify the stronger theorem merely because the original class excluded them. Modulus one, if admitted, gives the trivial complete cover of heft one. No cover with the stipulated minimum of two hits exists at n=1.

## Prior results inspected

| Primary source | Location | Relevant result |
|---|---|---|
| Myerson, Poon and Simpson, 2009 | Discrete Mathematics 309(13), 4428–4434, DOI 10.1016/j.disc.2009.02.002 | Original IRDCS study; publisher abstract confirms definition. Full text not obtained. |
| Emanuel, *Covering systems*, 2011 | Chapter 2, definition on printed p.15; section 2.3, printed pp.26–30 | Heft is sum 1/m; general lower bound tending to 3/4; text says Appendix C improves it. |
| Emanuel, 2011 | Appendix C, Theorem C.1, printed p.215 | h >= 1 + (2t^2-nt)/(n(n-t)) > sqrt(8)-2 > 0.828. |
| Emanuel, 2011 | Appendix C, Theorem C.2, printed pp.215–216 | Upper bound h <= 1.4055; an examiner's proposed stronger upper bound was explicitly unverified. Irrelevant to the present lower-threshold claim. |
| Emanuel, 2012 | Definition 1 and final paragraph, pp.1 and 6 | Same IRDCS definition; reports known standard IRDCS heft as low as 0.987952, and asks whether odd IRDCS can have heft below one. |
| Myerson, MathOverflow answer 499017 | Definition; fourth question; August 2026 updates | Explicit open lower target h<0.98, with no answer to that half in the retrieved current version. |

### Corrections and scope traps

1. The 2011 thesis main narrative (printed p.29) and 2012 paper report a minimum 0.987952. The thesis table for one-dimensional IRDCS at n=45 reports **0.987289** (Appendix A, printed p.191), which is lower. Do not present 0.987952 as an unqualified best known numerical value. Neither value contradicts a bound above 0.98. This audit did not reconstruct the n=45 witness.
2. The thesis includes **two-dimensional** restricted-covering examples below 0.98, such as a 6 by 5 system of heft 0.973785. Those are a different problem with different geometric normalization and do not falsify the one-dimensional theorem. State the dimension explicitly.
3. The 2026 MathOverflow update includes a newly rediscovered h>1.07 example already present in the 2011 thesis, and Myerson explicitly gives the thesis priority. This is a concrete reason to scope novelty claims carefully and inspect the appendices.
4. The proposed polynomial is not a new general optimization algorithm. Linear programming duality, polynomial approximation, and Bernstein nonnegativity certificates are established tools. An original mathematical consequence can result from a new explicit witness constructed using established methods; that does not demonstrate exclusive AGI capability, model-operation alpha, or a discovery advantage over competent conventional research.

## Mathematical audit of the construction

Let p(x)=Q(2x-1), where Q is the even degree-20 Chebyshev polynomial in `scout/revised_polynomial.json`. Coefficients in that file are already the coefficients used by the verifier. The metadata `scale` is provenance of construction and must not be applied a second time.

For a residue class with k>=2 members, normalized midpoint positions are a+j*d, j=0,...,k-1, where d=m/n. Maximality inside the integer interval implies

    max(0,1-k*d) <= a <= min(d,1-(k-1)*d).

With u=2*a+(k-1)*d-1, the evaluation points become u+(2*j-k+1)*d in Q coordinates. Symmetry of Q allows u>=0. Necessarily 1/(k+1)<=d<=1/(k-1), with the domain covered by the two verifier patches:

    d=(k+s)/(k*(k+1)),   u=v*s/k,
    d=(k-1+s)/(k*(k-1)), u=v*(1-s)/k,

for s,v in [0,1]. These domains include boundary cases conservatively. The certificate checks d*sum_j Q(u+(2*j-k+1)*d)<=1. Dividing by m gives sum_j p(x_j)/n<=1/m. Exact partition permits summing this inequality over all classes, yielding h >= (1/n)*sum_{i=1}^n p((i-1/2)/n).

Signed p values do not invalidate this implication: exact partition constraints are equalities, and the dual weights need not be nonnegative. The function need not represent a probability density.

Manual review of `scout/certify_bernstein.py` checked the polynomial expansion, the R^21 denominator clearing, conversion from monomials to tensor Bernstein coefficients, and midpoint de Casteljau subdivision. These operations have the expected normalization. The scout output records all 78 patches for k=2,...,40 passing exact nonnegativity checks. The lineage workstream separately implemented the bivariate calculation, tail bound, and midpoint checks.

The large-k tail proof applies quadrature to g=p-p(0) extended by zero outside [0,1], whose continuity at both endpoints follows from evenness of Q. The variation bound includes jumps in g' at both endpoints. The term |p(0)|*d accounts for kd differing from one. This avoids incorrectly extending the original p by zero with a discontinuity. A conservative shifted-lattice quadrature constant 1/8 is sufficient. The finite-n midpoint estimate and exact small-n evaluation originally established h>0.98. Subsequent `lineage/myerson_independent_uniform.json` reports an exact centered-moment recurrence proving the stronger midpoint inequality S_n(p)>integral(p) for every n>=2, matching the root workstream's Euler–Maclaurin polynomial. This final strengthening is recorded as the other workstreams' execution, not a new execution by this auditor.

## Source access and reproducibility

URLs inspected:

- https://mathoverflow.net/a/499017
- https://api.stackexchange.com/2.3/questions/462981/answers?site=mathoverflow&filter=withbody&pagesize=100
- https://doi.org/10.1016/j.disc.2009.02.002
- https://www.sciencedirect.com/science/article/pii/S0012365X09000399
- https://researchers.mq.edu.au/en/publications/incongruent-restricted-disjoint-covering-systems/
- https://doi.org/10.25949/19441907
- https://figshare.mq.edu.au/articles/thesis/Covering_systems/19441907
- https://api.figshare.com/v2/articles/19441907
- https://ndownloader.figshare.com/files/34541747
- https://math.colgate.edu/~integers/a8self/a8self.pdf
- https://www.laura-lyman.com/uploads/3/9/7/4/39745896/correctirdcspaper.pdf
- https://josiahwilson.me/projects/irdcs-three-hits/
- https://github.com/Aperturesurvivor/irdcs-divisible-by-4

Searches included the exact phrases "incongruent restricted", "heft", "0.98", "lower bound", and "polynomial", with both available web engines. The second engine returned materially better relevant coverage for this niche topic. A current primary problem statement and complete primary thesis were inspected rather than relying on search snippets alone. No resolution of the below-0.98 question or higher general lower bound was found in this bounded search. That is a scoped search outcome, not proof of novelty.

Local source cache and hashes are listed in `SOURCE_MANIFEST.json`. The dissertation is marked **In Copyright** by its repository. Keep the complete cached PDF and its extracted text in working research storage; do not redistribute those full files in the public evidence package without rights. The authored audit and bibliographic/source hashes can be included. Apply the same conservative redistribution treatment to the downloaded 2012 article unless a license is separately established. StackExchange source carries its applicable CC BY-SA license and attribution requirements.

## Stopped earlier branch

The odd-cycle channel-code search remains preserved under `challenge/channel_search/`. No claimed improvement was found. The requested conventional codec implementation was paused before creation when the theorem candidate survived the mathematical audit. The published C11^3 148-point source asset was saved and verified, but no fresh codec-confirmation seeds were generated. Do not imply completion of that abandoned codec comparison or count it as operational alpha.
