# Alpha 1.42.0: public installation and first run

[Public release](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/v1.42.0) · [Browser guide](https://montrealai.github.io/AGI-Alpha-Agent-v0/try/)

The actual public installer and the CLI/API operations below passed outside the
source checkout. Tested environment: Linux x86_64/glibc2.39, Python3.12.14,
Node24.22.1, a fresh venv with system site packages disabled. The base interpreter,
Node and existing download configuration/cache were inherited; this was not a new
operating system. The project supports Python3.11–3.13 and requires Node22 or later
for the optional workbench. Other fresh-public OS/runtime tuples are not established
by this receipt. No wallet or funded action is required.

Start in a new directory. These four downloads reproduce the selected installer
inputs; downloading every optional research/evidence asset is unnecessary.

```bash
mkdir -m 700 alpha142-run
cd alpha142-run
ALPHA_RELEASE=https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/download/v1.42.0
for ALPHA_ASSET in install_agent.py requirements-agent.lock alpha_factory_v1-1.42.0-py3-none-any.whl SHA256SUMS; do
  curl -fL "$ALPHA_RELEASE/$ALPHA_ASSET" -o "$ALPHA_ASSET"
done
python3.12 install_agent.py --release-dir "$PWD" --venv "$PWD/venv" --check-only
python3.12 install_agent.py --release-dir "$PWD" --venv "$PWD/venv"
venv/bin/python -I -m pip check
venv/bin/alpha-agent --version
venv/bin/alpha-agent --home mission-home init
venv/bin/alpha-agent successor-work example documentation --output mission.json
venv/bin/alpha-agent successor-work plan mission.json
venv/bin/alpha-agent --home mission-home successor-work run mission.json --output result
```

Inspect the result and its printed `run_id` and `result_digest`. A completed local
run is in `review`; that is not independent qualification or permission for an
external action. The plan exposes its bounded work contract. Edit the input before
submission; identified submissions retain their original snapshot.

The existing commands provide explicit local review, evidence export and input
restoration. Copy the actual IDs from your run. Retain your trusted journal public
key before exporting; a key supplied inside an untrusted evidence bundle is not
an independent trust anchor.

```bash
ALPHA_RUN_ID=copy-your-run-id
ALPHA_RESULT_DIGEST=copy-your-result-digest
ALPHA_SOURCE_KEY=$(venv/bin/python -I -c 'from alpha_factory_v1.core.runtime.store import Journal; print(Journal("mission-home").public)')
venv/bin/alpha-agent --home mission-home successor-work show "$ALPHA_RUN_ID"
venv/bin/alpha-agent --home mission-home successor-work review "$ALPHA_RUN_ID" --result-digest "$ALPHA_RESULT_DIGEST" --decision accepted --note "I checked this local artifact."
venv/bin/alpha-agent --home mission-home successor-work export "$ALPHA_RUN_ID" --output portable
venv/bin/alpha-agent successor-work verify-receipt portable/signed-receipt.json --source-key "$ALPHA_SOURCE_KEY"
venv/bin/alpha-agent successor-work restore portable/evidence.json --output restored-mission.json
venv/bin/alpha-agent --home restored-home successor-work run restored-mission.json --output restored-result
```

That restore recreates the submitted specification for an explicit new local run;
retain the export as historical evidence. The separate successor checkpoint/restore
journey below is covered by the full acceptance procedure and restores stopped,
with no active proof, grant or serving release.

For interruption, inspect the retained record before explicitly continuing the same
`--run-id` with `--resume`. A paused/stopped control record is a cancellation/control
request; wait for the executing worker to terminate before claiming physical
quiescence. Neither cancellation nor restore claims to undo an external effect.
The public acceptance reproduces interruption and explicit second-attempt recovery.

Run the existing two-generation rehearsal separately:

```bash
venv/bin/alpha-agent --home successor-home init
venv/bin/alpha-agent --home successor-home successor-demo --output successor-evidence
```

Its measured local decision is `RETAIN_INCUMBENT`, qualification `HOLD`, production
authority `false`. It uses changed synthetic streaming requirements; it is not the
held full Harness/Fleet journey or general self-improvement.

Equivalent installed API entry:

```python
from pathlib import Path
from uuid import uuid4
from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.workbench import execute, invoke

home = Path("api-home")
Journal.initialize(home)
spec = invoke({"operation": "example", "family": "documentation"})
record = execute(home, spec, str(uuid4()))
assert record["state"] == "review" and record["authority"] == []
```

The reproducible acceptance script uses the installed interpreter and fixed source
identity. Download these verification scripts from this evidence snapshot, without
installing the evidence branch as application source. Select new absent output
paths for each finite test.

```bash
venv/bin/python -I accept_installed.py --commit c352bad0a0941fdccd490a7224e3efd1b8de45d5 --module-sha256 87ad9f365ebf1b5c1e93edc275e6fe933b6c247e51b848b52dc66c34344a8492 --output "$PWD/acceptance"
venv/bin/python -I measure_installed.py --commit c352bad0a0941fdccd490a7224e3efd1b8de45d5 --output "$PWD/load-sample"
```

`verify_upgrade.py` additionally requires the operator's matching stopped1.41.1
private home and its original load/recovery receipts. Private keys/homes are not
published here. It acknowledges historical results without replay, new proof or
new authority. Random IDs, signing keys, timestamps and machine timings differ on
new executions; those differences must not be disguised as the original receipt.

Verified installer inputs:

| Asset | Bytes | SHA-256 |
|---|---:|---|
| install_agent.py | 6734 | `e0d165632be031627e601adf6a68b2a26a1dc29ed127de4473b93212a0bb2925` |
| requirements-agent.lock | 85690 | `d58df2a38d099f8123d7445f62fec4684d029e588ce4b615151387c4decd1392` |
| alpha_factory_v1-1.42.0-py3-none-any.whl | 5498450 | `fff8c6c8a8dbeeebf1f91cc8e9a3fae17113baac93b6ed0d6096ecb59d072554` |
| SHA256SUMS | 9631 | `ef704dcd7ef9d2cacf290e3873d021ba7449490e677cc9aaa4290efc00276175` |
