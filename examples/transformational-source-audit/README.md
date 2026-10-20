# Bounded static source-package audit

This separate driver produces a useful **static source inventory**: exact captured file/blob identities,
SPDX headers as found, top-level public symbols, syntactic import targets, captured direct/transitive
dependency closure, references outside the capture and unresolved dynamic-import warnings. It parses
supplied Python text with the standard AST parser. It never imports or executes that text, opens a
network connection, invokes a model, prepares a payment or changes the native selector language.
Its schema is `ti-source-package-audit/v1`, not `transformational-intelligence/v1`.

The capture is complete **only for its listed files**. From-imports conservatively include candidate
submodules present in that capture; a runtime attribute can shadow such a submodule. Dynamic imports,
optional-import control flow, installed external distributions and runtime side effects are not resolved.
This inventory is neither an execution graph nor a vulnerability or license-compliance certification.
Ambiguous `root/foo.py` / `root/foo/__init__.py` module identities are refused.

## Actual mechanisms and controls

The installed language contains all 64 combinations of six Boolean choices. A choice changes executed
operations and retained counters, rather than merely annotating the same computation.

| Axis | Inherited formulation | Installed alternative and observable ablation |
| --- | --- | --- |
| Representation | Sequential static fact list | Keyed fact dictionary; `build-fact-index` / `keyed-query` replace sequential fact examinations. This is a fact-list/index comparison, not a raw-language understanding claim. |
| Information query | Parse source again for each requested fact | Retain one bounded AST-derived fact materialization per source; `retain-facts` appears and actual `parse-ast` count falls. No extra external information or permission is supplied. |
| Dependency | Independently walk the captured graph for each source | Propagate closure through an explicit dependency work queue, including cycles; `dependency-queue-pop` replaces repeated dependency walks. This changes closure construction, not available hardware parallelism. |
| Production | Reconstruct canonical report fragments repeatedly | Retain/reuse immutable fragments, with construction and cache charges; `reuse-fragment` appears in the unbatched ablation. |
| Task boundary | Four inherited per-file reporting subtasks, later merged | Produce the final package inventory directly in one package job per file; actual job count falls from four per file to one. Both must deliver the complete same artifact. |
| Coordination mechanism | Unchecked last-write worker proposals | Version-bound proposals and exact row checking refuse stale or incorrect writes; `checked-CAS` / `reject-stale-or-invalid` retain the rejection. This is a bounded local protocol, not a distributed worker deployment. |
| Evaluation | A file-count proxy can reward an invented-symbol report | A real disagreement probe proposes the exact-report instrument. Separately configured verifier/controller signatures must revise the existing `MeasurementLedger`; a new campaign then reruns **all** controls under its common new epoch. The optimizer cannot sign or approve this revision. |

All comparisons share the supplied source, goal, static tools, action permissions and allowances.
The unchanged `000000` program, hand-engineered `111111` program, bounded automated development selection
and unrestricted per-package oracle are retained. Every one of the 64 methods actually executes on
development and confirmation. The oracle transparently reuses those measured costs/artifacts; its
selection inspections are charged. Exact equality with the fixed full-report reference remains an
admission gate even when the weaker file-count proxy reports success. No metric can admit an incorrect
artifact by changing the goal. The same reference is available to every method, including checked
handoffs; reference construction, row checks and final output checks are charged.

The six mechanisms are an installed finite software example. They do not establish general discovery
of arbitrary representations, experiments, coordination rules or evaluators. The inherited repeated
subtasks and stale-write fault are explicit constructed conditions, not a measured industry baseline.

## Reproduce the actual public-source fixture

`fixture.json` retains six real Apache-2.0 source files, including their original headers, from immutable
Alpha commit `d0d18127e3d75b2b1bd13ca448265ba7e75fc21e`. Development captures three utility files;
confirmation captures three different SUCCESSOR files and supplies an explicit stale-proposal fault.
The files were compared byte-for-byte with that Git commit when the fixture was prepared. At runtime,
Git blob and SHA256 commitments validate the supplied bytes. Those hashes do **not** establish remote
origin, public availability, authorship, non-personal content or permission to use arbitrary replacements.
The CLI consumes explicit captures as claims and does not download or inspect a caller-selected checkout.

Use only public, non-personal source with appropriate rights. Credential-shaped fields, populated Python
credential assignments/keys and serialized credential strings are refused before retention. Screening
is bounded and conservative; it does not classify all personal information or prove a capture is public.

With the installed locked runtime, choose new paths:

In the extracted operator bundle the fixture is
`transformational-examples/transformational-source-audit/fixture.json`; use that path in place of
the source-checkout `examples/...` path below. The same installed command needs no source checkout.

```bash
python -m alpha_factory_v1.core.runtime.successor.transformation_source_audit_cli \
  --home /ABS/NEW-PRIVATE-SOURCE-AUDIT \
  --output /ABS/NEW-SOURCE-AUDIT-EVIDENCE.json \
  demo examples/transformational-source-audit/fixture.json --approve-free-local-audit

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --noconftest -o addopts= \
  tests/runtime/test_transformation_source_audit.py -q
```

The approval flag covers only this exact bounded free local comparison. It does not approve imported
code execution or spending. The private Journal retains the charter, source text, bindings, frozen
program, method traces, exact reports, failed artifacts and costs. The evidence export contains no
Journal signing key. State/output paths are never overwritten. For an existing initialized home,
standalone `create`, `approve`, `freeze`, `confirm`, `control`, `show` and `context` commands expose the
same boundaries; `--help` describes their explicit arguments.

The checked-in `expected-results.json` records the actual run:

