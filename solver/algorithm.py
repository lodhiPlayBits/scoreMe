"""SSD-R: SLA-Slack DSATUR with Certified infeasibility and Repair (Task 3).

Four stages. The comments "Lnn" refer to the numbered pseudocode lines in
report/sections/t3_algorithm.tex.

  Stage 1  certify   cheap necessary conditions; if one fails, the instance
                     is PROVEN infeasible (L1-L4)
  Stage 2  construct saturation-ordered greedy: always place the task with
                     the fewest feasible slots left (L5-L11), restarted
                     with failed tasks promoted (R1-R3)
  Stage 3  repair    when a task has no feasible slot, evict its blockers
                     from one slot into other slots (L12-L17)
  Stage 4  improve   first-improvement local search with moves and swaps,
                     minimising the full penalty P (L18-L21)

Every step that changes the assignment first checks F1, F2 and F3, so the
algorithm never holds an infeasible partial assignment (the soundness
proof in Task 4 rests on this).

solve() returns (sigma, reason):
  reason == ""                    sigma is complete and feasible
  reason "PROVEN_INFEASIBLE: ..."  no feasible assignment exists; sigma is all None
  reason "NOT_FOUND: ..."          the heuristic gave up; sigma is the partial assignment
"""

from solver.instance import Instance
from solver.penalty import LAMBDA_BAL, LAMBDA_RISK
from solver.validate import EPS

MAX_LS_PASSES = 50


class State:
    """Assignment plus the incremental bookkeeping that makes each check O(d).

    conf[i][s] counts the conflict neighbours of task i currently placed in
    slot s. A conflict check is then one lookup, not a scan of i's
    neighbours. For the imbalance term B, the per-dimension sums of u and u^2
    over usable slots are kept, so a move changes B in O(d) instead of
    O(K*d).
    """

    def __init__(self, inst: Instance):
        self.inst = inst
        n, K, d = inst.n, inst.K, inst.d
        self.adj = [set() for _ in range(n)]
        for i, j in inst.conflicts:
            self.adj[i].add(j)
            self.adj[j].add(i)
        self.sigma = [None] * n
        self.load = [[0.0] * d for _ in range(K)]
        self.conf = [[0] * K for _ in range(n)]
        self.W = sum(inst.weights)
        # usable (slot, dim) cells for the B term, see penalty.load_imbalance
        self.usable = [[inst.capacities[s][k] > 0 for k in range(d)] for s in range(K)]
        self.m = [sum(self.usable[s][k] for s in range(K)) for k in range(d)]
        self.cells = sum(self.m)
        self.s1 = [0.0] * d   # sum of u over usable slots, per dim
        self.s2 = [0.0] * d   # sum of u^2

    # ---- feasibility ---------------------------------------------------
    def fits(self, i, s, ignore=()) -> bool:
        """F2 check for adding task i to slot s; tasks in `ignore` are treated
        as already removed from s (used by swaps and repair)."""
        inst = self.inst
        for k in range(inst.d):
            extra = sum(inst.resources[j][k] for j in ignore if self.sigma[j] == s)
            if self.load[s][k] - extra + inst.resources[i][k] > inst.capacities[s][k] + EPS:
                return False
        return True

    def can_place(self, i, s, ignore=()) -> bool:
        """F3, F1 and F2 for putting task i into slot s."""
        lo, hi = self.inst.windows[i]
        if not lo <= s <= hi:
            return False
        blocking = self.conf[i][s] - sum(1 for j in ignore if j in self.adj[i] and self.sigma[j] == s)
        return blocking == 0 and self.fits(i, s, ignore)

    def feasible_slots(self, i) -> list[int]:
        lo, hi = self.inst.windows[i]
        return [s for s in range(lo, hi + 1) if self.can_place(i, s)]

    # ---- mutation ------------------------------------------------------
    def _add(self, i, s, sign):
        inst = self.inst
        for k in range(inst.d):
            if self.usable[s][k]:
                u_old = self.load[s][k] / inst.capacities[s][k]
            self.load[s][k] += sign * inst.resources[i][k]
            if self.usable[s][k]:
                u_new = self.load[s][k] / inst.capacities[s][k]
                self.s1[k] += u_new - u_old
                self.s2[k] += u_new * u_new - u_old * u_old
        for j in self.adj[i]:
            self.conf[j][s] += sign

    def place(self, i, s):
        self.sigma[i] = s
        self._add(i, s, +1)

    def remove(self, i):
        s = self.sigma[i]
        self._add(i, s, -1)
        self.sigma[i] = None

    # ---- objective -----------------------------------------------------
    def task_cost(self, i, s) -> float:
        """The separable part of P for task i in slot s: P_base plus R."""
        w = self.inst.weights[i]
        lo, hi = self.inst.windows[i]
        risk = ((s - lo) / (hi - lo)) ** 2 if hi > lo else 0.0
        return w * (s + 1) + LAMBDA_RISK * w * risk

    def imbalance(self, s1=None, s2=None) -> float:
        """B term from the running sums. Each dim's variance sum is
        sum(u^2) - (sum u)^2 / m."""
        s1 = s1 or self.s1
        s2 = s2 or self.s2
        if self.cells == 0:
            return 0.0
        sq = sum(s2[k] - s1[k] ** 2 / self.m[k] for k in range(self.inst.d) if self.m[k])
        return self.W * sq / self.cells

    def imbalance_delta(self, changes) -> float:
        """Change in LAMBDA_BAL * B if the loads change by `changes`, a list of
        (slot, task, sign). Computed in O(d * len(changes)) without
        touching the state."""
        inst = self.inst
        s1, s2 = self.s1[:], self.s2[:]
        delta_load = {}
        for s, i, sign in changes:
            row = delta_load.setdefault(s, [0.0] * inst.d)
            for k in range(inst.d):
                row[k] += sign * inst.resources[i][k]
        for s, row in delta_load.items():
            for k in range(inst.d):
                if self.usable[s][k] and row[k]:
                    c = inst.capacities[s][k]
                    u_old = self.load[s][k] / c
                    u_new = (self.load[s][k] + row[k]) / c
                    s1[k] += u_new - u_old
                    s2[k] += u_new * u_new - u_old * u_old
        return LAMBDA_BAL * (self.imbalance(s1, s2) - self.imbalance())


