"""
HydroLex conference benchmark
=============================
Leximin allocation certified on a dissipative radial network, computed on two
independent physical media:

  Instance E -- IEEE 33-bus radial distribution feeder.
      Baran, M.E.; Wu, F.F. Network reconfiguration in distribution systems for
      loss reduction and load balancing. IEEE Trans. Power Deliv. 1989, 4(2),
      1401-1407. doi:10.1109/61.25627
      Line and load table as distributed in MATPOWER / pandapower `case33bw`
      (32 radial branches; the 5 tie branches are normally open and excluded).

  Instance C -- prismatic trapezoidal irrigation reach with 7 gated offtakes.
      Section geometry, Manning n and gate discharge coefficient are the
      published Canale Emiliano Romagnolo values (Luppi et al., Water 2018,
      10(8), 1017, doi:10.3390/w10081017, CC BY 3.0). The bed slope, the
      offtake spacing and the demand vector are DECLARED ASSUMED design values
      -- they are not reported in that paper.

Requires: numpy, scipy.  Run:  python hydrolex_bench.py
Everything the thesis reports is printed by this file. Nothing is typed by hand.
"""

import json
import sys
import time

import numpy as np
from scipy.optimize import linprog

TOL = 1e-9
G = 9.80665

# ----------------------------------------------------------------------------
# Instance E -- IEEE 33-bus feeder data (case33bw, 32 radial branches)
# ----------------------------------------------------------------------------
# (from_bus, to_bus, R_ohm, X_ohm), buses 1-indexed, bus 1 = substation/slack
BRANCH = [
    (1, 2, 0.0922, 0.0470), (2, 3, 0.4930, 0.2511), (3, 4, 0.3660, 0.1864),
    (4, 5, 0.3811, 0.1941), (5, 6, 0.8190, 0.7070), (6, 7, 0.1872, 0.6188),
    (7, 8, 0.7114, 0.2351), (8, 9, 1.0300, 0.7400), (9, 10, 1.0440, 0.7400),
    (10, 11, 0.1966, 0.0650), (11, 12, 0.3744, 0.1238), (12, 13, 1.4680, 1.1550),
    (13, 14, 0.5416, 0.7129), (14, 15, 0.5910, 0.5260), (15, 16, 0.7463, 0.5450),
    (16, 17, 1.2890, 1.7210), (17, 18, 0.7320, 0.5740), (2, 19, 0.1640, 0.1565),
    (19, 20, 1.5042, 1.3554), (20, 21, 0.4095, 0.4784), (21, 22, 0.7089, 0.9373),
    (3, 23, 0.4512, 0.3083), (23, 24, 0.8980, 0.7091), (24, 25, 0.8960, 0.7011),
    (6, 26, 0.2030, 0.1034), (26, 27, 0.2842, 0.1447), (27, 28, 1.0590, 0.9337),
    (28, 29, 0.8042, 0.7006), (29, 30, 0.5075, 0.2585), (30, 31, 0.9744, 0.9630),
    (31, 32, 0.3105, 0.3619), (32, 33, 0.3410, 0.5302),
]
# bus -> (P_kW, Q_kvar); bus 1 carries no load
LOAD_KW = {
    2: (100, 60), 3: (90, 40), 4: (120, 80), 5: (60, 30), 6: (60, 20),
    7: (200, 100), 8: (200, 100), 9: (60, 20), 10: (60, 20), 11: (45, 30),
    12: (60, 35), 13: (60, 35), 14: (120, 80), 15: (60, 10), 16: (60, 20),
    17: (60, 20), 18: (90, 40), 19: (90, 40), 20: (90, 40), 21: (90, 40),
    22: (90, 40), 23: (90, 50), 24: (420, 200), 25: (420, 200), 26: (60, 25),
    27: (60, 25), 28: (60, 20), 29: (120, 70), 30: (200, 600), 31: (150, 70),
    32: (210, 100), 33: (60, 40),
}
V_BASE_KV = 12.66
S_BASE_MVA = 1.0
Z_BASE = V_BASE_KV ** 2 / S_BASE_MVA          # ohm
NB = 33
LOAD_BUSES = sorted(LOAD_KW)                   # 32 claimants
P_D = np.array([LOAD_KW[b][0] for b in LOAD_BUSES], float)      # kW
Q_D = np.array([LOAD_KW[b][1] for b in LOAD_BUSES], float)      # kvar

V_FLOOR = 0.95      # ANSI C84.1-2016 Range A service voltage lower limit, p.u.
S_MAX_KW = 3200.0   # feeder-head supply cap, kW  (assumed deficit scenario)


def _feeder_topology():
    parent = np.full(NB + 1, -1, int)
    br_of = np.full(NB + 1, -1, int)
    children = {b: [] for b in range(1, NB + 1)}
    for k, (f, t, _, _) in enumerate(BRANCH):
        parent[t] = f
        br_of[t] = k
        children[f].append(t)
    order, stack = [], [1]
    while stack:
        b = stack.pop()
        order.append(b)
        stack.extend(children[b])
    assert len(order) == NB, "feeder is not a spanning radial tree"
    return parent, br_of, children, order


