#!/usr/bin/env bash
set -Eeuo pipefail

RUNS="${RUNS:-5}"
JUDGE="${JUDGE:-llama3.3:70b}"
SOURCE="${SOURCE:-data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng}"
read -r -a MODELS <<< "${MODELS:-llama3.1:8b llama3.1:70b qwen2.5:7b qwen2.5:72b}"
PIPE="uv run python -m llms_understand_network_traces.pipeline"

[ -f "$SOURCE" ] || { echo "missing $SOURCE (run scripts/download_cicids2017.sh)"; exit 1; }

for model in "${MODELS[@]}"; do
  $PIPE prepare --dataset cicids --model "$model" --first-run 1 --runs "$RUNS" --source "$SOURCE"
  $PIPE gt --dataset cicids --model "$model" --first-run 1 --runs "$RUNS"
done
for model in "${MODELS[@]}"; do
  $PIPE llm --dataset cicids --model "$model" --first-run 1 --runs "$RUNS"
done
for model in "${MODELS[@]}"; do
  $PIPE judge --dataset cicids --model "$model" --judge "$JUDGE" --first-run 1 --runs "$RUNS"
  $PIPE dotplot --dataset cicids --model "$model" --first-run 1 --runs "$RUNS"
done
