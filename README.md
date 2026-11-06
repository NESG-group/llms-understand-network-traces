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
- `data/qa/`: reference answers (PyShark) of the laboratory traces.
- `data/cicids2017/staging/<model>_run<N>/manifest.json`: the exact CIC-IDS2017 windows used in the paper.
- `results/ground_truth_cicids2017/`: reference answers of the CIC-IDS2017 levels.
- `results/basic/` and `results/cicids/`: model answers and judge outputs, `<model>/run<N>/{llm_answers,comparison/judge}/{general,filtered}`.
- `results/manual/{basic,cicids}/`: manual annotations of a sample of judged answers.
- `results/summary/`: aggregated metrics tables.

CIC-IDS2017 is not redistributed. Fetch the first 50,000 packets of the Monday capture from the [Hugging Face mirror](https://huggingface.co/datasets/bencorn/CICIDS2017):

```bash
uv run bash scripts/download_cicids2017.sh --max-packets 50000 --out-dir data/cicids2017/source
```

The original dataset is described in Sharafaldin et al. (ICISSP 2018); its terms of use apply.

> Directory names contain `:` (for example `results/basic/llama3.1:8b`), so the repository can be cloned on Linux and macOS but not on Windows (use WSL).

## Reproducing the analysis (no GPU needed)

The stored model answers, judge outputs and manual annotations are enough to regenerate every metric, figure and table of the paper. TShark and Ollama are not required for this step.

```bash
uv sync
bash scripts/reproduce_analysis.sh            # writes to results/reproduced/
```

It runs, in order: aggregated metrics (`metrics`), per-run dotplots, modal dotplots (`dotplot_model`), dotplots of the manual labels, the CIC-IDS2017 figures (`dotplot_cicids`, `graph_cicids`) and the judge vs. manual comparison (`compare_manual`, Cohen's and weighted kappa). Reference outputs of the paper are in `results/summary/`.

Individual commands:

```bash
uv run python -m llms_understand_network_traces.analysis.metrics --dataset basic
uv run python -m llms_understand_network_traces.analysis.metrics --dataset cicids
uv run python -m llms_understand_network_traces.analysis.metrics_per_model --models-dir results/basic
uv run python -m llms_understand_network_traces.analysis.dotplot_model --models-dir results/basic
uv run python -m llms_understand_network_traces.analysis.dotplot_cicids
uv run python -m llms_understand_network_traces.analysis.graph_cicids --runs 1 2 3 4 5
uv run python -m llms_understand_network_traces.comparison.compare_manual \
    --manual-dir results/manual/basic --judge-dir results/basic --run run1
```

## Reproducing the experiments (needs Ollama and a GPU)

`llms_understand_network_traces.pipeline` runs each step; every step is resumable per run and model.

```bash
PIPE="uv run python -m llms_understand_network_traces.pipeline"
```

| Step | What it does |
|---|---|
| `prepare` | (CIC-IDS2017) builds the window and the nested levels, then converts them to CSV |
| `gt` | reference answers with PyShark (CIC-IDS2017: one trace per process, up to 5 attempts) |
| `llm` | model answers, `general` and `filtered` views |
| `judge` | LLM-as-a-judge (default `llama3.3:70b`) |
| `dotplot` | dotplot of the judged run |
| `all` | `gt`, `llm`, `judge` and `dotplot` |

### Basic scenario

```bash
uv run python -m llms_understand_network_traces.preprocessing.convert_pcap_to_csv   # only to regenerate the CSVs
$PIPE gt --dataset basic
$PIPE llm --dataset basic --model llama3.1:8b --runs 5
$PIPE judge --dataset basic --model llama3.1:8b --runs 5
$PIPE dotplot --dataset basic --model llama3.1:8b --runs 5
```

Everything for the four answering models: `bash scripts/run_basic.sh` (`RUNS`, `MODELS` and `JUDGE` can be overridden).

### CIC-IDS2017

```bash
$PIPE prepare --dataset cicids --model llama3.1:8b --first-run 1 --runs 5 \
    --source data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng
$PIPE gt --dataset cicids --model llama3.1:8b --first-run 1 --runs 5
$PIPE llm --dataset cicids --model llama3.1:8b --first-run 1 --runs 5
$PIPE judge --dataset cicids --model llama3.1:8b --first-run 1 --runs 5
uv run python -m llms_understand_network_traces.cicids.cicids_status
```

Everything for the four models: `bash scripts/run_cicids.sh`. Run generation, judging and `--verify` one at a time: they share Ollama's memory.

`prepare` picks a random contiguous window of 8,000 packets (seed = run number, shared by all models) and writes one pcapng per level, with the manifest, to `data/cicids2017/staging/<model>_run<N>/`. The same options as in `answer_with_llm` (`--num-ctx`, `--temperature`, `--num-predict`, `--timeout`, `--retries`) are accepted by `pipeline`; `--help` lists the rest.

`scripts/ollama_context_probe.py` checks how many tokens the server actually processes for a given `num_ctx`.

## Tests

```bash
uv run pytest -m "not tshark"     # unit tests
uv run pytest -m tshark           # needs TShark; regenerates the CSVs and reference answers
```

## Repository structure

```
.
├── data/
│   ├── traces/{raw,processed_csv}/     laboratory traces and CSV views
│   ├── qa/                             reference answers of the laboratory traces
│   └── cicids2017/staging/             window manifests (data not included)
├── scripts/
│   ├── reproduce_analysis.sh           metrics, figures and validation from the stored results
│   ├── run_basic.sh, run_cicids.sh     full experiments (Ollama)
│   ├── download_cicids2017.sh          fetch and clip the CIC-IDS2017 capture
│   └── ollama_context_probe.py         context truncation check
├── src/llms_understand_network_traces/
│   ├── pipeline.py                     orchestrator
│   ├── preprocessing/                  TShark conversion
│   ├── evaluation/                     PyShark references, LLM answers
│   ├── cicids/                         windows, context levels, round analysis
│   ├── comparison/                     LLM judge, manual validation
│   ├── analysis/                       metrics and dotplots
│   └── utils/                          constants (questions) and helpers
├── tests/
└── results/
    ├── basic/, cicids/                 model answers and judge outputs
    ├── ground_truth_cicids2017/        CIC-IDS2017 reference answers
    ├── manual/                         manual annotations
    └── summary/                        aggregated metrics tables
```

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
