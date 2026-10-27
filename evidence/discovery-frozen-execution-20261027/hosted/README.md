# Hosted outcome for the frozen-execution repair

This is a subsequent evidence-only record for exact source e9cc4dcb5a27186fba1253ef0eebbc8df3a0c57b / tree db823b3e93971bfcc5b1a04d1c4841c80168dbab, PR #4976. It does not change that candidate, its review, an owner branch, a worker, a fixture, a publisher or a release.

Exact-head configured code review completed with no findings. Hosted Transformational Intelligence acceptance 40548268877 and MARK wallet acceptance 40548268921 passed. SUCCESSOR mission recovery 40548268945 failed its generated-source check, then its screenshot upload failed because the browser stage had not run. No failure or skipped work is relabeled passing.

The raw failed-job log is retained unchanged in mission-failure.log. Its actual PR merge commit 824ea4e31c24a4784782f97a68c55d833e940915 has the same tree as the reviewed candidate. The generated cache changed from agialpha-gallery-ad95f74d442075f0 to agialpha-gallery-aba7e8d3935cd34f in all three workers.

worker-baseline-comparison.json independently re-renders workers from exact Git blobs for both the unchanged #4972 parent 03b2eb97f1e150956ef0fa028e1ad665cc755cf6 and the repair. All 438 selected cache inputs match byte-for-byte. Both sources produce identical three-worker drift and the exact new cache seen in hosted logs. This attributes the failure to the inherited source state; it does not waive the generator gate or establish successful browser recovery.

Reproduction uses the unchanged scripts.build_service_worker.is_cache_asset and render_scripts functions, git ls-tree -r --name-only REF -- docs, git show REF:PATH for every selected asset and stored worker, and the release from REF:alpha_factory_v1/demos/catalog.json. No filesystem-generated worker or untracked file enters that comparison.

The original source packet already identifies the older owner stack's unqualified immutable-worker/release boundary. The current #4973/v1.46.1 publication lane remains open and authoritative. Its owners must reconcile the stack, regenerate and qualify the current worker/source set, and run all applicable final-source/installed/public gates. Do not fix this by editing an immutable fixture, weakening a check or creating a competing publication.

The repair stays draft and unmerged. This separate record preserves hosted outcomes without amending the reviewed candidate or repeatedly restarting its workflows. STATUS.json records exact identities and outcomes. Original local evidence and its original scopes remain unchanged.