PARENT, BR_OF, CHILDREN, BFS_ORDER = _feeder_topology()
Z_PU = np.array([complex(r, x) / Z_BASE for _, _, r, x in BRANCH])
R_PU = np.array([r / Z_BASE for _, _, r, _ in BRANCH])


def feeder_solve(ratio):
    """Backward-forward sweep. `ratio[i]` scales bus LOAD_BUSES[i] at constant
    power factor. Returns (P_head_kW, V_pu[1..33], loss_kW)."""
    s_pu = np.zeros(NB + 1, complex)
    for i, b in enumerate(LOAD_BUSES):
        s_pu[b] = ratio[i] * complex(P_D[i], Q_D[i]) / 1000.0 / S_BASE_MVA
    v = np.ones(NB + 1, complex)
    i_br = np.zeros(len(BRANCH), complex)
    for _ in range(200):
        i_inj = np.zeros(NB + 1, complex)
        for b in range(1, NB + 1):
            if s_pu[b] != 0:
                i_inj[b] = np.conj(s_pu[b] / v[b])
        i_br[:] = 0.0
        for b in reversed(BFS_ORDER):          # leaves first
            if b == 1:
                continue
            tot = i_inj[b] + sum(i_br[BR_OF[c]] for c in CHILDREN[b])
            i_br[BR_OF[b]] = tot
        v_new = v.copy()
        v_new[1] = 1.0 + 0j
        for b in BFS_ORDER:
            if b == 1:
                continue
            v_new[b] = v_new[PARENT[b]] - Z_PU[BR_OF[b]] * i_br[BR_OF[b]]
        if np.max(np.abs(v_new - v)) < 1e-12:
            v = v_new
            break
        v = v_new
    loss_pu = float(np.sum(np.abs(i_br) ** 2 * R_PU))
    p_head_pu = float(np.real(np.sum(s_pu))) + loss_pu
    return p_head_pu * S_BASE_MVA * 1000.0, np.abs(v), loss_pu * S_BASE_MVA * 1000.0


# ----------------------------------------------------------------------------
# Instance C -- trapezoidal canal reach with gated offtakes
# ----------------------------------------------------------------------------
CANAL = dict(
    L=7000.0,           # reach length, m           (CER Pilot Segment)
    b=6.0,              # bed width, m              (CER published range 6.0-6.4)
    z=1.5,              # side slope H:V            (CER published 1.5:1)
    n=0.013,            # Manning n                 (CER published)
    S0=1.0e-4,          # bed slope                 ASSUMED design value
    Cd=0.6,             # gate discharge coeff.     (CER published)
    w=1.00,             # offtake gate width, m     ASSUMED
    amax=0.28,          # max gate opening, m       ASSUMED
    dx=25.0,            # integration step, m
)
X_OFF = np.array([1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0])
D_CANAL = np.array([1.0, 0.7, 1.2, 0.5, 1.4, 0.9, 0.9])   # demands, m^3/s
Q_TAIL = 5.0        # mandated continuation to the downstream reach, m^3/s
Q_MAX = 10.0        # head-gate capacity, m^3/s (assumed deficit scenario)
Z_BED0 = 100.0      # bed elevation at the head gate, m (arbitrary datum)
Z_SUPPLY = 101.50   # maximum head-gate water-surface elevation, m  ASSUMED


def _area(h):
    return (CANAL["b"] + CANAL["z"] * h) * h


def _perim(h):
    return CANAL["b"] + 2.0 * h * np.sqrt(1.0 + CANAL["z"] ** 2)


def _top(h):
    return CANAL["b"] + 2.0 * CANAL["z"] * h


def _sf(h, q):
    a = _area(h)
    r = a / _perim(h)
    return CANAL["n"] ** 2 * q * q / (a * a * r ** (4.0 / 3.0))


def _dhdx(h, q):
    a = _area(h)
    fr2 = q * q * _top(h) / (G * a ** 3)
    return (CANAL["S0"] - _sf(h, q)) / (1.0 - fr2)


def normal_depth(q):
    if q <= 0:
        return 1e-3
    lo, hi = 1e-3, 50.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        a = _area(mid)
        qn = (1.0 / CANAL["n"]) * a * (a / _perim(mid)) ** (2.0 / 3.0) * np.sqrt(CANAL["S0"])
        if qn < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def canal_solve(q):
    """Standard-step GVF integrated upstream from a uniform-flow tail control.
    Returns (h_at_offtakes[7], z_headgate_m, Q_head)."""
    q = np.asarray(q, float)
    n_off = len(q)
    # discharge carried by the sub-reach that ENDS at offtake j: everything
    # still withdrawn at or below j, plus the mandated downstream continuation
    q_reach = np.array([q[j:].sum() + Q_TAIL for j in range(n_off)])
    h = normal_depth(max(Q_TAIL, 1e-6))          # tail control: uniform flow
    h_at = np.zeros(n_off)
    h_at[-1] = h
    x_nodes = np.concatenate(([0.0], X_OFF))
    for j in range(n_off - 1, -1, -1):           # integrate upstream
        qj = max(q_reach[j], 1e-6)
        span = x_nodes[j + 1] - x_nodes[j]
        nstep = max(int(np.ceil(span / CANAL["dx"])), 1)
        step = span / nstep
        for _ in range(nstep):                   # RK4 with dx = -step
            k1 = _dhdx(h, qj)
            k2 = _dhdx(max(h - 0.5 * step * k1, 1e-3), qj)
            k3 = _dhdx(max(h - 0.5 * step * k2, 1e-3), qj)
            k4 = _dhdx(max(h - step * k3, 1e-3), qj)
            h = max(h - step * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0, 1e-3)
        if j > 0:
            h_at[j - 1] = h
    z_head = Z_BED0 + h
    return h_at, z_head, float(q.sum() + Q_TAIL)


