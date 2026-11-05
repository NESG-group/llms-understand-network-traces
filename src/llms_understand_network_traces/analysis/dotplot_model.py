"""
dotplot_model.py
================================================================================
For each model under <models-dir>/<model>/, aggregates labels across all runs
(run1..runN) by majority vote (mode), then generates one dotplot per model
comparing the general and filtered views.

Notes:
  - The question list comes from --constants (default:
    llms_understand_network_traces.utils.constants). A warning is printed whenever a
    judge file does not contain the questions of the selected module.
  - Labels other than C/P/I (E = judge error, N = the LLM gave no answer) and questions
    missing from a file are NOT drawn as I: no dot is plotted for them.
  - Unreadable or half-written JSON files are skipped with a warning.
  - Traces are discovered across all runs (not only run1).
  - Headless-safe backend (Agg).

Expected structure:
    <models-dir>/<model>/run{N}/comparison/judge/general/judge_<trace>_answers.json
    <models-dir>/<model>/run{N}/comparison/judge/filtered/judge_<trace>_answers.json

Output:
    <output_dir>/<model_slug>/dotplot_<model_slug>.png

Usage:
    uv run python -m llms_understand_network_traces.analysis.dotplot_model --models-dir results/models
    uv run python -m llms_understand_network_traces.analysis.dotplot_model --output-dir output_graphs/dotplots
"""

import os
import re
import sys
import json
import argparse
import importlib
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from llms_understand_network_traces.utils.text import norm


VALID_LABELS = ("C", "P", "I")
TIE_PRIORITY = {"C": 0, "P": 1, "I": 2}

# Question layout: filled by set_layout() once --constants is known.
ALL_QUESTIONS = []
NUM_QUESTIONS = 0
LAYER_BOUNDARIES = {}
LAYER_SEPARATORS = []


def set_layout(module_name: str):
    """Loads ALL_QUESTIONS and the layer boundaries from the given constants module."""
    global ALL_QUESTIONS, NUM_QUESTIONS, LAYER_BOUNDARIES, LAYER_SEPARATORS
    mod = importlib.import_module(module_name)
    ALL_QUESTIONS = list(mod.ALL_QUESTIONS)
    NUM_QUESTIONS = len(ALL_QUESTIONS)
    n_arp = len(mod.ARP_QUESTIONS)
    n_ip = len(mod.IP_QUESTIONS)
    LAYER_BOUNDARIES = {
        "L2 - ARP":     (0, n_arp),
        "L3 - IP":      (n_arp, n_arp + n_ip),
        "L4 - TCP/UDP": (n_arp + n_ip, NUM_QUESTIONS),
    }
    LAYER_SEPARATORS = [n_arp, n_arp + n_ip]


# ==============================================================================
# LABEL EXTRACTION
# ==============================================================================

def extract_label(question_result: dict):
    """C / P / I, or None for anything else (E, N, missing): not drawn."""
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
        print(f"    [WARN] cannot read {filepath}: {e}")
        return None
    return {norm(q): extract_label(v) for q, v in data.get("questions", {}).items()}


def labels_for_trace_single_run(run_folder: str, mode: str,
                                trace_stem: str, prefix: str = "judge_"):
    """
    List of C/P/I/None in ALL_QUESTIONS order, or None if the file is missing/unreadable.
    mode: 'general' or 'filtered'
    """
    filepath = os.path.join(run_folder, "comparison", "judge", mode,
                            f"{prefix}{trace_stem}_answers.json")
    label_map = load_labels_from_file(filepath)
    if label_map is None:
        print(f"    [MISSING/UNREADABLE] {filepath}")
        return None
    absent = sum(1 for q in ALL_QUESTIONS if norm(q) not in label_map)
    if absent:
        print(f"    [WARN] {filepath}: {absent}/{NUM_QUESTIONS} questions of the selected "
              f"constants are not in the file (wrong --constants?). They are not drawn.")
    return [label_map.get(norm(q)) for q in ALL_QUESTIONS]

