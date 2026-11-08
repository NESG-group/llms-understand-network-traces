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
| llama3.1:70b | general | L25 | 20.0 ± 25.3 | 44.2 ± 21.2 | 35.8 ± 5.8 | 5 | 95 |
| llama3.1:70b | general | L50 | 11.6 ± 4.4 | 44.2 ± 12.7 | 44.2 ± 8.8 | 5 | 95 |
| llama3.1:70b | general | L75 | 9.5 ± 2.3 | 25.2 ± 12.0 | 65.2 ± 12.1 | 5 | 95 |
| llama3.1:70b | general | L25–L75 | 13.7 ± 10.0 | 37.9 ± 14.8 | 48.4 ± 6.1 | 5 | 285 |
| llama3.1:70b | general | L100 (125 %) | 11.6 ± 17.6 | 40.0 ± 12.1 | 48.4 ± 11.4 | 5 | 95 |
| llama3.1:70b | filtered | L25 | 30.5 ± 15.5 | 36.8 ± 13.9 | 32.6 ± 8.6 | 5 | 95 |
| llama3.1:70b | filtered | L50 | 20.0 ± 8.7 | 46.3 ± 12.0 | 33.7 ± 7.1 | 5 | 95 |
| llama3.1:70b | filtered | L75 | 12.6 ± 15.2 | 49.5 ± 19.2 | 37.9 ± 6.9 | 5 | 95 |
| llama3.1:70b | filtered | L25–L75 | 21.0 ± 11.6 | 44.2 ± 14.3 | 34.8 ± 5.8 | 5 | 285 |
| llama3.1:70b | filtered | L100 (125 %) | 13.7 ± 12.1 | 47.4 ± 9.8 | 38.9 ± 8.8 | 5 | 95 |
| llama3.1:8b | general | L25 | 6.3 ± 9.4 | 40.0 ± 4.7 | 53.7 ± 7.8 | 5 | 95 |
| llama3.1:8b | general | L50 | 3.2 ± 4.7 | 34.7 ± 2.8 | 62.1 ± 6.9 | 5 | 95 |
| llama3.1:8b | general | L75 | 4.2 ± 6.9 | 26.3 ± 3.7 | 69.5 ± 4.4 | 5 | 95 |
| llama3.1:8b | general | L25–L75 | 4.6 ± 6.6 | 33.7 ± 2.9 | 61.7 ± 5.9 | 5 | 285 |
| llama3.1:8b | general | L100 (125 %) | 5.3 ± 9.1 | 45.3 ± 8.0 | 49.5 ± 7.1 | 5 | 95 |
| llama3.1:8b | filtered | L25 | 4.2 ± 4.4 | 42.1 ± 15.3 | 53.7 ± 12.0 | 5 | 95 |
| llama3.1:8b | filtered | L50 | 7.4 ± 2.8 | 38.9 ± 14.2 | 53.7 ± 13.6 | 5 | 95 |
| llama3.1:8b | filtered | L75 | 6.3 ± 4.4 | 33.7 ± 19.2 | 60.0 ± 16.1 | 5 | 95 |
| llama3.1:8b | filtered | L25–L75 | 6.0 ± 2.9 | 38.2 ± 15.3 | 55.8 ± 13.4 | 5 | 285 |
| llama3.1:8b | filtered | L100 (125 %) | 3.2 ± 2.9 | 34.8 ± 16.9 | 62.1 ± 14.1 | 5 | 95 |
| qwen2.5:72b | general | L25 | 60.0 ± 13.7 | 22.1 ± 4.4 | 17.9 ± 10.3 | 5 | 95 |
| qwen2.5:72b | general | L50 | 43.1 ± 12.6 | 26.3 ± 7.4 | 30.5 ± 6.8 | 5 | 95 |
| qwen2.5:72b | general | L75 | 39.0 ± 12.7 | 31.6 ± 8.3 | 29.5 ± 6.0 | 5 | 95 |
| qwen2.5:72b | general | L25–L75 | 47.3 ± 11.4 | 26.7 ± 6.1 | 26.0 ± 5.4 | 5 | 285 |
| qwen2.5:72b | general | L100 (125 %) | 29.5 ± 21.6 | 31.6 ± 8.3 | 39.0 ± 15.2 | 5 | 95 |
| qwen2.5:72b | filtered | L25 | 58.9 ± 18.3 | 28.4 ± 10.9 | 12.6 ± 10.9 | 5 | 95 |
| qwen2.5:72b | filtered | L50 | 52.6 ± 8.3 | 28.4 ± 8.8 | 18.9 ± 7.1 | 5 | 95 |
| qwen2.5:72b | filtered | L75 | 46.3 ± 10.2 | 27.4 ± 4.4 | 26.3 ± 6.5 | 5 | 95 |
| qwen2.5:72b | filtered | L25–L75 | 52.6 ± 10.5 | 28.1 ± 5.3 | 19.3 ± 6.5 | 5 | 285 |
| qwen2.5:72b | filtered | L100 (125 %) | 36.8 ± 13.4 | 35.8 ± 8.6 | 27.4 ± 8.6 | 5 | 95 |
| qwen2.5:7b | general | L25 | 43.2 ± 28.2 | 15.8 ± 7.5 | 41.1 ± 21.5 | 5 | 95 |
| qwen2.5:7b | general | L50 | 22.1 ± 21.5 | 25.3 ± 12.0 | 52.6 ± 12.9 | 5 | 95 |
| qwen2.5:7b | general | L75 | 23.2 ± 16.9 | 21.1 ± 8.3 | 55.8 ± 8.8 | 5 | 95 |
| qwen2.5:7b | general | L25–L75 | 29.5 ± 20.9 | 20.7 ± 8.3 | 49.8 ± 13.2 | 5 | 285 |
| qwen2.5:7b | general | L100 (125 %) | 17.9 ± 24.6 | 33.7 ± 10.9 | 48.4 ± 16.0 | 5 | 95 |
| qwen2.5:7b | filtered | L25 | 43.1 ± 6.9 | 24.2 ± 13.7 | 32.6 ± 8.6 | 5 | 95 |
| qwen2.5:7b | filtered | L50 | 25.3 ± 18.8 | 42.1 ± 14.0 | 32.6 ± 15.0 | 5 | 95 |
| qwen2.5:7b | filtered | L75 | 22.1 ± 17.2 | 35.8 ± 16.0 | 42.1 ± 6.5 | 5 | 95 |
| qwen2.5:7b | filtered | L25–L75 | 30.2 ± 13.3 | 34.0 ± 11.9 | 35.8 ± 8.2 | 5 | 285 |
| qwen2.5:7b | filtered | L100 (125 %) | 23.2 ± 17.7 | 32.6 ± 12.6 | 44.2 ± 9.6 | 5 | 95 |

## 2. Answer correctness by protocol layer of the question (mean ± sd across runs)

