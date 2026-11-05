# Metrics — dataset: cicids

Runs: [1, 2, 3, 4, 5]. Pairing: runs. Tie-break for modal labels: C/P/I.

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
| llama3.1:70b | general | L25–L75 | 13.7 ± 10.0 | 37.9 ± 14.8 | 48.4 ± 6.1 | 5 | 285 |
| llama3.1:70b | general | L100 (125 %) | 11.6 ± 17.6 | 40.0 ± 12.1 | 48.4 ± 11.4 | 5 | 95 |
| llama3.1:70b | filtered | L25–L75 | 21.0 ± 11.6 | 44.2 ± 14.3 | 34.8 ± 5.8 | 5 | 285 |
| llama3.1:70b | filtered | L100 (125 %) | 13.7 ± 12.1 | 47.4 ± 9.8 | 38.9 ± 8.8 | 5 | 95 |
| llama3.1:8b | general | L25–L75 | 4.6 ± 6.6 | 33.7 ± 2.9 | 61.7 ± 5.9 | 5 | 285 |
| llama3.1:8b | general | L100 (125 %) | 5.3 ± 9.1 | 45.3 ± 8.0 | 49.5 ± 7.1 | 5 | 95 |
| llama3.1:8b | filtered | L25–L75 | 6.0 ± 2.9 | 38.2 ± 15.3 | 55.8 ± 13.4 | 5 | 285 |
| llama3.1:8b | filtered | L100 (125 %) | 3.2 ± 2.9 | 34.8 ± 16.9 | 62.1 ± 14.1 | 5 | 95 |
| qwen2.5:72b | general | L25–L75 | 47.3 ± 11.4 | 26.7 ± 6.1 | 26.0 ± 5.4 | 5 | 285 |
| qwen2.5:72b | general | L100 (125 %) | 29.5 ± 21.6 | 31.6 ± 8.3 | 39.0 ± 15.2 | 5 | 95 |
| qwen2.5:72b | filtered | L25–L75 | 52.6 ± 10.5 | 28.1 ± 5.3 | 19.3 ± 6.5 | 5 | 285 |
| qwen2.5:72b | filtered | L100 (125 %) | 36.8 ± 13.4 | 35.8 ± 8.6 | 27.4 ± 8.6 | 5 | 95 |
| qwen2.5:7b | general | L25–L75 | 29.5 ± 20.9 | 20.7 ± 8.3 | 49.8 ± 13.2 | 5 | 285 |
| qwen2.5:7b | general | L100 (125 %) | 17.9 ± 24.6 | 33.7 ± 10.9 | 48.4 ± 16.0 | 5 | 95 |
| qwen2.5:7b | filtered | L25–L75 | 30.2 ± 13.3 | 34.0 ± 11.9 | 35.8 ± 8.2 | 5 | 285 |
| qwen2.5:7b | filtered | L100 (125 %) | 23.2 ± 17.7 | 32.6 ± 12.6 | 44.2 ± 9.6 | 5 | 95 |

## 2. Answer correctness by protocol layer of the question (mean ± sd across runs)

