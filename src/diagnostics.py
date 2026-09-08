"""
Non-invasive diagnostics for the ICATE 2026 benchmark.

This script NEVER modifies `hydrolex_bench.py`. It imports it as a frozen
module and reuses its own functions and constants, so anything reported here is
computed by exactly the code that produced the published results.

It answers two questions the manuscript leaves open:

  1. Environment. Which interpreter and library versions produced the reference
     run? `hydrolex_bench.py` prints this to stdout but does not store it.

  2. Froude number. The manuscript states that the flow stays subcritical in
     every reported plan and quotes the largest Froude number. `canal_solve`
     computes F internally (inside `_dhdx`) but never returns it, so the value
     is not recoverable from `hydrolex_bench_results.json`. Here F is evaluated
     at every integration node of the full water-surface profile, not only at
     the offtake sections.

  3. Grid sensitivity. The GVF profile is recomputed with the integration step
     halved repeatedly, to show that the reported depths and gate capacities do
     not depend on the 25 m step. The step is changed only in memory, through
     the module's own CANAL dictionary, and is restored afterwards.

Run:  python diagnostics.py
Writes: ../results/diagnostics.json
"""

import json
import platform
import sys
from pathlib import Path

import numpy as np

import hydrolex_bench as hb

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"


# ---------------------------------------------------------------------------
# 1. Environment
# ---------------------------------------------------------------------------
def environment():
    env = {
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "numpy": np.__version__,
    }
    for name in ("scipy", "matplotlib"):
        try:
            env[name] = __import__(name).__version__
        except Exception:
            env[name] = "not installed"
    env["lp_solver"] = "scipy.optimize.linprog, method='highs'"
    env["random_seed"] = None
    env["notes"] = (
        "MATPOWER and pandapower are not imported; they are cited only as the "
        "distribution source of the case33bw data table."
    )
    return env


# ---------------------------------------------------------------------------
# 2. Froude number along the whole profile
# ---------------------------------------------------------------------------
def froude_profile(q):
    """Replay `hydrolex_bench.canal_solve` step by step, recording the Froude
    number at every RK4 node. The integration loop below mirrors canal_solve
    exactly and uses the module's own _dhdx, _area, _top and constants."""
    q = np.asarray(q, float)
    n_off = len(q)
    q_reach = np.array([q[j:].sum() + hb.Q_TAIL for j in range(n_off)])

    def fr(h, qq):
        return float(np.sqrt(qq * qq * hb._top(h) / (hb.G * hb._area(h) ** 3)))

    h = hb.normal_depth(max(hb.Q_TAIL, 1e-6))
    x_nodes = np.concatenate(([0.0], hb.X_OFF))
    samples = []                      # (chainage_m, depth_m, discharge, F)
    x_here = float(x_nodes[-1])
    samples.append((x_here, float(h), float(q_reach[-1]), fr(h, q_reach[-1])))

    for j in range(n_off - 1, -1, -1):
        qj = max(q_reach[j], 1e-6)
        span = x_nodes[j + 1] - x_nodes[j]
        nstep = max(int(np.ceil(span / hb.CANAL["dx"])), 1)
        step = span / nstep
        for _ in range(nstep):
            k1 = hb._dhdx(h, qj)
            k2 = hb._dhdx(max(h - 0.5 * step * k1, 1e-3), qj)
            k3 = hb._dhdx(max(h - 0.5 * step * k2, 1e-3), qj)
            k4 = hb._dhdx(max(h - step * k3, 1e-3), qj)
            h = max(h - step * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0, 1e-3)
            x_here -= step
            samples.append((x_here, float(h), float(qj), fr(h, qj)))

    arr = np.array(samples)
    k = int(np.argmax(arr[:, 3]))
    return {
        "nodes": int(len(arr)),
        "F_max": round(float(arr[k, 3]), 6),
        "at_chainage_m": round(float(arr[k, 0]), 1),
        "at_depth_m": round(float(arr[k, 1]), 6),
        "at_discharge_m3s": round(float(arr[k, 2]), 6),
        "F_at_offtake_sections_only": round(
            float(max(fr(hh, qq) for hh, qq in
                      zip(hb.canal_solve(q)[0], q_reach))), 6),
    }


# ---------------------------------------------------------------------------
# 3. Grid sensitivity of the GVF integration
# ---------------------------------------------------------------------------
def grid_refinement(q, steps=(25.0, 12.5, 6.25, 3.125)):
    original = hb.CANAL["dx"]
    out = []
    try:
        ref = None
        for dx in steps:
            hb.CANAL["dx"] = dx
            h, z_head, _ = hb.canal_solve(q)
            cap = hb.gate_cap(h)
            row = {
                "dx_m": dx,
                "z_head_m": round(float(z_head), 6),
                "depths_m": [round(float(v), 6) for v in h],
                "gate_capacity_m3s": [round(float(v), 6) for v in cap],
            }
            if ref is None:
                ref = h
                row["max_depth_change_vs_25m_m"] = 0.0
            else:
                row["max_depth_change_vs_25m_m"] = round(
                    float(np.max(np.abs(h - ref))), 9)
            out.append(row)
    finally:
        hb.CANAL["dx"] = original
    return out


# ---------------------------------------------------------------------------
def main():
    with open(RESULTS / "hydrolex_bench_results.json", encoding="utf-8") as f:
        res = json.load(f)
    detail = res["instance_C_detail"]
    plans = {
        "quantity_only_plan": np.array([d["decoupled_m3s"] for d in detail]),
        "certified_plan": np.array([d["certified_m3s"] for d in detail]),
        "largest_executable_uniform_plan":
            res["instance_C"]["best_uniform_feasible_ratio"] * hb.D_CANAL,
    }

    froude = {name: froude_profile(x) for name, x in plans.items()}

    # the uniform ray scanned for Figure 2, for completeness
    ray = [froude_profile(t * hb.D_CANAL)["F_max"]
           for t in np.linspace(0.02, 1.0, 197)]
    froude["figure2_uniform_ray_scan"] = {
        "grid": "t in [0.02, 1.0], 197 points",
        "F_max": round(float(max(ray)), 6),
    }
    froude["max_over_reported_plans"] = round(
        float(max(froude[k]["F_max"] for k in plans)), 6)
    froude["subcritical_everywhere"] = bool(
        froude["max_over_reported_plans"] < 1.0)

    out = {
        "purpose": "diagnostics that hydrolex_bench.py does not record; "
                   "the benchmark itself is unmodified",
        "environment": environment(),
        "froude": froude,
        "grid_refinement_certified_plan":
            grid_refinement(plans["certified_plan"]),
    }

    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "diagnostics.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(json.dumps(out["environment"], indent=2))
    print()
    for k in plans:
        print(f"  {k:34s} F_max = {froude[k]['F_max']:.4f} "
              f"at x = {froude[k]['at_chainage_m']:.0f} m")
    print(f"  {'max over the reported plans':34s} "
          f"F_max = {froude['max_over_reported_plans']:.4f}   "
          f"subcritical: {froude['subcritical_everywhere']}")
    print()
    print("  grid refinement of the certified plan (max depth change vs dx = 25 m):")
    for row in out["grid_refinement_certified_plan"]:
        print(f"    dx = {row['dx_m']:>6.3f} m   "
              f"{row['max_depth_change_vs_25m_m']:.3e} m")
    print("\nwritten to", RESULTS / "diagnostics.json")


if __name__ == "__main__":
    main()
