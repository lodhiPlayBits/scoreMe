# Roadmap: ScoreMe MSME Pipeline Scheduling Assignment

- **Date:** 2026-10-29
- **Status:** approved
- **Source:** `ScoreMe_MSME_Pipeline_Scheduling_Assignment (1).docx`. Line numbers below refer to its extracted text, `assignment.txt`.

## Goal and success measure

**Goal:** Take the assignment from an empty folder to a submission that the candidate wrote and can defend without notes, with an AI Usage Log that is honest from session #1.

**Success measure:**
- Every rubric deliverable exists: T1–T8 plus the AI log (lines 9, 67–184).
- Every phase's "done when" check passes.
- Two closed-book viva drills pass the written checklist.
- Target: at least 100/200, with the viva at 15/30 or more.
  - A viva below 15 caps the total at 120 (line 211).
  - Being unable to explain the work zeroes the whole assignment (line 184).

## Current state

- **Greenfield.** `D:\scoreMe` is empty and is not a git repo.
- **Facts from the spec (read from the text, not designed):**
  - **Slot indexing conflict.** The generator's windows are 0-based (lines 202–203). The prose and the toy instance are 1-based (lines 16, 61–62). P_base charges the slot index itself (line 42).
  - **Generator limits.** The generator always produces d=4 and uniform slot capacities (lines 198, 201). The viva asks about a 5th dimension and unequal capacities (lines 179–180), so those cases need hand-written JSON tests.
  - **A concept-level constraint, logged as AI-supplied.** Task 1 shows that feasibility is NP-hard. So no polynomial-time algorithm can have Task 4's "always finds a feasible assignment" (line 118) or an unconditional α (line 119), unless P=NP. How to scope those claims is the candidate's decision.

## Assumptions

- **A1 Team and time:** one candidate, part-time, no known deadline. Phase sizes are relative.
- **A2 Stack:** Python 3.12, the standard library, numpy and matplotlib (pandas optional). Tests use `unittest`. No new dependencies.
- **A3 Integrity tags:**
  - **[CANDIDATE]:** the candidate writes it alone.
  - **[AI-OK]:** AI may write boilerplate: I/O, data classes, CLI, charts and table formatting (lines 134, 139).
  - **[MIXED]:** the candidate owns the logic and AI does the plumbing.
  - The validator, penalty, brute force, infeasibility detection and all solver logic are [CANDIDATE].
- **A4 Claude's role on [CANDIDATE] files (pending Q3):** Claude may run commands and paste the raw output. Claude must not read and explain the code, diagnose failures, suggest fixes, or edit. kit:code-reviewer runs only on [AI-OK] diffs.
- **A5 Slot convention (decided 2026-10-29, Q1):** slots are 0-based, exactly as the generator produces them. The penalty charges (σ(tᵢ)+1), so slot 0 is not free and OPT > 0. The toy instance is stored with a −1 shift. This choice is AI-suggested idea (g) and must be logged in entry #1.
- **A6 CLI:** `run.py --n --K --density --seed` imports the unmodified generator, writes the instance JSON, and calls a solver entry point that takes a JSON path (lines 130, 145–157).
- **A7 Brute force:** exact search is fast enough for n≤12 and K≤4. The worst case is 4^12 ≈ 1.7e7 assignments before pruning.
- **A8 Report and submission:** LaTeX, or Markdown exported to PDF (Q6). The submission is one PDF with sections T1–T8, plus the repo.
- **A9 Git:** branches named `<type>/<slug>`, draft PRs or local branches (Q7). The user merges.

## Phases

### Phase 0: Scaffold, validator, brute force, census (S)

