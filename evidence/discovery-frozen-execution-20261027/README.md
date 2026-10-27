[Project notice](../../docs/DISCLAIMER_SNIPPET.md)

# Frozen execution must have an execution receipt

This additive correction continues discovery/construction owner #4972 at
`03b2eb97f1e150956ef0fa028e1ad665cc755cf6` and configured finding `4391406262`.
Its parent remains the existing executor, enterprise, protected library, Gym,
Journal, checkpoints and A/B/C ledger. It allocates no release or publisher.

## Defect and correction

A planned experiment could pin `execution_request_digest` while its observation
omitted `execution_operation`. That bypassed the existing frozen-input, terminal
receipt, artifact, permit-bucket and elapsed-time checks. Arbitrary current evidence
and unrelated accounting could advance the experiment.

The corrected boundary refuses that observation before recording it. Twelve
regressions cover omitted/null receipts, all three interpretations and known/unknown
costs. Each verifies an unchanged journal, checkpoint, bundle and ledger, absent
operation/observation/allocation records, then accepts the corrected observation
with the actual independently checked execution. Refusal does not replay work or
consume the observation's identity. Existing receipt-free research steps remain
supported when the plan does not pin an execution request.

## Reproduce

From the source checkout with the existing development dependencies:

```sh
python scripts/check_python_deps.py
python check_env.py --auto-install
python -m pytest tests/runtime/test_flywheel_discovery.py -q --no-cov
PYTHONPATH=. python scripts/record_discovery_flywheel.py --output /private/new-discovery-replay.json
python -m mypy --config-file mypy-runtime.ini
```

Choose a new output path; the recorder refuses replacement. The raw packet's
`sources` map binds all 89 runtime, recorder, foundation and test sources. Hash
these actual files before treating its evidence as applicable to another checkout.
The packet and `QUALIFICATION.json` report scopes separately. The public page is
unchanged and deterministically rebuilds to the original SHA-256
`d7338a1b8a8165f20723fb3711fe6e469b75f67a354201718c0233ac3220acaa`.

## Connected result and its limit

`discovery-replay.json` executes the existing source-backed workflow-inheritance
candidate and the preserved internal placement/Gym/peer regressions. The candidate
constructs an actual report/checking artifact and runs 76 tool-environment episodes.
All four comparison arms accept five cases, reject three bad outputs and refuse
eleven requests before actions. Identity reuse and the identical-content ordinary
library tie. The cheaper schema-plus-complete-output control stays visible.

The candidate's unknown complete C cost pauses its bundle. The unpriced offering
stays a hypothesis; the uncommitted arrangement stays held. Admission is rejected
and the next decision is stop. Actual model calls and customer collections are
zero; complete monetary cost and profit remain unknown. Measured CPU/wall resources
in `replay-resources.json` are not converted into invented monetary charges.
The positive peer episode uses fictional ENS/account/billing attestations and real
local cryptography/computation. It establishes no live identity, sale or net Alpha.

This continues the mechanisms in the preserved foundation sources: original purpose
is fixed; a construction requires an executable realization and falsifier; projected
arrangements are separate from actual acceptance and receipts; successors inherit
structure while current proof and authority remain separate. No new invention or
commercial feasibility claim follows from the custody correction.

## Source, publication and rollback

Only the runtime guard, directed regressions, operating clarification and this new
evidence directory change. Original papers, packets, worker fixtures, generated UI,
contracts, settlement and owner branches remain intact. The final repository-wide
and installed/public release campaign remains with the existing integration owner
after #4960/#4961/#4963/#4972 and the #4973 exact-paper lane are reconciled.

The local hook's first default comparison used newer main and correctly refused
the parent's older paper catalog. The final scoped hook uses the actual PR target
`03b2eb97` via the guard's supported GitHub-event base input; no rule is changed.
This is focused child qualification and does not qualify a main integration.

`development/` preserves the original red tests, initial hook failure, overly narrow
typing invocation and the pre-format replay whose source map no longer matches the
formatted test file. None is relabeled as final-source acceptance. The failed first
timing launcher did not execute the recorder; its log is retained too.

Rollback is a normal reviewed revert of this correction. Preserve journals and
checkpoints; do not reset them or reuse consumed authority. Earlier source requires
its own qualification and still contains the original receipt omission defect.

## Official model check, 2026-10-27

The existing model names were checked against the official
[Astra profile](https://developers.openai.com/api/docs/models/gpt-6-astra),
[Terra profile](https://developers.openai.com/api/docs/models/gpt-6.1-terra) and
[API pricing](https://developers.openai.com/api/docs/pricing).

| Model | Standard input / cached input / output, USD per million tokens | Reasoning efforts |
|---|---|---|
| `gpt-6-astra` | 10 / 1 / 50 | low, medium, high, xhigh, max |
| `gpt-6.1-terra` | 1 / 0.05 / 5 | none, low, medium, high, xhigh, max |

These short-context standard rates are public references, not verified account
tariffs or prices for this run. Long context, caching writes, tools, service mode
and region can change liability. Terra tool calls require Responses; both profiles
list computer-use support. Account quota, billing, access and deployment-specific
limits were not provisioned or tested. The replay retains its actual scripted-model
identifier. No production model default or paid resource is changed.

## Français

Une étape qui fige une mission doit référencer son reçu réel, même si l'observation
est négative ou incertaine. Le refus ne modifie ni le journal, ni les coûts, ni le
point de reprise. Une observation corrigée peut utiliser le reçu vérifié sans
réexécuter l'action. Les études sans mission figée restent possibles. Les résultats
locaux ne démontrent aucun revenu, profit complet ou accès ENS réel.
