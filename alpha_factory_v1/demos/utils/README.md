[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

<!-- CURRENT-DEMO:START -->
## Current runnable path — 1.4.0

**Mode:** Library. Shared notices and isolated demo code evaluation helpers.

**Prerequisites:** Python 3.11–3.13.

From the repository root after [installation](../README.md#start-locally):

```bash
python -m alpha_factory_v1.demos show utils
```

**Expected result:** Import utilities as documented; this is not an independent agent.

**Scope:** Supporting code, not a runnable business demo.

The [catalog](../README.md) explains installation, stopping, backups and recovery.
Browser charts for legacy demos are labeled sample replays. Original research
narratives and advanced scripts below are preserved; they do not expand the tested
scope stated here.
<!-- CURRENT-DEMO:END -->

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Demo Utilities


This directory holds helper utilities shared across demos, such as `disclaimer.py` which exposes the standard project disclaimer.
Use these helpers when writing demo scripts so the safety notice stays consistent.

## Example

```python
from alpha_factory_v1.demos.utils.disclaimer import print_disclaimer

print_disclaimer()
```