- **Delivers:** a repo where any instance can be generated, checked against F1–F3, and solved exactly when small.
- **Work:**
  - [AI-OK] Run `git init`, then `git switch -c chore/scaffold` on the unborn branch. Copy the generator unchanged into `generator.py` and record its sha256 in the README. Add JSON I/O and data classes that work for any d and for per-slot capacities.
  - [CANDIDATE] Write AI log entry #1, covering this roadmap session (v1 and v2). Mark each idea below as re-derived, rejected, or used with attribution.
    - (a) total demand vs total capacity per dimension
    - (b) a demand check over each slot range [a,b]
    - (c) a bipartiteness check on tasks confined to [K-2,K-1], with triangle-count estimates
    - (d) the generator's resource values collapsing to (0,1], with estimated utilisations
    - (e) the options for scoping the guarantee
    - (f) gadget ablation for the reduction
    - (g) using σ+1 in the penalty
    - (h) a test where two assignments tie on P_base
    - (i) a separate `random.Random` for the solver
    - (j) separating "proven infeasible" from "not found"
    - (k) comparing `--trace` output against the hand trace
  - [CANDIDATE] `validate.py`: checks F1, F2 (with a float tolerance) and F3, and computes P_base.
  - [CANDIDATE] `bruteforce.py`: exact search with an `objective` parameter.
  - [AI-OK] `tools/census.py`: prints raw descriptive statistics for the 9 benchmarks, with no verdict. The statistics are n, K, edge count, a histogram of window widths, and demand and capacity sums per dimension. For seeds 1–3 it also prints the brute-force status and the optimal P_base.
- **Depends on:** Q1. The gate is satisfied: 0-based slots with a σ+1 penalty, decided 2026-10-29.
- **Done when:**
  - The README states the slot convention and where it came from.
  - The toy instance is stored with a documented −1 shift.
  - `python -m unittest discover -s tests` passes.
  - `sha256sum generator.py` matches the README.
  - `python tools/census.py` prints 9 rows.
  - `AI_USAGE_LOG.md` contains entry #1.
  - `git branch --show-current` prints `chore/scaffold`.
- **Biggest risk:** building on an unconfirmed slot convention. The Q1 gate prevents this.

### Phase 1: Co-design the penalty, algorithm, α sketch and tight-instance sketch (T2, T3) (L)

- **Delivers:**
  - P(σ) as code.
  - A named algorithm as numbered pseudocode, with its rationale and 2 rejected alternatives.
  - A design that is shaped to be provable.
- **Work:**
  - [CANDIDATE] Define P: the formula, its ScoreMe motivation, why it can be evaluated in polynomial time, and why it is meaningful and non-trivial (lines 81–87). Implement `penalty.py` and test it against hand-computed values. Re-run the brute force with P.
  - [CANDIDATE] Write pseudocode with a justification for every non-obvious line (line 97). Describe 2 rejected alternatives with reasons (line 113).
  - [CANDIDATE] Write down the scope of the guarantee and the output semantics, including what `assignment` and `violation_reason` contain when `feasible=false`.
  - [CANDIDATE] Write a one-paragraph sketch of α tied to specific pseudocode lines, and a sketch of the tight instance. If either can't be written, change P or the design now.
  - [CANDIDATE] Start `journal_notes.md` with dated, first-person notes on each decision and each dead end. This is raw material for T7.
- **Depends on:** Phase 0.
- **Done when:**
  - `python -m unittest tests.test_penalty` passes.
  - The penalty section states that the extra term is non-negative and bounded relative to P_base, or explains why no bound is needed.
  - The α sketch and the tight-instance sketch both cite pseudocode line numbers.
  - A from-memory rewrite of the pseudocode, diffed against the document, shows no missing steps.
  - A hand trace on `generate_instance(6, 3, seed=<random>)` takes 5 minutes or less and is checked with `bruteforce.py`.
- **Biggest risk:** a design that can't be proved or can't be recalled. Both checks above run before the design is frozen.

### Phase 2: NP-hardness reduction (T1) (M), in parallel with Phases 1 and 3

