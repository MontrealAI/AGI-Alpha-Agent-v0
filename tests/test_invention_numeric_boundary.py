# SPDX-License-Identifier: Apache-2.0
"""Include source-token and deadline regressions in default release collection."""

from contrib.invention_automation.test_critic_loop import (
    test_generation_deadline_refuses_before_input_reads_and_output_creation as test_deadline_refusal,
)
from contrib.invention_automation.test_numeric_boundary import (
    test_complete_plain_decimal_and_unknown_unit_remain_supported as test_complete_decimal,
)
from contrib.invention_automation.test_numeric_boundary import (
    test_scientific_token_cannot_become_a_dimension_objection as test_unsupported_scientific_token,
)
