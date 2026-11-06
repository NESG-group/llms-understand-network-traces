"""
cicids_context.py
================================================================================
For ONE model and ONE run: picks a random contiguous window (seed = run) of a large
source pcap, computes how many packets fit in each context level (counting tokens on
the REAL general CSV) and writes one pcapng per level.

Flow (default mode = generate):
  1. Data budget of the model:
        (num_ctx - overhead_max - num_predict) * (1 - margin)
     overhead_max = build_prompt template + general-view description
     + the longest question of constants.ALL_QUESTIONS (model tokenizer).
  2. Random contiguous window of the source pcap (editcap). The start depends ONLY
     on the run (not on the model), so all models share the same start.
  3. The window is rendered with pcap2csvGeneral (the preprocessing script) and tokens
     are counted in blocks with the model tokenizer until the largest target is covered.
  4. Nested levels (prefixes of the same window). By default:
        100 -> 1.25 of the budget (does NOT fit),  75 -> 1.00,  50 -> 0.75,  25 -> 0.50
  5. One pcapng per level (editcap 1-N) is written to the staging folder, with a
     manifest.json.

--verify mode (after generating):
  Renders the real general CSV of every pcap in the staging folder, recounts its tokens
  and checks the real share of the context and that each CSV is a prefix of the window.

Requirements: a running Ollama, tshark and editcap on the PATH.

Usage:
    uv run python -m llms_understand_network_traces.cicids.cicids_context \
        --model llama3.1:8b --run 1 \
        --source data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng

    uv run python -m llms_understand_network_traces.cicids.cicids_context \
        --model llama3.1:8b --run 1 \
        --source data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng --verify
"""

import re
import sys
import json
import random
import argparse
import subprocess
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import ollama

from llms_understand_network_traces.utils import constants
from llms_understand_network_traces.evaluation import answer_with_llm as gen
from llms_understand_network_traces.preprocessing import convert_pcap_to_csv as default_preprocess

COUNT_NUM_CTX = 32768
BLOCK_FILL = 0.40
TIMEOUT = 900
DEFAULT_LEVELS = "100:1.25,75:1.0,50:0.75,25:0.5"
VIEW_DESC = gen.GENERAL_DESCRIPTION

CountFn = Callable[[str], int]


