# Selected-domain source addendum: covariance and Lyapunov certification

The selected executable domain is stable linear-system covariance and disturbance-energy analysis. Thermal and manufacturing opportunities remain shortlist alternatives because current owners already work those lanes.

## What the sources establish

- SciPy supplies a standard dense Bartels–Stewart Lyapunov solver. M.E.S.S. and integrated Krylov–ADI are established stronger alternatives for large sparse low-rank systems.
- Squared H2 equals output variance/power under the specified unit white-noise model. It is an existing control-engineering objective.
- A residual certificate bounds numerical error for the stated model under explicit assumptions. It does not validate a physical plant or establish robust safety.
- Related controls work has commercial precedents. No matched price or customer demand for the proposed report was found. Use transparent human-hours/rate estimates.

## Conditional numerical certificate

For sym(A) <= -alpha I, alpha > 0, covariance X solves AX+XA^T+BB^T=0. With R=A Xhat+Xhat A^T+BB^T, E=X-Xhat satisfies E=integral exp(At)R exp(A^T t)dt. Contraction gives ||E||F <= ||R||F/(2alpha). For J=tr(CXC^T), |J-Jhat| <= ||C^TC||F ||R||F/(2alpha). This is a standard consequence, not new algorithmic novelty. Stability alone is insufficient for this particular bound.

## Price and wage evidence

BLS reports May 2025 U.S. electrical-engineer median wage USD120,630 annually, including USD105,780 in engineering services. A 2080-hour conversion gives USD58/hour, but consultancy overhead, utilization and margins are extra assumptions. Job Bank gives Québec automation-engineer wages CAD35.00/53.85/78.21 low/median/high, from 2023–24 data. ApICS advertises on-site control stability service at $180/hour plus travel and overtime; that scope differs from an offline report. A USD150/hour and 4–12-hour report reference is a modeled estimate, not a sourced market quote.

## Opened primary references

### scipy_lyapunov

SciPy community. scipy.linalg.solve_continuous_lyapunov (2026).

https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_continuous_lyapunov.html

Solves AX+XA^H=Q using Bartels-Stewart and LAPACK TRSYL. Establishes available competent dense baseline; not asymptotic sparse best method.

Reference turn9view0; accessed 2026-10-27.

### mess

Max Planck Institute for Dynamics of Complex Technical Systems. M.E.S.S. (Matrix Equation Sparse Solver) (2026).

https://www.mpi-magdeburg.mpg.de/projects/mess

Established large sparse Lyapunov/Riccati and model reduction package; MATLAB/C implementations and Python bindings. Existing ordinary acquisition alternative.

Reference turn9view1; accessed 2026-10-27.

### mess_paper

Peter Benner; Martin Köhler; Jens Saak. Matrix Equations, Sparse Solvers: M-M.E.S.S.-2.0.1 — Philosophy, Features and Application for (Parametric) Model Order Reduction (2020).

https://arxiv.org/abs/2003.02088

Low-rank matrix equations in large-scale LTI/MOR. Residual-based LR-ADI with automatic shifts. Parametric examples are built from package routines; v2.0.1 did not directly support PMOR by default. Do not call parameter reuse a new algorithm.

Reference turn9view3; accessed 2026-10-27.

### krylov_adi

Peter Benner; Davide Palitta; Jens Saak. On an integrated Krylov-ADI solver for large-scale Lyapunov equations (2022).

https://link.springer.com/article/10.1007/s11075-022-01409-5

Established LR-ADI extended-Krylov alternative, reuse of one approximation space across shifted solves, shift-selection costs and assumptions. Published algorithm is stronger than a naive repeated dense baseline.

Reference turn12view1; accessed 2026-10-27.

### inexact_lyapunov

Patrick Kürschner; Melina A. Freitag. Inexact methods for the low rank solution to large scale Lyapunov equations (2019).

https://arxiv.org/abs/1809.06903

Primary literature for practical inexact low-rank Lyapunov solvers and residual stopping; no commercial evidence.

Reference turn13view2; accessed 2026-10-27.

### mathworks_h2

MathWorks. norm: Norm of linear model (2026).

https://www.mathworks.com/help/control/ref/dynamicsystem.norm.html

H2 squared equals steady-state expected output squared magnitude under unit white-noise input. H2 infinite for unstable systems or continuous systems with nonzero feedthrough. Existing ordinary software computes it.

Reference turn12view2; accessed 2026-10-27.

### mathworks_variance

MathWorks. TuningGoal.WeightedVariance: Frequency-weighted H2 norm constraint for control system tuning (2026).

https://www.mathworks.com/help/control/ref/tuninggoal.weightedvariance.html

Frequency-weighted H2 objective supports tuning stochastic disturbances including colored noise/wind gusts and LQG-like objectives. Source validates use-case mechanism, not customer demand.

Reference turn12view0; accessed 2026-10-27.

### apics_prices

ApICS LLC. Industrial Automation and Motion Control Services and Case Studies (2026).

https://apicsllc.com/apics/Services.html

Vendor advertises on-site industrial control stability support at $180/hr up to eight hours, overtime/travel extra; negotiated project prices not disclosed. Scope differs from offline covariance reports; advertised prices and self-reported case studies are not independently verified sales.

Reference turn11view0; accessed 2026-10-27.

### bls_electrical

U.S. Bureau of Labor Statistics. Electrical and Electronics Engineers: Occupational Outlook Handbook (2026).

https://www.bls.gov/ooh/architecture-and-engineering/electrical-and-electronics-engineers.htm

May 2025 median U.S. electrical-engineer annual wage USD120,630; engineering-services sector USD105,780. Wage is not a consultancy billing rate or the price of the proposed report.

Reference turn13view0; accessed 2026-10-27.

### jobbank_automation

Government of Canada Job Bank. Automation Engineer in Québec: Wages (2025).

https://www.jobbank.gc.ca/marketreport/wages-occupation/296279/QC

Updated 2025-11-19 from 2023–24 LFS: Québec low/median/high hourly wages 35.00/53.85/78.21 Canadian dollars. Wages only; not contractor or customer prices.

Reference turn13view1; accessed 2026-10-27.