- **Delivers:** the T1 proof, made of the construction, both directions and the polynomial size (line 78). All three constraint families must do real work (line 73).
- **Work:**
  - [CANDIDATE] Pick the source problem and build the construction.
  - [CANDIDATE] Choose a way to check the construction on small cases. Using the Phase 0 brute force is allowed. The checking method must be the candidate's own, or be logged as idea (f).
  - [CANDIDATE] Explain the reduction aloud, closed-book.
- **Depends on:** Phase 0.
- **Done when:**
  - The proof names its source problem, shows each family's role in both directions, and is 1–2 pages long.
  - The chosen check passes on at least one "yes" case and one "no" case, with the commands and output recorded.
- **Biggest risk:** a reduction that only exercises the conflict constraint (line 220). For each family, write one sentence on what breaks if that family's part of the construction is removed.

### Phase 3: Implementation, tests, first viva drill, journal draft (T5) (L)

- **Delivers:** `run.py` and a JSON entry point that output exactly the 5 required keys (line 131).
- **Work:**
  - [CANDIDATE] Write `algorithm.py` on `feat/solver`, matching the pseudocode line for line. Docstrings explain design decisions (line 135).
  - [AI-OK] argparse, writing the output JSON, and a `--trace` flag.
  - [CANDIDATE] Tests:
    - the 4 required cases (line 136)
    - hand-written d=5 and unequal-capacity cases
    - "every `feasible=true` output passes the validator"
    - the Phase 1 output semantics for `feasible=false`
  - [MIXED] A robustness run on extra seeds: 5 to 20 of them, depending on the cut list.
  - [CANDIDATE] Right after the first working build, do a viva drill on the toy instance and on one generator-made 6-node instance. Then write a journal draft from `journal_notes.md`.
- **Depends on:** the Phase 1 pseudocode being frozen.
- **Done when:**
  - `python -m unittest discover -s tests` passes.
  - `python run.py --n 8 --K 3 --density 0.3 --seed 1` prints JSON with exactly the 5 keys.
  - `grep -rnE "^\s*(import|from)\s+(ortools|pulp|cplex|gurobi|z3|networkx|pysat|pycosat)" solver/ tools/ tests/` returns nothing.
  - `requirements.txt` lists only numpy and matplotlib, plus pandas if used.
  - `--trace` on the toy instance matches the Phase 1 hand trace.
  - The drill checklist and the journal draft are committed.
- **Biggest risk:** the code drifting away from the pseudocode (line 139). Compare the trace with the hand trace on the first build.

### Phase 4: Formal proofs and tight example (T4) (M)

- **Delivers:**
  - A feasibility guarantee within the declared scope.
  - α.
  - A tight instance that reproduces α.
- **Work:**
  - [CANDIDATE] Turn the Phase 1 sketches into proofs. Each step cites a pseudocode line and uses the candidate's own P (lines 118–123).
  - [CANDIDATE] `instances/tight.json`.
  - [AI-OK] `tools/ratio.py <json>`: runs the solver and the brute force and prints the ratio.
- **Depends on:** Phase 3.
- **Done when:**
  - `python tools/ratio.py instances/tight.json` prints the proven α to within 1e-9.
  - Each proof step cites a pseudocode line.
  - The candidate gives the level-1 argument aloud, closed-book.
- **Biggest risk:** the tight instance doesn't reach α. It was sketched in Phase 1, so run `ratio.py` on it before writing the proof up.

### Phase 5: Benchmarks, report, final journal, viva rehearsal (T6, T7, T8) (M)

- **Delivers:** the submission PDF and a rehearsed candidate.
- **Work:**
  - [AI-OK] `tools/bench.py`: runs all 9 benchmark commands (lines 145–157) and writes `results.csv` plus 2 PNG charts.
  - [CANDIDATE] Explain every anomaly and every infeasible or not-found row, in the candidate's own analysis (line 159).
  - [CANDIDATE] The final 2-page journal, covering all 4 required points (lines 165–172).
  - [MIXED] Assemble the PDF and finalise the AI log.
  - [CANDIDATE] Two full drills, scored against the checklist:
    - whiteboard the pseudocode
    - trace a fresh 6-node instance in 5 minutes or less
    - explain 10 random code lines picked with `shuf -n 10`
    - answer the d=5 and unequal-capacity questions
    - name one decision you would make differently in hindsight