def gate_cap(h_at):
    """Free-flow undershot gate at maximum opening: q_max = Cd*w*a*sqrt(2 g h)."""
    return CANAL["Cd"] * CANAL["w"] * CANAL["amax"] * np.sqrt(2.0 * G * np.maximum(h_at, 0.0))


# ----------------------------------------------------------------------------
# Leximin over service ratios subject to linear constraints
# ----------------------------------------------------------------------------
def leximin(d, A_ub=None, b_ub=None, ub=None):
    """Lexicographic max-min of r_i = x_i/d_i over {A_ub x <= b_ub, 0<=x<=ub}.
    Returns (x, r). Sequential-LP with blocked-set detection."""
    n = len(d)
    d = np.asarray(d, float)
    ub = np.asarray(d if ub is None else ub, float)
    A_ub = np.zeros((0, n)) if A_ub is None else np.atleast_2d(np.asarray(A_ub, float))
    b_ub = np.zeros(0) if b_ub is None else np.asarray(b_ub, float).ravel()
    fixed = {}                                   # index -> pinned ratio
    x_best = np.zeros(n)
    for _ in range(n + 2):
        free = [i for i in range(n) if i not in fixed]
        if not free:
            break
        # variables: [x (n), t]
        A, b = [], []
        for row, rhs in zip(A_ub, b_ub):
            A.append(np.concatenate([row, [0.0]]))
            b.append(rhs)
        for i in free:                           # -x_i/d_i + t <= 0
            r = np.zeros(n + 1)
            r[i] = -1.0 / d[i]
            r[n] = 1.0
            A.append(r)
            b.append(0.0)
        A_eq, b_eq = [], []
        for i, ri in fixed.items():
            r = np.zeros(n + 1)
            r[i] = 1.0
            A_eq.append(r)
            b_eq.append(ri * d[i])
        bounds = [(0.0, ub[i]) for i in range(n)] + [(0.0, None)]
        c = np.zeros(n + 1)
        c[n] = -1.0
        res = linprog(c, A_ub=np.array(A), b_ub=np.array(b),
                      A_eq=np.array(A_eq) if A_eq else None,
                      b_eq=np.array(b_eq) if b_eq else None,
                      bounds=bounds, method="highs")
        if not res.success:
            return None, None
        t = res.x[n]
        x_best = res.x[:n].copy()
        # which free indices cannot exceed t while the others hold at t?
        newly = []
        for i in free:
            c2 = np.zeros(n + 1)
            c2[i] = -1.0 / d[i]
            A2 = list(A)
            b2 = list(b)
            r = np.zeros(n + 1)
            r[n] = -1.0
            A2.append(r)
            b2.append(-t + 1e-12)                # t >= t*
            res2 = linprog(c2, A_ub=np.array(A2), b_ub=np.array(b2),
                           A_eq=np.array(A_eq) if A_eq else None,
                           b_eq=np.array(b_eq) if b_eq else None,
                           bounds=bounds, method="highs")
            if (not res2.success) or (-res2.fun - t) <= 1e-7:
                newly.append(i)
        if not newly:
            newly = list(free)
        for i in newly:
            fixed[i] = t
        if len(fixed) == n:
            break
    r = np.array([fixed.get(i, x_best[i] / d[i]) for i in range(n)])
    # rebuild the plan consistent with the pinned ratios
    x = r * d
    return x, r


# ----------------------------------------------------------------------------
# Certification loops
# ----------------------------------------------------------------------------
def feeder_floor_bisect():
    """Instance E is downward closed, so the leximin floor is the largest
    uniform ratio the exact model executes. Bisection on the EXACT solver."""
    def ok(t):
        p, v, _ = feeder_solve(np.full(len(P_D), t))
        return (p <= S_MAX_KW + 1e-9) and (v[1:].min() >= V_FLOOR - 1e-12)
    lo, hi = 0.0, 1.0
    if ok(1.0):
        return 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if ok(mid):
            lo = mid
        else:
            hi = mid
    return lo


