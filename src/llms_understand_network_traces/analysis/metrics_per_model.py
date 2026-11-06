"""
metrics_per_model.py
================================================================================
Computes evaluation metrics per model from judge results across multiple runs.

Metrics:
  1. % C / P / I per model x layer x mode (general & filtered)
  2. Improvement score general -> filtered  (I->P=+1, P->C=+1, I->C=+2)
  3. Cohen's kappa general vs filtered
  4. Inter-run agreement (% questions where all runs agree)
  5. Mode confidence distribution (e.g. 5/5, 4/5, 3/5 majority)
  6. Cross-trace consistency (std dev of %C across traces per model x layer)

Notes:
  - The question list comes from --constants (default:
    llms_understand_network_traces.utils.constants). A warning is printed whenever a
    judge file does not contain the questions of the selected module.
  - Labels other than C/P/I (E = judge error, N = the LLM gave no answer) and questions
    missing from a file are EXCLUDED, not counted as I. Percentages, kappa, score and
    votes are computed over the valid labels only, and the number of excluded items is
    reported per layer and mode.
  - Unreadable or half-written JSON files are skipped with a warning.
  - Traces are discovered across all runs (not only run1).
  - Traces are shown as T1, T2... with a key, so long trace names do not collide.

Expected structure:
    <models-dir>/<model>/run{N}/comparison/judge/general/judge_<trace>_answers.json
    <models-dir>/<model>/run{N}/comparison/judge/filtered/judge_<trace>_answers.json

Usage:
    uv run python -m llms_understand_network_traces.analysis.metrics_per_model
    uv run python -m llms_understand_network_traces.analysis.metrics_per_model --models-dir results/basic --output metrics.txt
    uv run python -m llms_understand_network_traces.analysis.metrics_per_model --models llama3.1:8b qwen2.5:72b
"""

import os
import re
import sys
import json
import math
import argparse
import importlib
from collections import Counter

from llms_understand_network_traces.utils.text import norm


VALID_LABELS = ("C", "P", "I")
TIE_PRIORITY = {"C": 0, "P": 1, "I": 2}

# Question layout: filled by set_layout() once --constants is known.
ALL_QUESTIONS = []
NUM_QUESTIONS = 0
LAYER_BOUNDARIES = {}


def set_layout(module_name: str):
    """Loads ALL_QUESTIONS and the layer boundaries from the given constants module."""
    global ALL_QUESTIONS, NUM_QUESTIONS, LAYER_BOUNDARIES
    mod = importlib.import_module(module_name)
    ALL_QUESTIONS = list(mod.ALL_QUESTIONS)
    NUM_QUESTIONS = len(ALL_QUESTIONS)
    n_arp = len(mod.ARP_QUESTIONS)
    n_ip = len(mod.IP_QUESTIONS)
    LAYER_BOUNDARIES = {
        "L2-ARP":     (0, n_arp),
        "L3-IP":      (n_arp, n_arp + n_ip),
        "L4-TCP/UDP": (n_arp + n_ip, NUM_QUESTIONS),
    }


# ==============================================================================
# IMPROVEMENT SCORE TABLE
# ==============================================================================

SCORE_TABLE = {
    ("I", "C"): +2,
    ("I", "P"): +1,
    ("P", "C"): +1,
    ("C", "P"): -1,
    ("P", "I"): -1,
    ("C", "I"): -2,
}

# ==============================================================================
# LABEL I/O
# ==============================================================================

def extract_label(question_result: dict):
    """C / P / I, or None for anything else (E, N, missing): excluded from the metrics."""
    for key in ("final_label", "label"):
        val = question_result.get(key)
        if val in VALID_LABELS:
            return val
    return None


