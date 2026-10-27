# SPDX-License-Identifier: Apache-2.0
import copy, unittest
from graph_admission import bound_hash, inspect, make_simulated_record

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.a = make_simulated_record('S1', 0, 3, 12, [0, 1, 2, 3], True)
        dep = {'skill_id': 'S1', 'version': '1', 'evidence_sha256': self.a['evidence_sha256'], 'required_domains': [2, 3]}
        self.b = make_simulated_record('S2', 0, 8, 12, [2, 3, 4, 5], True, [dep])
        self.catalog = {'S1': self.a, 'S2': self.b}

    def test_valid_and_domain_expansion(self):
        self.assertTrue(inspect(self.a, 4, self.catalog, 1)['admitted'])
        self.assertTrue(inspect(self.b, 9, self.catalog, 2)['admitted'])
        self.assertTrue(inspect(self.b, 9, self.catalog, 5)['admitted'])

    def test_eligibility_and_authentication(self):
        for issuer in ('x.club.agi.eth', 'deep.x.agent.agi.eth', 'agent.agi.eth', 'x.agent.agi.eth.evil'):
            x = copy.deepcopy(self.a); x['attestation']['issuer'] = issuer
            self.assertFalse(inspect(x, 4, self.catalog)['admitted'])
        x = copy.deepcopy(self.a); x['attestation']['authenticated_simulated'] = False
        self.assertFalse(inspect(x, 4, self.catalog)['admitted'])

    def test_stale_future_revoked(self):
        for month in (2, 15, 16): self.assertFalse(inspect(self.a, month, self.catalog)['admitted'])
        x = copy.deepcopy(self.a); x['revoked'] = True
        self.assertFalse(inspect(x, 4, self.catalog)['admitted'])

    def test_binding_evidence_and_models(self):
        for field, value in [('evidence_sha256', '0' * 64), ('models', {'other': '1'}), ('scope_domains', [99])]:
            x = copy.deepcopy(self.a); x[field] = value
            self.assertFalse(inspect(x, 4, self.catalog)['admitted'])

    def test_missing_or_wrong_dependency(self):
        self.assertFalse(inspect(self.b, 9, {})['admitted'])
        x = copy.deepcopy(self.a); x['version'] = '2'
        self.assertFalse(inspect(self.b, 9, {'S1': x})['admitted'])

    def test_dependency_lifecycle(self):
        self.assertFalse(inspect(self.b, 16, self.catalog, 2)['admitted'])
        x = copy.deepcopy(self.a); x['revoked'] = True
        self.assertFalse(inspect(self.b, 9, {'S1': x}, 2)['admitted'])

    def test_cycle_rejected(self):
        x = copy.deepcopy(self.a)
        x['dependencies'] = [{'skill_id': 'S1', 'version': '1', 'evidence_sha256': x['evidence_sha256'], 'required_domains': [0]}]
        x['attestation']['bound_record_sha256'] = bound_hash(x)
        self.assertFalse(inspect(x, 4, {'S1': x}, 0)['admitted'])

    def test_failed_evaluation_and_authority(self):
        x = make_simulated_record('failed', 0, 3, 12, [0], False)
        self.assertFalse(inspect(x, 4, {})['admitted'])
        x = copy.deepcopy(self.a); x['execution_authority'] = ['settle']
        self.assertFalse(inspect(x, 4, {})['admitted'])

if __name__ == '__main__': unittest.main()
