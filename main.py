#!/usr/bin/env python3
"""Generate random CFGs and benchmark APS evaluators."""

import argparse
import csv
import difflib
import hashlib
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
APS_DIR = ROOT_DIR / ".." / "aps" / "examples" / "scala"
RESULTS_DIR = ROOT_DIR / "results"
EVALUATORS = ("DYNAMIC", "STATIC", "SYNTH")
RESULT_PREFIXES = ("FIRST ", "FOLLOW ", "NULLABLE ")


def cfg_files(results_dir):
    cfg_dir = results_dir / "cfg"
    return sorted(cfg_dir.glob("grammar-*.cfg"), key=cfg_size)


def cfg_size(cfg_file):
    return int(cfg_file.stem.removeprefix("grammar-"))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluator_dir(results_dir, evaluator):
    return results_dir / evaluator.lower()


def result_path(results_dir, evaluator, size):
    return evaluator_dir(results_dir, evaluator) / f"{size}.results"


def canonical_results(output_file):
    return sorted(
        line for line in output_file.read_text().splitlines(keepends=True)
        if line.startswith(RESULT_PREFIXES)
    )


def results_match(results_dir, reference, evaluator, size):
    reference_file = result_path(results_dir, reference, size)
    candidate_file = result_path(results_dir, evaluator, size)
    if (not reference_file.is_file() or reference_file.stat().st_size == 0
            or not candidate_file.is_file() or candidate_file.stat().st_size == 0):
        return None
    return sorted(reference_file.read_text().splitlines()) == sorted(
        candidate_file.read_text().splitlines()
    )


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
        parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)

    def run(self, args):
        if args.step <= 0 or args.start > args.stop:
            raise ValueError("require --step > 0 and --start <= --stop")

        results_dir = args.results_dir.resolve()
        cfg_dir = results_dir / "cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["dotnet", "build", "App/App.csproj"],
                       cwd=ROOT_DIR, check=True)

        generator_args = []
        if args.item_length is not None:
            generator_args.extend(["--itemlength", str(args.item_length)])
        if args.disallow_epsilon:
            generator_args.append("--DisallowEpsilon")
        if args.disallow_alternative:
            generator_args.append("--DisallowAlternative")

        for size in range(args.start, args.stop + 1, args.step):
            cfg_file = cfg_dir / f"grammar-{size}.cfg"
            if cfg_file.exists() and not args.force:
                print(f"  {cfg_file.name} already exists, skipping")
                continue
            print(f"  Generating {cfg_file.name} ({size} nonterminals) ...")
            with cfg_file.open("w") as output:
                subprocess.run(
                    ["dotnet", "run", "--no-build", "--project",
                     "App/App.csproj", "--", str(size), *generator_args],
                    cwd=ROOT_DIR, stdout=output, check=True,
                )

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
        parser.add_argument("--driver", default="GrammarDriver")
        parser.add_argument("--force", action="store_true",
                            help="Rerun completed CFGs")

    @staticmethod
    def run_one(cfg_file, evaluator, driver, aps_dir, results_dir, force):
        size = cfg_size(cfg_file)
        output_dir = evaluator_dir(results_dir, evaluator)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{size}.out"
        result_file = output_dir / f"{size}.results"
        time_file = output_dir / f"{size}.time"
        hash_file = output_dir / f"{size}.hash"
        current_hash = file_hash(cfg_file)

        if (not force and output_file.exists() and result_file.exists()
                and time_file.exists() and hash_file.exists()
                and hash_file.read_text().strip() == current_hash):
            return size, evaluator, "SKIPPED", float(time_file.read_text())

        start = time.monotonic()
        with output_file.open("w") as output:
            completed = subprocess.run(
                ["make", "--no-print-directory", f"EVALUATOR={evaluator}",
                 f"ARGS={cfg_file.resolve()}", f"{driver}.run"],
                cwd=aps_dir, stdout=output, stderr=subprocess.STDOUT,
            )
        elapsed = time.monotonic() - start
        time_file.write_text(f"{elapsed:.3f}\n")
        hash_file.write_text(current_hash + "\n")

        if completed.returncode != 0:
            result_file.unlink(missing_ok=True)
            return size, evaluator, f"FAILED (exit {completed.returncode})", elapsed

        result_file.write_text("".join(canonical_results(output_file)))
        return size, evaluator, "OK", elapsed

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

        evaluators = ([name.upper() for name in args.evaluators]
                      if args.evaluators else list(EVALUATORS))
        unknown = set(evaluators) - set(EVALUATORS)
        if unknown:
            raise ValueError(f"unknown evaluator(s): {', '.join(sorted(unknown))}")

        print(f"Found {len(grammars)} CFG file(s), batch size {args.jobs}, "
              f"driver {args.driver}\n")
        failed = False
        for evaluator in evaluators:
            print(f"=== Running with EVALUATOR={evaluator} ===")
            subprocess.run(
                ["make", "--no-print-directory", f"EVALUATOR={evaluator}", "clean"],
                cwd=aps_dir, check=True,
            )
            subprocess.run(
                ["make", "--no-print-directory", f"EVALUATOR={evaluator}",
                 f"{args.driver}.class"],
                cwd=aps_dir, check=True,
            )

            with ThreadPoolExecutor(max_workers=args.jobs) as executor:
                futures = [
                    executor.submit(
                        self.run_one, cfg_file, evaluator, args.driver,
                        aps_dir, results_dir, args.force,
                    )
                    for cfg_file in grammars
                ]
                for future in as_completed(futures):
                    size, name, status, elapsed = future.result()
                    print(f"  grammar-{size}.cfg -> {name} ... "
                          f"{status} ({elapsed:.3f}s)")
                    if status.startswith("FAILED"):
                        failed = True
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
        diff_dir = results_dir / "diffs"
        diff_dir.mkdir(parents=True, exist_ok=True)
        all_match = True

        for cfg_file in grammars:
            size = cfg_size(cfg_file)
            reference_file = result_path(results_dir, reference, size)
            size_matches = True
            for evaluator in evaluator_names:
                if evaluator == reference:
                    continue
                candidate_file = result_path(results_dir, evaluator, size)
                diff_file = diff_dir / f"{reference}-vs-{evaluator}-{size}.diff"
                match = results_match(results_dir, reference, evaluator, size)
                if match is None:
                    print(f"  MISSING: grammar-{size}.cfg in {evaluator}")
                    diff_file.write_text("MISSING\n")
                    size_matches = False
                    continue
                if match:
                    diff_file.write_text("MATCH\n")
                    continue

                reference_lines = sorted(reference_file.read_text().splitlines(keepends=True))
                candidate_lines = sorted(candidate_file.read_text().splitlines(keepends=True))
                diff = "".join(difflib.unified_diff(
                    reference_lines, candidate_lines,
                    fromfile=str(reference_file), tofile=str(candidate_file),
                ))
                diff_file.write_text(diff)
                print(f"  MISMATCH: grammar-{size}.cfg ({reference} vs {evaluator})")
                if args.verbose:
                    print(diff, end="")
                size_matches = False

            if size_matches:
                print(f"  OK: grammar-{size}.cfg")
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

        headers = ("Nonterminals", "DYNAMIC", "STATIC", "SYNTH",
                   "DYN=STATIC", "DYN=SYNTH", "Overall")
        widths = (14, 12, 12, 12, 14, 14, 12)
        print("".join(f"{value:<{width}}" for value, width in zip(headers, widths)))
        print("".join(f"{'-' * (width - 2):<{width}}" for width in widths))

        summary_rows = []
        for cfg_file in grammars:
            size = cfg_size(cfg_file)
            times = {}
            for evaluator in EVALUATORS:
                time_file = evaluator_dir(results_dir, evaluator) / f"{size}.time"
                times[evaluator.lower()] = (time_file.read_text().strip()
                                             if time_file.exists() else "N/A")
            static_match = results_match(results_dir, "dynamic", "static", size)
            synth_match = results_match(results_dir, "dynamic", "synth", size)
            status = lambda match: "MATCH" if match else ("MISMATCH" if match is False else "N/A")
            overall = ("MATCH" if static_match and synth_match else
                       "N/A" if static_match is None or synth_match is None else "MISMATCH")
            values = (str(size), *(f"{times[name]}s" if times[name] != "N/A" else "N/A"
                                   for name in ("dynamic", "static", "synth")),
                      status(static_match), status(synth_match), overall)
            print("".join(f"{value:<{width}}" for value, width in zip(values, widths)))
            summary_rows.append({
                "nonterminals": size,
                "dynamic_seconds": times["dynamic"],
                "static_seconds": times["static"],
                "synth_seconds": times["synth"],
                "dynamic_vs_static": status(static_match),
                "dynamic_vs_synth": status(synth_match),
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