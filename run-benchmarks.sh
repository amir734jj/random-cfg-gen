#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

start=${START_NON_TERMINALS:-20}
stop=${STOP_NON_TERMINALS:-200}
step=${STEP_NON_TERMINALS:-20}
out=${BENCHMARK_OUT:-results/cfg.out}
timeout_seconds=${TIMEOUT_SECONDS:-3600}
jobs=${JOBS:-1}
failed=0

echo "=== Random CFG benchmark ==="
python3 main.py generate --start "$start" --stop "$stop" --step "$step" \
  --timeout "$timeout_seconds" "$@"
if ! python3 main.py run --timeout "$timeout_seconds" --jobs "$jobs"; then
  failed=1
fi

mkdir -p "$(dirname "$out")"
echo "# Random CFG benchmark" > "$out"
if ! python3 main.py check | tee -a "$out"; then
  failed=1
fi
python3 main.py times | tee -a "$out"

if (( failed != 0 )); then
  echo "SOME BENCHMARKS FAILED"
  exit 1
fi

echo "ALL BENCHMARKS PASSED: $out"