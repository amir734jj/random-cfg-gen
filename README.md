# random-cfg-gen

Generate random context-free grammars and benchmark FIRST, FOLLOW, and NULLABLE
across the DYNAMIC, STATIC, and SYNTH APS evaluators.

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

Override the default range with environment variables:

```bash
START_NON_TERMINALS=100 STOP_NON_TERMINALS=1000 STEP_NON_TERMINALS=50 \
	./run-benchmarks.sh
```

Generator options:

```bash
python3 main.py generate --disallow-epsilon --disallow-alternative
python3 main.py generate --item-length 8 --force
```

Limit parallel evaluator runs or select evaluators:

```bash
python3 main.py run -j 2
python3 main.py run -e DYNAMIC SYNTH --force
```

Generated files are stored under `results/`:

```text
results/
	cfg/
	dynamic/
	static/
	synth/
	diffs/
	summary.csv
```

Evaluator results are sorted before comparison. `main.py check` stores unified
diffs under `results/diffs/`, and `main.py times` prints timing and match status
and updates `results/summary.csv`.
