#!/usr/bin/env python3
"""Generate random CFGs and benchmark APS evaluators."""

import argparse
import csv
import difflib
import fcntl
import hashlib
import os
import signal
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Event


ROOT_DIR = Path(__file__).resolve().parent
APS_DIR = ROOT_DIR / ".." / "aps" / "examples" / "scala"
RESULTS_DIR = ROOT_DIR / "results"
EVALUATORS = ("DYNAMIC", "STATIC", "SYNTH", "FARROW")
DEFAULT_TIMEOUT_SECONDS = 60 * 60
DRIVERS = (
    ("first", "FIRST", "FirstDriver"),
    ("follow", "FOLLOW", "FollowDriver"),
    ("nullable", "NULLABLE", "NullableDriver"),
)


def cfg_files(results_dir):
    cfg_dir = results_dir / "cfg"
    return sorted(cfg_dir.glob("grammar-*.cfg"), key=cfg_size)


def cfg_size(cfg_file):
    return int(cfg_file.stem.removeprefix("grammar-"))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluator_dir(results_dir, evaluator):
    return results_dir / evaluator.lower()


def analysis_dir(results_dir, evaluator, analysis):
    return evaluator_dir(results_dir, evaluator) / analysis


def result_path(results_dir, evaluator, analysis, size):
    return analysis_dir(results_dir, evaluator, analysis) / f"{size}.results"


def has_ok_status(results_dir, evaluator, analysis, size):
    status_file = (
        analysis_dir(results_dir, evaluator, analysis) / f"{size}.status")
    return (status_file.is_file()
            and status_file.read_text().strip() == "OK")


def canonical_results(output_file, result_name):
    lines = output_file.read_text().splitlines()
    try:
        result_start = lines.index("Results:") + 1
    except ValueError:
        return []
    return sorted(f"{result_name} {line}\n" for line in lines[result_start:])


def results_match(results_dir, reference, evaluator, analysis, size):
    reference_file = result_path(results_dir, reference, analysis, size)
    candidate_file = result_path(results_dir, evaluator, analysis, size)
    if (not has_ok_status(results_dir, reference, analysis, size)
            or not has_ok_status(results_dir, evaluator, analysis, size)
            or not reference_file.is_file() or reference_file.stat().st_size == 0
            or not candidate_file.is_file() or candidate_file.stat().st_size == 0):
        return None
    return sorted(reference_file.read_text().splitlines()) == sorted(
        candidate_file.read_text().splitlines()
    )


def match_status(match):
    if match is None:
        return "N/A"
    return "MATCH" if match else "MISMATCH"


