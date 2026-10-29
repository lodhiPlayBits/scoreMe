"""Run the Task 6 benchmark suite and write the CSV and charts.

Usage: .venv/bin/python tools/bench.py

Writes:
  report/data/results.csv        the 9 graded benchmarks + supplementary runs
  report/data/small_study.csv    SSD-R vs exact optimum on 1200 random small instances
  report/figures/penalty_vs_n.png
  report/figures/runtime_vs_n.png
  report/figures/ratio_hist.png

Each benchmark goes through run.solve, the same code path as `python
run.py ...`, so the numbers match the CLI. Runtime is the median of 3 runs:
runtime_ms is the integer the CLI reports, and runtime_ms_float is a
wall-clock time with sub-millisecond precision, which the chart uses so that
fast runs do not show as 0.
"""

import csv
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generator import generate_instance  # noqa: E402
from run import solve  # noqa: E402
from solver.bruteforce import solve_exact  # noqa: E402
from solver.instance import Instance  # noqa: E402
from solver.penalty import penalty  # noqa: E402
from solver.validate import p_base  # noqa: E402
from tools.census import BENCHMARKS  # noqa: E402

DATA = ROOT / "report" / "data"
FIGS = ROOT / "report" / "figures"

# Supplementary feasible instances for the scaling charts. Density 0.05 is
# low enough that the generator produces feasible instances at these sizes.
# n=150/K=12 and n=200/K=15 are left out: they are capacity-infeasible at
# any density (see report section 6).
SUPPLEMENTARY = [(n, K, 0.05, seed) for n, K in [(25, 6), (50, 8), (100, 10), (200, 20)]
                 for seed in range(5)]
SMALL_STUDY = [(6, 3, 0.3), (8, 3, 0.3), (8, 4, 0.4), (10, 4, 0.4), (10, 3, 0.2), (12, 4, 0.5)]

# Default palette, slots 1-3 in fixed order (dataviz skill, references/palette.md).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#6b6a64", "#e4e3df"


def status_of(reason: str) -> str:
    return reason.split(":")[0] if reason else "FEASIBLE"


def run_one(group, n, K, density, seed):
    inst = Instance(**generate_instance(n, K, conflict_density=density, seed=seed))
    results, times = [], []
    for _ in range(3):
        t = time.perf_counter()
        results.append(solve(inst, "heuristic"))
        times.append((time.perf_counter() - t) * 1000)
    res = results[0]
    row = dict(group=group, n=n, K=K, density=density, seed=seed, edges=len(inst.conflicts),
               status=status_of(res.violation_reason), feasible=res.feasible,
               penalty="", p_base="", runtime_ms=statistics.median(r.runtime_ms for r in results),
               runtime_ms_float=round(statistics.median(times), 3),
               opt_penalty="", ratio="", opt_runtime_ms="", reason=res.violation_reason)
    if res.feasible:
        sigma = [res.assignment[t] for t in inst.tasks]
        row["penalty"] = round(res.penalty, 4)
        row["p_base"] = round(p_base(inst, sigma), 4)
    if n <= 12:
        t = time.perf_counter()
        ex = solve_exact(inst, objective=penalty)
        row["opt_runtime_ms"] = round((time.perf_counter() - t) * 1000, 2)
        row["opt_penalty"] = round(ex.value, 4) if ex.value is not None else ex.status
        if res.feasible and ex.value:
            row["ratio"] = round(res.penalty / ex.value, 4)
    return row


def small_study():
    """Outcome of SSD-R vs the exact solver on many random small instances."""
    rows = []
    for n, K, density in SMALL_STUDY:
        for seed in range(200):
            inst = Instance(**generate_instance(n, K, conflict_density=density, seed=seed))
            res = solve(inst, "heuristic")
            ex = solve_exact(inst, objective=penalty)
            rows.append(dict(n=n, K=K, density=density, seed=seed,
                             heuristic=status_of(res.violation_reason), exact=ex.status,
                             ratio=round(res.penalty / ex.value, 6) if res.feasible else ""))
    return rows


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED)


def charts(rows, study):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGS.mkdir(parents=True, exist_ok=True)
    feas = [r for r in rows if r["feasible"]]

    # --- penalty vs n: SSD-R for every feasible run, exact optimum where known
    fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=200)
    ax.plot([r["n"] for r in feas], [r["penalty"] for r in feas], "o", ms=6, color=BLUE,
            markeredgecolor="white", markeredgewidth=1, label="SSD-R")
    opt = [r for r in feas if r["opt_penalty"] != ""]
    ax.plot([r["n"] for r in opt], [r["opt_penalty"] for r in opt], "D", ms=8,
            markerfacecolor="none", markeredgecolor=ORANGE, markeredgewidth=1.5,
            label="exact optimum (n ≤ 12)")
    ax.set_yscale("log")
    style(ax, "Penalty P(σ) of feasible runs vs n", "n (tasks)", "P(σ), log scale")
    ax.legend(frameon=False, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(FIGS / "penalty_vs_n.png")
    plt.close(fig)

    # --- runtime vs n: feasible runs vs runs ended by an infeasibility certificate
    fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=200)
    groups = [("FEASIBLE", "o", BLUE, "feasible schedule found"),
              ("PROVEN_INFEASIBLE", "s", AQUA, "proven infeasible (Stage 1)"),
              ("NOT_FOUND", "^", ORANGE, "not found")]
    for status, marker, colour, label in groups:
        pts = [r for r in rows if r["status"] == status]
        if pts:
            ax.plot([r["n"] for r in pts], [r["runtime_ms_float"] for r in pts], marker,
                    ms=6, color=colour, markeredgecolor="white", markeredgewidth=1, label=label)
    ax.set_yscale("log")
    style(ax, "SSD-R runtime vs n (median of 3 runs)", "n (tasks)", "runtime (ms, log scale)")
    ax.legend(frameon=False, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(FIGS / "runtime_vs_n.png")
    plt.close(fig)

    # --- empirical ratio distribution on the small study
    ratios = [r["ratio"] for r in study if r["ratio"] != ""]
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
    ax.hist(ratios, bins=[1 + 0.025 * i for i in range(27)], color=BLUE, edgecolor="white",
            linewidth=1)
    style(ax, f"Empirical ratio P(SSD-R)/P(OPT), {len(ratios)} feasible small instances",
          "ratio", "instances")
    fig.tight_layout()
    fig.savefig(FIGS / "ratio_hist.png")
    plt.close(fig)


def main():
    rows = [run_one("benchmark", *b) for b in BENCHMARKS]
    rows += [run_one("supplementary", *b) for b in SUPPLEMENTARY]
    write_csv(DATA / "results.csv", rows)
    study = small_study()
    write_csv(DATA / "small_study.csv", study)
    charts(rows, study)

    print(f"{'n':>4} {'K':>3} {'dens':>5} {'seed':>4} {'status':<18} {'P':>10} {'ms':>6} {'OPT':>10} {'ratio':>7}")
    for r in rows[:len(BENCHMARKS)]:
        print(f"{r['n']:>4} {r['K']:>3} {r['density']:>5} {r['seed']:>4} {r['status']:<18} "
              f"{r['penalty']!s:>10} {r['runtime_ms']:>6} {r['opt_penalty']!s:>10} {r['ratio']!s:>7}")
    from collections import Counter
    print("small study:", Counter((r["heuristic"], r["exact"]) for r in study))


if __name__ == "__main__":
    main()
