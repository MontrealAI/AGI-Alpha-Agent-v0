# Independent reference and confirmation

`reference.py` is an independent conventional exact planner and checker. Its author received only the frozen mission schema, did not inspect the retained compiler or development outputs, and implements probability arithmetic with rational numbers before output conversion. It enumerates every action independently at every reachable branch. Sensor probabilities and physical action consequences are supplied assumptions; no orbital simulation or physical calibration is claimed.

`generate_confirmation.py` builds 48 fresh synthetic cases across six declared categories: common information, zero/negative information value, adverse information, heterogeneous deadlines, sensor prerequisite refusal, and buyer withdrawal. The generator validates input structure only. The first generated commitment is recorded before compiling these inputs with the retained artifact. Its cases and answers remain outside the retained artifact. After the source freeze, the same generator becomes a reproducibility component; secrecy is a temporal evaluation control, not a claim that published tests remain secret forever.

## Commands

Generate the fixed cohort:

```bash
python evaluation/generate_confirmation.py --output-dir evaluation/protected/cases
```

Run the independent planner:

```bash
python evaluation/reference.py --mission INPUT.json --output REFERENCE.json
```

Check a submitted result against the independently computed reference:

```bash
python evaluation/reference.py --mission INPUT.json --candidate RESULT.json --output CHECK.json
```

The checker exits 0 for conformity, 1 for a discrepancy, and 2 for malformed input or file/JSON errors. Additional provenance/reason fields are allowed. It binds the exact mission file bytes, compares original risk limits through recomputed branch decisions, checks timeout aggregation, tests cheapest-action parity, checks all baseline/contingent totals and verifies that no execution authority is claimed.

Correct refusal is reported separately from accepted contingent delivery. A corpus full of correct refusals would not count as successful delivery. Cases with zero-probability branches retain those branches with null posterior/action/risk/cost/valid and `reachable:false`.

## Acceptance and falsifiers

Every reachable branch must meet the original operator-specific risk bound and action availability. Each buyer's timeout is a single aggregate of its late outcomes and null-result outcomes. It must use the same fallback declared before observation. Expected risk cannot replace the per-branch rule. A numerical tolerance of 1e-12 applies at specified equality boundaries. Mandatory timeout actions that become unsafe after conditioning are refused even when their prior risk was below the limit.

Unusable observations, uncleared rights and mismatched calibration scope must refuse observation while retaining separately valid baseline information. A shared observation can have negative value. The same-formulation conventional planner receives identical inputs, rights and arrangement permissions; parity is an intended control, not a failure to conceal.

The technical new-capability claim is falsified if the executable artifact is not portable, drops original obligations, relies on hidden answer material, or fails to reproduce competent exact results. A new-algorithm or numerical superiority claim is unsupported if the conventional planner ties. Commercial feasibility requires a separate complete accounting and participation assessment; technical acceptance does not imply a purchase, spacecraft safety, live authentication or payment.
