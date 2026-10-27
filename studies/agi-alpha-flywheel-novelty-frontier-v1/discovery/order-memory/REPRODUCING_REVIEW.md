# Reproducing the independent review

The original reviewer was run before packaging but contained an absolute scratch-directory path. Its exact source
bytes are preserved in `order_transfer_review.original.py.txt`. The portable `order_transfer_review.py` resolves its
data directory relative to its own location, adds explicit input/output arguments, and records its separate source
hash. Its decoding and comparison logic is unchanged. This replay is a portability check of the existing review,
not a new discovery experiment or a new hidden validation set.

## Run

From this directory, print the complete JSON report without writing a result file:

```sh
python3 order_transfer_review.py
```

From the study root, write a new report:

```sh
python3 discovery/order-memory/order_transfer_review.py \
  --output /tmp/order-memory-review-replay.json
```

To select another copy of the evidence explicitly:

```sh
python3 discovery/order-memory/order_transfer_review.py \
  --data-dir discovery/order-memory \
  --output /tmp/order-memory-review-second-replay.json
```

The default data directory is the script's parent directory, independent of the working directory. The `--output`
path is relative to the working directory unless absolute. Output is exclusive: an existing path is rejected, so
use a new filename for each saved replay. The default prints JSON to stdout and does not replace original evidence.
The script suppresses new Python bytecode files from its imported study module.

## Recorded replay

`adversarial_review_portable_replay.json` records a successful portable replay: all **198,840 saved cases** match the
independent codeword-intersection oracle, with **zero mismatches**; all **24,000 duplication-reference single-erasure
checks** pass. The saved two-error and mixed-error counterexamples are retained. The original source/configuration
and case-stream checks also pass. These results establish the scoped abstract implementation checks, not a physical
device, a novel coding theorem, learned transfer or AI superiority.

The original review report remains `adversarial_review_results.json`. Do not replace its recorded source hash with
the portable source hash: those hashes describe different files and executions.

| Artifact | SHA-256 |
|---|---|
| Exact original reviewer, now preserved as `.original.py.txt` | `e91ce5c41f7e6448955bea8c293752df76aec93eca81c0451fbe398fed045a65` |
| Portable reviewer | `3345c6471527c2a4964da97aee0ea344ab3449c866931ceabbfc6414f134d44a` |
| Unchanged original review report | `5645ff045f49063d8f0e2c1bc789b049ebece50b1713a3dac15001a9adf758d5` |

The new report uses `review_source_sha256` for the portable code and `original_review_source_sha256` for the
preserved original. It also records the original report hash and verifies that the original report is unchanged.
