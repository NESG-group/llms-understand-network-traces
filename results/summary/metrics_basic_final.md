# Metrics — dataset: basic

Runs: [1, 2, 3, 4, 5]. Pairing: mode. Tie-break for modal labels: C/P/I.

## 0. Files read

| Model | Runs | General files | Filtered files | Questions absent |
|---|---|---|---|---|
| llama3.1:70b | [1, 2, 3, 4, 5] | 20 | 20 | 0 |
| llama3.1:8b | [1, 2, 3, 4, 5] | 20 | 20 | 0 |
| qwen2.5:72b | [1, 2, 3, 4, 5] | 20 | 20 | 0 |
| qwen2.5:7b | [1, 2, 3, 4, 5] | 20 | 20 | 0 |

## 1. Answer correctness (% of answers, mean ± sd across runs)

| Model | View | Group | %C | %P | %I | Runs | Valid answers |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | general | all traces | 65.8 ± 0.0 | 19.4 ± 0.6 | 14.8 ± 0.6 | 5 | 380 |
| llama3.1:70b | filtered | all traces | 57.9 ± 0.0 | 17.1 ± 0.0 | 25.0 ± 0.0 | 5 | 380 |
| llama3.1:8b | general | all traces | 44.7 ± 0.0 | 31.9 ± 0.6 | 23.4 ± 0.6 | 5 | 380 |
| llama3.1:8b | filtered | all traces | 28.9 ± 0.0 | 30.3 ± 0.0 | 40.8 ± 0.0 | 5 | 380 |
| qwen2.5:72b | general | all traces | 60.5 ± 0.0 | 25.0 ± 0.0 | 14.5 ± 0.0 | 5 | 380 |
| qwen2.5:72b | filtered | all traces | 64.5 ± 0.0 | 23.7 ± 0.0 | 11.8 ± 0.0 | 5 | 380 |
| qwen2.5:7b | general | all traces | 45.0 ± 0.6 | 19.4 ± 0.6 | 35.5 ± 0.0 | 5 | 380 |
| qwen2.5:7b | filtered | all traces | 47.4 ± 0.0 | 32.9 ± 0.0 | 19.7 ± 0.0 | 5 | 380 |

## 2. Answer correctness by protocol layer of the question (mean ± sd across runs)

| Model | View | Group | Layer | %C | %P | %I |
|---|---|---|---|---|---|---|
| llama3.1:70b | general | all traces | ARP | 75.0 ± 0.0 | 23.3 ± 3.7 | 1.7 ± 3.7 |
| llama3.1:70b | general | all traces | IP | 62.5 ± 0.0 | 37.5 ± 0.0 | 0.0 ± 0.0 |
| llama3.1:70b | general | all traces | TCP/UDP | 64.6 ± 0.0 | 12.5 ± 0.0 | 22.9 ± 0.0 |
| llama3.1:70b | filtered | all traces | ARP | 58.3 ± 0.0 | 33.3 ± 0.0 | 8.3 ± 0.0 |
| llama3.1:70b | filtered | all traces | IP | 75.0 ± 0.0 | 25.0 ± 0.0 | 0.0 ± 0.0 |
| llama3.1:70b | filtered | all traces | TCP/UDP | 52.1 ± 0.0 | 10.4 ± 0.0 | 37.5 ± 0.0 |
| llama3.1:8b | general | all traces | ARP | 50.0 ± 0.0 | 41.7 ± 0.0 | 8.3 ± 0.0 |
| llama3.1:8b | general | all traces | IP | 31.2 ± 0.0 | 43.8 ± 0.0 | 25.0 ± 0.0 |
| llama3.1:8b | general | all traces | TCP/UDP | 47.9 ± 0.0 | 25.4 ± 0.9 | 26.7 ± 0.9 |
| llama3.1:8b | filtered | all traces | ARP | 16.7 ± 0.0 | 50.0 ± 0.0 | 33.3 ± 0.0 |
| llama3.1:8b | filtered | all traces | IP | 43.8 ± 0.0 | 37.5 ± 0.0 | 18.8 ± 0.0 |
| llama3.1:8b | filtered | all traces | TCP/UDP | 27.1 ± 0.0 | 22.9 ± 0.0 | 50.0 ± 0.0 |
| qwen2.5:72b | general | all traces | ARP | 75.0 ± 0.0 | 25.0 ± 0.0 | 0.0 ± 0.0 |
| qwen2.5:72b | general | all traces | IP | 50.0 ± 0.0 | 43.8 ± 0.0 | 6.2 ± 0.0 |
| qwen2.5:72b | general | all traces | TCP/UDP | 60.4 ± 0.0 | 18.8 ± 0.0 | 20.8 ± 0.0 |
| qwen2.5:72b | filtered | all traces | ARP | 66.7 ± 0.0 | 33.3 ± 0.0 | 0.0 ± 0.0 |
| qwen2.5:72b | filtered | all traces | IP | 75.0 ± 0.0 | 25.0 ± 0.0 | 0.0 ± 0.0 |
| qwen2.5:72b | filtered | all traces | TCP/UDP | 60.4 ± 0.0 | 20.8 ± 0.0 | 18.8 ± 0.0 |
| qwen2.5:7b | general | all traces | ARP | 58.3 ± 0.0 | 0.0 ± 0.0 | 41.7 ± 0.0 |
| qwen2.5:7b | general | all traces | IP | 43.8 ± 0.0 | 18.8 ± 0.0 | 37.5 ± 0.0 |
| qwen2.5:7b | general | all traces | TCP/UDP | 42.1 ± 0.9 | 24.6 ± 0.9 | 33.3 ± 0.0 |
| qwen2.5:7b | filtered | all traces | ARP | 41.7 ± 0.0 | 41.7 ± 0.0 | 16.7 ± 0.0 |
| qwen2.5:7b | filtered | all traces | IP | 68.8 ± 0.0 | 25.0 ± 0.0 | 6.2 ± 0.0 |
| qwen2.5:7b | filtered | all traces | TCP/UDP | 41.7 ± 0.0 | 33.3 ± 0.0 | 25.0 ± 0.0 |