def terminate_process(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def run_command(command, cwd, timeout, description, stdout=None, stderr=None):
    process = subprocess.Popen(
        command, cwd=cwd, stdout=stdout, stderr=stderr, start_new_session=True,
    )
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_process(process)
        raise RuntimeError(
            f"{description} timed out after {timeout:g}s") from None
    if returncode != 0:
        raise RuntimeError(f"{description} failed with exit {returncode}")


class BuildLock:
    def __init__(self, aps_dir):
        lock_name = hashlib.sha256(str(aps_dir).encode()).hexdigest()[:16]
        self.path = Path("/tmp") / f"random-cfg-gen-{lock_name}.lock"
        self.file = None

    def __enter__(self):
        self.file = self.path.open("w")
        fcntl.flock(self.file, fcntl.LOCK_EX)

    def __exit__(self, exc_type, exc_value, traceback):
        fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()


class Command:
    name = ""
    help = ""

    def configure(self, parser):
        pass

    def run(self, args):
        raise NotImplementedError


class GenerateCommand(Command):
    name = "generate"
    help = "Generate random CFG files"

    def configure(self, parser):
        parser.add_argument("--start", type=int, default=50,
                            help="Starting nonterminal count (default: 50)")
        parser.add_argument("--stop", type=int, default=500,
                            help="Ending nonterminal count (default: 500)")
        parser.add_argument("--step", type=int, default=50,
                            help="Nonterminal count step (default: 50)")
        parser.add_argument("--force", action="store_true",
                            help="Overwrite existing CFG files")
        parser.add_argument("--item-length", type=int,
                            help="Characters per terminal or nonterminal")
        parser.add_argument("--disallow-epsilon", action="store_true")
        parser.add_argument("--disallow-alternative", action="store_true")
        parser.add_argument("--rhs-continue-percent", type=int, default=60,
                    help="Chance to add another RHS symbol (default: 60)")
        parser.add_argument("--alternative-continue-percent", type=int, default=60,
                    help="Chance to add another alternative (default: 60)")
        parser.add_argument("--epsilon-percent", type=int, default=10,
                    help="Chance an eligible alternative is epsilon (default: 10)")
        parser.add_argument("--seed", type=int,
                    help="Random seed (the grammar size is added per file)")
        parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
        parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS,
                    help="Maximum seconds per build/generation step (default: 3600)")

    def run(self, args):
        if args.step <= 0 or args.start > args.stop:
            raise ValueError("require --step > 0 and --start <= --stop")
        if args.timeout <= 0:
            raise ValueError("--timeout must be greater than zero")
        if not 0 <= args.rhs_continue_percent <= 99:
            raise ValueError("--rhs-continue-percent must be between 0 and 99")
        if not 0 <= args.alternative_continue_percent <= 99:
            raise ValueError(
                "--alternative-continue-percent must be between 0 and 99")
        if not 0 <= args.epsilon_percent <= 100:
            raise ValueError("--epsilon-percent must be between 0 and 100")

        results_dir = args.results_dir.resolve()
        cfg_dir = results_dir / "cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        run_command(
            ["dotnet", "build", "App/App.csproj"], ROOT_DIR, args.timeout,
            "generator build",
        )

        generator_args = []
        if args.item_length is not None:
            generator_args.extend(["--itemlength", str(args.item_length)])
        if args.disallow_epsilon:
            generator_args.append("--DisallowEpsilon")
        if args.disallow_alternative:
            generator_args.append("--DisallowAlternative")
        generator_args.extend([
            "--rhs-continue-percent", str(args.rhs_continue_percent),
            "--alternative-continue-percent",
            str(args.alternative_continue_percent),
            "--epsilon-percent", str(args.epsilon_percent),
        ])

        for size in range(args.start, args.stop + 1, args.step):
            cfg_file = cfg_dir / f"grammar-{size}.cfg"
            if cfg_file.exists() and not args.force:
                print(f"  {cfg_file.name} already exists, skipping")
                continue
            print(f"  Generating {cfg_file.name} ({size} nonterminals) ...")
            try:
                size_args = list(generator_args)
                if args.seed is not None:
                    size_args.extend(["--seed", str(args.seed + size)])
                with cfg_file.open("w") as output:
                    run_command(
                        ["dotnet", "run", "--no-build", "--project",
                         "App/App.csproj", "--", str(size), *size_args],
                        ROOT_DIR, args.timeout, f"generating {cfg_file.name}",
                        stdout=output,
                    )
            except (OSError, RuntimeError):
                cfg_file.unlink(missing_ok=True)
                raise

        print(f"Done. {len(cfg_files(results_dir))} CFG file(s) in {cfg_dir}")


