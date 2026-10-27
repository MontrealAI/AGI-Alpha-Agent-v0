# Round 2: concrete digital failures and a focused construction opportunity

**27 October 2026. Read-only discovery; no new candidate code, reproducer execution, customer contact or sale.** Five focused queries and three deep primary-source reads were used. Issue status was checked on the actual pages; search snippets were not treated as current status.

## Ranked conclusion

**Rank 1 — a reusable executable counterexample and repair instrument for scientific compute-to-artifact handoffs.** Its narrow purpose is to establish that a computational workflow's reported completion corresponds to a durable, readable, semantically correct artifact, and that cancellation/retry does not admit a stale result. The first qualification target should be the actual Xarray/Dask/Zarr failure below; cancellation is a separate adapter and transfer challenge, not an assumed common cause.

The strongest joint contract would require **actual process quiescence within the agreed bound, correct retry identity, no stale authoritative publication, and a separately verified artifact**. All four must be tested when promised. Revoke publication rights alone does not satisfy a requirement to reclaim native computation. Structured concurrency, staging, single-writer ownership, leases and fencing are established building blocks. Their correct integration and economical reuse are candidate contributions; a new label for an already efficient complete workflow is not.

**Rank 2 — cancellation-safe operation of native jobs under durable workflow orchestration.** This is meaningful work, with an independently reported executor boundary problem and another user describing crash-isolated workers. Its scope is narrower than general agent debugging, but it has more application-specific interruption contracts and substantial established solutions. It is a promising adjacent recipient after the first instrument, not a ready-made second customer.

The proposed asset need not invent a new distributed-systems algorithm. Expert diagnosis, replay, property testing, temporary output, atomic publication, idempotency and task fencing are legitimate building blocks. The research question is whether an executable method makes repeated, consequential integration work materially cheaper or more reliable than E, while preserving the original purpose. A good manual expert workflow is the comparator, not a reason to reject the opportunity automatically.

**Selection boundary:** there is enough public grounding for a small qualification experiment. There is not yet evidence of a market price, a buyer commitment, a generalized solution, or a useful gain on fresh tasks. Thermal remains outside flagship selection pending its separate grounding requirements.

## Two independently originated incidents

### 1. Xarray/Dask/Zarr: a successful write call leaves an unreadable scientific store

