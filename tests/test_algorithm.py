import json
import subprocess
import sys
import unittest
from pathlib import Path

from generator import generate_instance
from solver.algorithm import largest_greedy_clique, odd_cycle, solve
from solver.bruteforce import solve_exact
from solver.instance import Instance, load_instance
from solver.penalty import penalty
from solver.validate import check, p_base

ROOT = Path(__file__).resolve().parent.parent
CAP = [32, 128, 8, 6.0]


def make(n, K, conflicts=(), resources=None, capacities=None, windows=None, weights=None):
    return Instance(tasks=[f"T{i}" for i in range(n)], conflicts=list(conflicts),
                    resources=resources or [[1, 1, 1, 0.5]] * n,
                    capacities=capacities or [CAP[:] for _ in range(K)],
                    windows=windows or [(0, K - 1)] * n,
                    weights=weights or [1.0] * n, K=K)


# ---- the four tests required by Task 5 -------------------------------

class RequiredEdgeCasesTest(unittest.TestCase):
    def test_all_conflict_graph_chromatic_number_above_K(self):
        """K_{K+1} with every window covering all slots: needs K+1 colours."""
        for K in (2, 3, 5):
            n = K + 1
            inst = make(n, K, conflicts=[(i, j) for i in range(n) for j in range(i + 1, n)])
            sigma, reason = solve(inst)
            self.assertTrue(reason.startswith("PROVEN_INFEASIBLE"), reason)
            self.assertEqual(solve_exact(inst).status, "infeasible")

    def test_all_conflict_graph_with_exactly_K_tasks_is_feasible(self):
        K = 4
        inst = make(K, K, conflicts=[(i, j) for i in range(K) for j in range(i + 1, K)])
        sigma, reason = solve(inst)
        self.assertEqual(reason, "")
        self.assertEqual(sorted(sigma), list(range(K)))

    def test_zero_capacity_slot_is_never_used(self):
        caps = [CAP[:], [0, 0, 0, 0], CAP[:]]
        inst = make(4, 3, capacities=caps)
        sigma, reason = solve(inst)
        self.assertEqual(reason, "")
        self.assertEqual(check(inst, sigma), [])
        self.assertNotIn(1, sigma)

    def test_zero_capacity_slot_only_option_is_proven_infeasible(self):
        caps = [CAP[:], [0, 0, 0, 0], CAP[:]]
        inst = make(2, 3, capacities=caps, windows=[(0, 2), (1, 1)])
        sigma, reason = solve(inst)
        self.assertTrue(reason.startswith("PROVEN_INFEASIBLE: task T1 fits in no slot"), reason)

    def test_tight_sla_windows_pin_every_task(self):
        """Width-1 windows leave no choice: the only schedule must be found."""
        inst = make(4, 4, conflicts=[(0, 1), (1, 2), (2, 3)],
                    windows=[(0, 0), (1, 1), (2, 2), (3, 3)])
        sigma, reason = solve(inst)
        self.assertEqual((sigma, reason), ([0, 1, 2, 3], ""))

    def test_tight_sla_windows_that_clash_are_proven_infeasible(self):
        inst = make(2, 3, conflicts=[(0, 1)], windows=[(1, 1), (1, 1)])
        sigma, reason = solve(inst)
        self.assertTrue(reason.startswith("PROVEN_INFEASIBLE: a conflicting pair"), reason)

    def test_tight_windows_with_capacity_forcing_order(self):
        """Width-2 windows; capacity lets only one task per slot."""
        inst = make(2, 2, resources=[[20, 1, 1, 1], [20, 1, 1, 1]],
                    windows=[(0, 1), (0, 1)], weights=[1, 5])
        sigma, reason = solve(inst)
        self.assertEqual(reason, "")
        self.assertEqual(sigma, [1, 0])  # heavier task takes the earlier slot

    def test_single_task(self):
        inst = make(1, 3, windows=[(1, 2)], weights=[7.0])
        sigma, reason = solve(inst)
        self.assertEqual((sigma, reason), ([1], ""))
        self.assertEqual(p_base(inst, sigma), 14.0)


# ---- viva perturbations: a 5th dimension and unequal capacities ------