| Model | View | Group | Layer | %C | %P | %I |
|---|---|---|---|---|---|---|
| llama3.1:70b | general | L25–L75 | ARP | 24.4 ± 29.8 | 28.9 ± 21.6 | 46.7 ± 14.5 |
| llama3.1:70b | general | L25–L75 | IP | 3.3 ± 7.5 | 63.3 ± 9.5 | 33.3 ± 5.9 |
| llama3.1:70b | general | L25–L75 | TCP/UDP | 14.4 ± 7.5 | 31.6 ± 17.0 | 53.9 ± 10.1 |
| llama3.1:70b | general | L100 (125 %) | ARP | 13.3 ± 29.8 | 53.4 ± 29.8 | 33.3 ± 0.0 |
| llama3.1:70b | general | L100 (125 %) | IP | 5.0 ± 11.2 | 65.0 ± 28.5 | 30.0 ± 32.6 |
| llama3.1:70b | general | L100 (125 %) | TCP/UDP | 13.3 ± 17.3 | 28.3 ± 17.3 | 58.3 ± 15.6 |
| llama3.1:70b | filtered | L25–L75 | ARP | 33.3 ± 11.1 | 33.3 ± 31.4 | 33.3 ± 23.6 |
| llama3.1:70b | filtered | L25–L75 | IP | 21.7 ± 9.5 | 63.3 ± 19.2 | 15.0 ± 10.9 |
| llama3.1:70b | filtered | L25–L75 | TCP/UDP | 17.8 ± 14.9 | 40.6 ± 11.5 | 41.7 ± 7.9 |
| llama3.1:70b | filtered | L100 (125 %) | ARP | 33.3 ± 0.0 | 53.4 ± 29.8 | 13.3 ± 29.8 |
| llama3.1:70b | filtered | L100 (125 %) | IP | 10.0 ± 13.7 | 45.0 ± 32.6 | 45.0 ± 44.7 |
| llama3.1:70b | filtered | L100 (125 %) | TCP/UDP | 10.0 ± 14.9 | 46.7 ± 13.9 | 43.4 ± 3.7 |
| llama3.1:8b | general | L25–L75 | ARP | 11.1 ± 19.2 | 17.8 ± 16.8 | 71.1 ± 12.7 |
| llama3.1:8b | general | L25–L75 | IP | 3.3 ± 7.5 | 58.3 ± 20.4 | 38.3 ± 23.3 |
| llama3.1:8b | general | L25–L75 | TCP/UDP | 3.3 ± 3.6 | 29.4 ± 3.7 | 67.2 ± 3.6 |
| llama3.1:8b | general | L100 (125 %) | ARP | 13.3 ± 29.8 | 46.7 ± 29.8 | 40.0 ± 14.9 |
| llama3.1:8b | general | L100 (125 %) | IP | 0.0 ± 0.0 | 65.0 ± 28.5 | 35.0 ± 28.5 |
| llama3.1:8b | general | L100 (125 %) | TCP/UDP | 5.0 ± 7.5 | 38.3 ± 15.1 | 56.7 ± 10.9 |
| llama3.1:8b | filtered | L25–L75 | ARP | 6.7 ± 9.9 | 40.0 ± 33.9 | 53.3 ± 33.7 |
| llama3.1:8b | filtered | L25–L75 | IP | 5.0 ± 7.5 | 53.3 ± 16.2 | 41.7 ± 21.2 |
| llama3.1:8b | filtered | L25–L75 | TCP/UDP | 6.1 ± 6.3 | 32.8 ± 14.9 | 61.1 ± 8.8 |
| llama3.1:8b | filtered | L100 (125 %) | ARP | 0.0 ± 0.0 | 60.0 ± 43.5 | 40.0 ± 43.5 |
| llama3.1:8b | filtered | L100 (125 %) | IP | 0.0 ± 0.0 | 30.0 ± 41.1 | 70.0 ± 41.1 |
| llama3.1:8b | filtered | L100 (125 %) | TCP/UDP | 5.0 ± 4.5 | 30.0 ± 15.1 | 65.0 ± 10.9 |
| qwen2.5:72b | general | L25–L75 | ARP | 84.5 ± 16.8 | 13.3 ± 18.2 | 2.2 ± 5.0 |
| qwen2.5:72b | general | L25–L75 | IP | 28.3 ± 15.2 | 61.7 ± 7.5 | 10.0 ± 10.9 |
| qwen2.5:72b | general | L25–L75 | TCP/UDP | 44.4 ± 9.2 | 18.3 ± 4.2 | 37.2 ± 5.4 |
| qwen2.5:72b | general | L100 (125 %) | ARP | 40.0 ± 54.8 | 0.0 ± 0.0 | 60.0 ± 54.8 |
| qwen2.5:72b | general | L100 (125 %) | IP | 20.0 ± 11.2 | 55.0 ± 20.9 | 25.0 ± 17.7 |
| qwen2.5:72b | general | L100 (125 %) | TCP/UDP | 30.0 ± 22.5 | 31.7 ± 18.1 | 38.4 ± 7.5 |
| qwen2.5:72b | filtered | L25–L75 | ARP | 68.9 ± 33.7 | 17.8 ± 16.8 | 13.3 ± 18.2 |
| qwen2.5:72b | filtered | L25–L75 | IP | 43.3 ± 12.3 | 56.7 ± 12.3 | 0.0 ± 0.0 |
| qwen2.5:72b | filtered | L25–L75 | TCP/UDP | 51.7 ± 10.1 | 21.1 ± 5.4 | 27.2 ± 7.7 |
| qwen2.5:72b | filtered | L100 (125 %) | ARP | 66.7 ± 33.4 | 20.0 ± 18.2 | 13.3 ± 18.2 |
| qwen2.5:72b | filtered | L100 (125 %) | IP | 30.0 ± 11.2 | 55.0 ± 11.2 | 15.0 ± 13.7 |
| qwen2.5:72b | filtered | L100 (125 %) | TCP/UDP | 31.7 ± 10.9 | 33.3 ± 10.2 | 35.0 ± 7.0 |
| qwen2.5:7b | general | L25–L75 | ARP | 55.6 ± 47.8 | 11.1 ± 15.7 | 33.3 ± 33.4 |
| qwen2.5:7b | general | L25–L75 | IP | 5.0 ± 11.2 | 43.4 ± 18.1 | 51.6 ± 10.9 |
| qwen2.5:7b | general | L25–L75 | TCP/UDP | 31.1 ± 19.4 | 15.5 ± 6.9 | 53.3 ± 13.6 |
| qwen2.5:7b | general | L100 (125 %) | ARP | 40.0 ± 54.8 | 0.0 ± 0.0 | 60.0 ± 54.8 |
| qwen2.5:7b | general | L100 (125 %) | IP | 0.0 ± 0.0 | 65.0 ± 22.4 | 35.0 ± 22.4 |
| qwen2.5:7b | general | L100 (125 %) | TCP/UDP | 18.3 ± 25.3 | 31.7 ± 18.1 | 50.0 ± 8.3 |
| qwen2.5:7b | filtered | L25–L75 | ARP | 48.9 ± 16.9 | 24.4 ± 27.7 | 26.6 ± 14.9 |
| qwen2.5:7b | filtered | L25–L75 | IP | 16.7 ± 21.2 | 61.7 ± 26.1 | 21.7 ± 9.5 |
| qwen2.5:7b | filtered | L25–L75 | TCP/UDP | 30.0 ± 10.3 | 27.2 ± 8.2 | 42.8 ± 11.2 |
| qwen2.5:7b | filtered | L100 (125 %) | ARP | 46.7 ± 18.3 | 26.7 ± 27.9 | 26.6 ± 14.9 |
| qwen2.5:7b | filtered | L100 (125 %) | IP | 25.0 ± 17.7 | 45.0 ± 27.4 | 30.0 ± 11.2 |
| qwen2.5:7b | filtered | L100 (125 %) | TCP/UDP | 16.7 ± 19.6 | 30.0 ± 7.5 | 53.3 ± 17.3 |

