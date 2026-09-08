"""
Sensitivity of the price of physical executability.

Answers the two questions the reviewers raised about the single point values
reported in the paper:

  (1) BASELINE SENSITIVITY (instance E). The quantity-only budget is
      B0 = eta0 * Sbar, so the reported price depends on the operating point at
      which the conveyance efficiency eta0 is calibrated. This script sweeps
      that calibration point over the whole load range and also evaluates two
      other legitimate quantity-only surrogates: a lossless budget and an
      affine loss model fitted along the uniform ray. The certified floor r*
      is a property of the medium and does not move.

      Instance C has no analogous freedom: its budget is
      B0 = Sbar - Lambda0 = 10.0 - 5.0 = 5.0 m3/s exactly, because the
      downstream continuation is a fixed commitment and not a calibrated
      efficiency. That asymmetry is itself a result.

  (2) DEFICIT SENSITIVITY (both media). The paper exercises each medium at one
      deficit scenario. This script sweeps the source cap and reports the price
      as a function of the quantity-only floor r0, which is dimensionless and
      therefore comparable across the two media.

The benchmark module is imported frozen and is never modified on disk. Module
constants are changed in memory only and restored in a finally block. The
floor cache of the benchmark is cleared whenever a constant changes, because
it is keyed on the bisection bracket and not on the scenario.

Run:   python sensitivity.py            full grids  (a few minutes)
       python sensitivity.py --quick    reduced grids, for a smoke test
Writes: ../results/sensitivity.json  and  ../results/fig4_sensitivity.png
"""

import json
import sys
from pathlib import Path

import numpy as np

import hydrolex_bench as hb

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
QUICK = "--quick" in sys.argv

C_DEC, C_CER, C_LIM = "#B03A2E", "#1B4F72", "#707B7C"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def feeder_uniform(t):
    """(head power kW, delivered kW) for the uniform plan at service ratio t."""
    p, _, _ = hb.feeder_solve(np.full(len(hb.P_D), float(t)))
    return float(p), float(t * hb.P_D.sum())


def price(r0, r_star):
    if r0 <= 0:
        return float("nan")
    return 100.0 * (r0 - r_star) / r0


def clear_cache():
    hb._FLOOR_CACHE.clear()


# ---------------------------------------------------------------------------
# 1. baseline sensitivity, instance E
# ---------------------------------------------------------------------------
def baseline_sensitivity_E():
    demand = float(hb.P_D.sum())
    s_bar = float(hb.S_MAX_KW)
    r_star = hb.feeder_floor_bisect()          # certified floor, baseline-free

    ts = np.round(np.arange(0.10, 1.0001, 0.05 if not QUICK else 0.15), 4)
    rows = []
    for t in ts:
        p, delivered = feeder_uniform(t)
        eta = delivered / p
        b0 = eta * s_bar
        r0 = min(1.0, b0 / demand)
        rows.append({
            "calibration_load_ratio": float(t),
            "eta0": round(eta, 6),
            "B0_kW": round(b0, 3),
            "r0": round(r0, 6),
            "price_percent": round(price(r0, r_star), 3),
        })

    # lossless surrogate
    r0_ll = min(1.0, s_bar / demand)
    lossless = {"eta0": 1.0, "B0_kW": round(s_bar, 3), "r0": round(r0_ll, 6),
                "price_percent": round(price(r0_ll, r_star), 3)}

    # affine loss surrogate: loss ~ a + b * delivered, fitted on the ray,
    # then B0 solves  B0 + a + b*B0 = Sbar
    dl, ls = [], []
    for t in np.linspace(0.1, 1.0, 19):
        p, delivered = feeder_uniform(t)
        dl.append(delivered)
        ls.append(p - delivered)
    b_coef, a_coef = np.polyfit(np.array(dl), np.array(ls), 1)
    b0_aff = (s_bar - a_coef) / (1.0 + b_coef)
    r0_aff = min(1.0, b0_aff / demand)
    affine = {"loss_kW": f"{a_coef:.4f} + {b_coef:.6f} * delivered_kW",
              "B0_kW": round(float(b0_aff), 3), "r0": round(float(r0_aff), 6),
              "price_percent": round(price(float(r0_aff), r_star), 3)}

    prices = [r["price_percent"] for r in rows] + \
             [lossless["price_percent"], affine["price_percent"]]
    return {
        "certified_floor": round(float(r_star), 6),
        "note": "the certified floor is a property of the medium and does not "
                "depend on the quantity-only surrogate",
        "paper_convention": "eta0 calibrated at full demand, "
                            "calibration_load_ratio = 1.0",
        "sweep": rows,
        "lossless_surrogate": lossless,
        "affine_loss_surrogate": affine,
        "price_range_percent": [round(min(prices), 3), round(max(prices), 3)],
    }