**Primary report:** [Xarray #10840](https://github.com/pydata/xarray/issues/10840), opened by `csubich` on 9 October 2025; still open on retrieval. The author supplies a complete synthetic reproducer and environment: Xarray 2025.10.1, Dask 2025.9.1, Zarr 3.1.3, Python 3.11.13. A Dask-backed dataset written through `to_zarr` produces a ZipStore that cannot subsequently be opened. A later reduction removes Xarray and still reproduces the problem with Dask and Zarr. A collaborator redirects the reduced case upstream to Zarr #3516. That linked issue's current fix status was not audited here. [S1]

This is actual publicly reported failure of an integration contract, with executable material rather than an invented customer story. The small array is a reduction of the defect, not the ceiling of the proposed instrument or evidence of a large commercial loss. The report demonstrates failed artifact integrity, **not silent numerical corruption**.

**Purpose to preserve:** write the intended dataset into the chosen supported storage representation, then recover its values and declared metadata in a separate reader. Source versions, execution mode, store lifecycle and output format matter. Merely suppressing a warning, changing the intended format without agreement, or declaring success before reopening the store does not satisfy that purpose.

**Credible beneficiaries:** scientific data-pipeline operators using this stack, maintainers integrating its components, and research-software engineers responsible for portable dataset delivery. They are beneficiary classes; the issue author has not agreed to buy anything.

**Available artifact:** full reproducer and version report on the issue, plus its reduced Dask/Zarr case. The dynamic issue page and an unpinned `main` installation are not sufficient frozen evidence: archive the report, pin source/wheel identities and dependencies, and preserve all outputs before any experimental claim. Current reproduction remains unperformed.

### 2. Temporal/native executors: logical cancellation does not necessarily stop work

**Primary report:** [Temporal Python #1048](https://github.com/temporalio/sdk-python/issues/1048), opened by `gregbrowndev` on 24 August 2025; still open on retrieval. The author links a runnable cancellation example and later a process-signal prototype. Maintainers explain that process execution needs explicit interruption/cancellation handling and offer existing APIs and an async-wrapper approach. Another user reports using a `billiard.Pool` adapter for activities that can segfault, then encounters missing activity context when waiting for cancellation from another thread; the maintainer explains context propagation. Duplicate effects and corrupted outputs are raised as risks, not demonstrated incidents in this thread. [S2]

**Purpose to preserve:** cancellation, worker shutdown and retry must follow the application's agreed compute and result-publication contract. Some jobs need bounded resource reclamation; others permit computation to finish but forbid its stale output from becoming authoritative. These are distinct obligations. An instrument cannot silently replace the first with the second.

**Credible beneficiaries:** operators of expensive native scientific or AI jobs, durable-workflow integration teams, and suppliers of crash-isolated computational services. Their executor, native library and output semantics determine what intervention is valid. No universal safe interruption method is established by the report.

**Available artifacts:** the issue links `hello_cancellation.py` and a public signal prototype. Their exact bytes, licenses, supported platforms and assumptions must be inspected and frozen before reuse. The linked code was not executed or independently audited in this desk pass; do not claim otherwise. The documented remedies belong in E.

## A third report that must not be misrepresented

[Temporal Python #1881](https://github.com/temporalio/sdk-python/issues/1881), opened 17 September 2026, provides a complete same-version live/replay reproducer involving local-activity completion grouping. A second reporter confirms the regression and explicitly says all tested variations failed loudly; effects in live worker replay were not established. A maintainer closed it on 30 September, saying the next Core update would fix it. The search listing still called it open. This is **historical development material**, not a fresh unresolved silent-corruption case. [S3]

It is useful for testing whether an instrument localizes semantic task identity across a language SDK/Core boundary. Existing `Replayer` already detects the failure; simply running it is not a new detection capability. The author supplied a reduced reproduction and diagnosis, so neither can be attributed to our system.

## What the instrument would actually construct

Start with an independently written task brief and the existing workflow/repository. Preserve the original output and cancellation contract. The candidate method must construct:

1. A frozen executable environment and adapter that observes computation, serialization, close/reopen, validation and publication at their actual boundaries.
2. An independent output oracle: for scientific stores, compare values, coordinates, dimensions, masks, units/attributes and relevant derived scientific quantities; for cancelled/retried work, associate permitted publication with the correct logical task, attempt and current authority.
3. A reduced, replayable causal counterexample. Intervene on one justified mechanism at a time—executor, lifetime, ownership, task grouping or publication protocol—and show which intervention changes the original-purpose outcome.
4. A repair or supported operating method, with regression coverage and explicit limitations. It may conclude that the requested execution/storage combination cannot satisfy the required contract within budget.
5. A transferable adapter/compiler component so a new recipient can qualify a different real workflow without rebuilding every observation and oracle connection manually.

This goes beyond a generic trace-summary service: actual software is executed and resulting bytes/state are checked. It also goes beyond collecting two bug scripts: the measured contribution is the construction and reuse procedure on unfamiliar jobs. Existing debugging, Hypothesis/property testing, upstream suites, deterministic replay and expert version bisection remain part of E. There is no need to prove that every commercial product lacks the feature; there is a need to demonstrate added value against the recipient's genuine outside option.

The shared structure is currently a **hypothesis**: task success and authoritative artifact success can be separated across integration boundaries. Do not claim that the two reports have the same root cause, require one repair, share buyers, or justify pooled finance merely because both involve asynchronous execution.

## Smallest decisive experiment

### Gate 1: reproduce the real problem and its ordinary remedy

After selection, **qualify the need before building the reusable instrument**: reproduce S1 and S2 in their reported closures and in authoritative current releases, identified from official release metadata and frozen dependencies. The first deliverables are inspectable artifact/process-state results and independent verdicts. Establish whether an upgrade or supported complete workflow already solves the joint requirement. A fixed version is a successful conventional outcome. Preserve the original failing history for development; an open issue alone is not evidence of a current defect.

Give E the same public report, current documentation, upstream tests, source access, capable frontier model and permitted tools as E+. Include a straightforward round-trip test, version bisection and maintainer remedies. If E+ merely automates a small check already available to the recipient, assess the measured operational saving proportionately; do not inflate it into a transformational platform.

### Gate 2: test useful reuse on independently collected workflows

Before developing the reusable policy, an independent curator should collect four additional public integration failures or owner-supplied needs with runnable artifacts, freeze their task requirements and hide their resolution evidence. Select by relevance and reproducibility, not whether the candidate wins. Use S1 and, if justified, S2/S3 only for development; all have already been read in this workstream.

A meaningful confirmation task includes the original scientific workflow or faithful public reproducer plus its actual intended output contract, rather than arbitrary perturbations of the same ten-element array. A public Earth-observation software lead surfaced during search: the EOPF Core Python Modules 3.0.0 release notes mention incorrect results associated with ambiguous Dask task names. This is **a search-only lead, not an audited fourth source or confirmed evaluation case**. Its linked issue and original workload would need separate inspection before use. [L1]

If fresh unresolved public tasks are unavailable, independently collected historical cases are acceptable as an explicitly **retrospective held-out evaluation**. Withhold patches and post-resolution discussions from the active task context, but acknowledge possible model-training contamination. Do not call them prospectively discovered bugs. At least one recipient should have a different storage/executor boundary and original purpose; generated fault variants can be adversarial controls, not replacements for independently originated needs.

A possible transfer is a native analysis job producing Parquet for an independent DuckDB consumer. Its source workflow, cancellation deadline, schema and intended query result must be independently chosen and frozen before outcome inspection. A researcher-created variant remains a transfer stress test, not a newly discovered public need. Do not assume this backend has a defect or that the retained instrument improves it.

At matched resource budgets, compare accepted reproductions, useful repairs, correct refusals, diagnosis accuracy, recurrence under perturbation, total preparation/correction/evaluation cost and elapsed time. Also compare complete cost at matched accepted quality. Freeze the candidate before confirmation, preserve failures and count construction costs. An independent evaluator must test the promised artifact/state invariant, including a case where no repair is needed. More passing generated tests alone is not customer value.

**Decisive falsifiers:** false acceptance of corrupted/stale output; a proposed remedy changing the original purpose; no useful savings after adaptation and review; repeated failure on a different stack; or existing E obtaining equivalent results at lower complete cost. A counterexample can be useful even if no repair is found; price and acceptance must reflect that narrower deliverable.

## Offering, participation and rights

A credible initial offer is a scoped **workflow handoff qualification and repair service**, with an executable reproduction, verified output contract, supported remedy or documented no-go, and a retained regression package. H is the equivalent research-software engineering service. An estimated price may use disclosed hours/rates; no matched quotation or observed demand was obtained here.

The common instrument can be retained while customer datasets, secrets and proprietary code remain private. A shared development commission is optional and requires genuine overlap among independently motivated jobs. Separate accepted diagnostic work, accepted repair and continuing support; distinguish advances, earned collection, refunds and available cash. A buyer can adopt an existing upgrade or decline.

Use public rights-cleared code or obtain permission; an issue's public visibility is not blanket reuse authority for every linked artifact. Contribution rules and maintainer release authority remain separate from a successful local test. No messages, upstream PRs, production actions or tool-triggered side effects are authorized by this dossier. Existing protected transport can distribute admitted executable components only after fresh scope, evidence and authority checks. Retain failed candidates, source provenance and costs; claim no live ENS authentication.

## Sources and evidence status

- **S1 — deep read:** https://github.com/pydata/xarray/issues/10840 ; browser refs `turn77view2`, `turn78view2`, `turn79view2`. Public reported corruption, complete and reduced reproductions, environment, upstream redirection. Current execution and upstream linked-fix status unverified.
- **S2 — deep read:** https://github.com/temporalio/sdk-python/issues/1048 ; refs `turn77view1`, `turn78view1`, `turn79view1`. Independent cancellation need, maintainer remedies, second executor user, linked examples. Current reproducer execution unperformed.
- **S3 — deep read:** https://github.com/temporalio/sdk-python/issues/1881 ; refs `turn77view0`, `turn78view0`, `turn79view0`. Historical complete reproducer, independent replication report, loud failures, explicit scope limits and closure.
- **L1 — search-only lead:** https://cpm.pages.eopf.copernicus.eu/eopf-cpm/3.0.0/srn.html ; `turn75search20`. Do not treat its source or fix as audited.

The proposed work is grounded in externally originated needs but remains researcher-selected. The instrument, subsequent fresh task collection, market assumptions and financing mechanism have not been constructed or observed. This edition can test actual digital artifacts without physical trials; it cannot substitute public bug counts for demand or simulated receipts for revenue.