## 3. Correctness by type of reference answer (pooled over runs)

| Model | View | Group | Reference type | n | %C | %P | %I |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | general | L25–L75 | layer absent | 15 | 60.0 | 0.0 | 40.0 |
| llama3.1:70b | general | L25–L75 | empty reference, layer present | 54 | 40.7 | 0.0 | 59.3 |
| llama3.1:70b | general | L25–L75 | with content | 216 | 3.7 | 50.0 | 46.3 |
| llama3.1:70b | general | L100 (125 %) | layer absent | 3 | 66.7 | 0.0 | 33.3 |
| llama3.1:70b | general | L100 (125 %) | empty reference, layer present | 17 | 35.3 | 0.0 | 64.7 |
| llama3.1:70b | general | L100 (125 %) | with content | 75 | 4.0 | 50.7 | 45.3 |
| llama3.1:70b | filtered | L25–L75 | layer absent | 15 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | filtered | L25–L75 | empty reference, layer present | 54 | 25.9 | 0.0 | 74.1 |
| llama3.1:70b | filtered | L25–L75 | with content | 216 | 19.0 | 58.3 | 22.7 |
| llama3.1:70b | filtered | L100 (125 %) | layer absent | 3 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | filtered | L100 (125 %) | empty reference, layer present | 17 | 23.5 | 0.0 | 76.5 |
| llama3.1:70b | filtered | L100 (125 %) | with content | 75 | 10.7 | 60.0 | 29.3 |
| llama3.1:8b | general | L25–L75 | layer absent | 15 | 20.0 | 0.0 | 80.0 |
| llama3.1:8b | general | L25–L75 | empty reference, layer present | 54 | 7.4 | 0.0 | 92.6 |
| llama3.1:8b | general | L25–L75 | with content | 216 | 2.8 | 44.4 | 52.8 |
| llama3.1:8b | general | L100 (125 %) | layer absent | 3 | 66.7 | 0.0 | 33.3 |
| llama3.1:8b | general | L100 (125 %) | empty reference, layer present | 17 | 11.8 | 0.0 | 88.2 |
| llama3.1:8b | general | L100 (125 %) | with content | 75 | 1.3 | 57.3 | 41.3 |
| llama3.1:8b | filtered | L25–L75 | layer absent | 15 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | filtered | L25–L75 | empty reference, layer present | 54 | 14.8 | 0.0 | 85.2 |
| llama3.1:8b | filtered | L25–L75 | with content | 216 | 4.2 | 50.5 | 45.4 |
| llama3.1:8b | filtered | L100 (125 %) | layer absent | 3 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | filtered | L100 (125 %) | empty reference, layer present | 17 | 17.6 | 0.0 | 82.4 |
| llama3.1:8b | filtered | L100 (125 %) | with content | 75 | 0.0 | 44.0 | 56.0 |
| qwen2.5:72b | general | L25–L75 | layer absent | 33 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | general | L25–L75 | empty reference, layer present | 66 | 63.6 | 0.0 | 36.4 |
| qwen2.5:72b | general | L25–L75 | with content | 186 | 32.3 | 40.9 | 26.9 |
| qwen2.5:72b | general | L100 (125 %) | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | general | L100 (125 %) | empty reference, layer present | 21 | 71.4 | 0.0 | 28.6 |
| qwen2.5:72b | general | L100 (125 %) | with content | 68 | 10.3 | 44.1 | 45.6 |
| qwen2.5:72b | filtered | L25–L75 | layer absent | 33 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | filtered | L25–L75 | empty reference, layer present | 66 | 56.1 | 0.0 | 43.9 |
| qwen2.5:72b | filtered | L25–L75 | with content | 186 | 43.0 | 43.0 | 14.0 |
| qwen2.5:72b | filtered | L100 (125 %) | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | filtered | L100 (125 %) | empty reference, layer present | 21 | 42.9 | 0.0 | 57.1 |
| qwen2.5:72b | filtered | L100 (125 %) | with content | 68 | 29.4 | 50.0 | 20.6 |
| qwen2.5:7b | general | L25–L75 | layer absent | 33 | 100.0 | 0.0 | 0.0 |
| qwen2.5:7b | general | L25–L75 | empty reference, layer present | 66 | 40.9 | 0.0 | 59.1 |
| qwen2.5:7b | general | L25–L75 | with content | 186 | 12.9 | 31.7 | 55.4 |
| qwen2.5:7b | general | L100 (125 %) | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:7b | general | L100 (125 %) | empty reference, layer present | 21 | 47.6 | 0.0 | 52.4 |
| qwen2.5:7b | general | L100 (125 %) | with content | 68 | 1.5 | 47.1 | 51.5 |
| qwen2.5:7b | filtered | L25–L75 | layer absent | 33 | 66.7 | 0.0 | 33.3 |
| qwen2.5:7b | filtered | L25–L75 | empty reference, layer present | 66 | 53.0 | 0.0 | 47.0 |
| qwen2.5:7b | filtered | L25–L75 | with content | 186 | 15.6 | 52.2 | 32.3 |
| qwen2.5:7b | filtered | L100 (125 %) | layer absent | 6 | 66.7 | 0.0 | 33.3 |
| qwen2.5:7b | filtered | L100 (125 %) | empty reference, layer present | 21 | 42.9 | 0.0 | 57.1 |
| qwen2.5:7b | filtered | L100 (125 %) | with content | 68 | 13.2 | 45.6 | 41.2 |

