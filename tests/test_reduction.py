import unittest

from solver.bruteforce import solve_exact
from tools.reduction import GRAPHS, colouring_from, reduce_3col, three_colourable


class ReductionTest(unittest.TestCase):
    def test_feasible_iff_three_colourable(self):
        for name, (m, edges) in GRAPHS.items():
            res = solve_exact(reduce_3col(m, edges))
            self.assertEqual(res.status == "optimal", three_colourable(m, edges), name)
            if res.status == "optimal":
                col = colouring_from(res.sigma, m)
                self.assertTrue(all(col[a] != col[b] for a, b in edges), name)

    def test_every_gadget_is_needed(self):
        m, edges = GRAPHS["K4"]
        for drop in ("F1", "F2", "F3"):
            self.assertEqual(solve_exact(reduce_3col(m, edges, drop=drop)).status, "optimal", drop)


if __name__ == "__main__":
    unittest.main()
