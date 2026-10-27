# SPDX-License-Identifier: Apache-2.0
import argparse, json
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from lyapunov_study import system, project, certificate, load_basis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--parameters", required=True)
    args = ap.parse_args()
    V = load_basis(Path(args.artifact), args.sha256)
    results = []
    with threadpool_limits(limits=1):
        for p in json.loads(args.parameters):
            A, B, alpha = system(p)
            X = project(A, B, V)
            c = certificate(A, B, X, alpha)
            results.append(c)
    print(
        json.dumps(
            {
                "artifact_sha256": args.sha256,
                "recipient_process": True,
                "training_data_loaded": False,
                "outputs": results,
            },
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