| Model | View | Group | Layer | %C | %P | %I |
|---|---|---|---|---|---|---|
| llama3.1:70b | general | L25 | ARP | 46.7 ± 50.6 | 26.7 ± 27.9 | 26.7 ± 27.9 |
| llama3.1:70b | general | L25 | IP | 10.0 ± 22.4 | 85.0 ± 22.4 | 5.0 ± 11.2 |
| llama3.1:70b | general | L25 | TCP/UDP | 16.7 ± 22.8 | 35.0 ± 20.8 | 48.3 ± 3.7 |
| llama3.1:70b | general | L50 | ARP | 13.3 ± 29.8 | 33.3 ± 33.4 | 53.3 ± 29.8 |
| llama3.1:70b | general | L50 | IP | 0.0 ± 0.0 | 80.0 ± 20.9 | 20.0 ± 20.9 |
| llama3.1:70b | general | L50 | TCP/UDP | 15.0 ± 7.0 | 35.0 ± 18.1 | 50.0 ± 15.6 |
| llama3.1:70b | general | L75 | ARP | 13.3 ± 18.2 | 26.6 ± 14.9 | 60.0 ± 14.9 |
| llama3.1:70b | general | L75 | IP | 0.0 ± 0.0 | 25.0 ± 17.7 | 75.0 ± 17.7 |
| llama3.1:70b | general | L75 | TCP/UDP | 11.7 ± 4.6 | 25.0 ± 13.2 | 63.3 ± 17.3 |
| llama3.1:70b | general | L25–L75 | ARP | 24.4 ± 29.8 | 28.9 ± 21.6 | 46.7 ± 14.5 |
| llama3.1:70b | general | L25–L75 | IP | 3.3 ± 7.5 | 63.3 ± 9.5 | 33.3 ± 5.9 |
| llama3.1:70b | general | L25–L75 | TCP/UDP | 14.4 ± 7.5 | 31.6 ± 17.0 | 53.9 ± 10.1 |
| llama3.1:70b | general | L100 (125 %) | ARP | 13.3 ± 29.8 | 53.4 ± 29.8 | 33.3 ± 0.0 |
| llama3.1:70b | general | L100 (125 %) | IP | 5.0 ± 11.2 | 65.0 ± 28.5 | 30.0 ± 32.6 |
| llama3.1:70b | general | L100 (125 %) | TCP/UDP | 13.3 ± 17.3 | 28.3 ± 17.3 | 58.3 ± 15.6 |
| llama3.1:70b | filtered | L25 | ARP | 40.0 ± 14.9 | 13.3 ± 18.2 | 46.7 ± 18.3 |
| llama3.1:70b | filtered | L25 | IP | 35.0 ± 13.7 | 60.0 ± 13.7 | 5.0 ± 11.2 |
| llama3.1:70b | filtered | L25 | TCP/UDP | 26.7 ± 23.9 | 35.0 ± 16.1 | 38.3 ± 12.6 |
| llama3.1:70b | filtered | L50 | ARP | 33.3 ± 0.0 | 33.3 ± 33.4 | 33.3 ± 33.4 |
| llama3.1:70b | filtered | L50 | IP | 25.0 ± 17.7 | 65.0 ± 22.4 | 10.0 ± 13.7 |
| llama3.1:70b | filtered | L50 | TCP/UDP | 15.0 ± 12.4 | 43.3 ± 9.1 | 41.7 ± 10.2 |
| llama3.1:70b | filtered | L75 | ARP | 26.7 ± 27.9 | 53.3 ± 44.7 | 20.0 ± 29.8 |
| llama3.1:70b | filtered | L75 | IP | 5.0 ± 11.2 | 65.0 ± 28.5 | 30.0 ± 27.4 |
| llama3.1:70b | filtered | L75 | TCP/UDP | 11.7 ± 16.2 | 43.3 ± 16.0 | 45.0 ± 9.5 |
| llama3.1:70b | filtered | L25–L75 | ARP | 33.3 ± 11.1 | 33.3 ± 31.4 | 33.3 ± 23.6 |
| llama3.1:70b | filtered | L25–L75 | IP | 21.7 ± 9.5 | 63.3 ± 19.2 | 15.0 ± 10.9 |
| llama3.1:70b | filtered | L25–L75 | TCP/UDP | 17.8 ± 14.9 | 40.6 ± 11.5 | 41.7 ± 7.9 |
| llama3.1:70b | filtered | L100 (125 %) | ARP | 33.3 ± 0.0 | 53.4 ± 29.8 | 13.3 ± 29.8 |
| llama3.1:70b | filtered | L100 (125 %) | IP | 10.0 ± 13.7 | 45.0 ± 32.6 | 45.0 ± 44.7 |
| llama3.1:70b | filtered | L100 (125 %) | TCP/UDP | 10.0 ± 14.9 | 46.7 ± 13.9 | 43.4 ± 3.7 |
| llama3.1:8b | general | L25 | ARP | 20.0 ± 29.8 | 13.3 ± 18.2 | 66.7 ± 23.6 |
| llama3.1:8b | general | L25 | IP | 5.0 ± 11.2 | 70.0 ± 20.9 | 25.0 ± 25.0 |
| llama3.1:8b | general | L25 | TCP/UDP | 3.3 ± 4.5 | 36.7 ± 9.5 | 60.0 ± 7.0 |
| llama3.1:8b | general | L50 | ARP | 0.0 ± 0.0 | 20.0 ± 18.2 | 80.0 ± 18.2 |
| llama3.1:8b | general | L50 | IP | 5.0 ± 11.2 | 65.0 ± 28.5 | 30.0 ± 32.6 |
| llama3.1:8b | general | L50 | TCP/UDP | 3.3 ± 4.5 | 28.3 ± 4.5 | 68.3 ± 7.0 |
| llama3.1:8b | general | L75 | ARP | 13.3 ± 29.8 | 20.0 ± 18.2 | 66.7 ± 23.6 |
| llama3.1:8b | general | L75 | IP | 0.0 ± 0.0 | 40.0 ± 13.7 | 60.0 ± 13.7 |
| llama3.1:8b | general | L75 | TCP/UDP | 3.3 ± 4.5 | 23.3 ± 3.7 | 73.3 ± 3.7 |
| llama3.1:8b | general | L25–L75 | ARP | 11.1 ± 19.2 | 17.8 ± 16.8 | 71.1 ± 12.7 |
| llama3.1:8b | general | L25–L75 | IP | 3.3 ± 7.5 | 58.3 ± 20.4 | 38.3 ± 23.3 |
| llama3.1:8b | general | L25–L75 | TCP/UDP | 3.3 ± 3.6 | 29.4 ± 3.7 | 67.2 ± 3.6 |
| llama3.1:8b | general | L100 (125 %) | ARP | 13.3 ± 29.8 | 46.7 ± 29.8 | 40.0 ± 14.9 |
| llama3.1:8b | general | L100 (125 %) | IP | 0.0 ± 0.0 | 65.0 ± 28.5 | 35.0 ± 28.5 |
| llama3.1:8b | general | L100 (125 %) | TCP/UDP | 5.0 ± 7.5 | 38.3 ± 15.1 | 56.7 ± 10.9 |
| llama3.1:8b | filtered | L25 | ARP | 6.7 ± 14.9 | 26.7 ± 27.9 | 66.7 ± 33.4 |
| llama3.1:8b | filtered | L25 | IP | 5.0 ± 11.2 | 65.0 ± 28.5 | 30.0 ± 32.6 |
| llama3.1:8b | filtered | L25 | TCP/UDP | 3.3 ± 7.5 | 38.3 ± 17.3 | 58.3 ± 10.2 |
| llama3.1:8b | filtered | L50 | ARP | 0.0 ± 0.0 | 40.0 ± 43.5 | 60.0 ± 43.5 |
| llama3.1:8b | filtered | L50 | IP | 10.0 ± 13.7 | 50.0 ± 0.0 | 40.0 ± 13.7 |
| llama3.1:8b | filtered | L50 | TCP/UDP | 8.3 ± 5.9 | 35.0 ± 19.0 | 56.7 ± 13.7 |
| llama3.1:8b | filtered | L75 | ARP | 13.3 ± 29.8 | 53.3 ± 38.0 | 33.3 ± 40.8 |
| llama3.1:8b | filtered | L75 | IP | 0.0 ± 0.0 | 45.0 ± 20.9 | 55.0 ± 20.9 |
| llama3.1:8b | filtered | L75 | TCP/UDP | 6.7 ± 7.0 | 25.0 ± 16.7 | 68.3 ± 10.9 |
| llama3.1:8b | filtered | L25–L75 | ARP | 6.7 ± 9.9 | 40.0 ± 33.9 | 53.3 ± 33.7 |
| llama3.1:8b | filtered | L25–L75 | IP | 5.0 ± 7.5 | 53.3 ± 16.2 | 41.7 ± 21.2 |
| llama3.1:8b | filtered | L25–L75 | TCP/UDP | 6.1 ± 6.3 | 32.8 ± 14.9 | 61.1 ± 8.8 |
| llama3.1:8b | filtered | L100 (125 %) | ARP | 0.0 ± 0.0 | 60.0 ± 43.5 | 40.0 ± 43.5 |
| llama3.1:8b | filtered | L100 (125 %) | IP | 0.0 ± 0.0 | 30.0 ± 41.1 | 70.0 ± 41.1 |
| llama3.1:8b | filtered | L100 (125 %) | TCP/UDP | 5.0 ± 4.5 | 30.0 ± 15.1 | 65.0 ± 10.9 |
| qwen2.5:72b | general | L25 | ARP | 86.7 ± 18.2 | 13.3 ± 18.2 | 0.0 ± 0.0 |
| qwen2.5:72b | general | L25 | IP | 25.0 ± 17.7 | 70.0 ± 11.2 | 5.0 ± 11.2 |
| qwen2.5:72b | general | L25 | TCP/UDP | 65.0 ± 13.7 | 8.3 ± 0.0 | 26.7 ± 13.7 |
| qwen2.5:72b | general | L50 | ARP | 80.0 ± 18.2 | 13.3 ± 18.2 | 6.7 ± 14.9 |
| qwen2.5:72b | general | L50 | IP | 30.0 ± 20.9 | 60.0 ± 13.7 | 10.0 ± 13.7 |
| qwen2.5:72b | general | L50 | TCP/UDP | 38.3 ± 9.5 | 18.4 ± 3.7 | 43.3 ± 7.0 |
| qwen2.5:72b | general | L75 | ARP | 86.7 ± 18.2 | 13.3 ± 18.2 | 0.0 ± 0.0 |
| qwen2.5:72b | general | L75 | IP | 30.0 ± 20.9 | 55.0 ± 11.2 | 15.0 ± 22.4 |
| qwen2.5:72b | general | L75 | TCP/UDP | 30.0 ± 12.6 | 28.3 ± 11.2 | 41.7 ± 5.9 |
| qwen2.5:72b | general | L25–L75 | ARP | 84.5 ± 16.8 | 13.3 ± 18.2 | 2.2 ± 5.0 |
| qwen2.5:72b | general | L25–L75 | IP | 28.3 ± 15.2 | 61.7 ± 7.5 | 10.0 ± 10.9 |
| qwen2.5:72b | general | L25–L75 | TCP/UDP | 44.4 ± 9.2 | 18.3 ± 4.2 | 37.2 ± 5.4 |
| qwen2.5:72b | general | L100 (125 %) | ARP | 40.0 ± 54.8 | 0.0 ± 0.0 | 60.0 ± 54.8 |
| qwen2.5:72b | general | L100 (125 %) | IP | 20.0 ± 11.2 | 55.0 ± 20.9 | 25.0 ± 17.7 |
| qwen2.5:72b | general | L100 (125 %) | TCP/UDP | 30.0 ± 22.5 | 31.7 ± 18.1 | 38.4 ± 7.5 |
| qwen2.5:72b | filtered | L25 | ARP | 73.3 ± 36.5 | 13.3 ± 18.2 | 13.3 ± 18.2 |
| qwen2.5:72b | filtered | L25 | IP | 45.0 ± 20.9 | 55.0 ± 20.9 | 0.0 ± 0.0 |
| qwen2.5:72b | filtered | L25 | TCP/UDP | 60.0 ± 19.9 | 23.3 ± 9.1 | 16.7 ± 16.7 |
| qwen2.5:72b | filtered | L50 | ARP | 66.7 ± 33.4 | 20.0 ± 18.2 | 13.3 ± 18.2 |
| qwen2.5:72b | filtered | L50 | IP | 45.0 ± 11.2 | 55.0 ± 11.2 | 0.0 ± 0.0 |
| qwen2.5:72b | filtered | L50 | TCP/UDP | 51.7 ± 6.9 | 21.7 ± 12.7 | 26.7 ± 6.9 |
| qwen2.5:72b | filtered | L75 | ARP | 66.7 ± 33.4 | 20.0 ± 18.2 | 13.3 ± 18.2 |
| qwen2.5:72b | filtered | L75 | IP | 40.0 ± 13.7 | 60.0 ± 13.7 | 0.0 ± 0.0 |
| qwen2.5:72b | filtered | L75 | TCP/UDP | 43.3 ± 10.9 | 18.3 ± 7.0 | 38.4 ± 7.5 |
| qwen2.5:72b | filtered | L25–L75 | ARP | 68.9 ± 33.7 | 17.8 ± 16.8 | 13.3 ± 18.2 |
| qwen2.5:72b | filtered | L25–L75 | IP | 43.3 ± 12.3 | 56.7 ± 12.3 | 0.0 ± 0.0 |
| qwen2.5:72b | filtered | L25–L75 | TCP/UDP | 51.7 ± 10.1 | 21.1 ± 5.4 | 27.2 ± 7.7 |
| qwen2.5:72b | filtered | L100 (125 %) | ARP | 66.7 ± 33.4 | 20.0 ± 18.2 | 13.3 ± 18.2 |
| qwen2.5:72b | filtered | L100 (125 %) | IP | 30.0 ± 11.2 | 55.0 ± 11.2 | 15.0 ± 13.7 |
| qwen2.5:72b | filtered | L100 (125 %) | TCP/UDP | 31.7 ± 10.9 | 33.3 ± 10.2 | 35.0 ± 7.0 |
| qwen2.5:7b | general | L25 | ARP | 60.0 ± 54.8 | 13.3 ± 18.2 | 26.7 ± 36.5 |
| qwen2.5:7b | general | L25 | IP | 5.0 ± 11.2 | 45.0 ± 20.9 | 50.0 ± 17.7 |
| qwen2.5:7b | general | L25 | TCP/UDP | 51.7 ± 30.3 | 6.7 ± 7.0 | 41.7 ± 24.3 |
| qwen2.5:7b | general | L50 | ARP | 46.7 ± 50.6 | 13.3 ± 18.2 | 40.0 ± 36.5 |
| qwen2.5:7b | general | L50 | IP | 5.0 ± 11.2 | 45.0 ± 27.4 | 50.0 ± 17.7 |
| qwen2.5:7b | general | L50 | TCP/UDP | 21.6 ± 19.2 | 21.7 ± 11.2 | 56.7 ± 12.3 |
| qwen2.5:7b | general | L75 | ARP | 60.0 ± 43.5 | 6.7 ± 14.9 | 33.3 ± 33.4 |
| qwen2.5:7b | general | L75 | IP | 5.0 ± 11.2 | 40.0 ± 13.7 | 55.0 ± 11.2 |
| qwen2.5:7b | general | L75 | TCP/UDP | 20.0 ± 14.0 | 18.3 ± 9.1 | 61.7 ± 7.5 |
| qwen2.5:7b | general | L25–L75 | ARP | 55.6 ± 47.8 | 11.1 ± 15.7 | 33.3 ± 33.4 |
| qwen2.5:7b | general | L25–L75 | IP | 5.0 ± 11.2 | 43.4 ± 18.1 | 51.6 ± 10.9 |
| qwen2.5:7b | general | L25–L75 | TCP/UDP | 31.1 ± 19.4 | 15.5 ± 6.9 | 53.3 ± 13.6 |
| qwen2.5:7b | general | L100 (125 %) | ARP | 40.0 ± 54.8 | 0.0 ± 0.0 | 60.0 ± 54.8 |
| qwen2.5:7b | general | L100 (125 %) | IP | 0.0 ± 0.0 | 65.0 ± 22.4 | 35.0 ± 22.4 |
| qwen2.5:7b | general | L100 (125 %) | TCP/UDP | 18.3 ± 25.3 | 31.7 ± 18.1 | 50.0 ± 8.3 |
| qwen2.5:7b | filtered | L25 | ARP | 53.3 ± 18.3 | 20.0 ± 29.8 | 26.6 ± 14.9 |
| qwen2.5:7b | filtered | L25 | IP | 15.0 ± 22.4 | 60.0 ± 33.5 | 25.0 ± 17.7 |
| qwen2.5:7b | filtered | L25 | TCP/UDP | 50.0 ± 5.9 | 13.3 ± 12.6 | 36.7 ± 7.5 |
| qwen2.5:7b | filtered | L50 | ARP | 46.7 ± 18.3 | 26.7 ± 27.9 | 26.6 ± 14.9 |
| qwen2.5:7b | filtered | L50 | IP | 15.0 ± 22.4 | 75.0 ± 17.7 | 10.0 ± 13.7 |
| qwen2.5:7b | filtered | L50 | TCP/UDP | 23.3 ± 19.0 | 35.0 ± 16.1 | 41.7 ± 20.4 |
| qwen2.5:7b | filtered | L75 | ARP | 46.7 ± 18.3 | 26.7 ± 27.9 | 26.6 ± 14.9 |
| qwen2.5:7b | filtered | L75 | IP | 20.0 ± 20.9 | 50.0 ± 30.6 | 30.0 ± 11.2 |
| qwen2.5:7b | filtered | L75 | TCP/UDP | 16.7 ± 16.7 | 33.3 ± 10.2 | 50.0 ± 10.2 |
| qwen2.5:7b | filtered | L25–L75 | ARP | 48.9 ± 16.9 | 24.4 ± 27.7 | 26.6 ± 14.9 |
| qwen2.5:7b | filtered | L25–L75 | IP | 16.7 ± 21.2 | 61.7 ± 26.1 | 21.7 ± 9.5 |
| qwen2.5:7b | filtered | L25–L75 | TCP/UDP | 30.0 ± 10.3 | 27.2 ± 8.2 | 42.8 ± 11.2 |
| qwen2.5:7b | filtered | L100 (125 %) | ARP | 46.7 ± 18.3 | 26.7 ± 27.9 | 26.6 ± 14.9 |
| qwen2.5:7b | filtered | L100 (125 %) | IP | 25.0 ± 17.7 | 45.0 ± 27.4 | 30.0 ± 11.2 |
| qwen2.5:7b | filtered | L100 (125 %) | TCP/UDP | 16.7 ± 19.6 | 30.0 ± 7.5 | 53.3 ± 17.3 |

