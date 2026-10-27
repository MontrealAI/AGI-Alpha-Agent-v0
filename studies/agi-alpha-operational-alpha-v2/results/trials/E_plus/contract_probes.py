# SPDX-License-Identifier: Apache-2.0
"""Small, domain-independent probes for observable stateful-service contracts.

The caller supplies a unittest-compatible assertion object, a side-effect-free
observer, and actions. Observations/results must support deepcopy and equality.
No service implementation, domain fixtures, or expected business rules live here.
"""
from copy import deepcopy


def assert_rejected_unchanged(case, observe, action, exception=ValueError):
    """Require a rejected action to preserve its complete observable state."""
    # Freeze the baseline even when the implementation's observer aliases state.
    before = deepcopy(observe())
    with case.assertRaises(exception):
        action()
    case.assertEqual(observe(), before, "rejected action changed observable state")


def assert_idempotent(case, observe, action):
    """Perform an action twice; the retry must preserve both result and state."""
    expected_result = deepcopy(action())
    after_first = deepcopy(observe())
    repeated_result = action()
    case.assertEqual(repeated_result, expected_result, "retry changed the result")
    case.assertEqual(observe(), after_first, "retry changed observable state")
    return repeated_result


def assert_independent_result(case, observe, action, mutate):
    """Mutate an action's returned object and require service-state isolation."""
    result = action()
    after_action = deepcopy(observe())
    mutate(result)
    case.assertEqual(observe(), after_action, "returned object aliases service state")
