[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Demo Utilities

This directory holds helper utilities shared across demos, such as `disclaimer.py` which exposes the standard project disclaimer.
Use these helpers to keep demo scripts consistent and to avoid duplicating boilerplate.

## Example usage

```python
from alpha_factory_v1.demos.utils.disclaimer import DISCLAIMER

print(DISCLAIMER)
```

Update this README whenever new shared utilities are added.