## 3. Correctness by type of reference answer (pooled over runs)

| Model | View | Group | Reference type | n | %C | %P | %I |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | general | L25 | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| llama3.1:70b | general | L25 | empty reference, layer present | 20 | 40.0 | 0.0 | 60.0 |
| llama3.1:70b | general | L25 | with content | 69 | 7.2 | 60.9 | 31.9 |
| llama3.1:70b | general | L50 | layer absent | 6 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | general | L50 | empty reference, layer present | 17 | 41.2 | 0.0 | 58.8 |
| llama3.1:70b | general | L50 | with content | 72 | 2.8 | 58.3 | 38.9 |
| llama3.1:70b | general | L75 | layer absent | 3 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | general | L75 | empty reference, layer present | 17 | 41.2 | 0.0 | 58.8 |
| llama3.1:70b | general | L75 | with content | 75 | 1.3 | 32.0 | 66.7 |
| llama3.1:70b | general | L25–L75 | layer absent | 15 | 60.0 | 0.0 | 40.0 |
| llama3.1:70b | general | L25–L75 | empty reference, layer present | 54 | 40.7 | 0.0 | 59.3 |
| llama3.1:70b | general | L25–L75 | with content | 216 | 3.7 | 50.0 | 46.3 |
| llama3.1:70b | general | L100 (125 %) | layer absent | 3 | 66.7 | 0.0 | 33.3 |
| llama3.1:70b | general | L100 (125 %) | empty reference, layer present | 17 | 35.3 | 0.0 | 64.7 |
| llama3.1:70b | general | L100 (125 %) | with content | 75 | 4.0 | 50.7 | 45.3 |
| llama3.1:70b | filtered | L25 | layer absent | 6 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | filtered | L25 | empty reference, layer present | 20 | 30.0 | 0.0 | 70.0 |
| llama3.1:70b | filtered | L25 | with content | 69 | 30.4 | 50.7 | 18.8 |
| llama3.1:70b | filtered | L50 | layer absent | 6 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | filtered | L50 | empty reference, layer present | 17 | 23.5 | 0.0 | 76.5 |
| llama3.1:70b | filtered | L50 | with content | 72 | 18.1 | 61.1 | 20.8 |
| llama3.1:70b | filtered | L75 | layer absent | 3 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | filtered | L75 | empty reference, layer present | 17 | 23.5 | 0.0 | 76.5 |
| llama3.1:70b | filtered | L75 | with content | 75 | 9.3 | 62.7 | 28.0 |
| llama3.1:70b | filtered | L25–L75 | layer absent | 15 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | filtered | L25–L75 | empty reference, layer present | 54 | 25.9 | 0.0 | 74.1 |
| llama3.1:70b | filtered | L25–L75 | with content | 216 | 19.0 | 58.3 | 22.7 |
| llama3.1:70b | filtered | L100 (125 %) | layer absent | 3 | 33.3 | 0.0 | 66.7 |
| llama3.1:70b | filtered | L100 (125 %) | empty reference, layer present | 17 | 23.5 | 0.0 | 76.5 |
| llama3.1:70b | filtered | L100 (125 %) | with content | 75 | 10.7 | 60.0 | 29.3 |
| llama3.1:8b | general | L25 | layer absent | 6 | 50.0 | 0.0 | 50.0 |
| llama3.1:8b | general | L25 | empty reference, layer present | 20 | 10.0 | 0.0 | 90.0 |
| llama3.1:8b | general | L25 | with content | 69 | 1.4 | 55.1 | 43.5 |
| llama3.1:8b | general | L50 | layer absent | 6 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | general | L50 | empty reference, layer present | 17 | 5.9 | 0.0 | 94.1 |
| llama3.1:8b | general | L50 | with content | 72 | 2.8 | 45.8 | 51.4 |
| llama3.1:8b | general | L75 | layer absent | 3 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | general | L75 | empty reference, layer present | 17 | 5.9 | 0.0 | 94.1 |
| llama3.1:8b | general | L75 | with content | 75 | 4.0 | 33.3 | 62.7 |
| llama3.1:8b | general | L25–L75 | layer absent | 15 | 20.0 | 0.0 | 80.0 |
| llama3.1:8b | general | L25–L75 | empty reference, layer present | 54 | 7.4 | 0.0 | 92.6 |
| llama3.1:8b | general | L25–L75 | with content | 216 | 2.8 | 44.4 | 52.8 |
| llama3.1:8b | general | L100 (125 %) | layer absent | 3 | 66.7 | 0.0 | 33.3 |
| llama3.1:8b | general | L100 (125 %) | empty reference, layer present | 17 | 11.8 | 0.0 | 88.2 |
| llama3.1:8b | general | L100 (125 %) | with content | 75 | 1.3 | 57.3 | 41.3 |
| llama3.1:8b | filtered | L25 | layer absent | 6 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | filtered | L25 | empty reference, layer present | 20 | 5.0 | 0.0 | 95.0 |
| llama3.1:8b | filtered | L25 | with content | 69 | 4.3 | 58.0 | 37.7 |
| llama3.1:8b | filtered | L50 | layer absent | 6 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | filtered | L50 | empty reference, layer present | 17 | 23.5 | 0.0 | 76.5 |
| llama3.1:8b | filtered | L50 | with content | 72 | 4.2 | 51.4 | 44.4 |
| llama3.1:8b | filtered | L75 | layer absent | 3 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | filtered | L75 | empty reference, layer present | 17 | 17.6 | 0.0 | 82.4 |
| llama3.1:8b | filtered | L75 | with content | 75 | 4.0 | 42.7 | 53.3 |
| llama3.1:8b | filtered | L25–L75 | layer absent | 15 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | filtered | L25–L75 | empty reference, layer present | 54 | 14.8 | 0.0 | 85.2 |
| llama3.1:8b | filtered | L25–L75 | with content | 216 | 4.2 | 50.5 | 45.4 |
| llama3.1:8b | filtered | L100 (125 %) | layer absent | 3 | 0.0 | 0.0 | 100.0 |
| llama3.1:8b | filtered | L100 (125 %) | empty reference, layer present | 17 | 17.6 | 0.0 | 82.4 |
| llama3.1:8b | filtered | L100 (125 %) | with content | 75 | 0.0 | 44.0 | 56.0 |
| qwen2.5:72b | general | L25 | layer absent | 21 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | general | L25 | empty reference, layer present | 24 | 83.3 | 0.0 | 16.7 |
| qwen2.5:72b | general | L25 | with content | 50 | 32.0 | 42.0 | 26.0 |
| qwen2.5:72b | general | L50 | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | general | L50 | empty reference, layer present | 21 | 47.6 | 0.0 | 52.4 |
| qwen2.5:72b | general | L50 | with content | 68 | 36.8 | 36.8 | 26.5 |
| qwen2.5:72b | general | L75 | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | general | L75 | empty reference, layer present | 21 | 57.1 | 0.0 | 42.9 |
| qwen2.5:72b | general | L75 | with content | 68 | 27.9 | 44.1 | 27.9 |
| qwen2.5:72b | general | L25–L75 | layer absent | 33 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | general | L25–L75 | empty reference, layer present | 66 | 63.6 | 0.0 | 36.4 |
| qwen2.5:72b | general | L25–L75 | with content | 186 | 32.3 | 40.9 | 26.9 |
| qwen2.5:72b | general | L100 (125 %) | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | general | L100 (125 %) | empty reference, layer present | 21 | 71.4 | 0.0 | 28.6 |
| qwen2.5:72b | general | L100 (125 %) | with content | 68 | 10.3 | 44.1 | 45.6 |
| qwen2.5:72b | filtered | L25 | layer absent | 21 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | filtered | L25 | empty reference, layer present | 24 | 75.0 | 0.0 | 25.0 |
| qwen2.5:72b | filtered | L25 | with content | 50 | 34.0 | 54.0 | 12.0 |
| qwen2.5:72b | filtered | L50 | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | filtered | L50 | empty reference, layer present | 21 | 52.4 | 0.0 | 47.6 |
| qwen2.5:72b | filtered | L50 | with content | 68 | 48.5 | 39.7 | 11.8 |
| qwen2.5:72b | filtered | L75 | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | filtered | L75 | empty reference, layer present | 21 | 38.1 | 0.0 | 61.9 |
| qwen2.5:72b | filtered | L75 | with content | 68 | 44.1 | 38.2 | 17.6 |
| qwen2.5:72b | filtered | L25–L75 | layer absent | 33 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | filtered | L25–L75 | empty reference, layer present | 66 | 56.1 | 0.0 | 43.9 |
| qwen2.5:72b | filtered | L25–L75 | with content | 186 | 43.0 | 43.0 | 14.0 |
| qwen2.5:72b | filtered | L100 (125 %) | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:72b | filtered | L100 (125 %) | empty reference, layer present | 21 | 42.9 | 0.0 | 57.1 |
| qwen2.5:72b | filtered | L100 (125 %) | with content | 68 | 29.4 | 50.0 | 20.6 |
| qwen2.5:7b | general | L25 | layer absent | 21 | 100.0 | 0.0 | 0.0 |
| qwen2.5:7b | general | L25 | empty reference, layer present | 24 | 58.3 | 0.0 | 41.7 |
| qwen2.5:7b | general | L25 | with content | 50 | 12.0 | 30.0 | 58.0 |
| qwen2.5:7b | general | L50 | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:7b | general | L50 | empty reference, layer present | 21 | 33.3 | 0.0 | 66.7 |
| qwen2.5:7b | general | L50 | with content | 68 | 11.8 | 35.3 | 52.9 |
| qwen2.5:7b | general | L75 | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:7b | general | L75 | empty reference, layer present | 21 | 28.6 | 0.0 | 71.4 |
| qwen2.5:7b | general | L75 | with content | 68 | 14.7 | 29.4 | 55.9 |
| qwen2.5:7b | general | L25–L75 | layer absent | 33 | 100.0 | 0.0 | 0.0 |
| qwen2.5:7b | general | L25–L75 | empty reference, layer present | 66 | 40.9 | 0.0 | 59.1 |
| qwen2.5:7b | general | L25–L75 | with content | 186 | 12.9 | 31.7 | 55.4 |
| qwen2.5:7b | general | L100 (125 %) | layer absent | 6 | 100.0 | 0.0 | 0.0 |
| qwen2.5:7b | general | L100 (125 %) | empty reference, layer present | 21 | 47.6 | 0.0 | 52.4 |
| qwen2.5:7b | general | L100 (125 %) | with content | 68 | 1.5 | 47.1 | 51.5 |
| qwen2.5:7b | filtered | L25 | layer absent | 21 | 66.7 | 0.0 | 33.3 |
| qwen2.5:7b | filtered | L25 | empty reference, layer present | 24 | 75.0 | 0.0 | 25.0 |
| qwen2.5:7b | filtered | L25 | with content | 50 | 18.0 | 46.0 | 36.0 |
| qwen2.5:7b | filtered | L50 | layer absent | 6 | 66.7 | 0.0 | 33.3 |
| qwen2.5:7b | filtered | L50 | empty reference, layer present | 21 | 42.9 | 0.0 | 57.1 |
| qwen2.5:7b | filtered | L50 | with content | 68 | 16.2 | 58.8 | 25.0 |
| qwen2.5:7b | filtered | L75 | layer absent | 6 | 66.7 | 0.0 | 33.3 |
| qwen2.5:7b | filtered | L75 | empty reference, layer present | 21 | 38.1 | 0.0 | 61.9 |
| qwen2.5:7b | filtered | L75 | with content | 68 | 13.2 | 50.0 | 36.8 |
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
| llama3.1:70b | L25 | 95 | +10.5 | -7.4 | -3.2 | 26 | 58 | 11 | +6.8 | 0.0201 |
| llama3.1:70b | L50 | 95 | +8.4 | +2.1 | -10.5 | 31 | 52 | 12 | +9.5 | 0.0054 |
| llama3.1:70b | L75 | 95 | +3.2 | +24.2 | -27.4 | 38 | 49 | 8 | +15.3 | 9.25e-06 |
| llama3.1:70b | L25–L75 | 285 | +7.4 | +6.3 | -13.7 | 95 | 159 | 31 | +10.5 | 9.61e-09 |
| llama3.1:70b | L100 (125 %) | 95 | +2.1 | +7.4 | -9.5 | 26 | 57 | 12 | +5.8 | 0.0336 |
| llama3.1:8b | L25 | 95 | -2.1 | +2.1 | +0.0 | 11 | 74 | 10 | -1.1 | 1 |
| llama3.1:8b | L50 | 95 | +4.2 | +4.2 | -8.4 | 20 | 63 | 12 | +6.3 | 0.215 |
| llama3.1:8b | L75 | 95 | +2.1 | +7.4 | -9.5 | 18 | 68 | 9 | +5.8 | 0.122 |
| llama3.1:8b | L25–L75 | 285 | +1.4 | +4.6 | -6.0 | 49 | 205 | 31 | +3.7 | 0.0567 |
| llama3.1:8b | L100 (125 %) | 95 | -2.1 | -10.5 | +12.6 | 9 | 64 | 22 | -7.4 | 0.0294 |
| qwen2.5:72b | L25 | 95 | -1.1 | +6.3 | -5.3 | 13 | 75 | 7 | +2.1 | 0.263 |
| qwen2.5:72b | L50 | 95 | +9.5 | +2.1 | -11.6 | 25 | 63 | 7 | +10.5 | 0.0021 |
| qwen2.5:72b | L75 | 95 | +7.4 | -4.2 | -3.2 | 21 | 65 | 9 | +5.3 | 0.0428 |
| qwen2.5:72b | L25–L75 | 285 | +5.3 | +1.4 | -6.7 | 59 | 203 | 23 | +6.0 | 8.72e-05 |
| qwen2.5:72b | L100 (125 %) | 95 | +7.4 | +4.2 | -11.6 | 27 | 59 | 9 | +9.5 | 0.00393 |
| qwen2.5:7b | L25 | 95 | +0.0 | +8.4 | -8.4 | 24 | 59 | 12 | +4.2 | 0.0652 |
| qwen2.5:7b | L50 | 95 | +3.2 | +16.8 | -20.0 | 27 | 61 | 7 | +11.6 | 0.000821 |
| qwen2.5:7b | L75 | 95 | -1.1 | +14.7 | -13.7 | 21 | 65 | 9 | +6.3 | 0.0428 |
| qwen2.5:7b | L25–L75 | 285 | +0.7 | +13.3 | -14.0 | 72 | 185 | 28 | +7.4 | 1.26e-05 |
| qwen2.5:7b | L100 (125 %) | 95 | +5.3 | -1.1 | -4.2 | 20 | 63 | 12 | +4.7 | 0.215 |

