# Reproduce the research edition

Run commands from `studies/agi-alpha-opportunity-construction-v1`, or from the same directory extracted from the research companion. Use a new output directory for every technical replay. The original fixtures, freezes and results are evidence and must remain intact.

## Environment

The observed runtime was Python **3.12.14** and Node **24.22.1** on Linux. The repository's Node target is **22.17.1**, which was not executed here; this study is not a repository-wide compatibility qualification. `config/dependencies.json` records the observed versions.

The economic engine uses only the Python standard library. The technical worker directly imports the supplied **MPyC 0.11** closure, whose wheel SHA256 is `059ffa3396089ebb77beb43ea2f8040f2a20f3fc7ff6d3c839df3b3f3c28d38e`. The authority wrapper additionally needs `cryptography==50.0.2` and `pydantic==2.11.7`:

```sh
python -m venv /tmp/agi-alpha-study-env
. /tmp/agi-alpha-study-env/bin/activate
python -m pip install -r requirements-study.txt
```

Creating a fresh environment and dependency installation are reader setup steps. The recorded reproduction used the already available versions; it does not claim a fresh network installation was tested. Transitive environment packages are not a fully hash-locked platform image. The technical freeze binds the actual used MPyC sources and dependency version record. No model API, consumer subscription, wallet, live ENS, confidential utility system or external network service is needed during the study execution.

MPyC uses three localhost worker processes and sockets. The supervisor enforces a 300-second timeout per worker group and terminates remaining workers on failure. Use an unused port range. If a managed environment does not permit local sockets, use its authorized execution workflow; do not change or bypass its restrictions.

## 1. Reproduce the original and successor results

```sh
python -B src/reproduce.py --destination /tmp/reserve-reproduction-01 --port 19100
```

The destination must not already exist. The command:

1. Verifies all **36** technical source/configuration/dependency bindings against the original freeze.
2. Regenerates the original 120 worlds and successor 120 worlds from the same published seeds.
3. Runs three actual MPyC processes for each cohort with a fresh local authorization fixture.
4. Executes the identical ordinary-library replays on the same generated inputs.
5. Compares all ten generated input JSON files byte for byte and every scientific result/answer in four result files.
6. Rechecks frozen sources and saves a complete `reproduction.json` in the new destination.

The recorded replay passed **14/14 comparisons**, with every original scientific result unchanged. `evidence/technical_reproduction.json` contains the actual receipt. Timing and process identifiers differ between executions. Message byte counts are recorded descriptively; the comparison does not treat randomized MPC traffic as a scientific output. Answers, input commitments, scenario hashes, oracle diagnostics, counts, fixed family strata and reference intervals must match exactly.

For separate runs, the underlying commands are:

```sh
python -B src/study.py confirm --cohort origin_confirmation --authority --port 19100 --output-root /tmp/reserve-separate-01
python -B src/study.py confirm --cohort successor_confirmation --authority --port 19130 --output-root /tmp/reserve-separate-01
python -B src/study.py library-replay --cohort origin_confirmation --authority --port 19160 --output-root /tmp/reserve-separate-01
python -B src/study.py library-replay --cohort successor_confirmation --authority --port 19190 --output-root /tmp/reserve-separate-01
```

Expected original totals: **120 agreement, 85 feasible, 35 not certified, 2 bilateral false positives**. Expected successor totals: **120 agreement, 84 feasible, 36 not certified, 5 bilateral false positives**. The identical library must return identical answers. This reproduces a finite result; it does not create a second fresh-recipient study or establish new transfer.

Do **not** call `src/study.py freeze` in the published package. Its original freeze occurred before confirmation input creation. A new policy or retained-capability claim needs a new version, prospective freeze and independent fresh seeds rather than rerunning public protected cases.

## 2. Reproduce economics

```sh
python -B src/reproduce_economics.py
```

This runner creates a disposable temporary tree from six original input/source files and copies no generated outputs. It runs these published stages there:

```sh
python -B src/economics.py self-test
python -B src/economics.py develop
python -B src/economics.py confirm
python -B src/economic_conditional_supplement.py run
python -B src/economic_tables.py
```

The command verifies **12** primary/supplemental bindings before execution, in the regenerated tree and after execution. It compares **ten artifacts byte for byte**, including development, selected-policy freeze, primary confirmation, sensitivities, retention, example ledger, summary, all-nine-policy supplement, plotting data and policy CSV. The recorded replay passed every comparison without numerical tolerances or metadata omissions. The temporary tree is removed after inspection. Original economic files remain unchanged. If a reproduction receipt already exists, the runner retains it in `previous_attempts` before appending the new receipt.