# ======================================================================
# Stage 1: certify infeasibility
# ======================================================================

def certify_infeasible(inst: Instance, adj) -> str:
    """Return a reason string if a necessary condition fails, else "".

    Each check is a valid proof of infeasibility (Task 4, Lemma 2):
    - L1  a task that does not fit, even alone, into any slot of its window
          cannot be placed in any schedule.
    - L3  the tasks whose windows lie inside [a, b] must all run in slots
          a..b, so their total demand in each dim must fit the total
          capacity of those slots.
    - L4  the conflict graph of those tasks must be (b-a+1)-colourable.
          Width 1: no edge at all. Width 2: bipartite, checked exactly by
          BFS. Width 3 or more: a clique larger than the width is a proof.
          It is found greedily, so this case is sound but not complete.
    Cost: O(K^2 * (n*d + n^2 * omega)), polynomial.
    """
    n, K, d = inst.n, inst.K, inst.d
    for i in range(n):                                                # L1
        lo, hi = inst.windows[i]
        if not any(all(inst.resources[i][k] <= inst.capacities[s][k] + EPS for k in range(d))
                   for s in range(lo, hi + 1)):
            return f"task {inst.tasks[i]} fits in no slot of its window [{lo}, {hi}]"

    for a in range(K):                                                # L2
        for b in range(a, K):
            inside = [i for i in range(n) if a <= inst.windows[i][0] and inst.windows[i][1] <= b]
            if not inside:
                continue
            for k in range(d):                                        # L3
                demand = sum(inst.resources[i][k] for i in inside)
                cap = sum(inst.capacities[s][k] for s in range(a, b + 1))
                if demand > cap + EPS:
                    return (f"tasks confined to slots [{a}, {b}] need {demand:.3f} of dim {k}, "
                            f"those slots offer only {cap:.3f}")
            width = b - a + 1                                         # L4
            if width <= 2:
                cycle = odd_cycle(inside, adj) if width == 2 else edge_in(inside, adj)
                if cycle:
                    names = ", ".join(inst.tasks[i] for i in cycle)
                    what = "an odd conflict cycle" if width == 2 else "a conflicting pair"
                    return (f"{what} ({names}) is confined to the {width} slot(s) [{a}, {b}], "
                            f"which needs more than {width} colours")
            else:
                clique = largest_greedy_clique(inside, adj)
                if len(clique) > width:
                    names = ", ".join(inst.tasks[i] for i in clique)
                    return (f"{len(clique)} mutually conflicting tasks ({names}) are confined "
                            f"to the {width} slots [{a}, {b}]")
    return ""


