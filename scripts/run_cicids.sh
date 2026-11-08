#!/usr/bin/env bash
# Runs the CIC-IDS2017 scenario end to end for every answering model: reference answers,
# model answers, judging and dotplots. Needs Ollama; see the README.
# Override with RUNS, JUDGE, MODELS (space-separated) and SOURCE (the 50,000-packet capture).
# PREPARE controls the window building: auto (only the missing ones), 1 (always) or 0 (never).
set -Eeuo pipefail

RUNS="${RUNS:-5}"
JUDGE="${JUDGE:-llama3.3:70b}"
SOURCE="${SOURCE:-data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng}"
PREPARE="${PREPARE:-auto}"   # auto: build windows only if missing; 1: always rebuild; 0: never
read -r -a MODELS <<< "${MODELS:-llama3.1:8b llama3.1:70b qwen2.5:7b qwen2.5:72b}"
PIPE="uv run python -m llms_understand_network_traces.pipeline"

windows_missing() {   # true if some run of the model has no manifest yet
  for run in $(seq 1 "$RUNS"); do
    [ -f "data/traces/raw/cicids/${1//:/-}_run$run/manifest.json" ] || return 0
  done
  return 1
}

for model in "${MODELS[@]}"; do
  if [ "$PREPARE" = 1 ] || { [ "$PREPARE" = auto ] && windows_missing "$model"; }; then
    [ -f "$SOURCE" ] || { echo "missing $SOURCE (run scripts/download_cicids2017.sh)"; exit 1; }
    $PIPE prepare --dataset cicids --model "$model" --first-run 1 --runs "$RUNS" --source "$SOURCE"
  fi
  $PIPE gt --dataset cicids --model "$model" --first-run 1 --runs "$RUNS"
done
for model in "${MODELS[@]}"; do
  $PIPE llm --dataset cicids --model "$model" --first-run 1 --runs "$RUNS"
done
for model in "${MODELS[@]}"; do
  $PIPE judge --dataset cicids --model "$model" --judge "$JUDGE" --first-run 1 --runs "$RUNS"
  $PIPE dotplot --dataset cicids --model "$model" --first-run 1 --runs "$RUNS"
done
