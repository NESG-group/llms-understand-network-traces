#!/usr/bin/env python3
"""
metrics.py
================================================================================
Métricas unificadas de las etiquetas del juez (solo lectura), para las trazas básicas
y para CICIDS, con una sola línea de comandos. Reemplaza a cicids_aggregate_rounds.py y a
basic_rounds_summary.py, y cubre lo esencial de metrics_per_model.py (a propósito, NO incluye
el kappa entre vistas, la confianza de la moda ni la consistencia entre trazas).
NO incluye el acuerdo del juez con lo manual: eso sigue en compare_manual.py.

Qué calcula (todo sale como tablas Markdown, listas para pegar, y como CSV):
  1. Corrección: %C, %P e %I por modelo, vista y grupo, con media ± sd entre rondas.
       - basic : un grupo ("all traces").
       - cicids: dos grupos, L25-L75 (los niveles que caben) y L100 (125 %, recortado en general).
  2. Por capa (ARP, IP, TCP/UDP): %C por modelo, vista y grupo.
  3. Por tipo de referencia: capa ausente / referencia vacía con capa presente / con contenido.
  4. Efecto del filtrado: diferencia de %C, %P e %I (filtrada - general), transiciones por
     pregunta (mejora / igual / empeora), puntuación de mejora normalizada (+2 de I a C,
     +1 de I a P o de P a C, signo contrario si empeora, escalada a +-100 %) y prueba de
     signos; en total y por tipo de referencia.
  5. Recursos: tokens de entrada medios, % de prompts recortados por el servidor, % de salidas
     cortadas por el tope, latencia por respuesta y % de desempates del juez.
  6. Reducción de tokens de la vista filtrada respecto a la general, por pregunta.
  7. Estabilidad entre ejecuciones (solo basic: las mismas trazas se repiten en cada ronda).

Cómo se emparejan general y filtrada para el efecto del filtrado (--pairing):
  - basic  (auto = mode): sobre la etiqueta modal de cada traza entre rondas, para no repetir
    la misma respuesta cinco veces a temperatura 0.
  - cicids (auto = runs): cada ronda y nivel es una ventana distinta; se emparejan todas.

Ojo con la lectura:
  - La sd entre rondas es descriptiva. Los niveles son prefijos de la misma ventana, así que
    las preguntas de un mismo nivel no son muestras independientes; el p-valor de la prueba de
    signos es orientativo.
  - El %C absoluto depende de cuántas preguntas tienen la capa vacía (mira la tabla 3).
  - Los tokens dependen del tokenizador: no se comparan entre familias. L100 de la vista general
    está recortado por el servidor (Ollama 0.33.3): no es "más contexto".
  - Las etiquetas E (error del juez), N (sin respuesta) y las preguntas ausentes se excluyen.

Lee, por modelo y ronda:
  <models-dir>/<modelo>/run<N>/comparison/judge/<vista>/judge_<traza>_answers.json
  <models-dir>/<modelo>/run<N>/llm_answers/<vista>/<traza>_answers.json   (si existe)

Uso (desde la raíz del proyecto):
  python3 src/analysis/metrics.py --dataset cicids
  python3 src/analysis/metrics.py --dataset cicids --runs 1 2 3 4 5 --tag _5rondas
  python3 src/analysis/metrics.py --dataset basic \
        --models-dir results/snapshots/06-10-2026/basic/temp_0.0/models --tag _basic_t0
  python3 src/analysis/metrics.py --dataset basic --models-dir <...> --constants utils.constants_old
================================================================================
"""
import argparse
import csv
import glob
import importlib
import json
import math
import os
import re
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

VIEWS = ("general", "filtered")
VALID = ("C", "P", "I")
SCORE = {("I", "C"): 2, ("I", "P"): 1, ("P", "C"): 1, ("C", "P"): -1, ("P", "I"): -1, ("C", "I"): -2}
PCT = {25: 50, 50: 75, 75: 100, 100: 125}
PRIO = {"CPI": {"C": 0, "P": 1, "I": 2}, "IPC": {"I": 0, "P": 1, "C": 2}}
CATS = ("layer absent", "empty reference, layer present", "with content")


# ------------------------------------------------------------------ utilidades
def norm(q):
    return re.sub(r"\s+", " ", str(q).strip())


def gt_empty(gt):
    ls = [l.strip() for l in str(gt).splitlines() if l.strip()]
    return bool(ls) and (ls[-1].lower().endswith("none") or ls[0].lower().startswith("no "))


