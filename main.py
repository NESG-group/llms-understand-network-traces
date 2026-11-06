"""
main.py
================================================================================
Main orchestrator for the LLMsUnderstandNetworkTraces pipeline.

Coordinates the full workflow:
  1. pyshark  — generate ground truth answers from PCAP traces
  2. llm      — generate LLM answers (general, wide and filtered views)
  3. judge    — evaluate LLM answers with LLM-as-a-Judge
  4. dotplot  — generate dotplot visualizations
  5. all      — run the full pipeline in order

Usage examples:
  python main.py --dataset cicids --action pyshark
  python main.py --dataset cicids --model qwen2.5:3b --action llm
  python main.py --dataset cicids --model qwen2.5:3b --judge qwen3.5:4b --action judge
  python main.py --dataset cicids --model qwen2.5:3b --judge qwen3.5:4b --action dotplot
  python main.py --dataset cicids --model qwen2.5:3b --judge qwen3.5:4b --runs 5 --action all
  python main.py --dataset cicids --model qwen2.5:3b --num-ctx 32768 --runs 4 --first-run 2 --action llm
  python main.py --dataset cicids --model qwen2.5:3b --num-ctx 32768 --trace Monday-WorkingHours_50pkts --mode filtered --action llm
"""

import os
import sys
import json
import argparse
import subprocess

# ==============================================================================
# PATHS
# ==============================================================================

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import utils.constants as constants

# Ground-truth folders carry the version of the questions so that a GT
# generated with an older question set is never reused by mistake.
DATASETS = {
    "basic": {
        "gt_folder":  os.path.join(ROOT, "results", "ground_truth"),
        "csv_folder": os.path.join(ROOT, "data", "networkTracesSamples", "processed_csv"),
        "raw_folder": os.path.join(ROOT, "data", "networkTracesSamples", "raw"),
    },
    "cicids": {
        "gt_folder":  os.path.join(ROOT, "results", "ground_truth_cicids2017"),
        "csv_folder": os.path.join(ROOT, "data", "cicids2017", "processed_csv"),
        "raw_folder": os.path.join(ROOT, "data", "cicids2017", "raw"),
    },
}

SCRIPTS = {
    "pyshark": os.path.join(ROOT, "src", "evaluation", "answer_with_pyshark.py"),
    "llm":     os.path.join(ROOT, "src", "evaluation", "answer_with_llm.py"),
    "judge":   os.path.join(ROOT, "src", "comparison", "compare_with_llm_judge.py"),
    "dotplot": os.path.join(ROOT, "src", "analysis", "dotplot.py"),
}

# Views run by default (--mode all). The "wide" view is left out for now; request it with --mode wide.
DEFAULT_MODES   = ["general", "filtered"]
AVAILABLE_MODES = ["general", "wide", "filtered"]

# ==============================================================================
# HELPERS
# ==============================================================================

