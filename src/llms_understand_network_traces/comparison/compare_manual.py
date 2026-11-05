#!/usr/bin/env python3
"""
compare_manual.py
================================================================================
Compara tus etiquetas manuales (C/P/I) con las del juez LLM y mide el acuerdo.
Solo lee ficheros: no modifica nada.

Entrada:
  --manual-dir  carpeta con los JSON etiquetados a mano (los que salen de
                reducir_juicios.py y has rellenado con manual_label), con la
                estructura <modelo>/<vista>/judge_<traza>_answers.json
  --judge-dir   carpeta con los JSON originales del juez, con la estructura
                <modelo>/<run>/comparison/judge/<vista>/judge_<traza>_answers.json
  --run         ronda del juez a comparar (por defecto run1)

Qué calcula (solo con las preguntas ya etiquetadas por ti):
  A. acuerdo exacto con su intervalo de Wilson al 95 %, kappa de Cohen y kappa
     ponderado (pesos lineales: C > P > I son ordinales), y el kappa C frente a no-C.
     En las líneas marcadas con "por preguntas": intervalos bootstrap al 95 %
     remuestreando preguntas enteras (traza + número), porque las respuestas de
     varios modelos y vistas a la misma pregunta comparten referencia y no son
     independientes. Wilson supone independencia, así que es optimista.
  B. matriz de confusión y, por etiqueta, cobertura (fila) y precisión (columna)
  C. dirección de los desacuerdos (juez más estricto o más laxo), con una prueba
     de signos, y cuántos son desempates del juez
  D. los mismos números por: desempate o unánime, GT vacío o con contenido,
     capa, modelo y vista; y D2: tasa de desempates por modelo, vista y capa
  E. sensibilidad: sin los ficheros que viste con el juez delante, por vista, y
     con otras reglas de desempate (la más laxa, o sin desempates)
  F. consistencia de las conclusiones: % de C e I por modelo y vista según tú y
     según el juez, orden de los modelos y efecto del filtrado

Muestras de CICIDS (preprocesses_manual.py --sample): las preguntas con manual_label = "SKIP" no se
etiquetan y se ignoran; la ronda de cada fichero se lee de su nombre (_runN_), así que el mismo
directorio puede mezclar rondas; y, para el bootstrap, las respuestas de modelos distintos a la misma
ventana y pregunta se agrupan (se quita el nombre del modelo del nombre de la traza).

Ficheros "vistos": --seen vistos_juez.txt, una línea por fichero con un trozo de su
ruta (por ejemplo "llama3.1_8b/general/judge_arp-icmp"). Las preguntas con la
etiqueta [vio_juez] en la nota también se consideran vistas.

Cuidado con la lectura: las preguntas con GT vacío se acuerdan casi siempre
(es la regla 4 de la rúbrica), así que el acuerdo global las infla. Mira el
bloque "GT con contenido". Y con pocas preguntas, el kappa es inestable.

Uso (desde la raíz del proyecto):
  python3 src/comparison/compare_manual.py \\
    --manual-dir results/snapshots/06-10-2026/comparison_manual/basic_run1 \\
    --judge-dir results/snapshots/06-10-2026/basic/temp_0.0/models \\
    --seen vistos_juez.txt \\
    --out-dir results/snapshots/06-10-2026/comparison_manual
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

LABELS = ("C", "P", "I")
IDX = {l: i for i, l in enumerate(LABELS)}
NAN = float("nan")


def norm(q):
    return re.sub(r"\s+", " ", q.strip())


def lines(s):
    return [l.strip() for l in str(s).splitlines() if l.strip()]


def gt_empty(gt):
    ls = lines(gt)
    return bool(ls) and (ls[-1].lower().endswith("none") or ls[0].lower().startswith("no "))


# ------------------------------------------------------------------ estadística
def wilson(k, n, z=1.96):
    if n == 0:
        return NAN, NAN
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def kappa(pairs, weighted=False):
    n = len(pairs)
    if n == 0:
        return NAN
    k = len(LABELS)
    m = [[0] * k for _ in range(k)]
    for a, b in pairs:
        m[IDX[a]][IDX[b]] += 1
    row = [sum(m[i]) for i in range(k)]
    col = [sum(m[i][j] for i in range(k)) for j in range(k)]
    w = (lambda i, j: 1 - abs(i - j) / (k - 1)) if weighted else (lambda i, j: 1.0 if i == j else 0.0)
    po = sum(w(i, j) * m[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w(i, j) * row[i] * col[j] for i in range(k) for j in range(k)) / (n * n)
    return NAN if pe == 1 else (po - pe) / (1 - pe)


def boot_ci(groups, stat, iters=1000, seed=42):
    """Bootstrap por grupos (cada grupo = todas las respuestas a una misma pregunta)."""
    if len(groups) < 8:
        return NAN, NAN
    rng = random.Random(seed)
    vals = []
    for _ in range(iters):
        pairs = [p for _ in groups for p in groups[rng.randrange(len(groups))]]
        v = stat(pairs)
        if not math.isnan(v):
            vals.append(v)
    if len(vals) < iters / 2:
        return NAN, NAN
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))]


def sign_test_p(a, b):
    """p bilateral exacto de la binomial(n, 0.5) para a frente a b desacuerdos (orientativo: no son independientes)."""
    n = a + b
    if n == 0:
        return NAN
    k = max(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def lenient(r):
    """Etiqueta del juez si en los desempates se tomara la pasada más laxa."""
    v = [x for x in r["votes"].split("/") if x in IDX]
    return min(v, key=lambda x: IDX[x]) if r["tie"] and v else r["judge"]


def f2(x):
    return "  n/a" if math.isnan(x) else f"{x:5.2f}"


def line(name, rows, boot=False):
    if not rows:
        print(f"  {name:<34} n=  0")
        return
    pairs = [(r["manual"], r["judge"]) for r in rows]
    n = len(pairs)
    k = sum(a == b for a, b in pairs)
    lo, hi = wilson(k, n)
    kw = kappa(pairs, True)
    txt = f"  {name:<34} n={n:>4}  acuerdo {k / n:5.1%} [{lo:5.1%}-{hi:5.1%}]  kappa {f2(kappa(pairs))}  kappa pond. {f2(kw)}"
    if boot:
        g = {}
        for r in rows:
            g.setdefault((r["group"], r["qn"]), []).append((r["manual"], r["judge"]))
        groups = list(g.values())
        alo, ahi = boot_ci(groups, lambda p: sum(a == b for a, b in p) / len(p))
        klo, khi = boot_ci(groups, lambda p: kappa(p, True))
        txt += f"\n  {'':<34} por preguntas ({len(groups)}): acuerdo [{alo:5.1%}-{ahi:5.1%}]  kappa pond. [{f2(klo)}, {f2(khi)}]"
    print(txt)


def pct(rs, who, lab):
    return sum(r[who] == lab for r in rs) / len(rs) if rs else NAN


# ------------------------------------------------------------------ carga
def layer_of(i, n_arp, n_ip):
    return "ARP" if i <= n_arp else "IP" if i <= n_arp + n_ip else "TCP/UDP"


def load(manual_dir, judge_dir, run, seen, n_arp, n_ip):
    rows, pend, err, missing = [], 0, 0, 0
    pattern = os.path.join(manual_dir, "**", "judge_*_answers.json")
    for f in sorted(glob.glob(pattern, recursive=True)):
        man = json.load(open(f, encoding="utf-8"))
        model, mode = man.get("llm_model"), man.get("mode")
        if not model or not mode:
            print(f"  [AVISO] {f}: sin llm_model/mode, se salta")
            continue
        trace = os.path.basename(f)[len("judge_"):-len("_answers.json")]
        mrun = re.search(r"_(run\d+)_L\d+_", trace)
        run_f = mrun.group(1) if mrun else run
        group = re.sub(r"_[^_]+_(run\d+_L\d+_\d+pkts)$", r"_\1", trace)
        jf = os.path.join(judge_dir, model, run_f, "comparison", "judge", mode, os.path.basename(f))
        if not os.path.exists(jf):
            print(f"  [AVISO] no existe el juicio del juez: {jf}")
            missing += 1
            continue
        jud = {norm(q): v for q, v in json.load(open(jf, encoding="utf-8"))["questions"].items()}
        seen_file = any(p in f for p in seen)
        for i, (q, v) in enumerate(man["questions"].items(), 1):
            ml = v.get("manual_label", "")
            if ml == "SKIP":
                continue
            if ml not in LABELS:
                pend += 1
                continue
            jv = jud.get(norm(q))
            if jv is None or jv.get("final_label") not in LABELS:
                err += 1
                continue
            note = v.get("notes") or ""
            tags = {t.lower() for t in re.findall(r"\[([^\]]+)\]", note)}
            votes = jv.get("votes", {})
            rows.append(dict(
                model=model, mode=mode, trace=trace, group=group, qn=i, manual=ml, judge=jv["final_label"],
                tie=not jv.get("consistent", True), votes=f'{votes.get("pass1")}/{votes.get("pass2")}',
                gt_empty=gt_empty(jv.get("gt_answer", "")), layer=layer_of(i, n_arp, n_ip),
                seen=seen_file or "vio_juez" in tags, note=note, question=q))
    return rows, pend, err, missing


# ------------------------------------------------------------------ informe
class Tee:
    """Escribe a la vez en la terminal y en un fichero."""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, x):
        for st in self.streams:
            st.write(x)

    def flush(self):
        for st in self.streams:
            st.flush()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manual-dir", required=True)
    ap.add_argument("--judge-dir", required=True)
    ap.add_argument("--run", default="run1")
    ap.add_argument("--seen", default=None, help="fichero con trozos de ruta de los ficheros vistos con el juez")
    ap.add_argument("--layers", default="3,4", help="preguntas de ARP e IP (por defecto 3,4; el resto TCP/UDP)")
    ap.add_argument("--out-dir", default=None,
                    help="carpeta donde guardar el informe (agreement_manual_vs_judge.txt) y el CSV de desacuerdos")
    ap.add_argument("--out-csv", default=None, help="ruta del CSV de desacuerdos (por defecto, dentro de --out-dir)")
    a = ap.parse_args()

    report = None
    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)
        report = open(os.path.join(a.out_dir, "agreement_manual_vs_judge.txt"), "w", encoding="utf-8")
        sys.stdout = Tee(sys.__stdout__, report)
    out_csv = a.out_csv or (os.path.join(a.out_dir, "desacuerdos_juez.csv") if a.out_dir
                            else "validacion/desacuerdos_juez.csv")

    seen = []
    if a.seen and os.path.exists(a.seen):
        seen = [l.strip() for l in open(a.seen, encoding="utf-8") if l.strip() and not l.startswith("#")]
    elif a.seen:
        print(f"[AVISO] no existe {a.seen}: las líneas 'vistos' del bloque E no excluyen nada")
    n_arp, n_ip = (int(x) for x in a.layers.split(","))

    rows, pend, err, missing = load(a.manual_dir, a.judge_dir, a.run, seen, n_arp, n_ip)
    if not rows:
        raise SystemExit("No hay ninguna pregunta etiquetada y emparejada. ¿Rellenaste manual_label? ¿Rutas correctas?")

    print(f"Pares comparados: {len(rows)}  |  sin etiquetar por ti: {pend}  |  juez E/N o sin emparejar: {err}"
          f"  |  ficheros sin juicio: {missing}\n")

    print("A. Global")
    line("todas", rows, boot=True)
    pb = [("C" if r["manual"] == "C" else "I", "C" if r["judge"] == "C" else "I") for r in rows]
    print(f"  {'C frente a no-C (binario)':<34} kappa {f2(kappa(pb))}")

    print("\nB. Matriz de confusión (filas: tu etiqueta; columnas: juez)")
    cm = Counter((r["manual"], r["judge"]) for r in rows)
    print("        " + "".join(f"{'juez ' + l:>9}" for l in LABELS))
    for m in LABELS:
        print(f"  tú {m}  " + "".join(f"{cm[(m, j)]:>9}" for j in LABELS))
    print("   Por etiqueta (cobertura = fila: si tú pones X, el juez también; precisión = columna: si el juez pone X, tú también)")
    for l in LABELS:
        tu = sum(cm[(l, j)] for j in LABELS)
        jz = sum(cm[(m, l)] for m in LABELS)
        ok = cm[(l, l)]
        cov = f"{ok}/{tu} ({ok / tu:.1%})" if tu else "n/a"
        prec = f"{ok}/{jz} ({ok / jz:.1%})" if jz else "n/a"
        print(f"   {l}:  cobertura {cov:<16} precisión {prec}")

    stricter = sum(IDX[r["judge"]] > IDX[r["manual"]] for r in rows)
    laxer = sum(IDX[r["judge"]] < IDX[r["manual"]] for r in rows)
    dis = [r for r in rows if r["manual"] != r["judge"]]
    print(f"\nC. Desacuerdos: {stricter + laxer} ({(stricter + laxer) / len(rows):.1%})  "
          f"juez más estricto que tú {stricter}  |  juez más laxo que tú {laxer}")
    if stricter + laxer:
        print(f"   Prueba de signos (binomial exacta, orientativa: las respuestas no son independientes): "
              f"p = {sign_test_p(stricter, laxer):.2g}")
        ties_dis = sum(r["tie"] for r in dis)
        print(f"   Desacuerdos que son desempates del juez: {ties_dis} de {len(dis)} ({ties_dis / len(dis):.1%}); "
              f"con las dos pasadas unánimes: {len(dis) - ties_dis}")
        by = Counter((r["manual"], r["judge"], "desempate" if r["tie"] else "unánime") for r in dis)
        for (m, j, t), n in sorted(by.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"     tú {m} -> juez {j} ({t}): {n}")
    jc = [r for r in rows if r["judge"] == "C"]
    mc = [r for r in rows if r["manual"] == "C"]
    if jc:
        print(f"   De las {len(jc)} C del juez, son C tuyas {sum(r['manual'] == 'C' for r in jc)} "
              f"({sum(r['manual'] == 'C' for r in jc) / len(jc):.1%})  <- el juez da por correcta una respuesta que tú no")
    if mc:
        print(f"   De tus {len(mc)} C, el juez da C a {sum(r['judge'] == 'C' for r in mc)} "
              f"({sum(r['judge'] == 'C' for r in mc) / len(mc):.1%})")

    print("\nD. Por tipo de caso")
    line("desempate del juez", [r for r in rows if r["tie"]])
    line("unánime", [r for r in rows if not r["tie"]])
    line("GT vacío (regla 4)", [r for r in rows if r["gt_empty"]])
    line("GT con contenido", [r for r in rows if not r["gt_empty"]], boot=True)
    for ly in ("ARP", "IP", "TCP/UDP"):
        line(f"capa {ly}", [r for r in rows if r["layer"] == ly])
    for md in sorted({r["model"] for r in rows}):
        line(f"modelo {md}", [r for r in rows if r["model"] == md])
    for mo in ("general", "filtered"):
        line(f"vista {mo}", [r for r in rows if r["mode"] == mo])

    print("\nD2. Desempates del juez (sus dos pasadas no coinciden)")
    for key, name in (("model", "modelo"), ("mode", "vista"), ("layer", "capa")):
        c, n = Counter(), Counter()
        for r in rows:
            n[r[key]] += 1
            c[r[key]] += r["tie"]
        print(f"  por {name}: " + ", ".join(f"{k} {c[k]}/{n[k]} ({c[k] / n[k]:.1%})" for k in sorted(n)))
    ties = [r for r in rows if r["tie"]]
    if ties:
        inv = sum(r["manual"] in r["votes"].split("/") for r in ties)
        print(f"  En los {len(ties)} desempates, tu etiqueta coincide con una de las dos pasadas en {inv}")

    print("\nE. Sensibilidad")
    line("sin los vistos con el juez", [r for r in rows if not r["seen"]], boot=True)
    for mo in ("general", "filtered"):
        line(f"vista {mo}, sin los vistos", [r for r in rows if r["mode"] == mo and not r["seen"]])
    line("desempate: la pasada más laxa", [dict(r, judge=lenient(r)) for r in rows], boot=True)
    line("sin desempates (solo unánimes)", [r for r in rows if not r["tie"]], boot=True)

    print("\nF. ¿Llegaría el juez a las mismas conclusiones? (% de respuestas con cada etiqueta)")
    print(f"  {'':<34}{'%C tuyo':>9}{'%C juez':>9}{'%I tuyo':>9}{'%I juez':>9}")
    models = sorted({r["model"] for r in rows})
    for md in models:
        for mo in ("general", "filtered"):
            rs = [r for r in rows if r["model"] == md and r["mode"] == mo]
            if rs:
                print(f"  {md + ' ' + mo:<34}{pct(rs, 'manual', 'C'):>9.1%}{pct(rs, 'judge', 'C'):>9.1%}"
                      f"{pct(rs, 'manual', 'I'):>9.1%}{pct(rs, 'judge', 'I'):>9.1%}")

    def rank(who):
        return sorted(models, key=lambda m: -pct([r for r in rows if r["model"] == m], who, "C"))
    print(f"  Orden de modelos por %C, según tú:   {' > '.join(rank('manual'))}")
    print(f"                           según el juez: {' > '.join(rank('judge'))}  "
          f"({'mismo orden' if rank('manual') == rank('judge') else 'orden distinto'})")
    print("  Efecto del filtrado en %C (filtered - general):")
    for md in models:
        g = [r for r in rows if r["model"] == md and r["mode"] == "general"]
        fl = [r for r in rows if r["model"] == md and r["mode"] == "filtered"]
        if g and fl:
            dm = pct(fl, "manual", "C") - pct(g, "manual", "C")
            dj = pct(fl, "judge", "C") - pct(g, "judge", "C")
            print(f"    {md:<30} tú {dm:+7.1%}   juez {dj:+7.1%}")

    if dis:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as g:
            w = csv.writer(g)
            w.writerow(["modelo", "vista", "traza", "pregunta_n", "tu_etiqueta", "juez", "votos_juez",
                        "desempate", "visto", "tu_nota", "pregunta"])
            for r in sorted(dis, key=lambda r: (r["model"], r["mode"], r["trace"], r["qn"])):
                w.writerow([r["model"], r["mode"], r["trace"], r["qn"], r["manual"], r["judge"], r["votes"],
                            int(r["tie"]), int(r["seen"]), r["note"], r["question"][:90]])
        print(f"\nDesacuerdos guardados en {out_csv} ({len(dis)}).")
    if report:
        sys.stdout = sys.__stdout__
        report.close()
        print(f"Informe guardado en {os.path.join(a.out_dir, 'agreement_manual_vs_judge.txt')}")


if __name__ == "__main__":
    main()