class RunCommand(Command):
    name = "run"
    help = "Run CFGs against APS evaluators"

    def configure(self, parser):
        parser.add_argument("-j", "--jobs", type=int, default=1,
                            help="Parallel jobs (default: 1)")
        parser.add_argument("-e", "--evaluators", nargs="+",
                            help="Evaluators to run (default: all)")
        parser.add_argument("--aps-dir", type=Path, default=APS_DIR)
        parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
        parser.add_argument("--force", action="store_true",
                            help="Rerun completed CFGs")
        parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS,
                    help="Maximum seconds per build/program (default: 3600)")

    @staticmethod
    def is_complete(cfg_file, evaluator, analysis, results_dir):
        size = cfg_size(cfg_file)
        output_dir = analysis_dir(results_dir, evaluator, analysis)
        required_files = (
            output_dir / f"{size}.out",
            output_dir / f"{size}.results",
            output_dir / f"{size}.time",
            output_dir / f"{size}.hash",
            output_dir / f"{size}.status",
        )
        return (all(path.is_file() for path in required_files)
                and required_files[-2].read_text().strip() == file_hash(cfg_file)
                and required_files[-1].read_text().strip() == "OK")

    @staticmethod
    def run_one(cfg_file, evaluator, analysis, result_name, driver,
                aps_dir, results_dir, force, timeout, stop_event):
        size = cfg_size(cfg_file)
        output_dir = analysis_dir(results_dir, evaluator, analysis)
        output_file = output_dir / f"{size}.out"
        result_file = output_dir / f"{size}.results"
        time_file = output_dir / f"{size}.time"
        hash_file = output_dir / f"{size}.hash"
        status_file = output_dir / f"{size}.status"
        current_hash = file_hash(cfg_file)

        if not force and RunCommand.is_complete(
            cfg_file, evaluator, analysis, results_dir):
            return size, evaluator, analysis, "SKIPPED", float(time_file.read_text())
        if stop_event.is_set():
            return size, evaluator, analysis, "CANCELLED", 0.0

        output_dir.mkdir(parents=True, exist_ok=True)
        for stale_file in (result_file, time_file, hash_file, status_file):
            stale_file.unlink(missing_ok=True)

        start = time.monotonic()
        with output_file.open("w") as output:
            process = subprocess.Popen(
                ["make", "--no-print-directory", f"EVALUATOR={evaluator}",
                 f"ARGS={cfg_file.resolve()}", f"{driver}.run"],
                cwd=aps_dir, stdout=output, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            deadline = start + timeout
            while True:
                if stop_event.is_set():
                    terminate_process(process)
                    status = "CANCELLED"
                    break

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    stop_event.set()
                    terminate_process(process)
                    status = f"TIMEOUT ({timeout:g}s)"
                    break

                try:
                    returncode = process.wait(timeout=min(1, remaining))
                    status = "OK" if returncode == 0 else f"FAILED (exit {returncode})"
                    if returncode != 0:
                        stop_event.set()
                    break
                except subprocess.TimeoutExpired:
                    continue
        elapsed = time.monotonic() - start

        if status != "OK":
            status_file.write_text(status + "\n")
            return size, evaluator, analysis, status, elapsed

        results = canonical_results(output_file, result_name)
        if not results:
            status = "FAILED (no results)"
            status_file.write_text(status + "\n")
            stop_event.set()
            return size, evaluator, analysis, status, elapsed

        result_file.write_text("".join(results))
        time_file.write_text(f"{elapsed:.3f}\n")
        hash_file.write_text(current_hash + "\n")
        status_file.write_text("OK\n")
        return size, evaluator, analysis, "OK", elapsed

    def run(self, args):
        results_dir = args.results_dir.resolve()
        aps_dir = args.aps_dir.resolve()
        grammars = cfg_files(results_dir)
        if not grammars:
            raise ValueError(f"no CFG files in {results_dir / 'cfg'}; run generate first")
        if not aps_dir.is_dir():
            raise ValueError(f"APS directory not found: {aps_dir}")
        if args.jobs <= 0:
            raise ValueError("--jobs must be greater than zero")
        if args.timeout <= 0:
            raise ValueError("--timeout must be greater than zero")

        evaluators = ([name.upper() for name in args.evaluators]
                      if args.evaluators else list(EVALUATORS))
        unknown = set(evaluators) - set(EVALUATORS)
        if unknown:
            raise ValueError(f"unknown evaluator(s): {', '.join(sorted(unknown))}")

        print(f"Found {len(grammars)} CFG file(s), batch size {args.jobs}\n")
        failed = False
        with BuildLock(aps_dir):
            for evaluator in evaluators:
                pending_by_analysis = {
                    analysis: [
                        cfg_file for cfg_file in grammars
                        if args.force or not self.is_complete(
                            cfg_file, evaluator, analysis, results_dir)
                    ]
                    for analysis, _, _ in DRIVERS
                }
                print(f"=== Running with EVALUATOR={evaluator} ===")
                if not any(pending_by_analysis.values()):
                    print("  All results already exist, skipping\n")
                    continue

                pending_drivers = [
                    driver for analysis, _, driver in DRIVERS
                    if pending_by_analysis[analysis]
                ]
                try:
                    run_command(
                        ["make", "--no-print-directory", f"EVALUATOR={evaluator}",
                         *(f"{driver}.class" for driver in pending_drivers)],
                        aps_dir, args.timeout, f"building {evaluator} drivers",
                    )
                except RuntimeError as error:
                    print(f"ERROR: {error}", file=sys.stderr)
                    print(f"  Skipping {evaluator} after driver build failure.\n")
                    failed = True
                    continue

                for analysis, result_name, driver in DRIVERS:
                    pending = pending_by_analysis[analysis]
                    if not pending:
                        continue

                    stop_event = Event()
                    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
                        futures = [
                            executor.submit(
                                self.run_one, cfg_file, evaluator, analysis,
                                result_name, driver, aps_dir, results_dir, args.force,
                                args.timeout, stop_event,
                            )
                            for cfg_file in pending
                        ]
                        for future in as_completed(futures):
                            size, name, completed_analysis, status, elapsed = future.result()
                            print(f"  grammar-{size}.cfg -> {name}/{completed_analysis} ... "
                                  f"{status} ({elapsed:.3f}s)")
                            if status not in ("OK", "SKIPPED"):
                                failed = True

                    if stop_event.is_set():
                        print(f"  Stopped larger {evaluator}/{analysis} grammars "
                              "after a failure or timeout.")
                print()

        if failed:
            raise RuntimeError("one or more evaluator runs failed")


class CheckCommand(Command):
    name = "check"
    help = "Compare evaluator results"

    def configure(self, parser):
        parser.add_argument("--reference", default="dynamic")
        parser.add_argument("-v", "--verbose", action="store_true",
                            help="Print unified diffs")
        parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)

    def run(self, args):
        results_dir = args.results_dir.resolve()
        reference = args.reference.lower()
        evaluator_names = [name.lower() for name in EVALUATORS]
        if reference not in evaluator_names:
            raise ValueError(f"unknown reference evaluator: {reference}")

        grammars = cfg_files(results_dir)
        if not grammars:
            raise ValueError("no generated CFG files; run generate first")
        all_match = True

        for cfg_file in grammars:
            size = cfg_size(cfg_file)
            for analysis, _, _ in DRIVERS:
                diff_dir = results_dir / "diffs" / analysis
                diff_dir.mkdir(parents=True, exist_ok=True)
                reference_file = result_path(results_dir, reference, analysis, size)
                analysis_matches = True
                for evaluator in evaluator_names:
                    if evaluator == reference:
                        continue
                    candidate_file = result_path(
                        results_dir, evaluator, analysis, size)
                    diff_file = (
                        diff_dir / f"{reference}-vs-{evaluator}-{size}.diff")
                    match = results_match(
                        results_dir, reference, evaluator, analysis, size)
                    if match is None:
                        print(f"  MISSING: grammar-{size}.cfg "
                              f"in {evaluator}/{analysis}")
                        diff_file.write_text("MISSING\n")
                        analysis_matches = False
                        continue
                    if match:
                        diff_file.write_text("MATCH\n")
                        continue

                    reference_lines = sorted(
                        reference_file.read_text().splitlines(keepends=True))
                    candidate_lines = sorted(
                        candidate_file.read_text().splitlines(keepends=True))
                    diff = "".join(difflib.unified_diff(
                        reference_lines, candidate_lines,
                        fromfile=str(reference_file), tofile=str(candidate_file),
                    ))
                    diff_file.write_text(diff)
                    print(f"  MISMATCH: grammar-{size}.cfg {analysis} "
                          f"({reference} vs {evaluator})")
                    if args.verbose:
                        print(diff, end="")
                    analysis_matches = False

                if analysis_matches:
                    print(f"  OK: grammar-{size}.cfg {analysis}")
                else:
                    all_match = False

        if all_match:
            print("\nAll outputs match.")
        else:
            raise RuntimeError("one or more outputs differ")