def load_preprocess(path: str | None = None) -> tuple[ModuleType, Path]:
    """Return the preprocessing module (the packaged one unless a script path is given)."""
    if path is None:
        return default_preprocess, Path(default_preprocess.__file__)
    spec = importlib.util.spec_from_file_location("preprocess_mod", path)
    if spec is None or spec.loader is None:
        sys.exit(f"Cannot import the preprocessing script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, Path(path)


def render_general(mod: ModuleType, pcap: Path, out_base: Path, disable_protocols: list[str]) -> tuple[list[str], str]:
    csv_path = mod.pcap2csvGeneral(str(pcap), base_folder=str(out_base), disable_protocols=tuple(disable_protocols))
    return read_lines(csv_path), csv_path


def count_packets(pcap: Path) -> int:
    result = subprocess.run(
        ["tshark", "-n", "-r", str(pcap), "-T", "fields", "-e", "frame.number"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"tshark failed while counting packets of {pcap}: {result.stderr[:200]}")
    return sum(1 for line in result.stdout.splitlines() if line.strip())


def cut(src: Path, dst: Path, first: int, last: int) -> None:
    """Keep packets first..last (1-based numbering) with their timestamps."""
    subprocess.run(["editcap", "-r", "-F", "pcapng", str(src), str(dst), f"{first}-{last}"], check=True)


def read_lines(csv_path: str | Path) -> list[str]:
    with open(csv_path, "r") as handle:
        lines = handle.readlines()
    return [line if line.endswith("\n") else line + "\n" for line in lines if line.strip()]


def nonce() -> str:
    """Fixed-width random prefix: invalidates the Ollama prefix cache."""
    return f"ID{random.randint(100000, 999999)}\n"


def prompt_eval(client: ollama.Client, model: str, prompt: str, num_ctx: int) -> int:
    response = client.generate(
        model=model,
        prompt=prompt,
        keep_alive="30m",
        options={"temperature": 0, "num_predict": 1, "num_ctx": num_ctx},
    )
    count = response.prompt_eval_count
    if not count:
        raise RuntimeError("Ollama did not return prompt_eval_count")
    return count


def setup_counting(client: ollama.Client, model: str) -> dict[str, Any]:
    base = prompt_eval(client, model, "x", COUNT_NUM_CTX)
    nonce_cost = max(prompt_eval(client, model, nonce() + "x", COUNT_NUM_CTX) - base, 0)
    overheads: dict[str, int] = {}
    for question in constants.ALL_QUESTIONS:
        cost = prompt_eval(client, model, nonce() + gen.build_prompt(question, "", VIEW_DESC), COUNT_NUM_CTX)
        overheads[question] = cost - nonce_cost
    ref_q = max(overheads, key=lambda q: overheads[q])
    return {
        "nonce_cost": nonce_cost,
        "overhead_max": overheads[ref_q],
        "baseline": overheads[ref_q] + nonce_cost,
        "ref_q": ref_q,
    }


def make_counter(client: ollama.Client, model: str, state: dict[str, Any]) -> CountFn:
    def count_fn(text: str) -> int:
        prompt = nonce() + gen.build_prompt(state["ref_q"], text, VIEW_DESC)
        return prompt_eval(client, model, prompt, COUNT_NUM_CTX) - state["baseline"]

    return count_fn


def choose_block_lines(count_fn: CountFn, lines: list[str]) -> int:
    n = min(100, len(lines))
    tokens_per_line = max(count_fn("".join(lines[:n])) / n, 1)
    return max(50, int(BLOCK_FILL * COUNT_NUM_CTX / tokens_per_line))


def count_blocks(count_fn: CountFn, lines: list[str], target: float, block_lines: int) -> list[dict[str, int]]:
    """Count data tokens in blocks until `target` is covered (or the lines run out)."""
    blocks: list[dict[str, int]] = []
    start, cumulative = 0, 0
    while cumulative < target and start < len(lines):
        end = min(start + block_lines, len(lines))
        tokens = count_fn("".join(lines[start:end]))
        if tokens + COUNT_NUM_CTX * 0.05 > COUNT_NUM_CTX * 0.95:
            raise RuntimeError("A block is close to the measuring context: reduce BLOCK_FILL.")
        blocks.append({"start": start, "end": end, "tokens": tokens, "cum_before": cumulative})
        cumulative += tokens
        start = end
        print(f"    block {len(blocks):>3}: lines {blocks[-1]['start']:>7}-{end:<7} "
              f"{tokens:>7,} tokens   cumulative {cumulative:>9,}")
    return blocks


def lines_for_target(
    count_fn: CountFn, lines: list[str], blocks: list[dict[str, int]], target: int
) -> tuple[int | None, int | None]:
    """Number of lines whose data adds up to ~target tokens (refined inside the block)."""
    for block in blocks:
        if block["cum_before"] + block["tokens"] < target:
            continue
        size = block["end"] - block["start"]
        tokens_per_line = block["tokens"] / size
        k = max(1, int((target - block["cum_before"]) / tokens_per_line))
        total = block["cum_before"]
        for _ in range(4):
            k = min(max(k, 1), size)
            total = block["cum_before"] + count_fn("".join(lines[block["start"]:block["start"] + k]))
            diff = target - total
            if abs(diff) <= tokens_per_line:
                break
            k += int(diff / tokens_per_line)
        k = min(max(k, 1), size)
        return block["start"] + k, total
    return None, None


def parse_levels(spec: str) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for item in spec.split(","):
        label, factor = item.split(":")
        out.append((label.strip(), float(factor)))
    return out


def model_tag(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9.\-]+", "-", model)


def generate(
    args: argparse.Namespace,
    mod: ModuleType,
    client: ollama.Client,
    ctx: int,
    count_model: str,
    levels: list[tuple[str, float]],
    staging: Path,
    work: Path,
) -> None:
    print("\n[1/5] Measuring template + question...")
    state = setup_counting(client, count_model)
    count_fn = make_counter(client, count_model, state)
    overhead_max = state["overhead_max"]
    print(f"      maximum overhead: {overhead_max:,} tokens (cache id: {state['nonce_cost']})")

    available = ctx - overhead_max - args.num_predict
    budget = int(available * (1 - args.margin))
    if budget <= 0:
        sys.exit("The data budget is <= 0.")
    print(f"\n[2/5] Data budget: {budget:,} tokens "
          f"(= {ctx:,} - {overhead_max:,} - {args.num_predict:,}, margin {args.margin:.0%})")
    max_target = int(max(f for _, f in levels) * budget)

    source = Path(args.source)
    total = count_packets(source)
    max_window = min(args.max_window, total)
    rng = random.Random(args.run)
    start = rng.randint(1, total - max_window + 1)
    print(f"\n[3/5] Source: {total:,} packets. Run {args.run} -> window start: packet {start:,} "
          f"(maximum window {max_window:,})")

    work.mkdir(parents=True, exist_ok=True)
    win_pcap = work / "window.pcapng"
    window = min(max_window, 8000)
    while True:
        last = start + window - 1
        cut(source, win_pcap, start, last)
        lines, csv_path = render_general(mod, win_pcap, work / "render", args.disable_protocol)
        if len(lines) != window:
            print(f"WARNING: the CSV has {len(lines):,} lines and the window {window:,} packets: "
                  f"line counts may not match packet counts. Check the preprocessing.")
        block_lines = choose_block_lines(count_fn, lines)
        print(f"      window {window:,} packets -> counting tokens (blocks of {block_lines} lines)...")
        blocks = count_blocks(count_fn, lines, max_target, block_lines)
        got = sum(b["tokens"] for b in blocks)
        if got >= max_target:
            break
        if window >= max_window:
            sys.exit(f"The maximum window ({max_window:,} packets) only gives {got:,} tokens and the largest "
                     f"level needs {max_target:,}. Use a larger source or raise --max-window.")
        window = min(max_window, window * 2)
        print(f"      target not reached: window extended to {window:,} packets")

    print("\n[4/5] Computing nested levels...")
    base_stem = re.sub(r"_\d+pkts$", "", source.stem)
    tag = model_tag(args.model)
    rows: list[dict[str, Any]] = []
    for label, factor in levels:
        target = int(factor * budget)
        n, data_tokens = lines_for_target(count_fn, lines, blocks, target)
        if n is None or data_tokens is None:
            sys.exit(f"Level {label} could not be computed.")
        prompt_tokens = data_tokens + overhead_max
        rows.append({
            "label": label,
            "factor": factor,
            "target_data_tokens": target,
            "packets": n,
            "est_data_tokens": data_tokens,
            "est_prompt_tokens": prompt_tokens,
            "est_pct_of_ctx": round(prompt_tokens / ctx * 100, 1),
            "fits": prompt_tokens + args.num_predict <= ctx,
            "stem": f"{base_stem}_{tag}_run{args.run}_L{label}_{n}pkts",
        })

    print(f"\n[5/5] Writing pcapng files to {staging} ...")
    staging.mkdir(parents=True, exist_ok=True)
    for row in rows:
        out = staging / f"{row['stem']}.pcapng"
        cut(win_pcap, out, 1, row["packets"])
        row["file"] = str(out)
        print(f"      level {row['label']}: {out.name}")

    print(f"\n{'level':>6} {'factor':>7} {'packets':>9} {'data tokens':>12} {'total prompt':>13} {'% ctx':>7}  fits")
    for row in rows:
        print(f"{row['label']:>6} {row['factor']:>7.2f} {row['packets']:>9,} {row['est_data_tokens']:>12,} "
              f"{row['est_prompt_tokens']:>13,} {row['est_pct_of_ctx']:>6}%  {'yes' if row['fits'] else 'NO'}")

    manifest = {
        "model": args.model,
        "count_model": count_model,
        "run": args.run,
        "seed": args.run,
        "source": str(source),
        "source_packets": total,
        "window_first_packet": start,
        "window_packets": window,
        "window_pcap": str(win_pcap),
        "window_csv": str(csv_path),
        "num_ctx": ctx,
        "num_predict": args.num_predict,
        "margin": args.margin,
        "overhead_max": overhead_max,
        "budget": budget,
        "disable_protocols": list(args.disable_protocol),
        "prompt_hash": gen.PROMPT_HASH,
        "levels": rows,
    }
    manifest_path = staging / "manifest.json"
    with open(manifest_path, "w") as handle:
        json.dump(manifest, handle, indent=2)
    print(f"\nManifest: {manifest_path}")


def verify(
    args: argparse.Namespace,
    mod: ModuleType,
    client: ollama.Client,
    ctx: int,
    count_model: str,
    staging: Path,
    work: Path,
) -> None:
    manifest_path = staging / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"{manifest_path} does not exist: run the generate mode first.")
    with open(manifest_path) as handle:
        manifest = json.load(handle)

    state = setup_counting(client, count_model)
    count_fn = make_counter(client, count_model, state)
    window_lines = read_lines(manifest["window_csv"])
    ctx = manifest["num_ctx"]
    num_predict = manifest["num_predict"]
    overhead_max = state["overhead_max"]
    print(f"\nVerifying {len(manifest['levels'])} levels (context {ctx:,}, overhead {overhead_max:,})...")

    all_ok = True
    for row in manifest["levels"]:
        pcap = Path(row["file"])
        lines, _ = render_general(mod, pcap, work / "verify", manifest["disable_protocols"])
        prefix_ok = lines == window_lines[:len(lines)] and len(lines) == row["packets"]
        block_lines = choose_block_lines(count_fn, lines)
        print(f"  level {row['label']}: counting {len(lines):,} lines...")
        blocks = count_blocks(count_fn, lines, float("inf"), block_lines)
        data_tokens = sum(b["tokens"] for b in blocks)
        prompt_tokens = data_tokens + overhead_max
        rel_dev = abs(data_tokens - row["est_data_tokens"]) / max(row["est_data_tokens"], 1)
        row["real_data_tokens"] = data_tokens
        row["real_prompt_tokens"] = prompt_tokens
        row["real_pct_of_ctx"] = round(prompt_tokens / ctx * 100, 1)
        row["real_fits"] = prompt_tokens + num_predict <= ctx
        row["prefix_of_window"] = prefix_ok
        row["deviation_vs_estimate"] = round(rel_dev, 4)
        ok = prefix_ok and rel_dev <= args.tolerance and (row["real_fits"] == row["fits"])
        row["verified"] = ok
        all_ok &= ok

    print(f"\n{'level':>6} {'packets':>9} {'est. data':>11} {'real data':>11} {'dev.':>7} "
          f"{'real % ctx':>10} {'fits':>5} {'prefix':>7}  ok")
    for row in manifest["levels"]:
        print(f"{row['label']:>6} {row['packets']:>9,} {row['est_data_tokens']:>11,} {row['real_data_tokens']:>11,} "
              f"{row['deviation_vs_estimate']:>6.1%} {row['real_pct_of_ctx']:>9}% "
              f"{'yes' if row['real_fits'] else 'NO':>5} {'yes' if row['prefix_of_window'] else 'NO':>7}  "
              f"{'OK' if row['verified'] else 'FAIL'}")

    manifest["verification"] = {"tolerance": args.tolerance, "all_ok": all_ok}
    with open(manifest_path, "w") as handle:
        json.dump(manifest, handle, indent=2)
    print("\nEverything verified." if all_ok else
          "\nWARNING: some level failed the verification: check the table before running the models.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Random window and context levels for one model and one run.")
    parser.add_argument("--model", required=True, help="Model whose context is used (e.g. llama3.1:8b)")
    parser.add_argument("--count-model", default=None, help="Model with the same tokenizer used to count. Default: --model")
    parser.add_argument("--run", type=int, required=True, help="Run number (it is the window seed)")
    parser.add_argument("--source", required=True, help="Large source pcap (e.g. 50000 packets)")
    parser.add_argument("--staging-dir", default=None,
                        help="Output folder. Default: data/cicids2017/staging/<model>_run<N>")
    parser.add_argument("--num-ctx", type=int, default=None, help="Context to use. Default: the model maximum")
    parser.add_argument("--num-predict", type=int, default=1024, help="Must match the generation value")
    parser.add_argument("--margin", type=float, default=0.01)
    parser.add_argument("--levels", default=DEFAULT_LEVELS,
                        help=f"comma-separated label:factor pairs (default {DEFAULT_LEVELS})")
    parser.add_argument("--max-window", type=int, default=20000,
                        help="Maximum window in packets. Keep the same value for every model (it fixes the start)")
    parser.add_argument("--disable-protocol", nargs="*", default=[], metavar="PROTO",
                        help="The SAME dissectors disabled when preprocessing CIC-IDS2017 for the general view")
    parser.add_argument("--preprocess-script", default=None,
                        help="Alternative preprocessing script (default: the packaged convert_pcap_to_csv)")
    parser.add_argument("--verify", action="store_true", help="Verify the generated pcaps instead of generating them")
    parser.add_argument("--tolerance", type=float, default=0.02,
                        help="Relative deviation allowed by --verify (default 0.02)")
    args = parser.parse_args()

    count_model = args.count_model or args.model
    levels = parse_levels(args.levels)
    client = ollama.Client(timeout=TIMEOUT)

    ctx = args.num_ctx or gen.get_model_context_limit(args.model)
    if not ctx:
        sys.exit("Could not read the model context; use --num-ctx.")

    mod, mod_path = load_preprocess(args.preprocess_script)
    staging = (
        Path(args.staging_dir)
        if args.staging_dir
        else Path("data/cicids2017/staging") / f"{model_tag(args.model)}_run{args.run}"
    )
    work = staging / "_work"

    print(f"Model: {args.model}   context: {ctx:,}   tokenizer of: {count_model}   run: {args.run}")
    print(f"Preprocessing: {mod_path}   disable-protocol: {args.disable_protocol or '(none)'}")
    print(f"Staging folder: {staging}")

    if args.verify:
        verify(args, mod, client, ctx, count_model, staging, work)
    else:
        generate(args, mod, client, ctx, count_model, levels, staging, work)


if __name__ == "__main__":
    main()