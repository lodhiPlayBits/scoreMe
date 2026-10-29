"""Extended penalty P(sigma) = P_base + LAMBDA_RISK * R + LAMBDA_BAL * B (Task 2).

R, SLA breach risk: sum of w_i * ((sigma_i - lo_i) / (hi_i - lo_i))^2.
    A bureau pull placed at the very end of its window has no slack left:
    any retry or slow upstream API breaches the lender SLA. The squared
    position (0 at lo, 1 at hi) charges the last slots of a window much
    more than the middle ones. R is not just a rescaled P_base: two tasks
    in the same slot pay different risk depending on their windows.

B, load imbalance: W * (mean over (slot, dim) of (u_sk - mean_k)^2), where
    u_sk = load_sk / C_sk is the utilisation of dimension k in slot s and
    W = sum of all weights. One slot at 100% CPU next to a slot at 10%
    leaves no headroom for the busy slot's retries. The variance is 0 for a
    perfectly even spread. Multiplying by W puts B in the same units as
    P_base.

Bounds used by the approximation proof (Task 4):
    0 <= R <= W, because each squared ratio is in [0, 1].
    0 <= B <= W / 4, because utilisations of a feasible sigma are in [0, 1]
        and the variance of values in [0, 1] is at most 1/4.
    P_base >= W, because sigma_i + 1 >= 1.
So P_base <= P <= (1 + LAMBDA_RISK + LAMBDA_BAL / 4) * P_base = 2.25 * P_base.

Everything is computed in O(n*d + K*d) time.
"""

from solver.instance import Instance
from solver.validate import p_base, slot_loads

LAMBDA_RISK = 1.0
LAMBDA_BAL = 1.0
PENALTY_FACTOR = 1 + LAMBDA_RISK + LAMBDA_BAL / 4   # P <= PENALTY_FACTOR * P_base


def sla_risk(inst: Instance, sigma) -> float:
    """R term. A width-1 window (lo == hi) leaves no choice, so its risk is 0.

    The generator never makes width-1 windows, but hand-written tests do.
    Treating them as 0 avoids a division by zero, and it does not change
    the optimum, because every schedule pays the same amount for them.
    """
    total = 0.0
    for w, s, (lo, hi) in zip(inst.weights, sigma, inst.windows):
        if hi > lo:
            total += w * ((s - lo) / (hi - lo)) ** 2
    return total


def load_imbalance(inst: Instance, sigma) -> float:
    """B term. A (slot, dim) cell with capacity 0 is left out.

    A zero-capacity cell can never hold any load, so its utilisation is
    undefined (0/0). Counting it as 0% would make B push work into slots
    that cannot take it.
    """
    load = slot_loads(inst, sigma)
    sq_dev, cells = 0.0, 0
    for k in range(inst.d):
        utils = [load[s][k] / inst.capacities[s][k]
                 for s in range(inst.K) if inst.capacities[s][k] > 0]
        if not utils:
            continue
        mean = sum(utils) / len(utils)
        sq_dev += sum((u - mean) ** 2 for u in utils)
        cells += len(utils)
    if cells == 0:
        return 0.0
    return sum(inst.weights) * sq_dev / cells


def components(inst: Instance, sigma) -> dict:
    """Each term separately, for reports and traces."""
    return dict(p_base=p_base(inst, sigma), sla_risk=sla_risk(inst, sigma),
                load_imbalance=load_imbalance(inst, sigma))


def penalty(inst: Instance, sigma) -> float:
    """The full objective P(sigma). It assumes sigma is complete."""
    c = components(inst, sigma)
    return c["p_base"] + LAMBDA_RISK * c["sla_risk"] + LAMBDA_BAL * c["load_imbalance"]