class TimesCommand(Command):
    name = "times"
    help = "Display timings and comparison status"

    def configure(self, parser):
        parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)

    def run(self, args):
        results_dir = args.results_dir.resolve()
        grammars = cfg_files(results_dir)
        if not grammars:
            raise ValueError("no generated CFG files; run generate first")

        compared_evaluators = ("static", "synth", "farrow")
        headers = ("Nonterminals", *EVALUATORS,
                   "DYN=STATIC", "DYN=SYNTH", "DYN=FARROW", "Overall")
        widths = (14, *(12 for _ in EVALUATORS), 14, 14, 16, 12)

        summary_rows = []
        for analysis, _, _ in DRIVERS:
            if summary_rows:
                print()
            print(analysis.upper())
            print("".join(
                f"{value:<{width}}" for value, width in zip(headers, widths)))
            print("".join(
                f"{'-' * (width - 2):<{width}}" for width in widths))

            for cfg_file in grammars:
                size = cfg_size(cfg_file)
                times = {}
                for evaluator in EVALUATORS:
                    time_file = (
                        analysis_dir(results_dir, evaluator, analysis)
                        / f"{size}.time")
                    times[evaluator.lower()] = (
                        time_file.read_text().strip()
                        if (has_ok_status(results_dir, evaluator, analysis, size)
                            and time_file.exists())
                        else "N/A")
                matches = {
                    evaluator: results_match(
                        results_dir, "dynamic", evaluator, analysis, size)
                    for evaluator in compared_evaluators
                }
                overall = ("N/A" if any(match is None for match in matches.values())
                           else "MATCH" if all(matches.values()) else "MISMATCH")
                values = (
                                        str(size),
                    *(f"{times[name]}s" if times[name] != "N/A" else "N/A"
                      for name in (name.lower() for name in EVALUATORS)),
                    *(match_status(matches[name]) for name in compared_evaluators),
                    overall,
                )
                print("".join(
                    f"{value:<{width}}" for value, width in zip(values, widths)))
                summary_rows.append({
                    "analysis": analysis,
                    "nonterminals": size,
                    "dynamic_seconds": times["dynamic"],
                    "static_seconds": times["static"],
                    "synth_seconds": times["synth"],
                    "farrow_seconds": times["farrow"],
                    "dynamic_vs_static": match_status(matches["static"]),
                    "dynamic_vs_synth": match_status(matches["synth"]),
                    "dynamic_vs_farrow": match_status(matches["farrow"]),
                    "overall": overall,
                })

        summary_file = results_dir / "summary.csv"
        with summary_file.open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=summary_rows[0].keys())
            writer.writeheader()
            writer.writerows(summary_rows)


