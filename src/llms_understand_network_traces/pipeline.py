"""Orchestrator for the full experimental pipeline.

Steps, in order: ``prepare`` (CIC-IDS windows), ``gt`` (PyShark ground truth),
``llm`` (model answers), ``judge`` (LLM-as-a-judge) and ``dotplot``.

Examples:
    uv run python -m llms_understand_network_traces.pipeline gt --dataset basic
    uv run python -m llms_understand_network_traces.pipeline llm --dataset basic --model llama3.1:8b --runs 5
    uv run python -m llms_understand_network_traces.pipeline judge --dataset basic --model llama3.1:8b --runs 5
    uv run python -m llms_understand_network_traces.pipeline prepare --model llama3.1:8b --run 1 \\
        --source data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng
    uv run python -m llms_understand_network_traces.pipeline all --dataset cicids --model llama3.1:8b --runs 5
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from llms_understand_network_traces.utils import constants

PACKAGE = "llms_understand_network_traces"
DEFAULT_JUDGE = "llama3.3:70b"
DEFAULT_MODES = ("general", "filtered")
ALL_MODES = ("general", "wide", "filtered")
MAX_GT_ATTEMPTS = 5
CICIDS_SOURCE = "data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng"
STEPS = ("prepare", "gt", "llm", "judge", "dotplot", "all")


@dataclass(frozen=True)
class Dataset:
    """Folder layout of one scenario."""

    name: str
    gt_dir: Path
    csv_dir: Path
    results_dir: Path
    raw_dir: Path | None


DATASETS: dict[str, Dataset] = {
    "basic": Dataset(
        name="basic",
        gt_dir=Path("data/qa"),
        csv_dir=Path("data/traces/processed_csv"),
        results_dir=Path("results/basic"),
        raw_dir=Path("data/traces/raw"),
    ),
    "cicids": Dataset(
        name="cicids",
        gt_dir=Path("results/ground_truth_cicids2017"),
        csv_dir=Path("data/cicids2017/processed_csv"),
        results_dir=Path("results/cicids"),
        raw_dir=None,
    ),
}


def slug(model: str) -> str:
    """Return the model name as used in staging folder names."""
    return model.replace(":", "-")


def staging_dir(model: str, run: int) -> Path:
    """Return the staging folder of a CIC-IDS model and run."""
    return Path("data/cicids2017/staging") / f"{slug(model)}_run{run}"


def cicids_stems(model: str, run: int) -> list[str]:
    """Return the trace stems of a CIC-IDS staging folder, smallest level first."""
    manifest = staging_dir(model, run) / "manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"missing {manifest}: run the 'prepare' step first")
    levels = json.loads(manifest.read_text())["levels"]
    return [level["stem"] for level in sorted(levels, key=lambda level: level["packets"])]


def run_module(module: str, args: Sequence[str]) -> None:
    """Run a package module as a subprocess and exit on failure."""
    cmd = [sys.executable, "-u", "-m", f"{PACKAGE}.{module}", *args]
    print(f"\n{'=' * 60}\n  {' '.join(cmd)}\n{'=' * 60}", flush=True)
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(f"step failed ({result.returncode}): {module}")


def gt_problems(gt_dir: Path, stems: Sequence[str]) -> list[str]:
    """Return the problems of the ground truth of the given traces (empty when usable)."""
    expected = set(constants.ALL_QUESTIONS)
    problems: list[str] = []
    for stem in stems:
        path = gt_dir / f"{stem}_answers.json"
        if not path.is_file():
            problems.append(f"missing ground truth for {stem}")
            continue
        questions = json.loads(path.read_text()).get("Questions", {})
        if set(questions) != expected:
            problems.append(f"{path.name}: question set differs from utils.constants")
        failed = [q for q, a in questions.items() if str(a).startswith("ERROR")]
        if failed:
            problems.append(f"{path.name}: {len(failed)} answer(s) with ERROR")
    return problems


def raw_stems(raw_dir: Path) -> list[str]:
    """Return the stems of the pcapng files in a folder."""
    return sorted(p.stem for p in raw_dir.glob("*.pcapng"))


def step_prepare(model: str, run: int, source: str) -> None:
    """Build the CIC-IDS window and level pcaps, then convert them to CSV."""
    dataset = DATASETS["cicids"]
    run_module("cicids.cicids_context", ["--model", model, "--run", str(run), "--source", source])
    run_module(
        "preprocessing.convert_pcap_to_csv",
        ["--input", str(staging_dir(model, run)), "--output", str(dataset.csv_dir)],
    )


def step_gt_basic(dataset: Dataset, force: bool) -> None:
    """Generate the ground truth of the basic traces."""
    assert dataset.raw_dir is not None
    stems = raw_stems(dataset.raw_dir)
    if not force and dataset.gt_dir.is_dir() and not gt_problems(dataset.gt_dir, stems):
        print(f"[gt] ground truth in {dataset.gt_dir} is valid, skipping")
        return
    run_module("evaluation.answer_with_pyshark", ["--input", str(dataset.raw_dir), "--output", str(dataset.gt_dir)])
    problems = gt_problems(dataset.gt_dir, stems)
    if problems:
        raise SystemExit("generated ground truth has problems:\n  " + "\n  ".join(problems))


def step_gt_cicids(dataset: Dataset, model: str, run: int, force: bool) -> None:
    """Generate the ground truth of one CIC-IDS staging folder, one trace per process with retries."""
    staging = staging_dir(model, run)
    dataset.gt_dir.mkdir(parents=True, exist_ok=True)
    for stem in cicids_stems(model, run):
        target = dataset.gt_dir / f"{stem}_answers.json"
        if not force and not gt_problems(dataset.gt_dir, [stem]):
            print(f"[gt] {stem}: valid, skipping")
            continue
        for attempt in range(1, MAX_GT_ATTEMPTS + 1):
            target.unlink(missing_ok=True)
            with tempfile.TemporaryDirectory() as tmp:
                shutil.copy2(staging / f"{stem}.pcapng", tmp)
                run_module("evaluation.answer_with_pyshark", ["--input", tmp, "--output", str(dataset.gt_dir)])
            if not gt_problems(dataset.gt_dir, [stem]):
                print(f"[gt] {stem}: OK (attempt {attempt})")
                break
            print(f"[gt] {stem}: attempt {attempt} failed")
        else:
            raise SystemExit(f"ground truth of {stem} still has errors after {MAX_GT_ATTEMPTS} attempts")


def step_llm(dataset: Dataset, model: str, run: int, mode: str, trace: str | None, extra: Sequence[str]) -> None:
    """Generate the model answers of one run."""
    base = [
        "--model", model,
        "--run", f"run{run}",
        "--csv-folder", str(dataset.csv_dir),
        "--results-dir", str(dataset.results_dir),
        "--mode", mode,
        *extra,
    ]
    if dataset.name == "cicids" and trace is None:
        for stem in cicids_stems(model, run):
            run_module("evaluation.answer_with_llm", [*base, "--trace", stem])
        return
    run_module("evaluation.answer_with_llm", [*base, *(["--trace", trace] if trace else [])])


def run_folder(dataset: Dataset, model: str, run: int) -> Path:
    """Return the output folder of a model and run."""
    return dataset.results_dir / model / f"run{run}"


def step_judge(dataset: Dataset, model: str, run: int, judge: str, modes: Sequence[str]) -> None:
    """Judge the answers of one run."""
    base = run_folder(dataset, model, run)
    for mode in modes:
        run_module(
            "comparison.compare_with_llm_judge",
            [
                "--judge-model", judge,
                "--gt-folder", str(dataset.gt_dir),
                "--llm-folder", str(base / "llm_answers" / mode),
                "--output-folder", str(base / "comparison" / "judge" / mode),
            ],
        )


def step_dotplot(dataset: Dataset, model: str, run: int, modes: Sequence[str]) -> None:
    """Draw the dotplot of one run."""
    if "general" not in modes or "filtered" not in modes:
        print(f"[dotplot] needs the general and filtered views, skipping (modes={list(modes)})")
        return
    base = run_folder(dataset, model, run)
    judge = base / "comparison" / "judge"
    args = [
        "--general-folder", str(judge / "general"),
        "--filtered-folder", str(judge / "filtered"),
        "--output", str(base / "dotplot_judge.png"),
        "--method", "judge",
    ]
    if "wide" in modes:
        args += ["--wide-folder", str(judge / "wide")]
    run_module("analysis.dotplot", args)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=STEPS)
    parser.add_argument("--dataset", choices=tuple(DATASETS), default="basic")
    parser.add_argument("--model", help="Ollama model that answers (e.g. llama3.1:8b)")
    parser.add_argument("--judge", default=DEFAULT_JUDGE, help=f"Ollama judge model (default: {DEFAULT_JUDGE})")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--first-run", type=int, default=1)
    parser.add_argument("--run", type=int, help="single run number (prepare only)")
    parser.add_argument("--trace", help="restrict the llm step to one trace stem")
    parser.add_argument("--mode", choices=(*ALL_MODES, "all"), default="all")
    parser.add_argument("--source", default=CICIDS_SOURCE, help="large CIC-IDS pcap (prepare)")
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--num-ctx", type=int, default=None)
    parser.add_argument("--num-predict", type=int, default=1024)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--force-gt", action="store_true", help="regenerate the ground truth even if valid")
    return parser


def llm_options(args: argparse.Namespace) -> list[str]:
    """Return the generation options forwarded to answer_with_llm."""
    options = [
        "--temperature", str(args.temperature),
        "--num-predict", str(args.num_predict),
        "--timeout", str(args.timeout),
        "--retries", str(args.retries),
    ]
    if args.num_ctx:
        options += ["--num-ctx", str(args.num_ctx)]
    return options


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    dataset = DATASETS[args.dataset]
    step: str = args.step
    needs_model = step != "gt" or dataset.name == "cicids"
    if needs_model and not args.model:
        parser.error(f"--model is required for step '{step}' on dataset '{dataset.name}'")
    modes = DEFAULT_MODES if args.mode == "all" else (args.mode,)
    if step == "prepare":
        if args.dataset != "cicids":
            parser.error("prepare only applies to --dataset cicids")
        runs = [args.run] if args.run else list(range(args.first_run, args.first_run + args.runs))
        for run in runs:
            step_prepare(args.model, run, args.source)
        return
    for run in range(args.first_run, args.first_run + args.runs):
        print(f"\n{'#' * 60}\n  run{run}  [{dataset.name}]  step={step}\n{'#' * 60}")
        if step in ("gt", "all"):
            if dataset.name == "basic":
                step_gt_basic(dataset, args.force_gt)
            else:
                step_gt_cicids(dataset, args.model, run, args.force_gt)
        if step in ("llm", "all"):
            step_llm(dataset, args.model, run, args.mode, args.trace, llm_options(args))
        if step in ("judge", "all"):
            step_judge(dataset, args.model, run, args.judge, modes)
        if step in ("dotplot", "all"):
            step_dotplot(dataset, args.model, run, modes)
    print("\nDone.")


if __name__ == "__main__":
    main()
