"""
dotplot_cicids.py
================================================================================
CIC-IDS2017 version of dotplot_model.py. Same drawing (filled dots = general view,
rings = filtered view, columns C/P/I and rows P1..P19), but every BLOCK is a context
level (50, 75, 100 and 125 % of the data budget) instead of a trace, and the label of
each question is the MODE over the available runs (by default, those found in
results/cicids/<model>/run*).

Difference with dotplot_model.py: there the mode aggregates the runs of the same trace;
in CIC-IDS2017 every run is another window of the pcap (other packets), so the same level
is voted across different windows. Hence the label of each block is "the one that appears
most often for that question, view and level across the runs", not that of one trace.

Ties (frequent with 5 runs: 2 C, 2 I, 1 P): by default they are resolved as in
dotplot_model.py, in favour of C > P > I (optimistic). With --tie-break IPC they are
resolved in favour of the worst label (conservative). The script prints how many ties
there are.

Reading caveats:
  - A question with an empty layer in a window is easy (the right answer is "None"); the
    mode mixes windows with and without that layer.
  - Levels are prefixes of the same window, not independent samples.
  - The 125 % level (L100) is trimmed by the server (Ollama 0.33.3): it is not "more context".
  - Labels E (judge error) and N (no answer) are neither drawn nor voted.

Usage (from the repository root):
  uv run python -m llms_understand_network_traces.analysis.dotplot_cicids
  uv run python -m llms_understand_network_traces.analysis.dotplot_cicids --levels 25 50 75   # figure of the paper
  uv run python -m llms_understand_network_traces.analysis.dotplot_cicids --runs 1 2 3 4 5 --tie-break IPC
  uv run python -m llms_understand_network_traces.analysis.dotplot_cicids \
          --models llama3.1:70b qwen2.5:72b --output-dir results/reproduced/figures/cicids_mode
================================================================================
"""
import argparse
import glob
import importlib
import json
import os
import re
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from llms_understand_network_traces.utils.text import norm


MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]
PCT = {25: 50, 50: 75, 75: 100, 100: 125}
VALID = ("C", "P", "I")
PRIORITY = {"CPI": {"C": 0, "P": 1, "I": 2}, "IPC": {"I": 0, "P": 1, "C": 2}}

ALL_QUESTIONS, NUM_QUESTIONS, LAYER_BOUNDARIES, LAYER_SEPARATORS = [], 0, {}, []


def set_layout(module_name):
    global ALL_QUESTIONS, NUM_QUESTIONS, LAYER_BOUNDARIES, LAYER_SEPARATORS
    mod = importlib.import_module(module_name)
    ALL_QUESTIONS = [norm(q) for q in mod.ALL_QUESTIONS]
    NUM_QUESTIONS = len(ALL_QUESTIONS)
    n_arp, n_ip = len(mod.ARP_QUESTIONS), len(mod.IP_QUESTIONS)
    LAYER_BOUNDARIES = {"L2 - ARP": (0, n_arp), "L3 - IP": (n_arp, n_arp + n_ip),
                        "L4 - TCP/UDP": (n_arp + n_ip, NUM_QUESTIONS)}
    LAYER_SEPARATORS = [n_arp, n_arp + n_ip]


def runs_found(models_dir):
    return sorted({int(m.group(1)) for p in glob.glob(f"{models_dir}/*/run*")
                   for m in [re.search(r"run(\d+)$", p)] if m})


def labels_of(filepath):
    """C/P/I/None labels in the order of ALL_QUESTIONS, or None if the file cannot be read."""
    try:
        with open(filepath, encoding="utf-8") as fh:
            d = json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        print(f"    [WARN] cannot read {filepath}: {e}")
        return None
    lm = {norm(q): (v.get("final_label") or v.get("label")) for q, v in d.get("questions", {}).items()}
    absent = sum(1 for q in ALL_QUESTIONS if q not in lm)
    if absent:
        print(f"    [WARN] {filepath}: {absent}/{NUM_QUESTIONS} questions are not in the file (wrong --constants?)")
    return [lm.get(q) if lm.get(q) in VALID else None for q in ALL_QUESTIONS]


def vote(labels_per_run, prio):
    """Mode per question. Returns (labels, number of ties)."""
    out, ties = [], 0
    for i in range(NUM_QUESTIONS):
        votes = [r[i] for r in labels_per_run if r[i] is not None]
        if not votes:
            out.append(None)
            continue
        cnt = Counter(votes)
        top = max(cnt.values())
        cands = [l for l, c in cnt.items() if c == top]
        ties += len(cands) > 1
        out.append(min(cands, key=lambda l: prio[l]))
    return out, ties


def build(models_dir, model, runs, prio, levels=None):
    """Return blocks (level order), general{block: labels}, filtered{...}, tie summary."""
    gen, fil, blocks, ties, nruns = {}, {}, [], {}, {}
    for lvl, pct in PCT.items():
        if levels and lvl not in levels:
            continue
        per_mode, pk = {}, set()
        for mode in ("general", "filtered"):
            lst = []
            for r in runs:
                for f in sorted(glob.glob(f"{models_dir}/{model}/run{r}/comparison/judge/{mode}/judge_Monday*_L{lvl}_*pkts_answers.json")):
                    m = re.search(r"_L\d+_(\d+)pkts", f)
                    if m:
                        pk.add(int(m.group(1)))
                    lab = labels_of(f)
                    if lab is not None:
                        lst.append(lab)
            per_mode[mode] = lst
        if not per_mode["general"] and not per_mode["filtered"]:
            continue
        rng = f"{min(pk):,}–{max(pk):,} pkts" if pk else ""
        name = f"{pct} % (L{lvl})\n{rng}\n{len(per_mode['general'])} runs"
        blocks.append(name)
        for mode, store in (("general", gen), ("filtered", fil)):
            if per_mode[mode]:
                store[name], t = vote(per_mode[mode], prio)
                ties[(mode, lvl)] = t
        nruns[lvl] = len(per_mode["general"])
    return blocks, gen, fil, ties


