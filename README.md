# llms-understand-network-traces

Code, data and analysis scripts for the paper *"Do LLMs Understand Network Traces? A Comparative Study of Reasoning over Raw and Filtered Traffic Data"*.

The pipeline measures how well LLMs answer natural-language questions about packet captures, and how much a protocol-aware preprocessing of the trace helps.

## Pipeline

1. **Traces**: PCAPNG captures (four laboratory traces, T1-T4, and windows of CIC-IDS2017).
2. **Preprocessing**: PCAPNG to CSV with TShark, in a default view (all protocols) and protocol-filtered views (ARP, IPv4, TCP, UDP).
3. **Reference answers**: 19 questions (3 ARP, 4 IPv4, 9 TCP, 3 UDP) answered from the PCAPNG with PyShark.
4. **Answer generation**: zero-shot prompts to Ollama-served models (temperature 0, 1,024 output tokens).
5. **Judging**: Llama 3.3 70B as LLM-as-a-judge (rubric, demonstrations, swapped-position passes). Labels: C / P / I; E = judge error, N = no answer.
6. **Validation and metrics**: judge vs. manual annotations (Cohen's and weighted kappa), C/P/I rates, filtering effect, tokens.

The filtering agent (Hermes + MCP) belongs to the VIGILANT backend and is not part of this repository.

## Scenarios

| Scenario | Data | Purpose |
|---|---|---|
| Basic | `arp-icmp`, `ip-networktrace2`, `nmap22-23-53-80-443`, `nmap22-23-53-80-443-threewayhandshake` (T1-T4) | Reliable check of reference answers and model errors |
| CIC-IDS2017 | Monday (benign), windows from the first 50,000 packets | Effect of input size on real traffic |

For CIC-IDS2017 each model gets four nested input levels (L25, L50, L75, L100 = 50, 75, 100 and 125 % of its input-token budget) over five runs with run-specific seeds.

## Models

| Model | Params | Quantisation | Role |
|---|---|---|---|
| Llama 3.1 (`llama3.1:8b`, `llama3.1:70b`) | 8.0B / 70.6B | Q4_K_M | Answers |
| Qwen 2.5 (`qwen2.5:7b`, `qwen2.5:72b`) | 7.6B / 72.7B | Q4_K_M | Answers |
| Llama 3.3 (`llama3.3:70b`) | 70.6B | Q4_K_M | Judge |

Experiments used Ollama 0.33.3 and TShark 4.2.2 on an NVIDIA GB10 (121 GiB). No API keys are needed.

## Installation

Requirements:

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/)
- TShark 4.2 or later, which also provides `capinfos` and `editcap`. It is a system package, not a Python one, so `uv sync` does not install it:

```bash
sudo apt install tshark        # Debian/Ubuntu (answer "No" to non-root capture)
brew install wireshark         # macOS
```

```bash
git clone https://github.com/NESG-group/llms-understand-network-traces.git
cd llms-understand-network-traces
uv sync
ollama pull llama3.1:8b && ollama pull llama3.1:70b
ollama pull qwen2.5:7b && ollama pull qwen2.5:72b
ollama pull llama3.3:70b
```

All commands below are run from the repository root.

## Data

Included in the repository:

- `data/traces/raw/`: the four laboratory traces (PCAPNG).
- `data/traces/processed_csv/`: their CSV views (`general`, `arp`, `ip`, `tcp`, `udp`).
- `data/cicids2017/staging/<model>_run<N>/manifest.json`: the exact windows used in the paper.
- `results/`: summaries, manual annotations and figures (see below).

