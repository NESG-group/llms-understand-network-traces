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
| CIC-IDS2017 | Monday, July 3, 2017 (benign), windows from the first 50,000 packets | Effect of input size on real traffic |

For CIC-IDS2017 each model gets four nested input levels (L25, L50, L75, L100 = 50, 75, 100 and 125 % of its input-token budget) over five runs with run-specific seeds. The paper analyses L25, L50 and L75; L100 is generated but excluded from the analysis because the server truncates it (see the caveat below), and it appears in the tables as a separate group.

> **Terminology.** The paper calls the unfiltered TShark text the *default view*; in the code, file names and result folders it is the `general` view. `filtered` is the same in both. Question numbers P1-P19 follow the order of `utils/constants.py` (P1-P3 ARP, P4-P7 IPv4, P8-P19 TCP/UDP).

## Models

| Model | Params | Quantisation | Role |
|---|---|---|---|
| Llama 3.1 (`llama3.1:8b`, `llama3.1:70b`) | 8.0B / 70.6B | Q4_K_M | Answers |
| Qwen 2.5 (`qwen2.5:7b`, `qwen2.5:72b`) | 7.6B / 72.7B | Q4_K_M | Answers |
| Llama 3.3 (`llama3.3:70b`) | 70.6B | Q4_K_M | Judge |

Experiments used Ollama 0.33.3 and TShark 4.2.2 on a system with an NVIDIA GB10 GPU, 121 GiB of RAM and a 20-core ARM CPU. Context windows are the maximum reported by Ollama for each model (131,072 tokens for Llama, 32,768 for Qwen). No API keys are needed.

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

- `data/traces/raw/basic/`: the four laboratory traces (PCAPNG).
- `data/traces/raw/cicids/<model>_run<N>/`: the CIC-IDS2017 extracts actually fed to each model, one PCAPNG per context level (`L25`, `L50`, `L75`, `L100`) plus the `manifest.json` of the window.
- `data/traces/processed_csv/{basic,cicids}/`: their CSV views (`general`, `arp`, `ip`, `tcp`, `udp`).
- `data/qa/{basic,cicids}/`: reference answers (PyShark) of the laboratory traces and of the CIC-IDS2017 extracts.
- `results/basic/` and `results/cicids/`: model answers and judge outputs, `<model>/run<N>/{llm_answers,comparison/judge}/{general,filtered}`.
- `results/manual/basic/`: manual annotations of a sample of judged answers (laboratory traces only; the CIC-IDS2017 sample was not annotated).
- `results/summary/`: the final metrics tables of the paper (`metrics_basic_final.md`, `metrics_cicids_final.md`).

