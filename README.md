# llms-understand-network-traces

Reproducible benchmark for evaluating Large Language Models (LLMs) on question answering over network traffic traces.

This repository contains the code, question-answer dataset and analysis scripts of the paper *"Do LLMs Understand Network Traces? A Comparative Study of Reasoning over Raw and Filtered Traffic Data"*.

## Overview

The pipeline compares how well LLMs answer natural-language questions about packet captures, and how much a protocol-aware preprocessing of the trace helps.

1. **Network data**: PCAPNG traces, either small laboratory captures or windows extracted from CIC-IDS2017.
2. **Question-answer dataset**: 19 questions across the TCP/IP stack (3 ARP, 4 IPv4, 9 TCP, 3 UDP). Reference answers are computed from the original PCAPNG with question-specific PyShark functions and stored as JSON.
3. **Preprocessing**: PCAPNG is converted to CSV with TShark in two views:
   - **Default view**: the TShark packet summary, covering all protocols.
   - **Protocol-filtered views**: one view per protocol (ARP, IPv4, TCP, UDP) with a curated set of header fields.
4. **Prompting**: zero-shot prompts (trace, instructions, question) answered by each model.
5. **Evaluation**: answers are labelled Correct (C), Partial (P) or Incorrect (I) by an LLM-as-a-judge, and the judge is compared against manual annotations.
6. **Filtering agent**: an LLM agent that selects the protocol views to use for each question, connected to the backend over the Model Context Protocol (MCP).

## Experimental scenarios

| Scenario | Data | Purpose |
|---|---|---|
| Basic | Four small laboratory traces (T1-T4) | Verify reference answers and model errors reliably |
| CIC-IDS2017 | Benign traffic of the Monday capture, windows from its first 50,000 packets | Study the effect of input size on real traffic |

For CIC-IDS2017, four nested input levels per model target 50, 75, 100 and 125 % of the model's input-token budget, over five runs with run-specific random seeds shared across models.

## Models

| Model | Parameters | Context | Quantisation | Role |
|---|---|---|---|---|
| Llama 3.1 | 8.0B | 131,072 | Q4_K_M | Answer generation |
| Llama 3.1 | 70.6B | 131,072 | Q4_K_M | Answer generation |
| Qwen 2.5 | 7.6B | 32,768 | Q4_K_M | Answer generation |
| Qwen 2.5 | 72.7B | 32,768 | Q4_K_M | Answer generation |
| Llama 3.3 | 70.6B | 131,072 | Q4_K_M | LLM-as-a-judge |

All generation runs use temperature 0 and a maximum of 1,024 output tokens. Models are served locally with Ollama; no API keys are required.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- [TShark](https://tshark.dev/) 4.2.2 (Wireshark CLI)
- [Ollama](https://ollama.com/) with the models above
- Enough GPU memory for the 70B models (the experiments were run on an NVIDIA GB10 with 121 GiB of RAM)

## Installation

```bash
git clone https://github.com/NESG-group/llms-understand-network-traces.git
cd llms-understand-network-traces
uv sync
```

Pull the models:

```bash
ollama pull llama3.1:8b
ollama pull llama3.1:70b
ollama pull qwen2.5:7b
ollama pull qwen2.5:72b
ollama pull llama3.3:70b
```

## Data

The four laboratory traces and the question-answer dataset are included under `data/`.

CIC-IDS2017 is not redistributed. Download the Monday capture and extract the first 50,000 packets with:

```bash
bash data/cicids2017/download_cicids2017.sh
```

The capture is obtained from the unofficial Hugging Face mirror [bencorn/CICIDS2017](https://huggingface.co/datasets/bencorn/CICIDS2017). The original dataset is described in Sharafaldin et al., ICISSP 2018, and its terms of use apply.

The exact windows used in the paper are fixed by the manifests in `data/cicids2017/manifests/`.

## Reproducing the experiments

Each stage reads the output of the previous one. Run them from the repository root.

```bash
uv run python -m llms_understand_network_traces.qa_generation
uv run python -m llms_understand_network_traces.preprocessing
uv run python -m llms_understand_network_traces.inference
uv run python -m llms_understand_network_traces.judge
uv run python -m llms_understand_network_traces.metrics
```

CIC-IDS2017 runs:

```bash
bash scripts/cicids_runs.sh
uv run python scripts/cicids_aggregate_rounds.py
```

Figures and tables of the paper:

```bash
uv run python scripts/make_figures.py
```

## Repository structure

```
.
├── data/
│   ├── traces/              laboratory traces T1-T4 (PCAPNG)
│   ├── qa/                  question-answer dataset and reference answers (JSON)
│   └── cicids2017/          download script and window manifests
├── src/llms_understand_network_traces/
│   ├── qa_generation/       PyShark reference-answer functions
│   ├── preprocessing/       TShark conversion (default and protocol-filtered views)
│   ├── inference/           prompt construction and Ollama queries
│   ├── judge/               LLM-as-a-judge with swapped-position evaluation
│   ├── metrics/             C/P/I rates, filtering effect, tokens, Cohen's kappa
│   ├── cicids/              window extraction and input-size levels
│   └── agent/               filtering agent skill and MCP views
├── scripts/                 experiment drivers, figures and tables
├── results/                 aggregated results used in the paper
└── tests/
```

## Evaluation protocol

- **Labels**: Correct (matches the reference with nothing missing, incorrect or extra), Partial (identifies part of the reference but omits or adds elements), Incorrect (identifies none of it). Order, formatting and duplicates are ignored.
- **Judge prompt**: explicit rubric with equivalent answer formats, worked examples of each label and a brief justification before the label.
- **Position bias**: each answer is judged twice with reference and candidate swapped; if the two judgements disagree, the stricter label is kept and the case is recorded as an inconsistency.
- **Metrics**: answer correctness (C/P/I percentages), effect of filtering (per-question label transitions summarised from -100 % to +100 %), resource consumption (input tokens and reduction from filtering), judge reliability (percentage agreement, Cohen's kappa and weighted kappa) and filter selection accuracy of the agent.


## Results

Aggregated results used in the paper are in `results/`. The full per-run outputs (model answers, judge outputs and intermediate CSV files) are available in the release assets of this repository.

## Citation

```bibtex
```

## Acknowledgements

This work is a result of the VIGILANT project (Ref. PID2024-161902OB-I00), funded by the Spanish Ministry of Science, Innovation and Universities.

## License

See [LICENSE](LICENSE).
