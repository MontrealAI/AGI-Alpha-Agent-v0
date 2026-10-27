# Independence boundary

The edge-balance checker was authored from the mathematical task specification before its author inspected the new numerical executor. It uses Python `math.fsum` over graph edges and node grounding, rather than the executor's sparse matrix assembly and SciPy solve routines. Its source has remained unchanged during executor review.

After writing and testing that checker, the same reviewing agent inspected the executor, reproduced validation/persistence defects and an integer-grounding assembly defect, and applied the root-authorized corrections before confirmation. That agent also wrote regression tests and reviewed the runner. Therefore the final checker is a separately implemented numerical check, but the final software package does **not** have completely disjoint authorship or an external institutional replication. Reviewers share the commissioning agent, task context, filesystem and hardware.

The integer-grounding counterexample is a concrete instance where the independent mathematical path exposed an executor defect. It does not prove that all correlated errors are excluded. Final raw-result aggregation should independently recompute claims without importing the producer's aggregation functions and retain its own source identity, while preserving this same-project limitation.
