# Where every published number comes from

Keys refer to `results/hydrolex_bench_results.json`, which
`src/hydrolex_bench.py` writes on every run. Values shown are the reference
run. Rounding to the precision printed in the paper is the only post-processing
applied.

## Table 2 — decoupled and certified plans

| Table 2 row | Instance E | key | Instance C | key |
|---|---|---|---|---|
| Egalitarian floor, quantity-only plan | 0.8168 | `instance_E.decoupled_floor` = 0.816811 | 0.7576 | `instance_C.decoupled_floor` = 0.757576 |
| Egalitarian floor, certified plan | 0.5947 | `instance_E.certified_floor` = 0.594681 | 0.5537 | `instance_C.certified_floor` = 0.553736 |
| Price of physical executability, % | 27.20 | `instance_E.PoPE_percent` = 27.195 | 26.91 | `instance_C.PoPE_percent` = 26.907 |
| Highest service ratio, certified plan | 0.5947 | `instance_E.certified_max_ratio` | 1.0000 | `instance_C.certified_max_ratio` |
| Demand-weighted mean service ratio, certified plan | 0.5947 | `instance_E.certified_mean_ratio` | 0.7576 | `instance_C.certified_mean_ratio` |
| Total delivered, quantity-only plan | 3034.5 kW | `decoupled_Phead_kW − decoupled_loss_kW` = 3165.927 − 131.475 | 5.000 m³/s | `decoupled_floor × 6.6` |
| Total delivered, certified plan | 2209.2 kW | `instance_E.certified_delivered_kW` = 2209.238 | 5.000 m³/s | `instance_C.certified_delivered_m3s` |
| Binding constraint | bus voltage | `instance_E.binding` | gate command head | `instance_C` gate slack = 0 |
| Largest executable uniform ratio | 0.5947 | `instance_E.certified_floor` (E is uniform) | 0.5472 | `instance_C.best_uniform_feasible_ratio` = 0.547198 |
| Gain of leximin over uniform derating, % | 0.00 | — (certified plan is the uniform plan) | 1.19 | `instance_C.leximin_gain_over_uniform_percent` = 1.1949 |

Note. `certified_mean_ratio` is computed as total delivered ÷ total demand,
i.e. the **demand-weighted** mean. For instance E all service ratios are equal,
so the weighted and unweighted means coincide; for instance C the unweighted
mean of the seven ratios is 0.7941.

## Materials and Methods — instance E

| Statement in the paper | Value | Source |
|---|---|---|
| total demand | 3715 kW, 2300 kvar | `self_tests.E_base_load_kW`; sum of `LOAD_KW` reactive column |
| source cap S̄ | 3200 kW | `instance_E.S_max_kW` |
| head power at full demand | 3917.7 kW | `self_tests.E_base_Phead_kW` = 3917.6771 |
| conveyance efficiency η₀ | 0.948266 | `instance_E.eta0` |
| base-case total loss | 202.677 kW | `self_tests.E_base_loss_kW` = 202.6771 |
| base-case minimum voltage | 0.913090 p.u. at bus 18 | `self_tests.E_base_Vmin_pu`, `E_base_Vmin_bus` |
| deviation from the Newton–Raphson reference | 1.3 × 10⁻⁴ kW, 4.8 × 10⁻⁷ p.u. | `self_tests.E_loss_err_kW` = 0.00013, `E_Vmin_err_pu` = 4.8e-07 |

## Materials and Methods — instance C

| Statement in the paper | Value | Source |
|---|---|---|
| reach length, offtake spacing | 7000 m, 1000 m | `CANAL["L"]`, `X_OFF` |
| bed width, side slope, Manning n, C_d | 6.0 m, 1.5:1, 0.013, 0.6 | `CANAL` |
| bed slope | 1.0 × 10⁻⁴ | `CANAL["S0"]` (assumed) |
| continuation, head-gate capacity, demand | 5.0, 10.0, 6.6 m³/s | `instance_C.Q_tail_m3s`, `Q_max_m3s`, `demand_m3s` |
| demand vector | (1.0, 0.7, 1.2, 0.5, 1.4, 0.9, 0.9) m³/s | `D_CANAL` |
| gate width, maximum opening | 1.00 m, 0.28 m | `CANAL["w"]`, `CANAL["amax"]` |
| head-gate level limit above the bed | 1.50 m | `Z_SUPPLY − Z_BED0` |
| largest Froude number | **0.3049** | `diagnostics.json.froude.max_over_reported_plans` |