# ---------------------------------------------------------------------------
# 2. deficit sensitivity
# ---------------------------------------------------------------------------
def deficit_sensitivity_E():
    demand = float(hb.P_D.sum())
    eta0 = float(hb.P_D.sum() / feeder_uniform(1.0)[0])   # paper convention
    caps = ([1800, 2000, 2200, 2400, 2600, 2800, 3000, 3200, 3400, 3600, 3800]
            if not QUICK else [1800, 2200, 2800, 3200, 3600])
    original = hb.S_MAX_KW
    rows = []
    try:
        for cap in caps:
            hb.S_MAX_KW = float(cap)
            r_star = float(hb.feeder_floor_bisect())
            r0 = min(1.0, eta0 * cap / demand)
            rows.append({
                "S_bar_kW": float(cap),
                "r0": round(r0, 6),
                "certified_floor": round(r_star, 6),
                "price_percent": round(price(r0, r_star), 3),
            })
    finally:
        hb.S_MAX_KW = original
    return {
        "eta0_fixed_at_full_demand": round(eta0, 6),
        "note": "a price at or below zero means the quantity-only budget is "
                "itself tighter than the physically executable floor, so the "
                "decoupled plan happens to be executable. In instance E this "
                "occurs at low source caps because eta0 is calibrated at full "
                "demand and therefore understates the efficiency at light "
                "load; the surrogate is then conservative rather than unsafe. "
                "The certified floor stops moving once the voltage limit "
                "rather than the source cap becomes the binding constraint.",
        "sweep": rows,
    }


def deficit_sensitivity_C():
    demand = float(hb.D_CANAL.sum())
    caps = ([7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5]
            if not QUICK else [8.0, 9.0, 10.0, 11.0])
    original = hb.Q_MAX
    rows = []
    try:
        for cap in caps:
            hb.Q_MAX = float(cap)
            clear_cache()
            r_cert, _, _ = hb.canal_floor_bisect()
            r0 = min(1.0, (cap - hb.Q_TAIL) / demand)
            rows.append({
                "Q_max_m3s": float(cap),
                "r0": round(r0, 6),
                "certified_floor": round(float(r_cert), 6),
                "price_percent": round(price(r0, float(r_cert)), 3),
            })
    finally:
        hb.Q_MAX = original
        clear_cache()
    return {
        "budget_note": "B0 = Q_max - Q_tail exactly; the canal baseline admits "
                       "no calibration freedom",
        "sweep": rows,
    }


