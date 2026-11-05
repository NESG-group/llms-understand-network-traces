#!/usr/bin/env python3
"""
cicids_status.py
================================================================================
Estado de cada modelo y ronda de CICIDS (solo lectura): cuántos ficheros hay de
cada etapa y cuándo se tocó lo último.

  GT      ground truth por nivel          (esperado 4/4)
  LLM     respuestas: 4 niveles x 2 vistas (esperado 8/8)
  juez    juicios:    4 niveles x 2 vistas (esperado 8/8)
  dotplot figura del modelo y la ronda     (esperado 1/1)

Una ronda está terminada para un modelo cuando sale 4/4, 8/8, 8/8 y 1/1.

Uso (desde la raíz del proyecto):
  python3 cicids_status.py 2          # solo la ronda 2
  python3 cicids_status.py 1 2        # rondas 1 y 2
  python3 cicids_status.py            # rondas 1 a 5
================================================================================
"""
import json
import os
import sys
import time

MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]


def main():
    runs = [int(x) for x in sys.argv[1:]] or [1, 2, 3, 4, 5]
    explicit = bool(sys.argv[1:])
    stamp = lambda t: time.strftime("%d/%m %H:%M", time.localtime(t))
    cnt = lambda paths: sum(os.path.exists(p) for p in paths)
    print(f"{'modelo':<13}{'ronda':>5}  {'GT':>5}  {'LLM':>5}  {'juez':>5}  {'dotplot':>7}  última modificación")
    for R in runs:
        for M in MODELS:
            man = f"data/cicids2017/staging/{M.replace(':', '-')}_run{R}/manifest.json"
            if not os.path.exists(man):
                if explicit:
                    print(f"{M:<13}{R:>5}  sin preparar (no existe {man})")
                continue
            stems = [l["stem"] for l in json.load(open(man))["levels"]]
            base = f"results/models/{M}/run{R}"
            gt = [f"results/ground_truth_cicids2017/{s}_answers.json" for s in stems]
            llm = [f"{base}/llm_answers/{m}/{s}_answers.json" for s in stems for m in ("general", "filtered")]
            jd = [f"{base}/comparison/judge/{m}/judge_{s}_answers.json" for s in stems for m in ("general", "filtered")]
            dp = [f"{base}/dotplot_judge.png"]
            existing = [p for p in gt + llm + jd + dp + [man] if os.path.exists(p)]
            last = max(os.path.getmtime(p) for p in existing)
            print(f"{M:<13}{R:>5}  {cnt(gt)}/{len(gt)}  {cnt(llm)}/{len(llm)}  {cnt(jd)}/{len(jd)}  {cnt(dp)}/1{'':>5}  {stamp(last)}")


if __name__ == "__main__":
    main()
