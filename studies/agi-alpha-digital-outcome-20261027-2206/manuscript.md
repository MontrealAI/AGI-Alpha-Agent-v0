# AGI ALPHA FLYWHEEL — When Capability Creates Opportunity

## From a numerical failure to a verified digital answer

*Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work*

**Vincent Boucher — President of MONTREAL.AI**

27 October 2026 · DIGITAL-20261027-R1 · Research review edition

# A useful answer, with its limits attached

**A public numerical failure can now be turned into an inspectable,
executable answer within a bounded agent mission.** This edition
delivers a scalar beta-quantile compatibility kernel, a command-line
interface, three frozen implementations, independent numerical checks, a
complete replay package and an explicit commercial decision. It changes
what a scientific software team can do immediately: reproduce an
extreme-tail failure, obtain a checked replacement value within a stated
domain, and inspect the evidence before deciding whether to integrate
the component.

The concrete example matters. For probability $10^{-16}$ and beta shape
parameters $a=0.5$, $b=3$, the installed SciPy 1.17.0 environment
returned a quantile of **0.5**. The independently evaluated value is
approximately **$2.844444444444444\times10^{-33}$**. The public report
supplied the failure and a candidate numerical recipe. We did not
discover that formulation. We converted it into bounded, failure-aware
artifacts and tested the contribution of different ways of operating the
available assistant. ([chrisb83 2026](#ref-scipyissue))

All three workflows passed the **64 fresh confirmation checks**: 56
numerical or endpoint cases and eight required refusals. Ordinary
competent operation and expert operation also handled a separately
disclosed, already-known subnormal rounding trap; the original
conventional implementation failed that diagnostic. Its correction is
preserved separately. The fresh bank is one mission’s case bank, not 64
independent missions or customers.

> **Decision: retain and deliver the useful engineering; pursue only a
> customer-funded qualification pilot. Do not promote this edition as an
> exclusive numerical breakthrough, a measured general Operational Alpha
> advantage, or a realized profitable business.**

## Three verdicts

| Question                      | What this edition establishes                                                                                                 | What remains missing                                                                                              |
|:------------------------------|:------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------|
| Commercial delivery           | An executable digital artifact accepted by the frozen research contract; a conditional service model with explicit thresholds | External buyer acceptance, willingness to pay, commitments, collections and complete actual costs                 |
| Operational Alpha             | Live, tool-using implementations by ordinary and expert agents; both pass the fresh bank and the rounding diagnostic          | A demonstrated improvement in accepted quality or complete economics from expert operation                        |
| Transformational contribution | A useful bridge from a reported failure to a bounded executable outcome                                                       | New numerical capability beyond the strongest identified established methods; an independent discovery comparison |

The program’s ambition remains larger than this result. Its discipline
is to preserve a useful construction without borrowing an achievement
from a failed hypothesis. The most productive successor may begin with a
reliable piece of engineering and a sharper question, rather than with a
claim of superiority.

The work was AI-assisted under the requested authorship. External
authors retain credit for the report, recipe, libraries and foundational
methods. No external peer review, production adoption or paid customer
approval is implied.

------------------------------------------------------------------------

# The opportunity and the early challenge

## Who benefits, and what changes

The immediate beneficiary is a maintainer or scientific software team
evaluating a beta-tail calculation. Such a recipient needs more than a
plausible formula: a reproducible failure, a bounded replacement,
evidence for extreme and invalid inputs, and clear integration limits.
Wrong finite values are particularly troublesome because a program may
continue without an exception. Several observed failures emitted
warnings; an application that ignores them can still consume an
incorrect finite value. Whether a particular recipient’s downstream
decision is materially affected remains a customer-specific question;
this study does not invent a deployed failure or financial loss.

The useful opportunity is **rapid numerical incident qualification**:
assembling a precise failure report and a tested compatibility component
from public inputs before an upstream release or a local migration is
available. The changes making this operationally plausible are
accessible source and issue histories, current numerical libraries,
arbitrary-precision arithmetic and an assistant capable of reading code,
compiling kernels, diagnosing failed checks and packaging evidence. This
study observes that combination working locally. It does not establish
that organizations were previously incapable of doing the same work.

Our shortlist was concentrated in scientific software, not a claim to an
exhaustive cross-industry search. The preceding gap sprint had already
explored broader opportunities. We narrowed the continuation to
deliverable public incidents where the reasoning and execution were real
and physical fabrication was unnecessary.

| Candidate                       | Unmet outcome and beneficiary                                                                | Strongest early alternative and disposition                                                                                                                         |
|:--------------------------------|:---------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Beta-tail failure qualification | Checked scalar answers and an inspectable compatibility kernel for a numerical software team | Current Boost.Math plus ordinary high-precision methods solved the public examples. Selected for delivery and agent comparison; algorithmic novelty rejected early. |
| Boundary confidence intervals   | Reliable boundary behavior and a validated repair for statistical software users             | Existing active repair PRs already owned the relevant statsmodels issues. Excluded rather than duplicate ongoing work.                                              |
| Kronecker-product correctness   | A usable symbolic correction and regression evidence for SymPy users                         | An active repair PR already addressed the report. Excluded from construction.                                                                                       |

The exact issue and PR records, rejected candidates and initial search
notes are included in the evidence package. Statsmodels issues
10536/10538 had active PRs 10537/10539; SymPy issue 30860 had active PR
30863 at inspection. ([statsmodels contributors 2026](#ref-statsmodels);
[SymPy contributors 2026](#ref-sympy))

## Conventional falsification came first

Before the three agent constructions began, a separate workstream
compiled current Boost.Math at commit
`70a36632cfbfe6a862cd8a5b88b357ca3a770a3d`. A double-precision policy
disabling promotion, with safe error handling and 400 root iterations,
solved **all five public examples**. Its maximum relative error against
the 80-digit public-recipe reference was approximately
$2.008\times10^{-14}$. Raising the cap to 2,000 did not change that
five-case result. A long-double configuration failed one example at both
caps; the failed configuration remains in the record.

This is a meaningful established alternative. SciPy itself documents
that `betaincinv` wraps Boost’s `ibeta_inv`; the Boost interface already
exposes precision and error policies. A successful current-Boost
configuration is therefore not an invented numerical method. ([SciPy
Developers 2026](#ref-scipydocs); [Boost.Math Developers
2026](#ref-boost))

**Selection changed because of this evidence.** The candidate survived
as a useful digital delivery and an operational comparison. Its
exclusive technical-breakthrough claim did not survive. Public-source
formulation credit stays with the reporter; execution comparators
received that formulation in full.

------------------------------------------------------------------------

# What was actually compared

## Equivalent information, capable baselines

Three new agent workstreams received the same common prompt, public
report and proposed recipe, pinned source extracts,
conventional-challenge results, libraries, acceptance contract, tool
access and resource limits. Each could inspect source, write code,
compile a C++ kernel, run tests and recover from failures. Ordinary
competent use was not reduced to a single prompt or forbidden from
verification.

The expert arm received an explicit operating checklist: extract
obligations, plan numerical regimes, verify independently, preserve
failures and recover before freezing. The conventional arm was asked to
compose the strongest practical established numerical techniques. Its
implementation was built by an assistant too; it is **not a measured
human-team trial**. The distinction is workflow and instruction, not a
claim that conventional reasoning excludes tool-using AI.

All arms used the inherited available assistant configuration. The
environment supplied the label **GPT-6 Astra Pro**. Provider-attested
backend identity, temperature, sampling seed, token counts and billed
cost were not exposed. These fields are recorded as unknown. No
independent API endpoint was invoked to manufacture a stronger identity
claim. The model work and local execution were live; this was not a
simulation of successful model behavior. The result is narrower than a
fully controlled, provider-metered same-model trial.

Computer execution consisted of shell commands, source inspection,
compilation, numerical tests and file construction. No graphical
interface performance was measured. No live `*.agent.agi.eth` identity,
external settlement or production authority was asserted.

## A bounded construction budget

The continuation reserved 120 minutes, starting at 18:06:05 on 27
October 2026 in Montréal, using existing authorized resources.
Opportunity selection and conventional falsification preceded
construction. Each implementation received a 15-minute, 25-tool
construction ceiling with no subagents. The remaining continuation
budget covered fresh confirmation, independent checking, economics,
reproducible delivery and publication preparation.

<figure>
<img src="figures/construction_time.svg"
alt="Recorded construction time. Expert operation took longer in this single trial. This is elapsed construction time, not token usage, billable cost or a population estimate." />
<figcaption aria-hidden="true">Recorded construction time. Expert
operation took longer in this single trial. This is elapsed construction
time, not token usage, billable cost or a population
estimate.</figcaption>
</figure>

| Arm                   | Recorded construction time | Source freeze, UTC | Tool count as recorded |
|:----------------------|---------------------------:|:-------------------|-----------------------:|
| Ordinary competent    |                  10.16 min | 22:32:41           |                     21 |
| Expert operation      |                  13.66 min | 22:36:25           |                     23 |
| Conventional workflow |                   8.22 min | 22:30:53           |                     13 |

Tool-count conventions differ: the expert manifest includes progress
messages, while the conventional count describes execution calls. They
are traceability records, not a normalized efficiency measure. Timings
start at the first recorded agent timestamp, not a provider scheduling
boundary. The expert also recovered from a task-storage exhaustion
during packaging; numerical work and original failed packaging evidence
were preserved.

## Discovery and execution are separate experiments

No discovery advantage is claimed. The user supplied the program’s
objective; the continuation search found the public issue; the issue
supplied the mathematical recipe. Every execution arm received it. A
future discovery comparison would need equivalent initial information
before revealing that recipe and a prespecified way to score the
usefulness and originality of the formulation. A technical tie cannot
supply that missing experiment retrospectively.

------------------------------------------------------------------------

# The accepted digital contract

The delivered object is deliberately bounded: **a scalar compatibility
component**, not a drop-in replacement for all SciPy distributions,
array broadcasting, accelerators, automatic differentiation or every
positive beta shape.

A request contains an identifier and three numbers: probability $q$ and
shapes $a,b$. The interpretation is the exact binary64 value received by
Python. The accepted numerical domain is

$$
0\le q\le1,\qquad 0.25\le a,b\le10^6,\qquad \min(a,b)\le100.
$$

The result preserves the identifier and returns a status with a value or
a refusal. Exact probabilities zero and one require their corresponding
endpoint values. An interior true quantile that rounds to binary64 zero
requires an explicit `underflow` status. Unsupported positive shapes are
distinguished from invalid inputs. Booleans, strings, nonfinite values,
nonpositive shapes and out-of-range probabilities are not silently
coerced into numerical success.

For a verified reference value $r$ strictly between zero and one, the
frozen acceptance tolerance is

$$
|\widehat x-r|\le \max\{2\,\operatorname{ulp}(r),\;10^{-11}\min(r,1-r)\}.
$$

A representable positive reference may not be replaced with zero.
Correct endpoint, underflow and refusal behavior is checked explicitly.
A computation that cannot establish an answer returns `failed`; a
plausible finite number does not automatically count as success.

## How the construction works

The three implementations combine established instruments: a pinned
Boost inverse, analytic special cases, incomplete-beta continued
fractions, symmetry, log-domain arithmetic and high-precision
safeguarded inversion when needed. This composition protects against
numerical scale and unsupported inputs. Its scientific ingredients are
conventional. Definitions, symmetry, the integer-shape binomial identity
and continued fractions appear in NIST’s reference treatment. ([National
Institute of Standards and Technology 2026](#ref-dlmf))

The ordinary implementation is the recommended research entry point
because it passed the primary contract and the disclosed rounding
regression with less recorded construction time than the expert arm.
That is a local delivery choice, not a universal ranking. All original
implementations remain available so a recipient can inspect the
tradeoffs rather than inherit a hidden selection.

For the public example, a recipient can run:

``` sh
python experiment/arms/ordinary/run.py <<'JSON'
{"id":"beta-tail","q":1e-16,"a":0.5,"b":3.0}
JSON
```

The expected accepted value is approximately `2.844444444444444e-33`,
with status `ok`. The package supplies a portable rebuild/replay command
so a recipient need not trust the included platform-specific binary.
Python and a C++17 compiler are required for that rebuild. Dependencies
and licenses are pinned and included.

## Acceptance does not transfer itself

The frozen numerical envelope is the product boundary. A recipient
integrating the component into a different distribution, vector API,
operating system, threat model or safety-critical process needs new
qualification appropriate to that use. This is a concrete limitation,
not an excuse to omit the delivered bounded result. External customer
acceptance was not observed; research acceptance and customer acceptance
remain separate records.

------------------------------------------------------------------------

# Fresh confirmation and independent checking

All three arm manifests were verified before the case bank was
generated. The root source freeze was recorded at **22:40:20.056812
UTC**; generation followed at **22:40:20.103189 UTC**. The generator’s
recorded seed is `2707272985118872086`. The seed was drawn after source
freeze, and the case bank was generated once. No primary implementation
was changed after viewing these cases.

The bank contained 24 extreme-tail cases, 12 central cases, eight
analytic-shape cases, four integer-shape cases, eight endpoint or
underflow cases, and eight invalid or unsupported requests. It
deliberately emphasizes adverse numerical regimes. It is not a random
sample of customer demand or the prevalence of bugs in software.

<figure>
<img src="figures/fresh_confirmation.svg"
alt="Primary fresh confirmation: all three frozen workflows satisfy 56 numerical or endpoint cases and eight refusals. The separately disclosed known midpoint diagnostic is outside this denominator." />
<figcaption aria-hidden="true">Primary fresh confirmation: all three
frozen workflows satisfy 56 numerical or endpoint cases and eight
refusals. The separately disclosed known midpoint diagnostic is outside
this denominator.</figcaption>
</figure>

The independent root evaluator used 80- and 120-digit arithmetic, a
log-domain bisection inverse and a separately written incomplete-beta
continued fraction. It did not call Boost’s inverse as its primary
judge. Analytic cases and exact rational integer-shape identities
provided additional controls. All 64 references were resolved. A
separate audit recomputed acceptance and used Decimal/Fraction controls;
its complete check record is supplied.

## What the checks do and do not prove

The bank establishes finite acceptance under a frozen contract. It does
not prove correctness throughout the continuous parameter envelope. Two
high-precision runs can share an error, and distinct programs can share
a mathematical ingredient. The evaluator therefore retains its
independent controls and uncertainty rather than treating agreement as a
proof of universal correctness.

Every primary call met its observed CPU limits: five seconds per call
and 120 seconds per worker. Raw timings are retained, but **no numerical
speedup is claimed**. Many recorded per-call CPU differences were zero;
the tiny batch and observed timer behavior do not support a stable
ratio. The identical reported peak memory high-water marks are likewise
unsuitable for an arm-level memory advantage. Import and build time are
recorded separately from solve time, and construction and verification
effort cannot be replaced by a microsecond solve-time figure.

The broad result is uncomplicated: competent ordinary operation
succeeded, explicit expert operation succeeded, and the strongest
identified conventional workflow succeeded on the fresh bank. The expert
checklist did not produce a better primary accepted outcome in this
trial.

## The additional boundary failure stays visible

After primary confirmation, the independent audit ran an already-known
diagnostic at the smallest positive binary64 probability, with
$a=1,b=2$. Ordinary and expert implementations returned the correct
positive subnormal value; the original conventional implementation
returned zero with `underflow`. This diagnostic was not fresh and was
not added to the primary denominator. A separately labeled conventional
correction, using ordinary analytic precision and lattice rounding,
passed the same 64-case replay plus the known midpoint diagnostic. These
are post hoc replays, not a new blind confirmation; the original failure
remains in the correction record. Neither the original failure nor the
corrected comparison disappears.

------------------------------------------------------------------------

# A better measuring instrument

The most instructive failure occurred in the numerical judge. Both the
ordinary and expert workstreams independently noticed that converting a
high-precision value to a machine float can conceal a subnormal rounding
error. Agreement at two precisions did not guarantee correct rounding.
The root evaluator initially shared that weakness.

The correction was made **before generating the fresh bank**. The old
evaluator, new evaluator, source hashes, diagnostic and rationale remain
in the package. The acceptance requirements did not change. All three
primary arms were evaluated by the same corrected instrument. We
disclose the feedback from the arm builders because the root evaluator
was not sealed from all development feedback.

## An exact counterexample

Let $\delta=2^{-1074}$, the smallest positive binary64 value. For a
Beta$(1,2)$ distribution,

$$
F(x)=2x-x^2.
$$

At the midpoint between zero and $\delta$,

$$
F(\delta/2)=\delta-\delta^2/4<\delta.
$$

The quantile at probability $\delta$ is therefore **above** that
midpoint and rounds to $\delta$, not zero. A computation that loses the
tiny positive correction can land on the midpoint and apply the wrong
rounding decision. This is a numerical instrument failure with an exact
rational adjudication, not an invented new special function.

The corrected reference explicitly rounds on the binary64 subnormal
lattice. Near a midpoint, it uses an exact integer-shape CDF when
available, otherwise a 500-digit adaptive calculation with an
unresolved-reference outcome if the decision remains too close. The
construction uses conventional mathematical identities; the contribution
is the preserved diagnosis and the accountable correction.

## Why this belongs in the main narrative

A fluent implementation and a passing high-precision comparison can
still be wrong in the same way. A useful agent must be able to question
its checker and produce independently inspectable evidence for that
challenge. In this study, **ordinary competent use already did that**.
It would be misleading to award the behavior exclusively to the expert
arm.

Transformational Intelligence argues that evaluators may themselves
impose restrictions, but that revising an evaluator must not become a
way for a candidate to award itself victory. Its prescribed discipline
is an independent outcome anchor, preserved old evidence and a common
corrected comparison. This continuation exercises that discipline on a
real numerical instrument. It does not thereby establish a novel theory
of evaluator revision. ([Boucher 2026c](#ref-ti))

The earlier kinetics construction remains supporting engineering. Its
conventional parity, thin conditional economics and untested physical
assumptions are unchanged. No chemical parameters, catalysts or
acceptance criteria were tuned in this continuation to manufacture a
second success.

------------------------------------------------------------------------

# The commercial offering and the cost boundary

The free delivered artifact is the recipient’s strongest outside option.
A prospective paid engagement must therefore purchase **bounded
qualification, integration and handoff in one declared buyer
environment**, including correction and support. It cannot earn a
license premium for a public conventional algorithm. That buyer-specific
engagement has not been performed or accepted by a customer; the
following economics are conditional on it.

All amounts are nominal US dollars. Let $M$ be the unknown additional
model/tool cost per future engagement, including retries and failed
attempts. Let $D$ be the unknown complete historical cost of this
research, development and publication project. Neither is inferred from
wall time. The same $M$ is used for all workflows because no metered
cost advantage was established. Historical $D$ is deducted once for
full-project recovery, not again per customer.

## Complete central cost per accepted engagement

| Item                   | Explicit central assumption                                          | Cost or receipt |
|:-----------------------|:---------------------------------------------------------------------|----------------:|
| Net revenue            | \$1,500 price, less 2% expected refunds                              |      \$1,470.00 |
| Successful delivery    | 2.5 h at \$125/h: scope, integration, qualification, handoff         |        \$312.50 |
| Failed attempts        | 20% failure probability; 1.5 h each; expected 0.375 h per acceptance |        \$46.875 |
| Support and correction | 0.5 h at \$125/h                                                     |         \$62.50 |
| Acquisition            | 0.75 h at \$125/h plus \$25 cash                                     |        \$118.75 |
| Infrastructure         | Per accepted engagement                                              |          \$5.00 |
| Payment expense        | Assumed 3% of price plus \$0.30                                      |         \$45.30 |
| Additional model/tools | All future engagement retries included                               |             $M$ |
| **Contribution**       | Before cohort fixed costs                                            | **$879.075-M$** |

No recurring human review is invented for each automated scalar
calculation. These hours describe future buyer integration and service,
not observed labor in the present experiment. Loaded rates of
\$100–175/h are scoped estimates; historical employee wages provide only
an order-of-magnitude anchor, not contractor quotations. The complete
cost model discloses hours, rates and uncertainty. ([US Bureau of Labor
Statistics 2026](#ref-bls))

Four central buyers share \$800 of maintenance and fixed business cost
over the cohort; \$500 of additional commercial setup is charged once.
That setup concerns service contracting and onboarding, not rebuilding
the already delivered code, tests or documentation. The central cohort
extends through day 115. The favorable cohort extends through day 195;
neither is an annual forecast.

| Scenario  | Buyers and price | Operating profit  | Full-project return |
|:----------|:-----------------|:------------------|:--------------------|
| Favorable | 8 at \$2,500     | $16,526.93-8M$    | $16,226.93-8M-D$    |
| Central   | 4 at \$1,500     | **$2,716.30-4M$** | **$2,216.30-4M-D$** |
| Adverse   | No buyers        | $-1,650$          | $-3,050-D$          |

**At an illustrative $M=\$100$, central operating profit is \$2,316.30;
full-project return is $1,816.30-D$.** This is a sensitivity coordinate,
not a measured model invoice. Operating profit requires $M<\$679.075$.
At $M=\$100$, the operating break-even price is \$890.45; recovering
additional setup raises it to \$1,022.03 before historical $D$.
Full-project profitability remains unknown.

The adverse case preserves zero demand rather than forcing a sale. A
conditional-commitment gate can avoid its prospective setup and
fixed-cost loss. If an adverse low-price sale did occur, its unit
contribution would be negative even before model cost. Expected profit
is not an observed earning.

------------------------------------------------------------------------

# Financing, demand and the next voluntary exchange

## Buyer value must survive the free alternative

The central price hypothesis has little room for error. It assumes eight
hours of avoided self-qualification at \$150/h, \$600 of avoided delay,
and one hour of buyer participation. The resulting value ceiling is
**\$1,650**, leaving only **\$150 of modeled buyer surplus** at the
proposed \$1,500 fee. The hours and delay value are unmeasured. A
competent recipient needing only two hours to reuse the free artifact,
with no valuable delay avoided, may rationally buy nothing.

Prices are independent buyer hypotheses, not a fixed discount from an
invented market price. The executable sensitivity grid holds volume
fixed only to show arithmetic; it does not assume buyers remain when
price exceeds their value. Extra participation is not automatically
beneficial: replacing a \$125 provider hour with a \$150 buyer hour
increases combined cost unless it brings another justified benefit.

A human team attempting an equivalent new repair from the same public
recipe is estimated separately at 14–38 hours, or \$1,400–\$6,650 at the
stated rate endpoints. The central attempt estimate is 24 h at \$125/h.
This is neither a measured human baseline nor willingness to pay, and it
is never added as a second bill for the already produced artifact.

## Cash comes before collection

At central $M=\$100$, acquisition and pre-acceptance work precede
collection. The modeled peak expected cash deficit is **\$2,091.25**. A
separate **\$1,875 reserve** covers one additional full refund and three
extra correction hours. Required unrestricted funding is therefore
**\$3,966.25**. Actual available funds, reserve balances, credit and
financing commitments are unknown. Any unpaid historical development
obligation must be added.

An earned milestone can reduce the funding threshold to **\$3,476.55**:
30% is paid after a separately useful, accepted qualification package;
the remainder follows final accepted delivery. This arrangement
preserves the numerical requirements, refund exposure and reserve. Two
collection fees reduce central full-project return by \$1.20 to
$1,815.10-D$ at the illustrative model-cost coordinate; the initial
calculation omitted that second fee and is preserved in the economic
correction record. It is a conditional contract design, not an observed
customer agreement or legal approval. A refundable deposit stays
restricted and supplies **zero unrestricted operating capital**. A
conditional commitment alone supplies no cash.

The reserve covers the specified stress, not multiple correlated
failures. Two extra full refunds exceed its refund component by \$1,500.
Delayed collection and financing fees can consume the margin. A reserve
is cash held, not an operating expense; it is not charged twice.

## Sharing is available to the conventional team too

| Matched arrangement, central $M=\$100$   | Return before historical $D$ |
|:-----------------------------------------|-----------------------------:|
| Conventional, four isolated engagements  |                  $-2,083.70$ |
| Expert operation alone, isolated         |                  $-2,083.70$ |
| Conventional, shared fixed costs         |                   $1,816.30$ |
| Expert operation plus shared fixed costs |                   $1,816.30$ |

This accounting counterfactual assumes equal capability and equal costs,
as the measured comparison warrants. The interaction attributable to
expert operation is zero. Sharing a known fixed cost can make a
conditional service viable; it is not a novel institution or exclusive
Alpha. All buyers retain the same public rights and can decline the
service.

**Observed commitments and collections: zero. Complete actual project
cost and available funds: unknown.** Buyer value, scope and costs still
need verification.

------------------------------------------------------------------------

# What the result makes possible

## Evidence: a small capability that works now

The demonstrated near-term capability is a bounded numerical incident
package: locate the relevant public evidence, reproduce the failure,
challenge the proposed novelty, construct a usable scalar component,
uncover a checker weakness, run fresh confirmation and deliver the
complete record. Its usefulness is inspectable without waiting for
physical fabrication, private data or a speculative future model.

The external libraries and public report do much of the intellectual
work. The live assistant’s contribution is to connect them into an
executable, checked outcome under a time limit. That is a real
productive capability, even when a competent conventional team could
perform the same task. The study does not establish that the expert
operating procedure improves that capability over ordinary competent
use.

## Conditional expansion: a portfolio of qualification missions

A broader service could qualify numerical incidents across scientific
packages, supply bounded compatibility components and help recipients
decide whether to integrate, upgrade or decline a workaround. That
expansion depends on evidence absent from this single mission: multiple
prospectively selected incidents, real recipient acceptance, adequate
model metering, known licensing and support obligations, and a measured
rate of failures that cannot be repaired within the paid scope.

The next economically informative step is one voluntary buyer pilot with
a written acceptance contract and a capped integration scope. A valuable
customer question might be whether this component resolves a blocked
calculation on the buyer’s actual supported stack. It must not be
silently replaced by passing our existing numerical bank. The free
artifact remains the buyer’s outside option; a buyer who can
self-integrate cheaply has no reason to pay a premium merely because an
agent was involved.

## Long-term ambition: capabilities that open better opportunities

The flywheel’s larger thesis is that a delivered capability can make a
later opportunity feasible. This result supplies a possible starting
asset, not evidence of compounding returns. A future successor could
reuse the source-pinning, numerical-regime analysis or exact-midpoint
checks on a genuinely new mission. It would still have to beat its own
competent baseline and an ordinary library containing the same asset
after retention, validation, integration and maintenance costs.

No fresh transfer trial was performed here. There is no retained-Alpha
or Gym-training claim. Adding transfer work would not repair the missing
expert advantage, and ordinary reuse is already available. Optional
learning investment should follow an expected benefit, not a prescribed
number of reinvestments.

Invent the Economy separates technical feasibility, participant value,
profitability, liquidity and actual exchange. Transformational
Autonomous Enterprises preserves comparisons in which a supplied
deterministic specialist matches quality and costs less. Those lessons
shape this edition: keep useful assets, let strong baselines win, and
require evidence for the next economic claim. ([Boucher
2026a](#ref-economy), [2026b](#ref-tae))

**Recommendation:** deliver the research artifact, retain the corrected
numerical instrument and conventional comparisons, and invite a narrowly
scoped customer qualification pilot. Stop the exclusive
algorithmic-novelty claim. Leave general Operational Alpha, discovery
advantage, retained benefit and realized commercial viability
unestablished until their own experiments support them.

------------------------------------------------------------------------

# Reproducibility, provenance and publication

## One edition, several readable forms

The package contains the compilable LaTeX manuscript, bibliography,
vector figures and plotting source; the polished PDF; a concise
executive brief; a complete offline HTML edition and a GitHub-readable
manuscript; frozen prompts, protocol, source and fresh results; the
conventional challenge and failures; the evaluator correction;
independent audit; executable economics; and a LinkedIn draft that has
not been posted.

The Markdown manuscript is the common content source for the LaTeX and
HTML editions. Numerical facts are checked against the machine-readable
result and economic files. The brief repeats the same verdicts and
conditions. Download identities and the publication status are recorded
separately so a review upload cannot be confused with a canonical
release.

The deterministic reproduction entry point rebuilds kernels in isolated
copies, replays the frozen case bank, recomputes references and scores,
and preserves the original source hashes. The native bridge reuses the
existing Journal, CostLedger and fitness components; it does not build a
second registry or invent a customer payment. Unknown actual charges
remain unknown. Its local research identity is not a live external
authentication claim.

## Evidence and source identities

| Item                           | Identity or location                                        |
|:-------------------------------|:------------------------------------------------------------|
| Edition                        | `DIGITAL-20261027-R1`                                       |
| Repository audit source        | `3947e4ec8fd74ad40e13e8ff825a149fa98a10e9`                  |
| Boost.Math construction source | `70a36632cfbfe6a862cd8a5b88b357ca3a770a3d`                  |
| SciPy inspected source         | `37fad094584e1129ea652680608cd2c1b02463b9`                  |
| Acceptance protocol            | `experiment/protocol.json` and SHA-256 sidecar              |
| Fresh source and case freeze   | `experiment/source_freeze.json`, `fresh_case_metadata.json` |
| Primary result                 | `experiment/comparison_results.json`                        |
| Instrument correction          | `experiment/evaluator_correction.json`                      |
| Complete claim map             | `delivery/claim_map.json`                                   |
| Monetary model                 | `economics/economics.py` and scenario outputs               |

All 24 preserved upstream component files were verified identical at the
prior and current repository snapshots. Third-party licenses remain
attached to their sources. Frozen experimental originals are retained
byte for byte; any publication-normalized or corrected copies have
separate identities. The previous gap archive is preserved with its
original SHA-256 in the continuation provenance.

## Publication is a separate acceptance boundary

The authorized route is an additive study review branch and draft pull
request under `studies/agi-alpha-digital-outcome-20261027-2206/`. The
mixed source, data and HTML package takes the repository’s full review
lane. It is not a passive-paper exemption. Existing runtime, discovery,
accounting and publication owners retain their roles. ([MONTREAL.AI
2026a](#ref-coordination), [2026b](#ref-publication))

This edition may be inspected and downloaded from its pinned review
source. Canonical production publication requires the existing owner’s
exact-source review, required hosted checks, qualified integration and
actual public deployment/served-byte verification. A green preparation
workflow with skipped deployment does not establish publication. The
delivery receipt states the exact source, public reading page, downloads
and any remaining external dependency; it does not borrow a prior
release’s approval.

------------------------------------------------------------------------

# Appendix: preserved failures and claim boundaries

## Corrections without erasure

| Record                      | Observed problem                                                                  | Treatment                                                                                            |
|:----------------------------|:----------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------|
| Early Boost challenge       | One long-double configuration failed a public example                             | Preserved beside the successful double configuration; no weak-only baseline                          |
| Ordinary development        | Subnormal rounding and an unscaled quadrature oracle produced misleading evidence | Original attempts retained; lattice rounding and normalized controls added before freeze             |
| Expert development          | Wrong finite subnormal-tail outputs and high-precision conversion error           | Trigger and rounding repairs made before freeze; original attempts retained                          |
| Root evaluator v1           | Direct high-precision-to-float conversion could double-round                      | v1 retained; exact midpoint controls and v2 freeze before fresh generation                           |
| Conventional primary source | Known post-confirmation Beta$(1,2)$ midpoint returned underflow                   | Failure retained outside primary denominator; correction separately labeled                          |
| Expert packaging            | Storage exhaustion interrupted README creation                                    | Partial attempt and recovery recorded; no numerical source erasure                                   |
| Root freeze check           | A hash copied into a summary contained a transcription error                      | Original source manifest rechecked; no source mutation or case generation occurred before resolution |

## What each positive result can support

- **Runnable construction:** yes, within the stated scalar envelope and
  finite tested cases. It is not universal proof or upstream
  integration.
- **Fresh research acceptance:** 64/64 checks for each original frozen
  arm, under a common corrected evaluator. Known diagnostic limitations
  remain visible.
- **Commercial operating profit:** conditional model only, with price,
  volume, scope, failure, support and unknown model-cost thresholds. No
  observed sale.
- **Financing feasibility:** conditional on actual unrestricted funds or
  explicitly agreed stages. Refundable balances do not become operating
  capital.
- **Operational Alpha:** not established. The expert arm did not improve
  primary accepted quality over competent ordinary use; complete cost
  and broad replication are missing.
- **Transformational contribution:** no exclusive numerical advance.
  Established methods meet the useful outcome; the public reporter
  supplied the formulation.
- **Fresh-transfer benefit:** untested. Ordinary reusable-library access
  remains a required comparator for a future transfer study.

## Research limits that affect the headline

One implementation trial per arm on one public mission cannot establish
population performance. Provider identity, billing and buyer demand are
unmeasured. Independent implementation and audit occurred within one
coordinated assistant session. Finite scalar acceptance does not justify
broader product claims. The conventional midpoint defect and post hoc
correction stay outside fresh confirmation. Human-service estimates are
assumptions, not quotations or willingness to pay.

------------------------------------------------------------------------

# References

<div id="refs" class="references csl-bib-body hanging-indent">

<div id="ref-boost" class="csl-entry">

Boost.Math Developers. 2026. “The Incomplete Beta Function Inverses.”
<https://www.boost.org/doc/libs/latest/libs/math/doc/html/math_toolkit/sf_beta/ibeta_inv_function.html>.

</div>

<div id="ref-economy" class="csl-entry">

Boucher, Vincent. 2026a. “Invent the Economy.”
<https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/3947e4ec8fd74ad40e13e8ff825a149fa98a10e9/docs/Invent_the_Economy.tex>.

</div>

<div id="ref-tae" class="csl-entry">

———. 2026b. “Transformational Autonomous Enterprises.”
<https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/3947e4ec8fd74ad40e13e8ff825a149fa98a10e9/docs/papers/transformational-autonomous-enterprises-v1.tex>.

</div>

<div id="ref-ti" class="csl-entry">

———. 2026c. “Transformational Intelligence: Learning to Change the
Game.”
<https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/3947e4ec8fd74ad40e13e8ff825a149fa98a10e9/docs/Transformational_Intelligence.tex>.

</div>

<div id="ref-scipyissue" class="csl-entry">

chrisb83. 2026. “BUG: Beta Quantile Failures in Extreme Tails, Issue
26531.” <https://github.com/scipy/scipy/issues/26531>.

</div>

<div id="ref-coordination" class="csl-entry">

MONTREAL.AI. 2026a. “AGI ALPHA Coordination Record, Issue 4850.”
<https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850>.

</div>

<div id="ref-publication" class="csl-entry">

———. 2026b. “Research Paper Upload and Publication Policy.”
<https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/3947e4ec8fd74ad40e13e8ff825a149fa98a10e9/docs/agent/PAPER_UPLOADS.md>.

</div>

<div id="ref-dlmf" class="csl-entry">

National Institute of Standards and Technology. 2026. “Digital Library
of Mathematical Functions, Section 8.17: Incomplete Beta Functions.”
<https://dlmf.nist.gov/8.17>.

</div>

<div id="ref-scipydocs" class="csl-entry">

SciPy Developers. 2026. “Scipy.special.betaincinv.”
<https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.betaincinv.html>.

</div>

<div id="ref-statsmodels" class="csl-entry">

statsmodels contributors. 2026. “Boundary Confidence Interval Issues and
Active Repairs.”
<https://github.com/statsmodels/statsmodels/issues/10536>.

</div>

<div id="ref-sympy" class="csl-entry">

SymPy contributors. 2026. “Kronecker Product Public Report and Existing
Repair.” <https://github.com/sympy/sympy/issues/30860>.

</div>

<div id="ref-bls" class="csl-entry">

US Bureau of Labor Statistics. 2026. “Software Developers, Quality
Assurance Analysts, and Testers.”
<https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm>.

</div>

</div>
