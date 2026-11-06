#!/usr/bin/env bash
set -Eeuo pipefail
export MPLBACKEND=Agg

OUT="${1:-results/reproduced}"
BASIC=results/basic
CICIDS=results/cicids
MANUAL=results/manual
MODELS=(llama3.1:8b llama3.1:70b qwen2.5:7b qwen2.5:72b)
RUN="uv run python -m llms_understand_network_traces"

for dir in "$BASIC" "$CICIDS" "$MANUAL/basic" "$MANUAL/cicids"; do
  [ -d "$dir" ] || { echo "missing folder: $dir (run from the repository root)"; exit 1; }
done
mkdir -p "$OUT"/{metrics,figures/basic_by_run,figures/basic_mode,figures/basic_manual,figures/cicids_mode,figures/cicids_consistency,validation}

echo "[1/6] metrics"
$RUN.analysis.metrics --dataset basic --models-dir "$BASIC" --out-dir "$OUT/metrics" --tag _basic > "$OUT/metrics/log_basic.txt"
$RUN.analysis.metrics --dataset cicids --models-dir "$CICIDS" --out-dir "$OUT/metrics" --tag _cicids > "$OUT/metrics/log_cicids.txt"

echo "[2/6] basic scenario: one dotplot per model and run"
for model in "${MODELS[@]}"; do
  for run in 1 2 3 4 5; do
    judge="$BASIC/$model/run$run/comparison/judge"
    $RUN.analysis.dotplot --general-folder "$judge/general" --filtered-folder "$judge/filtered" \
      --output "$OUT/figures/basic_by_run/dotplot_${model//:/_}_run$run.png" --method "LLM-Judge | $model run$run"
  done
done

echo "[3/6] basic scenario: modal label over runs"
$RUN.analysis.dotplot_model --models-dir "$BASIC" --output-dir "$OUT/figures/basic_mode"

echo "[4/6] basic scenario: manual labels"
for model in "${MODELS[@]}"; do
  slug="${model//:/_}"
  $RUN.analysis.dotplot --general-folder "$MANUAL/basic/$slug/general" --filtered-folder "$MANUAL/basic/$slug/filtered" \
    --label-key manual_label --output "$OUT/figures/basic_manual/dotplot_manual_$slug.png" --method "Manual labels | $model"
done

echo "[5/6] CIC-IDS2017 figures"
$RUN.analysis.dotplot_cicids --models-dir "$CICIDS" --output-dir "$OUT/figures/cicids_mode"
$RUN.analysis.graph_cicids --models-dir "$CICIDS" --output-dir "$OUT/figures/cicids_consistency"

echo "[6/6] judge vs. manual annotations"
$RUN.comparison.compare_manual --manual-dir "$MANUAL/basic" --judge-dir "$BASIC" --run run1 \
  --out-dir "$OUT/validation/basic" > /dev/null
$RUN.comparison.compare_manual --manual-dir "$MANUAL/cicids" --judge-dir "$CICIDS" --run run1 \
  --out-dir "$OUT/validation/cicids" > /dev/null

echo "Done. Everything is in $OUT"
