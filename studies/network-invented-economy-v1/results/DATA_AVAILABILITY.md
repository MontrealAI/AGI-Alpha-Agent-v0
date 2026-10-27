# Data availability and reconstruction

Every event in this directory is simulated unless a record explicitly identifies an
actual local software check. There are no customer receipts or live frontier task
measurements in the dataset.

The source contribution includes the protocol, selected policies, aggregate results,
audit receipts, recipient comparison and illustrative trace. The separately delivered
**AGI_Alpha_Flywheel_Evidence.zip** contains the complete raw streams, sample histories,
all 768 confirmation ledgers, development history and data provenance. Extract it into
the study directory so that its `results/` and `evidence/` paths merge with the source.

The complete confirmation ledger stream has 81,763,432 compressed bytes and SHA-256:

`3268bfc29949e0f63f754f720835db1cf9ba656ade6d010d72498d837173fccf`

Its path is `results/confirmation_ledgers.jsonl.gz`. The source audit records hashes
of the other inputs. Gzip containers can have different timestamp metadata after a
replay; compare their parsed records or uncompressed streams when checking semantic
reproducibility. Runtime timings and publication-file timestamps are not scientific
outputs.

The raw output is also reproducible without provider or financial access:

```sh
python3 -m src.run_study all --out results/replay --workers 4
```

The saved 20-file freeze is verified before each phase. A new replay records its own
freeze timestamp while using the declared scientific seed schedule. To reproduce the
original published protocol identity, preserve `results/protocol_freeze.json` and
use a distinct directory containing an exact copy rather than overwriting it.

The original v1 amendment and v2 storage interruption remain in the evidence archive.
They are development/provenance records, not additional confirmation. Supplied source
manuscripts are cited and hashed but are not redistributed.