The original development used seeds **630100–630349**. The primary confirmation used **9811000–9811999**. The later all-nine-policy supplement used new paired seeds **9821000–9821999**, with unchanged value, demand, pricing, timing, readiness and funding assumptions. Replay uses the committed supplement; it does not re-freeze or select a new policy.

Expected primary result: no launch is best tested; the selected direct policy has mean full-venture profit **−$30,146.88**. Expected supplement: all nine policies have zero launches and mean screening loss **$3,509.86** each. The post-result model-upgrade analytic bound is preserved and explicitly excluded from the list of regenerated prospective outputs.

## 3. Re-run native integration into new destinations

The final preserved artifact run is `integration/artifacts/final-02`. Native JavaScript dependencies and licenses are bundled and hash-checked; no npm installation is required for this adapter.

```sh
node integration/run_integration.mjs --input config/venture.json --output integration/artifacts/reader-replay-01
```

Choose a new output path. Expected: **15/15 artifact and boundary checks**, the same supplied opportunity and FusionPlan root, unchanged empty production qualification registry, zero financial actions. New random capsule salts/IVs and project identifiers create new encrypted bytes. Compare semantic contents, source/input bindings and checks; do not demand byte identity of randomized ciphertext.

Run the native query-authority controls using the already public manifests:

```sh
python -B integration/query_authority_controls.py --origin data/origin_confirmation/manifest.json --successor data/successor_confirmation/manifest.json --worker src/mpc_worker.py --output /tmp/reserve-authority-reader-01
```

Expected: **21/21 controls**, including exactly one accepted concurrent caller, replay refusal, preservation of roles, refusal of an old origin grant on the successor mission and acceptance of a separate fresh successor grant. Private keys and journals are temporary; published receipts contain public evidence. These are local simulated identities, not live ENS or malicious-host rollback resistance.

The explicit recipient namespace fixture can also be reproduced:

```sh
python -B integration/recipient_access.py --artifact src/mpc_worker.py --descriptor config/capability_descriptor.json --output /tmp/reserve-recipient-reader-01.json
```

Expected: exact descriptor/instrument binding, an existing worker-role signature, **5/5 refusal controls**, zero live ENS checks and zero network publication. Receiving a file is distinct from the separately recorded execution of fresh recipient work.

## 4. Inspect or replay manual adversarial cases

`evidence/challenge_checks.json` preserves eight independently hand-constructed cases under each of two scenario families, giving **16** expected/oracle/MPC agreements plus **3** malformed-input refusals. These are deterministic challenge cases, not a statistical sample. In particular, two universal eligible assets suffice for every pair but not every triple.

`src/challenge_checks.py` writes to the study's evidence path. To preserve the published original, run it only in a separately extracted copy:

```sh
python -B src/challenge_checks.py
```

The source contains no customer inputs. Do not treat its historical “constructed before confirmation” provenance text as a new temporal claim for your replay. Its fresh runtime receipt establishes only that the same public challenges ran again.

## 5. Rebuild publication files

```sh
python -m pip install -r requirements-publication.txt
python -B src/figures.py
python -B src/build_publication.py --study-dir . --render-dpi 105
```

Run in a copy if preserving exact original PDF bytes is required. Fonts and the PDF rendering utility (`pdftoppm`) must be available; see the builder's error message if a local dependency is absent. The publication pipeline produces three PDFs and a self-contained HTML edition. Its QA records page counts, extracted text and bounds checks; actual visual inspection is separately recorded. Regenerated PDF metadata/rendering may differ by environment, so use the original hashes for the published edition.

## 6. Evidence boundaries and changes

Reproduction confirms computation from specified inputs. It does not validate real demand, insurability, independently operated host security, physical compatibility or model reasoning reliability. The hosted discovery runs cannot be exactly replayed from a deterministic seed because backend snapshots and realized token bills were not exposed; original packets, budget caps, outputs, source checks and rejection reasons are supplied.

The main pipeline generated code and fixtures locally. It did not train closed-model weights, claim protected-test accuracy, collect revenue, mint tokens or move customer funds. All automated-delivery, business and financing figures are transparent simulations except explicitly measured local execution. Additional assessments, retention and Gym costs are separated as B/C, with no second charge for the originating A-funded instrument.

If a required check fails, preserve its receipt and investigate. Do not silently regenerate a frozen source, delete a failing world or reclassify a conditional financial loss. A changed policy belongs in a new prospective experiment.