- **Depends on:** Phases 2, 3 and 4. The benchmark runs can start as soon as Phase 3 is done.
- **Done when:**
  - `results.csv` has 9 rows and both PNGs exist.
  - Every `feasible=false` row has a violation_reason and its own named paragraph in the report.
  - The empirical ratio is reported for every small instance that is feasible.
  - The journal names a specific seed.
  - Both drills pass every checklist item.
  - The AI log covers every session.
- **Biggest risk:** running out of time before the drills, which gate everything. Use the cut list below, and start the drills in Phase 3.

## Cut list

Drop items from the top first.

1. Robustness seeds, from 20 down to 5. No points at risk.
2. The machine check of the reduction. Replace it with a hand check on one case. Puts T1 at some risk.
3. Chart polish and supplementary seeds. No points at risk.
4. The exact tight example. Up to 10 points at risk.
5. The α proof, only if the level-1 guarantee is solid. Up to 10 points at risk.

**Never cut:** viva drills, all 9 benchmark runs, the 4 required tests, T2, the rejected alternatives, the journal, the AI log.

## Dependency order

`0 → {1, 2}`; `1 → 3 → 4`; `{2, 3, 4} → 5`

## Explicitly out of scope

- A Java implementation.
- Any change to the generator (line 188).
- Forbidden solvers (line 132).
- CI, packaging or a GUI.
- Tuning against held-out seeds.
- Any roadmap content that supplies infeasibility-check designs, anomaly explanations, guarantee options, α, the reduction or the output semantics. Those belong to the candidate.

## Open questions for the user

1. ~~**Q1, slot convention (gate for Phase 0)**~~ **Answered 2026-10-29:** 0-based slots, with (σ+1) in the penalty. See A5.
2. **Q2:** will the coordinator confirm that AI-assisted planning, including this roadmap, counts as "concept clarification"? Either way, this session is AI log entry #1.
3. **Q3:** do you accept A4? On [CANDIDATE] files Claude only runs commands and pastes the raw output, with no diagnosis, no fixes and no kit:code-reviewer. This narrows your CLAUDE.md fix and review rules for those files.
4. **Q4:** what are the deadline and the viva date?
5. **Q5:** is someone available to run mock vivas with you, or are the drills self-scored on generator instances?
6. **Q6:** is LaTeX available (Overleaf or MiKTeX), or is Markdown exported to PDF acceptable?
7. **Q7:** will there be a GitHub remote for draft PRs, or a local repo only?

## Challenged by plan-critic

**Verdict:** PROCEED WITH CHANGES. There was one critique round and one revision.

**Accepted:**
1. **BLOCKING, roadmap supplied graded design ideas.** The design hints were removed. AI log entry #1 lists all 11 AI-supplied ideas. Whether planning help counts as "concept clarification" is now Q2.
2. **Penalty, algorithm and α were frozen one after another.** They are now merged into one co-design phase, which gates on sketches of α and the tight instance.
3. **The forbidden-library grep matched "DSATUR".** It now matches import lines only, and `requirements.txt` is checked too.
4. **No cut-line.** Added a ranked cut list. The first drill and the journal draft moved up to straight after the first build.
5. **Phase 0 checks depended on later decisions.** The slot-convention gate was added, the brute force takes a pluggable objective, and the toy instance has a documented −1 shift.
6. **The AI boundary covered review but not debugging.** Rule A4 was added, pending the user's answer to Q3.
7. **Mock vivas depended on a peer.** Drill instances now come from the generator, with a 5-minute limit per trace and a written checklist.
8. **`assignment` was undefined when `feasible=false`.** The candidate decides this in Phase 1 and tests it in Phase 3.
- **Minor, the empty `main` commit.** The repo now starts directly on `chore/scaffold`.

**Rejected:** none.