def ms(vals, dec=1):
    v = [x for x in vals if x is not None]
    if not v:
        return "n/a"
    if len(v) == 1:
        return f"{v[0]:.{dec}f}"
    return f"{statistics.mean(v):.{dec}f} ± {statistics.stdev(v):.{dec}f}"


def pc(num, den, dec=1):
    return None if not den else round(100.0 * num / den, dec)


def fnum(x, dec=1, sign=False):
    if x is None:
        return "n/a"
    return f"{x:+.{dec}f}" if sign else f"{x:.{dec}f}"


def sign_test(imp, wor):
    m = imp + wor
    if m == 0:
        return None
    k = min(imp, wor)
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m)


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


# ------------------------------------------------------------------ carga
def load_layout(module_name):
    mod = importlib.import_module(module_name)
    qs = [norm(q) for q in mod.ALL_QUESTIONS]
    n_arp, n_ip = len(mod.ARP_QUESTIONS), len(mod.IP_QUESTIONS)
    layers = {"ARP": (0, n_arp), "IP": (n_arp, n_arp + n_ip), "TCP/UDP": (n_arp + n_ip, len(qs))}
    return qs, layers


def load_record(jf, lf, qs):
    try:
        with open(jf, encoding="utf-8") as fh:
            jd = json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] no se puede leer {jf}: {e}")
        return None
    jmap = {norm(k): v for k, v in jd.get("questions", {}).items()}
    lmap, met = {}, {}
    if os.path.exists(lf):
        try:
            with open(lf, encoding="utf-8") as fh:
                ld = json.load(fh)
            lq = ld.get("Questions", {})
            lmap = {norm(k): v for k, v in lq.items()}
            met = ld.get("Metrics", {}) or {}
            # si las preguntas no coinciden por texto pero hay el mismo número, se emparejan por posición
            if jmap and lmap and not (set(jmap) & set(lmap)) and len(jmap) == len(lmap):
                lmap = {norm(jk): lv for jk, lv in zip(jd.get("questions", {}).keys(), lq.values())}
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] no se puede leer {lf}: {e}")
    rec = dict(lab=[], tok=[], trunc=[], cut=[], cempty=[], gempty=[], tie=[], layer=[], absent=0,
               lat=met.get("total_latency_s"), answered=met.get("questions_answered"))
    for q in qs:
        j, l = jmap.get(q), lmap.get(q, {})
        if j is None:
            rec["absent"] += 1
            rec["lab"].append(None); rec["tok"].append(None); rec["layer"].append(None)
            for k in ("trunc", "cut", "cempty", "gempty", "tie"):
                rec[k].append(False)
            continue
        lab = j.get("final_label") or j.get("label")
        tok = j.get("tokens_input", l.get("tokens_input"))
        rec["lab"].append(lab if lab in VALID else None)
        rec["tok"].append(tok if isinstance(tok, (int, float)) else None)
        rec["trunc"].append(bool(j.get("truncation_suspected", l.get("truncation_suspected", False))))
        rec["cut"].append(bool(j.get("output_truncated", l.get("output_truncated", False))))
        rec["cempty"].append(bool(j.get("csv_empty")) or j.get("csv_rows") == 0)
        rec["gempty"].append(gt_empty(j.get("gt_answer", "")))
        rec["tie"].append(not j.get("consistent", True))
        rec["layer"].append(l.get("csv_source") or j.get("csv_source"))
    return rec


def load_all(models_dir, models, runs, dataset, qs):
    recs = {}
    for m in models:
        for rdir in sorted(glob.glob(f"{models_dir}/{m}/run*")):
            mr = re.search(r"run(\d+)$", rdir)
            if not mr or (runs and int(mr.group(1)) not in runs):
                continue
            run = int(mr.group(1))
            for view in VIEWS:
                for jf in sorted(glob.glob(f"{rdir}/comparison/judge/{view}/judge_*_answers.json")):
                    stem = os.path.basename(jf)[len("judge_"):-len("_answers.json")]
                    lv = re.search(r"_L(\d+)_(\d+)pkts", stem)
                    if dataset == "cicids":
                        if not lv or int(lv.group(1)) not in PCT:
                            continue
                        unit, pk = int(lv.group(1)), int(lv.group(2))
                    else:
                        if lv:
                            continue
                        unit, pk = stem, None
                    rec = load_record(jf, f"{rdir}/llm_answers/{view}/{stem}_answers.json", qs)
                    if rec is not None:
                        rec["pk"] = pk
                        recs[(m, run, view, unit)] = rec
    return recs


