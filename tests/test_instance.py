import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from generator import generate_instance
from solver.instance import Instance, Result, load_instance, save_instance

ROOT = Path(__file__).resolve().parent.parent
GENERATOR_SHA256 = "0d97463215c0edbec3163178a7534f74451519ba05f8170dbc102d48c73f8b65"


def toy_dict():
    return json.loads((ROOT / "instances" / "toy.json").read_text(encoding="utf-8"))


class GeneratorTest(unittest.TestCase):
    def test_generator_is_unmodified(self):
        digest = hashlib.sha256((ROOT / "generator.py").read_bytes()).hexdigest()
        self.assertEqual(digest, GENERATOR_SHA256)

    def test_generator_output_loads_as_instance(self):
        inst = Instance(**generate_instance(12, 4, conflict_density=0.5, seed=3))
        self.assertEqual((inst.n, inst.K, inst.d), (12, 4, 4))


class ToyInstanceTest(unittest.TestCase):
    def test_toy_matches_spec_with_windows_shifted(self):
        inst = load_instance(ROOT / "instances" / "toy.json")
        self.assertEqual((inst.n, inst.K, inst.d), (6, 4, 4))
        self.assertEqual(inst.conflicts, [(0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 5)])
        self.assertEqual(inst.resources, [[8, 32, 4, 1.5], [4, 16, 0, 3.0], [2, 8, 0, 2.0],
                                          [16, 64, 2, 0.5], [8, 32, 2, 1.0], [4, 16, 0, 1.5]])
        self.assertEqual(inst.capacities, [[32, 128, 8, 6.0]] * 4)
        self.assertEqual(inst.weights, [5, 4, 3, 2, 3, 2])
        spec_windows = [(1, 3), (1, 4), (1, 4), (2, 4), (1, 4), (2, 4)]
        self.assertEqual(inst.windows, [(lo - 1, hi - 1) for lo, hi in spec_windows])


class CensusTest(unittest.TestCase):
    def test_census_prints_one_row_per_benchmark(self):
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "census.py")],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(len(out.strip().splitlines()), 9)


class RoundTripTest(unittest.TestCase):
    def test_save_then_load_is_identity(self):
        inst = load_instance(ROOT / "instances" / "toy.json")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "toy.json"
            save_instance(inst, path)
            self.assertEqual(load_instance(path), inst)


class ShapeCheckTest(unittest.TestCase):
    def test_accepts_five_dims_and_unequal_capacities(self):
        data = toy_dict()
        data["resources"] = [r + [1] for r in data["resources"]]
        data["capacities"] = [[32, 128, 8, 6.0, 4], [16, 64, 4, 3.0, 2],
                              [0, 0, 0, 0, 0], [32, 128, 8, 6.0, 4]]
        self.assertEqual(Instance(**data).d, 5)

    def test_rejects_window_past_last_slot(self):
        data = toy_dict()
        data["windows"][0] = [1, 4]  # 1-based spec value, not shifted
        with self.assertRaises(ValueError):
            Instance(**data)

    def test_rejects_dimension_mismatch(self):
        data = toy_dict()
        data["resources"][2] = [2, 8, 0]
        with self.assertRaises(ValueError):
            Instance(**data)

    def test_rejects_self_conflict(self):
        data = toy_dict()
        data["conflicts"].append([3, 3])
        with self.assertRaises(ValueError):
            Instance(**data)


class ResultTest(unittest.TestCase):
    def test_result_json_has_exactly_the_five_required_keys(self):
        keys = set(json.loads(Result().to_json()))
        self.assertEqual(keys, {"assignment", "penalty", "runtime_ms",
                                "feasible", "violation_reason"})


if __name__ == "__main__":
    unittest.main()
