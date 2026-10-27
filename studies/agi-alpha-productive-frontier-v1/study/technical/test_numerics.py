# SPDX-License-Identifier: Apache-2.0
import gzip
import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from lyapunov_study import (
    ROOT,
    system,
    parameters,
    exact,
    project,
    certificate,
    load_basis,
    validate_basis,
    validate_system,
    digest,
)


class NumericalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.basispath = ROOT / "results/gym_pod48.npy"
        self.sha = digest(self.basispath)
        self.V = load_basis(self.basispath, self.sha)
        self.A, self.B, self.alpha = system(parameters(8401, 1)[0])

    def test_dissipativity_claim_is_checked(self):
        with self.assertRaises(ValueError):
            validate_system(self.A, self.B, self.alpha + 1)
        with self.assertRaises(ValueError):
            validate_system(-self.A, self.B, 0.1)
        with self.assertRaises(ValueError):
            validate_system(self.A, self.B, 0)

    def test_bad_shapes_and_nonfinite_refused(self):
        with self.assertRaises(ValueError):
            validate_system(np.ones((3, 4)), np.ones((3, 1)), 1)
        B = self.B.copy()
        B[0, 0] = np.nan
        with self.assertRaises(ValueError):
            validate_system(self.A, B, self.alpha)
        with self.assertRaises(ValueError):
            validate_basis(self.V[:10], 192)
        V = self.V.copy()
        V[:, 0] *= 2
        with self.assertRaises(ValueError):
            validate_basis(V, 192)

    def test_artifact_hash_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corrupt.npy"
            data = bytearray(self.basispath.read_bytes())
            data[-1] ^= 1
            p.write_bytes(data)
            with self.assertRaises(ValueError):
                load_basis(p, self.sha)

    def test_actual_errors_obey_independent_bounds(self):
        for p in parameters(8401, 8):
            A, B, alpha = system(p)
            X = project(A, B, self.V)
            truth = exact(A, B)
            c = certificate(A, B, X, alpha)
            residual = A @ X + X @ A.T + B @ B.T
            error_bound = np.linalg.norm(residual, "fro") / (2 * alpha)
            self.assertLessEqual(np.linalg.norm(truth - X, "fro"), error_bound + 1e-12)
            self.assertLessEqual(abs(np.trace(truth - X)), np.sqrt(len(A)) * error_bound + 1e-12)
            self.assertLessEqual(
                np.linalg.norm(truth - X, "fro") / np.linalg.norm(truth, "fro"), c["relative_fro_certificate"] + 1e-12
            )
            self.assertLessEqual(c["relative_fro_certificate"], c["relative_trace_certificate"] + 1e-12)

    def test_independent_recipient_uses_same_artifact(self):
        ps = parameters(9401, 4)
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "recipient.py"),
                "--artifact",
                str(self.basispath),
                "--sha256",
                self.sha,
                "--parameters",
                json.dumps(ps.tolist()),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        self.assertFalse(data["training_data_loaded"])
        for p, reported in zip(ps, data["outputs"]):
            A, B, alpha = system(p)
            expected = certificate(A, B, project(A, B, self.V), alpha)
            self.assertAlmostEqual(reported["trace"], expected["trace"], places=11)

    def test_archived_source_hash_matches_initial_freeze(self):
        freeze = json.loads((ROOT / "results/preconfirmation_freeze.json").read_text())
        raw = gzip.decompress((ROOT / "archived_initial/lyapunov_study.py.gz").read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), freeze["implementation_sha256"])
        self.assertEqual(digest(ROOT / "archived_initial/protocol.json"), freeze["protocol_sha256"])


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        unittest.main()
