"""Feasibility checks F1-F3 and the base penalty.

Kept independent of every solver so that it can act as the referee: tests
run each solver's output through `check`, and a solver bug cannot hide
behind a shared helper.

An assignment `sigma` is a list where sigma[i] is the 0-based slot of task
i, or None if task i is unassigned.
"""

from solver.instance import Instance

# Generator resources are floats, so a slot filled "exactly" to capacity can
# overshoot by rounding error. 1e-9 is far below any real resource unit.
EPS = 1e-9


def slot_loads(inst: Instance, sigma) -> list[list[float]]:
    """Return load[s][k], the summed demand of dimension k in slot s.

    Unassigned tasks (None) are skipped, so partial assignments also work.
    """
    load = [[0.0] * inst.d for _ in range(inst.K)]
    for i, s in enumerate(sigma):
        if s is None:
            continue
        for k, r in enumerate(inst.resources[i]):
            load[s][k] += r
    return load


def check(inst: Instance, sigma) -> list[str]:
    """Return every violation of F1, F2, F3 as text; an empty list means feasible.

    All violations are listed, not just the first one: a debugging run then
    shows every broken constraint at once. A task that is unassigned or
    placed outside 0..K-1 is reported and then left out of the F1/F2 checks.
    """
    errors = []
    if len(sigma) != inst.n:
        return [f"assignment has {len(sigma)} entries, expected {inst.n}"]

    placed = [False] * inst.n
    for i, s in enumerate(sigma):
        name = inst.tasks[i]
        if s is None:
            errors.append(f"{name} is unassigned")
        elif not 0 <= s < inst.K:
            errors.append(f"{name} is in slot {s}, outside 0..{inst.K - 1}")
        else:
            placed[i] = True
            lo, hi = inst.windows[i]
            if not lo <= s <= hi:
                errors.append(f"F3: {name} in slot {s}, window [{lo}, {hi}]")

    for i, j in inst.conflicts:
        if placed[i] and placed[j] and sigma[i] == sigma[j]:
            errors.append(f"F1: {inst.tasks[i]} and {inst.tasks[j]} share slot {sigma[i]}")

    load = slot_loads(inst, [s if placed[i] else None for i, s in enumerate(sigma)])
    for s in range(inst.K):
        for k in range(inst.d):
            if load[s][k] > inst.capacities[s][k] + EPS:
                errors.append(f"F2: slot {s} dim {k} load {load[s][k]:.4f} "
                              f"> capacity {inst.capacities[s][k]}")
    return errors


def is_feasible(inst: Instance, sigma) -> bool:
    return not check(inst, sigma)


def p_base(inst: Instance, sigma) -> float:
    """P_base = sum of w_i * (sigma_i + 1).

    The +1 converts our 0-based slots back to the spec's 1-based slot index,
    so slot 0 still costs w_i and the optimum is never 0. This matters
    because an approximation ratio against an optimum of 0 is undefined.
    """
    return sum(w * (s + 1) for w, s in zip(inst.weights, sigma))