## 4. Effect of filtering (filtered vs general, paired by question)

Δ in percentage points (filtered − general). Improved/worsened = label better/worse in the filtered view. Score: +2 I→C, +1 I→P or P→C, opposite sign if worse, scaled to ±100 %. p: two-sided sign test (indicative).

| Model | Group | Pairs | Δ%C | Δ%P | Δ%I | Improved | Same | Worsened | Score % | p |
|---|---|---|---|---|---|---|---|---|---|---|
| llama3.1:70b | L25–L75 | 285 | +7.4 | +6.3 | -13.7 | 95 | 159 | 31 | +10.5 | 9.61e-09 |
| llama3.1:70b | L100 (125 %) | 95 | +2.1 | +7.4 | -9.5 | 26 | 57 | 12 | +5.8 | 0.0336 |
| llama3.1:8b | L25–L75 | 285 | +1.4 | +4.6 | -6.0 | 49 | 205 | 31 | +3.7 | 0.0567 |
| llama3.1:8b | L100 (125 %) | 95 | -2.1 | -10.5 | +12.6 | 9 | 64 | 22 | -7.4 | 0.0294 |
| qwen2.5:72b | L25–L75 | 285 | +5.3 | +1.4 | -6.7 | 59 | 203 | 23 | +6.0 | 8.72e-05 |
| qwen2.5:72b | L100 (125 %) | 95 | +7.4 | +4.2 | -11.6 | 27 | 59 | 9 | +9.5 | 0.00393 |
| qwen2.5:7b | L25–L75 | 285 | +0.7 | +13.3 | -14.0 | 72 | 185 | 28 | +7.4 | 1.26e-05 |
| qwen2.5:7b | L100 (125 %) | 95 | +5.3 | -1.1 | -4.2 | 20 | 63 | 12 | +4.7 | 0.215 |