## 3. Correctness by type of reference answer (pooled over runs)

| Model | View | Group | Reference type | n | %C | %P | %I |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | general | all traces | layer absent | 75 | 100.0 | 0.0 | 0.0 |
| llama3.1:70b | general | all traces | empty reference, layer present | 80 | 62.5 | 0.0 | 37.5 |
| llama3.1:70b | general | all traces | with content | 225 | 55.6 | 32.9 | 11.6 |
| llama3.1:70b | filtered | all traces | layer absent | 75 | 40.0 | 0.0 | 60.0 |
| llama3.1:70b | filtered | all traces | empty reference, layer present | 80 | 56.2 | 0.0 | 43.8 |
| llama3.1:70b | filtered | all traces | with content | 225 | 64.4 | 28.9 | 6.7 |
| llama3.1:8b | general | all traces | layer absent | 75 | 100.0 | 0.0 | 0.0 |
| llama3.1:8b | general | all traces | empty reference, layer present | 80 | 43.8 | 0.0 | 56.2 |
| llama3.1:8b | general | all traces | with content | 225 | 26.7 | 53.8 | 19.6 |
| llama3.1:8b | filtered | all traces | layer absent | 75 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | filtered | all traces | empty reference, layer present | 80 | 31.2 | 0.0 | 68.8 |
| llama3.1:8b | filtered | all traces | with content | 225 | 37.8 | 51.1 | 11.1 |
| qwen2.5:72b | general | all traces | layer absent | 75 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | general | all traces | empty reference, layer present | 80 | 62.5 | 0.0 | 37.5 |
| qwen2.5:72b | general | all traces | with content | 225 | 46.7 | 42.2 | 11.1 |
| qwen2.5:72b | filtered | all traces | layer absent | 75 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | filtered | all traces | empty reference, layer present | 80 | 56.2 | 0.0 | 43.8 |
| qwen2.5:72b | filtered | all traces | with content | 225 | 55.6 | 40.0 | 4.4 |
| qwen2.5:7b | general | all traces | layer absent | 75 | 100.0 | 0.0 | 0.0 |
| qwen2.5:7b | general | all traces | empty reference, layer present | 80 | 56.2 | 0.0 | 43.8 |
| qwen2.5:7b | general | all traces | with content | 225 | 22.7 | 32.9 | 44.4 |
| qwen2.5:7b | filtered | all traces | layer absent | 75 | 66.7 | 0.0 | 33.3 |
| qwen2.5:7b | filtered | all traces | empty reference, layer present | 80 | 75.0 | 0.0 | 25.0 |
| qwen2.5:7b | filtered | all traces | with content | 225 | 31.1 | 55.6 | 13.3 |

## 4. Effect of filtering (filtered vs general, paired by question)

Δ in percentage points (filtered − general). Improved/worsened = label better/worse in the filtered view. Score: +2 I→C, +1 I→P or P→C, opposite sign if worse, scaled to ±100 %. p: two-sided sign test (indicative).

