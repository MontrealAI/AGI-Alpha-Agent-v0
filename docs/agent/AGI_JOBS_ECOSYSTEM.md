[Project notice](../DISCLAIMER_SNIPPET.md)

# Alpha Agent + AGI Jobs: from a useful idea to accepted work

**Alpha helps produce useful work. AGI Jobs supplies rules for commissioning, reviewing and settling it.**
The combination offers building blocks for a traceable work cycle: choose a task, produce an artifact,
check it against agreed criteria, settle the accepted work and retain what proved useful.

For a nontechnical introduction, open the **[visual guide and complete contract directory][visual-guide]**
or its **[French edition][visual-guide-fr]**. Both editions contain all addresses as ordinary page content;
no account, wallet or browser script is needed to read them. The [AGI Jobs companion guide][jobs-guide]
explains the other side of the connection.

## One shared token, two independent contract suites

Both public deployment records identify this token:

| Field | Recorded value |
| --- | --- |
| Token | **AGI ALPHA · `$AGIALPHA`** |
| Network | **Ethereum mainnet · chain ID 1** |
| Decimals | **18** |
| Contract | [`0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA`][token] |

The shared token allows both suites to express funding, stakes or settlement in the same asset according
to their own rules. Each suite still has separate balances, approvals, roles and contract state.
A payment to the native agent, an Alpha campaign contribution and an AGI Jobs escrow deposit are distinct actions.
The [Alpha manifest][alpha-manifest] and [Jobs inventory][jobs-inventory] identify the same token;
the [native capability matrix](CAPABILITIES.md) describes the separate invoice and receipt workflow.

| Suite | Public record | What the record contains |
| --- | --- | --- |
| Alpha Ascension | **11 October 2026** · [pinned manifest][alpha-manifest] | **5 deployed contracts** for participant admission, plan records, risk review, campaign funding and Alpha's own job market |
| AGIJobsv0 | **12 October 2026** · [pinned inventory][jobs-inventory] | **24 deployed instances**: deployment coordinator, 13 modules and 10 fixed implementation contracts |

There are **29 suite instances** in this directory. The canonical token is a shared dependency and is not
included as an additional suite instance. The [complete address data](../assets/ecosystem/contracts.json)
retains the exact names, addresses and immutable source references used by the English and French pages.

## What each part contributes

### Alpha: plans, artifacts, evidence and constrained funding

The supported agent performs bounded research, allocation, scheduling, forecasting and isolated code missions.
It can retain the input, result, review and signed evidence needed to examine a decision later. Approved memory
reuse helps later compatible missions; it does not automatically retrain a general model or grant future actions.
SUCCESSOR Ω explores bounded capability development with fresh evidence for a successor.
See the [capability matrix](CAPABILITIES.md) and [SUCCESSOR architecture](SUCCESSOR_ARCHITECTURE.md).

The deployed Ascension suite adds contract rules around a project and its funding. Its five roles are:

| Contract | Plain-language purpose |
| --- | --- |
| **AscensionAccess** | Check participant identity and admission through the configured ENS roles |
| **NovaSeed** | Represent a plan record and its lineage as a token; token ownership does not establish legal ownership of every referenced artifact |
| **AscensionRiskOracle** | Collect staked risk reviews and record reviewer availability |
| **AscensionJobMarket** | Apply Alpha market rules for auctions, work review and settlement |
| **AscensionMark** | Receive campaign funding and restrict spending to jobs allowed by the committed plan |

Read the [archived deployed source][alpha-source] alongside the [Alpha deployment guide](MAINNET_DEPLOYMENT.md).
The source currently maintained in the repository includes later safeguards and is not a substitute for the
archived source when assessing an existing address.

### AGI Jobs: the commissioned-work lifecycle

AGI Jobs provides a job registry, escrow and stake accounting, validation, dispute handling, reputation,
completion-certificate records, fees, identity and platform controls. Its deployment also includes fixed code
components used by the main modules. These components are counted in the 24 instances; they are not additional
marketplaces. The [deployed-source revision][jobs-source] and [deployment inventory][jobs-inventory] identify
the implementation being described.

These mechanisms can make terms, commitments and authorized outcomes traceable. Reviewers and task-specific
tests must establish whether the artifact meets the agreed requirements. A token transfer, hash or signature
alone does not establish that a report is accurate or a program is useful.

### The connection: an explicit operating workflow

A useful connection passes the exact task, artifact, acceptance criteria and review evidence between the
producer and the chosen market. The operator must choose that market, map the participants, configure the
permitted actions and commission the end-to-end process.

**The deployed Alpha MARK contract is fixed to Alpha's own JobMarket.** It does not automatically route campaign
funds into AGIJobsv0. Sharing AGIALPHA is not a bridge between the two markets. This guide does not establish a
completed cross-repository live job or a ready-to-use unified service. That boundary follows from the
[deployed MARK source][alpha-source] and the [deployment guidance](MAINNET_DEPLOYMENT.md).

