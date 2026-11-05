"""
dotplot.py
================================================================================
Dotplot visualization for LLM answer evaluation.

Reads judge evaluation results and plots one row per question and one block per
trace, comparing the views:
  - general  : filled circle   (color = trace)
  - wide     : hollow diamond  (color = trace)           [optional]
  - filtered : hollow black ring

Columns inside each trace block:
  C (correct), P (partial), I (incorrect), N/E (no valid evaluation: the LLM
  produced no answer, or the judge failed). N/E answers are NOT counted as I.

Questions and layer boundaries are read from utils.constants, so the plot
updates automatically if the questions change. Results are matched to rows by
question text: a result file generated with a different version of the
questions is reported (and aborts if nothing matches) instead of being drawn
as "all incorrect".

Context-level traces (names containing _L<n>_<N>pkts) are ordered by level and
labelled with the share of the data budget and the number of packets. Any other
trace (e.g. the basic ones) keeps its alphabetical order and its full name.
"""

import os
import re
import sys
import json
import argparse

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from llms_understand_network_traces.utils import constants

# ==============================================================================
# QUESTION LAYOUT — read from constants
# ==============================================================================

ALL_QUESTIONS = constants.ALL_QUESTIONS
NUM_QUESTIONS = len(ALL_QUESTIONS)

N_ARP = len(constants.ARP_QUESTIONS)
N_IP  = len(constants.IP_QUESTIONS)

# Layer boundary indices (exclusive end)
LAYER_BOUNDARIES = {
    "L2 - ARP":     (0,            N_ARP),
    "L3 - IP":      (N_ARP,        N_ARP + N_IP),
    "L4 - TCP/UDP": (N_ARP + N_IP, NUM_QUESTIONS),
}

# Horizontal separators are drawn before these indices
LAYER_SEPARATORS = [N_ARP, N_ARP + N_IP]

# Columns of each trace block
COLS       = ["C", "P", "I", "X"]
COL_NAMES  = {"X": "N/E"}
COL_COLORS = {"C": "#2ca02c", "P": "#ff7f0e", "I": "#d62728", "X": "#7f7f7f"}
BLOCK_W    = len(COLS)

TRACE_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
LABEL_KEY = None   # None = claves del juez (final_label / label)

def _norm(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip())


NORMALIZED_QUESTIONS = [_norm(q) for q in ALL_QUESTIONS]

# Level name (L25...) -> % of the data budget. Update it if you change the levels.
LEVEL_PCT = {"25": 50, "50": 75, "75": 100, "100": 125}


def trace_order(stem: str):
    """Sorts context-level traces by level (L25, L50, L75, L100); the rest go last, alphabetically."""
    m = re.search(r'_L(\d+)_', stem)
    return (int(m.group(1)) if m else 10**9, stem)


def trace_label(stem: str) -> str:
    """Short x-axis label (level and packets). Without a level in the name, the name itself."""
    m = re.search(r'_L(\d+)_(\d+)pkts$', stem)
    if not m:
        return stem
    pct = LEVEL_PCT.get(m.group(1), m.group(1))
    return f"{pct} %\n{int(m.group(2)):,} pkts".replace(",", ".")

# ==============================================================================
# LABEL EXTRACTION
# ==============================================================================

def extract_label(question_result: dict):
    """
    Returns "C", "P" or "I"; "X" for E (judge error) or N (no LLM answer);
    None if there is no usable label.
    """
    if LABEL_KEY:
        label = question_result.get(LABEL_KEY)
    else:
        label = question_result.get("final_label") or question_result.get("label")
    if label in ("C", "P", "I"):
        return label
    if label in ("E", "N"):
        return "X"
    return None


def load_labels_from_file(filepath: str):
    """
    Loads {normalized question: label} from a judge evaluation JSON.
    Returns None if the file does not exist.
    """
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        data = json.load(f)

    questions = data.get("questions", {})
    return {_norm(q): extract_label(v) for q, v in questions.items()}


