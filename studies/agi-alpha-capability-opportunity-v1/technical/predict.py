# SPDX-License-Identifier: Apache-2.0
"""Evaluate a delivered response model on supplied inputs without any simulator oracle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from learning import features


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    args = parser.parse_args()
    model = json.loads(args.model.read_text())
    inputs = np.asarray(json.loads(args.inputs.read_text()), dtype=float)
    predictions = features(inputs) @ np.asarray(model["coefficients"], dtype=float)
    print(json.dumps({"predictions": predictions.tolist(), "scope": "bounded synthetic response family"}))


if __name__ == "__main__":
    main()
