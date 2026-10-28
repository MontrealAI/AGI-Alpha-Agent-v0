# Offline English/French evidence companion

`template.html` defines the presentation and local browser interaction. `build_demo.py` embeds the exact available source bytes, their identities and an evidence index into one self-contained `index.html`. It does not query the network, invent missing outcomes, execute production or run a market campaign.

```sh
python demo/build_demo.py
```

Before complete evidence exists, absent results remain explicitly pending. The final build requires actual production, reuse-control and completed market artifacts:

```sh
python demo/build_demo.py --final
```

The companion provides a useful-mission inspector, a four-skill typed graph, source/evidence/attestation details, separate attestation and root permissions, real browser WebCrypto inclusion and epoch/history-integrity checks, a local tamper test, recorded allow/refuse controls, matched production results, recorded condition/cost/policy/seed selectors, finite-cash investment decisions, exact decision-packet and selection-trace downloads and a technical appendix.

The independent attention/workload heatmap is explicitly hypothetical. It never rewrites frozen data or credits unmeasured attention to the experiment. The direct D alternative and unknown complete costs remain visible. USD scenarios are separate from actual receipts, USDC routes and $AGIALPHA utility.

Local integrity verification is deliberately limited to typed SHA-256 commitments and root-history integrity. It performs no ENS lookup and authenticates no real signer. Authority is a bounded fixture, fixture signatures are noncryptographic, and live identity enforcement remains NOT RUN.

## Browser review

Use installed Playwright and an available isolated Chromium executable. The checker uses the runtime module location when CODEX_PRIMARY_RUNTIME_NODE_MODULES is defined, otherwise a locally installed playwright package:

```sh
VERIFIED_CAPABILITY_CHROMIUM=/absolute/path/to/chrome-headless-shell node demo/test_browser.mjs
```

The default Playwright executable may be used by omitting the variable when installed. Browser checks cover EN/FR desktop/mobile, all four skill and four edge inclusion/tamper cases, every recorded reuse control, every fresh mission, all 48 market cells plus the 24 reference seeds, exact downloaded hashes, unknown-cost handling, responsive layout, no-JavaScript boundaries and zero external requests. Screenshots and checks are in `browser-review/`. Source construction and browser review are local artifact checks, not new scientific confirmation missions.

The first scaffold passed 42 browser checks with zero page errors and zero external requests. Initial missing-browser and sandbox-startup failures are retained in `browser-review/launch-attempts.json`. Final-source browser verification must follow the final data rebuild.

The complete local edition passed 178 browser checks, including all 18 fresh missions, all 38 recorded allow/refuse cases, all 48 economic cells, the 24 reference seeds, and the preserved positive individual path. There were zero page errors and zero external requests. Its evidence index includes the exact resource ledger, frozen inputs, 18 complete decision-packet ZIPs, selection traces, PDF and positive-world inspection. The final HTML identity is recorded in build-receipt.json and the matching browser-review/checks.json.
