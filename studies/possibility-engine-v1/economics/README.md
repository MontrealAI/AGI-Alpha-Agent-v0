# Experiment Construction Pack: enterprise model

This directory contains a reproducible hypothetical business model for the finite software experiment-construction offering.
All commercial behavior and money are simulated. Technical validation is owned by the separate construction/evaluation lane.

## Run

From this directory, using Python 3.11–3.13 and its standard library:

```sh
python arrangements.py
python model.py confirm --seed-file ../evidence/confirmation/seeds.json --output replay-confirmation
```

To repeat development, first copy the study and then run `python model.py develop --output replay-development` in that copy.
Development writes `selected_policy.json`; keeping it separate protects the released confirmation record.
The preserved reference journals and operating breakdown can be reproduced from the original confirmation output with:

```sh
python persist_confirmation_references.py
python report_confirmation.py
```

The seed bank above was issued by the independent checker after the study source freeze. Confirmation refuses a changed economic source/policy file and requires the bank to bind
either the study freeze or the economic freeze. It requires at least 128 unique fresh economic seeds.

The original price grid and results are preserved in archive-v1. A single bounded redesign added a lower price grid.
Final development has 24 entries and 20 unique price/deposit/capacity combinations, scored on 12 common development seeds.
The frozen attempted policy is in selected_policy.json. Stop-after-research retains every estimated research cost.

## Files

- model.py: game, account journal, complete lifecycle, development and fresh-confirmation runner.
- assumptions.json: explicit prices, labor, demand, behavioral parameters, uncertainty scenarios and staged-investment gate.
- PROTOCOL.md: offer scope, assumptions, game objectives/information, accounting rules, bounds and limitations.
- FREEZE.json: SHA-256 identities of the selected economic source, inputs and policy.
- development/: corrected policy search and complete witness.
- archive-v1/: original source/config and initial12-policy run.
- archive-v2-pre-free-delay/: intermediate development outputs before equal-delay free-baseline correction.
- FAILURES.md: retained errors, challenge findings and corrections.
- arrangements.py and arrangement_analysis.json: optional joint commissioning and bounded scale/pilot arithmetic.
- confirmation/: produced only after independently issued fresh seeds.
- FINDINGS.md: complete economic results, cost and cash interpretation, independent reconciliation and decision.
- persist_confirmation_references.py: saves the original conventional and no-launch calculations on the same frozen seeds.
- report_confirmation.py: derives operating metrics from hash-checked confirmation records.

The independent account checker and branch controls live in the study's verification directory. They reconstruct each
journal without importing the simulator. Controls force life-cycle branches solely to test them; they do not count as
buyer observations or demand worlds.

## Interpret the numbers

Full-project profit includes the complete estimated research campaign and exit. Operating contribution excludes the
one-time research/development block, finance and successor investment, while retaining acquisition, ongoing overhead,
verification, support, correction, collections and exit. Gross collections include deposits; net collections subtract
refunds. Restricted cash cannot fund research or salaries. Final obligations must be zero and final cash minus opening
equity must equal profit. Modeling all costs does not measure the actual historical cost of this chat session.

The ordinary same-AI conventional route uses identical economic assumptions and therefore ties by construction.
This is an explicit counterfactual, not evidence of measured operational parity. A distinct technical comparator is
evaluated elsewhere. No retained-capability premium is presumed.

## Commercial next evidence

A narrower research pilot would need a real user who has an admissible ambiguity problem, lawful access to both proposed
ports, value beyond free/current-AI substitutes, and an acceptance test covering their actual model and uncertainty.
Before a repeatable paid offer, measure extraction, validation, integration, corrections and support on externally
supplied tasks; obtain actual willingness-to-pay evidence with separately authorized outreach. Physical behavior remains
a separate experiment. No paid work, outreach, transfers, credentials or deployment are performed by this model.

