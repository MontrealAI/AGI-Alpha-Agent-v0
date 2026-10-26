# Bounded commercial screen: Python dependency upgrade decision packets

Screen started 2026-10-26T13:13:32Z. Allowance: at most 15 minutes of this research session. Sources accessed 26 October 2026. No outreach, account creation, purchase, quotation request, or financial transaction occurred. This is discovery evidence, not held-out confirmation.

## Decision

**A real need and a priced adjacent service category exist. A commercially defensible price for the current bounded AGI ALPHA dossier has not been established.** Free tools already perform substantial parts of this work. A generic upstream declaration-change report is insufficient evidence of a paid product; a faster repeat of that report is an engineering result, not commercial validation.

Continue the research only with a concrete user-decision test: can the packet tell a maintainer what an actual proposed dependency upgrade changes for their code, with verifiable evidence and useful next actions, beyond what their free tools already provide? If the implementation cannot connect affected declarations to the consumer's real use sites or a maintainer's explicit API promise, describe that as a missing useful capability. Do not call a package-wide list of possible changes a customer-specific compatibility assessment.

The strongest bounded offering is an **upgrade decision packet for one public Python codebase and one substantive dependency transition**. Its buyer hypothesis is a maintainer or engineering lead who needs to decide which code or tests must change before accepting a specific upgrade. A repeat mission needs a changed target version, consumer source revision, or declared requirement. No-op polls are not jobs.

## What public evidence establishes

### 1. There is a genuine technical need

In Starlette discussion #2770, dated 28 November 2024, a user reports that upgrading HTTPX to 0.28.0 broke tests for a service using Starlette 0.36.3: the forwarded `app` keyword was no longer accepted. The accepted response identifies upgrading Starlette or pinning HTTPX as practical choices. This is a concrete user problem and decision, not paid-demand evidence. The example is historical and exposed during this screen; it must not become an unseen confirmation case. [Primary discussion](https://github.com/Kludex/starlette/discussions/2770), web evidence `turn16view0` / `turn17view0`.

The underlying problem is broader than argument binding. Real upgrade work can also require test changes, environment adjustments, behavioral checks and deployment decisions. This study's limited call semantics must stay visible in its product description; an absence of supported call failures is not a general compatibility clearance.

### 2. A provider advertises a paid assessment, with substantially broader scope

Netlandish advertises a **$1,500 Django upgrade assessment**. It audits the codebase, dependencies, tests and deployment, then supplies a written upgrade plan and a fixed quote for subsequent implementation. The assessment fee is credited toward the upgrade. The same page discusses migration execution and cutover support, but those are subsequent work. This is a provider's current asking price, not a verified collected payment; the page does not explicitly label the dollar currency. It does not establish a price for a static call report or a non-AI execution baseline. [Provider page](https://www.netlandish.com/services/django-upgrades/), web evidence `turn13view0` / `turn14view0`.

The useful inference is that upgrade planning can be a paid professional-service deliverable. It is invalid to price AGI ALPHA at $1,500, claim that the dossier replaces that assessment, or report the difference as customer savings while omitting its broader scope and professional responsibility.

### 3. Provider case evidence supports the pain, without establishing our economics

