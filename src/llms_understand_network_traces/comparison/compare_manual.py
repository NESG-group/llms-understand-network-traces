"""
compare_manual.py
================================================================================
Compares your manual labels (C/P/I) with those of the LLM judge and measures the
agreement. It only reads files: it does not modify anything.

Input:
  --manual-dir  folder with the manually labelled JSON files (the ones produced by
                preprocesses_manual.py and filled in with manual_label), with the
                structure <model>/<view>/judge_<trace>_answers.json
  --judge-dir   folder with the original judge JSON files, with the structure
                <model>/<run>/comparison/judge/<view>/judge_<trace>_answers.json
  --run         judge run to compare (default run1)

What it computes (only with the questions you already labelled):
  A. exact agreement with its 95 % Wilson interval, Cohen's kappa and weighted kappa
     (linear weights: C > P > I are ordinal), and the C vs not-C kappa. Lines marked
     "per question" give 95 % bootstrap intervals resampling whole questions (trace +
     number), because answers of several models and views to the same question share a
     reference and are not independent. Wilson assumes independence, so it is optimistic.
  B. confusion matrix and, per label, coverage (row) and precision (column)
  C. direction of the disagreements (judge stricter or laxer), with a sign test, and how
     many are judge tie-breaks
  D. the same numbers by: tie-break or unanimous, empty or non-empty reference, layer,
     model and view; and D2: tie-break rate by model, view and layer
  E. sensitivity: without the files you saw with the judge at hand, per view, and with
     other tie-break rules (the laxest one, or no tie-breaks)
  F. consistency of the conclusions: %C and %I per model and view according to you and
     to the judge, model ranking and filtering effect

CIC-IDS2017 samples (preprocesses_manual.py --sample): questions with manual_label =
"SKIP" are not labelled and are ignored; the run of each file is read from its name
(_runN_), so the same directory can mix runs; and, for the bootstrap, answers of
different models to the same window and question are grouped (the model name is removed
from the trace name).

"Seen" files: --seen seen_by_judge.txt, one line per file with a piece of its path (for
example "llama3.1_8b/general/judge_arp-icmp"). Questions tagged [vio_juez] in the note
are also considered seen.

Reading caveat: questions with an empty reference are almost always agreed on (rule 4 of
the rubric), so the global agreement is inflated by them. Look at the "reference with
content" block. And with few questions, kappa is unstable.

Usage (from the repository root):
  uv run python -m llms_understand_network_traces.comparison.compare_manual \
    --manual-dir results/final/06-10-2026/comparison_manual/basic_run1 \
    --judge-dir results/basic \
    --seen seen_by_judge.txt \
    --out-dir results/final/06-10-2026/comparison_manual
================================================================================
"""
import argparse
import csv
import glob
import json
import math
import os
import random
import re
import sys
from collections import Counter
from typing import Any, Callable

from llms_understand_network_traces.utils.text import gt_empty, norm

LABELS = ("C", "P", "I")
IDX = {label: i for i, label in enumerate(LABELS)}
NAN = float("nan")

