#!/usr/bin/env python3
"""
cicids_aggregate_rounds.py
================================================================================
Resumen de varias rondas de CICIDS a la vez (solo lectura): % de C e I por modelo,
vista y nivel, con la media y la desviación típica entre rondas, y los tokens de
entrada y los prompts truncados de cada ronda.

Lee, para cada modelo y ronda:
  results/models/<modelo>/run<N>/comparison/judge/<vista>/judge_Monday*_answers.json
      (campo "summary": C, P, I, judge_errors, prompt_truncated_suspected,
       output_truncated, inconsistent_swaps)
  results/models/<modelo>/run<N>/llm_answers/<vista>/Monday*_answers.json
      (campo "Questions": tokens_input, data_tokens, truncation_suspected, csv_source)

Bloques:
  A. Por modelo y vista, niveles L25-L75 juntos (sin L100): % de C e I por ronda y
     media ± sd entre rondas.
  B. Por modelo, vista y nivel: % de C por ronda y media ± sd.
  C. Tokens: tokens de entrada por ronda y nivel (vista general: los de la primera
     pregunta; vista filtered: el máximo de cualquier capa) y cuántas preguntas
     tuvieron el prompt truncado.

Ojo con la lectura:
  - Los niveles son prefijos de la misma ventana, así que sus 19 preguntas no son
    muestras independientes. La sd entre rondas es descriptiva: no la conviertas en
    un intervalo de confianza con 2 o 3 rondas.
  - Cada ronda usa otra ventana del pcap (otros paquetes), así que las diferencias
    entre rondas mezclan azar del modelo (a temperatura 0, casi ninguno) y tráfico
    distinto.
  - El % de C absoluto depende de cuántas preguntas tienen la capa vacía en la
    ventana. Para comparar rondas, mira también los bloques "con contenido" de
    cicids_round_analysis.py.

Uso (desde la raíz del proyecto):
  python3 cicids_aggregate_rounds.py                       # todas las rondas que haya
  python3 cicids_aggregate_rounds.py --runs 1 2 3
  python3 cicids_aggregate_rounds.py --csv results/summary/cicids_rounds_long.csv
================================================================================
"""
import argparse
import csv
import glob
import json
import re
import statistics

MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]
MODES = ("general", "filtered")
PCT = {25: 50, 50: 75, 75: 100, 100: 125}


def runs_found(models_dir):
    rs = set()
    for p in glob.glob(f"{models_dir}/*/run*"):
        m = re.search(r"run(\d+)$", p)
        if m:
            rs.add(int(m.group(1)))
    return sorted(rs)


def collect(models_dir, runs, models):
    """J[(modelo, ronda, vista, nivel)] = dict(pk, C, P, I, ...);  T[...] = dict(tok, trunc, layer)."""
    J, T = {}, {}
    for M in models:
        for R in runs:
            for mode in MODES:
                for f in glob.glob(f"{models_dir}/{M}/run{R}/comparison/judge/{mode}/judge_Monday*_answers.json"):
                    m = re.search(r"_L(\d+)_(\d+)pkts", f)
                    if not m:
                        continue
                    s = json.load(open(f, encoding="utf-8")).get("summary", {})
                    J[(M, R, mode, int(m.group(1)))] = dict(
                        pk=int(m.group(2)), C=s.get("C", 0), P=s.get("P", 0), I=s.get("I", 0),
                        err=s.get("judge_errors", 0), ptrunc=s.get("prompt_truncated_suspected", 0),
                        otrunc=s.get("output_truncated", 0), ties=s.get("inconsistent_swaps", 0))
                for f in glob.glob(f"{models_dir}/{M}/run{R}/llm_answers/{mode}/Monday*_answers.json"):
                    m = re.search(r"_L(\d+)_(\d+)pkts", f)
                    if not m:
                        continue
                    qs = list(json.load(open(f, encoding="utf-8")).get("Questions", {}).values())
                    if not qs:
                        continue
                    if mode == "general":
                        tok, layer = qs[0].get("tokens_input", 0), "general"
                    else:
                        best = max(qs, key=lambda q: q.get("tokens_input", 0))
                        tok, layer = best.get("tokens_input", 0), best.get("csv_source", "?")
                    T[(M, R, mode, int(m.group(1)))] = dict(
                        tok=tok, layer=layer, trunc=sum(1 for q in qs if q.get("truncation_suspected")))
    return J, T