def run(cmd: list, step: str):
    """Runs a subprocess command and exits on failure."""
    print(f"\n{'='*60}")
    print(f"  {step}")
    print(f"{'='*60}")
    print(f"  CMD: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"\n❌ Step failed: {step}")
        sys.exit(result.returncode)


def model_run_base(model: str, run_id: str) -> str:
    return os.path.join(ROOT, "results", "models", model, run_id)


def llm_answers_folder(model: str, run_id: str, mode: str) -> str:
    return os.path.join(model_run_base(model, run_id), "llm_answers", mode)


def eval_folder(model: str, run_id: str, method: str, mode: str) -> str:
    return os.path.join(model_run_base(model, run_id), "comparison", method, mode)


def dotplot_path(model: str, run_id: str, method: str) -> str:
    return os.path.join(model_run_base(model, run_id), f"dotplot_{method}.png")


def gt_problems(gt_folder: str, raw_folder: str) -> list:
    """
    Checks that the ground truth is usable: one file per raw trace, with exactly
    the current questions and no answer that is an error.
    """
    problems = []
    expected = set(constants.ALL_QUESTIONS)
    raw_stems = (
        sorted(os.path.splitext(f)[0] for f in os.listdir(raw_folder) if f.endswith(".pcapng"))
        if os.path.isdir(raw_folder) else []
    )
    for stem in raw_stems:
        path = os.path.join(gt_folder, f"{stem}_answers.json")
        if not os.path.exists(path):
            problems.append(f"missing GT for trace {stem}")
            continue
        with open(path) as f:
            questions = json.load(f).get("Questions", {})
        if set(questions) != expected:
            problems.append(f"{os.path.basename(path)}: question set differs from utils.constants")
        errors = [q for q, a in questions.items() if str(a).startswith("ERROR")]
        if errors:
            problems.append(f"{os.path.basename(path)}: {len(errors)} answer(s) with ERROR")
    return problems

# ==============================================================================
# STEPS
# ==============================================================================

def step_pyshark(dataset: dict, force: bool = False):
    """Generate ground truth answers with pyshark (reuse only if it is valid)."""
    gt_folder  = dataset["gt_folder"]
    raw_folder = dataset["raw_folder"]

    if not force and os.path.isdir(gt_folder) and os.listdir(gt_folder):
        problems = gt_problems(gt_folder, raw_folder)
        if not problems:
            print(f"\n[pyshark] Ground truth in {gt_folder} is valid — skipping.")
            return
        print(f"\n❌ Ground truth in {gt_folder} cannot be reused:")
        for p in problems:
            print(f"   - {p}")
        print("   Use --force-pyshark to regenerate it.")
        sys.exit(1)

    run(
        [
            sys.executable, "-u", SCRIPTS["pyshark"],
            "--input",  raw_folder,
            "--output", gt_folder,
        ],
        f"Generating ground truth with pyshark [{raw_folder}]"
    )

    problems = gt_problems(gt_folder, raw_folder)
    if problems:
        print(f"\n❌ The generated ground truth has problems:")
        for p in problems:
            print(f"   - {p}")
        sys.exit(1)


def step_llm(model: str, run_id: str, trace: str | None, mode: str, dataset: dict,
             temperature: float, num_ctx: int | None, num_predict: int, timeout: int, retries: int):
    """Generate LLM answers."""
    cmd = [
        sys.executable, "-u", SCRIPTS["llm"],
        "--model",       model,
        "--run",         run_id,
        "--csv-folder",  dataset["csv_folder"],
        "--mode",        mode,
        "--temperature", str(temperature),
        "--num-predict", str(num_predict),
        "--timeout",     str(timeout),
        "--retries",     str(retries),
    ]
    if num_ctx:                      # otherwise the script uses the model's own maximum context
        cmd += ["--num-ctx", str(num_ctx)]
    if trace:
        cmd += ["--trace", trace]
    run(cmd, f"Generating LLM answers [{model}] [{run_id}] [mode={mode}] "
             f"[temp={temperature}] [num_ctx={num_ctx or 'model max'}]")


def step_judge(model: str, run_id: str, judge_model: str, mode: str, dataset: dict):
    """Evaluate with LLM-as-a-Judge."""
    run(
        [
            sys.executable, "-u", SCRIPTS["judge"],
            "--judge-model",   judge_model,
            "--gt-folder",     dataset["gt_folder"],
            "--llm-folder",    llm_answers_folder(model, run_id, mode),
            "--output-folder", eval_folder(model, run_id, "judge", mode),
        ],
        f"LLM-as-Judge [{judge_model}] on [{model}] [{run_id}] [mode={mode}]"
    )


def step_dotplot(model: str, run_id: str, method: str, modes: list):
    if "general" not in modes or "filtered" not in modes:
        print(f"\n[dotplot] Needs the general and filtered views — skipping (modes={modes}).")
        return
    cmd = [
        sys.executable, "-u", SCRIPTS["dotplot"],
        "--general-folder",  eval_folder(model, run_id, method, "general"),
        "--filtered-folder", eval_folder(model, run_id, method, "filtered"),
        "--output",          dotplot_path(model, run_id, method),
        "--method",          method,
        "--prefix",          f"{method}_",
    ]
    if "wide" in modes:
        cmd += ["--wide-folder", eval_folder(model, run_id, method, "wide")]
    run(cmd, f"Dotplot [{method}] for [{model}] [{run_id}]")

# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LLMsUnderstandNetworkTraces — main orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--action", required=True,
        choices=["pyshark", "llm", "judge", "dotplot", "all"],
        help="Step to execute."
    )
    parser.add_argument("--model",  default=None, help="Ollama model for LLM answers (e.g. qwen2.5:3b)")
    parser.add_argument("--judge",  default=None, help="Ollama model for judge evaluation (e.g. qwen3.5:4b)")
    parser.add_argument("--trace",  default=None, help="Run only this trace stem. Default: all traces.")
    parser.add_argument("--runs",   default=1, type=int, help="Number of runs (default: 1)")
    parser.add_argument("--first-run", default=1, type=int,
                        help="Number of the first run (default: 1). E.g. --first-run 2 --runs 4 executes run2..run5.")
    parser.add_argument("--mode",   default="all", choices=AVAILABLE_MODES + ["all"],
                        help="View(s) to run (default: all = general + filtered; 'wide' only if requested). Applies to llm/judge/dotplot.")
    parser.add_argument("--dataset", default="basic", choices=list(DATASETS.keys()),
                        help="Which dataset to use: 'basic' (toy traces) or 'cicids' (default: basic)")
    parser.add_argument("--temperature", default=0, type=float,
                        help="Sampling temperature for LLM generation (default: 0)")
    parser.add_argument("--num-ctx", default=None, type=int,
                        help="Context window passed to Ollama. Default: each model's own maximum context.")
    parser.add_argument("--num-predict", default=1024, type=int,
                        help="Maximum output tokens per answer (default: 1024)")
    parser.add_argument("--timeout", default=600, type=int,
                        help="Timeout in seconds of the first attempt of each question; retries use 2x, 3x... (default: 600)")
    parser.add_argument("--retries", default=1, type=int,
                        help="Retries per question after a timeout or a transient server/connection error (default: 1)")
    parser.add_argument("--force-pyshark", action="store_true",
                        help="Regenerate ground truth even if it already exists.")

    args = parser.parse_args()

    if args.action in ("llm", "judge", "dotplot", "all") and not args.model:
        parser.error(f"--model is required for action '{args.action}'")
    if args.action in ("judge", "all") and not args.judge:
        parser.error(f"--judge is required for action '{args.action}'")

    dataset = DATASETS[args.dataset]
    modes = DEFAULT_MODES if args.mode == "all" else [args.mode]

    last_run = args.first_run + args.runs - 1
    for run_n in range(args.first_run, last_run + 1):
        run_id = f"run{run_n}"
        print(f"\n{'#'*60}")
        print(f"  RUN {run_n} of {args.first_run}..{last_run}  —  {run_id}  "
              f"[dataset={args.dataset}] [temp={args.temperature}]")
        print(f"{'#'*60}")

        if args.action == "pyshark":
            step_pyshark(dataset, force=args.force_pyshark)

        elif args.action == "llm":
            step_llm(args.model, run_id, args.trace, args.mode, dataset,
                     args.temperature, args.num_ctx, args.num_predict, args.timeout, args.retries)

        elif args.action == "judge":
            for mode in modes:
                step_judge(args.model, run_id, args.judge, mode, dataset)

        elif args.action == "dotplot":
            step_dotplot(args.model, run_id, "judge", modes)

        elif args.action == "all":
            step_pyshark(dataset, force=args.force_pyshark)
            step_llm(args.model, run_id, args.trace, args.mode, dataset,
                     args.temperature, args.num_ctx, args.num_predict, args.timeout, args.retries)
            for mode in modes:
                step_judge(args.model, run_id, args.judge, mode, dataset)
            step_dotplot(args.model, run_id, "judge", modes)

        print(f"\n✅ Run {run_n} completed.")

    print(f"\n✅ All done (runs {args.first_run}..{last_run}).")