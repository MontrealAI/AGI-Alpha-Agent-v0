[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Edge-of-Human-Knowledge Demo Tasks Sprint for Codex

This sprint describes how Codex can publish the **Alpha-Factory v1** demo gallery to GitHub Pages in a polished subdirectory. The goal is a user-friendly deployment where every demo plays in real time with rich visuals and smooth interactions.

Run `./scripts/edge_of_knowledge_sprint.sh` from the repository root for an automated workflow.

The steps below triple-verify environment integrity, rebuild all assets and deploy a consistently beautiful gallery. Revisit them whenever the demos or documentation change.

## 1. Validate the Environment
1. Install **Python 3.11+** and **Node.js 20+**.
2. Confirm the versions:
   ```bash
   python --version
   node --version
   ```
3. Execute the preflight script:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
   ```
4. Verify the browser demo requirements:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
5. Install optional dependencies so verification tools succeed:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```
6. Confirm each README contains the standard disclaimer:
   ```bash
   python scripts/verify_disclaimer_snippet.py
   ```
7. Validate the demo packages:
   ```bash
   python -m alpha_factory_v1.demos.validate_demos
   ```
8. Run the pre‑commit hooks to catch formatting issues:
   ```bash
   pre-commit run --files docs/AT_THE_EDGE_OF_HUMAN_KNOWLEDGE_DEMO_TASKS_SPRINT.md
   ```

## 2. Build the Insight Demo
Compile the progressive web app and verify the service worker hash:
```bash
./scripts/build_insight_docs.sh
```
If lineage logs are available this exports `tree.json`, updates
`docs/index.html` via `scripts/generate_gallery_html.py` and ensures the
**Meta-Agentic Tree Search** animates organically.

## 3. Generate the Demo Gallery
From the repository root run:
```bash
./scripts/deploy_gallery_pages.sh
```
The script fetches assets, rebuilds documentation and compiles the MkDocs site under `site/`.
Afterwards confirm the build is clean:
```bash
mkdocs build --strict
```
If the command fails, address the warnings before publishing.

## 4. Preview Locally
Serve the pages and check that animations are fluid:
```bash
python -m http.server --directory site 8000
```
Navigate to <http://localhost:8000/> and step through `index.html`. Confirm that each README showcases preview media so viewers can follow along in real time.

Spot-check the offline cache:
```bash
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1
python scripts/verify_insight_offline.py
```

## 5. Deploy to GitHub Pages
Publish the gallery when satisfied:
```bash
mkdocs gh-deploy --force
```
The resulting URL typically looks like:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
Open the link in an incognito window and verify the service worker caches assets. The landing page now shows quick links; choose **Visual Demo Gallery** for the full list or **Launch Demo** for the insight preview.

## 6. Maintenance Tips
- Re-run the helper whenever demo docs or assets change.
- Capture short GIFs or screenshots under `docs/<demo>/assets/` for a highly visual experience.
- Test with `mkdocs build --strict` before deploying and ensure `pre-commit` hooks pass.
- Run `pre-commit run --files <changed_files>` and `pytest -m 'not e2e'` to confirm formatting and basic tests before publishing.
- Periodically verify every README still embeds the [disclaimer snippet](../docs/DISCLAIMER_SNIPPET.md).

## 7. Final Polish
- Open the gallery in multiple browsers and confirm the layout feels professional and inspiring.
- Ensure preview media loads instantly and animations remain fluid on slower machines.
- Validate the offline cache by toggling airplane mode and refreshing the page.
- Keep the aesthetic consistent across all pages by leveraging the bundled `stylesheets/cards.css`.