def pct(num, den):
    return 100.0 * num / den if den else None


def ms(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return "   n/a"
    if len(v) == 1:
        return f"{v[0]:5.1f}      "
    return f"{statistics.mean(v):5.1f} ± {statistics.stdev(v):4.1f}"


def fmt(x):
    return "   - " if x is None else f"{x:5.1f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", default="results/models")
    ap.add_argument("--runs", type=int, nargs="*", default=None, help="rondas a incluir (por defecto, todas las que haya)")
    ap.add_argument("--csv", default=None, help="guarda además una tabla larga (una fila por modelo, ronda, vista y nivel)")
    a = ap.parse_args()

    runs = a.runs or runs_found(a.models_dir)
    J, T = collect(a.models_dir, runs, MODELS)
    if not J:
        raise SystemExit(f"No hay juicios en {a.models_dir} para las rondas {runs}.")
    print(f"Rondas: {runs}\n")

    print("A. %C y %I por modelo y vista, niveles L25-L75 (sin L100), por ronda y media ± sd entre rondas")
    head = "".join(f"{'r' + str(r):>7}" for r in runs)
    for lab in ("C", "I"):
        print(f"\n  %{lab}{'':<22}{head}   media ± sd")
        for M in MODELS:
            for mode in MODES:
                vals = []
                for R in runs:
                    ks = [(M, R, mode, l) for l in (25, 50, 75) if (M, R, mode, l) in J]
                    n = sum(J[k]["C"] + J[k]["P"] + J[k]["I"] for k in ks)
                    vals.append(pct(sum(J[k][lab] for k in ks), n) if len(ks) == 3 else None)
                if any(v is not None for v in vals):
                    print(f"  {M + ' ' + mode:<24}" + "".join(f"{fmt(v):>7}" for v in vals) + f"   {ms(vals)}")

    print("\nB. %C por modelo, vista y nivel, por ronda y media ± sd entre rondas")
    print(f"  {'':<24}{'nivel':>6}{head}   media ± sd")
    for M in MODELS:
        for mode in MODES:
            for lvl in PCT:
                vals = []
                for R in runs:
                    j = J.get((M, R, mode, lvl))
                    vals.append(pct(j["C"], j["C"] + j["P"] + j["I"]) if j else None)
                if any(v is not None for v in vals):
                    print(f"  {M + ' ' + mode:<24}{'L' + str(lvl):>6}" + "".join(f"{fmt(v):>7}" for v in vals) + f"   {ms(vals)}")

    print("\nC. Tokens de entrada por ronda y nivel (general: primera pregunta; filtered: máximo y su capa) y preguntas con prompt truncado")
    for M in MODELS:
        for mode in MODES:
            for lvl in PCT:
                cells = []
                for R in runs:
                    t = T.get((M, R, mode, lvl))
                    cells.append("-" if not t else f"{t['tok']:,}" + ("" if mode == "general" else f" ({t['layer']})")
                                 + (f" TRUNC×{t['trunc']}" if t["trunc"] else ""))
                if any(c != "-" for c in cells):
                    print(f"  {M + ' ' + mode:<24}{'L' + str(lvl):>6}  " + " | ".join(f"r{r}: {c}" for r, c in zip(runs, cells)))

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as g:
            w = csv.writer(g)
            w.writerow(["modelo", "ronda", "vista", "nivel", "paquetes", "C", "P", "I", "pctC", "pctI",
                        "errores_juez", "prompts_truncados", "salidas_cortadas", "desempates", "tokens_input", "capa_max_tokens"])
            for (M, R, mode, lvl), j in sorted(J.items()):
                n = j["C"] + j["P"] + j["I"]
                t = T.get((M, R, mode, lvl), {})
                w.writerow([M, R, mode, lvl, j["pk"], j["C"], j["P"], j["I"],
                            f"{pct(j['C'], n):.1f}" if n else "", f"{pct(j['I'], n):.1f}" if n else "",
                            j["err"], j["ptrunc"], j["otrunc"], j["ties"], t.get("tok", ""), t.get("layer", "")])
        print(f"\nTabla larga guardada en {a.csv}")


if __name__ == "__main__":
    main()
