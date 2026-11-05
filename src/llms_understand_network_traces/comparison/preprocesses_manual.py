"""
preprocesses_manual.py
================================================================================
Creates reduced copies of the judge JSON files for the manual validation.

By default it keeps, per question, everything UP TO AND INCLUDING 'final_label'
(question, gt_answer, llm_answer, truncation_suspected, margin_violated,
output_truncated, csv_empty, csv_rows, tokens_input, final_label...) and drops what
comes after (consistent, unanimous, single_pass, degraded, votes, pass1, pass2: the
judge votes and reasoning). The header and the summary are kept as they are.

Options:
  --blind    also drops the judge label (final_label) and, at file level, the summary
             and judge_model, so you can label without seeing the verdict. The original
             judge JSON files remain the key.
  --manual   adds the empty fields "manual_label" and "notes" to each question.
  --compact  condenses answers with repeated lines (loops): keeps the unique lines with a
             "[N lines, M unique]" notice and stores the full answer in "llm_answer_full".

SAMPLING (for CIC-IDS2017, where labelling everything is not feasible):
  --sample K        enables sampling: K questions WITH a non-empty reference for every
                    (model, level) cell, plus --sample-empty E with an empty reference
                    (default 1). The chosen questions are THE SAME in both views (general
                    and filtered), so the filtering effect can be compared. The selection
                    does not use the judge label.
  --runs 1 2 3 4 5  runs to choose from: for every (model, level) cell ONE random run is
                    picked (the same for both views). This covers different windows.
  --seed N          seed (default 2026): always the same sample.
  --max-gt-lines N  excludes (among the questions with content) those whose reference has
                    more than N lines (default 0 = no limit).
  Questions NOT chosen are kept in the file (so their question number and layer do not
  change) but with manual_label = "SKIP": they do not need to be labelled.
  <out>/sample_manifest.json is saved with the selection.

The originals are not touched. Output: <out>/<model>/<view>/<file>.json

Usage (from the repository root):
  # one full run (e.g. the basic traces)
  uv run python -m llms_understand_network_traces.comparison.preprocesses_manual \
      --models-dir results/models --run run1 --out <output> --blind --manual --compact
  # CIC-IDS2017 sample: 4 questions per model and level (3 with content + 1 empty), one random run per cell
  uv run python -m llms_understand_network_traces.comparison.preprocesses_manual \
      --models-dir results/models --runs 1 2 3 4 5 --sample 3 --sample-empty 1 \
      --out <output> --blind --manual --compact
================================================================================
"""
import argparse
import glob
import json
import os
import random
import re
from typing import Any

from llms_understand_network_traces.utils.text import gt_empty


def non_blank_lines(text: object) -> list[str]:
    return [line.strip() for line in str(text).splitlines() if line.strip()]


def compact_answer(text: str) -> tuple[str, bool]:
    """Return (condensed text, changed). Keeps the order of the unique lines."""
    lines = [line for line in str(text).splitlines() if line.strip()]
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    if len(unique) == len(lines):
        return text, False
    return f"[{len(lines)} lines, {len(unique)} unique]\n" + "\n".join(unique), True


def reduce_question(entry: dict[str, Any], blind: bool, manual: bool, compact: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in entry.items():
        if key == "final_label":
            if not blind:
                out[key] = value
            break
        out[key] = value
    if compact and "llm_answer" in out:
        condensed, changed = compact_answer(out["llm_answer"])
        if changed:
            out["llm_answer_full"] = out["llm_answer"]
            out["llm_answer"] = condensed
    if manual:
        out["manual_label"] = ""
        out["notes"] = ""
    return out


def reduce_file(
    data: dict[str, Any], blind: bool, manual: bool, compact: bool, keep: set[str] | None = None
) -> dict[str, Any]:
    """keep = None: all questions; otherwise the set of questions to label (the rest are SKIP)."""
    reduced: dict[str, Any] = {}
    for key, value in data.items():
        if key == "questions":
            continue
        if blind and key in ("summary", "judge_model"):
            continue
        reduced[key] = value
    questions: dict[str, Any] = {}
    for question, entry in data["questions"].items():
        if keep is None or question in keep:
            questions[question] = reduce_question(entry, blind, manual, compact)
        else:
            questions[question] = {"question": entry.get("question", question), "manual_label": "SKIP", "notes": ""}
    reduced["questions"] = questions
    return reduced


def level_of(path: str) -> int | None:
    match = re.search(r"_L(\d+)_", os.path.basename(path))
    return int(match.group(1)) if match else None


def choose_questions(
    general_data: dict[str, Any], k: int, e: int, max_gt_lines: int, rng: random.Random
) -> set[str]:
    """K questions with a non-empty reference + E with an empty one (completed with others if short)."""
    items = [(q, v.get("gt_answer", "")) for q, v in general_data["questions"].items()]
    content = [
        q for q, gt in items
        if not gt_empty(gt) and (max_gt_lines <= 0 or len(non_blank_lines(gt)) <= max_gt_lines)
    ]
    empty = [q for q, gt in items if gt_empty(gt)]
    chosen = rng.sample(content, min(k, len(content)))
    want_empty = e + (k - len(chosen))
    chosen += rng.sample(empty, min(want_empty, len(empty)))
    rest = [q for q, _ in items if q not in chosen]
    if len(chosen) < k + e:
        chosen += rng.sample(rest, min(k + e - len(chosen), len(rest)))
    return set(chosen)


def load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)
    return data


