"""Exact branch-and-bound search, used as ground truth on small instances.

It is exponential (K^n in the worst case) and exists only to measure the
heuristic's empirical approximation ratio on the small benchmarks (n <= 12)
and to check hand traces. It is never used on the medium or stress
instances.
"""

from dataclasses import dataclass

from solver.instance import Instance
from solver.validate import EPS, p_base


@dataclass
class ExactResult:
    status: str            # "optimal", "infeasible" or "limit"
    sigma: list | None     # best assignment found (None if none found)
    value: float | None    # objective value of sigma
    nodes: int             # search nodes expanded


def solve_exact(inst: Instance, objective=None, node_limit: int = 50_000_000) -> ExactResult:
    """Find an assignment minimising `objective` subject to F1, F2, F3.

    Design decisions:
    - Branch on tasks ordered by narrowest window first, then highest
      conflict degree. Tasks that are most constrained fail early, which
      cuts the tree near the root.
    - Try each task's slots in increasing order, because low slots are cheap
      under P_base. A good solution is found early, which tightens the bound.
    - Bound: cost so far + sum of w_i * (lo_i + 1) over unassigned tasks.
      No feasible completion can place a task below its window start, so
      this never cuts off the optimum. The bound is valid for any
      `objective` with objective(sigma) >= P_base(sigma). Our extended
      penalty only adds non-negative terms, so this holds for it.
    - Conflicts are checked against already-placed neighbours, and capacity
      against the running slot loads. Every complete leaf is therefore
      feasible by construction, with no separate validation pass.

    `status` is "limit" if the node budget ran out. The best assignment
    found so far is then returned, but it is not proven optimal.
    """
    objective = objective or p_base
    n, K, d = inst.n, inst.K, inst.d
    adj = [[] for _ in range(n)]
    for i, j in inst.conflicts:
        adj[i].append(j)
        adj[j].append(i)

    order = sorted(range(n), key=lambda i: (inst.windows[i][1] - inst.windows[i][0], -len(adj[i])))
    # rest_lb[p] = lower bound on the cost of tasks order[p:]
    rest_lb = [0.0] * (n + 1)
    for p in range(n - 1, -1, -1):
        i = order[p]
        rest_lb[p] = rest_lb[p + 1] + inst.weights[i] * (inst.windows[i][0] + 1)

    sigma = [None] * n
    load = [[0.0] * d for _ in range(K)]
    best = ExactResult("infeasible", None, None, 0)
    best_val = float("inf")

    def dfs(p: int, cost: float) -> bool:
        """Return False once the node limit is hit, to unwind the search."""
        nonlocal best_val
        best.nodes += 1
        if best.nodes > node_limit:
            return False
        if cost + rest_lb[p] >= best_val - EPS:
            return True
        if p == n:
            val = objective(inst, sigma)
            if val < best_val - EPS:
                best_val = val
                best.sigma, best.value = sigma[:], val
            return True
        i = order[p]
        lo, hi = inst.windows[i]
        r, w = inst.resources[i], inst.weights[i]
        for s in range(lo, hi + 1):
            if any(sigma[j] == s for j in adj[i]):
                continue
            if any(load[s][k] + r[k] > inst.capacities[s][k] + EPS for k in range(d)):
                continue
            sigma[i] = s
            for k in range(d):
                load[s][k] += r[k]
            ok = dfs(p + 1, cost + w * (s + 1))
            for k in range(d):
                load[s][k] -= r[k]
            sigma[i] = None
            if not ok:
                return False
        return True

    finished = dfs(0, 0.0)
    if not finished:
        best.status = "limit"
    elif best.sigma is not None:
        best.status = "optimal"
    return best
