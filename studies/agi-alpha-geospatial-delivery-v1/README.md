# 🌌♾️ AGI ALPHA FLYWHEEL — When Capability Creates Opportunity

**Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work**

**Vincent Boucher — President of MONTREAL.AI**

TRANSFORMATIONAL INTELLIGENCE: LEARNING TO CHANGE THE GAME

FIND YOUR ALPHA. BUILD YOUR SUCCESSOR Ω.

> “As Columbus braved the seas, we now venture into the vast oceans of AGI. The age of AGI exploration has dawned, and the horizons are boundless. Dare to dream, dare to explore.” — α-AGI Agent

## A complete delivery with a testable commercial case

This study constructs a reproducible Montréal geospatial onboarding and assurance package, then evaluates its complete economics under explicit assumptions. The executed deliverable preserves **3,476 recreation assets and 2,245 park/green-space polygons**, supplies **3,175 source-consistent associations**, and retains every unresolved relationship in a review queue. The customer receives usable files, provenance, maps, acceptance checks and an operator handoff.

The selected central scenario supports **modeled profitability under the stated assumptions**:

| Commercial quantity | Central result, CAD |
|---|---:|
| Estimated equivalent human-service reference | 1,092.94 |
| Selected selling price | 874.35 |
| Customer savings at the assumed matched acceptance standard | 218.59 per accepted package |
| Complete business cost per accepted delivery, mean | 326.54 |
| Accepted deliveries over twelve months, modeled mean | 74.47 |
| Twelve-month operating profit, modeled mean | 40,916.74 |
| Actual collected service revenue | **0** |

The price policy is the best mean-profit result within the tested family under its central demand assumptions; it is not a globally optimal market price. The broader uncertainty analysis includes losses and can favor a lower price. Human hours, buyer behavior, customer acceptance probabilities, demand, token usage and business costs are scenario inputs. Complete actual research expenditure is unmetered. The percentage of asset identifiers agreeing with geometry is **not** used as a model mission-success rate.

The offering is the **complete assurance handoff, including an explicit exception queue**. It does not include cadastral certification, field verification, source-owner fact correction or municipal/customer production-system writes. A buyer requiring those additional outcomes needs a different scope and economic case.

## Read the study

- [Complete paper](publication/PAPER.md)
- [Downloadable paper PDF](publication/AGI_ALPHA_FLYWHEEL.pdf)
- [Self-contained browser edition](publication/AGI_ALPHA_FLYWHEEL.html)
- [Executive brief](publication/EXECUTIVE_BRIEF.pdf)
- [Connected example and operator handoff](technical/OPERATOR_HANDOFF.md)
- [Final technical results](technical/final_results.json)
- [Final commercial confirmation](economics/final_results/confirmation.json)
- [Opportunity screen and human-effort rationale](opportunity_dossier.json)
- [Commercial assumptions and all cost categories](configs/economics.json)

The browser edition can be downloaded and opened locally. This is an additive research contribution under the repository’s ordinary draft/review process. Canonical Pages deployment, release sequencing and production qualification remain with the existing owners; no new publication route or release version is created here.

## Evidence and attribution

| Question | Evidence |
|---|---|
| Does the bounded package execute? | Actual official-source processing, preserved row identities, complete provenance, SQLite/GDAL readback and executable acceptance |
| Does the implementation agree with competent conventional tools? | **128/128** sampled nondevelopment decisions match a separate conventional implementation using the same formulation |
| Does the corrected instrument handle fresh structural cases? | **48/48** independently authored, seeded cases pass after the version 1.1.0 freeze |
| Was the retained instrument actually used by a recipient? | A separate process applied frozen version 1.0.0 to Anjou: **100 assets, 89 source-consistent associations, 11 reviews**; identical-information ordinary-library outputs tie byte for byte |
| Did optional format practice establish unrestricted transfer? | **29/32** fresh CSV/WKT/CRS missions have identical association semantics; all **256 rows** and extra fields survive; three boundary-rounding divergences remain visible, so unrestricted use is **HOLD** |
| Is Operational Alpha measured? | Controlled H/U/E/E+ trials were not run; U/E effects are explicit counterfactual sensitivities, including no benefit |
| Is optional retention commercially justified? | Its added costs and uncertain marginal savings are evaluated separately; baseline profitability does not depend on admission |
| Is authenticated sharing live? | **10/10** local checks use the existing TrustRegistry and the actual manifest; no live ENS, new native scope or production authority is claimed |

