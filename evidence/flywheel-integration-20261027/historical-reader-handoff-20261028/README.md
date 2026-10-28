# Historical-reader migration handoff

This is inert data for the primary owner's commercial/decision-authority correction.
It does not apply a runtime or executable-test change and does not qualify C516 or
the repaired runtime. Base: c5164a385f54b59a11b53d70cf491e5e21ad3b18, full tree
895e9dd85f6a2c5c292fd28432bfbbdef44d8bf5. The primary owner remains authoritative.

The proposed three reader changes bind connected/frontier/delivery-guard history
to its original enterprise bytes and make the superseded delivery-guard worker
and page checks explicitly historical. The original source freezes, worker JSONs,
all existing profiles and the earlier distinct enterprise archive remain exact.
The new enterprise archive is data only: 37,034 bytes, SHA256
fa79c1f3ef9d587b382aaf9a01c0a09b133109fde4bc2d471d0388d56371ade1.
The page archive is the exact C516 page: 1,607,690 bytes, SHA256
acc4af5755188df76526c67387c683b0d598c050c70ebefacf6f2893eabfb6ff.

SOURCE_PATCH.json names the five intended targets, expected original hashes and
inert payloads. Reuse the payloads only after checking each before hash, or
reconcile manually if the primary's migration already changes the same files.
The patch text covers the three readers; the two archive payloads are separate.
No autonomous patch application, alternate registry or publisher is introduced.

Checks ran in an isolated C516 checkout, with only these proposed readers and
archives. Original drift counterexample: changing the current enterprise module
by an inert comment made all three old readers fail. After migration: all162
historical cases passed on exact source, and all162 passed with inert changes to
the current enterprise module, page and all three workers. All3 selected readers
refused a same-size archive mutation. All probe mutations were restored in
finally blocks. Current Ruff0.12.5 and pinned Ruff0.2.1 passed the three readers.
Commands, durations, outputs and original failures are preserved alongside.
One initial plain `ruff` command was unavailable on PATH; the actual modern pass
used `python -m ruff`. No full local hook pass is claimed for this data handoff.

These are historical preservation tests. A separately strict NEWEST-edition test
must bind the repaired current module, page, workers and full source closure;
the final composed source still needs its normal review, CI and release gates.
The archive-isolation pass cannot qualify any changed current runtime behavior.
The four held behavioral nodes were not selected in this handoff. The earlier
selection incident remains separately unqualified; all five held source pins
are untouched. No live provider, wallet, buyer or frozen public canary ran here.