The Froude number is **not** written by `hydrolex_bench.py`. It is computed
without modifying the benchmark by `src/diagnostics.py`, which imports the
frozen module and evaluates F at every RK4 node of the full water-surface
profile of every plan the paper reports:

| Plan | F_max | chainage |
|---|---|---|
| quantity-only plan | 0.3049 | x = 4975 m |
| certified plan | 0.3011 | x = 975 m |
| largest executable uniform plan | 0.2863 | x = 2975 m |
| **maximum over the reported plans** | **0.3049** | subcritical everywhere |

> **Correction to the submitted manuscript.** The submitted text states that
> "the largest Froude number being 0.31". The value produced by the frozen
> model is **0.3049**, which rounds to **0.30**. The revised manuscript should
> read 0.30, or state the bound as "below 0.31". The physical claim — the flow
> is subcritical in every reported plan, so the denominator of Eq. (8) is
> bounded away from zero — is unaffected.

## Grid sensitivity of the gradually-varied-flow integration

`src/diagnostics.py` recomputes the certified-plan profile with the RK4 step
halved repeatedly, changing only `CANAL["dx"]` in memory and restoring it
afterwards:

| step dx | maximum change of the offtake depths vs dx = 25 m |
|---|---|
| 25 m | — (reference) |
| 12.5 m | 0.0 m |
| 6.25 m | 0.0 m |
| 3.125 m | 0.0 m |

The reported depths and gate capacities are therefore independent of the
integration step at the precision the paper prints.

## Results

| Statement in the paper | Value | Source |
|---|---|---|
| quantity-only plan drives bus 18 to … | 0.9301 p.u. | `instance_E.decoupled_Vmin_pu` = 0.930096 |
| … below the limit by | 0.0199 p.u. | `instance_E.decoupled_voltage_violation_pu` = 0.019904 |
| unused supply at the feeder head | 34 kW | `S_max_kW − decoupled_Phead_kW` = 3200 − 3165.927 |
| gates commanded above capacity | 2 of 7 | `instance_C.decoupled_gates_infeasible` |
| worst overdraw, at offtake 5 | 0.2879 m³/s | `instance_C.decoupled_max_gate_overdraw_m3s`, `decoupled_worst_gate` |
| halving one feeder load leaves V_min at | 0.9504 p.u. | `structural_probe.feeder_cut_one_load_Vmin_pu` = 0.950385 |
| halving the tail withdrawal violates by | 0.0100 m³/s | `structural_probe.canal_cut_tail_max_violation_m3s` = 0.009959 |

## Discussion

| Statement in the paper | Value | Source |
|---|---|---|
| total delivery falls from … to … | 3034 → 2209 kW | as in Table 2 |
| certified canal ratios range | 0.5537 – 1.0000 | `instance_C_detail[*].ratio` |
| offtakes exactly on their gate capacity | 3, 5, 6, 7 | `instance_C_detail`: `certified_m3s == cap_m3s` |
| offtake served in full | 4 | `instance_C_detail[3].ratio` = 1.0 |
| largest executable uniform ratio vs certified floor | 0.5472 vs 0.5537, gain 1.19 % | `best_uniform_feasible_ratio`, `certified_floor`, `leximin_gain_over_uniform_percent` |
| the two prices | 27.20 %, 26.91 % | as in Table 2 |

## Figures

| Figure | Produced by | Data |
|---|---|---|
| Figure 1 `results/fig1_media.png` | `make_figures`, panels (a)/(b) | bus voltages of the quantity-only plan; commanded withdrawals vs gate capacity |
| Figure 2 `results/fig2_frontier.png` | `make_figures` | `frontier` block (197 points, t ∈ [0.02, 1]) |
| Figure 3 `results/fig3_convergence.png` | `make_figures` | `convergence.phase1_at_floor`, `phase1_above_floor`, `bracket` |

## Sensitivity study — `src/sensitivity.py` → `results/sensitivity.json`

### Baseline dependence (instance E)

The quantity-only budget of instance E is B₀ = η₀ S̄, so the reported price
depends on the operating point at which η₀ is calibrated. The certified floor
r\* = 0.594681 is a property of the medium and does **not** move.

