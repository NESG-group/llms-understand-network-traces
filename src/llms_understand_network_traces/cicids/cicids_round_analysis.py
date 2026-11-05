"""
cicids_status.py
================================================================================
Read-only status of every CIC-IDS2017 model and run: how many files exist for
each stage and when the last one was touched.

  GT       reference answers per level            (expected 4/4)
  LLM      answers: 4 levels x 2 views            (expected 8/8)
  judge    judgements: 4 levels x 2 views         (expected 8/8)
  dotplot  figure of the model and run            (expected 1/1)

A run is finished for a model when it shows 4/4, 8/8, 8/8 and 1/1.

Usage (from the repository root):
  uv run python -m llms_understand_network_traces.cicids.cicids_status 2
  uv run python -m llms_understand_network_traces.cicids.cicids_status 1 2
  uv run python -m llms_understand_network_traces.cicids.cicids_status
================================================================================
"""
import json
import os
import sys
import time

MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]


def main() -> None:
    if any(arg in ("-h", "--help") for arg in sys.argv[1:]):
        print(__doc__)
        return
    runs = [int(x) for x in sys.argv[1:]] or [1, 2, 3, 4, 5]
    explicit = bool(sys.argv[1:])
    stamp = lambda t: time.strftime("%d/%m %H:%M", time.localtime(t))
    cnt = lambda paths: sum(os.path.exists(p) for p in paths)
    print(f"{'model':<13}{'run':>5}  {'GT':>5}  {'LLM':>5}  {'judge':>5}  {'dotplot':>7}  last modified")
    for run in runs:
        for model in MODELS:
            man = f"data/cicids2017/staging/{model.replace(':', '-')}_run{run}/manifest.json"
            if not os.path.exists(man):
                if explicit:
                    print(f"{model:<13}{run:>5}  not prepared ({man} does not exist)")
                continue
            with open(man) as handle:
                stems = [level["stem"] for level in json.load(handle)["levels"]]
            base = f"results/models/{model}/run{run}"
            gt = [f"results/ground_truth_cicids2017/{s}_answers.json" for s in stems]
            llm = [f"{base}/llm_answers/{m}/{s}_answers.json" for s in stems for m in ("general", "filtered")]
            jd = [f"{base}/comparison/judge/{m}/judge_{s}_answers.json" for s in stems for m in ("general", "filtered")]
            dp = [f"{base}/dotplot_judge.png"]
            existing = [p for p in gt + llm + jd + dp + [man] if os.path.exists(p)]
            last = max(os.path.getmtime(p) for p in existing)
            print(f"{model:<13}{run:>5}  {cnt(gt)}/{len(gt)}  {cnt(llm)}/{len(llm)}  {cnt(jd)}/{len(jd)}  {cnt(dp)}/1{'':>5}  {stamp(last)}")


if __name__ == "__main__":
    main()
    