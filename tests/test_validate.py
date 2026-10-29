import json
import subprocess
import sys
import unittest
from itertools import product
from pathlib import Path

from generator import generate_instance
from solver.bruteforce import solve_exact
from solver.instance import Instance, load_instance
from solver.validate import check, is_feasible, p_base

ROOT = Path(__file__).resolve().parent.parent
TOY = ROOT / "instances" / "toy.json"


def enumerate_optimum(inst):
    """Plain K^n enumeration, independent of the branch-and-bound code."""
    best = None
    for sigma in product(range(inst.K), repeat=inst.n):
        if is_feasible(inst, list(sigma)):
            val = p_base(inst, sigma)
            if best is None or val < best:
                best = val
    return best


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.inst = load_instance(TOY)

    def test_known_feasible_assignment(self):
        self.assertEqual(check(self.inst, [1, 0, 0, 1, 1, 2]), [])

    def test_p_base_uses_slot_plus_one(self):
        # weights 5,4,3,2,3,2 ; slots+1 = 2,1,1,2,2,3
        self.assertEqual(p_base(self.inst, [1, 0, 0, 1, 1, 2]), 10 + 4 + 3 + 4 + 6 + 6)

    def test_detects_conflict(self):
        errs = check(self.inst, [1, 1, 0, 2, 0, 2])  # T1-T2 share slot 1
        self.assertTrue(any(e.startswith("F1: T1 and T2") for e in errs))

    def test_detects_window(self):
        errs = check(self.inst, [3, 0, 0, 1, 1, 2])  # T1 window is [0, 2]
        self.assertTrue(any(e.startswith("F3: T1") for e in errs))

    def test_detects_capacity(self):
        data = json.loads(TOY.read_text())
        data["capacities"][1] = [32, 128, 7, 6.0]  # slot 1 GPU now 7 < 4+2+2
        errs = check(Instance(**data), [1, 0, 0, 1, 1, 2])
        self.assertTrue(any(e.startswith("F2: slot 1 dim 2") for e in errs))

    def test_detects_unassigned(self):
        self.assertIn("T6 is unassigned", check(self.inst, [1, 0, 0, 1, 1, None]))


class BruteForceTest(unittest.TestCase):
    def test_toy_matches_enumeration(self):
        inst = load_instance(TOY)
        res = solve_exact(inst)
        self.assertEqual(res.status, "optimal")
        self.assertEqual(check(inst, res.sigma), [])
        self.assertAlmostEqual(res.value, enumerate_optimum(inst))

    def test_benchmark_seed1_matches_enumeration(self):
        inst = Instance(**generate_instance(8, 3, conflict_density=0.3, seed=1))
        res = solve_exact(inst)
        self.assertEqual(check(inst, res.sigma), [])
        self.assertAlmostEqual(res.value, enumerate_optimum(inst))

    def test_small_benchmarks_solve_to_optimal(self):
        for n, K, dens, seed in [(8, 3, 0.3, 1), (10, 4, 0.4, 2), (12, 4, 0.5, 3)]:
            inst = Instance(**generate_instance(n, K, conflict_density=dens, seed=seed))
            res = solve_exact(inst)
            self.assertEqual(res.status, "optimal", (n, K, seed))
            self.assertEqual(check(inst, res.sigma), [])

    def test_random_small_instances_match_enumeration(self):
        for seed in range(100, 130):
            inst = Instance(**generate_instance(6, 3, conflict_density=0.5, seed=seed))
            res = solve_exact(inst)
            expected = enumerate_optimum(inst)
            if expected is None:
                self.assertEqual(res.status, "infeasible", seed)
            else:
                self.assertAlmostEqual(res.value, expected, msg=f"seed {seed}")

    def test_infeasible_triangle_in_two_slots(self):
        data = dict(tasks=["A", "B", "C"], conflicts=[[0, 1], [1, 2], [0, 2]],
                    resources=[[1]] * 3, capacities=[[10]] * 2,
                    windows=[[0, 1]] * 3, weights=[1, 1, 1], K=2)
        self.assertEqual(solve_exact(Instance(**data)).status, "infeasible")


class RunCliTest(unittest.TestCase):
    def test_brute_cli_prints_five_keys(self):
        out = subprocess.run([sys.executable, str(ROOT / "run.py"), "--n", "8", "--K", "3",
                              "--density", "0.3", "--seed", "1", "--solver", "brute"],
                             capture_output=True, text=True, check=True, cwd=ROOT).stdout
        res = json.loads(out)
        self.assertEqual(set(res), {"assignment", "penalty", "runtime_ms", "feasible", "violation_reason"})
        self.assertTrue(res["feasible"])
        self.assertEqual(len(res["assignment"]), 8)


if __name__ == "__main__":
    unittest.main()
