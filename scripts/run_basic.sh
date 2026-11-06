#!/usr/bin/env bash
set -Eeuo pipefail

RUNS="${RUNS:-5}"
JUDGE="${JUDGE:-llama3.3:70b}"
read -r -a MODELS <<< "${MODELS:-llama3.1:8b llama3.1:70b qwen2.5:7b qwen2.5:72b}"
PIPE="uv run python -m llms_understand_network_traces.pipeline"

$PIPE gt --dataset basic
for model in "${MODELS[@]}"; do
  $PIPE llm --dataset basic --model "$model" --runs "$RUNS"
done
for model in "${MODELS[@]}"; do
  $PIPE judge --dataset basic --model "$model" --judge "$JUDGE" --runs "$RUNS"
  $PIPE dotplot --dataset basic --model "$model" --runs "$RUNS"
done
