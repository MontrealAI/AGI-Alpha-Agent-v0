# Reproduce the Software Capability Foundry

This is an independent research companion, not a production scheduler. It preserves the original studies and release gates. Python executes local deterministic source retrieval and archive diagnosis; the browser runs a separate, clearly labeled local illustration through the existing AGI ALPHA workbench. No paid service, wallet, model API or new persistent credential is required.

## Environments

The recorded experiment used Python 3.12.14, Git 2.51.1 and Linux x86-64. The reader uses `git cat-file --batch-command`. Its Python implementation uses only the standard library. The original Alpha call-site reproduction additionally imports the pinned repository's `cryptography` and `packaging` dependencies. `protocol/environment.json` records the actual host. Other supported Alpha platforms were inspected but not benchmarked. Physical disk-cold behavior is untested.

## Inspect the no-account demonstration

Open `browser/Foundry_Lab.html` in a modern browser. The bundled example computes locally without network access. The page labels recorded Python results separately and says that an approved external executor is not connected. Try A, B, C and D; pause, STOP, reopen, export, restore or retire the capability. User-selected inputs are restricted to the declared supported file domain. This is not a claim of live external autonomous execution.

The modular page can also be served from the companion directory with `python3 -m http.server 8767 --bind 127.0.0.1`, then opened at `http://127.0.0.1:8767/browser/`. Stop the server after use. Browser source and tests are documented in `browser/README.md`.

## Verify the prospective boundary

Run from the companion root:

```sh
python3 -c "from pathlib import Path; import sys; sys.path.insert(0,'src'); from freeze import verify; print(verify(Path('.').resolve()))"
```

Every listed source identity must match. `protocol/FREEZE.json` is the active scientific boundary. The preserved earlier boundary and `publication/storage-amendment.json` disclose a pre-experiment storage-only amendment after automatic approval review blocked durable saving. All 29 scientific file identities, comparators, budgets, task rules and analysis were unchanged. No confirmation task was generated before the amendment and independent freeze review.

The final archive inventory is in `MANIFEST.sha256.json`. A lightweight verification script is supplied as `verify_package.py`. Its file hashes verify custody; they do not confer release authority.

## Recompute the recorded analysis

This reads existing raw evidence and does not rerun any participant:

```sh
python3 src/analysis.py results/confirmation/campaign.json --output /tmp/foundry-recomputed-analysis.json
```

Compare the JSON with `results/analysis.json`. The frozen analyzer requires exactly 24 unique instances by seven arms, retains failures, aggregates repeated calls within an instance, and computes the registered paired log-ratio bootstrap. The primary gate is zero required-check failures and a 95% CPU-ratio upper bound below 0.95 against the direct specialist. Descriptive secondary comparisons are not additional independent discoveries.

## Replicate execution on the published cases

The published `confirmation/` directory contains all 24 generated repositories, archives, expected outputs and provenance. Run a new replication into a new destination:

```sh
python3 src/campaign.py --cases confirmation/cases.json --destination replication/run-001 --order-seed 812953
python3 src/analysis.py replication/run-001/campaign.json --output replication/run-001-analysis.json
```

The campaign will not overwrite an existing destination. Keep its failures and timing variation. This is a replication on now-public cases, not a new held-out confirmation. It creates only local research output under the specified destination and does not edit the repositories' committed files. Exact output correctness should reproduce; timings and confidence intervals can differ with machine and runtime conditions.

## Rebuild the source-derived input repositories

To reproduce the generator, obtain the public Alpha source at exact commit `f836f06e8351e64db1da770e16e304b5feb01f28` in a separate checkout, then run:

```sh
python3 review/confirmation_generator.py --source /absolute/path/to/alpha --commit f836f06e8351e64db1da770e16e304b5feb01f28 --destination /tmp/foundry-recreated-inputs --seed c1e429d05d24407a4abbe40d8e185499d1b3e6eb3f769ce93c022d163c798131
```

The destination must not exist. These inputs use genuine public software bytes in controlled changed layouts. They are generated instances nested in one source ecosystem, not 24 independently sampled natural projects. Intentional working-tree decoys and archive defects are expected. Do not "repair" the published confirmation inputs.

## Check the reader and child contracts

The independent development checks are shareable. The original recorded results remain under `review/` and `development/`. A new execution is a replication and should write outside the original records. The reader suite includes 29 cases; the final child suite includes 19 cases. These checks do not replace the original Alpha test/security/release campaign.

```sh
python3 -c "import sys; sys.path[:0]=['src','review']; import snapshot_reader,adversarial_check; print(adversarial_check.check(snapshot_reader.read))"
python3 -c "import sys; sys.path[:0]=['src','review']; import snapshot_reader,drift_core,child_adversarial_check; print(child_adversarial_check.check(lambda r,c,p,a,max_file=8000000,total=32000000:drift_core.compare(snapshot_reader.read(r,c,p,max_file,total),a,max_file,total)))"
```

## Review the useful patches

`patches/0001-add-bounded-snapshot-reader-and-adapters.patch` adds a bounded helper and adapters. It does not modify the production callers automatically. `patches/README.md` explains the existing-owner integration decision. The pinned original A and B outputs were compared byte-for-byte in development; raw method order, process traces, timings and selected source are retained. A's selected method was fixed before B. No full-CI speedup, platform qualification or deployment is inferred.

The `src/development.py` driver refuses to overwrite its completed development boundary. Reproducing development requires a separate companion copy with new output locations and an explicit replication label; it must not overwrite the published records or change the confirmation selection.

## Compile the paper and editable figures

The manuscript uses standard LaTeX packages, BibTeX and editable TikZ figures. The measured charts have editable plotting source and SVG outputs. From `paper/`:

```sh
pdflatex -interaction=nonstopmode -halt-on-error Software_Capability_Foundry.tex
bibtex Software_Capability_Foundry
pdflatex -interaction=nonstopmode -halt-on-error Software_Capability_Foundry.tex
pdflatex -interaction=nonstopmode -halt-on-error Software_Capability_Foundry.tex
```

The final PDF was rendered and every page visually inspected. `audit/pdf-qa.json` records the final inspected identity. Use `pdftoppm` or another renderer after changing source, then inspect every page again. Generated source is sufficient to compile without the original foundation PDFs; their canonical URLs, exact retrieved hashes and page references are included in the bibliography and source manifest.

## Costs and limitations

Read `results/cost-account.json` for measured categories and explicit unknowns. Benchmark provider calls are zero, while interactive research-model costs, human work, integration and future maintenance remain unknown. CPU seconds, wall latency, process counts, runner minutes and money are separate quantities. No live Jobs or token utility was executed. The complete investment has not been shown to pay for itself, and a repeated speedup does not establish acceleration.

The recorded candidate writes only its own artifact directory. Procedural role separation, frozen source identities, and before/after hash checks protect the evaluator and generated cases; this is a shared workspace, without OS-isolated evaluation. If a reproduction identifies an evaluator defect, retain the original run, review the correction separately, declare a new evidence boundary and make any repeated-testing history explicit.
