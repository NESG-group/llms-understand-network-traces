"""
cicids_aggregate_rounds.py
================================================================================
Summary of several CIC-IDS2017 runs at once (read-only): %C and %I per model,
view and level, with the mean and standard deviation across runs, plus the input
tokens and truncated prompts of every run.

Reads, for each model and run:
  results/cicids/<model>/run<N>/comparison/judge/<view>/judge_Monday*_answers.json
      ("summary" field: C, P, I, judge_errors, prompt_truncated_suspected,
       output_truncated, inconsistent_swaps)
  results/cicids/<model>/run<N>/llm_answers/<view>/Monday*_answers.json
      ("Questions" field: tokens_input, data_tokens, truncation_suspected, csv_source)

Blocks:
  A. Per model and view, levels L25-L75 together (no L100): %C and %I per run and
     mean ± sd across runs.
  B. Per model, view and level: %C per run and mean ± sd.
  C. Tokens: input tokens per run and level (general view: first question; filtered
     view: the maximum over any layer) and how many questions had a truncated prompt.

Reading caveats:
  - Levels are prefixes of the same window, so their 19 questions are not
    independent samples. The sd across runs is descriptive: do not turn it into a
    confidence interval with 2 or 3 runs.
  - Each run uses another window of the pcap (different packets), so differences
    between runs mix model randomness (almost none at temperature 0) with different
    traffic.
  - The absolute %C depends on how many questions have an empty layer in the
    window. To compare runs, also look at the "with content" blocks of
    cicids_round_analysis.py.

Usage (from the repository root):
  uv run python -m llms_understand_network_traces.cicids.cicids_aggregate_rounds --runs 1 2 3
  uv run python -m llms_understand_network_traces.cicids.cicids_aggregate_rounds --csv results/summary/cicids_rounds_long.csv
================================================================================
"""
import argparse
import csv
import glob
import json
import re
import statistics
from typing import Any

MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]
MODES = ("general", "filtered")
PCT = {25: 50, 50: 75, 75: 100, 100: 125}

Key = tuple[str, int, str, int]


def runs_found(models_dir: str) -> list[int]:
    found: set[int] = set()
    for path in glob.glob(f"{models_dir}/*/run*"):
        match = re.search(r"run(\d+)$", path)
        if match:
            found.add(int(match.group(1)))
    return sorted(found)


def collect(
    models_dir: str, runs: list[int], models: list[str]
) -> tuple[dict[Key, dict[str, int]], dict[Key, dict[str, Any]]]:
    judged: dict[Key, dict[str, int]] = {}
    tokens: dict[Key, dict[str, Any]] = {}
    for model in models:
        for run in runs:
            for mode in MODES:
                pattern = f"{models_dir}/{model}/run{run}/comparison/judge/{mode}/judge_Monday*_answers.json"
                for path in glob.glob(pattern):
                    match = re.search(r"_L(\d+)_(\d+)pkts", path)
                    if not match:
                        continue
                    with open(path, encoding="utf-8") as handle:
                        summary = json.load(handle).get("summary", {})
                    judged[(model, run, mode, int(match.group(1)))] = {
                        "pk": int(match.group(2)),
                        "C": summary.get("C", 0),
                        "P": summary.get("P", 0),
                        "I": summary.get("I", 0),
                        "err": summary.get("judge_errors", 0),
                        "ptrunc": summary.get("prompt_truncated_suspected", 0),
                        "otrunc": summary.get("output_truncated", 0),
                        "ties": summary.get("inconsistent_swaps", 0),
                    }
                pattern = f"{models_dir}/{model}/run{run}/llm_answers/{mode}/Monday*_answers.json"
                for path in glob.glob(pattern):
                    match = re.search(r"_L(\d+)_(\d+)pkts", path)
                    if not match:
                        continue
                    with open(path, encoding="utf-8") as handle:
                        questions = list(json.load(handle).get("Questions", {}).values())
                    if not questions:
                        continue
                    if mode == "general":
                        tok, layer = questions[0].get("tokens_input", 0), "general"
                    else:
                        best = max(questions, key=lambda q: q.get("tokens_input", 0))
                        tok, layer = best.get("tokens_input", 0), best.get("csv_source", "?")
                    tokens[(model, run, mode, int(match.group(1)))] = {
                        "tok": tok,
                        "layer": layer,
                        "trunc": sum(1 for q in questions if q.get("truncation_suspected")),
                    }
    return judged, tokens


