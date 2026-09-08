# Numerical parameters

Every constant below is read directly from `src/hydrolex_bench.py`. Nothing in
the algorithms is left to a default that is not stated here, and there is no
randomness anywhere in the script: no seed, no sampling, no restarts.

## Environment

| Item | Value |
|---|---|
| Language | Python 3 |
| Numerical library | NumPy |
| Optimizer | SciPy `scipy.optimize.linprog`, `method="highs"` (HiGHS dual simplex/IPM) |
| Plotting | Matplotlib, `savefig.dpi = 600`, Agg backend |
| External solvers | none |
| MATPOWER / pandapower | **not used at runtime** — cited only as the distribution source of the `case33bw` data table |
| Randomness | none |

Exact interpreter and package versions of the reference run are recorded by
`src/diagnostics.py` in `results/diagnostics.json` under `environment`.

## Physical constants and scenario data

| Symbol | Value | Meaning |
|---|---|---|
| `G` | 9.80665 m s⁻² | gravitational acceleration |
| `TOL` | 1 × 10⁻⁹ | generic comparison tolerance |
| `V_BASE_KV` | 12.66 kV | feeder base voltage |
| `S_BASE_MVA` | 1.0 MVA | power base |
| `V_FLOOR` | 0.95 p.u. | bus-voltage floor, instance E |
| `S_MAX_KW` | 3200.0 kW | feeder-head supply cap S̄ (assumed deficit scenario) |
| `L` | 7000.0 m | canal reach length |
| `b` | 6.0 m | bed width (lower end of the published CER range 6.0–6.4 m) |
| `z` | 1.5 | side slope H:V (CER published) |
| `n` | 0.013 | Manning roughness (CER published) |
| `S0` | 1.0 × 10⁻⁴ | bed slope (**assumed**) |
| `Cd` | 0.6 | gate discharge coefficient (CER published) |
| `w` | 1.00 m | offtake gate width (**assumed**) |
| `amax` | 0.28 m | maximum gate opening (**assumed**) |
| `dx` | 25.0 m | nominal GVF integration step |
| `X_OFF` | 1000 … 7000 m, 1000 m spacing | offtake chainages (**assumed**) |
| `D_CANAL` | (1.0, 0.7, 1.2, 0.5, 1.4, 0.9, 0.9) m³/s | demand vector (**assumed**) |
| `Q_TAIL` | 5.0 m³/s | mandated downstream continuation Λ₀ |
| `Q_MAX` | 10.0 m³/s | head-gate capacity S̄ (assumed deficit scenario) |
| `Z_BED0` | 100.0 m | bed elevation at the head gate (arbitrary datum) |
| `Z_SUPPLY` | 101.50 m | maximum head-gate water-surface elevation (**assumed**) |

## Exact network solvers

**Instance E — backward–forward sweep (`feeder_solve`)**

| Parameter | Value |
|---|---|
| Maximum sweeps | 200 |
| Convergence test | `max |V_new − V| < 1 × 10⁻¹²` p.u. |
| Slack | bus 1 held at 1.00 ∠ 0 p.u. |
| Load model | constant power, P and Q scaled together at constant power factor |
| Loss | Σ \|I_branch\|² R_branch |

**Instance C — gradually varied flow (`canal_solve`)**

| Parameter | Value |
|---|---|
| Integrator | classical fourth-order Runge–Kutta (RK4) |
| Direction | upstream, from the downstream tail control |
| Step | `nstep = ceil(span / 25 m)` per sub-reach, uniform inside the sub-reach |
| Tail control | normal depth at `Q_TAIL`, 200 bisection steps on h ∈ [10⁻³, 50] m |
| Depth floor | 10⁻³ m (numerical guard, never active in the reported plans) |
| Sub-reach discharge | `q_reach[j] = Σ_{i≥j} q_i + Q_TAIL` |

Grid check: with no withdrawals every sub-reach carries `Q_TAIL`, so the exact
solution is uniform flow. The self-test `C_uniform_profile_err_m` measures the
departure of the RK4 profile from that exact solution over the full 7000 m and
reports 0.0 m at `dx = 25 m`, together with `C_manning_identity_err = 0.0`.

## Leximin linear programs (`leximin`)

| Parameter | Value |
|---|---|
| Formulation | sequential LP in variables `[x (n), t]`, maximize `t` s.t. `t ≤ x_i/d_i` for every free `i` |
| Outer stages | at most `n + 2` |
| Blocked-set detection | index `i` is pinned when it cannot exceed the stage optimum `t`, tested by a second LP with `t ≥ t* − 1 × 10⁻¹²` and an improvement tolerance of `1 × 10⁻⁷` |
| Pinned stages | enforced as equality rows `x_i = r_i d_i` |
| Tie-breaking | if no index is detected as blocked, all free indices are pinned at the stage optimum |
| Lexicographic comparison | `_lexkey` = sorted ratio vector rounded to 9 decimals |
| Solver | HiGHS via `linprog` |