| η₀ calibrated at load level t | η₀ | r₀ | price, % |
|---|---|---|---|
| 0.10 | 0.995216 | 0.857252 | 30.63 |
| 0.30 | 0.985417 | 0.848811 | 29.94 |
| 0.50 | 0.975285 | 0.840084 | 29.21 |
| 0.70 | 0.964788 | 0.831042 | 28.44 |
| 0.90 | 0.953884 | 0.821650 | 27.62 |
| **1.00 — the convention used in the paper** | **0.948266** | **0.816811** | **27.20** |
| lossless surrogate, η₀ = 1 | 1.000000 | 0.861373 | 30.96 |
| affine loss surrogate, loss ≈ a + b·delivered | — | 0.825105 | 27.93 |

**Range over legitimate baselines: 27.20 – 30.96 %.** The convention adopted in
the paper — calibration at full demand — is the **minimum** of this family, so
the published figure is the most conservative member: any other legitimate
quantity-only surrogate makes the price larger, not smaller.

Instance C admits no such freedom: B₀ = S̄ − Λ₀ = 10.0 − 5.0 = 5.0 m³/s
exactly, because the continuation is a fixed commitment rather than a
calibrated efficiency.

### Deficit dependence (both media)

The paper exercises each medium at one deficit scenario. Sweeping the source
cap, with η₀ held at the paper's full-demand calibration for instance E:

| Instance E, S̄ (kW) | r₀ | r\* | price, % | binding |
|---|---|---|---|---|
| 1800 | 0.459456 | 0.473215 | −3.00 | source cap |
| 2000 | 0.510507 | 0.524375 | −2.72 | source cap |
| 2200 | 0.561557 | 0.575246 | −2.44 | source cap |
| 2400 | 0.612608 | 0.594681 | 2.93 | bus voltage |
| 2600 | 0.663659 | 0.594681 | 10.39 | bus voltage |
| 2800 | 0.714709 | 0.594681 | 16.79 | bus voltage |
| 3000 | 0.765760 | 0.594681 | 22.34 | bus voltage |
| **3200 — the paper** | **0.816811** | **0.594681** | **27.20** | bus voltage |
| 3400 | 0.867861 | 0.594681 | 31.48 | bus voltage |
| 3600 | 0.918912 | 0.594681 | 35.28 | bus voltage |
| 3800 | 0.969963 | 0.594681 | 38.69 | bus voltage |

| Instance C, Q_max (m³/s) | r₀ | r_cert | price, % | binding |
|---|---|---|---|---|
| 7.5 | 0.378788 | 0.378788 | 0.00 | head-gate discharge |
| 8.0 | 0.454545 | 0.454545 | 0.00 | head-gate discharge |
| 8.5 | 0.530303 | 0.530303 | 0.00 | head-gate discharge |
| 9.0 | 0.606061 | 0.552218 | 8.88 | gate command head |
| 9.5 | 0.681818 | 0.553736 | 18.79 | gate command head |
| **10.0 — the paper** | **0.757576** | **0.553736** | **26.91** | gate command head |
| 10.5 | 0.833333 | 0.553736 | 33.55 | gate command head |
| 11.0 | 0.909091 | 0.553736 | 39.09 | gate command head |
| 11.5 | 0.984848 | 0.553736 | 43.77 | gate command head |

### Threshold deficit

In both media the certified floor stops moving once the **potential** rather
than the quantity becomes the binding constraint, and from that point the
entire variation of the price comes from r₀ alone. The threshold follows from
values already published in the paper:

| Medium | Threshold | Derivation |
|---|---|---|
| E | S̄ = **2276.7 kW** | the head power of the certified plan, `instance_E.certified_Phead_kW`; above it the 0.95 p.u. voltage floor binds and r\* is frozen at 0.594681 |
| C | Q_max = **8.655 m³/s** | Q_tail + r_cert · Σd = 5.0 + 0.553736 × 6.6; above it the gate command head binds and r_cert is frozen at 0.553736 |

Below the threshold the price is zero or slightly negative: the quantity-only
budget is itself tighter than the physically executable floor, so the decoupled
plan happens to be executable. In instance E the small negative values arise
because η₀ calibrated at full demand understates the efficiency at light load,
which makes the surrogate conservative rather than unsafe.

**Consequence for the paper.** The price is not a constant of a medium. It is
zero below a threshold deficit, and above that threshold it grows monotonically
with the severity of the deficit, because the physical floor is frozen while
the quantity-only floor keeps rising. The two published values, 27.20 % and
26.91 %, are point values on those curves.
