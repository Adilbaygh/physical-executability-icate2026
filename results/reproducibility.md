# Reproducibility record

## Environments in which this package has been executed

`src/diagnostics.py` imports the frozen benchmark module and re-runs its
gradually-varied-flow machinery. It was executed in two independent
environments that share no operating system, no interpreter version and no
library version:

| | Environment A | Environment B |
|---|---|---|
| Operating system | Linux 6.18 (x86_64, glibc 2.39) | Windows 10 10.0.19045 (AMD64) |
| CPython | 3.11.15 | 3.13.5 |
| NumPy | 2.4.4 | 2.3.5 |
| SciPy | 1.16.3 | 1.17.0 |
| Matplotlib | 3.10.9 | 3.10.8 |
| Date | 2026-09-08 | 2026-09-08 |

The two environments therefore differ in the operating system, the interpreter
minor version, and both numerical library versions.

## Agreement

The two environments produced **identical** values to every digit printed:

```
quantity_only_plan                 F_max = 0.3049 at x = 4975 m
certified_plan                     F_max = 0.3011 at x =  975 m
largest_executable_uniform_plan    F_max = 0.2863 at x = 2975 m
max over the reported plans        F_max = 0.3049   subcritical: True

grid refinement of the certified plan (max depth change vs dx = 25 m):
  dx = 25.000 m   0.000e+00 m
  dx = 12.500 m   0.000e+00 m
  dx =  6.250 m   0.000e+00 m
  dx =  3.125 m   0.000e+00 m
```

This is stronger than the reproducibility claim made in the manuscript, which
reports agreement between two operating systems only: agreement also holds
across two NumPy releases and two SciPy releases, so the results do not depend
on a particular BLAS build, a particular HiGHS build or a particular
interpreter version.

`results/diagnostics.json` in this package is the file written by environment
B, the machine on which all published results were produced.

## Agreement of the sensitivity study

`src/sensitivity.py` was subsequently executed in the same two environments. It
is a considerably harder test than the diagnostics: it re-runs the feeder floor
bisection at eleven supply caps, the canal floor bisection at nine head-gate
capacities and the exact feeder solve at nineteen calibration points, so it
exercises the HiGHS linear-programming path several hundred times rather than
the gradually-varied-flow integrator alone.

The two environments produced `results/sensitivity.json` files that are
**identical after normalizing the line ending** — Windows writes CRLF, Linux
writes LF — and therefore identical in every stored digit, not merely in the
digits printed to the console:

```
sha/md5 of the LF-normalized payload   identical
numeric differences over all 3 sweeps  0
environment-dependent fields           none (the file stores no version block)
```

This matters for the reported price. HiGHS ships inside SciPy, so the two runs
used two different builds of the optimizer (SciPy 1.16.3 and 1.17.0) on two
different BLAS stacks, and still selected the same vertex at every stage of
every leximin ladder, including the two sub-threshold canal capacities where
the sequential-linearization heuristic certifies `r_cert = 0.552218` at
`Q_max = 9.0 m³/s` rather than the frozen `0.553736`. That value is a property
of the heuristic, not of the floating-point environment.

## How to repeat the check

```bash
cd src
python diagnostics.py          # writes ../results/diagnostics.json
```

The script prints the environment block first, so the comparison above can be
extended by anyone who runs it. Nothing in the benchmark is seeded, sampled or
timed, so any difference between two runs would indicate a genuine numerical
discrepancy rather than nondeterminism.