## Instance E — floor and certification

| Parameter | Value |
|---|---|
| Floor bisection (`feeder_floor_bisect`) | 80 bisection steps on t ∈ [0, 1] |
| Acceptance in the bisection | `P_head ≤ S̄ + 1 × 10⁻⁹` kW and `V_min ≥ 0.95 − 1 × 10⁻¹²` p.u. |
| Sensitivities | central finite differences, step `e_i = max(10⁻³ · P_D,i , 10⁻⁴)` kW; at the box boundary the one-sided denominator `x⁺_i − x⁻_i` is used |
| Outer iterations (`feeder_certified`) | at most 30 |
| Damping | `λ ← λ/2`, at most 40 halvings per iteration |
| Acceptance of a candidate | exact model with `P_head ≤ S̄ + 1 × 10⁻⁶` kW and `V_min ≥ 0.95 − 1 × 10⁻⁹` p.u. |
| Stopping rule | `max |x_new − x| < 1 × 10⁻⁶` kW |
| Lower bound during the leximin stage | the certified uniform floor `t*·d` (no component may drop below it) |

## Instance C — phase-1, floor and certification

| Parameter | Value |
|---|---|
| Sensitivities | central finite differences, step `e = 1 × 10⁻⁴` m³/s |
| Exact feasibility test (`canal_exact_ok`) | `Q_head ≤ Q_MAX + 10⁻⁹`, `z_head ≤ Z_SUPPLY + 10⁻⁹`, `q_j ≤ cap_j + 10⁻⁹` for every j |
| Phase-1 rounds (`canal_floor_achievable`) | at most 30 |
| Phase-1 objective | maximize the worst linearized gate slack subject to `x ≥ t·d` |
| Phase-1 damping | `λ ← λ/2`, at most 30 halvings, abandoned when `λ < 10⁻³`; then one fixed half-step |
| Phase-1 stopping rule | `max |x_new − x| < 1 × 10⁻⁹` m³/s |
| Floor bisection (`canal_floor_bisect`) | 26 bisection steps on t ∈ [0, 1] |
| Certification outer iterations (`canal_certified`) | at most 60 |
| Certification damping | `λ ← λ/2`, at most 50 halvings |
| Certification stopping rule | `max |x_new − x| < 1 × 10⁻⁷` m³/s |
| Retained plan | the lexicographically best iterate that the **exact** model certifies |
| Uniform-ray scan (`canal_ray_scan`) | 200 points on t ∈ (0, 1], then 40 bisection steps refining the last crossing; the number of sign changes is reported, not assumed to be one |

**Status of the bisection bracket.** The upper end of the bracket produced by
`canal_floor_bisect` is a floor at which the phase-1 heuristic *failed to
certify* a plan. It is **not** a proof of infeasibility: no global
feasibility/infeasibility certificate is computed for the seven-variable
nonconvex instance. The bracket should be read as a heuristic search interval.

## Structural probe

| Probe | Definition |
|---|---|
| Canal | halve the tail withdrawal of the certified plan, re-solve exactly, report the worst violation |
| Feeder | halve the last load of the certified plan, re-solve exactly, report the minimum voltage |

A failed probe is a counterexample and disproves downward closure. A successful
probe does **not** prove downward closure; for instance E the claim rests in
addition on the monotonicity argument stated in the paper.

## Sensitivity study (`src/sensitivity.py`)

The script imports the frozen benchmark, changes `S_MAX_KW` or `Q_MAX` in
memory only, and restores them in a `finally` block. `hydrolex_bench._FLOOR_CACHE`
is cleared whenever a scenario constant changes, because that cache is keyed on
the bisection bracket and not on the scenario.

| Sweep | Grid | Quantity recomputed |
|---|---|---|
| Instance E, baseline calibration | `t = 0.10 … 1.00`, step 0.05 | η₀ from the exact solve at the uniform plan `t·d`; `r*` is **not** recomputed because the certified floor does not depend on the surrogate |
| Instance E, lossless surrogate | — | `B₀ = S̄` |
| Instance E, affine loss surrogate | least-squares fit of `loss ≈ a + b·delivered` on 19 points, `t ∈ [0.1, 1]` | `B₀ = (S̄ − a)/(1 + b)` |
| Instance E, deficit level | `S̄ = 1800 … 3800 kW`, step 200 | `r*` by `feeder_floor_bisect` at each cap |
| Instance C, deficit level | `Q_max = 7.5 … 11.5 m³/s`, step 0.5, `Q_tail = 5.0` fixed | `r_cert` by `canal_floor_bisect` at each cap |

The common abscissa of the deficit panel is the quantity-only floor `r₀`, which
is dimensionless and therefore comparable across the two media.

## Frontier scan (Figure 2)

| Parameter | Value |
|---|---|
| Grid | 197 points, `t ∈ [0.02, 1.0]`, uniform |
| Normalization | each margin divided by \|its value at the first grid point, t = 0.02\| |