### 4b. By type of reference answer

| Model | Group | Reference type | Pairs | Improved | Same | Worsened | Score % |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | L25 | layer absent | 6 | 0 | 2 | 4 | -66.7 |
| llama3.1:70b | L25 | empty reference, layer present | 20 | 1 | 16 | 3 | -10.0 |
| llama3.1:70b | L25 | with content | 69 | 25 | 40 | 4 | +18.1 |
| llama3.1:70b | L50 | layer absent | 6 | 1 | 4 | 1 | +0.0 |
| llama3.1:70b | L50 | empty reference, layer present | 17 | 1 | 12 | 4 | -17.6 |
| llama3.1:70b | L50 | with content | 72 | 29 | 36 | 7 | +16.7 |
| llama3.1:70b | L75 | layer absent | 3 | 1 | 1 | 1 | +0.0 |
| llama3.1:70b | L75 | empty reference, layer present | 17 | 2 | 10 | 5 | -17.6 |
| llama3.1:70b | L75 | with content | 75 | 35 | 38 | 2 | +23.3 |
| llama3.1:70b | L25–L75 | layer absent | 15 | 2 | 7 | 6 | -26.7 |
| llama3.1:70b | L25–L75 | empty reference, layer present | 54 | 4 | 38 | 12 | -14.8 |
| llama3.1:70b | L25–L75 | with content | 216 | 89 | 114 | 13 | +19.4 |
| llama3.1:70b | L100 (125 %) | layer absent | 3 | 0 | 2 | 1 | -33.3 |
| llama3.1:70b | L100 (125 %) | empty reference, layer present | 17 | 1 | 13 | 3 | -11.8 |
| llama3.1:70b | L100 (125 %) | with content | 75 | 25 | 42 | 8 | +11.3 |
| llama3.1:8b | L25 | layer absent | 6 | 0 | 3 | 3 | -50.0 |
| llama3.1:8b | L25 | empty reference, layer present | 20 | 0 | 19 | 1 | -5.0 |
| llama3.1:8b | L25 | with content | 69 | 11 | 52 | 6 | +4.3 |
| llama3.1:8b | L50 | layer absent | 6 | 0 | 6 | 0 | +0.0 |
| llama3.1:8b | L50 | empty reference, layer present | 17 | 4 | 12 | 1 | +17.6 |
| llama3.1:8b | L50 | with content | 72 | 16 | 45 | 11 | +4.2 |
| llama3.1:8b | L75 | layer absent | 3 | 0 | 3 | 0 | +0.0 |
| llama3.1:8b | L75 | empty reference, layer present | 17 | 2 | 15 | 0 | +11.8 |
| llama3.1:8b | L75 | with content | 75 | 16 | 50 | 9 | +4.7 |
| llama3.1:8b | L25–L75 | layer absent | 15 | 0 | 12 | 3 | -20.0 |
| llama3.1:8b | L25–L75 | empty reference, layer present | 54 | 6 | 46 | 2 | +7.4 |
| llama3.1:8b | L25–L75 | with content | 216 | 43 | 147 | 26 | +4.4 |
| llama3.1:8b | L100 (125 %) | layer absent | 3 | 0 | 1 | 2 | -66.7 |
| llama3.1:8b | L100 (125 %) | empty reference, layer present | 17 | 3 | 12 | 2 | +5.9 |
| llama3.1:8b | L100 (125 %) | with content | 75 | 6 | 51 | 18 | -8.0 |
| qwen2.5:72b | L25 | layer absent | 21 | 0 | 21 | 0 | +0.0 |
| qwen2.5:72b | L25 | empty reference, layer present | 24 | 1 | 20 | 3 | -8.3 |
| qwen2.5:72b | L25 | with content | 50 | 12 | 34 | 4 | +8.0 |
| qwen2.5:72b | L50 | layer absent | 6 | 0 | 6 | 0 | +0.0 |
| qwen2.5:72b | L50 | empty reference, layer present | 21 | 4 | 14 | 3 | +4.8 |
| qwen2.5:72b | L50 | with content | 68 | 21 | 43 | 4 | +13.2 |
| qwen2.5:72b | L75 | layer absent | 6 | 0 | 6 | 0 | +0.0 |
| qwen2.5:72b | L75 | empty reference, layer present | 21 | 0 | 17 | 4 | -19.0 |
| qwen2.5:72b | L75 | with content | 68 | 21 | 42 | 5 | +13.2 |
| qwen2.5:72b | L25–L75 | layer absent | 33 | 0 | 33 | 0 | +0.0 |
| qwen2.5:72b | L25–L75 | empty reference, layer present | 66 | 5 | 51 | 10 | -7.6 |
| qwen2.5:72b | L25–L75 | with content | 186 | 54 | 119 | 13 | +11.8 |
| qwen2.5:72b | L100 (125 %) | layer absent | 6 | 0 | 6 | 0 | +0.0 |
| qwen2.5:72b | L100 (125 %) | empty reference, layer present | 21 | 0 | 15 | 6 | -28.6 |
| qwen2.5:72b | L100 (125 %) | with content | 68 | 27 | 38 | 3 | +22.1 |
| qwen2.5:7b | L25 | layer absent | 21 | 0 | 14 | 7 | -33.3 |
| qwen2.5:7b | L25 | empty reference, layer present | 24 | 6 | 16 | 2 | +16.7 |
| qwen2.5:7b | L25 | with content | 50 | 18 | 29 | 3 | +14.0 |
| qwen2.5:7b | L50 | layer absent | 6 | 0 | 4 | 2 | -33.3 |
| qwen2.5:7b | L50 | empty reference, layer present | 21 | 2 | 19 | 0 | +9.5 |
| qwen2.5:7b | L50 | with content | 68 | 25 | 38 | 5 | +16.2 |
| qwen2.5:7b | L75 | layer absent | 6 | 0 | 4 | 2 | -33.3 |
| qwen2.5:7b | L75 | empty reference, layer present | 21 | 2 | 19 | 0 | +9.5 |
| qwen2.5:7b | L75 | with content | 68 | 19 | 42 | 7 | +8.8 |
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
| llama3.1:70b | general | L25 | 64,447 | 0.0 | 1.1 | 32.6 | 7.4 |
| llama3.1:70b | general | L50 | 96,593 | 0.0 | 8.4 | 76.7 | 7.4 |
| llama3.1:70b | general | L75 | 128,778 | 0.0 | 24.2 | 111.5 | 9.5 |
| llama3.1:70b | general | L25–L75 | 96,606 | 0.0 | 11.2 | 73.6 | 8.1 |
| llama3.1:70b | general | L100 (125 %) | n/a | 100.0 | 5.3 | 298.4 | 9.5 |
| llama3.1:70b | filtered | L25 | 22,027 | 0.0 | 3.2 | 41.7 | 10.5 |
| llama3.1:70b | filtered | L50 | 33,433 | 0.0 | 8.4 | 63.5 | 16.8 |
| llama3.1:70b | filtered | L75 | 45,229 | 0.0 | 12.6 | 71.9 | 10.5 |
| llama3.1:70b | filtered | L25–L75 | 33,563 | 0.0 | 8.1 | 59.0 | 12.6 |
| llama3.1:70b | filtered | L100 (125 %) | 47,934 | 8.4 | 9.5 | 88.5 | 10.5 |
| llama3.1:8b | general | L25 | 64,447 | 0.0 | 33.7 | 25.4 | 10.5 |
| llama3.1:8b | general | L50 | 96,593 | 0.0 | 49.5 | 45.5 | 6.3 |
| llama3.1:8b | general | L75 | 128,778 | 0.0 | 51.6 | 59.2 | 11.6 |
| llama3.1:8b | general | L25–L75 | 96,606 | 0.0 | 44.9 | 43.4 | 9.5 |
| llama3.1:8b | general | L100 (125 %) | n/a | 100.0 | 29.5 | 60.8 | 9.5 |
| llama3.1:8b | filtered | L25 | 22,027 | 0.0 | 35.8 | 18.2 | 14.7 |
| llama3.1:8b | filtered | L50 | 33,433 | 0.0 | 42.1 | 26.0 | 20.0 |
| llama3.1:8b | filtered | L75 | 45,229 | 0.0 | 52.6 | 37.6 | 16.8 |
| llama3.1:8b | filtered | L25–L75 | 33,563 | 0.0 | 43.5 | 27.3 | 17.2 |
| llama3.1:8b | filtered | L100 (125 %) | 47,934 | 8.4 | 50.5 | 50.0 | 12.6 |
| qwen2.5:72b | general | L25 | 15,792 | 0.0 | 4.2 | 21.1 | 4.2 |
| qwen2.5:72b | general | L50 | 23,588 | 0.0 | 3.2 | 22.4 | 6.3 |
| qwen2.5:72b | general | L75 | 31,397 | 0.0 | 5.3 | 29.8 | 4.2 |
| qwen2.5:72b | general | L25–L75 | 23,592 | 0.0 | 4.2 | 24.4 | 4.9 |
| qwen2.5:72b | general | L100 (125 %) | n/a | 100.0 | 0.0 | 47.8 | 8.4 |
| qwen2.5:72b | filtered | L25 | 5,251 | 0.0 | 0.0 | 11.9 | 4.2 |
| qwen2.5:72b | filtered | L50 | 8,321 | 0.0 | 0.0 | 15.6 | 4.2 |
| qwen2.5:72b | filtered | L75 | 10,449 | 4.2 | 0.0 | 18.5 | 8.4 |
| qwen2.5:72b | filtered | L25–L75 | 7,972 | 1.4 | 0.0 | 15.4 | 5.6 |
| qwen2.5:72b | filtered | L100 (125 %) | 10,201 | 16.8 | 2.1 | 26.5 | 7.4 |
| qwen2.5:7b | general | L25 | 15,792 | 0.0 | 1.1 | 1.0 | 2.1 |
| qwen2.5:7b | general | L50 | 23,588 | 0.0 | 1.1 | 1.5 | 4.2 |
| qwen2.5:7b | general | L75 | 31,397 | 0.0 | 3.2 | 2.4 | 5.3 |
| qwen2.5:7b | general | L25–L75 | 23,592 | 0.0 | 1.8 | 1.7 | 3.9 |
| qwen2.5:7b | general | L100 (125 %) | n/a | 100.0 | 1.1 | 5.7 | 3.2 |
| qwen2.5:7b | filtered | L25 | 5,251 | 0.0 | 0.0 | 1.2 | 11.6 |
| qwen2.5:7b | filtered | L50 | 8,321 | 0.0 | 0.0 | 1.6 | 9.5 |
| qwen2.5:7b | filtered | L75 | 10,449 | 4.2 | 0.0 | 2.1 | 10.5 |
| qwen2.5:7b | filtered | L25–L75 | 7,972 | 1.4 | 0.0 | 1.6 | 10.5 |
| qwen2.5:7b | filtered | L100 (125 %) | 10,201 | 16.8 | 2.1 | 2.7 | 7.4 |

