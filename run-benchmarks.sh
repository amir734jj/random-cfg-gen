#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

non_terminals=${1:-1024}
shift $(( $# > 0 ? 1 : 0 ))

aps_dir=${APS_DIR:-../aps/examples/scala}
results_dir=${RESULTS_DIR:-results}
grammar_file="$results_dir/grammar-$non_terminals.cfg"
failed=0

mkdir -p "$results_dir"

echo "=== Generating CFG with $non_terminals nonterminals ==="
dotnet run --project App/App.csproj -- "$non_terminals" "$@" > "$grammar_file"
echo "Generated $grammar_file"
echo

run_benchmark() {
  local evaluator=$1
  local name=${evaluator,,}
  local output_file="$results_dir/$name.out"
  local time_file="$results_dir/$name.time"

  echo "=== FIRST / FOLLOW / NULLABLE: $evaluator ==="
  make --no-print-directory -C "$aps_dir" EVALUATOR="$evaluator" clean

  if command time -p -o "$time_file" \
      make --no-print-directory -C "$aps_dir" \
        EVALUATOR="$evaluator" ARGS="$(realpath "$grammar_file")" \
        GrammarDriver.run > "$output_file" 2>&1; then
    echo "PASS: $output_file ($(tr '\n' ' ' < "$time_file"))"
  else
    echo "FAIL: $output_file"
    failed=1
  fi
  echo
}

run_benchmark DYNAMIC
run_benchmark STATIC
run_benchmark SYNTH

if (( failed != 0 )); then
  echo "SOME BENCHMARKS FAILED"
  exit 1
fi

echo "ALL BENCHMARKS PASSED"