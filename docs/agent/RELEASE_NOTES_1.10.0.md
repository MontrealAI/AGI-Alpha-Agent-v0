# Version 1.10.0 — Decisions that respect the operation

This audit corrects two operational mismatches in the Decision Studio. Service capacity previously
reused replenishment arithmetic. Delivery planning minimized makespan before considering missed
commitments. Both could produce a mathematically reproducible result that answered the wrong question.

The service desk now converts forecast cases into productive workload and a staffing plan for every
shift. It accounts for handling time, shrinkage, occupancy, demand reserve, existing staff, additional
staff caps, incremental cost and a backlog-clearance target. Backlog carries forward; spare time does
not. Uncovered shifts stay on HOLD. Demand shocks expose both their cost and remaining shortfalls.
The default constructed case proposes additional staffing costing 7,920 USD and clears its backlog;
a 20% demand shock exceeds available coverage.

Delivery and launch planning now minimize total job lateness plus delivery-window overrun, then
makespan. Every feasible priority order beats every deadline-violating order. A commitment table shows
each completion, due time and slack. The default factory case reduces total job lateness from 48 to 20
hours, and the launch case from 12 to 3 hours; both correctly remain on HOLD. This is exhaustive only
within the documented serial scheduling policy, not a global job-shop infeasibility proof.

The audit also bounds repeated prerequisite traversal, requires string IDs, measures input limits in
UTF-8 bytes and prevents partial numeric matches inside grouped or scientific-notation evidence.
Table paging, additions and removals retain keyboard focus. Supporting tables and stress-test units
are visible in the interface. Reports identify their calculation version; existing 1.9.0 dossiers
continue to replay against the archived policy, visibly labeled, rather than silently changing results.

The release package now includes the Decision Studio method guide. Publication requires the full set
of public Studio journeys for the exact packaged commit and version, including staffing failure,
archived replay, real downloaded-dossier execution, mobile, accessibility and offline checks.
See the [method guide](DECISION_STUDIO.md) for bounds and a worked staffing example.

Constructed data remains labeled. These bounded decision tools require operational review and do not
submit orders, dispatch equipment, schedule staff or promote capabilities automatically. The original
198-page manuscript, historical implementations and signed evidence protocols remain intact.