Only the extracts used in the experiments are redistributed, so the CIC-IDS2017 steps `gt`, `llm` and `judge` run without downloading anything. The original 50,000-packet capture the windows are drawn from is not included; it is only needed to rebuild the windows with `prepare`. Fetch it from the [Hugging Face mirror](https://huggingface.co/datasets/bencorn/CICIDS2017):

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

It runs, in order: aggregated metrics (`metrics`), per-run dotplots, modal dotplots (`dotplot_model`), dotplots of the manual labels, the CIC-IDS2017 figure (`dotplot_cicids`) and the judge vs. manual comparison of the laboratory traces (`compare_manual`, Cohen's and weighted kappa). Reference outputs of the paper are in `results/summary/`.

To check that the stored results give the tables of the paper, regenerate the two summaries and compare them (no output means identical):

```bash
uv run python -m llms_understand_network_traces.analysis.metrics --dataset basic  --out-dir results/reproduced/metrics --tag _final
uv run python -m llms_understand_network_traces.analysis.metrics --dataset cicids --out-dir results/reproduced/metrics --tag _final
diff results/reproduced/metrics/metrics_basic_final.md  results/summary/metrics_basic_final.md
diff results/reproduced/metrics/metrics_cicids_final.md results/summary/metrics_cicids_final.md
```

Individual commands:

```bash
uv run python -m llms_understand_network_traces.analysis.metrics --dataset basic
uv run python -m llms_understand_network_traces.analysis.metrics --dataset cicids
uv run python -m llms_understand_network_traces.analysis.dotplot_model --models-dir results/basic
uv run python -m llms_understand_network_traces.analysis.dotplot_cicids --levels 25 50 75   # as in Fig. 3 of the paper
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

The windows used in the paper are already in `data/traces/raw/cicids/`. Skip `prepare` to reuse them; it is only needed to rebuild the windows and requires the original capture (see [Data](#data)).

```bash
$PIPE prepare --dataset cicids --model llama3.1:8b --first-run 1 --runs 5 \
    --source data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng
$PIPE gt --dataset cicids --model llama3.1:8b --first-run 1 --runs 5
$PIPE llm --dataset cicids --model llama3.1:8b --first-run 1 --runs 5
$PIPE judge --dataset cicids --model llama3.1:8b --first-run 1 --runs 5
uv run python -m llms_understand_network_traces.cicids.status
```

Everything for the four models: `bash scripts/run_cicids.sh` (it only runs `prepare` for the windows that are missing; `PREPARE=1` forces a rebuild). Run generation, judging and `--verify` one at a time: they share Ollama's memory.

`prepare` picks a random contiguous window of 8,000 packets (seed = run number, shared by all models) and writes one pcapng per level, with the manifest, to `data/traces/raw/cicids/<model>_run<N>/`. The same options as in `answer_with_llm` (`--num-ctx`, `--temperature`, `--num-predict`, `--timeout`, `--retries`) are accepted by `pipeline`; `--help` lists the rest.

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
│   ├── traces/{raw,processed_csv}/     PCAPNG traces and CSV views, each in basic/ and cicids/
│   ├── qa/{basic,cicids}/              reference answers
│   └── cicids2017/                     original capture (downloaded, not tracked)
├── scripts/
│   ├── reproduce_analysis.sh           metrics, figures and validation from the stored results
│   ├── run_basic.sh, run_cicids.sh     full experiments (Ollama)
│   ├── download_cicids2017.sh          fetch and clip the CIC-IDS2017 capture
│   └── ollama_context_probe.py         context truncation check
├── src/llms_understand_network_traces/
│   ├── pipeline.py                     orchestrator
│   ├── preprocessing/                  TShark conversion
│   ├── generation/                     PyShark references, LLM answers
│   ├── cicids/                         windows, context levels, run status
│   ├── comparison/                     LLM judge, manual validation
│   ├── analysis/                       metrics and dotplots
│   └── utils/                          constants (questions) and helpers
├── tests/
└── results/
    ├── basic/, cicids/                 model answers and judge outputs
    ├── manual/basic/                   manual annotations
    └── summary/                        final metrics tables of the paper
```

## Evaluation protocol

- **Labels**: Correct (matches the reference with nothing missing, wrong or extra), Partial (identifies part of it), Incorrect. Order, formatting and duplicates are ignored.
- **Position bias**: each answer is judged twice with the positions of the reference and the candidate swapped; if the two passes disagree, the stricter label is kept and the case is recorded as an inconsistency.
- **Excluded from percentages**: E (judge error) and N (no answer).
- **Caveat**: the L100 level of the general view exceeds the context window and Ollama 0.33.3 truncates it to about half of the configured size, so the model never receives the full input; it is not "more context".

## Paper and reproducibility map

Where each result of the paper comes from. Run `bash scripts/reproduce_analysis.sh` first (outputs go to `results/reproduced/`); `results/summary/` holds the tables as used in the paper.

| In the paper | Source in this repository |
|---|---|
| Table II (packets per trace and view) | row counts of `data/traces/processed_csv/basic/` (`general` = default view; one file per protocol view, minus its header row) |
| Table III, quantitative columns (C/P/I per layer and view) | `results/summary/metrics_cicids_final.md`, sections 1 (all layers) and 2 (per layer); groups L25, L50, L75 = 50, 75 and 100 % |
| Table III, qualitative column (transition score) | section 4 of the same file, column `Score %` |
| Token reduction and mean prompt length (Section V) | sections 5 and 6 of the same file |
| Fig. 3 (modal label per question) | `analysis.dotplot_cicids --levels 25 50 75`, written by `reproduce_analysis.sh` to `results/reproduced/figures/cicids_mode/` |
| Judge vs. manual agreement (95.1 %, kappa 0.92, weighted kappa 0.94, 29 of 30 disagreements stricter) | `comparison.compare_manual`, written to `results/reproduced/validation/basic/agreement_manual_vs_judge.txt` from the 608 labels in `results/manual/basic/` (annotation sheets built with `comparison.preprocess_manual`) |
| Basic-scenario results | `results/summary/metrics_basic_final.md` |

## Citation

The citation details will be added here once the paper is published.

## Acknowledgements

This work is a result of the VIGILANT project (Ref. PID2024-161902OB-I00), funded by MICIU/AEI/10.13039/501100011033 (Spanish Ministry of Science, Innovation and Universities).

## License

See [LICENSE](LICENSE).
