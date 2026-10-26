import unittest

from build_calibration import index_records


def fixtures():
    return [{'chain': f'SYNTHETIC-{i:02}', 'family': family, 'arm': arm, 'cohort': 'primary',
             'accepted': False, 'cpu_seconds': 1.0, 'elapsed_seconds': 1.1, 'child_cpu_complete': True,
             'node_count': [100, 625, 1600, 2500][i % 4]}
            for i in range(12) for family in ['forward', 'inverse', 'design'] for arm in 'ABCD']


class CalibrationControls(unittest.TestCase):
    def test_all_failed_cases_remain_in_complete_cohort(self):
        chains, rows = index_records(fixtures())
        self.assertEqual(len(chains), 12)
        self.assertEqual(len(rows), 144)
        self.assertFalse(any(row['accepted'] for row in rows.values()))

    def test_partial_or_duplicate_rows_are_refused(self):
        rows = fixtures()
        with self.assertRaises(ValueError):
            index_records(rows[:-1])
        rows[-1] = rows[0].copy()
        with self.assertRaises(ValueError):
            index_records(rows)

    def test_unmeasured_terminated_child_cpu_cannot_be_certified(self):
        rows = fixtures()
        rows[0]['child_cpu_complete'] = False
        rows[0]['exit_code'] = 124
        with self.assertRaisesRegex(ValueError, 'COMPLETE_CPU_UNKNOWN'):
            index_records(rows)

    def test_explicitly_blocked_stage_stays_failed_and_has_no_execution_charge(self):
        rows = fixtures()
        rows[0].update(not_executed=True, cpu_seconds=0.0, elapsed_seconds=0.0,
                       child_cpu_complete=False, blocked='UPSTREAM_INVERSE_NOT_ACCEPTED')
        _, indexed = index_records(rows)
        self.assertTrue(indexed[rows[0]['chain'], rows[0]['family'], rows[0]['arm']]['not_executed'])
        rows[0]['accepted'] = True
        with self.assertRaises(ValueError):
            index_records(rows)

    def test_chain_strata_cannot_be_reassigned_by_arm(self):
        rows = fixtures()
        rows[0]['node_count'] = 625
        with self.assertRaisesRegex(ValueError, 'CONNECTED_CHAIN_SIZE_STRATUM_DRIFT'):
            index_records(rows)


if __name__ == '__main__':
    unittest.main()