# ------------------------------------------------------------------ agregación
def category(recs, m, run, unit, qi):
    f = recs.get((m, run, "filtered", unit))
    if f is None:
        return "with content"
    if f["cempty"][qi]:
        return "layer absent"
    if f["gempty"][qi]:
        return "empty reference, layer present"
    return "with content"


def in_group(unit, gunits):
    return gunits is None or unit in gunits


def runs_of(recs, m):
    return sorted({k[1] for k in recs if k[0] == m})


def run_counts(recs, m, view, gunits, qsel=None, dataset="basic"):
    """{ronda: Counter de etiquetas} sobre los registros del grupo; qsel(run, unit, qi) -> bool."""
    out = {}
    for r in runs_of(recs, m):
        units = [k[3] for k in recs if k[0] == m and k[1] == r and k[2] == view and in_group(k[3], gunits)]
        if not units or (gunits is not None and set(units) != set(gunits) and dataset == "cicids"):
            continue
        c = Counter()
        for u in units:
            rec = recs[(m, r, view, u)]
            for qi, lab in enumerate(rec["lab"]):
                if lab and (qsel is None or qsel(r, u, qi)):
                    c[lab] += 1
        if sum(c.values()):
            out[r] = c
    return out


def vote(label_lists, prio):
    res = []
    for qi in range(len(label_lists[0])):
        v = [l[qi] for l in label_lists if l[qi]]
        if not v:
            res.append(None)
            continue
        cnt = Counter(v)
        top = max(cnt.values())
        res.append(min((x for x, n in cnt.items() if n == top), key=lambda x: prio[x]))
    return res


def make_pairs(recs, m, gunits, pairing, prio):
    pairs = []
    if pairing == "runs":
        for (mm, r, v, u), f in recs.items():
            if mm != m or v != "filtered" or not in_group(u, gunits):
                continue
            g = recs.get((m, r, "general", u))
            if g is None:
                continue
            for qi in range(len(f["lab"])):
                if g["lab"][qi] and f["lab"][qi]:
                    pairs.append((g["lab"][qi], f["lab"][qi], category(recs, m, r, u, qi)))
    else:
        for u in sorted({k[3] for k in recs if k[0] == m and in_group(k[3], gunits)}, key=str):
            gl = [recs[k]["lab"] for k in recs if k[0] == m and k[2] == "general" and k[3] == u]
            fl = [recs[k]["lab"] for k in recs if k[0] == m and k[2] == "filtered" and k[3] == u]
            if not gl or not fl:
                continue
            gm, fm = vote(gl, prio), vote(fl, prio)
            r0 = min(k[1] for k in recs if k[0] == m and k[2] == "filtered" and k[3] == u)
            for qi in range(len(gm)):
                if gm[qi] and fm[qi]:
                    pairs.append((gm[qi], fm[qi], category(recs, m, r0, u, qi)))
    return pairs


def trans(pairs):
    n = len(pairs)
    s = [SCORE.get((g, f), 0) for g, f, _ in pairs]
    imp, wor = sum(1 for x in s if x > 0), sum(1 for x in s if x < 0)
    cg = Counter(g for g, _, _ in pairs)
    cf = Counter(f for _, f, _ in pairs)
    d = {lab: (None if not n else round(100.0 * (cf[lab] - cg[lab]) / n, 1)) for lab in VALID}
    return dict(n=n, imp=imp, same=n - imp - wor, wor=wor, score=None if not n else round(100.0 * sum(s) / (2 * n), 1),
                p=sign_test(imp, wor), d=d)