## 6. Token reduction of the filtered prompt vs the general prompt (per question)

Excludes truncated prompts and questions whose layer is empty. Each filtered prompt is compared with the mean general prompt of the same trace/window. Negative reduction = filtered prompt larger.

| Model | Group | Questions | Mean % | Median % | Min % | Max % | Filtered ≥ general |
|---|---|---|---|---|---|---|---|
| llama3.1:70b | L25 | 89 | 63.5 | 77.3 | 3.6 | 99.5 | 0 |
| llama3.1:70b | L50 | 89 | 63.1 | 79.8 | 7.0 | 99.4 | 0 |
| llama3.1:70b | L75 | 92 | 63.7 | 73.8 | 8.1 | 99.5 | 0 |
| llama3.1:70b | L25–L75 | 270 | 63.4 | 76.3 | 3.6 | 99.5 | 0 |
| llama3.1:70b | L100 (125 %) | 0 | n/a | n/a | n/a | n/a | n/a |
| llama3.1:8b | L25 | 89 | 63.5 | 77.3 | 3.6 | 99.5 | 0 |
| llama3.1:8b | L50 | 89 | 63.1 | 79.8 | 7.0 | 99.4 | 0 |
| llama3.1:8b | L75 | 92 | 63.7 | 73.8 | 8.1 | 99.5 | 0 |
| llama3.1:8b | L25–L75 | 270 | 63.4 | 76.3 | 3.6 | 99.5 | 0 |
| llama3.1:8b | L100 (125 %) | 0 | n/a | n/a | n/a | n/a | n/a |
| qwen2.5:72b | L25 | 74 | 57.7 | 57.8 | 1.9 | 96.5 | 0 |
| qwen2.5:72b | L50 | 89 | 62.4 | 67.8 | -6.3 | 98.0 | 4 |
| qwen2.5:72b | L75 | 85 | 64.4 | 68.0 | 10.5 | 98.5 | 0 |
| qwen2.5:72b | L25–L75 | 248 | 61.7 | 63.1 | -6.3 | 98.5 | 4 |
| qwen2.5:72b | L100 (125 %) | 0 | n/a | n/a | n/a | n/a | n/a |
| qwen2.5:7b | L25 | 74 | 57.7 | 57.8 | 1.9 | 96.5 | 0 |
| qwen2.5:7b | L50 | 89 | 62.4 | 67.8 | -6.3 | 98.0 | 4 |
| qwen2.5:7b | L75 | 85 | 64.4 | 68.0 | 10.5 | 98.5 | 0 |
| qwen2.5:7b | L25–L75 | 248 | 61.7 | 63.1 | -6.3 | 98.5 | 4 |
| qwen2.5:7b | L100 (125 %) | 0 | n/a | n/a | n/a | n/a | n/a |

## 7. Stability across runs

Not computed for cicids: each round is a different window of the capture. See the sd across rounds in table 1; `analysis/dotplot_cicids.py` draws the modal label of each question per level.