def generate_dotplot(blocks, general_labels, filtered_labels, method_label, output_path):
    col_cats = ["C", "P", "I"]
    nb = len(blocks)
    col_colors = {"C": "#2ca02c", "P": "#ff7f0e", "I": "#d62728"}
    block_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    fig, ax = plt.subplots(figsize=(max(9, nb * 2.5), NUM_QUESTIONS * 0.55 + 4))
    for i in range(NUM_QUESTIONS + 1):
        ax.axhline(i - 0.5, color="#eeeeee", zorder=1)
    for j in range(nb * 3 + 1):
        ax.axvline(j - 0.5, color="#eeeeee", zorder=1)

    for q in range(NUM_QUESTIONS):
        for b, name in enumerate(blocks):
            labs = general_labels.get(name, [])
            cat = labs[q] if q < len(labs) else None
            for j, c in enumerate(col_cats):
                if cat == c:
                    ax.scatter(b * 3 + j, q, s=60, color=block_colors[b % len(block_colors)], zorder=4)
    for q in range(NUM_QUESTIONS):
        for b, name in enumerate(blocks):
            labs = filtered_labels.get(name, [])
            cat = labs[q] if q < len(labs) else None
            for j, c in enumerate(col_cats):
                if cat == c:
                    ax.scatter(b * 3 + j, q, s=180, facecolors="none", edgecolors="black", linewidths=1.5, zorder=5)

    ax.set_xlim(-0.5, nb * 3 - 0.5)
    ax.set_ylim(NUM_QUESTIONS - 0.5, -0.5)
    ax.set_xticks([i * 3 + 1 for i in range(nb)])
    ax.set_xticklabels(blocks, fontsize=9)
    ax.set_yticks(range(NUM_QUESTIONS))
    ax.set_yticklabels([f"P{i + 1}" for i in range(NUM_QUESTIONS)], fontsize=9)
    for b in range(nb):
        for j, cat in enumerate(col_cats):
            ax.text(b * 3 + j, -1.2, cat, ha="center", va="center", fontsize=7, fontweight="bold", color=col_colors[cat])
    for i in range(1, nb):
        ax.axvline(x=i * 3 - 0.5, color="black", linestyle=(0, (2, 4)), linewidth=1)
    for sep in LAYER_SEPARATORS:
        ax.axhline(y=sep - 0.5, color="black", linestyle=(0, (2, 4)), linewidth=1)
    for name, (s, e) in LAYER_BOUNDARIES.items():
        ax.text(-1.5, (s + e - 1) / 2, name, rotation=90, va="center", ha="center", fontsize=8, fontweight="bold")
    for sp in ax.spines.values():
        sp.set_visible(False)

    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="w", markerfacecolor="gray", markersize=8, label="Default (color = input size)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="none", markeredgecolor="black",
               markeredgewidth=1.5, markersize=12, label="Filtered")],
        loc="lower center", bbox_to_anchor=(0.5, 1.12), ncol=2, fontsize=10, frameon=True,
        title=f"Evaluation method: {method_label}", title_fontsize=10)
    plt.subplots_adjust(left=0.18, bottom=0.22, right=0.97, top=0.82)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {output_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", default="results/cicids")
    ap.add_argument("--output-dir", default="results/reproduced/figures/cicids_mode")
    ap.add_argument("--runs", type=int, nargs="*", default=None)
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--constants", default="llms_understand_network_traces.utils.constants")
    ap.add_argument("--levels", type=int, nargs="*", choices=sorted(PCT), default=None,
                    help="Levels to draw (default: all). The figure of the paper uses 25 50 75, "
                         "i.e. 50, 75 and 100 %% of the budget, without the trimmed 125 %% level")
    ap.add_argument("--tie-break", choices=("CPI", "IPC"), default="CPI",
                    help="CPI (default, as in dotplot_model.py): on a tie the best label wins; "
                         "IPC: the worst wins")
    a = ap.parse_args()

    set_layout(a.constants)
    runs = a.runs or runs_found(a.models_dir)
    prio = PRIORITY[a.tie_break]
    print(f"Runs: {runs} | questions: {NUM_QUESTIONS} ({a.constants}) | tie-break: {a.tie_break}\n")

    for model in a.models:
        print("=" * 60 + f"\n{model}\n" + "=" * 60)
        blocks, gen, fil, ties = build(a.models_dir, model, runs, prio, a.levels)
        if not blocks:
            print("  [SKIP] no judgements\n")
            continue
        for (mode, lvl), t in sorted(ties.items()):
            print(f"  ties in the mode — {mode:<8} L{lvl:<3}: {t}/{NUM_QUESTIONS}")
        slug = re.sub(r"[^\w\-.]", "_", model)
        tie_note = "" if a.tie_break == "CPI" else f" | tie-break {a.tie_break}"
        generate_dotplot(blocks, gen, fil, f"LLM-Judge | modal label over runs {runs} | {model}{tie_note}",
                         os.path.join(a.output_dir, slug, f"dotplot_cicids_{slug}.png"))
        print()


if __name__ == "__main__":
    main()