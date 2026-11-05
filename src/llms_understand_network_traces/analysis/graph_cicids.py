#!/usr/bin/env python3
"""
dotplot_cicids_rounds.py
================================================================================
Consistencia por pregunta entre las rondas de CICIDS (solo lectura de los JSON del juez).

Por qué no se usa dotplot_model.py con CICIDS: ese script agrega por moda las rondas de
una MISMA traza. En CICIDS cada ronda es una ventana distinta (otros paquetes), así que
cada traza existe en una sola ronda: la moda no agrega nada, salen 5 x 4 = 20 bloques por
modelo y avisos de ficheros inexistentes.

Qué dibuja (un PNG por modelo): dos paneles, uno para C y otro para I. Filas = las 19
preguntas; columnas = los cuatro niveles (50, 75, 100 y 125 % del presupuesto de datos) y,
dentro de cada nivel, la vista general (G) y la filtrada (F). Cada celda muestra k/n:
en cuántas de las n rondas con etiqueta válida esa pregunta recibió C (panel izquierdo)
o I (panel derecho). Las celdas grises no tienen ninguna etiqueta válida (E, N o ausente).

También imprime las preguntas que nunca reciben C en ninguna vista, nivel ni ronda
(candidatas a patrón de error sistemático).

Ojo con la lectura:
  - Cada ronda es otra ventana: una pregunta puede ser fácil en una ronda porque la capa
    está vacía (la respuesta correcta es "None"). Mira también el desglose por tipo de
    pregunta de cicids_round_analysis.py.
  - Los niveles son prefijos de la misma ventana: no son muestras independientes.
  - El 125 % (L100) se recorta en el servidor (Ollama 0.33.3): no es "más contexto".

Uso (desde la raíz del proyecto):
  python3 dotplot_cicids_rounds.py                           # todas las rondas que haya
  python3 dotplot_cicids_rounds.py --runs 1 2 3 4 5
  python3 dotplot_cicids_rounds.py --models llama3.1:70b qwen2.5:72b --output-dir output_graphs/cicids_rounds
================================================================================
"""
import argparse
import glob
import importlib
import json
import os
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, os.getcwd())

MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]
MODES = ("general", "filtered")
PCT = {25: 50, 50: 75, 75: 100, 100: 125}
VALID = ("C", "P", "I")


def norm(q):
    return re.sub(r"\s+", " ", q.strip())


def load_layout(module_name):
    mod = importlib.import_module(module_name)
    qs = [norm(q) for q in mod.ALL_QUESTIONS]
    return qs, len(mod.ARP_QUESTIONS), len(mod.IP_QUESTIONS)


def runs_found(models_dir):
    return sorted({int(m.group(1)) for p in glob.glob(f"{models_dir}/*/run*")
                   for m in [re.search(r"run(\d+)$", p)] if m})


def collect(models_dir, model, qs, runs):
    """data[(vista, nivel)][indice_pregunta] = [etiquetas C/P/I de cada ronda]."""
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
                    print(f"  [WARN] no se puede leer {f}: {e}")
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
    ap.add_argument("--constants", default="utils.constants")
    a = ap.parse_args()

    qs, n_arp, n_ip = load_layout(a.constants)
    runs = a.runs or runs_found(a.models_dir)
    print(f"Rondas: {runs}  |  preguntas: {len(qs)} ({a.constants})\n")

    for model in a.models:
        data, used, absent = collect(a.models_dir, model, qs, runs)
        if not data:
            print(f"[SKIP] {model}: no hay juicios en las rondas {runs}")
            continue
        if absent:
            print(f"[WARN] {model}: {absent} preguntas de {a.constants} no están en algún fichero (¿--constants equivocado?)")
        fig, axes = plt.subplots(1, 2, figsize=(15, len(qs) * 0.42 + 2.5))
        draw(axes[0], data, qs, n_arp, n_ip, "C", "#2ca02c")
        draw(axes[1], data, qs, n_arp, n_ip, "I", "#d62728")
        axes[0].set_title("Rondas con etiqueta C (k/n)", fontsize=10)
        axes[1].set_title("Rondas con etiqueta I (k/n)", fontsize=10)
        fig.suptitle(f"{model} | rondas {used} | G = vista general, F = vista filtrada | niveles = % del presupuesto de datos",
                     fontsize=10)
        slug = re.sub(r"[^\w\-.]", "_", model)
        out = os.path.join(a.output_dir, slug, f"consistencia_{slug}.png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.tight_layout(rect=(0, 0.03, 1, 0.96))
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"[OK] {out}")
        never = [f"P{i + 1}" for i in range(len(qs))
                 if all("C" not in data.get(k, {}).get(i, []) for k in data) and any(i in data[k] for k in data)]
        print(f"     preguntas sin ninguna C (todas las vistas, niveles y rondas): {never if never else 'ninguna'}\n")


if __name__ == "__main__":
    main()