class PerturbationTest(unittest.TestCase):
    def test_five_dimensions(self):
        inst = make(3, 2, resources=[[1, 1, 1, 1, 3]] * 3,
                    capacities=[[32, 128, 8, 6, 4], [32, 128, 8, 6, 6]])
        sigma, reason = solve(inst)
        self.assertEqual(reason, "")
        self.assertEqual(check(inst, sigma), [])
        self.assertEqual(sorted(sigma), [0, 1, 1])  # 5th dim lets one task into slot 0

    def test_unequal_capacities(self):
        caps = [[8, 32, 2, 1.5], CAP[:], CAP[:]]
        inst = make(3, 3, resources=[[8, 32, 2, 1.5]] * 3)
        inst.capacities = caps
        sigma, reason = solve(inst)
        self.assertEqual(reason, "")
        self.assertEqual(check(inst, sigma), [])
        self.assertEqual(sigma.count(0), 1)


# ---- soundness against the exact solver ------------------------------

class SoundnessTest(unittest.TestCase):
    def test_against_brute_force_on_random_instances(self):
        """Feasible outputs pass the validator; PROVEN_INFEASIBLE is never wrong;
        the heuristic is never better than the optimum (sanity check of both)."""
        for n, K, dens in [(6, 3, 0.3), (8, 4, 0.4), (10, 4, 0.4)]:
            for seed in range(40):
                inst = Instance(**generate_instance(n, K, conflict_density=dens, seed=seed))
                sigma, reason = solve(inst)
                exact = solve_exact(inst, objective=penalty)
                if reason == "":
                    self.assertEqual(check(inst, sigma), [], (n, K, seed))
                    self.assertGreaterEqual(penalty(inst, sigma), exact.value - 1e-9)
                elif reason.startswith("PROVEN_INFEASIBLE"):
                    self.assertEqual(exact.status, "infeasible", (n, K, seed))

    def test_not_found_keeps_partial_assignment_valid(self):
        """Partial output has no conflict, capacity or window violation among placed tasks."""
        for seed in range(300):
            inst = Instance(**generate_instance(10, 3, conflict_density=0.4, seed=seed))
            sigma, reason = solve(inst)
            if reason.startswith("NOT_FOUND"):
                errors = [e for e in check(inst, sigma) if "unassigned" not in e]
                self.assertEqual(errors, [], seed)

    def test_odd_cycle_certificate_is_genuine(self):
        inst = Instance(**generate_instance(200, 20, conflict_density=0.1, seed=22))
        adj = [set() for _ in range(inst.n)]
        for i, j in inst.conflicts:
            adj[i].add(j)
            adj[j].add(i)
        confined = [i for i in range(inst.n) if inst.windows[i][0] >= 18]
        cycle = odd_cycle(confined, adj)
        self.assertEqual(len(cycle) % 2, 1)
        for a, b in zip(cycle, cycle[1:] + cycle[:1]):
            self.assertIn(b, adj[a])

    def test_greedy_clique_is_a_clique(self):
        inst = Instance(**generate_instance(100, 10, conflict_density=0.3, seed=11))
        adj = [set() for _ in range(inst.n)]
        for i, j in inst.conflicts:
            adj[i].add(j)
            adj[j].add(i)
        clique = largest_greedy_clique(list(range(inst.n)), adj)
        for x in clique:
            for y in clique:
                if x != y:
                    self.assertIn(y, adj[x])


# ---- Task 4: the tight example reaches the bound exactly -------------

class TightExampleTest(unittest.TestCase):
    def test_ratio_equals_K(self):
        for K in (2, 4):
            inst = load_instance(ROOT / "instances" / f"tight_K{K}.json")
            sigma, reason = solve(inst)
            self.assertEqual(reason, "")
            self.assertEqual(p_base(inst, sigma) / solve_exact(inst).value, K)


class CliTest(unittest.TestCase):
    def test_heuristic_cli_on_toy(self):
        out = subprocess.run([sys.executable, str(ROOT / "run.py"), "--input", "instances/toy.json"],
                             capture_output=True, text=True, check=True, cwd=ROOT).stdout
        res = json.loads(out)
        self.assertTrue(res["feasible"])
        self.assertEqual(len(res["assignment"]), 6)


if __name__ == "__main__":
    unittest.main()