### 4b. By type of reference answer

| Model | Group | Reference type | Pairs | Improved | Same | Worsened | Score % |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | L25–L75 | layer absent | 15 | 2 | 7 | 6 | -26.7 |
| llama3.1:70b | L25–L75 | empty reference, layer present | 54 | 4 | 38 | 12 | -14.8 |
| llama3.1:70b | L25–L75 | with content | 216 | 89 | 114 | 13 | +19.4 |
| llama3.1:70b | L100 (125 %) | layer absent | 3 | 0 | 2 | 1 | -33.3 |
| llama3.1:70b | L100 (125 %) | empty reference, layer present | 17 | 1 | 13 | 3 | -11.8 |
| llama3.1:70b | L100 (125 %) | with content | 75 | 25 | 42 | 8 | +11.3 |
| llama3.1:8b | L25–L75 | layer absent | 15 | 0 | 12 | 3 | -20.0 |
| llama3.1:8b | L25–L75 | empty reference, layer present | 54 | 6 | 46 | 2 | +7.4 |
| llama3.1:8b | L25–L75 | with content | 216 | 43 | 147 | 26 | +4.4 |
| llama3.1:8b | L100 (125 %) | layer absent | 3 | 0 | 1 | 2 | -66.7 |
| llama3.1:8b | L100 (125 %) | empty reference, layer present | 17 | 3 | 12 | 2 | +5.9 |
| llama3.1:8b | L100 (125 %) | with content | 75 | 6 | 51 | 18 | -8.0 |
| qwen2.5:72b | L25–L75 | layer absent | 33 | 0 | 33 | 0 | +0.0 |
| qwen2.5:72b | L25–L75 | empty reference, layer present | 66 | 5 | 51 | 10 | -7.6 |
| qwen2.5:72b | L25–L75 | with content | 186 | 54 | 119 | 13 | +11.8 |
| qwen2.5:72b | L100 (125 %) | layer absent | 6 | 0 | 6 | 0 | +0.0 |
| qwen2.5:72b | L100 (125 %) | empty reference, layer present | 21 | 0 | 15 | 6 | -28.6 |
| qwen2.5:72b | L100 (125 %) | with content | 68 | 27 | 38 | 3 | +22.1 |
| qwen2.5:7b | L25–L75 | layer absent | 33 | 0 | 22 | 11 | -33.3 |
| qwen2.5:7b | L25–L75 | empty reference, layer present | 66 | 10 | 54 | 2 | +12.1 |
| qwen2.5:7b | L25–L75 | with content | 186 | 62 | 109 | 15 | +12.9 |
| qwen2.5:7b | L100 (125 %) | layer absent | 6 | 0 | 4 | 2 | -33.3 |
| qwen2.5:7b | L100 (125 %) | empty reference, layer present | 21 | 1 | 18 | 2 | -4.8 |
| qwen2.5:7b | L100 (125 %) | with content | 68 | 19 | 41 | 8 | +11.0 |

