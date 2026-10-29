# Roadmap: ScoreMe MSME Pipeline Scheduling Assignment (v2)

- **Date:** 2026-10-29
- **Status:** active. v2 replaces v1.
- **Source:** `ScoreMe_MSME_Pipeline_Scheduling_Assignment_No_AI_Restrictions.pdf`

## What changed from v1

- **No AI rules.** The new spec has no AI restrictions and no AI usage log. The [CANDIDATE]/[AI-OK] tags, rule A4, the AI log, Q2 and Q3 are all removed.
- **The Task 5 title says "Java", but the body says Python 3.10+**, and Java needs prior written approval. We stay with **Python**.
- **The viva (T8, 30 pts) is still the main risk.** A score below 15/30 caps the total at 120/200, so you must be able to explain every line yourself. The drills stay in the plan.

## Goal

A submission scoring 100/200 or more (target 150+), made of:

- one report (PDF) with sections T1 to T8
- the repo: code, tests, `run.py`, benchmark CSV and charts

## Current state (checked 2026-10-29)

| Item | Status |
|---|---|
| Repo, `generator.py` unmodified (sha256 checked by a test) | Done |
| `solver/instance.py`: `Instance`/`Result` classes, JSON I/O, shape checks for any d and per-slot capacities | Done |
| `instances/toy.json`: toy instance with 0-based windows | Done |
| `tools/census.py`: statistics for the 9 benchmarks | Done |
| `tests/test_instance.py`: 10 tests | Pass |
| Slot convention: 0-based, penalty charges σ+1 | Decided (see README) |
| Validator, brute force, `run.py` (Phase A) | Done 2026-10-29: 22 tests pass |
| Penalty P (T2): `solver/penalty.py`, `report/sections/t2_penalty.tex` (Phase B) | Done 2026-10-29: 30 tests pass |
| Algorithm (T3), proofs (T1, T4) | **Not started** |
| Benchmarks, report, journal (T6, T7) | **Not started** |

Everything is on `main` as one commit. v1 planned a `chore/scaffold` branch, which was not created.

### What the census shows (raw output from `tools/census.py`)

| Instance | Dimension over total capacity | Consequence |
|---|---|---|
| n=150 K=12 seed=12 | Net 82.8 > 72 | Infeasible |
| n=200 K=15 seed=20 | Net 94.6 > 90 | Infeasible |
| n=200 K=5 seed=21 | GPU 103.8 > 40, Net 98.2 > 30 | Infeasible |

- **Why this happens:** when `cap[d] // (n//K+1)` is 0 or 1, the generator draws resources from `uniform(1, 0)` or `uniform(1, 1)`, so every task needs roughly 0.5 to 1 unit. The Net and GPU totals then exceed capacity.
- **Consequence:** these 3 rows must come out `feasible=false`, with a *proof-based* `violation_reason`. That is the "correct infeasibility detection" the T5 rubric asks for. Explaining these rows is also your T6 anomaly analysis.
- **The other 6 instances still need checking.** A global sum below capacity does not make an instance feasible.
- **Windows have width ≥ 2.** Every generator window satisfies `hi ≥ lo+1`.

## Phases

Each phase lists its deliverable and how you know it is done. Sizes: S < half a day, M ≈ 1 day, L ≈ 2 days.

### Phase A: Finish the core tools (S)

- `solver/validate.py`
  - `check(inst, sigma)` returns a list of F1, F2 and F3 violations.
    - F2 uses a float tolerance, e.g. `1e-9`.
    - Handle a slot with zero capacity.
  - `p_base(inst, sigma)` = Σ w·(σ+1).
- `solver/bruteforce.py`
  - Exact DFS that takes a pluggable `objective`.
  - Prune by window, then by conflict, then by capacity, then by a bound (partial cost plus Σ w·(lo+1) for the unassigned tasks).
  - Order tasks by window width.
- `run.py`
  - Takes `--n --K --density --seed`, or `--input file.json`.
  - Also takes `--out`, plus `--brute` for small n.
  - Prints JSON with exactly the 5 keys.
- **Done when:**
  - The brute force solves the toy instance and seeds 1, 2 and 3.
  - Every brute-force result passes `check`.
  - The tests pass.

### Phase B: Penalty function, T2 (S, 15 pts)

**Recommended design:** P = P_base + λ₁·SLA-risk + λ₂·load-imbalance. Each extra term must be:

- non-negative
- computable in O(n + K·d)
- not a constant

