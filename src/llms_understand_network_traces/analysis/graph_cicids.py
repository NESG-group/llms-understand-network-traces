"""
graph_cicids.py
================================================================================
Per-question consistency across the CIC-IDS2017 runs (read-only over the judge JSON files).

Why dotplot_model.py is not used with CIC-IDS2017: that script aggregates by mode the runs
of the SAME trace. In CIC-IDS2017 every run is a different window (other packets), so every
trace exists in a single run: the mode aggregates nothing, 5 x 4 = 20 blocks per model
appear and warnings about missing files are printed.

What it draws (one PNG per model): two panels, one for C and one for I. Rows = the 19
questions; columns = the four levels (50, 75, 100 and 125 % of the data budget) and, inside
each level, the general (G) and the filtered (F) view. Each cell shows k/n: in how many of
the n runs with a valid label that question received C (left panel) or I (right panel).
Grey cells have no valid label (E, N or absent).

It also prints the questions that never receive C in any view, level or run (candidates for
a systematic error pattern).

Reading caveats:
  - Every run is another window: a question can be easy in one run because the layer is
    empty (the right answer is "None"). Also look at the breakdown by question type of
    cicids_round_analysis.py.
  - Levels are prefixes of the same window: they are not independent samples.
  - The 125 % level (L100) is trimmed by the server (Ollama 0.33.3): it is not "more context".

Usage (from the repository root):
  uv run python -m llms_understand_network_traces.analysis.graph_cicids
  uv run python -m llms_understand_network_traces.analysis.graph_cicids --runs 1 2 3 4 5
  uv run python -m llms_understand_network_traces.analysis.graph_cicids \
          --models llama3.1:70b qwen2.5:72b --output-dir output_graphs/cicids_rounds
================================================================================
"""
import argparse
import glob
import importlib
import json
import os
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from llms_understand_network_traces.utils.text import norm


MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]
MODES = ("general", "filtered")
PCT = {25: 50, 50: 75, 75: 100, 100: 125}
VALID = ("C", "P", "I")


def load_layout(module_name):
    mod = importlib.import_module(module_name)
    qs = [norm(q) for q in mod.ALL_QUESTIONS]
    return qs, len(mod.ARP_QUESTIONS), len(mod.IP_QUESTIONS)


def runs_found(models_dir):
    return sorted({int(m.group(1)) for p in glob.glob(f"{models_dir}/*/run*")
                   for m in [re.search(r"run(\d+)$", p)] if m})


def collect(models_dir, model, qs, runs):
    """data[(view, level)][question_index] = [C/P/I labels of each run]."""
    data = defaultdict(lambda: defaultdict(list))
    used, absent = set(), 0
    for run in runs:
        for mode in MODES:
            for f in sorted(glob.glob(f"{models_dir}/{model}/run{run}/comparison/judge/{mode}/judge_Monday*_answers.json")):
                m = re.search(r"_L(\d+)_", f)
                if not m or int(m.group(1)) not in PCT:
                    continue
                try:
                    with open(f, encoding="utf-8") as fh:
                        d = json.load(fh)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"  [WARN] cannot read {f}: {e}")
                    continue
                lm = {norm(q): v.get("final_label") for q, v in d.get("questions", {}).items()}
                for i, q in enumerate(qs):
                    if q not in lm:
                        absent += 1
                    elif lm[q] in VALID:
                        data[(mode, int(m.group(1)))][i].append(lm[q])
                used.add(run)
    return data, sorted(used), absent


def draw(ax, data, qs, n_arp, n_ip, label, color):
    cols = [(lvl, mode) for lvl in PCT for mode in MODES]
    cmap = LinearSegmentedColormap.from_list("c", ["#ffffff", color])
    cmap.set_bad("#e6e6e6")
    M = np.full((len(qs), len(cols)), np.nan)
    for j, (lvl, mode) in enumerate(cols):
        for i in range(len(qs)):
            labs = data.get((mode, lvl), {}).get(i, [])
            if labs:
                M[i, j] = sum(1 for x in labs if x == label) / len(labs)
    ax.imshow(np.ma.masked_invalid(M), cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for j, (lvl, mode) in enumerate(cols):
        for i in range(len(qs)):
            labs = data.get((mode, lvl), {}).get(i, [])
            if labs:
                k = sum(1 for x in labs if x == label)
                ax.text(j, i, f"{k}/{len(labs)}", ha="center", va="center", fontsize=7,
                        color="white" if M[i, j] > 0.6 else "black")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([("G" if m == "general" else "F") for _, m in cols], fontsize=8)
    for g, lvl in enumerate(PCT):
        ax.text(2 * g + 0.5, len(qs) + 0.9, f"{PCT[lvl]} %", ha="center", va="center", fontsize=9)
        if g:
            ax.axvline(2 * g - 0.5, color="black", linestyle=(0, (2, 4)), linewidth=1)
    ax.set_yticks(range(len(qs)))
    ax.set_yticklabels([f"P{i + 1}" for i in range(len(qs))], fontsize=8)
    for sep in (n_arp, n_arp + n_ip):
        ax.axhline(sep - 0.5, color="black", linestyle=(0, (2, 4)), linewidth=1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", default="results/models")
    ap.add_argument("--output-dir", default="output_graphs/cicids_rounds")
    ap.add_argument("--runs", type=int, nargs="*", default=None)
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--constants", default="llms_understand_network_traces.utils.constants")
    a = ap.parse_args()

    qs, n_arp, n_ip = load_layout(a.constants)
    runs = a.runs or runs_found(a.models_dir)
    print(f"Runs: {runs}  |  questions: {len(qs)} ({a.constants})\n")

    for model in a.models:
        data, used, absent = collect(a.models_dir, model, qs, runs)
        if not data:
            print(f"[SKIP] {model}: no judgements in runs {runs}")
            continue
        if absent:
            print(f"[WARN] {model}: {absent} questions of {a.constants} are missing in some file (wrong --constants?)")
        fig, axes = plt.subplots(1, 2, figsize=(15, len(qs) * 0.42 + 2.5))
        draw(axes[0], data, qs, n_arp, n_ip, "C", "#2ca02c")
        draw(axes[1], data, qs, n_arp, n_ip, "I", "#d62728")
        axes[0].set_title("Runs labelled C (k/n)", fontsize=10)
        axes[1].set_title("Runs labelled I (k/n)", fontsize=10)
        fig.suptitle(f"{model} | runs {used} | G = general view, F = filtered view | levels = % of the data budget",
                     fontsize=10)
        slug = re.sub(r"[^\w\-.]", "_", model)
        out = os.path.join(a.output_dir, slug, f"consistency_{slug}.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.tight_layout(rect=(0, 0.03, 1, 0.96))
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"[OK] {out}")
        never = [f"P{i + 1}" for i in range(len(qs))
                 if all("C" not in data.get(k, {}).get(i, []) for k in data) and any(i in data[k] for k in data)]
        print(f"     questions never labelled C (all views, levels and runs): {never if never else 'none'}\n")


if __name__ == "__main__":
    main()