def edge_in(nodes, adj) -> list:
    """Any conflict edge inside `nodes`: tasks confined to one slot must not conflict."""
    inside = set(nodes)
    for i in nodes:
        for j in adj[i]:
            if j in inside:
                return [i, j]
    return []


def odd_cycle(nodes, adj) -> list:
    """Return an odd cycle in the conflict graph induced by `nodes`, or [].

    Tasks confined to two slots can be scheduled only if that subgraph is
    2-colourable, i.e. bipartite. So for width-2 ranges this check is
    exact, not a heuristic. BFS 2-colours each component. An edge with both
    ends the same colour closes an odd cycle, which is then rebuilt from the
    BFS parents as a certificate the reader can check by hand.
    O(|nodes| + edges).
    """
    inside = set(nodes)
    colour, parent, depth = {}, {}, {}
    for root in nodes:
        if root in colour:
            continue
        colour[root], parent[root], depth[root] = 0, None, 0
        queue = [root]
        for u in queue:
            for v in adj[u]:
                if v not in inside:
                    continue
                if v not in colour:
                    colour[v], parent[v], depth[v] = 1 - colour[u], u, depth[u] + 1
                    queue.append(v)
                elif colour[v] == colour[u]:
                    # climb from both ends to the common ancestor
                    left, right = [u], [v]
                    x, y = u, v
                    while x != y:
                        if depth[x] >= depth[y]:
                            x = parent[x]
                            left.append(x)
                        else:
                            y = parent[y]
                            right.append(y)
                    return left + right[-2::-1]
    return []


def largest_greedy_clique(nodes, adj) -> list:
    """Best clique found by growing greedily from every start node.

    Starting from every node, not just the highest-degree one, finds cliques
    that a single greedy pass misses. It is still a heuristic: max clique is
    NP-hard, so a large clique can go unnoticed and the instance is then
    reported NOT_FOUND, not PROVEN_INFEASIBLE.
    O(|nodes|^2 * clique size).
    """
    best = []
    order = sorted(nodes, key=lambda i: -len(adj[i]))
    for start in order:
        clique = [start]
        for i in order:
            if i != start and all(j in adj[i] for j in clique):
                clique.append(i)
        if len(clique) > len(best):
            best = clique
    return best


# ======================================================================
# Stage 3: repair
# ======================================================================