There are **301 facility review rows** and **456 park-layer review rows**, totaling **757**. The park reviews contain 455 missing logical indices and one invalid geometry. A missing park index may be legitimate for an otherwise valid private/other green space. `confirmed` in the technical files means agreement of a source identifier and unique geometric support; it is not independent proof of real-world truth or administrative approval.

Original version 1.0.0 failures remain preserved in `technical/independent_audit/`: null-property handling, nonpolygon park acceptance and shared coordinate-axis mistakes. Corrected version 1.1.0 is frozen separately. Its public-data rerun is explicitly a replay, and its new structural cases are separately identified. Earlier economic failures and corrections are preserved under `economics/history/`, `economics/results/` and `economics/development_failures.json`; authoritative final calculations are under `economics/final_results/`.

## Reproduce the complete study

The actual run used **Python 3.12.14**. Direct dependencies are pinned to the installed versions in [requirements-study.txt](requirements-study.txt). The replay uses local source files and does not call paid APIs, customer systems, wallets or live ENS.

From the repository checkout containing this study:

```bash
cd studies/agi-alpha-geospatial-delivery-v1
python3.12 -m venv .venv-study
. .venv-study/bin/activate
python -m pip install -r requirements-study.txt
python reproduce_study.py --output /tmp/agi-alpha-geospatial-replay --include-native-trust --repository-root ../..
```

Choose a **new or empty** output directory. The wrapper preserves historical receipts. It verifies the technical and economic freezes, regenerates the technical package, replays scoped checks, reruns the economic selection/confirmation with final confirmation seed **730552**, and compares all final economic JSON outputs by content. It writes `reproduction_receipt.json` and step logs beneath the chosen output directory. Successful reproduction means the recorded outcomes, including unfavorable ones, are reproduced.

The complete wrapper was executed successfully in this repository. Its compact receipt and logs are retained in [reproduction_complete/](reproduction_complete/). These scoped checks do not constitute full repository or release qualification.

### Standalone study archive

The technical and economic replay can run from an extracted study archive:

```bash
python reproduce_study.py --output /tmp/agi-alpha-geospatial-standalone
```

The optional trust fixture imports the **existing canonical repository**. To include it, extract this study under `studies/agi-alpha-geospatial-delivery-v1/` in the corresponding repository checkout, or supply `--repository-root /absolute/path/to/AGI-Alpha-Agent-v0`. The inspected runtime baseline was commit `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`. Signature replay uses new ephemeral keys; the ten semantic checks should match, while signature bytes legitimately change. No private key is retained.

For a technical-only replay, use:

```bash
python src/reproduce_technical.py --out /tmp/agi-alpha-geospatial-technical
```

For an economics-only replay, use:

```bash
python economics/run.py all --output /tmp/agi-alpha-geospatial-economics
```

The publication source and renderers are included. Regeneration uses the pinned Python packages and the DejaVu font family bundled with Matplotlib. From the study directory:

```bash
python publication/build_figures.py
python publication/render_publication.py
```

Publication rendering is separate from the computational replay and its preserved receipts. The downloaded PDF and HTML already contain the prepared publication.

## Source rights and inheritance

Code is Apache-2.0. Municipal source data is attributed to **Ville de Montréal under CC BY 4.0**, with exact source URLs, sizes, retrieval records and hashes in [public_data_sources.json](sources/public_data_sources.json). The corpus is preserved byte for byte; derived files do not imply municipal endorsement.

The workflow uses established GeoPackage, GDAL, PROJ and Shapely components. Its contribution is the connected service construction, testable handoff and explicit commercial/retention analysis. It does not claim invention of spatial joins, a geographic-information monopoly or autonomous market discovery.

**Reuse stable structure. Recheck new mission meaning. Regrant authority separately.** The [capability manifest](technical/capability_manifest.json) records rights, dependencies and limitations. Existing native scope does not admit this geospatial capability. The commercial baseline and optional capability investment remain separate decisions.
