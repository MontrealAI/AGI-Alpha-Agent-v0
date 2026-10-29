# Generalist control API

`direct_solver.py` exposes `solve(target, cache=False) -> artifact`. It is an actual standalone implementation written by the same frontier model as the campaign root. It directly constructs a conventional fixed-route LP and uses installed SciPy/HiGHS. It imports no new structural-transfer module, runtime, engine or adaptation code.

Invocation:

```sh
python campaign/transfer_v3/controls/generalist/direct_solver.py --target TASK.json --output ARTIFACT.json
```

With no arguments it reads one JSON task from stdin and writes its JSON artifact to stdout. The artifact implements `agialpha/eadarp-certificate/v1`; hashes are SHA256 over UTF-8 `json.dumps(target, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. The raw instance's original decoded text is hashed separately without newline normalization.

The fixed route must serve every pickup and dropoff once, in pickup-before-dropoff order, respect vehicle origin/destination and seating, and visit charging stations without passengers. The LP has service-start minutes, charging minutes and arrival kWh at each route position; raw Uber travel matrix entries are multiplied by two. It uses finite independent base bounds T∈[0,H], C∈[0,H] at stations or C=0 elsewhere, and B∈[0,Q]. Updated windows are separate constraints: low=rawLow+shift and high=low+(rawHigh−rawLow)×scale. It enforces service/travel/charge timing, energy conservation, departure battery cap, initial battery, final fractional reserve and minimum/maximum ride times. Travel, charge-rate and consumption multipliers are separate typed quantities.

`FEASIBLE` requires a returned primal schedule passing an original-Decimal row replay at tolerance 1e-7. Its reported objective includes weighted drive and excess ride, excluding the 1e-9 charge-time tie break. An infeasible solver status alone is insufficient: `INFEASIBLE` requires a nonnegative dual witness whose original-Decimal weighted rows contradict the finite base bounds using the independent checker's bounded-residual criterion. Unknown, invalid or numerically unproved cases return `UNRESOLVED`. The campaign's separate checker supplies actual independent acceptance.

Predeclared chronological cache: the process-local exact-task cache is optional. It may store only an already computed artifact under the complete canonical task hash and returns deep copies for exact subsequent repeats. It never uses approximate matches, future labels, expected statuses or hidden tasks. New task hashes run the fixed conventional solver. No future-case-triggered code repair, learned feature, uncertainty model or shared-charger successor is prebuilt.

Development used only the public u2-16-0.7 raw source instance and its published routes. Seven tests cover the disclosed feasible case, the already-public no-charger failure, an explicit same-source window/horizon contradiction, malformed identity/update/route refusals and exact chronological cache behavior. The public prior checker was imported only in the development comparison; it is not imported by production control. No held instance or label was consumed.

This is a certificate for the declared deterministic eADARP linear model. It does not certify battery physics, routing optimality across orders, dispatch safety, forecast uncertainty, charger contention or operational readiness.