# ==============================================================================
# MODE AGGREGATION
# ==============================================================================

def majority_vote(labels_per_run: list) -> list:
    """
    Majority-vote label per question position over the runs, ignoring None votes.
    Tie-breaking order: C > P > I. None if no run has a valid label for that question.
    """
    result = []
    for q_idx in range(NUM_QUESTIONS):
        votes = [run[q_idx] for run in labels_per_run if run[q_idx] is not None]
        if not votes:
            result.append(None)
            continue
        counts = Counter(votes)
        max_count = max(counts.values())
        candidates = [lab for lab, cnt in counts.items() if cnt == max_count]
        result.append(min(candidates, key=lambda l: TIE_PRIORITY[l]))
    return result


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


def compute_mode_labels(model_dir: str, traces: list, prefix: str = "judge_"):
    """
    For every trace, aggregates labels across all runs found under model_dir.
    Returns (general_mode_labels, filtered_mode_labels): {trace_stem: [label x NUM_QUESTIONS]}
    """
    run_dirs = list_run_dirs(model_dir)
    if not run_dirs:
        print(f"  [WARN] No run* directories found in {model_dir}")
        return {}, {}

    print(f"  Runs found: {[os.path.basename(r) for r in run_dirs]}")

    general_mode, filtered_mode = {}, {}

    for trace in traces:
        gen_runs, filt_runs = [], []

        for run_dir in run_dirs:
            g = labels_for_trace_single_run(run_dir, "general", trace, prefix)
            f = labels_for_trace_single_run(run_dir, "filtered", trace, prefix)
            if g is not None:
                gen_runs.append(g)
            if f is not None:
                filt_runs.append(f)

        if gen_runs:
            general_mode[trace] = majority_vote(gen_runs)
        if filt_runs:
            filtered_mode[trace] = majority_vote(filt_runs)

    return general_mode, filtered_mode

# ==============================================================================
# DOTPLOT
# ==============================================================================

def generate_dotplot(traces: list, general_labels: dict, filtered_labels: dict,
                     method_label: str, output_path: str) -> None:
    col_cats     = ['C', 'P', 'I']
    num_blocks   = len(traces)
    col_colors   = {'C': '#2ca02c', 'P': '#ff7f0e', 'I': '#d62728'}
    trace_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

    fig, ax = plt.subplots(figsize=(max(9, num_blocks * 2.5), NUM_QUESTIONS * 0.55 + 4))

    # Grid
    for i in range(NUM_QUESTIONS + 1):
        ax.axhline(i - 0.5, color='#eeeeee', zorder=1)
    for j in range(num_blocks * 3 + 1):
        ax.axvline(j - 0.5, color='#eeeeee', zorder=1)

    # General - filled dots (no dot when the label is missing/excluded)
    for q_idx in range(NUM_QUESTIONS):
        for blk_idx, trace in enumerate(traces):
            labels = general_labels.get(trace, [])
            cat = labels[q_idx] if q_idx < len(labels) else None
            color = trace_colors[blk_idx % len(trace_colors)]
            for j, c in enumerate(col_cats):
                if cat == c:
                    ax.scatter(blk_idx * 3 + j, q_idx, s=60, color=color, zorder=4)

    # Filtered - hollow dots
    for q_idx in range(NUM_QUESTIONS):
        for blk_idx, trace in enumerate(traces):
            labels = filtered_labels.get(trace, [])
            cat = labels[q_idx] if q_idx < len(labels) else None
            for j, c in enumerate(col_cats):
                if cat == c:
                    ax.scatter(blk_idx * 3 + j, q_idx,
                               s=180, facecolors='none',
                               edgecolors='black', linewidths=1.5, zorder=5)

    # Axes
    ax.set_xlim(-0.5, num_blocks * 3 - 0.5)
    ax.set_ylim(NUM_QUESTIONS - 0.5, -0.5)
    ax.set_xticks([i * 3 + 1 for i in range(num_blocks)])
    ax.set_xticklabels(traces, rotation=45, ha='right', fontsize=9)
    ax.set_yticks(range(NUM_QUESTIONS))
    ax.set_yticklabels([f"P{i + 1}" for i in range(NUM_QUESTIONS)], fontsize=9)

    # C/P/I column headers
    for blk_idx in range(num_blocks):
        for j, cat in enumerate(col_cats):
            ax.text(blk_idx * 3 + j, -1.2, cat,
                    ha='center', va='center',
                    fontsize=7, fontweight='bold', color=col_colors[cat])

    # Separators
    for i in range(1, num_blocks):
        ax.axvline(x=i * 3 - 0.5, color='black', linestyle=(0, (2, 4)), linewidth=1)
    for sep in LAYER_SEPARATORS:
        ax.axhline(y=sep - 0.5, color='black', linestyle=(0, (2, 4)), linewidth=1)

    # Layer labels
    for layer_name, (start, end) in LAYER_BOUNDARIES.items():
        mid = (start + end - 1) / 2
        ax.text(-1.5, mid, layer_name, rotation=90,
                va='center', ha='center', fontsize=8, fontweight='bold')

    for spine in ax.spines.values():
        spine.set_visible(False)

    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
               markersize=8, label='General (color = trace)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='none',
               markeredgecolor='black', markeredgewidth=1.5,
               markersize=12, label='Filtered (layer-specific CSV)'),
    ]
    ax.legend(
        handles=legend_elements,
        loc='lower center',
        bbox_to_anchor=(0.5, 1.12),
        ncol=2,
        fontsize=10,
        frameon=True,
        title=f"Evaluation method: {method_label}",
        title_fontsize=10,
    )

    plt.subplots_adjust(left=0.18, bottom=0.22, right=0.97, top=0.82)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: {output_path}")
    plt.close()

# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Aggregate run labels by majority vote and generate one dotplot per model."
    )
    parser.add_argument("--models-dir", default="results/models",
                        help="Root directory containing one subfolder per model (default: results/models)")
    parser.add_argument("--output-dir", default="output_graphs/models",
                        help="Directory where per-model PNGs will be saved (default: output_graphs/models)")
    parser.add_argument("--prefix", default="judge_",
                        help="Filename prefix of evaluation JSONs (default: judge_)")
    parser.add_argument("--models", nargs="*", default=None,
                        help="Restrict to these model names (default: all subdirs of --models-dir)")
    parser.add_argument("--constants", default="llms_understand_network_traces.utils.constants",
                        help="Module with ALL_QUESTIONS, ARP_QUESTIONS and IP_QUESTIONS "
                             "(default: llms_understand_network_traces.utils.constants)")
    args = parser.parse_args()

    set_layout(args.constants)

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

    print(f"Models to process: {model_names}")
    print(f"Questions from {args.constants}: {NUM_QUESTIONS} ({list(LAYER_BOUNDARIES.keys())})\n")

    for model_name in model_names:
        model_dir = os.path.join(args.models_dir, model_name)
        print(f"{'=' * 60}")
        print(f"Model: {model_name}")
        print(f"{'=' * 60}")

        traces = discover_traces(model_dir, args.prefix)
        if not traces:
            print(f"  [SKIP] No evaluation files found in any run of {model_dir}\n")
            continue

        print(f"  Traces: {traces}")

        general_mode, filtered_mode = compute_mode_labels(model_dir, traces, args.prefix)

        if not general_mode:
            print(f"  [SKIP] No general labels computed for {model_name}\n")
            continue

        # Sanitise model name for filesystem (e.g. "llama3.1:8b" -> "llama3.1_8b")
        model_slug = re.sub(r'[^\w\-.]', '_', model_name)
        output_path = os.path.join(args.output_dir, model_slug, f"dotplot_{model_slug}.png")

        generate_dotplot(
            traces=traces,
            general_labels=general_mode,
            filtered_labels=filtered_mode,
            method_label=f"LLM-Judge | majority vote over runs | {model_name}",
            output_path=output_path,
        )
        print()