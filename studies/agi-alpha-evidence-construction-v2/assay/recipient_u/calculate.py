# SPDX-License-Identifier: Apache-2.0
"""Reconstruct requested contrasts from published rounded table summaries."""
import json
from math import sqrt
from scipy.stats import t

n_retrieval = n_restudy = 30
mean_retrieval, sd_retrieval = 0.83, 0.10
mean_restudy, sd_restudy = 0.61, 0.21
v_retrieval = sd_retrieval ** 2 / n_retrieval
v_restudy = sd_restudy ** 2 / n_restudy
difference_a = mean_retrieval - mean_restudy
se_a = sqrt(v_retrieval + v_restudy)
df_a = (v_retrieval + v_restudy) ** 2 / (
    v_retrieval ** 2 / (n_retrieval - 1) + v_restudy ** 2 / (n_restudy - 1)
)
critical_a = t.ppf(0.975, df_a)
ci_a = [difference_a - critical_a * se_a, difference_a + critical_a * se_a]
short_effect, long_effect = 0.115, 0.122
short_se = long_se = 0.04
result = {
    "A": {"difference_proportion": difference_a, "SE_proportion": se_a,
          "Welch_df": df_a, "critical_t": critical_a,
          "CI95_proportion": ci_a,
          "difference_percentage_points": difference_a * 100,
          "CI95_percentage_points": [x * 100 for x in ci_a]},
    "B": {"long_minus_short_standardized_effect": long_effect - short_effect,
          "short_SE": short_se, "long_SE": long_se,
          "variance_difference": "0.04**2 + 0.04**2 - 2*covariance(long, short)",
          "covariance": "unidentified from supplied summaries",
          "CI95": "hold: joint covariance / linked joint analysis required"}
}
print(json.dumps(result, indent=2))
