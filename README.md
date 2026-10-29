# ScoreMe MSME Credit Pipeline Scheduling

The candidate's submission for the ScoreMe "Advanced Systems Design" coding assignment. The plan is in [docs/roadmap/2026-10-29-scoreme-assignment.md](docs/roadmap/2026-10-29-scoreme-assignment.md).

## Slot convention

- **Slots are 0-based** (`0 .. K-1`), exactly as `generator.py` produces windows. This was decided 2026-10-29 (roadmap Q1).
- The penalty charges `σ(tᵢ) + 1` per task, so slot 0 is not free and the optimum is never 0.
- `instances/toy.json` is the toy instance from the assignment (section 3.3). Its SLA windows are **shifted by −1** from the spec's 1-based values; for example, the spec gives T1:[1,3], which is stored as [0,2].
- Task names are kept as `T1..T6`; task indices in `conflicts`, `resources`, `windows` and `weights` are 0-based.

## Generator

`generator.py` is the assignment's instance generator, **not modified**: its text is identical to the spec, stored with LF line endings (`.gitattributes` stops git from converting them).

```
sha256  0d97463215c0edbec3163178a7534f74451519ba05f8170dbc102d48c73f8b65  generator.py
```

`tests/test_instance.py` fails if the file changes.

## Layout

| Path | Contents |
|---|---|
| `generator.py` | Provided generator, unmodified |
| `solver/instance.py` | `Instance` / `Result` data classes and JSON I/O (boilerplate) |
| `solver/validate.py` | F1/F2/F3 checker and P_base (independent referee) |
| `solver/bruteforce.py` | Exact branch-and-bound for small instances |
| `solver/penalty.py` | Extended penalty P = P_base + SLA risk + load imbalance (T2) |
| `solver/algorithm.py` | SSD-R heuristic (T3/T5) |
| `tools/reduction.py` | T1 reduction (3-Colouring -> scheduling), machine-checked |
| `tools/bench.py` | T6 benchmark suite: CSVs and charts in `report/` |
| `tools/ratio.py` | SSD-R vs exact optimum on one instance |
| `report/` | LaTeX report: `main.tex` + `sections/`; compiled `main.pdf` is the submission |
| `run.py` | CLI: `--n --K --density --seed` or `--input`, `--solver heuristic\|brute` |
| `instances/` | Hand-written instances (toy) |
| `tools/census.py` | Raw statistics for the 9 benchmark instances |
| `tests/` | `unittest` tests |

## Commands

```bash
python -m unittest discover -s tests
```

```bash
python tools/census.py
python run.py --n 8 --K 3 --density 0.3 --seed 1            # SSD-R
python run.py --input instances/toy.json --trace              # step-by-step log
python run.py --n 8 --K 3 --density 0.3 --seed 1 --solver brute
python tools/ratio.py instances/tight_K4.json
```

Python 3.10+ (developed on 3.12). The solver needs only the standard library. To run the benchmarks and draw the charts:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python tools/bench.py      # writes report/data/*.csv and report/figures/*.png
```

## Report

```bash
cd report && latexmk -pdf main.tex     # needs texlive-latex-extra + texlive-science
```
