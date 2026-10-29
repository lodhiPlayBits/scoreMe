"""Task 1: build the 3-Colouring -> scheduling reduction and check it by machine.

Construction for a graph G = (V, E) with m = |V| (report section 1):
  K = 5 uniform slots with the generator's capacity C = [32, 128, 8, 6].
  One vertex task t_v per vertex: window [0, 3], resources C / (m + 1).
  One blocker task b: window [0, 3], resources exactly C.
  Conflicts: E (only between vertex tasks).
G is 3-colourable if and only if the instance is feasible.

The ablation checks each family's gadget: removing it turns K4 (not
3-colourable) into a feasible instance, so the reduction would be wrong.

Usage: python tools/reduction.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solver.bruteforce import solve_exact  # noqa: E402
from solver.instance import Instance  # noqa: E402

CAP = [32, 128, 8, 6.0]
K = 5


def reduce_3col(m, edges, drop=None) -> Instance:
    """Build the instance. `drop` removes one family's gadget:
    "F1" drops the conflicts, "F2" makes the blocker weightless, and "F3"
    opens every window to all K slots."""
    share = [c / (m + 1) for c in CAP]
    resources = [share[:] for _ in range(m)] + [[0.0] * 4 if drop == "F2" else CAP[:]]
    window = (0, K - 1) if drop == "F3" else (0, 3)
    return Instance(tasks=[f"v{i}" for i in range(m)] + ["b"],
                    conflicts=[] if drop == "F1" else [tuple(e) for e in edges],
                    resources=resources, capacities=[CAP[:] for _ in range(K)],
                    windows=[window] * (m + 1), weights=[1.0] * (m + 1), K=K)


def colouring_from(sigma, m):
    """The (<=) direction made concrete: relabel the 3 slots the blocker
    leaves free as colours 0, 1, 2."""
    free = [s for s in range(4) if s != sigma[m]]
    return [free.index(sigma[v]) for v in range(m)]


def three_colourable(m, edges) -> bool:
    """Plain 3^m check, independent of the scheduler."""
    from itertools import product
    return any(all(c[a] != c[b] for a, b in edges) for c in product(range(3), repeat=m))


GRAPHS = {
    "C5 (odd cycle)": (5, [(i, (i + 1) % 5) for i in range(5)]),
    "K4": (4, [(a, b) for a in range(4) for b in range(a + 1, 4)]),
    "W5 (wheel, 5 rim)": (6, [(i, (i + 1) % 5) for i in range(5)] + [(i, 5) for i in range(5)]),
    "Petersen": (10, [(i, (i + 1) % 5) for i in range(5)] + [(i, i + 5) for i in range(5)]
                 + [(5 + i, 5 + (i + 2) % 5) for i in range(5)]),
}


def main():
    for name, (m, edges) in GRAPHS.items():
        res = solve_exact(reduce_3col(m, edges))
        feasible = res.status == "optimal"
        line = f"{name:<20} 3-colourable={three_colourable(m, edges)!s:<5} schedule feasible={feasible!s:<5}"
        if feasible:
            col = colouring_from(res.sigma, m)
            line += f" colouring={col} proper={all(col[a] != col[b] for a, b in edges)}"
        print(line)
    m, edges = GRAPHS["K4"]
    for drop in ("F1", "F2", "F3"):
        status = solve_exact(reduce_3col(m, edges, drop=drop)).status
        print(f"ablation: K4 with {drop} gadget removed -> {status}")


if __name__ == "__main__":
    main()
