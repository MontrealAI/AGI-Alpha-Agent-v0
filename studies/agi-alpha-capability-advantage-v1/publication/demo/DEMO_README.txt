THE CAPABILITY ADVANTAGE — OFFLINE EN/FR DEMONSTRATION

Deliverable: The_Capability_Advantage_EN_FR.html
Open the HTML file locally. It embeds all data, CSS and JavaScript and needs no network or external assets.

The transfer panel, primary evaluation and economic model are separate evidence layers. The default economic case remains the prespecified structural-01/reference/12001 loss-making example. The scenario selector displays stored cell summaries; it does not run new simulations. Economic figures are modeled USD, not earned revenue. Unknown actual costs remain unknown.

Rebuild from the workspace root:
python publication/demo/build_demo.py --primary evidence/primary/summary.json --economics economics/results-primary/summary.json --market-analysis economics/analysis-primary/analysis.json --market-completion economics/results-primary/completion.json --market-representative economics/results-primary/preselected-representative.json --market-protocol economics/market-protocol.json

Run the Node DOM/application checks with the provided Node runtime and NODE_PATH pointing to its installed modules:
node publication/demo/qa_dom.cjs

QA: all 24 language/chain/stage/timing states and all 144 economic cells in EN and FR passed, along with repeated controls, provenance, selected-evidence JSON downloads and no-network checks. Declared palette contrasts passed WCAG calculations.

Real browser layout and screenshot QA: NOT RUN. An existing local Chrome binary was found, but the execution sandbox blocked startup before any page opened. The unsuccessful attempt is preserved in qa_browser_report.json. No browser was installed; no cloud browser or authenticated session was opened.

Source builder: build_demo.py and demo_template.html.
Authoritative input paths and hashes: build_receipt.json.
