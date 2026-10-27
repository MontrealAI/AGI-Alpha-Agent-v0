# AGI ALPHA · Maintenance decision — call contract

**F04 · Hugging Face Hub default HTTP client factories across the HTTPX transition**

Scope: `default_client_factory, default_async_client_factory`; httpx 0.27.2 → 0.28.1.

## Recommended action

**REVIEW_UNRESOLVED_SCOPE**

This review identifies calls to revise or test. It is not behavioral validation, a security assessment or deployment approval. Complete scope acceptance is audited separately.

## Evidence and limits

### `httpx.Client` · L130 · UNRESOLVED

Hold the decision for `httpx.Client`. Identify the actual target and expanded or bound arguments, then run an isolated test of this consumer path under both versions, recording values, types and exceptions. The reason below identifies the missing evidence.

[Consumer source](https://github.com/huggingface/huggingface_hub/blob/cd57d24e013c66181e742f5e3b6c2fe464ee47cd/src/huggingface_hub/utils/_http.py#L130) · SHA-256 `65c6a3636cd65047e8ba6ca14a1a95ddf2943f9a6702b6b7d39034b382d3e291`

```python
httpx.Client(
        event_hooks={"request": [hf_request_event_hook]},
        follow_redirects=True,
        timeout=httpx.Timeout(constants.DEFAULT_REQUEST_TIMEOUT, write=60.0),
    )
```

Retained qualification: constructor or descriptor receiver dispatch requires runtime verification

- before: [`Client.__init__`](https://github.com/encode/httpx/blob/609df7ecc0f7cb10a1c998aa9c269bba77337c5f/httpx/_client.py) · SHA-256 `c4abf7e3485c2df38f0a78a57b1121da0360e41ac442a212eff3b4641f67c56c`
- after: [`Client.__init__`](https://github.com/encode/httpx/blob/26d48e0634e6ee9cdc0533996db289ce4b430177/httpx/_client.py) · SHA-256 `c43f941baefe58c91e96d00039e1868fe719d91453026d7db1647194563bff8d`

### `httpx.Timeout` · L133 · UNRESOLVED

Hold the decision for `httpx.Timeout`. Identify the actual target and expanded or bound arguments, then run an isolated test of this consumer path under both versions, recording values, types and exceptions. The reason below identifies the missing evidence.

[Consumer source](https://github.com/huggingface/huggingface_hub/blob/cd57d24e013c66181e742f5e3b6c2fe464ee47cd/src/huggingface_hub/utils/_http.py#L133) · SHA-256 `65c6a3636cd65047e8ba6ca14a1a95ddf2943f9a6702b6b7d39034b382d3e291`

```python
httpx.Timeout(constants.DEFAULT_REQUEST_TIMEOUT, write=60.0)
```

Retained qualification: constructor or descriptor receiver dispatch requires runtime verification

- before: [`Timeout.__init__`](https://github.com/encode/httpx/blob/609df7ecc0f7cb10a1c998aa9c269bba77337c5f/httpx/_config.py) · SHA-256 `0496434a9de7460ed71cf86f3f6bf3ecafc0f67e2d79fa904b817e52614bc970`
- after: [`Timeout.__init__`](https://github.com/encode/httpx/blob/26d48e0634e6ee9cdc0533996db289ce4b430177/httpx/_config.py) · SHA-256 `a4fa7653ec2271f70ab05f8a6111352d876dddee84446788a1767c1a3a372d67`

### `httpx.AsyncClient` · L141 · UNRESOLVED

Hold the decision for `httpx.AsyncClient`. Identify the actual target and expanded or bound arguments, then run an isolated test of this consumer path under both versions, recording values, types and exceptions. The reason below identifies the missing evidence.

[Consumer source](https://github.com/huggingface/huggingface_hub/blob/cd57d24e013c66181e742f5e3b6c2fe464ee47cd/src/huggingface_hub/utils/_http.py#L141) · SHA-256 `65c6a3636cd65047e8ba6ca14a1a95ddf2943f9a6702b6b7d39034b382d3e291`

```python
httpx.AsyncClient(
        event_hooks={"request": [async_hf_request_event_hook], "response": [async_hf_response_event_hook]},
        follow_redirects=True,
        timeout=httpx.Timeout(constants.DEFAULT_REQUEST_TIMEOUT, write=60.0),
    )
```

Retained qualification: constructor or descriptor receiver dispatch requires runtime verification

- before: [`AsyncClient.__init__`](https://github.com/encode/httpx/blob/609df7ecc0f7cb10a1c998aa9c269bba77337c5f/httpx/_client.py) · SHA-256 `c4abf7e3485c2df38f0a78a57b1121da0360e41ac442a212eff3b4641f67c56c`
- after: [`AsyncClient.__init__`](https://github.com/encode/httpx/blob/26d48e0634e6ee9cdc0533996db289ce4b430177/httpx/_client.py) · SHA-256 `c43f941baefe58c91e96d00039e1868fe719d91453026d7db1647194563bff8d`

### `httpx.Timeout` · L144 · UNRESOLVED

Hold the decision for `httpx.Timeout`. Identify the actual target and expanded or bound arguments, then run an isolated test of this consumer path under both versions, recording values, types and exceptions. The reason below identifies the missing evidence.

[Consumer source](https://github.com/huggingface/huggingface_hub/blob/cd57d24e013c66181e742f5e3b6c2fe464ee47cd/src/huggingface_hub/utils/_http.py#L144) · SHA-256 `65c6a3636cd65047e8ba6ca14a1a95ddf2943f9a6702b6b7d39034b382d3e291`

```python
httpx.Timeout(constants.DEFAULT_REQUEST_TIMEOUT, write=60.0)
```

Retained qualification: constructor or descriptor receiver dispatch requires runtime verification

- before: [`Timeout.__init__`](https://github.com/encode/httpx/blob/609df7ecc0f7cb10a1c998aa9c269bba77337c5f/httpx/_config.py) · SHA-256 `0496434a9de7460ed71cf86f3f6bf3ecafc0f67e2d79fa904b817e52614bc970`
- after: [`Timeout.__init__`](https://github.com/encode/httpx/blob/26d48e0634e6ee9cdc0533996db289ce4b430177/httpx/_config.py) · SHA-256 `a4fa7653ec2271f70ab05f8a6111352d876dddee84446788a1767c1a3a372d67`

## Complete cost not identified

Measured local resources are in the receipt. Inference, preparation, human review, integration and upkeep charges are not all available; complete cost remains unknown. Actual collections are zero.

[Captured input](raw-task.json) · [Decision record](decision-record.json) · [Call inventory](call-inventory.json) · [Cost record](costs.json) · [Execution result](result.json) · [Receipt](receipt.json)

Authority: HOLD; no operator authority; settlement disconnected. Recommendations require the maintainer’s decision.