| Observation | Result |
| --- | --- |
| Frozen development selection | `110010`, indexed / retained queries / package batching, unchecked handoff |
| Fresh confirmation | Candidate rejected: its stale worker proposal corrupts the final artifact |
| Exact confirmation methods | 32 of 64; all 32 checked-handoff methods reject the stale write |
| Hand-engineered `111111` | 22,745 logical units |
| Unrestricted oracle over executed methods | 22,721 logical units |
| Full development + confirmation comparison | 4,832,867 declared logical units, including 673 search inspections |
| Claimed advantage over oracle | None |

The negative candidate remains terminal; confirmation cannot be replaced by a more favorable package.
The exact reference report and successful alternative artifacts remain inspectable alongside the
corrupted report. Replaying the exact terminal input returns history without executing or charging again.
An exposure ledger in the same Journal records capture identities and individual source blobs from
development inputs, measurement probes and committed confirmation captures before their comparison,
including partial and failed work. A later campaign cannot reuse **any** previously observed blob as
part of a fresh terminal package, or overlap source blobs between terminal packages. Adding an
irrelevant file to a known capture cannot mint freshness. Raw committed captures
remain in confirmation evidence even when the comparison fails. Identical source-blob sets relabeled
with new paths, repositories, commits, fault flags or duplicated bytes remain the same exposure. The
bounded ledger refuses further admission at 512 unique captures or 4,096 source blobs; it is never reset to obtain a fresh
holdout. A legacy prototype Journal missing its exposure checkpoint fails closed rather than guessing.
These checks do not establish semantic independence or cross-journal experimental
custody. The public same-repository captures are not independent benchmark campaigns.

## Separately approved evaluator revision

`propose-measurement PACKAGE.json` performs and journals an actual disagreement probe: preserve the file
count while inventing a public symbol. The old proxy returns 1,000,000 ppm; the exact report checker and
declared outcome return zero. The unsigned proposal includes both reports, their evidence commitment,
the proposed instrument and its logical costs. It cannot change the current measurement context.

A separately installed public trust registry and producing identity are required for
`revise-measurement PROPOSAL_DIGEST VERIFIER.json CONTROLLER.json --operation-id ID`, supplied with global
`--trust` and `--producer`. The verifier's `measurement-validation` payload must bind this Journal,
the current previous instrument, the exact proposed instrument digest, diagnosis, scope and retained
disagreement cases. The distinct controller's `measurement-approval` binds the entire signed validation.
The existing ledger checks signatures, configured roles, distinct principals/keys and stale predecessors.
Neither production module nor CLI generates signers or signatures. Test-only local signers demonstrate
the boundary and do not constitute independent organizational review.

After revision, `context` returns the new exact instrument/epoch. Older approvals cannot continue under
it. Create and separately approve a **new** campaign with that context and a new complete comparison;
the driver reruns all 64 controls under the same instrument. A source change also invalidates instrument
bindings. A new measurement epoch does not make previously observed confirmation source fresh.
Historical results remain readable. The driver does not reserve a statistical confirmation
attempt, attest independent samples, claim calibration or promote a method into the native library.

## Costs, bounds and recovery

Logical costs explicitly cover source/AST observations, index and fact construction, queries,
dependency operations, fragment/report production, work proposals/checking, exact reference comparison,
search and oracle inspections. Failed/partial work retains charges. Artifact deduplication shares only
identical retained evidence; method execution is not skipped. Revision-proposal costs are retained in
their separate Journal record, not silently charged as a successful discovery comparison.

Each fact parse charges its byte observations and every explicit AST-node visit in the node census,
import pass, dynamic-call pass and top-level symbol pass. Graph construction and both closure algorithms
charge vertex/edge examinations, membership tests, set insertion/removal attempts and stack/queue
pushes/pops. Traversal sorts set members to make these declared counters reproducible. A separate
regression checks the AST-visit arithmetic against a hand-counted AST, and the wildcard-import
regression asserts the initializer/helper closure independently of the shared parser.
Candidate exactness/cost inspections, every development/control minimum candidate, oracle validity
and minimum comparisons, and frozen candidate/control comparisons have separate charged search traces.

The rule excludes Python allocation and CPU instructions, schema validation/hashing and source binding,
Journal signing/I/O, human review, energy and money. These costs are unknown here; declared logical units
do not establish elapsed-time savings, an economic break-even horizon or production efficiency. The
actual fixture command took about seven seconds locally; this is no performance guarantee.

Public-source admission screens visible bindings and statically closed text/bytes composition without
executing supplied code. Literal additions, bounded repetitions and supported static f-strings are
folded before nested-source screening; nonempty static format specifiers are refused. Each parsed or
constructed value is limited to 65,536 bytes. A shared 1,000,000 byte-unit budget covers recursive
parsing and literal construction, alongside the existing 12,000-node and four-level nesting bounds.
These are conservative admission limits, not physical resource measurements or proof of arbitrary
runtime values, aliases or privacy. Operators must supply public, non-personal source.

Inputs have bounded file count/UTF-8 bytes/AST nodes and the finite 64-program language. Phase execution
is serialized by the Journal transaction. Pause/cancel and native STOP apply between these bounded
phases; they do not interrupt an AST parse or promise asynchronous termination. Normal concurrent
restarts execute a phase once. A process crash can perform unrecorded physical work before rollback;
that unknown cost is not zero. Keep a separately retained checkpoint and private backup. Restore into
a new home with its exact runtime; do not discard newer cancellation/accounting history to repeat a run.
Exports are inert, incompatible with native TI v1 importers, and grant no execution, reuse, publication,
wallet or settlement authority.