def repair(st: State, i, trace) -> int | None:
    """Make room for task i in one slot of its window, or return None.

    For each slot s, lowest first, the blockers are i's conflict neighbours
    in s. If i still does not fit in s, the largest tasks in s (by their
    share of the dimension that overflows) are added until i fits. Every
    blocker must then move to another feasible slot. All moves are applied
    tentatively and rolled back if any blocker cannot move, so a failed
    repair leaves the state unchanged.

    Why one level deep: the evicted tasks may only go to slots that are
    already feasible for them. No chain of evictions is tried, which keeps
    the cost polynomial: O(K * n * K * d) per call.
    """
    inst = st.inst
    lo, hi = inst.windows[i]
    for s in range(lo, hi + 1):                                       # L12
        members = [j for j in range(inst.n) if st.sigma[j] == s]
        blockers = [j for j in members if j in st.adj[i]]             # L13
        others = [j for j in members if j not in st.adj[i]]

        def overflow(bl):
            return [k for k in range(inst.d)
                    if st.load[s][k] - sum(inst.resources[j][k] for j in bl)
                    + inst.resources[i][k] > inst.capacities[s][k] + EPS]

        while overflow(blockers) and others:                          # L14
            k = overflow(blockers)[0]
            big = max(others, key=lambda j: inst.resources[j][k])
            others.remove(big)
            blockers.append(big)
        if overflow(blockers):
            continue

        moved = []                                                    # L15
        for j in blockers:
            st.remove(j)
            moved.append((j, s))
        ok = True
        for j, _ in moved:
            # i is not placed yet, but slot s is reserved for it: j must
            # leave s, and must not take the room i needs.
            options = [t for t in st.feasible_slots(j) if t != s]
            if not options:
                ok = False
                break
            t = min(options, key=lambda t: st.task_cost(j, t))
            st.place(j, t)
        if ok and st.can_place(i, s):                                 # L16
            if trace is not None:
                trace.append(f"  repair: moved {[inst.tasks[j] for j, _ in moved]} "
                             f"out of slot {s} to make room for {inst.tasks[i]}")
            return s
        for j, orig in moved:                                         # roll back
            if st.sigma[j] is not None:
                st.remove(j)
            st.place(j, orig)
    return None                                                       # L17


# ======================================================================
# Stage 4: local search
# ======================================================================

def local_search(st: State, trace) -> int:
    """First-improvement descent on P with two move types.

    - move: one task to another slot of its window (L19).
    - swap: two tasks in different slots exchange slots (L20). A swap can
      fix cases a move cannot. If slot 0 is full, a heavy task in slot 1 and
      a light task in slot 0 can still trade places.
    A step is taken only if it is feasible and lowers P by more than EPS,
    so P strictly decreases and the search cannot cycle. The number of
    passes is capped at MAX_LS_PASSES, and each pass is O(n^2 * d), so the
    stage is polynomial.
    Returns the number of improving steps applied.
    """
    inst = st.inst
    n = inst.n
    steps = 0
    for _ in range(MAX_LS_PASSES):                                    # L18
        improved = False
        for i in range(n):                                            # L19
            s = st.sigma[i]
            lo, hi = inst.windows[i]
            for t in range(lo, hi + 1):
                if t == s or not st.can_place(i, t):
                    continue
                delta = (st.task_cost(i, t) - st.task_cost(i, s)
                         + st.imbalance_delta([(s, i, -1), (t, i, +1)]))
                if delta < -EPS:
                    st.remove(i)
                    st.place(i, t)
                    s = t
                    steps += 1
                    improved = True
        for i in range(n):                                            # L20
            for j in range(i + 1, n):
                si, sj = st.sigma[i], st.sigma[j]
                if si == sj:
                    continue
                if not (st.can_place(i, sj, ignore=(j,)) and st.can_place(j, si, ignore=(i,))):
                    continue
                delta = (st.task_cost(i, sj) + st.task_cost(j, si)
                         - st.task_cost(i, si) - st.task_cost(j, sj)
                         + st.imbalance_delta([(si, i, -1), (sj, j, -1), (sj, i, +1), (si, j, +1)]))
                if delta < -EPS:
                    st.remove(i)
                    st.remove(j)
                    st.place(i, sj)
                    st.place(j, si)
                    steps += 1
                    improved = True
        if not improved:
            break
    if trace is not None:
        trace.append(f"local search: {steps} improving steps")
    return steps


# ======================================================================
# Driver
# ======================================================================

