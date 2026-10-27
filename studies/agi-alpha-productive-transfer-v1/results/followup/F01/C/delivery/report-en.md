# AGI ALPHA · Maintenance decision — call contract

**F01 · Flask startup banner across the Click 8.1.7 to 8.2.1 transition**

Scope: `show_server_banner`; click 8.1.7 → 8.2.1.

## Recommended action

**REVIEW_UNRESOLVED_SCOPE**

This review identifies calls to revise or test. It is not behavioral validation, a security assessment or deployment approval. Complete scope acceptance is audited separately.

## Evidence and limits

### `click.echo` · L724 · BINDING_PRESERVED

These two signatures require no argument change for `click.echo`. Confirm the imported target and test this consumer path under both versions; binding alone does not justify production approval.

[Consumer source](https://github.com/pallets/flask/blob/3205b53c7cf69d17fee49cac6b84978175b7dd73/src/flask/cli.py#L724) · SHA-256 `3c3c1909f3da822e465336fe0fa74437bcb6d205a25408377a3467c4128d1cf0`

```python
click.echo(f" * Serving Flask app '{app_import_path}'")
```

Retained qualification: Conditional on the declared target; runtime dispatch/import identity is unproved.

- before: [`echo`](https://github.com/pallets/click/blob/874ca2bc1c30d93a4ac6e36a15ed685eafe89097/src/click/utils.py) · SHA-256 `d78efa51db94358e9478f194e26d7cbb35472edd6c28cd8f3f7c96b1085b22d3`
- after: [`echo`](https://github.com/pallets/click/blob/fd183b2ced1cb5857784fe7fb22f4982f671f098/src/click/utils.py) · SHA-256 `6f5326faeb040c11ed13070f96d3c89f7cd22b89f0d8a4e9e460bbfe849394ba`

After signature: `message (POSITIONAL_OR_KEYWORD, optional), file (POSITIONAL_OR_KEYWORD, optional), nl (POSITIONAL_OR_KEYWORD, optional), err (POSITIONAL_OR_KEYWORD, optional), color (POSITIONAL_OR_KEYWORD, optional)`

### `click.echo` · L727 · BINDING_PRESERVED

These two signatures require no argument change for `click.echo`. Confirm the imported target and test this consumer path under both versions; binding alone does not justify production approval.

[Consumer source](https://github.com/pallets/flask/blob/3205b53c7cf69d17fee49cac6b84978175b7dd73/src/flask/cli.py#L727) · SHA-256 `3c3c1909f3da822e465336fe0fa74437bcb6d205a25408377a3467c4128d1cf0`

```python
click.echo(f" * Debug mode: {'on' if debug else 'off'}")
```

Retained qualification: Conditional on the declared target; runtime dispatch/import identity is unproved.

- before: [`echo`](https://github.com/pallets/click/blob/874ca2bc1c30d93a4ac6e36a15ed685eafe89097/src/click/utils.py) · SHA-256 `d78efa51db94358e9478f194e26d7cbb35472edd6c28cd8f3f7c96b1085b22d3`
- after: [`echo`](https://github.com/pallets/click/blob/fd183b2ced1cb5857784fe7fb22f4982f671f098/src/click/utils.py) · SHA-256 `6f5326faeb040c11ed13070f96d3c89f7cd22b89f0d8a4e9e460bbfe849394ba`

After signature: `message (POSITIONAL_OR_KEYWORD, optional), file (POSITIONAL_OR_KEYWORD, optional), nl (POSITIONAL_OR_KEYWORD, optional), err (POSITIONAL_OR_KEYWORD, optional), color (POSITIONAL_OR_KEYWORD, optional)`

## Complete cost not identified

Measured local resources are in the receipt. Inference, preparation, human review, integration and upkeep charges are not all available; complete cost remains unknown. Actual collections are zero.

[Captured input](raw-task.json) · [Decision record](decision-record.json) · [Call inventory](call-inventory.json) · [Cost record](costs.json) · [Execution result](result.json) · [Receipt](receipt.json)

Authority: HOLD; no operator authority; settlement disconnected. Recommendations require the maintainer’s decision.