# ---------------------------------------------------------------------------
# figure
# ---------------------------------------------------------------------------
def make_figure(out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[figure skipped: matplotlib unavailable -- {exc}]")
        return None
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"],
                         "font.size": 8, "axes.linewidth": 0.6,
                         "lines.linewidth": 1.0, "savefig.dpi": 600})
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.05))

    b = out["baseline_sensitivity_E"]
    t = [r["calibration_load_ratio"] for r in b["sweep"]]
    p = [r["price_percent"] for r in b["sweep"]]
    ax[0].plot(t, p, "o-", ms=2.4, color=C_CER,
               label=r"$\eta_0$ calibrated at load level $t$")
    ax[0].axhline(b["lossless_surrogate"]["price_percent"], color=C_DEC,
                  ls="-.", lw=0.9, label="lossless surrogate")
    ax[0].axhline(b["affine_loss_surrogate"]["price_percent"], color=C_LIM,
                  ls=":", lw=0.9, label="affine loss surrogate")
    paper = [r for r in b["sweep"] if abs(r["calibration_load_ratio"] - 1.0) < 1e-9]
    if paper:
        ax[0].plot([1.0], [paper[0]["price_percent"]], "s", ms=4.0,
                   color=C_DEC, label="value reported in the paper")
    ax[0].set_xlabel("calibration load level $t$")
    ax[0].set_ylabel("price of executability, %")
    ax[0].set_title("(a) Instance E: baseline dependence", fontsize=8)
    ax[0].legend(frameon=False, fontsize=6.2, loc="upper right")
    ax[0].tick_params(labelsize=7)

    e = out["deficit_sensitivity_E"]["sweep"]
    c = out["deficit_sensitivity_C"]["sweep"]
    ax[1].plot([r["r0"] for r in e], [r["price_percent"] for r in e], "o-",
               ms=2.4, color=C_CER, label="instance E (feeder)")
    ax[1].plot([r["r0"] for r in c], [r["price_percent"] for r in c], "s--",
               ms=2.4, color=C_DEC, label="instance C (canal)")
    ax[1].set_xlabel("quantity-only floor $r_0$")
    ax[1].set_ylabel("price of executability, %")
    ax[1].set_title("(b) Dependence on the deficit level", fontsize=8)
    ax[1].legend(frameon=False, fontsize=6.5, loc="best")
    ax[1].tick_params(labelsize=7)

    fig.tight_layout()
    path = RESULTS / "fig4_sensitivity.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


# ---------------------------------------------------------------------------
def main():
    out = {
        "purpose": "sensitivity of the price of physical executability to the "
                   "quantity-only baseline and to the deficit level",
        "grids": "quick" if QUICK else "full",
        "baseline_sensitivity_E": baseline_sensitivity_E(),
        "deficit_sensitivity_E": deficit_sensitivity_E(),
        "deficit_sensitivity_C": deficit_sensitivity_C(),
    }
    out["figure"] = make_figure(out)

    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "sensitivity.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    b = out["baseline_sensitivity_E"]
    print("Instance E - baseline dependence (certified floor "
          f"{b['certified_floor']}, fixed):")
    for r in b["sweep"]:
        print(f"    eta0 at t = {r['calibration_load_ratio']:.2f}   "
              f"eta0 = {r['eta0']:.6f}   r0 = {r['r0']:.6f}   "
              f"price = {r['price_percent']:6.3f} %")
    print(f"    lossless surrogate                     "
          f"r0 = {b['lossless_surrogate']['r0']:.6f}   "
          f"price = {b['lossless_surrogate']['price_percent']:6.3f} %")
    print(f"    affine loss surrogate                  "
          f"r0 = {b['affine_loss_surrogate']['r0']:.6f}   "
          f"price = {b['affine_loss_surrogate']['price_percent']:6.3f} %")
    print(f"    price range over legitimate baselines: "
          f"{b['price_range_percent'][0]} - {b['price_range_percent'][1]} %")

    print("\nInstance E - deficit dependence:")
    for r in out["deficit_sensitivity_E"]["sweep"]:
        print(f"    Sbar = {r['S_bar_kW']:7.1f} kW   r0 = {r['r0']:.6f}   "
              f"r* = {r['certified_floor']:.6f}   "
              f"price = {r['price_percent']:6.3f} %")

    print("\nInstance C - deficit dependence:")
    for r in out["deficit_sensitivity_C"]["sweep"]:
        print(f"    Qmax = {r['Q_max_m3s']:5.1f} m3/s  r0 = {r['r0']:.6f}   "
              f"r_cert = {r['certified_floor']:.6f}   "
              f"price = {r['price_percent']:6.3f} %")

    print("\nwritten to", RESULTS / "sensitivity.json")
    if out["figure"]:
        print("figure   ", RESULTS / out["figure"])


if __name__ == "__main__":
    main()