def meta(path: str) -> tuple[str, str, str]:
    parts = path.split(os.sep)
    return parts[-6], parts[-5], parts[-2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models-dir", required=True,
                        help="Folder with <model>/<run>/comparison/judge/<view>/judge_*.json")
    parser.add_argument("--run", default="run1", help="Run to process (default run1); ignored when --runs is used")
    parser.add_argument("--runs", type=int, nargs="*", default=None, help="Runs to sample from (with --sample)")
    parser.add_argument("--out", required=True, help="Output folder")
    parser.add_argument("--blind", action="store_true")
    parser.add_argument("--manual", action="store_true")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--sample", type=int, default=0,
                        help="K questions with content per (model, level) cell; 0 = no sampling")
    parser.add_argument("--sample-empty", type=int, default=1,
                        help="E questions with an empty reference per cell (default 1)")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--max-gt-lines", type=int, default=0,
                        help="exclude references longer than N lines (0 = no limit)")
    args = parser.parse_args()

    runs = [f"run{r}" for r in args.runs] if (args.sample and args.runs) else [args.run]
    files: list[str] = []
    pattern = ""
    for run in runs:
        pattern = os.path.join(args.models_dir, "*", run, "comparison", "judge", "*", "judge_*_answers.json")
        files += sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No files found with the pattern:\n  {pattern}\nAre you in the repository root?")

    plan: list[tuple[str, set[str] | None]] = []
    manifest: list[dict[str, Any]] = []
    if args.sample:
        cells: dict[tuple[str, int | None], dict[str, dict[str, str]]] = {}
        for path in files:
            model, run, view = meta(path)
            cells.setdefault((model, level_of(path)), {}).setdefault(run, {})[view] = path
        for (model, level), by_run in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
            rng = random.Random(f"{args.seed}|{model}|{level}")
            complete = sorted(r for r, v in by_run.items() if "general" in v and "filtered" in v)
            run = rng.choice(complete or sorted(by_run))
            views = by_run[run]
            reference = views.get("general") or next(iter(views.values()))
            reference_data = load_json(reference)
            chosen = choose_questions(reference_data, args.sample, args.sample_empty, args.max_gt_lines, rng)
            for _view, path in sorted(views.items()):
                plan.append((path, chosen))
            question_list = list(reference_data["questions"])
            manifest.append({
                "model": model,
                "run": run,
                "level": level,
                "views": sorted(views),
                "question_numbers": sorted(question_list.index(q) + 1 for q in chosen),
            })
    else:
        plan = [(path, None) for path in files]

    n_files = n_label = 0
    for path, keep in plan:
        model, _run, mode = meta(path)
        reduced = reduce_file(load_json(path), args.blind, args.manual, args.compact, keep)
        dst_dir = os.path.join(args.out, model.replace(":", "_"), mode)
        os.makedirs(dst_dir, exist_ok=True)
        with open(os.path.join(dst_dir, os.path.basename(path)), "w", encoding="utf-8") as handle:
            json.dump(reduced, handle, indent=4, ensure_ascii=False)
        n_files += 1
        n_label += len(reduced["questions"]) if keep is None else len(keep)

    if args.sample:
        with open(os.path.join(args.out, "sample_manifest.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "seed": args.seed,
                "sample": args.sample,
                "sample_empty": args.sample_empty,
                "runs": args.runs,
                "max_gt_lines": args.max_gt_lines,
                "cells": manifest,
            }, handle, indent=2)
    print(f"{n_files} files, {n_label} questions to label -> {args.out}")
    print(f"options: blind={args.blind} manual={args.manual} compact={args.compact} sample={args.sample}")


if __name__ == "__main__":
    main()