def labels_for_trace(eval_folder: str, trace_stem: str, prefix: str = "judge_") -> list:
    """
    Returns a list of labels in ALL_QUESTIONS order for one trace.
    Missing file or question -> None (nothing is drawn). Aborts if the file
    exists but none of its questions match the current constants.
    """
    filepath = os.path.join(eval_folder, f"{prefix}{trace_stem}_answers.json")
    label_map = load_labels_from_file(filepath)

    if label_map is None:
        print(f"⚠️  Missing evaluation file: {filepath}")
        return [None] * NUM_QUESTIONS

    matched = [q for q in NORMALIZED_QUESTIONS if q in label_map]
    if label_map and not matched:
        raise ValueError(
            f"None of the {len(label_map)} questions in {filepath} matches utils.constants. "
            f"The results were probably generated with a different version of the questions."
        )
    if len(matched) != NUM_QUESTIONS or len(label_map) != NUM_QUESTIONS:
        print(f"⚠️  {filepath}: {len(matched)}/{NUM_QUESTIONS} current questions matched, "
              f"{len(label_map)} questions in file")

    return [label_map.get(q) for q in NORMALIZED_QUESTIONS]

# ==============================================================================
# DOTPLOT
# ==============================================================================

def generate_dotplot(
    traces:         list,
    labels_by_view: dict,   # {"general": {trace: [labels]}, "wide": {...}, "filtered": {...}}
    method_label:   str,
    output_path:    str,
):
    num_blocks = len(traces)

    fig, ax = plt.subplots(
        figsize=(max(9, num_blocks * BLOCK_W * 0.85), NUM_QUESTIONS * 0.55 + 4)
    )

    # Grid
    for i in range(NUM_QUESTIONS + 1):
        ax.axhline(i - 0.5, color='#eeeeee', zorder=1)
    for j in range(num_blocks * BLOCK_W + 1):
        ax.axvline(j - 0.5, color='#eeeeee', zorder=1)

    def cell_x(blk_idx, cat):
        return blk_idx * BLOCK_W + COLS.index(cat)

    # General — small filled circles (color = trace)
    for blk_idx, trace in enumerate(traces):
        color = TRACE_COLORS[blk_idx % len(TRACE_COLORS)]
        for q_idx, cat in enumerate(labels_by_view.get("general", {}).get(trace, [])):
            if cat is None:
                continue
            ax.scatter(cell_x(blk_idx, cat), q_idx, s=60, color=color, marker='o', zorder=4)

    # Wide — hollow diamonds (color = trace)
    for blk_idx, trace in enumerate(traces):
        color = TRACE_COLORS[blk_idx % len(TRACE_COLORS)]
        for q_idx, cat in enumerate(labels_by_view.get("wide", {}).get(trace, [])):
            if cat is None:
                continue
            ax.scatter(cell_x(blk_idx, cat), q_idx, s=130, facecolors='none',
                       edgecolors=color, linewidths=1.5, marker='D', zorder=5)

    # Filtered — large hollow black rings
    for blk_idx, trace in enumerate(traces):
        for q_idx, cat in enumerate(labels_by_view.get("filtered", {}).get(trace, [])):
            if cat is None:
                continue
            ax.scatter(cell_x(blk_idx, cat), q_idx, s=240, facecolors='none',
                       edgecolors='black', linewidths=1.5, marker='o', zorder=6)

    # Axes
    ax.set_xlim(-0.5, num_blocks * BLOCK_W - 0.5)
    ax.set_ylim(NUM_QUESTIONS - 0.5, -0.5)
    ax.set_xticks([i * BLOCK_W + (BLOCK_W - 1) / 2 for i in range(num_blocks)])

    # Short labels (level + packets) for context-level traces; full names, rotated, for the rest
    tick_labels = [trace_label(t) for t in traces]
    leveled = all('\n' in l for l in tick_labels)
    ax.set_xticklabels(tick_labels,
                       rotation=0 if leveled else 45,
                       ha='center' if leveled else 'right',
                       fontsize=10 if leveled else 9)

    ax.set_yticks(range(NUM_QUESTIONS))
    ax.set_yticklabels([f"P{i+1}" for i in range(NUM_QUESTIONS)], fontsize=9)

    # Column headers
    for blk_idx in range(num_blocks):
        for j, cat in enumerate(COLS):
            ax.text(blk_idx * BLOCK_W + j, -1.2, COL_NAMES.get(cat, cat),
                    ha='center', va='center', fontsize=7, fontweight='bold',
                    color=COL_COLORS[cat])

    # Vertical separators between traces
    for i in range(1, num_blocks):
        ax.axvline(x=i * BLOCK_W - 0.5, color='black', linestyle=(0, (2, 4)), linewidth=1)

    # Horizontal separators between layers
    for sep in LAYER_SEPARATORS:
        ax.axhline(y=sep - 0.5, color='black', linestyle=(0, (2, 4)), linewidth=1)

    # Layer labels on the left
    for layer_name, (start, end) in LAYER_BOUNDARIES.items():
        mid = (start + end - 1) / 2
        ax.text(-1.5, mid, layer_name, rotation=90, va='center', ha='center',
                fontsize=8, fontweight='bold')

    for spine in ax.spines.values():
        spine.set_visible(False)

    # Legend (only the views that are present)
    legend_elements = []
    if "general" in labels_by_view:
        legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
                                      markersize=8, label='General (color = trace)'))
    if "wide" in labels_by_view:
        legend_elements.append(Line2D([0], [0], marker='D', color='w', markerfacecolor='none',
                                      markeredgecolor='gray', markeredgewidth=1.5,
                                      markersize=9, label='Wide (color = trace)'))
    if "filtered" in labels_by_view:
        legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='none',
                                      markeredgecolor='black', markeredgewidth=1.5,
                                      markersize=12, label='Filtered (layer-specific CSV)'))
    ax.legend(
        handles=legend_elements,
        loc='lower center',
        bbox_to_anchor=(0.5, 1.12),
        ncol=len(legend_elements),
        fontsize=10,
        frameon=True,
        title=f"Evaluation method: {method_label}   (N/E = no LLM answer or judge error)",
        title_fontsize=10,
    )

    plt.subplots_adjust(left=0.18, bottom=0.12 if leveled else 0.22, right=0.97, top=0.82)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: {output_path}")
    plt.close()

# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dotplot from judge evaluation results.")
    parser.add_argument("--general-folder",  required=True, help="Folder with judge results for the general view")
    parser.add_argument("--filtered-folder", required=True, help="Folder with judge results for the filtered view")
    parser.add_argument("--wide-folder",     default=None,  help="Folder with judge results for the wide view (optional)")
    parser.add_argument("--output",          required=True, help="Output path for the dotplot PNG")
    parser.add_argument("--method",          default="LLM-Judge", help="Method label for the plot title")
    parser.add_argument("--prefix",          default="judge_", help="Filename prefix of evaluation JSONs")
    parser.add_argument("--label-key", default=None, help="Clave con la etiqueta (p. ej. manual_label)")
    args = parser.parse_args()

    LABEL_KEY = args.label_key

    # Discover traces from the general folder (context levels in level order)
    traces = sorted(
        (os.path.splitext(f)[0][len(args.prefix):].replace("_answers", "")
         for f in os.listdir(args.general_folder)
         if f.endswith(".json") and f.startswith(args.prefix)),
        key=trace_order,
    )

    if not traces:
        print(f"⚠️  No evaluation files found in: {args.general_folder}")
        sys.exit(1)

    print(f"Traces found: {traces}")
    print(f"Questions: {NUM_QUESTIONS} ({list(LAYER_BOUNDARIES.keys())})")

    folders = {"general": args.general_folder, "filtered": args.filtered_folder}
    if args.wide_folder:
        folders["wide"] = args.wide_folder

    labels_by_view = {
        view: {t: labels_for_trace(folder, t, args.prefix) for t in traces}
        for view, folder in folders.items()
    }

    generate_dotplot(
        traces=traces,
        labels_by_view=labels_by_view,
        method_label=args.method,
        output_path=args.output,
    )