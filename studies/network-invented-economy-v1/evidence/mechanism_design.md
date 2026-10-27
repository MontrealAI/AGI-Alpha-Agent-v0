# Executable witness: a budget-aware coordination-mechanism foundry

## Status and boundary

This is a locally executed, known-method software experiment on openly synthetic data.
It is not a run of Astra reasoning over customer jobs, an autonomous invention campaign,
an authenticated ENS exchange, a sale, or a procurement transaction. No model calls,
credentials, external services, or real payments are required. The economic simulator
must not infer an AI success rate or dollar delivery cost from this witness.

The bounded offering is an executable allocation-and-payment protocol for obtaining a
complete set of complementary inputs under a hard common budget. Each supplier controls
one necessary component. Its private cost is an integer drawn from a supplied finite
distribution. Utility is payment less cost when its component is acquired. The buyer
receives value only when the whole bundle is acquired. Costs are independent in the
optimization model; reports need not be truthful in the validation experiment.

Such protocols could be components of a non-safety-critical compute or research-service
consortium. The witness does not establish demand for such an offering. Real contract
terms, correlated costs, multi-dimensional preferences, collusion, strategic identity
creation, and professional review would require a separate scope and evidence.

## The transformation and its decisive experiment

The binding restriction is the combination of a shared hard payment cap and a large
space of possible threshold vectors. Ordinary independently designed component offers
can each be truthful while their sum violates that cap. Standard welfare-efficient
VCG procurement is another important negative control: its incentive property does
not imply a hard payment bound. These failures are retained explicitly.

A reusable distribution compiler produces cumulative acceptance masses. A budget-aware
composition engine replaces an exponential threshold-vector search by an exact prefix
frontier. A separate certificate checker verifies each recorded vector, payment total,
acceptance mass, and Bellman upper-bound inequality. Finally, an exhaustive finite
deviation checker tests the emitted protocol for unilateral truthfulness, ex-post
individual rationality, all-or-none acquisition, and the budget bound.

The decisive small-domain comparison is against an exact exhaustive optimizer of the
same admissible mechanism family. It is a strong mathematical oracle, not an external
AI competitor. The new representation must match its optimum exactly. Better-than-oracle
performance is neither expected nor claimed. The large-domain experiment checks exact
Bellman certificates; it does not pretend to enumerate all large type/report profiles.

### Mathematical model

Let supplier i have cost c_i in {0,...,m_i}, probability weights w_i(c_i), and cumulative
mass W_i(p_i)=sum_{c<=p_i} w_i(c). A posted-price vector p acquires every component if and
only if every report is at most its corresponding p_i. On acquisition the mechanism
pays p_i to i; otherwise it acquires nothing and pays zero.

For a buyer value V and hard budget B, the declared objective is

    max_{p: sum p_i <= B} (V - sum p_i) product_i W_i(p_i) / product_i sum_c w_i(c),

with an explicit no-offer alternative of zero. All comparisons use integer numerators;
there is no floating-point tolerance in the optimization or finite correctness checks.

For every exact total s, the prefix frontier stores

    D_i(s) = max_{0<=p<=m_i, p<=s} D_{i-1}(s-p) W_i(p),

starting with D_0(0)=1 and other base states unreachable. For fixed s, maximizing
acceptance probability maximizes surplus whenever V-s is nonnegative. A negative
surplus vector cannot beat the no-offer alternative. Hence choosing the best
(V-s)D_n(s) for s<=B is exact within this family. A stored feasible witness establishes
attainability; every predecessor inequality establishes the upper bound by induction.

Truthfulness follows directly from thresholds that do not depend on the supplier's own
report. With other reports fixed, either acquisition is impossible, or supplier i can
choose between zero utility and p_i-c_i. Truthful reporting chooses an option with
maximal utility. Ex-post individual rationality follows from c_i<=p_i whenever truthfully
allocated. The budget follows from sum p_i<=B. These arguments assume one component per
supplier and quasilinear utility. They do not establish coalitional truthfulness,
truthfulness of identity creation, or correctness of arbitrary generated mechanisms.

## Complementary retained capabilities