def load_labels_from_file(filepath: str):
    """{normalised_question: C/P/I/None}. None if the file is missing or unreadable."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] cannot read {filepath}: {e}")
        return None
    return {norm(q): extract_label(v) for q, v in data.get("questions", {}).items()}


def labels_for_trace_single_run(run_folder: str, mode: str,
                                trace_stem: str, prefix: str = "judge_"):
    """
    List of C/P/I/None in ALL_QUESTIONS order, or None if the file is missing/unreadable.
    """
    filepath = os.path.join(run_folder, "comparison", "judge", mode,
                            f"{prefix}{trace_stem}_answers.json")
    label_map = load_labels_from_file(filepath)
    if label_map is None:
        return None
    absent = sum(1 for q in ALL_QUESTIONS if norm(q) not in label_map)
    if absent:
        print(f"  [WARN] {filepath}: {absent}/{NUM_QUESTIONS} questions of the selected "
              f"constants are not in the file (wrong --constants?). They are excluded.")
    return [label_map.get(norm(q)) for q in ALL_QUESTIONS]

# ==============================================================================
# MAJORITY VOTE  (tie-break: C > P > I; None votes ignored)
# ==============================================================================

def majority_vote(labels_per_run: list) -> list:
    result = []
    for q_idx in range(NUM_QUESTIONS):
        votes = [run[q_idx] for run in labels_per_run if run[q_idx] is not None]
        if not votes:
            result.append(None)
            continue
        counts = Counter(votes)
        max_count = max(counts.values())
        candidates = [l for l, c in counts.items() if c == max_count]
        result.append(min(candidates, key=lambda l: TIE_PRIORITY[l]))
    return result

# ==============================================================================
# DATA LOADING
# ==============================================================================

def list_run_dirs(model_dir: str) -> list:
    return sorted(
        os.path.join(model_dir, d)
        for d in os.listdir(model_dir)
        if re.match(r'^run\d+$', d) and os.path.isdir(os.path.join(model_dir, d))
    )


def discover_traces(model_dir: str, prefix: str) -> list:
    """Traces with a judge file in the general mode of ANY run."""
    traces = set()
    suffix = "_answers.json"
    for run_dir in list_run_dirs(model_dir):
        p = os.path.join(run_dir, "comparison", "judge", "general")
        if os.path.isdir(p):
            for f in os.listdir(p):
                if f.startswith(prefix) and f.endswith(suffix):
                    traces.add(f[len(prefix):-len(suffix)])
    return sorted(traces)


def load_model_data(model_dir: str, traces: list, prefix: str = "judge_"):
    """
    Returns (data, run_dirs, runs_with_data):
      data = {trace: {"general": [[labels_run1], ...], "filtered": [[...], ...]}}
    """
    run_dirs = list_run_dirs(model_dir)
    data = {t: {"general": [], "filtered": []} for t in traces}
    runs_with_data = set()

    for run_dir in run_dirs:
        for trace in traces:
            for mode in ("general", "filtered"):
                labels = labels_for_trace_single_run(run_dir, mode, trace, prefix)
                if labels is not None:
                    data[trace][mode].append(labels)
                    runs_with_data.add(os.path.basename(run_dir))

    return data, run_dirs, sorted(runs_with_data)

# ==============================================================================
# METRIC 1 — % C/P/I per layer x mode (over valid labels)
# ==============================================================================

def valid_slice(labels: list, start: int, end: int) -> list:
    return [l for l in labels[start:end] if l is not None]


def excluded_count(labels: list, start: int, end: int) -> int:
    return sum(1 for l in labels[start:end] if l is None)


def pct_cpi(labels: list, start: int, end: int) -> dict:
    sl = valid_slice(labels, start, end)
    n = len(sl)
    if n == 0:
        return {"C": None, "P": None, "I": None}
    return {cat: round(sl.count(cat) / n * 100, 1) for cat in VALID_LABELS}

# ==============================================================================
# METRIC 2 — Improvement score (pairs where both labels are valid)
# ==============================================================================

def improvement_score(gen: list, fil: list, start: int, end: int):
    pairs = [(g, f) for g, f in zip(gen[start:end], fil[start:end])
             if g is not None and f is not None]
    if not pairs:
        return None, None
    score = sum(SCORE_TABLE.get(p, 0) for p in pairs)
    norm_score = round(score / (len(pairs) * 2) * 100, 1)
    return score, norm_score

# ==============================================================================
# METRIC 3 — Cohen's kappa (pairs where both labels are valid)
# ==============================================================================

def cohen_kappa(a: list, b: list, start: int, end: int):
    pairs = [(x, y) for x, y in zip(a[start:end], b[start:end])
             if x is not None and y is not None]
    n = len(pairs)
    if n == 0:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    p_o = sum(1 for x, y in pairs if x == y) / n
    p_e = sum((xs.count(c) / n) * (ys.count(c) / n) for c in VALID_LABELS)
    if p_e == 1.0:
        return 1.0
    return round((p_o - p_e) / (1 - p_e), 3)

# ==============================================================================
# METRIC 4 — Inter-run agreement
# ==============================================================================

def inter_run_agreement(runs: list, start: int, end: int) -> dict:
    """
    For each question in [start, end), uses the valid labels of the runs.
      unanimous: % questions where all those runs give the same label
      strong   : % questions where >= 80% of those runs agree
    """
    n_q = unanimous = strong = 0
    for q_idx in range(start, end):
        votes = [run[q_idx] for run in runs if run[q_idx] is not None]
        if not votes:
            continue
        n_q += 1
        top = Counter(votes).most_common(1)[0][1]
        if top == len(votes):
            unanimous += 1
        if top >= math.ceil(0.8 * len(votes)):
            strong += 1
    if n_q == 0:
        return {"unanimous": None, "strong": None}
    return {
        "unanimous": round(unanimous / n_q * 100, 1),
        "strong":    round(strong / n_q * 100, 1),
    }

# ==============================================================================
# METRIC 5 — Mode confidence distribution
# ==============================================================================

def mode_confidence(runs: list, start: int, end: int) -> dict:
    """
    Distribution of majority strength across questions in [start, end).
    Keys look like "5/5" (votes for the winning label / valid votes).
    """
    buckets = Counter()
    n_q = 0
    for q_idx in range(start, end):
        votes = [run[q_idx] for run in runs if run[q_idx] is not None]
        if not votes:
            continue
        top = Counter(votes).most_common(1)[0][1]
        buckets[(top, len(votes))] += 1
        n_q += 1
    if n_q == 0:
        return {}
    ordered = sorted(buckets.items(), key=lambda kv: (-kv[0][0] / kv[0][1], -kv[0][1]))
    return {f"{t}/{v}": {"count": c, "pct": round(c / n_q * 100, 1)} for (t, v), c in ordered}

# ==============================================================================
# METRIC 6 — Cross-trace consistency (std dev of %C across traces)
# ==============================================================================

def cross_trace_std(pct_C_per_trace: list) -> float:
    n = len(pct_C_per_trace)
    if n < 2:
        return 0.0
    mean = sum(pct_C_per_trace) / n
    var = sum((x - mean) ** 2 for x in pct_C_per_trace) / (n - 1)
    return round(math.sqrt(var), 1)

# ==============================================================================
# FORMATTING HELPERS
# ==============================================================================

def hdr(title: str, width: int = 72) -> str:
    return f"\n{'=' * width}\n  {title}\n{'=' * width}"


def sub(title: str, width: int = 72) -> str:
    return f"\n  {title}\n  {'-' * (width - 2)}"


def sgn(val: float, dec: int = 1) -> str:
    fmt = f"{{:+.{dec}f}}" if val != 0 else f"{{:.{dec}f}}"
    return fmt.format(val)


def fp(v, w, dec=1):        # percentage cell
    return f"{'n/a':>{w}}" if v is None else f"{v:>{w - 1}.{dec}f}%"


def fs(v, w, dec=1):        # signed number cell
    return f"{'n/a':>{w}}" if v is None else f"{sgn(v, dec):>{w}}"


def fsp(v, w, dec=1):       # signed percentage cell
    return f"{'n/a':>{w}}" if v is None else f"{sgn(v, dec):>{w - 1}}%"


def fk(v, w):               # kappa cell
    return f"{'n/a':>{w}}" if v is None else f"{v:>{w}.3f}"


def row_label(text: str) -> str:
    return f"    {text:<20}"


def mean_valid(vals: list, dec: int = 1):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), dec) if vals else None


def kappa_label(k) -> str:
    if k is None:
        return "n/a"
    if k >= 0.81: return "almost perfect"
    if k >= 0.61: return "substantial"
    if k >= 0.41: return "moderate"
    if k >= 0.21: return "fair"
    if k >= 0.00: return "slight"
    return "poor"

# ==============================================================================
# MAIN REPORT
# ==============================================================================

def report_model(model_name: str, model_dir: str,
                 traces: list, prefix: str = "judge_") -> str:
    lines = []
    w = 72
    col_w = 10

    lines.append(hdr(f"MODEL: {model_name}", w))

    raw_data, run_dirs, runs_with_data = load_model_data(model_dir, traces, prefix)
    lines.append(f"\n  Run folders       : {[os.path.basename(r) for r in run_dirs]}")
    lines.append(f"  Runs with judging : {runs_with_data}")

    if not runs_with_data:
        lines.append("\n  [SKIP] No judge files found in any run.")
        return "\n".join(lines)

    mode_gen, mode_fil = {}, {}
    runs_gen, runs_fil = {}, {}

    for trace in traces:
        rg = raw_data[trace]["general"]
        rf = raw_data[trace]["filtered"]
        if rg:
            mode_gen[trace] = majority_vote(rg)
            runs_gen[trace] = rg
        if rf:
            mode_fil[trace] = majority_vote(rf)
            runs_fil[trace] = rf

    valid_traces = [t for t in traces if t in mode_gen and t in mode_fil]
    if not valid_traces:
        lines.append("\n  [SKIP] No traces with both general and filtered data.")
        return "\n".join(lines)

    tags = {t: f"T{i + 1}" for i, t in enumerate(valid_traces)}
    lines.append("\n  Trace key:")
    for t, tag in tags.items():
        n_g = len(runs_gen[t])
        n_f = len(runs_fil[t])
        lines.append(f"    {tag} = {t}   (runs: general {n_g}, filtered {n_f})")
    header = "".join(f"{tags[t]:>{col_w}}" for t in valid_traces)

    # -- METRIC 1 & 2 & 3 ------------------------------------------------------
    lines.append(sub("1. % C / P / I  |  2. Improvement score  |  3. Cohen's kappa", w))
    lines.append("  (percentages over valid labels; E/N/missing are excluded and counted below)")
    lines.append(f"\n  {'':22}{header}")

    for layer, (s, e) in LAYER_BOUNDARIES.items():
        lines.append(f"\n  [{layer}]")

        for mode_name, md in (("Gen", mode_gen), ("Fil", mode_fil)):
            for cat in VALID_LABELS:
                row = row_label(f"{mode_name}  {cat}")
                for t in valid_traces:
                    row += fp(pct_cpi(md[t], s, e)[cat], col_w)
                lines.append(row)

        for mode_name, md in (("Gen", mode_gen), ("Fil", mode_fil)):
            row = row_label(f"Excluded {mode_name}")
            for t in valid_traces:
                row += f"{excluded_count(md[t], s, e):>{col_w}d}"
            lines.append(row)

        row_b = row_label("Score (raw)")
        row_n = row_label("Score (norm)")
        row_k = row_label("Kappa")
        row_ki = row_label("Kappa interp.")
        for t in valid_traces:
            sb, sn = improvement_score(mode_gen[t], mode_fil[t], s, e)
            k = cohen_kappa(mode_gen[t], mode_fil[t], s, e)
            row_b += fs(sb, col_w)
            row_n += fsp(sn, col_w)
            row_k += fk(k, col_w)
            row_ki += f"{kappa_label(k)[:col_w - 1]:>{col_w}}"
        lines.extend([row_b, row_n, row_k, row_ki])

    # -- METRIC 4 — Inter-run agreement ------------------------------------------
    lines.append(sub("4. Inter-run agreement (general mode, valid votes only)", w))
    lines.append(f"\n  {'':22}{header}")

    for layer, (s, e) in LAYER_BOUNDARIES.items():
        lines.append(f"\n  [{layer}]")
        row_u = row_label("Unanimous")
        row_s = row_label("Strong (>=80%)")
        for t in valid_traces:
            ag = inter_run_agreement(runs_gen.get(t, []), s, e)
            row_u += fp(ag["unanimous"], col_w)
            row_s += fp(ag["strong"], col_w)
        lines.append(row_u)
        lines.append(row_s)

    # -- METRIC 5 — Mode confidence ----------------------------------------------
    lines.append(sub("5. Mode confidence distribution (general mode, all layers)", w))

    for t in valid_traces:
        lines.append(f"\n  {tags[t]} = {t}")
        conf = mode_confidence(runs_gen.get(t, []), 0, NUM_QUESTIONS)
        if not conf:
            lines.append("    (no valid votes)")
        for majority, vals in conf.items():
            bar = "#" * int(vals["pct"] / 5)
            lines.append(f"    {majority:>5} votes agree: "
                         f"{vals['count']:>3} questions  "
                         f"({vals['pct']:>5.1f}%)  {bar}")

    # -- METRIC 6 — Cross-trace consistency --------------------------------------
    lines.append(sub("6. Cross-trace consistency  (std dev of %C across traces)", w))
    lines.append(f"\n  {'Layer':<18} {'Mode':<10} {'Mean %C':>9} {'Std dev':>9}  Traces included")

    for layer, (s, e) in LAYER_BOUNDARIES.items():
        for mode_label, mode_dict in (("General", mode_gen), ("Filtered", mode_fil)):
            pcts = [pct_cpi(mode_dict[t], s, e)["C"] for t in valid_traces if t in mode_dict]
            pcts = [p for p in pcts if p is not None]
            if not pcts:
                continue
            mean = round(sum(pcts) / len(pcts), 1)
            std = cross_trace_std(pcts)
            lines.append(f"  {layer:<18} {mode_label:<10} {mean:>8.1f}%  {std:>8.1f}%  n={len(pcts)}")

    # -- GLOBAL SUMMARY (across traces) ------------------------------------------
    lines.append(sub("Summary (averaged across traces)", w))

    for layer, (s, e) in LAYER_BOUNDARIES.items():
        lines.append(f"\n  [{layer}]")
        for cat in VALID_LABELS:
            mg = mean_valid([pct_cpi(mode_gen[t], s, e)[cat] for t in valid_traces])
            mf = mean_valid([pct_cpi(mode_fil[t], s, e)[cat] for t in valid_traces])
            delta = None if mg is None or mf is None else round(mf - mg, 1)
            lines.append(f"    {cat}  Gen={fp(mg, 7)}  Fil={fp(mf, 7)}  Delta={fsp(delta, 8)}")

        mean_score = mean_valid([improvement_score(mode_gen[t], mode_fil[t], s, e)[1]
                                 for t in valid_traces])
        mean_k = mean_valid([cohen_kappa(mode_gen[t], mode_fil[t], s, e)
                             for t in valid_traces], dec=3)
        k_txt = "n/a" if mean_k is None else f"{mean_k:.3f}"
        lines.append(f"    Score norm mean={fsp(mean_score, 8)}  "
                     f"Kappa mean={k_txt} ({kappa_label(mean_k)})")

    return "\n".join(lines)

# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute evaluation metrics per model from judge results."
    )
    parser.add_argument("--models-dir", default="results/basic",
                        help="Root directory containing one subfolder per model (default: results/basic)")
    parser.add_argument("--output", default=None,
                        help="Optional path to save the report as a .txt file")
    parser.add_argument("--prefix", default="judge_",
                        help="Filename prefix of evaluation JSONs (default: judge_)")
    parser.add_argument("--models", nargs="*", default=None,
                        help="Restrict to these model names (default: all subdirs of --models-dir)")
    parser.add_argument("--constants", default="llms_understand_network_traces.utils.constants",
                        help="Module with ALL_QUESTIONS, ARP_QUESTIONS and IP_QUESTIONS "
                             "(default: llms_understand_network_traces.utils.constants)")
    args = parser.parse_args()

    set_layout(args.constants)
    print(f"Questions from {args.constants}: {NUM_QUESTIONS}  layers: {LAYER_BOUNDARIES}\n")

    if args.models:
        model_names = args.models
    else:
        model_names = sorted(
            d for d in os.listdir(args.models_dir)
            if os.path.isdir(os.path.join(args.models_dir, d))
        )

    if not model_names:
        print(f"No models found in {args.models_dir}")
        sys.exit(1)

    all_lines = []

    for model_name in model_names:
        model_dir = os.path.join(args.models_dir, model_name)
        traces = discover_traces(model_dir, args.prefix)

        if not traces:
            print(f"[SKIP] {model_name} - no general judge files in any run of {model_dir}")
            continue

        report = report_model(model_name, model_dir, traces, args.prefix)
        all_lines.append(report)
        print(report)

    if args.output:
        out_dir = os.path.dirname(args.output)
        os.makedirs(out_dir if out_dir else ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_lines))
        print(f"\n[OK] Report saved to {args.output}")