CIC-IDS2017 is not redistributed. Fetch the first 50,000 packets of the Monday capture from the [Hugging Face mirror](https://huggingface.co/datasets/bencorn/CICIDS2017):

```bash
uv run bash scripts/download_cicids2017.sh --max-packets 50000 --out-dir data/cicids2017/source
```

The original dataset is described in Sharafaldin et al. (ICISSP 2018); its terms of use apply.

## Reproducing the experiments

### Basic scenario

```bash
M=llama3.1:8b          # repeat for each answering model

# 1. PCAPNG -> CSV views
uv run python -m llms_understand_network_traces.preprocessing.convert_pcap_to_csv

# 2. Reference answers (PyShark) -> data/qa
uv run python -m llms_understand_network_traces.evaluation.answer_with_pyshark

# 3. Model answers -> results/models/$M/run1/llm_answers
uv run python -m llms_understand_network_traces.evaluation.answer_with_llm --model $M --run run1

# 4. Judge (pass the judge model: the script default is a small test model)
uv run python -m llms_understand_network_traces.comparison.compare_with_llm_judge \
    --judge-model llama3.3:70b \
    --gt-folder data/qa \
    --llm-folder results/models/$M/run1/llm_answers/general \
    --output-folder results/models/$M/run1/comparison/judge/general
# repeat with .../llm_answers/filtered and .../judge/filtered
```

Use `--help` on each module for the remaining options (`--num-ctx`, `--mode`, `--trace`, `--temperature`, ...). Answers and judgements are written under `results/models/<model>/run<N>/`.

### CIC-IDS2017

```bash
uv run python -m llms_understand_network_traces.cicids.cicids_context \
    --model $M --run run1 --source data/cicids2017/source/<capture>.pcapng
uv run python -m llms_understand_network_traces.cicids.cicids_status
```

`cicids_context` builds the nested windows (writing the manifests in `data/cicids2017/staging/`) and runs the answer generation; the judge step is the same as above.

### Metrics, validation and figures

```bash
# Aggregated metrics (Markdown + CSV)
uv run python -m llms_understand_network_traces.analysis.metrics --dataset basic
uv run python -m llms_understand_network_traces.analysis.metrics --dataset cicids

# Per-model metrics (kappa between views, run agreement, ...)
uv run python -m llms_understand_network_traces.analysis.metrics_per_model --models-dir results/models

# Judge vs. manual annotations
uv run python -m llms_understand_network_traces.comparison.preprocesses_manual \
    --models-dir results/models --run run1 --out <dir> --blind --manual --compact
uv run python -m llms_understand_network_traces.comparison.compare_manual \
    --manual-dir <annotated-dir> --judge-dir results/models --run run1

# Figures
uv run python -m llms_understand_network_traces.analysis.dotplot_model --models-dir results/models
uv run python -m llms_understand_network_traces.analysis.dotplot_cicids
uv run python -m llms_understand_network_traces.analysis.graph_cicids --runs 1 2 3 4 5
```

## Repository structure

```
.
├── data/
│   ├── traces/{raw,processed_csv}/     laboratory traces and CSV views
│   └── cicids2017/staging/             window manifests (data not included)
├── scripts/download_cicids2017.sh      fetch and clip the CIC-IDS2017 capture
├── src/llms_understand_network_traces/
│   ├── preprocessing/                  TShark conversion
│   ├── evaluation/                     PyShark references, LLM answers
│   ├── cicids/                         windows, context levels, round analysis
│   ├── comparison/                     LLM judge, manual validation
│   ├── analysis/                       metrics and dotplots
│   └── utils/                          constants (questions) and helpers
└── results/
    ├── summary/                        aggregated metrics tables
    └── final/                          manual annotations and figures of the paper
```

Raw per-run outputs (model answers and judge JSONs) are large and are published as release assets (`results-final-raw.zip`); extract them under `results/` to rerun the analysis scripts.

## Evaluation protocol

- **Labels**: Correct (matches the reference with nothing missing, wrong or extra), Partial (identifies part of it), Incorrect. Order, formatting and duplicates are ignored.
- **Position bias**: each answer is judged twice with positions swapped; disagreements are resolved by a tie-break rule and recorded.
- **Excluded from percentages**: E (judge error) and N (no answer).
- **Caveat**: the L100 level of the general view exceeds the context and is truncated by the server (Ollama 0.33.3); it is not "more context".

## Citation

```bibtex
```

## Acknowledgements

This work is a result of the VIGILANT project (Ref. PID2024-161902OB-I00), funded by the Spanish Ministry of Science, Innovation and Universities.

## License

See [LICENSE](LICENSE).
