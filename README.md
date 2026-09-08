# The Price of Physical Executability — reproducibility package

Deterministic benchmark accompanying the ICATE 2026 conference paper

> **The Price of Physical Executability in Fair Resource Allocation on Radial
> Supply Networks**
> A. Kudaybergenov, M. Kazimbetova, G. Ametova, J. Ispanova, B. Absametov and
> M. Qudaynazarov.
> II International Scientific and Practical Conference *Advanced Technologies in
> Engineering* (ICATE 2026), Tashkent State Transport University, 25–26 November
> 2026. To appear in AIP Conference Proceedings.

Every number, table entry and figure in the paper is produced by
`src/hydrolex_bench.py`. Nothing is typed by hand.

---

## What the benchmark computes

A lexicographic max-min (leximin) allocation is solved twice on each of two
physically unrelated radial media:

| | Instance E | Instance C |
|---|---|---|
| Medium | IEEE 33-bus radial distribution feeder | prismatic trapezoidal canal reach, 7 gated offtakes |
| Transported quantity | active power, kW | discharge, m³/s |
| Potential | bus voltage magnitude, p.u. | flow depth at the offtake, m |
| Exact network solve | backward–forward sweep | RK4 integration of the gradually-varied-flow equation |
| Feasible set downward closed | yes (under the monotonicity argument of the paper) | no (numerical counterexample) |

The two solves are (i) on a **quantity-only** feasible set, in which the network
is compressed into one scalar budget, and (ii) on a **certified** feasible set,
in which every candidate plan is evaluated through the exact nonlinear network
model. The *price of physical executability* is the relative loss of the
egalitarian floor between the two.

---

## Contents

```
src/hydrolex_bench.py            the benchmark — one deterministic script
src/diagnostics.py               non-invasive diagnostics (environment, Froude profile, grid check)
src/sensitivity.py               sensitivity of the price to the baseline and to the deficit level
results/hydrolex_bench_results.json   reference output of the benchmark
results/diagnostics.json              output of the diagnostics script
results/sensitivity.json              output of the sensitivity script
results/fig4_sensitivity.png          sensitivity figure
results/reproducibility.md            the environments in which this package has been run
results/fig1_media.png                Figure 1 of the paper
results/fig2_frontier.png             Figure 2 of the paper
results/fig3_convergence.png          Figure 3 of the paper
PARAMETERS.md                    every numerical parameter of the algorithms
MAPPING.md                       every published number → its source in the JSON
docs/data-and-code-availability.md    statement text for the manuscript
requirements.txt                 dependencies
CITATION.cff, LICENSE, .zenodo.json
```

`src/hydrolex_bench.py` is **frozen**: it is byte-identical to the script that
produced the published results. `src/diagnostics.py` imports it as a module and
never modifies it.

---

## How to run

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt

cd src
python hydrolex_bench.py        # writes hydrolex_bench_results.json and fig1..fig3.png
python diagnostics.py           # writes ../results/diagnostics.json
python sensitivity.py           # writes ../results/sensitivity.json and fig4
```

`sensitivity.py --quick` runs the same study on reduced grids for a fast check.
Neither `diagnostics.py` nor `sensitivity.py` modifies the benchmark: both
import it as a frozen module, change its constants in memory only, and restore
them.

Runtime is a few minutes on a laptop. The script needs no data files, no
network access and no random seed: there is no randomness anywhere in it.

### What you should see

`hydrolex_bench.py` first runs four self-tests and aborts if any fails:

| Self-test | Threshold |
|---|---|
| Feeder loss vs the published IEEE 33-bus base case | < 0.05 kW |
| Feeder minimum voltage vs the published base case | < 5 × 10⁻⁵ p.u. |
| GVF integration preserves uniform flow over 7000 m | < 10⁻⁴ m |
| Leximin returns the uniform ratio under a pure capacity constraint | < 10⁻⁷ |

It then prints the headline results:

```
instance E   decoupled_floor 0.816811   certified_floor 0.594681   PoPE 27.195 %
instance C   decoupled_floor 0.757576   certified_floor 0.553736   PoPE 26.907 %
```

Every plan the script reports is re-evaluated through the exact model and
asserted feasible before it is printed.

---

## Reproducibility status

* The script is deterministic — no seed, no sampling, no restarts — and two
  runs under different operating systems produced byte-identical output.
* The diagnostics have additionally been reproduced across two operating
  systems, two CPython minor versions and two NumPy/SciPy releases with
  identical results to every printed digit; see `results/reproducibility.md`.
* The sensitivity study has been reproduced in the same two environments, and
  the two `results/sensitivity.json` files agree in every stored digit — the
  files differ only in the line ending. Two different HiGHS builds therefore
  select the same vertex at every stage of every leximin ladder.
* All algorithm parameters are listed in `PARAMETERS.md`; none of them is
  hidden inside the narrative of the paper.
* The exact interpreter and library versions of the reference run are recorded
  in `results/diagnostics.json` (`environment` block).
* The maximum Froude number over the reported plans is **0.3049** (subcritical
  everywhere), and the offtake depths are unchanged when the integration step
  is refined from 25 m to 3.125 m.

### Scope of the claims

Instance E is reported under a monotonicity argument for the radial
constant-power load-flow model; instance C is not downward closed and its floor
is obtained by a sequential-linearization heuristic with **exact feasibility
certification but no global optimality certificate**. A certified plan proves
that the true egalitarian floor is *at least* the reported value, hence the
reported price is an **upper bound** on the true price. Readers should treat the
canal price accordingly.

---

## Data provenance

**Instance E.** Line and load table of the IEEE 33-bus feeder of Baran & Wu
(1989), as distributed with MATPOWER and pandapower under the name `case33bw`
(32 radial branches; the five tie branches are normally open and excluded).
MATPOWER and pandapower are cited as the source of this table only — they are
**not** dependencies of this package, which implements its own
backward–forward sweep.

**Instance C.** Section geometry, Manning roughness and gate discharge
coefficient are taken from the published Canale Emiliano Romagnolo values of
Luppi et al., *Water* **10**, 1017 (2018), doi:10.3390/w10081017 (CC BY 3.0);
the 6.0 m bed width is the lower end of the range reported there. The bed
slope, gate dimensions, offtake spacing, continuation flow, head-gate level
limit and demand vector are **declared design assumptions** and are not
reported in that source. The reach is therefore a controlled synthetic
benchmark informed by published CER parameters, not a calibrated model of the
CER pilot segment.

---

## Citing

Please cite both the paper and this package; see `CITATION.cff`.

## Licence

Creative Commons Attribution 4.0 International (CC BY 4.0) for the whole
package — code, figures and result files alike. See `LICENSE` for the
attribution string the authors ask you to use, and for the terms of the two
third-party inputs (the `case33bw` table and the published CER parameters).
