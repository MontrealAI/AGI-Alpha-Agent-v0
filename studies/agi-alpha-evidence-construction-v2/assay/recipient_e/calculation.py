# SPDX-License-Identifier: Apache-2.0
"""Reconstruct only the specified printed-summary contrasts."""
from decimal import Decimal
from math import sqrt, isclose
from scipy.stats import t
import json

n_r = n_s = 30
mean_r, mean_s = 0.83, 0.61
sd_r, sd_s = 0.10, 0.21
v_r, v_s = sd_r ** 2 / n_r, sd_s ** 2 / n_s
se_a = sqrt(v_r + v_s)
df_a = (v_r + v_s) ** 2 / (v_r ** 2 / (n_r - 1) + v_s ** 2 / (n_s - 1))
delta_a = mean_r - mean_s
critical = float(t.ppf(0.975, df_a))
ci_a = [delta_a - critical * se_a, delta_a + critical * se_a]
# Independent exact-decimal checks of arithmetic inputs.
assert isclose(delta_a, float(Decimal('0.83') - Decimal('0.61')))
variance_decimal = Decimal('0.10') ** 2 / Decimal(30) + Decimal('0.21') ** 2 / Decimal(30)
assert isclose(se_a ** 2, float(variance_decimal))
delta_b = float(Decimal('0.122') - Decimal('0.115'))
result = {
    'A': {'difference_proportion': delta_a, 'SE_proportion': se_a,
          'Welch_df': df_a, 't_critical': critical, 'approx_95_CI_proportion': ci_a,
          'difference_percentage_points': 100 * delta_a,
          'approx_95_CI_percentage_points': [100*x for x in ci_a]},
    'B': {'descriptive_difference_standardized_units': delta_b,
          'SE_long': 0.04, 'SE_short': 0.04,
          'variance_formula': 'SE_long**2 + SE_short**2 - 2*Cov(long,short)',
          'CI': None, 'hold_reason': 'Joint covariance and exact sample overlap are not supplied'},
}
if __name__ == '__main__':
    print(json.dumps(result, indent=2))