Pairs = list[tuple[str, str]]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return NAN, NAN
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def kappa(pairs: Pairs, weighted: bool = False) -> float:
    n = len(pairs)
    if n == 0:
        return NAN
    k = len(LABELS)
    matrix = [[0] * k for _ in range(k)]
    for a, b in pairs:
        matrix[IDX[a]][IDX[b]] += 1
    row = [sum(matrix[i]) for i in range(k)]
    col = [sum(matrix[i][j] for i in range(k)) for j in range(k)]
    if weighted:
        def weight(i: int, j: int) -> float:
            return 1 - abs(i - j) / (k - 1)
    else:
        def weight(i: int, j: int) -> float:
            return 1.0 if i == j else 0.0
    po = sum(weight(i, j) * matrix[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(weight(i, j) * row[i] * col[j] for i in range(k) for j in range(k)) / (n * n)
    return NAN if pe == 1 else (po - pe) / (1 - pe)


def boot_ci(
    groups: list[Pairs], stat: Callable[[Pairs], float], iters: int = 1000, seed: int = 42
) -> tuple[float, float]:
    """Bootstrap by groups (each group = all answers to the same question)."""
    if len(groups) < 8:
        return NAN, NAN
    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(iters):
        pairs = [p for _ in groups for p in groups[rng.randrange(len(groups))]]
        value = stat(pairs)
        if not math.isnan(value):
            values.append(value)
    if len(values) < iters / 2:
        return NAN, NAN
    values.sort()
    return values[int(0.025 * len(values))], values[min(len(values) - 1, int(0.975 * len(values)))]


def sign_test_p(a: int, b: int) -> float:
    """Exact two-sided binomial(n, 0.5) p for a versus b disagreements (indicative: not independent)."""
    n = a + b
    if n == 0:
        return NAN
    k = max(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def lenient(r: dict[str, Any]) -> str:
    """Judge label if ties were resolved to the laxest pass."""
    votes = [x for x in r["votes"].split("/") if x in IDX]
    return min(votes, key=lambda x: IDX[x]) if r["tie"] and votes else r["judge"]


def f2(x: float) -> str:
    return "  n/a" if math.isnan(x) else f"{x:5.2f}"


def line(name: str, rows: list[dict[str, Any]], boot: bool = False) -> None:
    if not rows:
        print(f"  {name:<34} n=  0")
        return
    pairs = [(r["manual"], r["judge"]) for r in rows]
    n = len(pairs)
    k = sum(a == b for a, b in pairs)
    lo, hi = wilson(k, n)
    text = (f"  {name:<34} n={n:>4}  agreement {k / n:5.1%} [{lo:5.1%}-{hi:5.1%}]  "
            f"kappa {f2(kappa(pairs))}  weighted kappa {f2(kappa(pairs, True))}")
    if boot:
        grouped: dict[tuple[str, int], Pairs] = {}
        for r in rows:
            grouped.setdefault((r["group"], r["qn"]), []).append((r["manual"], r["judge"]))
        groups = list(grouped.values())
        alo, ahi = boot_ci(groups, lambda p: sum(a == b for a, b in p) / len(p))
        klo, khi = boot_ci(groups, lambda p: kappa(p, True))
        text += (f"\n  {'':<34} per question ({len(groups)}): agreement [{alo:5.1%}-{ahi:5.1%}]  "
                 f"weighted kappa [{f2(klo)}, {f2(khi)}]")
    print(text)


def pct(rows: list[dict[str, Any]], who: str, label: str) -> float:
    return sum(r[who] == label for r in rows) / len(rows) if rows else NAN


def layer_of(i: int, n_arp: int, n_ip: int) -> str:
    return "ARP" if i <= n_arp else "IP" if i <= n_arp + n_ip else "TCP/UDP"


def load(
    manual_dir: str, judge_dir: str, run: str, seen: list[str], n_arp: int, n_ip: int
) -> tuple[list[dict[str, Any]], int, int, int]:
    rows: list[dict[str, Any]] = []
    pending = errors = missing = 0
    pattern = os.path.join(manual_dir, "**", "judge_*_answers.json")
    for path in sorted(glob.glob(pattern, recursive=True)):
        with open(path, encoding="utf-8") as handle:
            manual = json.load(handle)
        model, mode = manual.get("llm_model"), manual.get("mode")
        if not model or not mode:
            print(f"  [WARN] {path}: no llm_model/mode, skipped")
            continue
        trace = os.path.basename(path)[len("judge_"):-len("_answers.json")]
        run_match = re.search(r"_(run\d+)_L\d+_", trace)
        file_run = run_match.group(1) if run_match else run
        group = re.sub(r"_[^_]+_(run\d+_L\d+_\d+pkts)$", r"_\1", trace)
        judge_path = os.path.join(judge_dir, model, file_run, "comparison", "judge", mode, os.path.basename(path))
        if not os.path.exists(judge_path):
            print(f"  [WARN] judge file does not exist: {judge_path}")
            missing += 1
            continue
        with open(judge_path, encoding="utf-8") as handle:
            judged = {norm(q): v for q, v in json.load(handle)["questions"].items()}
        seen_file = any(p in path for p in seen)
        for i, (question, entry) in enumerate(manual["questions"].items(), 1):
            label = entry.get("manual_label", "")
            if label == "SKIP":
                continue
            if label not in LABELS:
                pending += 1
                continue
            verdict = judged.get(norm(question))
            if verdict is None or verdict.get("final_label") not in LABELS:
                errors += 1
                continue
            note = entry.get("notes") or ""
            tags = {t.lower() for t in re.findall(r"\[([^\]]+)\]", note)}
            votes = verdict.get("votes", {})
            rows.append({
                "model": model,
                "mode": mode,
                "trace": trace,
                "group": group,
                "qn": i,
                "manual": label,
                "judge": verdict["final_label"],
                "tie": not verdict.get("consistent", True),
                "votes": f'{votes.get("pass1")}/{votes.get("pass2")}',
                "gt_empty": gt_empty(verdict.get("gt_answer", "")),
                "layer": layer_of(i, n_arp, n_ip),
                "seen": seen_file or "vio_juez" in tags,
                "note": note,
                "question": question,
            })
    return rows, pending, errors, missing


class Tee:
    """Write to the terminal and to a file at the same time."""

    def __init__(self, *streams: Any) -> None:
        self.streams = streams

    def write(self, text: str) -> None:
        for stream in self.streams:
            stream.write(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manual-dir", required=True)
    parser.add_argument("--judge-dir", required=True)
    parser.add_argument("--run", default="run1")
    parser.add_argument("--seen", default=None, help="file with path fragments of the files seen with the judge")
    parser.add_argument("--layers", default="3,4", help="number of ARP and IP questions (default 3,4; the rest TCP/UDP)")
    parser.add_argument("--out-dir", default=None,
                        help="folder for the report (agreement_manual_vs_judge.txt) and the disagreements CSV")
    parser.add_argument("--out-csv", default=None, help="path of the disagreements CSV (default: inside --out-dir)")
    args = parser.parse_args()

    report = None
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        report = open(os.path.join(args.out_dir, "agreement_manual_vs_judge.txt"), "w", encoding="utf-8")
        sys.stdout = Tee(sys.__stdout__, report)
    out_csv = args.out_csv or (
        os.path.join(args.out_dir, "judge_disagreements.csv") if args.out_dir else "validation/judge_disagreements.csv"
    )

    seen: list[str] = []
    if args.seen and os.path.exists(args.seen):
        with open(args.seen, encoding="utf-8") as handle:
            seen = [x.strip() for x in handle if x.strip() and not x.startswith("#")]
    elif args.seen:
        print(f"[WARN] {args.seen} does not exist: the 'seen' lines of block E exclude nothing")
    n_arp, n_ip = (int(x) for x in args.layers.split(","))

    rows, pending, errors, missing = load(args.manual_dir, args.judge_dir, args.run, seen, n_arp, n_ip)
    if not rows:
        raise SystemExit("No labelled and matched question. Did you fill in manual_label? Are the paths right?")

    print(f"Compared pairs: {len(rows)}  |  not labelled by you: {pending}  |  judge E/N or unmatched: {errors}"
          f"  |  files without judgement: {missing}\n")

    print("A. Global")
    line("all", rows, boot=True)
    binary = [("C" if r["manual"] == "C" else "I", "C" if r["judge"] == "C" else "I") for r in rows]
    print(f"  {'C vs not-C (binary)':<34} kappa {f2(kappa(binary))}")

    print("\nB. Confusion matrix (rows: your label; columns: judge)")
    confusion = Counter((r["manual"], r["judge"]) for r in rows)
    print("        " + "".join(f"{'judge ' + label:>9}" for label in LABELS))
    for m in LABELS:
        print(f"  you {m}  " + "".join(f"{confusion[(m, j)]:>9}" for j in LABELS))
    print("   Per label (coverage = row: if you say X, so does the judge; "
          "precision = column: if the judge says X, so do you)")
    for label in LABELS:
        yours = sum(confusion[(label, j)] for j in LABELS)
        judges = sum(confusion[(m, label)] for m in LABELS)
        ok = confusion[(label, label)]
        cov = f"{ok}/{yours} ({ok / yours:.1%})" if yours else "n/a"
        prec = f"{ok}/{judges} ({ok / judges:.1%})" if judges else "n/a"
        print(f"   {label}:  coverage {cov:<16} precision {prec}")

    stricter = sum(IDX[r["judge"]] > IDX[r["manual"]] for r in rows)
    laxer = sum(IDX[r["judge"]] < IDX[r["manual"]] for r in rows)
    disagreements = [r for r in rows if r["manual"] != r["judge"]]
    print(f"\nC. Disagreements: {stricter + laxer} ({(stricter + laxer) / len(rows):.1%})  "
          f"judge stricter than you {stricter}  |  judge laxer than you {laxer}")
    if stricter + laxer:
        print(f"   Sign test (exact binomial, indicative: answers are not independent): "
              f"p = {sign_test_p(stricter, laxer):.2g}")
        ties_dis = sum(r["tie"] for r in disagreements)
        print(f"   Disagreements that are judge tie-breaks: {ties_dis} of {len(disagreements)} "
              f"({ties_dis / len(disagreements):.1%}); with both passes unanimous: {len(disagreements) - ties_dis}")
        by_kind = Counter((r["manual"], r["judge"], "tie-break" if r["tie"] else "unanimous") for r in disagreements)
        for (m, j, kind), n in sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"     you {m} -> judge {j} ({kind}): {n}")
    judge_c = [r for r in rows if r["judge"] == "C"]
    manual_c = [r for r in rows if r["manual"] == "C"]
    if judge_c:
        agree = sum(r["manual"] == "C" for r in judge_c)
        print(f"   Of the judge's {len(judge_c)} C, {agree} are also C for you ({agree / len(judge_c):.1%})"
              f"  <- the judge accepts an answer that you do not")
    if manual_c:
        agree = sum(r["judge"] == "C" for r in manual_c)
        print(f"   Of your {len(manual_c)} C, the judge gives C to {agree} ({agree / len(manual_c):.1%})")

    print("\nD. By case type")
    line("judge tie-break", [r for r in rows if r["tie"]])
    line("unanimous", [r for r in rows if not r["tie"]])
    line("empty reference (rule 4)", [r for r in rows if r["gt_empty"]])
    line("reference with content", [r for r in rows if not r["gt_empty"]], boot=True)
    for layer in ("ARP", "IP", "TCP/UDP"):
        line(f"layer {layer}", [r for r in rows if r["layer"] == layer])
    for model in sorted({r["model"] for r in rows}):
        line(f"model {model}", [r for r in rows if r["model"] == model])
    for mode in ("general", "filtered"):
        line(f"view {mode}", [r for r in rows if r["mode"] == mode])

    print("\nD2. Judge tie-breaks (its two passes disagree)")
    for key, name in (("model", "model"), ("mode", "view"), ("layer", "layer")):
        tie_count: Counter[str] = Counter()
        total: Counter[str] = Counter()
        for r in rows:
            total[r[key]] += 1
            tie_count[r[key]] += r["tie"]
        print(f"  by {name}: " + ", ".join(f"{k} {tie_count[k]}/{total[k]} ({tie_count[k] / total[k]:.1%})"
                                           for k in sorted(total)))
    ties = [r for r in rows if r["tie"]]
    if ties:
        matches = sum(r["manual"] in r["votes"].split("/") for r in ties)
        print(f"  In the {len(ties)} tie-breaks, your label matches one of the two passes in {matches}")

    print("\nE. Sensitivity")
    line("without the files seen with the judge", [r for r in rows if not r["seen"]], boot=True)
    for mode in ("general", "filtered"):
        line(f"view {mode}, without seen", [r for r in rows if r["mode"] == mode and not r["seen"]])
    line("tie-break: laxest pass", [dict(r, judge=lenient(r)) for r in rows], boot=True)
    line("no tie-breaks (unanimous only)", [r for r in rows if not r["tie"]], boot=True)

    print("\nF. Would the judge reach the same conclusions? (% of answers with each label)")
    print(f"  {'':<34}{'your %C':>9}{'judge %C':>9}{'your %I':>9}{'judge %I':>9}")
    models = sorted({r["model"] for r in rows})
    for model in models:
        for mode in ("general", "filtered"):
            subset = [r for r in rows if r["model"] == model and r["mode"] == mode]
            if subset:
                print(f"  {model + ' ' + mode:<34}{pct(subset, 'manual', 'C'):>9.1%}{pct(subset, 'judge', 'C'):>9.1%}"
                      f"{pct(subset, 'manual', 'I'):>9.1%}{pct(subset, 'judge', 'I'):>9.1%}")

    def rank(who: str) -> list[str]:
        return sorted(models, key=lambda m: -pct([r for r in rows if r["model"] == m], who, "C"))

    print(f"  Model order by %C, according to you:   {' > '.join(rank('manual'))}")
    print(f"                    according to the judge: {' > '.join(rank('judge'))}  "
          f"({'same order' if rank('manual') == rank('judge') else 'different order'})")
    print("  Filtering effect on %C (filtered - general):")
    for model in models:
        general = [r for r in rows if r["model"] == model and r["mode"] == "general"]
        filtered = [r for r in rows if r["model"] == model and r["mode"] == "filtered"]
        if general and filtered:
            dm = pct(filtered, "manual", "C") - pct(general, "manual", "C")
            dj = pct(filtered, "judge", "C") - pct(general, "judge", "C")
            print(f"    {model:<30} you {dm:+7.1%}   judge {dj:+7.1%}")

    if disagreements:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["model", "view", "trace", "question_n", "your_label", "judge", "judge_votes",
                             "tie_break", "seen", "your_note", "question"])
            for r in sorted(disagreements, key=lambda r: (r["model"], r["mode"], r["trace"], r["qn"])):
                writer.writerow([r["model"], r["mode"], r["trace"], r["qn"], r["manual"], r["judge"], r["votes"],
                                 int(r["tie"]), int(r["seen"]), r["note"], r["question"][:90]])
        print(f"\nDisagreements saved to {out_csv} ({len(disagreements)}).")
    if report:
        sys.stdout = sys.__stdout__
        report.close()
        print(f"Report saved to {os.path.join(args.out_dir, 'agreement_manual_vs_judge.txt')}")


if __name__ == "__main__":
    main()