"""Command-line entry point.

    python run.py --n 8 --K 3 --density 0.3 --seed 1            # generate, then solve
    python run.py --input instances/toy.json                    # solve a JSON file
    python run.py --n 8 --K 3 --density 0.3 --seed 1 --solver brute

Prints the result JSON (exactly the 5 keys required by the spec) and, with
--out, also writes it to a file.
"""

import argparse
import sys
import time

from generator import generate_instance
from solver.instance import Instance, Result, load_instance, save_instance, save_result
from solver.penalty import penalty
from solver.validate import check


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="MSME credit pipeline scheduler")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="instance JSON file")
    src.add_argument("--n", type=int, help="number of tasks (generate an instance)")
    ap.add_argument("--K", type=int, help="number of slots")
    ap.add_argument("--density", type=float, default=0.3, help="conflict density")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--solver", choices=["heuristic", "brute"], default="heuristic")
    ap.add_argument("--out", help="write result JSON here")
    ap.add_argument("--save-instance", help="write the generated instance JSON here")
    args = ap.parse_args(argv)
    if args.n is not None and args.K is None:
        ap.error("--K is required with --n")
    return args


def get_instance(args) -> Instance:
    if args.input:
        return load_instance(args.input)
    inst = Instance(**generate_instance(args.n, args.K, conflict_density=args.density, seed=args.seed))
    if args.save_instance:
        save_instance(inst, args.save_instance)
    return inst


def solve(inst: Instance, solver: str) -> Result:
    """Run the chosen solver and package its output as a Result.

    Every assignment reported as feasible is re-checked with the
    independent validator, so a solver bug shows up as feasible=false
    with the reason, not as a silently invalid schedule.
    """
    start = time.perf_counter()
    if solver == "brute":
        from solver.bruteforce import solve_exact
        ex = solve_exact(inst, objective=penalty)
        sigma = ex.sigma
        reason = {"optimal": "", "infeasible": "PROVEN_INFEASIBLE: exhaustive search found no assignment",
                  "limit": "NOT_FOUND: brute-force node limit reached"}[ex.status]
    else:
        from solver.algorithm import solve as heuristic  # added in Phase F
        sigma, reason = heuristic(inst)
    runtime_ms = int((time.perf_counter() - start) * 1000)

    res = Result(runtime_ms=runtime_ms, violation_reason=reason)
    if sigma is not None:
        res.assignment = {inst.tasks[i]: s for i, s in enumerate(sigma) if s is not None}
    if sigma is not None and not reason:
        errors = check(inst, sigma)
        if errors:
            res.violation_reason = "INVALID_OUTPUT: " + "; ".join(errors)
        else:
            res.feasible = True
            res.penalty = penalty(inst, sigma)
    return res


def main(argv=None):
    args = parse_args(argv)
    res = solve(get_instance(args), args.solver)
    if args.out:
        save_result(res, args.out)
    print(res.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