The two terms:

- **SLA breach risk:** Σᵢ wᵢ · ((σᵢ − loᵢ)/(hiᵢ − loᵢ))².
  - It penalises tasks placed near the upper edge of their window.
  - The width is always ≥ 1, so there is no division by zero.
- **Load imbalance:** Σ_dims Σ_slots (util_{s,k} − mean_k)², where util = load/capacity.
  - Skip any slot whose capacity in that dimension is 0.

Bound each extra term by a multiple of P_base. Phase D's α proof needs this.

**Deliverables:**

- `solver/penalty.py`
- tests against hand-computed values on the toy instance
- a 1-page write-up covering the formula, the ScoreMe motivation (bureau-pull SLA, OCR GPU cluster), polynomial time, monotonicity and non-triviality

### Phase C: Algorithm design, T3 (M, 40 pts, the largest single task)

**Suggested name:** **SLA-Slack DSATUR with Certified Infeasibility and Repair (SSD-R).** Rename it if you prefer.

The algorithm has 4 stages:

1. **Pre-checks that prove infeasibility.** Each check is a sound certificate.
   - **Empty window.** A task has no slot in its window that fits its resource vector.
   - **Interval demand.** For every interval [a,b] and every dimension, take the tasks whose window lies inside [a,b]. Their total demand must be ≤ the summed capacity of slots a..b. This is O(K²·n·d). It catches all 3 census infeasibles.
   - **Clique in a narrow window.** A clique of tasks all confined to [a,b] is larger than b−a+1. Use a greedy clique on each window; this is a cheap check, not an exact one.
2. **Constructive greedy.** Repeatedly pick the unassigned task with:
   - the fewest still-feasible slots (DSATUR saturation, adapted to windows and capacity);
   - ties broken by conflict degree, then by weight.

   Put it in the feasible slot with the smallest marginal P.
3. **Repair when a task has no feasible slot.** Try a bounded Kempe-style move: move one blocking neighbour or capacity hog to another slot it can use. Allow at most R attempts.
4. **Local search improvement.** Try single moves and pairwise swaps that keep F1, F2 and F3 and lower P. Stop when no improving move exists or after an iteration cap. This is polynomial per pass.

**Output semantics** (decide now and test them later):

- `feasible=false` with reason `"PROVEN_INFEASIBLE: …"` when a stage-1 certificate fires.
- `"NOT_FOUND: …"` when the heuristic gave up.
- In both cases `assignment` holds the partial assignment.

**Two rejected alternatives** for the write-up:

- **Exact ILP or branch-and-bound.** It is exponential, and the spec forbids solvers.
- **Pure simulated annealing.** It has no feasibility certificate, is not reproducible without seeding, and its ratio cannot be proved.

**Deliverables:**

- numbered pseudocode, with a one-line justification for each non-obvious line
- a 1-page rationale
- the two rejected alternatives

**Done when:** you can rewrite the pseudocode from memory and hand-trace the toy instance in 5 minutes or less.

### Phase D: Proofs, T4 (M, 30 pts)

- **Feasibility (10 pts).** An unconditional guarantee would imply P = NP, so the claim must be scoped. Prove these three things:
  - **Soundness:** every `feasible=true` output satisfies F1, F2 and F3, because each assignment step checks all three.
  - **Certificate correctness:** each `PROVEN_INFEASIBLE` reason is a valid proof.
  - **Completeness for tractable sub-classes:** for example, no conflicts with a single dimension and full windows, or the case where every task has a slot where it fits.

  In the write-up, state clearly that this is the best a polynomial-time algorithm can do, unless P = NP.
- **Approximation ratio (10 pts), for P_base:**
  - Every feasible σ has σᵢ ≤ hiᵢ.
  - OPT ≥ Σ wᵢ(loᵢ+1).
  - Therefore α = max_i (hiᵢ+1)/(loᵢ+1) ≤ K.

  Tie each step to the pseudocode lines. Extend α to the full P using the Phase B bound.
- **Tight example (10 pts).** Build an instance where the greedy is forced to the top of every window and OPT sits at the bottom. For example, one heavy task fills slot 0, and that blocks every other task.
  - Put it in `instances/tight.json`.
  - `tools/ratio.py` prints exactly α.

### Phase E: NP-hardness proof, T1 (M, 20 pts; can run in parallel with C and D)