# ------------------------------------------------------------------ informe
def build_report(dataset, models, recs, qs, layers, groups, pairing, prio, runs_label):
    out, csv_pairs = [], []
    out.append(f"# Metrics — dataset: {dataset}\n\nRuns: {runs_label}. Pairing: {pairing}. "
               f"Tie-break for modal labels: {'/'.join(sorted(prio, key=prio.get))}.\n")

    # 0. inventario
    rows = []
    for m in models:
        rs = runs_of(recs, m)
        ng = sum(1 for k in recs if k[0] == m and k[2] == "general")
        nf = sum(1 for k in recs if k[0] == m and k[2] == "filtered")
        ab = sum(r["absent"] for k, r in recs.items() if k[0] == m)
        rows.append([m, rs, ng, nf, ab])
    out.append("## 0. Files read\n\n" + md_table(["Model", "Runs", "General files", "Filtered files", "Questions absent"], rows) + "\n")

    # 1. corrección
    rows = []
    for m in models:
        for view in VIEWS:
            for gname, gu in groups:
                rc = run_counts(recs, m, view, gu, dataset=dataset)
                if not rc:
                    continue
                pcts = {lab: [pc(c[lab], sum(c.values())) for c in rc.values()] for lab in VALID}
                rows.append([m, view, gname] + [ms(pcts[l]) for l in VALID] + [len(rc), sum(sum(c.values()) for c in rc.values())])
    out.append("## 1. Answer correctness (% of answers, mean ± sd across runs)\n\n"
               + md_table(["Model", "View", "Group", "%C", "%P", "%I", "Runs", "Valid answers"], rows) + "\n")

    # 2. por capa
    rows = []
    for m in models:
        for view in VIEWS:
            for gname, gu in groups:
                for lname, (s, e) in layers.items():
                    rc = run_counts(recs, m, view, gu, qsel=lambda r, u, qi, s=s, e=e: s <= qi < e, dataset=dataset)
                    if not rc:
                        continue
                    pcts = {lab: [pc(c[lab], sum(c.values())) for c in rc.values()] for lab in VALID}
                    rows.append([m, view, gname, lname] + [ms(pcts[l]) for l in VALID])
    out.append("## 2. Answer correctness by protocol layer of the question (mean ± sd across runs)\n\n"
               + md_table(["Model", "View", "Group", "Layer", "%C", "%P", "%I"], rows) + "\n")
    
    # 3. por tipo de referencia
    rows = []
    for m in models:
        for view in VIEWS:
            for gname, gu in groups:
                for cat in CATS:
                    rc = run_counts(recs, m, view, gu, dataset=dataset,
                                    qsel=lambda r, u, qi, m=m, cat=cat: category(recs, m, r, u, qi) == cat)
                    c = sum(rc.values(), Counter())
                    n = sum(c.values())
                    if n:
                        rows.append([m, view, gname, cat, n] + [fnum(pc(c[l], n)) for l in VALID])
    out.append("## 3. Correctness by type of reference answer (pooled over runs)\n\n"
               + md_table(["Model", "View", "Group", "Reference type", "n", "%C", "%P", "%I"], rows) + "\n")

    # 4. efecto del filtrado
    rows, rows_cat = [], []
    for m in models:
        for gname, gu in groups:
            pairs = make_pairs(recs, m, gu, pairing, prio)
            if not pairs:
                continue
            t = trans(pairs)
            rows.append([m, gname, t["n"], fnum(t["d"]["C"], sign=True), fnum(t["d"]["P"], sign=True), fnum(t["d"]["I"], sign=True),
                         t["imp"], t["same"], t["wor"], fnum(t["score"], sign=True), "n/a" if t["p"] is None else f"{t['p']:.3g}"])
            csv_pairs.append([m, gname, "all", t["n"], t["imp"], t["same"], t["wor"], t["score"], t["p"]])
            for cat in CATS:
                pcat = [p for p in pairs if p[2] == cat]
                if pcat:
                    tc = trans(pcat)
                    rows_cat.append([m, gname, cat, tc["n"], tc["imp"], tc["same"], tc["wor"], fnum(tc["score"], sign=True)])
                    csv_pairs.append([m, gname, cat, tc["n"], tc["imp"], tc["same"], tc["wor"], tc["score"], tc["p"]])
    out.append("## 4. Effect of filtering (filtered vs general, paired by question)\n\n"
               "Δ in percentage points (filtered − general). Improved/worsened = label better/worse in the filtered view. "
               "Score: +2 I→C, +1 I→P or P→C, opposite sign if worse, scaled to ±100 %. p: two-sided sign test (indicative).\n\n"
               + md_table(["Model", "Group", "Pairs", "Δ%C", "Δ%P", "Δ%I", "Improved", "Same", "Worsened", "Score %", "p"], rows) + "\n")
    out.append("### 4b. By type of reference answer\n\n"
               + md_table(["Model", "Group", "Reference type", "Pairs", "Improved", "Same", "Worsened", "Score %"], rows_cat) + "\n")

    # 5. recursos
    rows = []
    for m in models:
        for view in VIEWS:
            for gname, gu in groups:
                rs = [r for k, r in recs.items() if k[0] == m and k[2] == view and in_group(k[3], gu)]
                if not rs:
                    continue
                toks = [t for r in rs for t, tr in zip(r["tok"], r["trunc"]) if t is not None and not tr]
                nq = sum(1 for r in rs for l in r["lab"] if l is not None)
                ntr = sum(sum(r["trunc"]) for r in rs)
                ncut = sum(sum(r["cut"]) for r in rs)
                ntie = sum(sum(r["tie"]) for r in rs)
                nall = sum(len(r["lab"]) for r in rs)
                lat = sum(r["lat"] for r in rs if isinstance(r["lat"], (int, float)))
                ans = sum(r["answered"] for r in rs if isinstance(r["answered"], (int, float)))
                rows.append([m, view, gname, f"{statistics.mean(toks):,.0f}" if toks else "n/a", fnum(pc(ntr, nall)), fnum(pc(ncut, nall)),
                             fnum(lat / ans) if ans and lat else "n/a", fnum(pc(ntie, nall))])
    out.append("## 5. Resource use (pooled over runs)\n\n"
               "Tokens: mean `tokens_input` of non-truncated prompts (as counted by the inference server; not comparable across model families).\n\n"
               + md_table(["Model", "View", "Group", "Mean input tokens", "% prompts truncated", "% outputs cut at token cap", "Latency per answer (s)", "% judge ties"], rows) + "\n")

    # 6. reducción de tokens por pregunta
    rows = []
    for m in models:
        for gname, gu in groups:
            red, nb = [], 0
            for (mm, r, v, u), f in recs.items():
                if mm != m or v != "filtered" or not in_group(u, gu):
                    continue
                g = recs.get((m, r, "general", u))
                if g is None:
                    continue
                gt = [t for t, tr in zip(g["tok"], g["trunc"]) if t is not None and not tr]
                if not gt or any(g["trunc"]):
                    continue
                gmean = statistics.mean(gt)
                for qi, t in enumerate(f["tok"]):
                    if t is None or f["trunc"][qi] or f["cempty"][qi]:
                        continue
                    red.append(100.0 * (1 - t / gmean))
                    nb += t >= gmean
            if red:
                rows.append([m, gname, len(red), fnum(statistics.mean(red)), fnum(statistics.median(red)), fnum(min(red)), fnum(max(red)), nb])
            else:
                rows.append([m, gname, 0, "n/a", "n/a", "n/a", "n/a", "n/a"])
    out.append("## 6. Token reduction of the filtered prompt vs the general prompt (per question)\n\n"
               "Excludes truncated prompts and questions whose layer is empty. Each filtered prompt is compared with the mean "
               "general prompt of the same trace/window. Negative reduction = filtered prompt larger.\n\n"
               + md_table(["Model", "Group", "Questions", "Mean %", "Median %", "Min %", "Max %", "Filtered ≥ general"], rows) + "\n")

    # 7. estabilidad (solo basic)
    if dataset == "basic":
        rows = []
        for m in models:
            for view in VIEWS:
                un = a = n = 0
                nr = 0
                for u in sorted({k[3] for k in recs if k[0] == m}, key=str):
                    ll = [recs[k]["lab"] for k in recs if k[0] == m and k[2] == view and k[3] == u]
                    nr = max(nr, len(ll))
                    if len(ll) < 2:
                        continue
                    for qi in range(len(ll[0])):
                        v = [l[qi] for l in ll if l[qi]]
                        if not v:
                            continue
                        n += 1
                        top = Counter(v).most_common(1)[0][1]
                        un += top == len(v)
                        a += top >= math.ceil(0.8 * len(v))
                if n:
                    rows.append([m, view, nr, n, fnum(pc(un, n)), fnum(pc(a, n))])
        out.append("## 7. Stability across runs (same traces repeated)\n\n"
                   + md_table(["Model", "View", "Runs", "Questions", "% unanimous", "% ≥80 % agree"], rows) + "\n")
    else:
        out.append("## 7. Stability across runs\n\nNot computed for cicids: each round is a different window of the capture. "
                   "See the sd across rounds in table 1 and `dotplot_cicids_rounds.py` for per-question consistency.\n")
    return "\n".join(out), csv_pairs


