"""Compare SSD-R with the exact optimum on one instance file.

Usage: python tools/ratio.py instances/tight_K4.json
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solver.algorithm import solve  # noqa: E402
from solver.bruteforce import solve_exact  # noqa: E402
from solver.instance import load_instance  # noqa: E402
from solver.penalty import penalty  # noqa: E402
from solver.validate import p_base  # noqa: E402


def main(path):
    inst = load_instance(path)
    sigma, reason = solve(inst)
    if reason:
        print(reason)
        return
    for name, f in (("P_base", p_base), ("P", penalty)):
        opt = solve_exact(inst, objective=f).value
        print(f"{name}: SSD-R {f(inst, sigma):.6f}  optimum {opt:.6f}  ratio {f(inst, sigma) / opt:.9f}")


if __name__ == "__main__":
    main(sys.argv[1])
