#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

start=${START_NON_TERMINALS:-50}
stop=${STOP_NON_TERMINALS:-100}
step=${STEP_NON_TERMINALS:-50}
out=${BENCHMARK_OUT:-cfg.out}
failed=0

echo "=== Random CFG benchmark ==="
python3 main.py clean --programs
python3 main.py generate --start "$start" --stop "$stop" --step "$step" "$@"
python3 main.py run

echo "# Random CFG benchmark" > "$out"
if ! python3 main.py check | tee -a "$out"; then
  failed=1
fi
python3 main.py times | tee -a "$out"

if (( failed != 0 )); then
  echo "SOME BENCHMARKS FAILED"
  exit 1
fi

echo "ALL BENCHMARKS PASSED: $out"#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec python3 run-benchmarks.py "$@"