# Independent RC-circuit execution

This is same-session independent numerical implementation, not institutional peer review. It executes the generated
computational RC analogues and does not establish fabricated hardware or physical thermal validation.

## Frozen rule and executed result

`CIRCUIT_ACCEPTANCE.json` declared absolute agreement at most `1e-6` before the first nominal circuit run. It compares
each generated experiment's predicted nominal output with two separate calculations:

1. A netlist parser stamps resistor conductances and grounded capacitor values, then integrates Kirchhoff's current
   equations using SciPy `solve_ivp`, method DOP853, `rtol=1e-11`, `atol=1e-13`. It imports no primary engine or primary
   closed response formula. An isolated ideal voltage-controlled readout applies the explicitly specified gain.
2. The free ngspice 42 binary executes the same `.cir` in batch mode with user initialization disabled. Its native
   transient `.measure` result is read from the retained output.

The corrected nominal run in `circuit_nominal_v3/` passes **32/32 circuits**: two binary-witness circuits and thirty
six-hypothesis successor circuits. Maximum absolute differences are `1.3530843112619095e-14` for ODE versus primary,
`1.2638226385558449e-9` for ngspice versus primary, and `1.2638270863868373e-9` for ngspice versus ODE. These are model
agreement measurements, not measurement-error bounds for real apparatus. Ngspice's printed `.measure` precision
contributes to the reported difference.

Every run writes its input/source binding manifest before executing cases and refuses an existing output directory.
`results.json` records Python, NumPy, SciPy and simulator versions; native stdout/stderr are retained per circuit.
These are nominal development checks. Fresh randomized confirmation requires a separately frozen new input batch.

## Reproduction

With Python 3.12, NumPy 2.3.5, SciPy 1.17.0 and an installed ngspice 42:

```sh
python3 verification/test_circuit_runner.py
python3 verification/circuit_runner.py evidence/development verification/circuit_reproduction --ngspice /path/to/ngspice
```

If running the isolated package used here, add
`--library-dir /tmp/possibility-ngspice/root/usr/lib/x86_64-linux-gnu` and point `--ngspice` to
`/tmp/possibility-ngspice/root/usr/bin/ngspice`. The package itself is an external dependency and is not redistributed
in this study. Without `--ngspice`, the runner performs only the ODE check and records ngspice as not run.

The simulator was downloaded from the official Ubuntu archive as `ngspice_42+ds-3build1_amd64.deb` and unpacked only in
`/tmp`; it was not installed system-wide. Its SHA-256 is
`466c4c06418107ceaa9c9457065b3bb71a9d9dc5ec6fef186d7de9d5208ce8db`, matched to the official noble package index.
The binary SHA-256 is `820658317b0b54035208da41936fd6871ce924036e5ea4113a4168b821b7fc45`. Dependency and package
receipts are `ngspice-package-verification.json` and `ngspice-dependency-verification.json`. The official index was
retrieved over TLS; its cryptographic repository signature was not independently checked.

## Preserved failures and corrections

- The initial environment had no ngspice executable; the two package website lookups failed. Direct official archive
  retrieval succeeded.
- The unpacked binary initially exited 127 because `libXft.so.2` was missing. Two checksum-matched Ubuntu libraries
  were unpacked alongside it. Only the simulator process's library path was changed.
- The first nominal run, `circuit_nominal_v1/`, failed **32/32** because the independent parser did not yet admit the
  generator's new isolated `EREAD` gain source. It refused the unsupported directive before numerical execution.
  The original checker bytes are retained in `failures/circuit_runner_v0_unhandled_readout.py.txt`. The corrected
  parser explicitly supports that source and rejects feedback through its output. The tolerance and scientific
  acceptance rule were not relaxed. All old input hashes and failure results remain intact.
- Ngspice reports a missing system `spinit` file and uses its SPARSE 1.3 solver. This warning is retained in every log;
  transient execution and measurements still completed successfully.

## Physical interpretation and limits

Each capacitor starts with a specified voltage. With unit capacitance and one node initialized to one, this is an
idealized unit deposited charge, followed by passive RC relaxation. It is mathematically equivalent to the state
jump from an ideal current impulse in this normalized model. It does **not** implement a finite physical pulse,
specify a charger, demonstrate switch isolation, calibrate sensor loading, or qualify a thermal heater. A real
commission would need a feasible preparation/reset or finite waveform, calibration, component tolerances, timing,
access, loading and safety qualification. Leakage and uniform conductances are stipulated model properties.

The independent integration checks the translation from generated circuit text to the mathematical response.
Correct circuit simulation cannot establish that a buyer's object belongs to this model family or that all relevant
hypotheses are included. The full campaign must keep these obligations beside any claimed enabling result.

## Source validation

Six analytic/parser controls pass and Ruff passes. Strict mypy remains failed because SciPy type stubs are absent; the original two local naming/return-type errors were corrected before fresh confirmation. The prior parser and typing versions, as well as the earlier source-freeze receipt, are preserved under `failures/`. The final nominal32 run is `circuit_nominal_v3/`, after the typing-only correction. No tolerance changed.