| Model | Group | Pairs | Δ%C | Δ%P | Δ%I | Improved | Same | Worsened | Score % | p |
|---|---|---|---|---|---|---|---|---|---|---|
| llama3.1:70b | all traces | 76 | -7.9 | -2.6 | +10.5 | 11 | 50 | 15 | -9.2 | 0.557 |
| llama3.1:8b | all traces | 76 | -15.8 | -1.3 | +17.1 | 14 | 37 | 25 | -16.4 | 0.108 |
| qwen2.5:72b | all traces | 76 | +3.9 | -1.3 | -2.6 | 12 | 57 | 7 | +3.3 | 0.359 |
| qwen2.5:7b | all traces | 76 | +2.6 | +13.2 | -15.8 | 21 | 47 | 8 | +9.2 | 0.0241 |

### 4b. By type of reference answer

| Model | Group | Reference type | Pairs | Improved | Same | Worsened | Score % |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | all traces | layer absent | 15 | 0 | 6 | 9 | -60.0 |
| llama3.1:70b | all traces | empty reference, layer present | 16 | 0 | 15 | 1 | -6.2 |
| llama3.1:70b | all traces | with content | 45 | 11 | 29 | 5 | +6.7 |
| llama3.1:8b | all traces | layer absent | 15 | 0 | 0 | 15 | -100.0 |
| llama3.1:8b | all traces | empty reference, layer present | 16 | 0 | 14 | 2 | -12.5 |
| llama3.1:8b | all traces | with content | 45 | 14 | 23 | 8 | +10.0 |
| qwen2.5:72b | all traces | layer absent | 15 | 0 | 15 | 0 | +0.0 |
| qwen2.5:72b | all traces | empty reference, layer present | 16 | 0 | 15 | 1 | -6.2 |
| qwen2.5:72b | all traces | with content | 45 | 12 | 27 | 6 | +7.8 |
| qwen2.5:7b | all traces | layer absent | 15 | 0 | 10 | 5 | -33.3 |
| qwen2.5:7b | all traces | empty reference, layer present | 16 | 3 | 13 | 0 | +18.8 |
| qwen2.5:7b | all traces | with content | 45 | 18 | 24 | 3 | +20.0 |

## 5. Resource use (pooled over runs)

Tokens: mean `tokens_input` of non-truncated prompts (as counted by the inference server; not comparable across model families).

| Model | View | Group | Mean input tokens | % prompts truncated | % outputs cut at token cap | Latency per answer (s) | % judge ties |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | general | all traces | 1,860 | 0.0 | 1.3 | 7.9 | 4.2 |
| llama3.1:70b | filtered | all traces | 659 | 0.0 | 0.0 | 7.6 | 1.3 |
| llama3.1:8b | general | all traces | 1,860 | 0.0 | 2.6 | 1.3 | 6.6 |
| llama3.1:8b | filtered | all traces | 659 | 0.0 | 1.3 | 1.4 | 2.6 |
| qwen2.5:72b | general | all traces | 2,551 | 0.0 | 0.0 | 5.8 | 2.6 |
| qwen2.5:72b | filtered | all traces | 881 | 0.0 | 0.0 | 7.3 | 2.6 |
| qwen2.5:7b | general | all traces | 2,551 | 0.0 | 0.0 | 0.4 | 7.6 |
| qwen2.5:7b | filtered | all traces | 881 | 0.0 | 0.0 | 0.5 | 1.3 |

## 6. Token reduction of the filtered prompt vs the general prompt (per question)

Excludes truncated prompts and questions whose layer is empty. Each filtered prompt is compared with the mean general prompt of the same trace/window. Negative reduction = filtered prompt larger.

| Model | Group | Questions | Mean % | Median % | Min % | Max % | Filtered ≥ general |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | all traces | 305 | 60.0 | 68.3 | 3.0 | 85.5 | 0 |
| llama3.1:8b | all traces | 305 | 60.0 | 68.3 | 3.0 | 85.5 | 0 |
| qwen2.5:72b | all traces | 305 | 60.7 | 69.4 | 3.7 | 85.8 | 0 |
| qwen2.5:7b | all traces | 305 | 60.7 | 69.4 | 3.7 | 85.8 | 0 |

## 7. Stability across runs (same traces repeated)

| Model | View | Runs | Questions | % unanimous | % ≥80 % agree |
|---|---|---|---|---|---|
| llama3.1:70b | general | 5 | 76 | 98.7 | 100.0 |
| llama3.1:70b | filtered | 5 | 76 | 100.0 | 100.0 |
| llama3.1:8b | general | 5 | 76 | 98.7 | 100.0 |
| llama3.1:8b | filtered | 5 | 76 | 100.0 | 100.0 |
| qwen2.5:72b | general | 5 | 76 | 100.0 | 100.0 |
| qwen2.5:72b | filtered | 5 | 76 | 100.0 | 100.0 |
| qwen2.5:7b | general | 5 | 76 | 98.7 | 100.0 |
| qwen2.5:7b | filtered | 5 | 76 | 100.0 | 100.0 |