def pct(num: float, den: float) -> float | None:
    return 100.0 * num / den if den else None


def ms(values: list[float | None]) -> str:
    valid = [x for x in values if x is not None]
    if not valid:
        return "   n/a"
    if len(valid) == 1:
        return f"{valid[0]:5.1f}      "
    return f"{statistics.mean(valid):5.1f} ± {statistics.stdev(valid):4.1f}"


def fmt(x: float | None) -> str:
    return "   - " if x is None else f"{x:5.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models-dir", default="results/cicids")
    parser.add_argument("--runs", type=int, nargs="*", default=None, help="runs to include (default: all found)")
    parser.add_argument("--csv", default=None, help="also save a long table (one row per model, run, view and level)")
    args = parser.parse_args()

    runs = args.runs or runs_found(args.models_dir)
    judged, tokens = collect(args.models_dir, runs, MODELS)
    if not judged:
        raise SystemExit(f"No judgements in {args.models_dir} for runs {runs}.")
    print(f"Runs: {runs}\n")

    print("A. %C and %I per model and view, levels L25-L75 (no L100), per run and mean ± sd across runs")
    head = "".join(f"{'r' + str(r):>7}" for r in runs)
    for label in ("C", "I"):
        print(f"\n  %{label}{'':<22}{head}   mean ± sd")
        for model in MODELS:
            for mode in MODES:
                values: list[float | None] = []
                for run in runs:
                    keys = [(model, run, mode, lvl) for lvl in (25, 50, 75) if (model, run, mode, lvl) in judged]
                    total = sum(judged[k]["C"] + judged[k]["P"] + judged[k]["I"] for k in keys)
                    values.append(pct(sum(judged[k][label] for k in keys), total) if len(keys) == 3 else None)
                if any(v is not None for v in values):
                    print(f"  {model + ' ' + mode:<24}" + "".join(f"{fmt(v):>7}" for v in values) + f"   {ms(values)}")

    print("\nB. %C per model, view and level, per run and mean ± sd across runs")
    print(f"  {'':<24}{'level':>6}{head}   mean ± sd")
    for model in MODELS:
        for mode in MODES:
            for lvl in PCT:
                values = []
                for run in runs:
                    j = judged.get((model, run, mode, lvl))
                    values.append(pct(j["C"], j["C"] + j["P"] + j["I"]) if j else None)
                if any(v is not None for v in values):
                    print(f"  {model + ' ' + mode:<24}{'L' + str(lvl):>6}"
                          + "".join(f"{fmt(v):>7}" for v in values) + f"   {ms(values)}")

    print("\nC. Input tokens per run and level (general: first question; filtered: maximum and its layer) "
          "and questions with a truncated prompt")
    for model in MODELS:
        for mode in MODES:
            for lvl in PCT:
                cells = []
                for run in runs:
                    t = tokens.get((model, run, mode, lvl))
                    if not t:
                        cells.append("-")
                        continue
                    cell = f"{t['tok']:,}" + ("" if mode == "general" else f" ({t['layer']})")
                    cells.append(cell + (f" TRUNC×{t['trunc']}" if t["trunc"] else ""))
                if any(c != "-" for c in cells):
                    print(f"  {model + ' ' + mode:<24}{'L' + str(lvl):>6}  "
                          + " | ".join(f"r{r}: {c}" for r, c in zip(runs, cells)))

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as out:
            writer = csv.writer(out)
            writer.writerow(["model", "run", "view", "level", "packets", "C", "P", "I", "pctC", "pctI",
                             "judge_errors", "truncated_prompts", "cut_outputs", "tie_breaks",
                             "tokens_input", "max_token_layer"])
            for (model, run, mode, lvl), j in sorted(judged.items()):
                n = j["C"] + j["P"] + j["I"]
                t = tokens.get((model, run, mode, lvl), {})
                pc_c, pc_i = pct(j["C"], n), pct(j["I"], n)
                writer.writerow([model, run, mode, lvl, j["pk"], j["C"], j["P"], j["I"],
                                 f"{pc_c:.1f}" if pc_c is not None else "",
                                 f"{pc_i:.1f}" if pc_i is not None else "",
                                 j["err"], j["ptrunc"], j["otrunc"], j["ties"],
                                 t.get("tok", ""), t.get("layer", "")])
        print(f"\nLong table saved to {args.csv}")


if __name__ == "__main__":
    main()