Infield offers software and an expert-assisted upgrade service. Its Alice Financial case describes repeatedly postponed Rails upgrades and planning that became stale as dependencies changed. This is a vendor-published customer account in another ecosystem; it supports the hypothesis that current, actionable upgrade plans matter. Its savings claims and third-party quote are not adopted as measurements for this study. No current same-scope price was retrieved. [Provider](https://www.infield.ai/) and [case study](https://www.infield.ai/post/upgrading-rails-at-alice), web evidence `turn16view1` / `turn16view4`.

## The best free alternatives must remain in the comparison

| Alternative | Verified available capability | What the packet must add or demonstrate |
| --- | --- | --- |
| **Griffe** | ISC-licensed Python API extraction; compare Git revisions or PyPI package versions; detect breakages; Markdown output; GitHub CI annotations | A consumer-specific decision, validated reproducible witnesses, useful scope handling, or demonstrably lower complete delivery burden. Reformatting its output is not enough. |
| **Dependabot** | Included in GitHub Free; creates version/security update pull requests and presents release material; maintainers review the changes and test outcomes | Resolve a real uncertainty left by the update PR. Do not sell version detection or PR creation as a novel paid capability. |
| **Renovate Community Cloud / CLI** | Free community cloud across unlimited public/private repositories; open-source CLI; upgrade PRs, scheduling and configuration; eligible OSS projects can request enhanced resources | Give a useful report in the maintainer's existing update workflow without requiring a competing upgrade scheduler. |
| **Competent maintainer with Git, tests and these tools** | A legitimate human/conventional workflow with existing caches and project knowledge | Compare equivalent acceptance and responsibility. Do not disable these assets to create an easy baseline. |

Sources:

* [Griffe checking guide](https://mkdocstrings.github.io/griffe/guide/users/checking/), `turn13view2`; [PyPI project metadata](https://pypi.org/project/griffe/), `turn16view3`. License metadata and report capabilities were checked; this is not a statement that hosting or operation has zero resource cost.
* [GitHub pricing](https://github.com/pricing), `turn16view2`; [Dependabot version updates](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-version-updates), `turn14view2`. GitHub includes the feature in its free plan. [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), `turn15view2`, distinguishes free standard hosted runs for public repositories from private-repository usage allowances. Preserve actual execution charges where applicable.
* [Mend resource tiers](https://docs.mend.io/renovate/latest/mend-renovate-cloud-resource-tiers), `turn13view4`; [Renovate CLI repository](https://github.com/renovatebot/renovate), `turn11search15`.

Mend also lists Renovate Enterprise at **up to $250 per contributing developer per year**, with enterprise automation, confidence workflows and support. That is an advertised subscription metric, not a per-assessment transaction or a comparable standalone dossier price. It makes the commercial comparison more demanding rather than supplying a favorable price to borrow. [Pricing](https://www.mend.io/pricing/), `turn12view2`.

## Concrete acceptance standard for a useful offer

The packet should contain a short maintainer-facing decision summary; exact consumer and dependency source identities; affected declarations and the relevant supported use sites; independently checked witnesses explaining why a call previously accepted becomes rejected; next code/test actions; and an explicit unresolved-case inventory. It should be downloadable with source-pinned replay commands.

Each finding must distinguish an actual consumer exposure from a hypothetical upstream breaking call. The latter can be useful background but must not automatically block the user's upgrade. Findings must not imply production safety, correctness of business behavior, full dynamic-Python coverage, security clearance or completed migration. False all-clear results are unacceptable. Residual review belongs in the accepted outcome and cost model.

This definition does not claim that these additional capabilities are already implemented. It defines the commercial usefulness threshold against which the actual implementation must be inspected. A declaration-only result can still support a library maintainer's explicit public-API promise, but its incremental usefulness over Griffe requires evidence.

## Smallest practical test without outreach

1. Choose **one existing real upgrade decision** in a permitted public codebase: a recorded dependency update, pending source change, or explicit maintainer requirement. Freeze the consumer revision, source pair, decision question and acceptance criteria before inspecting outcomes. A known solved historical case may be a demonstration, not unseen confirmation.
2. Produce the ordinary free-tool dossier using Griffe plus the project's normal updater/test evidence. Keep its caches, output formats and relevant documentation. Separately produce the AGI ALPHA packet and a conventional builder's packet under comparable scope and resources.
3. Have an independent same-session reviewer determine whether the recipient can identify the relevant code, explain the failure and select a justified next action from each packet. Check every claimed exposure and unresolved case. Record usefulness and errors; count assertions separately from missions. This is product-readiness evidence, not a recruited buyer study.
4. Meter the entire production path, including inputs, tool setup, review, corrections, packaging, retries and the retained capability's construction. Report missing billing/attention data explicitly. If the packet adds no decision-useful evidence over the free alternative, reject it as the paid offering regardless of a faster inner loop.
5. Prepare the exact downloadable packet and a one-page offer with scope, acceptance, exclusions, required public inputs, and **price not yet validated**. A future inbound request or an existing authorized user's genuine purchasing choice can test willingness to pay. No synthetic respondent, internal allocation, download or page view establishes paid demand.

Without a buyer's choice or a transaction, a no-outreach test cannot establish willingness to pay. That limitation should be stated rather than obscured by a plausible consultant price. There is no need to delay a completed useful engineering result while claiming that missing market validation has occurred.

## Direct answers to the commercial questions

| Question | Supported answer today |
| --- | --- |
| What would a customer buy? | Hypothesis: one bounded, actionable upgrade decision packet for their public codebase and proposed version transition. Actual implementation must satisfy the acceptance standard above. |
| What does comparable service cost? | A broader Django assessment is advertised at $1,500; relevant free tools exist. No observed price for this exact limited deliverable was found. |
| What is our complete delivery cost? | Unknown until inference, construction, failures, upkeep and residual effort are identified or defensibly bounded. CPU time alone does not answer it. |
| What price can AGI ALPHA charge? | Unestablished; no arbitrary numeric price is introduced. A real customer choice and complete cost boundary are missing. |
| What does the customer save? | Unknown. The appropriate threshold uses the price plus customer effort and an equivalent human/free-tool alternative; no matched duration or willingness to pay was observed. |
| What surplus can finance reuse? | Actual collections in this study are zero. Earned surplus and complete repayment are not demonstrated. A numerical reserve allocation is not earned revenue. |
| Is continued research justified? | Conditional on useful decision support beyond the strongest free alternative and the predeclared bounded protocol. This is not commercial validation. |

## Evidence rejected or restricted during discovery

| Candidate | Disposition and reason |
| --- | --- |
| [Infield pricing-old](https://www.infield.ai/pricing-old) | Explicitly old pricing path; not treated as current numeric price evidence. Current `/pricing` fetch did not yield a usable page. |
| [Upwork Django audit listing](https://www.upwork.com/services/product/development-it-a-django-upgrade-audit-with-a-clear-plan-and-fixed-quote-2110448015644408805) | Search snippets showed tier prices, but full fetch returned 403. Not used as verified scope/price, much less a paid transaction. |
| [Agnotic Python consulting](https://www.agnotic.com/services/python-consulting) | Primary provider explicitly does not publish prices and quotes after inspection. Useful scope context; no numeric comparison. |
| GSA labor ceilings from the earlier economics screen | Maximum awarded hourly rates, without a matched dossier duration or collected price. Cannot establish per-deliverable willingness to pay. |
| UK procurement search results for Python/Django teams | Broad development/support or rebuild contracts surfaced, often through aggregators; no primary matched-price assessment transaction was established within the bounded search. Do not allocate an arbitrary slice of a large contract to this offering. |
| [Mend pricing](https://www.mend.io/pricing/) | Retained as adjacent subscription price context; excluded from direct per-dossier replacement savings. |
| [Infield Alice case](https://www.infield.ai/post/upgrading-rails-at-alice) | Retained for need/recurrence hypothesis; vendor-reported savings and quoted full Rails migration price excluded from the primary economics. |
| Safety/PyUp scanners and third-party essays | Different security-product scope or secondary claims. They do not price a call-compatibility decision packet. |

No source in this screen establishes an existing AGI ALPHA customer, a sale, a non-AI human duration, or a completed production upgrade. The resulting contribution should be presented as an executable, bounded move toward a useful service, with an explicit commercial gate that remains unpassed if decision utility, full cost or demand is missing.
