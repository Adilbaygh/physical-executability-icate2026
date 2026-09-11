#!/usr/bin/env python3
"""Redraw Figures 2 and 3 from the archived benchmark output.

Why this script exists
----------------------
The published figures were drawn by `hydrolex_bench.py` at a time when the
manuscript wrote the computed floor as r*. The revised manuscript reserves r*
for the leximin floor of problem P1 — the true optimum, which is not computed —
and writes the value a certified plan attains as r_cert. Figures 2 and 3 still
carried the old symbol, so they labelled a certified lower bound with the symbol
the paper reserves for the optimum. Figure 3 additionally described the
sequential-linearization search interval as a "bracket", which reads as a proved
bound and is not one.

This script corrects those labels and nothing else. It recomputes nothing: every
plotted value is read from `results/hydrolex_bench_results.json`, the reference
output archived with version 1.0.0 of this package. `hydrolex_bench.py` is left
byte-identical to the script that produced that output.

Usage
-----
    cd src
    python figures.py

writes ../results/fig2_frontier.png and ../results/fig3_convergence.png
"""
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")

# style, identical to hydrolex_bench.py
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"],
                     "font.size": 8, "axes.linewidth": 0.6,
                     "lines.linewidth": 1.0, "savefig.dpi": 600})
C_DEC, C_CER, C_LIM = "#B03A2E", "#1B4F72", "#707B7C"

# the symbol the revised manuscript uses for a floor a certified plan attains
R_CERT = r"$r_{\mathrm{cert}}$"


def load():
    with open(os.path.join(RESULTS, "hydrolex_bench_results.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def figure2(res):
    fr = res["frontier"]
    t = np.array(fr["t"])

    def nrm(v):
        v = np.array(v, float)
        return v / abs(v[0])

    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.05))
    ax[0].plot(t, nrm(fr["E_voltage_margin_pu"]), color=C_CER,
               label="potential: bus voltage")
    ax[0].plot(t, nrm(fr["E_supply_margin"]), color=C_DEC, ls="-.",
               label="quantity: feeder-head supply")
    ax[1].plot(t, nrm(fr["C_gate_margin_m3s"]), color=C_CER,
               label="potential: offtake command head")
    ax[1].plot(t, nrm(fr["C_head_margin_m3s"]), color=C_DEC, ls="-.",
               label="quantity: head-gate discharge")
    ax[1].plot(t, nrm(fr["C_level_margin_m"]), color="#7D6608", ls=":",
               label="potential: supply level")
    for a, inst, ttl in ((ax[0], "instance_E", "(a) Instance E"),
                         (ax[1], "instance_C", "(b) Instance C")):
        a.axhline(0, color="k", lw=0.6)
        a.axvline(res[inst]["decoupled_floor"], color=C_DEC, ls=":", lw=0.9)
        a.axvline(res[inst]["certified_floor"], color=C_CER, ls="--", lw=0.9)
        a.annotate("$r_0$", (res[inst]["decoupled_floor"], 0.92), fontsize=7,
                   color=C_DEC, ha="left", va="top", xytext=(2, 0),
                   textcoords="offset points")
        a.annotate(R_CERT, (res[inst]["certified_floor"], 0.92), fontsize=7,
                   color=C_CER, ha="right", va="top", xytext=(-2, 0),
                   textcoords="offset points")
        a.set_xlabel("uniform service ratio $t$")
        a.set_ylabel("normalized constraint margin")
        a.set_title(ttl, fontsize=8)
        a.set_ylim(-1.05, 1.05)
        a.legend(frameon=False, fontsize=6.2, loc="lower left")
        a.tick_params(labelsize=7)
    fig.tight_layout()
    out = os.path.join(RESULTS, "fig2_frontier.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def figure3(res):
    cv = res["convergence"]
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.05))
    ok = np.maximum(np.abs(np.array(cv["phase1_at_floor"])), 1e-16)
    bad = np.maximum(np.abs(np.array(cv["phase1_above_floor"])), 1e-16)
    floor = res["instance_C"]["certified_floor"]
    ax[0].semilogy(np.arange(1, len(ok) + 1), ok, "o-", ms=3, color=C_CER,
                   label=r"$t = r_{\mathrm{cert}}$ = %.4f" % floor)
    ax[0].semilogy(np.arange(1, len(bad) + 1), bad, "s--", ms=3, color=C_DEC,
                   label=r"$t = r_{\mathrm{cert}} + 0.02$")
    ax[0].set_xlabel("phase-1 iteration")
    ax[0].set_ylabel("|worst exact violation|, m$^3$/s")
    ax[0].set_title("(a) Phase-1 convergence, Instance C", fontsize=8)
    ax[0].legend(frameon=False, fontsize=6.5)

    br = np.array(cv["bracket"])
    if br.size:
        k = np.arange(1, len(br) + 1)
        ax[1].plot(k, br[:, 0], color=C_CER, label="lower end, search interval")
        ax[1].plot(k, br[:, 1], color=C_DEC, ls="--",
                   label="upper end, search interval")
        ax[1].fill_between(k, br[:, 0], br[:, 1], color=C_LIM, alpha=0.18)
    ax[1].set_xlabel("bisection iteration")
    ax[1].set_ylabel("service-ratio floor")
    ax[1].set_title("(b) Heuristic floor search, Instance C", fontsize=8)
    ax[1].legend(frameon=False, fontsize=6.5)
    for a in ax:
        a.tick_params(labelsize=7)
    fig.tight_layout()
    out = os.path.join(RESULTS, "fig3_convergence.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def main():
    res = load()
    print("redrawing from results/hydrolex_bench_results.json — no value is recomputed")
    for out in (figure2(res), figure3(res)):
        print("   written", os.path.normpath(out))
    print("\nlabel changes only:")
    print("   Figure 2, both panels : r*  ->  r_cert")
    print("   Figure 3, panel (a)   : t = r*  ->  t = r_cert   (both legend entries)")
    print("   Figure 3, panel (b)   : 'lower/upper bracket'  ->  'lower/upper end, "
          "search interval'")
    print("   Figure 3, panel (b)   : title 'Floor bisection'  ->  'Heuristic floor search'")


if __name__ == "__main__":
    main()