def feeder_certified():
    """Floor by exact bisection, then the leximin hierarchy above the floor
    under linearized physics, with every accepted plan re-certified exactly."""
    t0 = feeder_floor_bisect()
    n = len(P_D)
    x = t0 * P_D
    for _ in range(30):
        p0, v0, _ = feeder_solve(x / P_D)
        # sensitivities d(P_head)/dx_i and d(V_j)/dx_i by central differences
        dp = np.zeros(n)
        dv = np.zeros((NB, n))
        for i in range(n):
            e = max(1e-3 * P_D[i], 1e-4)
            xp, xm = x.copy(), x.copy()
            xp[i] += e
            xm[i] = max(xm[i] - e, 0.0)
            pp, vp, _ = feeder_solve(xp / P_D)
            pm, vm, _ = feeder_solve(xm / P_D)
            den = xp[i] - xm[i]
            dp[i] = (pp - pm) / den
            dv[:, i] = (vp[1:] - vm[1:]) / den
        A = [dp]
        b = [S_MAX_KW - p0 + dp @ x]
        for j in range(NB):
            A.append(-dv[j])
            b.append(v0[1 + j] - V_FLOOR - dv[j] @ x)
        A = np.array(A)
        b = np.array(b)
        lo_x = t0 * P_D                       # never drop below the floor
        A_sh = A
        b_sh = b - A @ lo_x
        xs, _ = leximin(P_D, A_ub=A_sh, b_ub=b_sh, ub=P_D - lo_x)
        if xs is None:
            break
        x_new = lo_x + xs
        # exact certification with backtracking
        lam = 1.0
        for _ in range(40):
            cand = x + lam * (x_new - x)
            p, v, _ = feeder_solve(cand / P_D)
            if p <= S_MAX_KW + 1e-6 and v[1:].min() >= V_FLOOR - 1e-9:
                break
            lam *= 0.5
        else:
            break
        if np.max(np.abs(cand - x)) < 1e-6:
            x = cand
            break
        x = cand
    p, v, loss = feeder_solve(x / P_D)
    return x, x / P_D, p, v, loss


def canal_exact_ok(q):
    h, zh, qh = canal_solve(q)
    cap = gate_cap(h)
    ok = (qh <= Q_MAX + 1e-9 and zh <= Z_SUPPLY + 1e-9
          and np.all(np.asarray(q) <= cap + 1e-9))
    return bool(ok), h, zh, qh, cap


def canal_ray_scan(m=200):
    """Largest UNIFORM service ratio the exact model executes -- the reference
    a leximin plan must beat. Instance C is not downward closed, so the scan
    also counts sign changes rather than assuming a single crossing."""
    ts = np.linspace(1.0 / m, 1.0, m)
    flags = np.array([canal_exact_ok(t * D_CANAL)[0] for t in ts])
    if not flags.any():
        return 0.0, 0, int(m), 0
    changes = int(np.sum(np.diff(flags.astype(int)) != 0))
    last = int(np.max(np.where(flags)[0]))
    lo = ts[last]
    hi = ts[last + 1] if last + 1 < m else 1.0
    for _ in range(40):                              # refine the last crossing
        mid = 0.5 * (lo + hi)
        if canal_exact_ok(mid * D_CANAL)[0]:
            lo = mid
        else:
            hi = mid
    return float(lo), int(flags.sum()), int(m), changes


def _lexkey(r):
    return tuple(np.round(np.sort(np.asarray(r)), 9))


def _canal_linearize(x):
    """Return (z0, cap0, dz, dcap) at x by central finite differences."""
    n = len(x)
    h0, z0, _ = canal_solve(x)
    cap0 = gate_cap(h0)
    dz = np.zeros(n)
    dcap = np.zeros((n, n))
    for i in range(n):
        e = 1e-4
        xp, xm = x.copy(), x.copy()
        xp[i] += e
        xm[i] = max(xm[i] - e, 0.0)
        hp, zp, _ = canal_solve(xp)
        hm, zm, _ = canal_solve(xm)
        den = xp[i] - xm[i]
        dz[i] = (zp - zm) / den
        dcap[:, i] = (gate_cap(hp) - gate_cap(hm)) / den
    return z0, cap0, dz, dcap


def canal_violation(q):
    """Worst exact-model constraint violation at q (<= 0 means feasible)."""
    h, zh, qh = canal_solve(q)
    cap = gate_cap(h)
    return float(max(np.max(np.asarray(q) - cap),
                     qh - Q_MAX, zh - Z_SUPPLY))


def canal_floor_achievable(t, rounds=30, history=None):
    """Phase-1: is there an EXACTLY feasible plan with every service ratio >= t?
    Maximize the worst linearized gate slack, re-linearize, damp, and stop the
    moment the exact model certifies the iterate. Returns (bool, x)."""
    n = len(D_CANAL)
    lo = t * D_CANAL
    if lo.sum() > Q_MAX - Q_TAIL + 1e-12:
        if history is not None:
            history.append(float(lo.sum() - (Q_MAX - Q_TAIL)))
        return False, None
    x = lo.copy()
    for _ in range(rounds):
        if history is not None:
            history.append(canal_violation(x))
        if canal_exact_ok(x)[0]:
            return True, x
        z0, cap0, dz, dcap = _canal_linearize(x)
        # variables [x (n), s]; maximize s
        A, b = [], []
        A.append(np.concatenate([np.ones(n), [0.0]]))
        b.append(Q_MAX - Q_TAIL)
        A.append(np.concatenate([dz, [0.0]]))
        b.append(Z_SUPPLY - z0 + dz @ x)
        for j in range(n):                     # x_j - cap_j(x) + s <= 0
            row = -dcap[j].copy()
            row[j] += 1.0
            A.append(np.concatenate([row, [1.0]]))
            b.append(cap0[j] - dcap[j] @ x)
        c = np.zeros(n + 1)
        c[n] = -1.0
        bounds = [(lo[i], D_CANAL[i]) for i in range(n)] + [(None, None)]
        res = linprog(c, A_ub=np.array(A), b_ub=np.array(b), bounds=bounds,
                      method="highs")
        if not res.success:
            return False, None
        target = res.x[:n]
        lam, stepped = 1.0, False
        for _ in range(30):
            cand = x + lam * (target - x)
            if canal_exact_ok(cand)[0]:
                return True, cand
            if lam < 1e-3:
                break
            lam *= 0.5
        cand = x + 0.5 * (target - x)
        if np.max(np.abs(cand - x)) < 1e-9:
            break
        x = cand
    return canal_exact_ok(x)[0], x