def takes_last_option(st: State, i, s, unplaced, options) -> bool:
    """Forward check for L10: would putting i in s kill another task's only slot?

    That happens when an unplaced task j has s as its last feasible slot,
    and j either conflicts with i or no longer fits in s once i is there.
    Without this check the cheapest-slot rule walks into dead ends that the
    restarts cannot escape. On generator instance (100, 10, 0.05, seed 1),
    four tasks with nested 2-3 slot windows kept squeezing each other out in
    a cycle, pass after pass. Cost: O(n * d) per candidate slot.
    """
    inst = st.inst
    for j in unplaced:
        if j == i or options[j] != [s]:
            continue
        if j in st.adj[i]:
            return True
        if any(st.load[s][k] + inst.resources[i][k] + inst.resources[j][k]
               > inst.capacities[s][k] + EPS for k in range(inst.d)):
            return True
    return False


def construct(inst: Instance, promoted: list, trace):
    """Stage 2 (+3): one saturation-greedy pass. Returns (state, failed_task).

    failed_task is None on success. Otherwise it is the task that had no
    slot even after repair; the state then holds the partial assignment.
    """
    st = State(inst)
    rank = {t: r for r, t in enumerate(promoted)}
    unplaced = set(range(inst.n))                                     # L5
    while unplaced:                                                   # L6
        options = {i: st.feasible_slots(i) for i in unplaced}         # L7
        # L8: promoted tasks (failures of earlier passes) go first, latest
        # failure first. Otherwise fewest options first (DSATUR saturation,
        # generalised to windows and capacity). Ties: more conflicts, then
        # heavier weight, then lower index for determinism.
        i = min(unplaced, key=lambda i: (rank.get(i, len(rank)), len(options[i]),
                                         -len(st.adj[i]), -inst.weights[i], i))
        slots = options[i]
        if not slots:                                                 # L9
            s = repair(st, i, trace)
            if s is None:
                return st, i
            slots = [s]
        # L10: forward check, then the cheapest slot by marginal P (ties go
        # to the lower slot)
        safe = [s for s in slots if not takes_last_option(st, i, s, unplaced, options)] or slots
        s = min(safe, key=lambda s: (st.task_cost(i, s) + st.imbalance_delta([(s, i, +1)]), s))
        st.place(i, s)
        unplaced.discard(i)                                           # L11
        if trace is not None:
            trace.append(f"place {inst.tasks[i]}: options {slots} -> slot {s}")
    return st, None


def solve(inst: Instance, trace: list | None = None):
    """Run SSD-R. Returns (sigma, reason); see the module docstring.

    Pass a list as `trace` to collect a step-by-step log, which can be
    compared against a hand trace in the viva.

    Restarts ("squeaky wheel"): if a pass fails on task i, i is promoted to
    the front of the order and the pass is rerun. A task that fails late
    was usually squeezed out by earlier choices, and placing it first lets
    the others fit around it. There are at most n passes, each polynomial,
    so the whole algorithm stays polynomial.
    """
    adj = State(inst).adj
    reason = certify_infeasible(inst, adj)                            # Stage 1
    if reason:
        return [None] * inst.n, "PROVEN_INFEASIBLE: " + reason

    promoted = []
    for attempt in range(inst.n):                                     # R1
        st, failed = construct(inst, promoted, trace)                 # R2
        if failed is None:
            break
        if trace is not None:
            trace.append(f"pass {attempt + 1} failed on {inst.tasks[failed]}; promoting it")
        if failed in promoted:
            promoted.remove(failed)
        promoted.insert(0, failed)                                    # R3
    else:
        placed = sum(s is not None for s in st.sigma)
        return st.sigma, (f"NOT_FOUND: after {inst.n} passes, {inst.tasks[failed]} "
                          f"(window {list(inst.windows[failed])}) still had no feasible slot "
                          f"and repair failed; {placed} of {inst.n} tasks placed")

    local_search(st, trace)                                           # Stage 4
    return st.sigma, ""                                               # L21
