"""Instance and result data classes plus JSON I/O.

Boilerplate only (assignment line 134): no feasibility or scheduling logic
lives here. Slots are 0-based, matching generator.py (see README).
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Instance:
    """One scheduling instance in the generator's format.

    The number of resource dimensions and the per-slot capacities are read
    from the data, not hard-coded, so hand-written instances with d != 4 or
    unequal slot capacities load the same way as generator output.
    """

    tasks: list[str]
    conflicts: list[tuple[int, int]]
    resources: list[list[float]]
    capacities: list[list[float]]
    windows: list[tuple[int, int]]
    weights: list[float]
    K: int

    @property
    def n(self) -> int:
        return len(self.tasks)

    @property
    def d(self) -> int:
        return len(self.capacities[0]) if self.capacities else 0

    def __post_init__(self):
        self.conflicts = [tuple(e) for e in self.conflicts]
        self.windows = [tuple(w) for w in self.windows]
        self._check_shape()

    def _check_shape(self):
        """Reject malformed input early, so later code can trust the shapes.

        Only structural checks: lengths, index ranges, window order. Whether
        an assignment respects conflicts, capacity or windows is not checked
        here.
        """
        n, K = self.n, self.K
        if len(self.capacities) != K:
            raise ValueError(f"expected {K} capacity vectors, got {len(self.capacities)}")
        for name in ("resources", "windows", "weights"):
            if len(getattr(self, name)) != n:
                raise ValueError(f"expected {n} {name}, got {len(getattr(self, name))}")
        d = self.d
        for s, c in enumerate(self.capacities):
            if len(c) != d:
                raise ValueError(f"capacity of slot {s} has {len(c)} dimensions, expected {d}")
        for i, r in enumerate(self.resources):
            if len(r) != d:
                raise ValueError(f"resources of task {i} have {len(r)} dimensions, expected {d}")
        for i, j in self.conflicts:
            if not (0 <= i < n and 0 <= j < n) or i == j:
                raise ValueError(f"bad conflict edge ({i}, {j})")
        for i, (lo, hi) in enumerate(self.windows):
            if not 0 <= lo <= hi < K:
                raise ValueError(f"window of task {i} is [{lo}, {hi}], outside slots 0..{K - 1}")


def load_instance(path) -> Instance:
    with open(path, encoding="utf-8") as f:
        return Instance(**json.load(f))


def save_instance(inst: Instance, path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(inst), f, indent=1)


@dataclass
class Result:
    """Solver output with exactly the five keys required by assignment line 131."""

    assignment: dict[str, int] = field(default_factory=dict)
    penalty: float = 0.0
    runtime_ms: int = 0
    feasible: bool = False
    violation_reason: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1)


def save_result(res: Result, path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(res.to_json())