_FLOOR_CACHE = {}


def canal_floor_bisect(lo=0.0, hi=1.0, iters=26):
    """Largest service-ratio floor for which phase-1 certifies a plan."""
    key = (lo, hi, iters)
    if key in _FLOOR_CACHE:
        return _FLOOR_CACHE[key]
    best_x = None
    bracket = []
    ok, xh = canal_floor_achievable(hi)
    if ok:
        _FLOOR_CACHE[key] = (hi, xh, bracket)
        return hi, xh, bracket
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        ok, xm = canal_floor_achievable(mid)
        if ok:
            lo, best_x = mid, xm
        else:
            hi = mid
        bracket.append((float(lo), float(hi)))
    _FLOOR_CACHE[key] = (lo, best_x, bracket)
    return lo, best_x, bracket


def canal_certified(x_start=None):
    """Sequential linearization with exact certification and backtracking,
    started from the best uniform plan the exact model executes."""
    n = len(D_CANAL)
    t_floor, x_floor, _ = canal_floor_bisect()
    x = x_floor if x_start is None else np.array(x_start, float)
    exact_ok = canal_exact_ok
    best = (x.copy(), x / D_CANAL) if canal_exact_ok(x)[0] else None
    for _ in range(60):
        h0, z0, _ = canal_solve(x)
        cap0 = gate_cap(h0)
        dz = np.zeros(n)
        dcap = np.zeros((n, n))
        for i in range(n):
            e = 1e-4
            xp, xm = x.copy(), x.copy()
            xp[i] += e
            xm[i] = max(xm[i] - e, 0.0)
            hp, zp, _ = canal_solve(xp)
            hm, zm, _ = canal_solve(xm)
            den = xp[i] - xm[i]
            dz[i] = (zp - zm) / den
            dcap[:, i] = (gate_cap(hp) - gate_cap(hm)) / den
        A = [np.ones(n), dz]
        b = [Q_MAX - Q_TAIL, Z_SUPPLY - z0 + dz @ x]
        for j in range(n):                    # x_j - cap_j(x) <= 0
            row = -dcap[j].copy()
            row[j] += 1.0
            A.append(row)
            b.append(cap0[j] - dcap[j] @ x)
        xs, rs = leximin(D_CANAL, A_ub=np.array(A), b_ub=np.array(b), ub=D_CANAL)
        if xs is None:
            break
        lam = 1.0
        moved = False
        for _ in range(50):
            cand = x + lam * (xs - x)
            ok, h, zh, qh, cap = exact_ok(cand)
            if ok:
                moved = True
                break
            lam *= 0.5
        if not moved:
            break
        if best is None or _lexkey(cand / D_CANAL) > _lexkey(best[1]):
            best = (cand.copy(), cand / D_CANAL)
        if np.max(np.abs(cand - x)) < 1e-7:
            x = cand
            break
        x = cand
    if best is None:
        raise RuntimeError("instance C: no exactly feasible plan was found")
    x = best[0]
    ok, h, zh, qh, cap = canal_exact_ok(x)
    assert ok, "instance C: the returned plan does not pass exact certification"
    return x, x / D_CANAL, h, zh, qh, cap


