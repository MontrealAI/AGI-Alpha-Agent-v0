# Independent preconfirmation review

This review is by a separate assistant agent. It is not an external laboratory replication, human security audit, or production release approval. No protected confirmation inputs or results were generated or inspected by this reviewer during the review recorded here.

## Reviewed contribution

The parent is a bounded exact-commit Git reader. It replaces repeated native Git process launches with native batch commands while preserving requested-path, regular-file, commit-type, per-file, aggregate-byte, batch-stream and returned-blob identity checks. It contains no persistent mutable-file digest cache.

The child is a deterministic composition of the accepted parent reader with a prewritten archive-drift comparison mechanism. The controller binds the child to the accepted parent bytes and a content-hashed prior-use receipt. The executed child invokes the parent and records the returned inventory. This is concrete software composition and qualification, not autonomous invention of a new algorithm.

## Independently written comparator

`specialist.py` was written before inspection of candidate code. Its final direct reader uses two Git processes: literal `ls-tree -l` and `cat-file --batch-command`. It independently deduplicates blob identities and checks every returned blob's native SHA-1 identity. Its direct archive diagnoser qualifies archive bytes and reports complete changed, missing and extra path lists. The earlier three-process comparator was superseded during development by a stronger two-process version; this is a development revision, not confirmation tuning.

## Executed development checks

- Parent: 29 independent valid-input, refusal and corruption checks. Candidate and specialist pass.
- Child: 19 independent checks, including complete drift, stored/deflated data, traversal, duplicate names, linked files, directories, byte budgets, encryption, CRC, truncation, archive symlinks, excess members, noncanonical names, empty archives, NUL truncation, DOS directory flags and detected mutation during capture. Candidate and specialist pass.
- The capture-mutation check changes the actual archive mtime between its read and the subsequent file-descriptor stat check using a test wrapper. It checks the implemented detection boundary; it is not a proof against every possible filesystem race.

The initial child source review identified acceptance-domain differences involving empty archives, NUL-truncated names, DOS directory flags, archive bounds and capture-change checks. Root corrected these before this review's candidate child execution. The executed candidate child checks therefore passed; this review does not invent an earlier failing execution.

## Experimental design findings

Seven arms include a direct specialist, an unrestricted no-asset alternative, ordinary saved tooling, an equally funded conventional reusable-tool arm, the proposed composition, independent equivalent content, and exact reconstruction with legitimate template access. The strongest specialist remains available. No agent is forced into a weak algorithm or unnecessary reconstruction merely to create an apparent benefit.

The protected generator creates 24 fresh, source-derived Git repository instances with variable inventories, layouts, duplicate-object regimes, poisoned working trees and preassigned archive drift. The statistical unit is a generated repository instance, conditional on one source ecosystem and generator. These are not 24 independently sampled natural repositories.

The primary estimand is paired mean log CPU ratio for the orchestrated read-plus-child pipeline, including construction, retrieval, independent output verification and intermediate persistence up to the final outcome-row write. Each phase aggregates one initial process call and three warm-process calls. The predeclared gate requires zero correctness failures and the 95% bootstrap upper bound below 0.95 against the strongest direct specialist. The four within-instance repetitions are not treated as four independent observations.

The analysis must preserve every attempted arm, including refusals and timeouts; failures block admission. Timings under failed correctness are unqualified cost records. All benchmark operations are deterministic; no language-model agent comparison is executed.

## Cost and authority boundaries

Execution CPU and elapsed time are observed separately. Construction/materialization and service accounts are separated. Discovery, hand-authored implementation, reviewer effort, model use in research, integration and future maintenance are not free simply because they are outside the timed worker. Unknown amounts remain unknown. Full research payoff and monetary profit are not established by a small operational CPU reduction.

Native Git SHA-1 checks establish consistency with the repository's object format for returned blobs. The reader still relies on Git's interpretation of the commit/tree graph in a trusted local repository. It is not an authenticity proof, signing mechanism, release approval, or complete hostile-object-database verifier.

The paper-only caller's non-executable-mode policy must remain stricter than the general reader's regular-file policy. A general helper does not authorize widening any existing caller or release policy. Production publication, approved connected execution and final release checks retain their own owners.

## Outstanding freeze checklist

Before the one confirmation campaign, freeze candidate/comparator/constructor/worker/runner/measurement/analysis/oracles/generator bytes, protocol, selection and development evidence. Generate the fresh seed afterward. Lock each oracle and archive along with the case manifest. Verify the source freeze and task lock before and after execution. Require complete 24-by-7 outcome coverage and no duplicated pairs. Record fresh-process and warm-process timing separately as secondary observations.

The reviewed runner and analysis now implement the required timeout accounting, complete-pair validation, independent parent-trace checks, input locks, identical before/after freeze identities, complete instance costs and separate fresh/warm summaries. Final freeze contents still need their own byte-level check immediately before generating the confirmation seed.

Development selection chose the candidate from five A-only repetitions whose median complete-operation CPU was approximately 2.6% below the direct specialist. That small, noise-sensitive development difference is a method-selection observation, not an established performance benefit. The prospective confirmation remains the decision evidence.

This is a scientific review of the bounded experiment. It grants no release or execution authority.
