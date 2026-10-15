[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

<!-- CURRENT-DEMO:START -->
## Current runnable path — 1.31.3

**Mode:** Bounded local optimization. Computes an exact dependency-aware plan from supplied assumptions.

**Prerequisites:** Python standard library.

After [installation](../README.md#start-locally):

```bash
python -m alpha_factory_v1.demos check alpha_super_planner_v1
python -m alpha_factory_v1.demos run alpha_super_planner_v1
```

The catalog command uses bundled inputs and explicit offline defaults.

**Expected result:** JSON selecting collect, compare and review: cost 7, effort 7, assumed value 15.

**Scope:** Optimizes at most 16 supplied tasks; does not execute tasks or establish real savings.

The [catalog](../README.md) explains installation, stopping, backups and recovery.
Browser charts for legacy demos are labeled sample replays. Original research
narratives and advanced scripts below are preserved; they do not expand the tested
scope stated here.
<!-- CURRENT-DEMO:END -->

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Alpha Super Planner V1 👁️✨

An exact dependency-aware planner over supplied integer assumptions.

To launch the demonstration:

```bash
python -m alpha_factory_v1.demos.alpha_super_planner_v1
```

## Supply your own task

Pass `--input path/to/plan.json` to the module command. See
[the input fixture](fixtures/supplier-plan.json) and
[expected result](fixtures/supplier-result.json). Inputs are bounded to 64 KiB.
Cost, effort and value must be integers from 0 to 1,000,000; risk from 0 to 100.
Risk is a per-task threshold, not an aggregate probability. Unique lowercase IDs
and acyclic dependencies are required. Unknown fields and duplicate JSON keys
are rejected. Goal and labels must be nonempty trimmed strings.

All feasible subsets are examined. The objective maximizes supplied value, then
minimizes cost, effort and lexicographic sorted task IDs. Steps use the smallest
available ID at each topological step. Empty selection is valid. Save input
and stdout to reproduce a plan. Interruption has no external side effects;
rerun the same input. No output file is overwritten automatically. Units must
be consistent; value and risk remain assumptions, not measured benefits.
Selecting a task does not authorize its execution.