# ----------------------------------------------------------------------------
# Figures (all drawn from the computed results; nothing is drawn by hand)
# ----------------------------------------------------------------------------
def make_figures(res, x0_E, xE, vE, v0_E, x0_C, xC, hC, h0_C, capC, cap0_C):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                        # figures are optional
        print(f"\n[figures skipped: matplotlib unavailable -- {exc}]")
        res["figures"] = "skipped"
        return
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"],
                         "font.size": 8, "axes.linewidth": 0.6,
                         "lines.linewidth": 1.0, "savefig.dpi": 600})
    C_DEC, C_CER, C_LIM = "#B03A2E", "#1B4F72", "#707B7C"

    # ---- FIGURE 1 : what the medium does -----------------------------------
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.05))
    bus = np.arange(1, NB + 1)
    ax[0].plot(bus, v0_E[1:], "o-", ms=2.2, color=C_DEC, label="decoupled plan")
    ax[0].plot(bus, vE[1:], "s-", ms=2.2, color=C_CER, label="certified plan")
    ax[0].axhline(V_FLOOR, color=C_LIM, ls="--", lw=0.8, label="0.95 p.u. limit")
    ax[0].set_xlabel("bus index"), ax[0].set_ylabel("voltage magnitude, p.u.")
    ax[0].set_title("(a) Instance E: feeder voltage", fontsize=8)
    ax[0].legend(frameon=False, fontsize=6.5, loc="lower left")
    w = 0.36
    idx = np.arange(1, len(D_CANAL) + 1)
    ax[1].bar(idx - w / 2, x0_C, w, color=C_DEC, label="decoupled withdrawal")
    ax[1].bar(idx + w / 2, xC, w, color=C_CER, label="certified withdrawal")
    ax[1].hlines(cap0_C, idx - w, idx, color="k", lw=1.0,
                 label="gate capacity, decoupled")
    ax[1].hlines(capC, idx, idx + w, color=C_LIM, lw=1.0, ls="--",
                 label="gate capacity, certified")
    ax[1].set_xlabel("offtake"), ax[1].set_ylabel("discharge, m$^3$/s")
    ax[1].set_ylim(0, 1.32)
    ax[1].set_title("(b) Instance C: offtake gate capacity", fontsize=8)
    ax[1].legend(frameon=False, fontsize=6.0, loc="upper center", ncol=2,
                 columnspacing=0.8, handlelength=1.6)
    for a in ax:
        a.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig("fig1_media.png", bbox_inches="tight")
    plt.close(fig)

    # ---- FIGURE 2 : feasibility frontier along the uniform ray --------------
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
        a.annotate("$r^*$", (res[inst]["certified_floor"], 0.92), fontsize=7,
                   color=C_CER, ha="right", va="top", xytext=(-2, 0),
                   textcoords="offset points")
        a.set_xlabel("uniform service ratio $t$")
        a.set_ylabel("normalized constraint margin")
        a.set_title(ttl, fontsize=8)
        a.set_ylim(-1.05, 1.05)
        a.legend(frameon=False, fontsize=6.2, loc="lower left")
        a.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig("fig2_frontier.png", bbox_inches="tight")
    plt.close(fig)

    # ---- FIGURE 3 : convergence --------------------------------------------
    cv = res["convergence"]
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.05))
    ok = np.maximum(np.abs(np.array(cv["phase1_at_floor"])), 1e-16)
    bad = np.maximum(np.abs(np.array(cv["phase1_above_floor"])), 1e-16)
    ax[0].semilogy(np.arange(1, len(ok) + 1), ok, "o-", ms=3, color=C_CER,
                   label=f"$t = r^*$ = {res['instance_C']['certified_floor']:.4f}")
    ax[0].semilogy(np.arange(1, len(bad) + 1), bad, "s--", ms=3, color=C_DEC,
                   label="$t = r^* + 0.02$")
    ax[0].set_xlabel("phase-1 iteration")
    ax[0].set_ylabel("|worst exact violation|, m$^3$/s")
    ax[0].set_title("(a) Phase-1 convergence, Instance C", fontsize=8)
    ax[0].legend(frameon=False, fontsize=6.5)
    br = np.array(cv["bracket"])
    if br.size:
        k = np.arange(1, len(br) + 1)
        ax[1].plot(k, br[:, 0], color=C_CER, label="lower bracket")
        ax[1].plot(k, br[:, 1], color=C_DEC, ls="--", label="upper bracket")
        ax[1].fill_between(k, br[:, 0], br[:, 1], color=C_LIM, alpha=0.18)
    ax[1].set_xlabel("bisection iteration"), ax[1].set_ylabel("service-ratio floor")
    ax[1].set_title("(b) Floor bisection, Instance C", fontsize=8)
    ax[1].legend(frameon=False, fontsize=6.5)
    for a in ax:
        a.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig("fig3_convergence.png", bbox_inches="tight")
    plt.close(fig)
    res["figures"] = ["fig1_media.png", "fig2_frontier.png", "fig3_convergence.png"]
    print("\nfigures written: fig1_media.png  fig2_frontier.png  fig3_convergence.png")


# ----------------------------------------------------------------------------
# Self-tests
# ----------------------------------------------------------------------------
def self_tests():
    out = {}
    p, v, loss = feeder_solve(np.ones(len(P_D)))
    out["E_base_loss_kW"] = round(loss, 4)
    out["E_base_Vmin_pu"] = round(float(v[1:].min()), 6)
    out["E_base_Vmin_bus"] = int(np.argmin(v[1:]) + 1)
    out["E_base_Phead_kW"] = round(p, 4)
    out["E_base_load_kW"] = float(P_D.sum())
    out["E_ref_loss_kW"] = 202.677          # pandapower/MATPOWER Newton-Raphson
    out["E_ref_Vmin_pu"] = 0.913090
    out["E_loss_err_kW"] = round(abs(loss - 202.677), 5)
    out["E_Vmin_err_pu"] = round(abs(float(v[1:].min()) - 0.913090), 8)

    # canal: with no withdrawals every reach carries Q_TAIL, so uniform flow
    # must be an exact fixed point of the GVF integration over all 7000 m
    hn = normal_depth(Q_TAIL)
    h, zh, qh = canal_solve(np.zeros(7))
    out["C_normal_depth_m"] = round(hn, 6)
    out["C_uniform_profile_err_m"] = round(float(np.max(np.abs(h - hn))), 9)
    out["C_uniform_zhead_err_m"] = round(abs(zh - (Z_BED0 + hn)), 9)
    # Manning identity check
    a = _area(hn)
    q_check = (1.0 / CANAL["n"]) * a * (a / _perim(hn)) ** (2 / 3) * np.sqrt(CANAL["S0"])
    out["C_manning_identity_err"] = round(abs(q_check - Q_TAIL), 9)

    # leximin sanity: pure capacity constraint gives the uniform ratio
    d = np.array([2.0, 1.0, 3.0])
    xs, rs = leximin(d, A_ub=np.ones((1, 3)), b_ub=np.array([3.0]))
    out["LX_uniform_ratio"] = round(float(rs.min()), 9)
    out["LX_uniform_expected"] = 0.5
    return out