| Capability | Restriction changed | Construction / validation | New supported action | Failure / falsifier |
| --- | --- | --- | --- | --- |
| Typed independent-cost compiler | Raw distributions cannot safely be multiplied without a declared scope | Validate finite integer support, masses and dimensions; hash exact input | Portable cumulative masses and domain identity | Reject changed distributions, unsupported correlation or out-of-domain queries |
| Budget frontier composer | Separate offers ignore the common cap; vector enumeration grows exponentially | Construct exact prefix table; independently check every witness and Bellman inequality | Optimize a complete bundle under changed public budget/value | Any finite oracle mismatch or false inequality rejects the artifact |
| Deviation / constraint certifier | Agent agreement or a 'truthful' label is not evidence | Enumerate all own reports against all declared profiles on bounded small domains | Attach precise finite DSIC, IR, budget and acquisition evidence | A profitable deviation or budget breach rejects the candidate |

No component needs to earn revenue alone. The composer without the scope compiler can
optimize a misspecified independence model; the compiler without the budget composer
cannot enforce joint affordability; a correctness label without the certifier does not
establish the properties promised by the offering.

## Recipient baseline and transfer

Recipients already know posted-price theory, dynamic programming, available optimization
tools, and ordinary validation methods. Missing a skill file does not imply missing
intelligence. The experiment transfers a compiled, input-specific frontier and its
finite certificate, not secret theoretical knowledge.

Twelve recipients receive fresh public budget/value queries against the same supplied
distribution family. The equal-intelligence cold baseline constructs and checks the
same exact dynamic program at each recipient's required budget. Shared recipients import
the full portable frontier, verify its bytes and applicability, **and independently
recheck its mathematical certificate** before their fresh query. That receiving-agent
validation cost is counted, even if it makes reuse unattractive. The constructor's
original work and validation are also counted. Integer transition/comparison counts,
selection scans and bytes hashed are reported separately; they are not interchangeable
units of operating cost.

A separate number shows what full trusted-attestation reuse would avoid. It is expressly
a scenario for the graph/economic model, not executed authenticated network evidence.
Duplicating an already-held artifact has zero incremental construction benefit. A new
distribution, a revoked or stale attestation, or an incompatible domain requires a new
validation decision. Graph admission, freshness, revocation and authorization are the
responsibility of the study's separate graph lifecycle, not a claim made by this module.

## Prospective protocol and execution

The full deterministic protocol is in `PROTOCOL` in `src/mechanism_witness.py`. Development
tests use seeds 0-7 and 51-60. Confirmation uses disjoint seeds 261026700-261026747 for 48
small domains, 261026900-261026904 for five larger domains, and 261027100 for the recipient
reuse example. No adaptive reranking or selective reporting is permitted.

Before reading confirmation results, run `python3 src/mechanism_witness.py freeze`.
This creates `evidence/mechanism_witness.json` with the protocol and SHA-256 identities of
the source, tests and this design statement. Then run `python3 src/mechanism_witness.py
confirm`. `verify` repeats the exact deterministic experiment and compares the retained
result identity. A changed source must not be relabeled as the frozen experiment.

Acceptance requires all 48 small exact-oracle matches and all 48 finite protocol passes,
five valid large-domain certificates, unchanged negative-control rejection, and the
adversarial unit tests. Reuse economics is an outcome, not an acceptance requirement.
Production deployment is outside the package. The local tests use the Python standard
library; repository-wide setup, credentials, hosted checks and operational qualification
are separate and are not claimed by this component.

## Source and novelty limits

The direct external research motivation is Jiayuan Liu, Mingyu Guo and Vincent Conitzer,
*An Interpretable Automated Mechanism Design Framework with Large Language Models*,
arXiv:2502.12203v1, 16 February 2025, retrieved 26 October 2026:
https://arxiv.org/html/2502.12203v1 . The paper studies generated mechanism code with
problem-specific corrections and evaluations. It also reports rapid recovery of known
theory by strong models, which supports a strong recipient baseline. It supplies no
Astra-specific acceptance rate for this offering. Our posted-price recurrence and proof
are independently specified known mathematical methods, not an asserted new mechanism.

The implementation can demonstrate exact optimization, composition failure, evidence
checking, input-specific transfer and their computational costs. It cannot establish
that a current frontier model invented a commercially novel capability, that authorized
network members are unable to reconstruct it, or that buyers would pay the modeled price.