- **Reduce from Graph 3-Coloring.** All three constraint families must do real work:
  - **Conflicts:** E maps directly to the conflict edges.
  - **Resources:** add one GPU unit per vertex task, with slot GPU capacity equal to the size of the largest colour class allowed. Alternatively, add "blocker" tasks that fill a slot completely.
  - **Windows:** blocker tasks have width-1 windows that pin them to specific slots. Vertex tasks have windows [0,2]. Use K = 3 + the number of blocker slots.
- **Both directions:** a 3-colouring gives a feasible schedule, and a feasible schedule gives a 3-colouring. Show the construction size is polynomial.
- For each family, add one sentence saying what breaks if its gadget is removed. This addresses the rubric's main T1 failure mode.
- **Optional check:** use the brute force on small yes and no graphs, for example C₅ (3-colourable) and K₄ (not).
- **Deliverable:** 1 to 2 pages in LaTeX or Markdown.

### Phase F: Implementation and tests, T5 (L, 25 pts)

- `solver/algorithm.py`
  - It matches the pseudocode, with stage and line numbers in comments.
  - Each docstring explains *why* the design is as it is.
  - It takes an optional `--trace` flag.
- **The 4 required tests:**
  - **All-conflict graph with χ > K:** K_{K+1} with full windows gives `feasible=false`.
  - **Zero-capacity slot:** the solver never uses it, and the case is still solved when other slots are free.
  - **Tight SLA windows:** width-1 or width-2 windows, with feasible and infeasible versions.
  - **Single task.**
- **Extra tests:**
  - every `feasible=true` result passes `validate.check`
  - d=5, and unequal capacities (for the viva questions)
  - the heuristic equals the brute force on the toy instance, or is within ratio
  - a run on 20 random seeds never yields an invalid assignment
- Update `requirements.txt` to list numpy and matplotlib.
- **Done when:**
  - all tests pass;
  - a grep for forbidden imports returns nothing;
  - `--trace` on the toy instance matches your hand trace.

### Phase G: Benchmarks, T6 (S to M, 20 pts)

- `tools/bench.py` runs all 9 commands, plus the brute force for n ≤ 12.
  - It writes `results/results.csv` with: penalty, runtime_ms, feasible, reason, brute-force optimum and ratio.
  - It also writes two charts: penalty vs n, and runtime vs n.
- **Brute-force note:** at n=12, K=4 the search space is 4¹² ≈ 1.7e7, which needs pruning. Check the time early.
- **Write-up:** one paragraph per anomaly. This covers the 3 proven-infeasible rows, any `NOT_FOUND` row, and any ratio > 1. Do not hide failures.

### Phase H: Journal, report, viva prep, T7 and T8 (M, 50 pts together)

- **Journal (2 pages):**
  - the hardest decision (say which step and which alternative you rejected)
  - a named failing benchmark and its failure mode
  - a ScoreMe production system: for example the OCR GPU cluster, with Kafka partitions as conflicts, or the bureau API gateway with its rate limits
  - what surprised you
- **Report:** assemble T1 to T8 into one PDF.
- **Viva drills (do at least 2):**
  - whiteboard the pseudocode
  - trace a fresh `generate_instance(6, 3, seed=random)` instance in 5 minutes or less and check it with the brute force
  - explain 10 random lines picked with `shuf`
  - answer "a 5th dimension?": d is read from the data, so this costs only O(d) per check
  - answer "unequal capacities?": capacity is per slot in `Instance`, so the checks are already per slot
  - name one decision you would make differently in hindsight

## Order and critical path

```
A ─┬─ B ─ C ─ F ─ D ─┐
   └─ E (parallel) ──┴─ G ─ H
```

**Suggested order:** A → B → C → F → G (the benchmarks can start early) → D → E → H.

## Cut list (drop from the top first)

1. Local search (stage 4): greedy plus repair is enough for feasibility.
2. The machine check of the reduction.
3. The exact tight example: up to 10 pts at risk.
4. The α extension to the full P: give it for P_base only.

**Never cut:** all 9 benchmark rows, the 4 required tests, the rejected alternatives, the journal, the viva drills.

## Schedule (answered 2026-10-29)

- **Submission: 2026-10-30.** The viva is planned for Monday 2026-11-02.
- **Report: LaTeX.**
- **Compressed order for the deadline:** B → C+F together (write the pseudocode and the code side by side) → G → D → E → LaTeX assembly → H journal.
- **The viva drills move to the weekend**, after submission.
- **If short on time, cut first:** local search (stage 4) and the machine check of the reduction.
