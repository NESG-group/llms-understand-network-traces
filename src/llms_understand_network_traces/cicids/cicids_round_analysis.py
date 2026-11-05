#!/usr/bin/env python3
"""
cicids_round_analysis.py
================================================================================
Resumen de una ronda de CICIDS a partir de los JSON del juez (solo lectura).

Imprime, para los cuatro modelos:
  A. Totales de C/P/I por vista, con todos los niveles y sin el 125 % (en ese nivel
     la vista general no cabe en el contexto y el modelo ve solo el final).
  B. Desglose por tipo de pregunta, sin el 125 %:
       - capa ausente:           el CSV filtered de esa capa no tiene filas (acertar = decir None)
       - GT vacío, capa presente: la capa tiene datos pero ningún elemento cumple la condición
       - con contenido:           el ground truth lista elementos
  C. Respuestas cortadas por el tope de salida (bucles) y desempates del juez.

Ojo con la lectura: los niveles son prefijos de la misma ventana, así que las 19
preguntas repetidas en 3 o 4 niveles NO son muestras independientes. Y los modelos
de una familia comparten datos, pero llama y qwen no (distinto contexto y tokenizer,
distinto número de paquetes por nivel).

Uso (desde la raíz del proyecto):
  python3 cicids_round_analysis.py                       # results/models, run1
  python3 cicids_round_analysis.py --run run2
  python3 cicids_round_analysis.py --models-dir results/models --run run1
================================================================================
"""
import argparse
import glob
import json
import re
from collections import Counter

MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]


def lines(s):
    return [l.strip() for l in str(s).splitlines() if l.strip()]


def gt_empty(gt):
    ls = lines(gt)
    return bool(ls) and (ls[-1].lower().endswith("none") or ls[0].lower().startswith("no "))


def load(models_dir, run):
    data = {}
    for model in MODELS:
        for mode in ("general", "filtered"):
            pat = f"{models_dir}/{model}/{run}/comparison/judge/{mode}/judge_Monday*_answers.json"
            for f in glob.glob(pat):
                lvl = int(re.search(r"_L(\d+)_", f).group(1))
                qs = json.load(open(f, encoding="utf-8"))["questions"]
                data[(model, lvl, mode)] = [
                    dict(label=v["final_label"], tie=not v.get("consistent", True),
                         cut=bool(v.get("output_truncated")), gt_empty=gt_empty(v["gt_answer"]),
                         csv_empty=bool(v.get("csv_empty")))
                    for v in qs.values()]
    return data


def cpi(counter):
    n = counter["C"] + counter["P"] + counter["I"]
    pc = f"{counter['C'] / n:6.1%}" if n else "   n/a"
    return f"C{counter['C']:>3} P{counter['P']:>3} I{counter['I']:>3}  ({pc} C, n={n})"


def totals(data, levels):
    for model in MODELS:
        for mode in ("general", "filtered"):
            c = Counter()
            for (m, lvl, md), rows in data.items():
                if m == model and md == mode and lvl in levels:
                    c.update(r["label"] for r in rows)
            print(f"  {model:<13}{mode:<9}{cpi(c)}")


def categorias(data, levels):
    for model in MODELS:
        cat = {}
        for lvl in levels:
            g, f = data.get((model, lvl, "general")), data.get((model, lvl, "filtered"))
            if not g or not f:
                continue
            for rg, rf in zip(g, f):
                if rf["csv_empty"]:
                    k = "capa ausente (CSV filtered vacío)"
                elif rf["gt_empty"]:
                    k = "GT vacío, capa presente"
                else:
                    k = "con contenido"
                cat.setdefault(k, {"general": Counter(), "filtered": Counter()})
                cat[k]["general"][rg["label"]] += 1
                cat[k]["filtered"][rf["label"]] += 1
        print(f"  {model}")
        for k in ("capa ausente (CSV filtered vacío)", "GT vacío, capa presente", "con contenido"):
            if k in cat:
                print(f"    {k:<34} general {cpi(cat[k]['general'])}")
                print(f"    {'':<34} filtered {cpi(cat[k]['filtered'])}")


def bucles_y_desempates(data):
    for model in MODELS:
        tot = cut = tie = 0
        for (m, lvl, md), rows in data.items():
            if m == model:
                tot += len(rows)
                cut += sum(r["cut"] for r in rows)
                tie += sum(r["tie"] for r in rows)
        if tot:
            print(f"  {model:<13}evaluaciones {tot:>3}  cortadas por el tope {cut:>3} ({cut / tot:5.1%})"
                  f"  desempates {tie:>3} ({tie / tot:5.1%})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", default="results/models")
    ap.add_argument("--run", default="run1")
    a = ap.parse_args()
    data = load(a.models_dir, a.run)
    if not data:
        raise SystemExit(f"No hay juicios en {a.models_dir}/<modelo>/{a.run}/comparison/judge/... ¿estás en la raíz del proyecto?")
    print(f"RONDA {a.run}\n\nA1. Totales, todos los niveles")
    totals(data, (25, 50, 75, 100))
    print("\nA2. Totales, sin el nivel del 125 % (L100)")
    totals(data, (25, 50, 75))
    print("\nB. Por tipo de pregunta, sin L100")
    categorias(data, (25, 50, 75))
    print("\nC. Bucles y desempates (todos los niveles y vistas)")
    bucles_y_desempates(data)


if __name__ == "__main__":
    main()
