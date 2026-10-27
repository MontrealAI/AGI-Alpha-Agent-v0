# Reproduce confirmation

Run commands from the study directory. The numerical runtime recorded for the first run was Python 3.12.14, NumPy 2.3.2 and SciPy 1.17.0. The optional compressed-chunk decoder was Numcodecs 0.16.3. Source, task and data hashes are verified by the runner before outcomes are calculated.

```bash
python -m pip install numpy==2.3.2 scipy==1.17.0 numcodecs==0.16.3
python run_confirmation.py --output confirmation/results/reproduction-01
```

The output directory must be new. The runner will refuse to overwrite the primary evidence. It requires the already recovered artifact at `integration/results/frozen-v1/received-artifact.py`, whose SHA-256 must match the frozen source. This does not contact a live identity network.

The delivered `.npy` source exports are sufficient for this run. To reconstruct exports from the preserved public compressed chunks, use:

```bash
python data/curate_idr.py holdout --offline
```

This writes the same two NumPy exports and a separate offline replay manifest. The original download manifest remains intact. Online retrieval without `--offline` is optional and depends on continued public hosting; it is not required for reproduction. Source URLs and rights are recorded in the data manifests and curation notes.

To audit existing numerical outputs without rerunning the instrument:

```bash
python audit_confirmation.py
```

The audit checks the same declared thresholds with explicit finite-value and duplicate-identity guards. It also verifies rejection of injected NaNs. The initially used comparator and runner are preserved in `results/frozen-v1/evaluator-source/`; the stricter audit report is `results/frozen-v1/strict-output-audit.json`. Acceptance did not change.

Primary evidence starts at `results/frozen-v1/summary.json`. Each compatible task directory contains its contract, coordinate reference, conventional analytical answer, recovered-recipient answer, ordinary-library answer and execution receipts. Semantic cases have their exact invalid contract and refusal. Some invalid fixtures deliberately contain nonstandard JSON NaN or Infinity tokens to exercise parser/semantic rejection; these are not valid data contracts to imitate.

Read `RESULTS.md` for scope, comparisons and timing interpretation. Read `data/confirmation/CURATION_NOTES.md` for public-source attribution and the difference between source physical measure and mapped geometric measure.