def main():
    t_start = time.time()
    print("=" * 78)
    print("HydroLex conference benchmark -- leximin certified on a radial medium")
    print("=" * 78)
    print("numpy", np.__version__, "| python", sys.version.split()[0])

    st = self_tests()
    print("\n--- SELF-TESTS ---")
    for k, val in st.items():
        print(f"  {k:28s} {val}")
    assert st["E_loss_err_kW"] < 0.05, "feeder solver does not match the published base case"
    assert st["E_Vmin_err_pu"] < 5e-5, "feeder Vmin does not match the published base case"
    assert st["C_uniform_profile_err_m"] < 1e-4, "GVF does not preserve uniform flow"
    assert abs(st["LX_uniform_ratio"] - 0.5) < 1e-7, "leximin broken"
    print("  ALL SELF-TESTS PASSED")

    res = {"self_tests": st}

    # ---------------- Instance E ----------------
    print("\n--- INSTANCE E : IEEE 33-bus feeder ---")
    p_full, v_full, loss_full = feeder_solve(np.ones(len(P_D)))
    eta0_E = float(P_D.sum() / p_full)
    r0_E = min(1.0, eta0_E * S_MAX_KW / P_D.sum())
    x0_E = r0_E * P_D
    p0_E, v0_E, loss0_E = feeder_solve(np.full(len(P_D), r0_E))
    xE, rE, pE, vE, lossE = feeder_certified()
    popE = 100.0 * (r0_E - rE.min()) / r0_E
    E = dict(
        S_max_kW=S_MAX_KW, V_floor_pu=V_FLOOR, demand_kW=float(P_D.sum()),
        eta0=round(eta0_E, 6),
        decoupled_floor=round(r0_E, 6),
        decoupled_Phead_kW=round(p0_E, 3),
        decoupled_Vmin_pu=round(float(v0_E[1:].min()), 6),
        decoupled_Vmin_bus=int(np.argmin(v0_E[1:]) + 1),
        decoupled_voltage_violation_pu=round(float(V_FLOOR - v0_E[1:].min()), 6),
        decoupled_loss_kW=round(loss0_E, 3),
        certified_floor=round(float(rE.min()), 6),
        certified_mean_ratio=round(float((xE.sum()) / P_D.sum()), 6),
        certified_max_ratio=round(float(rE.max()), 6),
        certified_Phead_kW=round(pE, 3),
        certified_Vmin_pu=round(float(vE[1:].min()), 6),
        certified_Vmin_bus=int(np.argmin(vE[1:]) + 1),
        certified_loss_kW=round(lossE, 3),
        certified_delivered_kW=round(float(xE.sum()), 3),
        binding="voltage" if abs(float(vE[1:].min()) - V_FLOOR) < 1e-4 else "supply",
        PoPE_percent=round(popE, 3),
    )
    for k, val in E.items():
        print(f"  {k:32s} {val}")
    res["instance_E"] = E
    res["instance_E_ratios"] = {int(b): round(float(rr), 6)
                                for b, rr in zip(LOAD_BUSES, rE)}

    # ---------------- Instance C ----------------
    print("\n--- INSTANCE C : trapezoidal canal reach, 7 gated offtakes ---")
    r0_C = min(1.0, (Q_MAX - Q_TAIL) / D_CANAL.sum())   # no volumetric loss modelled
    x0_C = r0_C * D_CANAL
    h0_C, z0_C, q0_C = canal_solve(x0_C)
    cap0_C = gate_cap(h0_C)
    t_ray, n_feas, n_scan, n_changes = canal_ray_scan()
    t_floor, _, floor_bracket = canal_floor_bisect()
    xC, rC, hC, zC, qC, capC = canal_certified()
    popC = 100.0 * (r0_C - rC.min()) / r0_C
    C = dict(
        Q_max_m3s=Q_MAX, Q_tail_m3s=Q_TAIL, demand_m3s=float(D_CANAL.sum()),
        z_supply_m=Z_SUPPLY,
        best_uniform_feasible_ratio=round(float(t_ray), 6),
        ray_feasible_points=f"{n_feas}/{n_scan}",
        ray_sign_changes=n_changes,
        leximin_gain_over_uniform_percent=round(
            100.0 * (float(rC.min()) - float(t_ray)) / float(t_ray), 4),
        floor_by_bisection=round(float(t_floor), 6),
        decoupled_floor=round(r0_C, 6),
        decoupled_Qhead_m3s=round(q0_C, 4),
        decoupled_z_head_m=round(z0_C, 4),
        decoupled_worst_gate=int(np.argmax(x0_C - cap0_C) + 1),
        decoupled_max_gate_overdraw_m3s=round(float(np.max(x0_C - cap0_C)), 4),
        decoupled_gates_infeasible=int(np.sum(x0_C > cap0_C + 1e-9)),
        certified_floor=round(float(rC.min()), 6),
        certified_mean_ratio=round(float(xC.sum() / D_CANAL.sum()), 6),
        certified_max_ratio=round(float(rC.max()), 6),
        certified_Qhead_m3s=round(qC, 4),
        certified_z_head_m=round(zC, 4),
        certified_delivered_m3s=round(float(xC.sum()), 4),
        certified_min_slack_m3s=round(float(np.min(capC - xC)), 6),
        PoPE_percent=round(popC, 3),
    )
    for k, val in C.items():
        print(f"  {k:32s} {val}")
    print("  per-offtake  depth_m / cap_m3s / demand / decoupled / certified")
    for j in range(len(D_CANAL)):
        print(f"    O{j+1} x={X_OFF[j]:6.0f} h={hC[j]:.4f} cap={capC[j]:.4f} "
              f"d={D_CANAL[j]:.2f} x0={x0_C[j]:.4f} x*={xC[j]:.4f} r*={rC[j]:.4f}")
    res["instance_C"] = C
    res["instance_C_detail"] = [
        dict(offtake=j + 1, x_m=float(X_OFF[j]), depth_m=round(float(hC[j]), 5),
             cap_m3s=round(float(capC[j]), 5), demand_m3s=float(D_CANAL[j]),
             decoupled_m3s=round(float(x0_C[j]), 5),
             certified_m3s=round(float(xC[j]), 5),
             ratio=round(float(rC[j]), 5))
        for j in range(len(D_CANAL))]

    # downward-closure probe: is the feasible set downward closed?
    print("\n--- STRUCTURAL PROBE : downward closure ---")
    probe = {}
    xt = xC.copy()
    xt[-1] *= 0.5                                    # cut the TAIL offtake only
    h_t, z_t, q_t = canal_solve(xt)
    cap_t = gate_cap(h_t)
    probe["canal_cut_tail_creates_violation"] = bool(np.any(xt > cap_t + 1e-9))
    probe["canal_cut_tail_max_violation_m3s"] = round(float(np.max(xt - cap_t)), 6)
    xe = xE.copy()
    xe[-1] *= 0.5
    _, v_e, _ = feeder_solve(xe / P_D)
    probe["feeder_cut_one_load_Vmin_pu"] = round(float(v_e[1:].min()), 6)
    probe["feeder_cut_one_load_still_feasible"] = bool(v_e[1:].min() >= V_FLOOR - 1e-9)
    for k, val in probe.items():
        print(f"  {k:40s} {val}")
    res["structural_probe"] = probe

    # ---------------- feasibility frontier along the uniform ray -------------
    print("\n--- FEASIBILITY FRONTIER (uniform ray) ---")
    ts = np.linspace(0.02, 1.0, 197)
    fe_v, fe_s = [], []
    for t in ts:
        p, v, _ = feeder_solve(np.full(len(P_D), t))
        fe_v.append(float(v[1:].min()) - V_FLOOR)
        fe_s.append((S_MAX_KW - p) / S_MAX_KW)
    fc_g, fc_q, fc_z = [], [], []
    for t in ts:
        qq = t * D_CANAL
        h_, z_, qh_ = canal_solve(qq)
        fc_g.append(float(np.min(gate_cap(h_) - qq)))
        fc_q.append(Q_MAX - qh_)
        fc_z.append(Z_SUPPLY - z_)
    frontier = dict(t=ts.tolist(), E_voltage_margin_pu=fe_v, E_supply_margin=fe_s,
                    C_gate_margin_m3s=fc_g, C_head_margin_m3s=fc_q,
                    C_level_margin_m=fc_z)
    res["frontier"] = frontier
    sign_changes = int(np.sum(np.diff(np.sign(np.array(fc_g))) != 0))
    print(f"  canal gate-margin sign changes along the ray : {sign_changes}")
    print(f"  feeder voltage-margin sign changes           : "
          f"{int(np.sum(np.diff(np.sign(np.array(fe_v))) != 0))}")
    res["frontier_summary"] = dict(canal_gate_sign_changes=sign_changes,
                                   feeder_voltage_sign_changes=int(np.sum(
                                       np.diff(np.sign(np.array(fe_v))) != 0)))

    # ---------------- convergence history -----------------------------------
    hist_ok, hist_fail = [], []
    canal_floor_achievable(float(t_floor), history=hist_ok)
    canal_floor_achievable(float(t_floor) + 0.02, history=hist_fail)
    res["convergence"] = dict(bracket=floor_bracket,
                              phase1_at_floor=hist_ok,
                              phase1_above_floor=hist_fail)
    print(f"  phase-1 at the floor  : {len(hist_ok)} iterations, "
          f"final violation {hist_ok[-1]:.3e}")
    print(f"  phase-1 above the floor: {len(hist_fail)} iterations, "
          f"final violation {hist_fail[-1]:.3e}")

    make_figures(res, x0_E, xE, vE, v0_E, x0_C, xC, hC, h0_C, capC, cap0_C)

    res["runtime_s"] = round(time.time() - t_start, 2)
    print(f"\nruntime {res['runtime_s']} s")
    with open("hydrolex_bench_results.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("results written to hydrolex_bench_results.json")


if __name__ == "__main__":
    main()
