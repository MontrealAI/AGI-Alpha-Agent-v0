# SPDX-License-Identifier: Apache-2.0
"""Independent mathematical and lifecycle checks for the PDE relay."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from technical import Diffusion, Reduced, ResidualGym, execute, orthogonal_append, reference_solve, sample


class TechnicalChecks(unittest.TestCase):
    def setUp(self):
        self.domain = Diffusion(9)
        self.spec = sample(301, 1, "transfer")[0]

    def test_stencil_matches_assembled_matrix(self):
        rng = np.random.default_rng(302)
        z = rng.normal(size=81)
        b = self.domain.source(self.spec)
        expected = np.linalg.norm(self.domain.matrix(self.spec) @ z - b) / np.linalg.norm(b)
        self.assertAlmostEqual(self.domain.check_residual(self.spec, z, b), expected, places=10)

    def test_operator_and_preconditioner_spd(self):
        matrix = self.domain.matrix(self.spec).toarray()
        self.assertLess(np.linalg.norm(matrix - matrix.T), 1e-10)
        self.assertGreater(np.linalg.eigvalsh(matrix)[0], 0)
        operator = self.domain.preconditioner(self.spec)
        inverse = np.column_stack([operator @ v for v in np.eye(81)])
        self.assertLess(np.linalg.norm(inverse - inverse.T), 1e-12)
        self.assertGreater(np.linalg.eigvalsh(inverse)[0], 0)

    def test_all_solvers_meet_independent_acceptance(self):
        ref, ref_s = reference_solve(self.domain, self.spec)
        basis = orthogonal_append(np.empty((81, 0)), ref)
        model = Reduced(self.domain, basis)
        for method in ["direct", "ilu_gmres", "spectral_pcg", "v1", "improved_generalist"]:
            row, _ = execute(self.domain, self.spec, method, model if method == "v1" else None, ref, ref_s)
            self.assertTrue(row["accepted"], method)
            self.assertGreaterEqual(row["complete_s"], row["solve_s"] + row["setup_s"])

    def test_discrete_error_bound_covers_arbitrary_approximation(self):
        ref, _ = reference_solve(self.domain, self.spec)
        z = ref + np.random.default_rng(303).normal(size=81) * 0.001
        rhs = self.domain.source(self.spec)
        rr = self.domain.check_residual(self.spec, z, rhs)
        kx, ky, _, reaction = self.spec["theta"]
        alpha = (kx + ky) * self.domain.eigen[0] + reaction * self.domain.reaction.min()
        self.assertLessEqual(np.linalg.norm(ref - z), rr * np.linalg.norm(rhs) / alpha)

    def test_gym_changes_artifact_and_enforces_action_budget(self):
        initial, _ = reference_solve(self.domain, self.spec)
        basis = orthogonal_append(np.empty((81, 0)), initial)
        gym = ResidualGym(self.domain, basis, sample(304, 3, "transfer"), budget=2)
        self.assertEqual(gym.observe()["remaining_actions"], 2)
        gym.step({"kind": "solve_and_enrich", "index": 0})
        with self.assertRaises(ValueError):
            gym.step({"kind": "solve_and_enrich", "index": 0})
        with self.assertRaises(ValueError):
            gym.step({"kind": "read_confirmation_answer", "index": 1})
        gym.step({"kind": "solve_and_enrich", "index": 1})
        self.assertTrue(gym.observe()["terminated"])
        with self.assertRaises(ValueError):
            gym.step({"kind": "solve_and_enrich", "index": 2})
        self.assertEqual(gym.basis.shape[1], 3)
        self.assertLess(np.linalg.norm(gym.basis.T @ gym.basis - np.eye(3)), 1e-12)
        self.assertTrue(np.array_equal(basis[:, 0], gym.initial[:, 0]))

    def test_identity_freeze_and_seed_generation(self):
        import technical

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "basis.npy"
            np.save(path, np.eye(3))
            before = technical.digest(path)
            np.save(path, np.eye(3) * 2)
            self.assertNotEqual(before, technical.digest(path))
        self.assertEqual(sample(305, 3, "transfer"), sample(305, 3, "transfer"))
        self.assertNotEqual(sample(305, 3, "transfer"), sample(306, 3, "transfer"))


if __name__ == "__main__":
    unittest.main()