class CleanCommand(Command):
    name = "clean"
    help = "Remove generated benchmark outputs"

    def configure(self, parser):
        parser.add_argument("--programs", "--grammars", dest="grammars",
                            action="store_true", help="Also remove generated CFGs")
        parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)

    def run(self, args):
        results_dir = args.results_dir.resolve()
        for evaluator in EVALUATORS:
            directory = evaluator_dir(results_dir, evaluator)
            if directory.exists():
                shutil.rmtree(directory)
                print(f"  Removed {directory}")
        for name in ("diffs",):
            directory = results_dir / name
            if directory.exists():
                shutil.rmtree(directory)
                print(f"  Removed {directory}")
        summary_file = results_dir / "summary.csv"
        if summary_file.exists():
            summary_file.unlink()
            print(f"  Removed {summary_file}")
        cfg_dir = results_dir / "cfg"
        if args.grammars and cfg_dir.exists():
            shutil.rmtree(cfg_dir)
            print(f"  Removed {cfg_dir}")
        print("Done.")


COMMANDS = [GenerateCommand(), RunCommand(), CheckCommand(), TimesCommand(), CleanCommand()]


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark random CFGs across APS evaluators.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        command_parser = subparsers.add_parser(command.name, help=command.help)
        command.configure(command_parser)
        command_parser.set_defaults(command_object=command)

    args = parser.parse_args()
    try:
        args.command_object.run(args)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())