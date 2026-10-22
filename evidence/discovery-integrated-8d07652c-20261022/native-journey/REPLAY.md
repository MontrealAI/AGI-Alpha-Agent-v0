# Replay the saved cde docket

Requires Node **24.21.0**, standard Node modules, `sha256sum`, and `unzip`. No repository checkout, package install, network, Git, provider, or original workspace path is needed. Run these commands from this `native-journey` directory with that Node version on `PATH`:

```sh
printf '%s  %s\n' \
  '6c8c0d8283505101078f63a79d8c03144b3ee550bc27f265b027bbd5d55f9314' \
  'actual-native-cde-evidence.zip' | sha256sum -c -
replay_dir="$(mktemp -d)"
unzip -q actual-native-cde-evidence.zip -d "$replay_dir/evidence"
node --experimental-vm-modules --max-old-space-size=512 \
  ./replay_saved_docket.mjs "$replay_dir/evidence" "$replay_dir/replay-result.json" \
  > "$replay_dir/replay.stdout.json" 2> "$replay_dir/replay.stderr.log"
cat "$replay_dir/replay-result.json"
```

The script requires an existing absolute extracted directory and an **absent absolute output file outside it**. It authenticates all 147 original files against fixed hashes before importing code, including the complete source manifest, original report, and shared `8d3575…edad5` helper. It parses the 31 captured Alpha modules without linking/evaluating them, then uses the owned-byte boundary with only the actual workspace and docket entry modules. Recorded Git modes remain authenticated metadata; extracted permissions need not reproduce the original capture permissions.

Actual Alpha APIs replay the saved mission history, reconcile the thirteen-section docket against independently fixed source/receiver/mission/head expectations, and require byte-identical workspace reopening and docket reexport. All input hashes are checked again afterward. The script never writes input bytes, imports native receiver implementations, or executes an imported real-task artifact/proposal. Only a new result file and redirected logs are written outside the extracted input.

This is **semantic and raw-history verification of saved evidence** for Alpha `cde3010e1e137c49885477f1f514ece6efec0fdd` / tree `dca53a253eae34c67ee7ea7ad0dffd264239bd41`, catalog `644258ac…eebf2` (41 entries). Deterministic finite checks and future comparisons are recomputed; the thirteen native observations are **not rerun**. Their original raw receipts remain unauthenticated invocation evidence. This supplies no later-HEAD, hosted-browser, released-installed, operational, human, or organizational acceptance. Authority remains `none`; unknown costs remain unknown.

One ordinary positive run on a fresh ZIP extraction passed on Node 24.21.0: all 147 input files verified before and after replay, all thirteen docket sections reconciled, and workspace/docket bytes matched exactly. Its result and identical stdout were retained beside the public packet as `public-evidence-integrated8d-replay-result.json` and `public-evidence-integrated8d-replay.stdout.json`; the stderr log contains only Node's expected experimental VM-module warning. The original evidence directory and ZIP were rehashed afterward and remain unchanged.