The Jobs identity code supports Alpha namespace aliases. That is useful compatibility at the code level;
actual admission still depends on the selected deployment's configuration, role ownership and stake terms.
An Alpha identity or an agent's local signing key is not automatic permission to participate in Jobs.
See the [Jobs identity source][jobs-identity] and [Alpha capability boundaries](CAPABILITIES.md).

## A practical example: make a public-data calculation faster

The following is an **illustrative connected workflow**, not a report of an actual paid job:

1. **Agree on success.** Choose public or licensed data, define exact expected outputs and a runtime target,
   and agree on a budget, review deadline and acceptance tests.
2. **Produce a candidate.** Use a suitable Alpha code or research workflow to propose an implementation.
   Compare it with a baseline and retain the program, input digest, environment and measured results.
3. **Connect the work to the selected market.** Through a commissioned integration, register the agreed job
   terms and provide the exact artifact and evidence to the authorized reviewers.
4. **Review before accepting.** Reproduce the important tests and evaluate the result against the original
   criteria. Handle disagreement through the selected protocol's process.
5. **Settle according to the rules.** The chosen market applies its configured settlement rules to the
   accepted outcome. The operator records the corresponding result and payment evidence.
6. **Retain what was useful.** Keep the accepted artifact and measured lessons. A later task still needs its
   own budget, permissions and checks.

The benefit is a clearer chain from a work request to an examinable result. This example supplies no measured
speedup, earning forecast or claim of general autonomous intelligence. A small, reproducible task is the useful
starting point because its result can be checked.

## Deployment evidence and readiness are separate

The directory was prepared from public records on **12 October 2026**. It identifies deployed addresses and
their recorded sources; it is not a fresh RPC snapshot or a security audit.

The Alpha record does not establish participant commissioning or public funding readiness. Its deployed
contracts predate newer settlement safeguards and cannot be upgraded in place. Resolve that difference using
the [current Alpha deployment and migration guidance](MAINNET_DEPLOYMENT.md) before admission or funding.

The dated Jobs record explicitly does not approve production or open live intake. Its recorded deployment
state should not be treated as a statement of current permissions or operating status. Consult the
[current Jobs readiness guide][jobs-readiness] and the [dated commissioning record][jobs-commissioning].

The two repositories discussed here are **AGI-Alpha-Agent-v0** and **AGIJobsv0**, with their recorded AGIALPHA
deployments. The separately maintained AGIJobManager project has a different settlement model. Always match
the repository, network, token and address to the intended workflow.

## Explore and maintain this guide

Start with the [personal SUCCESSOR Ω lab][personal-lab] or [first-plan experience][first-plan]. Both are free
browser experiences and do not submit blockchain transactions. Then inspect the [29-address directory][visual-guide]
and the linked public evidence at your own pace.

For maintainers, `scripts/generate_ecosystem.py` reads `docs/assets/ecosystem/contracts.json` and the two
maintained HTML templates. It is called by the normal `scripts/generate_gallery_html.py` build. It checks the
network, token, instance counts, distinct complete addresses and Alpha archive agreement before rendering
the static English and French pages. Regenerate the gallery and service-worker assets after changes;
retain dated evidence when updating the directory rather than relabeling an old snapshot as current.

[visual-guide]: https://montrealai.github.io/AGI-Alpha-Agent-v0/ecosystem/
[visual-guide-fr]: https://montrealai.github.io/AGI-Alpha-Agent-v0/ecosystem/fr/
[jobs-guide]: https://montrealai.github.io/AGIJobsv0/ecosystem/
[token]: https://etherscan.io/address/0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA#code
[alpha-manifest]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/755f678954be8e334e69e4d37f56f3fe10da2d84/deployments/ethereum-mainnet/2026-10-11/manifest.json
[alpha-source]: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/755f678954be8e334e69e4d37f56f3fe10da2d84/deployments/ethereum-mainnet/2026-10-11/sources/contracts/ascension
[jobs-inventory]: https://github.com/MontrealAI/AGIJobsv0/blob/a1dea46d2f9dfa5680d11e24529f107d65cd4369/docs/deployments/ethereum-mainnet-2026-10-12.json
[jobs-source]: https://github.com/MontrealAI/AGIJobsv0/tree/b4c5b66ea05a6bb27f1f1cb197f055c179bbd38e/contracts/v2
[jobs-identity]: https://github.com/MontrealAI/AGIJobsv0/blob/b4c5b66ea05a6bb27f1f1cb197f055c179bbd38e/contracts/v2/IdentityRegistry.sol
[jobs-readiness]: https://github.com/MontrealAI/AGIJobsv0/blob/main/docs/production/readiness.md
[jobs-commissioning]: https://github.com/MontrealAI/AGIJobsv0/blob/a1dea46d2f9dfa5680d11e24529f107d65cd4369/docs/production/mainnet-deployment-2026-10-12.md
[personal-lab]: https://montrealai.github.io/AGI-Alpha-Agent-v0/successor/play/
[first-plan]: https://montrealai.github.io/AGI-Alpha-Agent-v0/start/
