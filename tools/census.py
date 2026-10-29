"""Print raw descriptive statistics for the 9 benchmark instances.

Descriptive only: it reports counts and sums and makes no feasibility
verdict. Interpreting these numbers is the candidate's T6 work.

Usage: python tools/census.py
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generator import generate_instance  # noqa: E402
from solver.instance import Instance  # noqa: E402

# (n, K, density, seed) from assignment lines 145-157.
BENCHMARKS = [
    (8, 3, 0.3, 1),
    (10, 4, 0.4, 2),
    (12, 4, 0.5, 3),
    (50, 8, 0.25, 10),
    (100, 10, 0.30, 11),
    (150, 12, 0.35, 12),
    (200, 15, 0.40, 20),
    (200, 5, 0.60, 21),
    (200, 20, 0.10, 22),
]

DIMS = ["CPU", "RAM", "GPU", "Net"]


def census_row(n, K, density, seed):
    inst = Instance(**generate_instance(n, K, conflict_density=density, seed=seed))
    widths = Counter(hi - lo + 1 for lo, hi in inst.windows)
    demand = [sum(r[k] for r in inst.resources) for k in range(inst.d)]
    capacity = [sum(c[k] for c in inst.capacities) for k in range(inst.d)]
    return inst, widths, demand, capacity


def main():
    for n, K, density, seed in BENCHMARKS:
        inst, widths, demand, capacity = census_row(n, K, density, seed)
        width_str = " ".join(f"{w}:{c}" for w, c in sorted(widths.items()))
        dim_str = " ".join(f"{name}={dem:.1f}/{cap:.1f}"
                           for name, dem, cap in zip(DIMS, demand, capacity))
        print(f"n={n:<3} K={K:<2} dens={density:<4} seed={seed:<2} "
              f"edges={len(inst.conflicts):<5} widths[{width_str}] demand/cap[{dim_str}]")


if __name__ == "__main__":
    main()
