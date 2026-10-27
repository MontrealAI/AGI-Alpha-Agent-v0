# The Network That Learns to Invent: bilingual evidence companion

Open `index.html` in a modern browser. It contains its own CSS, JavaScript, measured summaries, numerical field arrays and economic summaries. It performs no external network requests and works offline. The PDF and source links use the surrounding research package.

From the study root, rebuild after the actual economic experiment finishes:

```bash
python build_demo.py
python demo/qa_demo.py
```

`build_demo.py` reads the frozen technical confirmation, selected checkpoints, retained numerical solutions and `economy/results.json`. It never substitutes invented economic results. When that file is unavailable, the economic section explicitly says confirmation is pending. `manifest.json` records all input hashes and whether actual economics were included.

For a local HTTP preview, run this from the study root and open `http://127.0.0.1:8765/demo/`:

```bash
python -m http.server 8765 --bind 127.0.0.1 --directory .
```

The interactive paired intervals are calculated directly by this builder using 10,000 bootstrap resamples and seed 854201. They do not embed the paper's separate 5,000-resample, seed-81221 calculation. Both are descriptive case-level calculations; small Monte Carlo differences in endpoints are expected.

## Interactive evidence

- English/French switching preserves the selected conditions.
- Twelve actual field examples are the first four from each family, without selection by outcome. Reference fields come from retained confirmation arrays. Uncorrected v1/v2 predictions are reconstructed from the frozen checkpoints solely for visualization.
- Heatmaps use a common v1/v2 error scale by default. Individual scales are optional and labeled.
- A training-residual trace shows the observation before each of 32 enrichment actions; it is not presented as fresh evaluation.
- Numerical comparisons include all six methods, fresh thermal/transfer cases and deliberately shifted cases. Paired bootstrap intervals are descriptive case-level uncertainty, not independent-machine speed claims.
- Inverse-mission composition compares against a competent generalist already equipped with the same sensor-design method. Fixed sensors are an ablation.
- Enterprise controls select actual simulated result groups and policies, keeping gross collections, refunds, costs, reserves, receivables, cash and available earned funds separate.
- The break-even explorer is explicitly counterfactual arithmetic. Its workload multiplier is an assumption, not additional measured evidence.
- The evidence-receipt download retains the displayed source/checkpoint/result identities and current selections.

## Scope

The edition reports local numerical learning and synthetic enterprise experiments. It does not claim autonomous invention, measured frontier-model delivery, actual customer revenue, live authenticated ENS agents, physical validation, production admission of a PDE capsule, or specialist ASI.

`qa/QA_REPORT.json` contains the complete actual-economics Chromium control, download, language and responsive-layout campaign. `qa/PUBLICATION_QA.json` checks the final bootstrap disclosure, relative links, browser-paper math/citations/figures, and final mobile layout. `qa/FINAL_QA.json` connects their exact source identities and scopes. Screenshots cover English/French desktop and mobile layouts. This local QA does not qualify a public deployment.
