import unittest
from pathlib import Path

from generator import generate_instance
from solver.bruteforce import solve_exact
from solver.instance import Instance, load_instance
from solver.penalty import PENALTY_FACTOR, components, load_imbalance, penalty, sla_risk
from solver.validate import check, p_base

ROOT = Path(__file__).resolve().parent.parent
SIGMA = [1, 0, 0, 1, 1, 2]  # feasible toy assignment, checked in test_validate


class PenaltyHandValuesTest(unittest.TestCase):
    """Expected values computed by hand (see report section T2)."""

    def setUp(self):
        self.inst = load_instance(ROOT / "instances" / "toy.json")

    def test_sla_risk(self):
        # T1 5*(1/2)^2 + T5 3*(1/3)^2 + T6 2*(1/2)^2 ; others sit at lo
        self.assertAlmostEqual(sla_risk(self.inst, SIGMA), 1.25 + 1 / 3 + 0.5)

    def test_load_imbalance(self):
        # utilisation per slot: CPU and RAM .1875 1 .125 0, GPU 0 1 0 0, Net 5/6 .5 .25 0
        def var_sum(u):
            m = sum(u) / len(u)
            return sum((x - m) ** 2 for x in u)
        cpu = [0.1875, 1, 0.125, 0]
        sq = 2 * var_sum(cpu) + var_sum([0, 1, 0, 0]) + var_sum([5 / 6, 0.5, 0.25, 0])
        self.assertAlmostEqual(load_imbalance(self.inst, SIGMA), 19 * sq / 16)
        self.assertAlmostEqual(load_imbalance(self.inst, SIGMA), 2.81490, places=4)

    def test_total(self):
        self.assertAlmostEqual(penalty(self.inst, SIGMA), 33 + 2.083333 + 2.814900, places=4)


class PenaltyPropertiesTest(unittest.TestCase):
    def test_bounds_hold_on_random_feasible_assignments(self):
        """P_base <= P <= PENALTY_FACTOR * P_base, which Task 4 depends on."""
        for seed in range(20):
            inst = Instance(**generate_instance(8, 3, conflict_density=0.3, seed=seed))
            res = solve_exact(inst)
            if res.sigma is None:
                continue
            c = components(inst, res.sigma)
            w = sum(inst.weights)
            self.assertLessEqual(c["sla_risk"], w + 1e-9)
            self.assertLessEqual(c["load_imbalance"], w / 4 + 1e-9)
            pb = p_base(inst, res.sigma)
            self.assertLessEqual(pb, penalty(inst, res.sigma))
            self.assertLessEqual(penalty(inst, res.sigma), PENALTY_FACTOR * pb + 1e-9)

    def test_extension_is_not_trivial(self):
        """Two schedules with equal P_base get different P."""
        data = dict(tasks=["A", "B"], conflicts=[], resources=[[1], [1]],
                    capacities=[[2], [2], [2]], windows=[[0, 1], [0, 2]], weights=[1, 1], K=3)
        inst = Instance(**data)
        a, b = [1, 0], [0, 1]  # both P_base = 3; A at its window end in a
        self.assertEqual(p_base(inst, a), p_base(inst, b))
        self.assertNotAlmostEqual(penalty(inst, a), penalty(inst, b))
        self.assertLess(penalty(inst, b), penalty(inst, a))

    def test_zero_capacity_slot_is_ignored_by_balance(self):
        data = dict(tasks=["A", "B"], conflicts=[], resources=[[1], [1]],
                    capacities=[[2], [0], [2]], windows=[[0, 2], [0, 2]], weights=[1, 1], K=3)
        inst = Instance(**data)
        sigma = [0, 2]  # both usable slots at 50%: perfectly balanced
        self.assertEqual(check(inst, sigma), [])
        self.assertAlmostEqual(load_imbalance(inst, sigma), 0.0)

    def test_width_one_window_has_zero_risk(self):
        data = dict(tasks=["A"], conflicts=[], resources=[[1]], capacities=[[1], [1]],
                    windows=[[1, 1]], weights=[5], K=2)
        self.assertEqual(sla_risk(Instance(**data), [1]), 0.0)


class BruteForceWithPenaltyTest(unittest.TestCase):
    def test_exact_under_p_matches_enumeration(self):
        from itertools import product
        from solver.validate import is_feasible
        inst = load_instance(ROOT / "instances" / "toy.json")
        best = min(penalty(inst, list(s)) for s in product(range(inst.K), repeat=inst.n)
                   if is_feasible(inst, list(s)))
        res = solve_exact(inst, objective=penalty)
        self.assertAlmostEqual(res.value, best)


if __name__ == "__main__":
    unittest.main()