## 5. Resource use (pooled over runs)

Tokens: mean `tokens_input` of non-truncated prompts (as counted by the inference server; not comparable across model families).

| Model | View | Group | Mean input tokens | % prompts truncated | % outputs cut at token cap | Latency per answer (s) | % judge ties |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | general | L25–L75 | 96,606 | 0.0 | 11.2 | 73.6 | 8.1 |
| llama3.1:70b | general | L100 (125 %) | n/a | 100.0 | 5.3 | 298.4 | 9.5 |
| llama3.1:70b | filtered | L25–L75 | 33,563 | 0.0 | 8.1 | 59.0 | 12.6 |
| llama3.1:70b | filtered | L100 (125 %) | 47,934 | 8.4 | 9.5 | 88.5 | 10.5 |
| llama3.1:8b | general | L25–L75 | 96,606 | 0.0 | 44.9 | 43.4 | 9.5 |
| llama3.1:8b | general | L100 (125 %) | n/a | 100.0 | 29.5 | 60.8 | 9.5 |
| llama3.1:8b | filtered | L25–L75 | 33,563 | 0.0 | 43.5 | 27.3 | 17.2 |
| llama3.1:8b | filtered | L100 (125 %) | 47,934 | 8.4 | 50.5 | 50.0 | 12.6 |
| qwen2.5:72b | general | L25–L75 | 23,592 | 0.0 | 4.2 | 24.4 | 4.9 |
| qwen2.5:72b | general | L100 (125 %) | n/a | 100.0 | 0.0 | 47.8 | 8.4 |
| qwen2.5:72b | filtered | L25–L75 | 7,972 | 1.4 | 0.0 | 15.4 | 5.6 |
| qwen2.5:72b | filtered | L100 (125 %) | 10,201 | 16.8 | 2.1 | 26.5 | 7.4 |
| qwen2.5:7b | general | L25–L75 | 23,592 | 0.0 | 1.8 | 1.7 | 3.9 |
| qwen2.5:7b | general | L100 (125 %) | n/a | 100.0 | 1.1 | 5.7 | 3.2 |
| qwen2.5:7b | filtered | L25–L75 | 7,972 | 1.4 | 0.0 | 1.6 | 10.5 |
| qwen2.5:7b | filtered | L100 (125 %) | 10,201 | 16.8 | 2.1 | 2.7 | 7.4 |

## 6. Token reduction of the filtered prompt vs the general prompt (per question)

Excludes truncated prompts and questions whose layer is empty. Each filtered prompt is compared with the mean general prompt of the same trace/window. Negative reduction = filtered prompt larger.

| Model | Group | Questions | Mean % | Median % | Min % | Max % | Filtered ≥ general |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | L25–L75 | 270 | 63.4 | 76.3 | 3.6 | 99.5 | 0 |
| llama3.1:70b | L100 (125 %) | 0 | n/a | n/a | n/a | n/a | n/a |
| llama3.1:8b | L25–L75 | 270 | 63.4 | 76.3 | 3.6 | 99.5 | 0 |
| llama3.1:8b | L100 (125 %) | 0 | n/a | n/a | n/a | n/a | n/a |
| qwen2.5:72b | L25–L75 | 248 | 61.7 | 63.1 | -6.3 | 98.5 | 4 |
| qwen2.5:72b | L100 (125 %) | 0 | n/a | n/a | n/a | n/a | n/a |
| qwen2.5:7b | L25–L75 | 248 | 61.7 | 63.1 | -6.3 | 98.5 | 4 |
| qwen2.5:7b | L100 (125 %) | 0 | n/a | n/a | n/a | n/a | n/a |

## 7. Stability across runs

Not computed for cicids: each round is a different window of the capture. See the sd across rounds in table 1 and `dotplot_cicids_rounds.py` for per-question consistency.
