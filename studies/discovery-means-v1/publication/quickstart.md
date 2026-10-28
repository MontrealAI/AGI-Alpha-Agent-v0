The executed limited research installation used an editable native distribution and add-on, reusing the session's existing dependencies. From a complete source checkout, the repository-prescribed full setup remains `FULL_INSTALL=1 ./codex/setup.sh`. That setup did not complete here: no offline wheelhouse was available, and the sparse checkout lacked the preflight module. A clean locked release installation is therefore not claimed.

```sh
python3 -m venv --system-site-packages .venv-discovery
.venv-discovery/bin/python -m pip install --no-deps --no-build-isolation -e . -e contrib/discovery_means_v1
.venv-discovery/bin/python -m discovery_means.cli contrib/discovery_means_v1/examples/adaptive.json --output /tmp/policy.json
.venv-discovery/bin/python -m discovery_means.cli contrib/discovery_means_v1/examples/adaptive.json --transcript contrib/discovery_means_v1/examples/transcript.json --output /tmp/continued.json
```

The authored example uses a 1-unit screen followed by a 2-unit branch-specific test. Every contingent path costs at most 3 units, whereas buying both branch tests costs 4. Its supplied `screen=R2`, `right=c` transcript identifies `H2`; these are authored symbolic observations. The CLI reports a checked policy, finite infeasibility or incomplete computation, and never executes imported probes.

The actual native custody journey is separately reproducible with a new private directory:

```sh
.venv-discovery/bin/python -m discovery_means.native_run contrib/discovery_means_v1/examples/adaptive.json --private-directory /tmp/discovery-fresh-private --output /tmp/native-journey.json
```

It exercises the installed signed native custody path with ephemeral research roles. It records opportunity, witness, bundle and locally executed evidence, checks readback, and refuses replay. Private keys and state are not publication artifacts. The expected bundle state is `paused-uncertain`; incomplete cost buckets remain incomplete.

A portable replay also ran from an unrelated working directory, preserving the frozen sources:

```sh
.venv-discovery/bin/python studies/discovery-means-v1/reproduce.py --repo-root . --out /tmp/discovery-replay-fresh
```

It reproduced all 24 instrument, adaptive-control and static-control outputs, six malformed-input refusals and all 12 native predecessor worlds, and re-audited the saved hosted outputs. Re-auditing does not rerun a hosted model. Full input schema, limits, development commands and environment qualifications are in `contrib/discovery_means_v1/README.md`.
