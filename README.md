# random-cfg-gen

Generate random context-free grammars and benchmark FIRST, FOLLOW, and NULLABLE
across the DYNAMIC, STATIC, optimized SYNTH, and FARROW APS
evaluators.

```bash
python3 main.py clean --programs
python3 main.py generate --start 50 --stop 500 --step 50
python3 main.py run
python3 main.py check
python3 main.py times
```

Run the complete benchmark:

```bash
./run-benchmarks.sh
```

The script preserves existing grammars and results. It generates missing grammar
sizes and runs only missing or stale evaluator results. Use
`python3 main.py clean --programs` first only when a full reset is intended.

Override the default range with environment variables:

```bash
START_NON_TERMINALS=100 STOP_NON_TERMINALS=1000 STEP_NON_TERMINALS=50 \
	./run-benchmarks.sh
```

Each build, generation, or evaluator step has a one-hour timeout. Override it
with `TIMEOUT_SECONDS`, in seconds:

```bash
TIMEOUT_SECONDS=1800 ./run-benchmarks.sh
```

The wrapper uses one job by default so grammar sizes run in order. When one size
times out, larger sizes are skipped only for that evaluator and analysis; the
other analyses and evaluators continue. Parallel execution can be enabled when
strict size ordering is unnecessary:

```bash
JOBS=4 ./run-benchmarks.sh
```

Generator options:

```bash
python3 main.py generate --disallow-epsilon --disallow-alternative
python3 main.py generate --item-length 8 --force
python3 main.py generate --seed 854 --force
python3 main.py generate --rhs-continue-percent 40 \
	--alternative-continue-percent 60 --epsilon-percent 10 --force
```

RHS lengths and alternative counts use geometric distributions. Each successful
continuation test adds one item; RHSs start at zero when epsilon is allowed, and
productions always start with one alternative. At the default 60% continuation
chance, nonempty RHSs and production alternative lists each average 2.5 items.
Lower `--rhs-continue-percent` to make grammars thinner. Epsilon generation is
separate and defaults to a 10% chance for each eligible alternative, so nullable
nonterminals are sparse seeds instead of almost all being direct base cases. A
nonterminal gets at most one epsilon alternative, preserving useful nullable
chains without filling a production with duplicate epsilon alternatives. With
`--seed`, each grammar size gets a distinct but reproducible seed.

Limit parallel evaluator runs or select evaluators:

```bash
python3 main.py run -j 2
python3 main.py run -e SYNTH FARROW
python3 main.py run -e DYNAMIC SYNTH --force  # explicitly rerun completed results
python3 main.py run --timeout 1800             # 30-minute limit per step
```

Each evaluator runs `FirstDriver`, `FollowDriver`, and `NullableDriver`. Their
individual output and timing files are stored alongside the combined result.
Normal runs only schedule grammar/analysis pairs whose result files are missing
or whose stored grammar hash is stale. A result is complete only when its status
file contains `OK`; failed and timed-out steps do not publish timing or hash
files. A failure or timeout stops larger sizes only for the current evaluator
and analysis. Evaluators with no pending results do not invoke Make.

Generated files are stored under `results/`:

```text
results/
	cfg/
	dynamic/{first,follow,nullable}/
	static/{first,follow,nullable}/
	synth/{first,follow,nullable}/
	farrow/{first,follow,nullable}/
	diffs/{first,follow,nullable}/
	summary.csv
```

Evaluator results are sorted before comparison. `main.py check` stores unified
diffs under `results/diffs/`, and `main.py times` prints timing and match status
and updates `results/summary.csv`.
