#!/usr/bin/env python3
"""
preprocesses_manual.py
================================================================================
Crea copias reducidas de los JSON del juez para la validación manual.

Por defecto deja, por pregunta, todo lo que hay HASTA 'final_label' incluido
(question, gt_answer, llm_answer, truncation_suspected, margin_violated,
output_truncated, csv_empty, csv_rows, tokens_input, final_label...) y quita lo
que viene después (consistent, unanimous, single_pass, degraded, votes,
pass1, pass2: los votos y el razonamiento del juez). La cabecera y el summary
se conservan tal cual.

Opciones:
  --blind    quita también la etiqueta del juez (final_label) y, a nivel de
             fichero, el summary y judge_model, para etiquetar sin ver el
             veredicto. Los JSON originales del juez siguen siendo la clave.
  --manual   añade a cada pregunta los campos vacíos "manual_label" y "notes".
  --compact  condensa las respuestas con líneas repetidas (bucles): deja las
             líneas únicas con un aviso "[N líneas, M únicas]" y guarda la
             respuesta íntegra en "llm_answer_full".

MUESTREO (para CICIDS, donde etiquetar todo es inviable):
  --sample K        activa el muestreo: K preguntas CON referencia no vacía por cada
                    celda (modelo, nivel), más --sample-empty E con referencia vacía
                    (por defecto 1). Las preguntas elegidas son LAS MISMAS en las dos
                    vistas (general y filtered), para poder comparar el efecto del
                    filtrado. La selección no usa la etiqueta del juez.
  --runs 1 2 3 4 5  rondas entre las que se elige, para cada celda (modelo, nivel), UNA
                    ronda al azar (la misma para las dos vistas). Cubre así ventanas
                    distintas.
  --seed N          semilla (por defecto 2026): misma muestra siempre.
  --max-gt-lines N  excluye (de las preguntas con contenido) las que tengan una
                    referencia de más de N líneas (por defecto 0 = sin límite).
  Las preguntas NO elegidas se conservan en el fichero (para que su número de pregunta
  y su capa no cambien) pero con manual_label = "SKIP": no hay que etiquetarlas.
  Se guarda <out>/sample_manifest.json con lo elegido.

Los originales no se tocan. Salida: <out>/<modelo>/<vista>/<fichero>.json

Uso (desde la raíz del proyecto):
  # lo de siempre (una ronda completa, p. ej. las trazas básicas)
  python3 src/comparison/preprocesses_manual.py --models-dir <models> --run run1 --out <salida> --blind --manual --compact
  # muestra de CICIDS: 4 preguntas por modelo y nivel (3 con contenido + 1 vacía), una ronda al azar por celda
  python3 src/comparison/preprocesses_manual.py --models-dir <models> --runs 1 2 3 4 5 --sample 3 --sample-empty 1 \
      --out <salida> --blind --manual --compact
================================================================================
"""
import argparse
import glob
import json
import os
import random
import re

DEFAULT_MODELS_DIR = "results/snapshots/06-10-2026/basic/temp_0.0/models"


def lines(s):
    return [l.strip() for l in str(s).splitlines() if l.strip()]


def gt_empty(gt):
    ls = lines(gt)
    return bool(ls) and (ls[-1].lower().endswith("none") or ls[0].lower().startswith("no "))


def compact_answer(text: str):
    """Devuelve (texto_condensado, cambió). Conserva el orden de las líneas únicas."""
    ls = [l for l in str(text).splitlines() if l.strip()]
    seen, uniq = set(), []
    for l in ls:
        if l not in seen:
            seen.add(l)
            uniq.append(l)
    if len(uniq) == len(ls):
        return text, False
    return f"[{len(ls)} líneas, {len(uniq)} únicas]\n" + "\n".join(uniq), True


def reduce_question(v: dict, blind: bool, manual: bool, compact: bool) -> dict:
    out = {}
    for k, val in v.items():
        if k == "final_label":
            if not blind:
                out[k] = val
            break
        out[k] = val
    if compact and "llm_answer" in out:
        new, changed = compact_answer(out["llm_answer"])
        if changed:
            out["llm_answer_full"] = out["llm_answer"]
            out["llm_answer"] = new
    if manual:
        out["manual_label"] = ""
        out["notes"] = ""
    return out


def reduce_file(data: dict, blind, manual, compact, keep=None):
    """keep = None: todas las preguntas; si no, conjunto de preguntas a etiquetar (las demás, SKIP)."""
    red = {}
    for k, val in data.items():
        if k == "questions":
            continue
        if blind and k in ("summary", "judge_model"):
            continue
        red[k] = val
    qs = {}
    for q, v in data["questions"].items():
        if keep is None or q in keep:
            qs[q] = reduce_question(v, blind, manual, compact)
        else:
            qs[q] = {"question": v.get("question", q), "manual_label": "SKIP", "notes": ""}
    red["questions"] = qs
    return red