def write_csvs(recs, csv_pairs, prefix):
    with open(prefix + "_perfile.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["model", "run", "view", "unit", "packets", "C", "P", "I", "n_valid", "tokens_first", "prompts_truncated",
                    "outputs_cut", "judge_ties", "latency_s", "answered"])
        for (m, r, v, u), rec in sorted(recs.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], str(kv[0][3]))):
            c = Counter(l for l in rec["lab"] if l)
            tok = next((t for t in rec["tok"] if t is not None), "")
            w.writerow([m, r, v, u, rec["pk"] or "", c["C"], c["P"], c["I"], sum(c.values()), tok, sum(rec["trunc"]),
                        sum(rec["cut"]), sum(rec["tie"]), rec["lat"] or "", rec["answered"] or ""])
    with open(prefix + "_transitions.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["model", "group", "reference_type", "pairs", "improved", "same", "worsened", "score_pct", "sign_test_p"])
        w.writerows(csv_pairs)
    with open(prefix + "_layer_tokens.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["model", "run", "unit", "layer", "tokens_max", "truncated_questions", "general_tokens_first"])
        for (m, r, v, u), rec in sorted(recs.items(), key=lambda kv: (kv[0][0], kv[0][1], str(kv[0][3]))):
            if v != "filtered":
                continue
            gen = recs.get((m, r, "general", u))
            gtok = next((t for t in gen["tok"] if t is not None), "") if gen else ""
            lay = {}
            for t, tr, ly in zip(rec["tok"], rec["trunc"], rec["layer"]):
                if t is None or not ly:
                    continue
                d = lay.setdefault(ly, [0, 0])
                d[0] = max(d[0], t)
                d[1] += tr
            for ly, (t, tr) in sorted(lay.items()):
                w.writerow([m, r, u, ly, t, tr, gtok])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", choices=("basic", "cicids"), required=True, help="basic = trazas básicas; cicids = ventanas de CICIDS")
    ap.add_argument("--models-dir", default="results/models", help="carpeta con una subcarpeta por modelo (p. ej. un snapshot)")
    ap.add_argument("--models", nargs="*", default=None, help="restringe a estos modelos (por defecto, todas las subcarpetas)")
    ap.add_argument("--runs", type=int, nargs="*", default=None, help="rondas a incluir (por defecto, todas)")
    ap.add_argument("--constants", default="utils.constants", help="módulo con ALL_QUESTIONS, ARP_QUESTIONS e IP_QUESTIONS")
    ap.add_argument("--pairing", choices=("auto", "mode", "runs"), default="auto",
                    help="cómo emparejar general y filtrada: auto = mode en basic, runs en cicids")
    ap.add_argument("--tie-break", choices=("CPI", "IPC"), default="CPI",
                    help="empates de la moda: CPI = gana la mejor etiqueta (como dotplot_model.py); IPC = la peor")
    ap.add_argument("--out-dir", default="results/summary")
    ap.add_argument("--tag", default="", help="sufijo para los ficheros de salida (p. ej. _basic_t0)")
    ap.add_argument("--no-files", action="store_true", help="solo imprime, sin escribir ficheros")
    a = ap.parse_args()

    qs, layers = load_layout(a.constants)
    if not os.path.isdir(a.models_dir):
        raise SystemExit(f"No existe --models-dir: {a.models_dir}")
    models = a.models or sorted(d for d in os.listdir(a.models_dir) if os.path.isdir(os.path.join(a.models_dir, d)))
    recs = load_all(a.models_dir, models, a.runs, a.dataset, qs)
    if not recs:
        raise SystemExit(f"No hay juicios en {a.models_dir} para el dataset '{a.dataset}' (¿dataset o --models-dir equivocados?).")
    models = [m for m in models if any(k[0] == m for k in recs)]
    groups = [("L25–L75", {25, 50, 75}), ("L100 (125 %)", {100})] if a.dataset == "cicids" else [("all traces", None)]
    pairing = a.pairing if a.pairing != "auto" else ("runs" if a.dataset == "cicids" else "mode")
    runs_label = a.runs or sorted({k[1] for k in recs})
    text, csv_pairs = build_report(a.dataset, models, recs, qs, layers, groups, pairing, PRIO[a.tie_break], runs_label)
    print(text)
    if not a.no_files:
        os.makedirs(a.out_dir, exist_ok=True)
        prefix = os.path.join(a.out_dir, f"metrics_{a.dataset}{a.tag}")
        with open(prefix + ".md", "w", encoding="utf-8") as fh:
            fh.write(text)
        write_csvs(recs, csv_pairs, prefix)
        print(f"\n[OK] {prefix}.md, {prefix}_perfile.csv, {prefix}_transitions.csv, {prefix}_layer_tokens.csv")


if __name__ == "__main__":
    main()