"""
dotplot_model_cicids.py
================================================================================
Versión de dotplot_model.py para CICIDS. Mismo dibujo (puntos rellenos = vista
general, anillos = vista filtrada, columnas C/P/I y filas P1..P19), pero cada
BLOQUE es un nivel de contexto (50, 75, 100 y 125 % del presupuesto de datos) en vez
de una traza, y la etiqueta de cada pregunta es la MODA de las rondas disponibles
(por defecto, las que haya en results/models/<modelo>/run*).

Diferencia con dotplot_model.py: allí la moda agrega las rondas de una misma traza;
en CICIDS cada ronda es otra ventana del pcap (otros paquetes), así que el mismo nivel
se vota entre ventanas distintas. Por eso la etiqueta de cada bloque es "la que más
veces sale para esa pregunta, vista y nivel entre las rondas", no la de una traza.

Empates (con 5 rondas son frecuentes: 2 C, 2 I, 1 P): por defecto se resuelven como en
dotplot_model.py, a favor de C > P > I (optimista). Con --tie-break IPC se resuelven a
favor de la peor etiqueta (conservador). El script imprime cuántos empates hay.

Ojo con la lectura:
  - Una pregunta con capa vacía en una ventana es fácil (la respuesta correcta es
    "None"); la moda mezcla ventanas con y sin esa capa.
  - Los niveles son prefijos de la misma ventana, no muestras independientes.
  - El 125 % (L100) se recorta en el servidor (Ollama 0.33.3): no es "más contexto".
  - Las etiquetas E (error del juez) y N (sin respuesta) no se dibujan ni votan.

Uso (desde la raíz del proyecto):
  python3 dotplot_model_cicids.py                              # todos los modelos y rondas
  python3 dotplot_model_cicids.py --runs 1 2 3 4 5 --tie-break IPC
  python3 dotplot_model_cicids.py --models llama3.1:70b qwen2.5:72b \
          --output-dir output_graphs/cicids_mode
================================================================================
"""
import argparse
import glob
import importlib
import json
import os
import re
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, os.getcwd())

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


def norm(q):
    return re.sub(r"\s+", " ", q.strip())


def runs_found(models_dir):
    return sorted({int(m.group(1)) for p in glob.glob(f"{models_dir}/*/run*")
                   for m in [re.search(r"run(\d+)$", p)] if m})


def labels_of(filepath):
    """Etiquetas C/P/I/None en el orden de ALL_QUESTIONS, o None si no se puede leer."""
    try:
        with open(filepath, encoding="utf-8") as fh:
            d = json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        print(f"    [WARN] no se puede leer {filepath}: {e}")
        return None
    lm = {norm(q): (v.get("final_label") or v.get("label")) for q, v in d.get("questions", {}).items()}
    absent = sum(1 for q in ALL_QUESTIONS if q not in lm)
    if absent:
        print(f"    [WARN] {filepath}: {absent}/{NUM_QUESTIONS} preguntas no están en el fichero (¿--constants equivocado?)")
    return [lm.get(q) if lm.get(q) in VALID else None for q in ALL_QUESTIONS]


def vote(labels_per_run, prio):
    """Moda por pregunta. Devuelve (etiquetas, nº de empates)."""
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


def build(models_dir, model, runs, prio):
    """Devuelve bloques (orden de nivel), general{bloque: etiquetas}, filtered{...}, resumen de empates."""
    gen, fil, blocks, ties, nruns = {}, {}, [], {}, {}
    for lvl, pct in PCT.items():
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
        name = f"{pct} % (L{lvl})\n{rng}\n{len(per_mode['general'])} rondas"
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
        Line2D([0], [0], marker="o", color="w", markerfacecolor="gray", markersize=8, label="General (color = context level)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="none", markeredgecolor="black",
               markeredgewidth=1.5, markersize=12, label="Filtered (layer-specific CSV)")],
        loc="lower center", bbox_to_anchor=(0.5, 1.12), ncol=2, fontsize=10, frameon=True,
        title=f"Evaluation method: {method_label}", title_fontsize=10)
    plt.subplots_adjust(left=0.18, bottom=0.22, right=0.97, top=0.82)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  [OK] {output_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", default="results/models")
    ap.add_argument("--output-dir", default="output_graphs/cicids_mode")
    ap.add_argument("--runs", type=int, nargs="*", default=None)
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--constants", default="utils.constants")
    ap.add_argument("--tie-break", choices=("CPI", "IPC"), default="CPI",
                    help="CPI (por defecto, como dotplot_model.py): ante un empate gana la mejor etiqueta; "
                         "IPC: gana la peor")
    a = ap.parse_args()

    set_layout(a.constants)
    runs = a.runs or runs_found(a.models_dir)
    prio = PRIORITY[a.tie_break]
    print(f"Rondas: {runs} | preguntas: {NUM_QUESTIONS} ({a.constants}) | desempate: {a.tie_break}\n")

    for model in a.models:
        print("=" * 60 + f"\n{model}\n" + "=" * 60)
        blocks, gen, fil, ties = build(a.models_dir, model, runs, prio)
        if not blocks:
            print("  [SKIP] sin juicios\n")
            continue
        for (mode, lvl), t in sorted(ties.items()):
            print(f"  empates en la moda — {mode:<8} L{lvl:<3}: {t}/{NUM_QUESTIONS}")
        slug = re.sub(r"[^\w\-.]", "_", model)
        generate_dotplot(blocks, gen, fil, f"LLM-Judge | majority vote over runs {runs} | {model} | tie-break {a.tie_break}",
                         os.path.join(a.output_dir, slug, f"dotplot_cicids_{slug}.png"))
        print()


if __name__ == "__main__":
    main()