def level_of(path):
    m = re.search(r"_L(\d+)_", os.path.basename(path))
    return int(m.group(1)) if m else None


def choose_questions(general_data, k, e, max_gt_lines, rng):
    """K preguntas con referencia no vacía + E con referencia vacía (si no hay bastantes, se completa con otras)."""
    items = [(q, v.get("gt_answer", "")) for q, v in general_data["questions"].items()]
    content = [q for q, gt in items if not gt_empty(gt) and (max_gt_lines <= 0 or len(lines(gt)) <= max_gt_lines)]
    empty = [q for q, gt in items if gt_empty(gt)]
    chosen = rng.sample(content, min(k, len(content)))
    want_empty = e + (k - len(chosen))                    # si faltan con contenido, se completa con vacías
    chosen += rng.sample(empty, min(want_empty, len(empty)))
    rest = [q for q, _ in items if q not in chosen]
    if len(chosen) < k + e:
        chosen += rng.sample(rest, min(k + e - len(chosen), len(rest)))
    return set(chosen)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", required=True, help="Carpeta con <modelo>/<run>/comparison/judge/<vista>/judge_*.json")
    ap.add_argument("--run", default="run1", help="Ronda a procesar (por defecto run1); ignorado si se usa --runs")
    ap.add_argument("--runs", type=int, nargs="*", default=None, help="Rondas entre las que muestrear (con --sample)")
    ap.add_argument("--out", required=True, help="Carpeta de salida")
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--manual", action="store_true")
    ap.add_argument("--compact", action="store_true")
    ap.add_argument("--sample", type=int, default=0, help="K preguntas con contenido por celda (modelo, nivel); 0 = sin muestreo")
    ap.add_argument("--sample-empty", type=int, default=1, help="E preguntas con referencia vacía por celda (por defecto 1)")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--max-gt-lines", type=int, default=0, help="excluye referencias de más de N líneas (0 = sin límite)")
    args = ap.parse_args()

    runs = [f"run{r}" for r in args.runs] if (args.sample and args.runs) else [args.run]
    files = []
    for r in runs:
        pattern = os.path.join(args.models_dir, "*", r, "comparison", "judge", "*", "judge_*_answers.json")
        files += sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No se han encontrado ficheros con el patrón:\n  {pattern}\n¿Estás en la raíz del proyecto?")

    def meta(f):
        p = f.split(os.sep)
        return p[-6], p[-5], p[-2]          # modelo, ronda, vista

    plan = []                                # (fichero, claves a etiquetar o None)
    manifest = []
    if args.sample:
        cells = {}
        for f in files:
            model, run, view = meta(f)
            cells.setdefault((model, level_of(f)), {}).setdefault(run, {})[view] = f
        for (model, level), by_run in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
            rng = random.Random(f"{args.seed}|{model}|{level}")
            run = rng.choice(sorted(r for r, v in by_run.items() if "general" in v and "filtered" in v) or sorted(by_run))
            views = by_run[run]
            ref = views.get("general") or next(iter(views.values()))
            chosen = choose_questions(json.load(open(ref, encoding="utf-8")), args.sample, args.sample_empty, args.max_gt_lines, rng)
            for view, f in sorted(views.items()):
                plan.append((f, chosen))
            qlist = list(json.load(open(ref, encoding="utf-8"))["questions"])
            manifest.append(dict(model=model, run=run, level=level, views=sorted(views),
                                 question_numbers=sorted(qlist.index(q) + 1 for q in chosen)))
    else:
        plan = [(f, None) for f in files]

    n_files = n_label = 0
    for f, keep in plan:
        model, run, mode = meta(f)
        data = json.load(open(f, encoding="utf-8"))
        red = reduce_file(data, args.blind, args.manual, args.compact, keep)
        dst_dir = os.path.join(args.out, model.replace(":", "_"), mode)
        os.makedirs(dst_dir, exist_ok=True)
        with open(os.path.join(dst_dir, os.path.basename(f)), "w", encoding="utf-8") as g:
            json.dump(red, g, indent=4, ensure_ascii=False)
        n_files += 1
        n_label += len(red["questions"]) if keep is None else len(keep)

    if args.sample:
        with open(os.path.join(args.out, "sample_manifest.json"), "w", encoding="utf-8") as g:
            json.dump(dict(seed=args.seed, sample=args.sample, sample_empty=args.sample_empty, runs=args.runs,
                           max_gt_lines=args.max_gt_lines, cells=manifest), g, indent=2)
    print(f"{n_files} ficheros, {n_label} preguntas para etiquetar -> {args.out}")
    print(f"opciones: blind={args.blind} manual={args.manual} compact={args.compact} sample={args.sample}")


if __name__ == "__main__":
    main()