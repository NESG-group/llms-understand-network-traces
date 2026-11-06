import os
import time
import hashlib
import argparse
from functools import lru_cache

import httpx
import ollama


from llms_understand_network_traces.utils import constants
from llms_understand_network_traces.utils.utils import save_json_to_file

# ==============================================================================
# PROMPT
# ==============================================================================

# One-line legend for the GENERAL view only. That view has no header row (the filtered
# CSVs have one), so the legend gives the model the same information about the format.
# It describes the FORMAT of the data, never its content.
GENERAL_DESCRIPTION = (
    "Wireshark packet list in text form: one line per packet, tab-separated columns "
    "without a header row (frame number, relative time in seconds, source, destination, "
    "protocol, length, info)"
)
VIEW_DESCRIPTIONS = {"general": GENERAL_DESCRIPTION}   # other views: no description

# Prefix of the answer stored when a question is skipped by the circuit breaker.
# It starts with "ERROR" (so the judge labels it N) but can be counted apart from timeouts.
SKIPPED_PREFIX = "ERROR: SKIPPED"


def build_prompt(question: str, csv_data: str, data_description: str | None = None) -> str:
    """
    Builds the prompt following the 3-part structure:
    1. Task — what to do (role + question)
    2. Steering + guardrail — orientation and constraints
    3. Termination criterion — what a good answer looks like
    The DATA block goes BEFORE the question and the rules on purpose: when a prompt does not
    fit in num_ctx, Ollama keeps the TAIL of the prompt and drops the beginning, so the
    question and the rules must not be at the start.
    """
    data_header = f"DATA ({data_description}):" if data_description else "DATA:"
    return (
        # 1. Task
        f"You are a network traffic analyst. "
        f"Answer the question about the network trace provided below.\n\n"
        f"{data_header}\n{csv_data}\n\n"
        f"QUESTION: {question}\n\n"
        # 2. Steering + guardrail
        f"Use only the information present in the data above. "
        f"You may apply standard networking knowledge to interpret it, but do not report "
        f"values that cannot be derived from the data. "
        f"If no item in the data matches the question, or the data contains no relevant rows, "
        f"respond with: 'None'.\n\n"
        # 3. Termination criterion
        f"Start your answer immediately without any preamble or explanation. "
        f"Answer concisely and in the exact format specified in the question. "
        f"Report only what was asked, nothing else."
    )


# Short fingerprint of the template, stored with the results.
PROMPT_HASH = hashlib.sha256(
    (build_prompt("{question}", "{data}", GENERAL_DESCRIPTION)
     + build_prompt("{question}", "{data}", None)).encode("utf-8")
).hexdigest()[:12]

# ==============================================================================
# ENVIRONMENT
# ==============================================================================

@lru_cache(maxsize=1)
def get_ollama_version() -> str:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    if not host.startswith("http"):
        host = f"http://{host}"
    try:
        return httpx.get(f"{host}/api/version", timeout=5).json().get("version", "unknown")
    except Exception:
        return "unknown"


def truncation_suspected(tokens_input: int, num_ctx: int) -> bool | None:
    """
    HEURISTIC. Observed on this server: when the prompt does not fit in num_ctx,
    Ollama keeps only the TAIL of the prompt and evaluates about num_ctx/2 + 2
    tokens (2048 -> 1026, 4096 -> 2050). A prompt that really has that size would
    also match, so treat this as a flag, not as proof. The reliable check is to
    compare tokens_input with the expected prompt tokens measured beforehand.
    """
    if tokens_input == -1:
        return None
    return abs(tokens_input - (num_ctx // 2 + 2)) <= 8

# ==============================================================================
# SINGLE QUESTION
# ==============================================================================

def _error_result(msg, latency, question_tokens, context_limit, num_ctx, num_predict, attempts=0):
    return {
        "answer":                msg if msg.startswith("ERROR") else f"ERROR: {msg}",
        "latency_s":             latency,
        "attempts":              attempts,
        "tokens_input":          -1,
        "tokens_output":         -1,
        "tokens_total":          -1,
        "question_tokens":       question_tokens,
        "data_tokens":           -1,
        "context_limit":         context_limit,
        "num_ctx":               num_ctx,
        "num_predict":           num_predict,
        "done_reason":           None,
        "output_truncated":      None,
        "truncation_suspected":  None,
        "margin_violated":       None,
    }


def _is_transient(exc: Exception) -> bool:
    """Errors worth retrying: timeouts, connection/transport problems and server (5xx) errors.
    Deterministic errors (e.g. 404 model not found) are not retried."""
    if isinstance(exc, (httpx.TransportError, ConnectionError)):
        return True
    status = getattr(exc, "status_code", None)      # ollama.ResponseError
    return isinstance(status, int) and status >= 500


def ask_question(
    model_name: str,
    question: str,
    csv_data: str,
    view_description: str | None,
    num_ctx: int,
    num_predict: int = 1024,
    timeout: int = 600,
    temperature: float = 0,
    question_tokens: int = -1,
    context_limit: int | None = None,
    retries: int = 1,
) -> dict:
    """
    Asks one question. Transient errors are retried up to `retries` times. The timeout
    grows with each attempt (timeout, 2*timeout, 3*timeout...): a slow call usually needs
    more time, not the same time again, and the server may still be busy with the
    abandoned generation. `latency_s` is the duration of the successful attempt.
    """
    prompt = build_prompt(question, csv_data, view_description)
    start = time.time()
    options = {"temperature": temperature, "num_predict": num_predict, "num_ctx": num_ctx}

    response, attempt, last_error = None, 0, "no attempt made"
    for attempt in range(1, retries + 2):
        attempt_timeout = timeout * attempt
        # Timeout in the HTTP client: a request that exceeds it is actually aborted.
        client = ollama.Client(timeout=attempt_timeout)
        t0 = time.time()
        try:
            response = client.generate(model=model_name, prompt=prompt, options=options)
            latency = round(time.time() - t0, 3)
            break
        except Exception as e:
            is_timeout = isinstance(e, httpx.TimeoutException)
            last_error = f"Timeout after {attempt_timeout}s" if is_timeout else str(e)
            if not _is_transient(e):
                return _error_result(last_error, round(time.time() - start, 3), question_tokens,
                                     context_limit, num_ctx, num_predict, attempts=attempt)
            print(f"    ⚠️  {last_error} (attempt {attempt}/{retries + 1})")
            if attempt <= retries and not is_timeout:
                time.sleep(5 * attempt)      # short pause before retrying connection/server errors
    else:
        return _error_result(f"{last_error} (after {retries + 1} attempts)", round(time.time() - start, 3),
                             question_tokens, context_limit, num_ctx, num_predict, attempts=retries + 1)

    tokens_input = response.prompt_eval_count if response.prompt_eval_count else -1

    # Data payload = full prompt tokens - fixed template/view/question overhead
    data_tokens = (tokens_input - question_tokens) if (tokens_input != -1 and question_tokens != -1) else -1

    done_reason = getattr(response, "done_reason", None)
    output_truncated = (done_reason == "length")
    trunc = truncation_suspected(tokens_input, num_ctx)
    margin_violated = (tokens_input + num_predict > num_ctx) if tokens_input != -1 else None

    print(f"    → respondió en {latency}s" + (f" (intento {attempt})" if attempt > 1 else ""))
    print(f"    → respuesta: '{response.response[:100]}'")
    if trunc:
        print(f"    ⚠️  tokens_input ({tokens_input}) ≈ num_ctx/2 ({num_ctx // 2}): prompt probably TRUNCATED")
    if margin_violated:
        print(f"    ⚠️  tokens_input ({tokens_input}) + num_predict ({num_predict}) > num_ctx ({num_ctx})")
    if output_truncated:
        print(f"    ⚠️  output cut at num_predict={num_predict}")

    return {
        "answer":                response.response.strip(),
        "latency_s":             latency,
        "attempts":              attempt,
        "tokens_input":          tokens_input,
        "tokens_output":         response.eval_count if response.eval_count else -1,
        "tokens_total":          (response.prompt_eval_count or 0) + (response.eval_count or 0),
        "question_tokens":       question_tokens,
        "data_tokens":           data_tokens,
        "context_limit":         context_limit,
        "num_ctx":               num_ctx,
        "num_predict":           num_predict,
        "done_reason":           done_reason,
        "output_truncated":      output_truncated,
        "truncation_suspected":  trunc,
        "margin_violated":       margin_violated,
    }

# ==============================================================================
# CSV LOADER
# ==============================================================================

def load_csv(csv_folder: str, layer: str, trace_stem: str) -> str | None:
    """
    Loads the CSV file for a given trace and view.
    Returns the content as a string ("" if the file exists but is empty, e.g. a
    trace without UDP packets), or None if the file does not exist.
    """
    csv_path = os.path.join(csv_folder, layer, f"{trace_stem}.csv")
    if not os.path.exists(csv_path):
        print(f"  ⚠️  CSV not found: {csv_path}")
        return None
    with open(csv_path, "r") as f:
        return f.read()


def count_data_rows(csv_data: str, has_header: bool) -> int:
    """
    Number of DATA rows in a CSV text: non-blank lines, minus the header line if there is one.
    A 0-byte file and a file with only the header row both give 0.
    """
    lines = sum(1 for l in csv_data.splitlines() if l.strip())
    return max(lines - (1 if has_header else 0), 0)

# ==============================================================================
# LAYER → QUESTIONS MAPPING
# ==============================================================================

LAYER_QUESTIONS = {
    "arp": constants.ARP_QUESTIONS,
    "ip":  constants.IP_QUESTIONS,
    "tcp": constants.TCP_QUESTIONS,
    "udp": constants.UDP_QUESTIONS,
}

# ==============================================================================
# METRICS
# ==============================================================================

def _aggregate_metrics(results: dict, context_limit, num_ctx, num_predict) -> dict:
    def valid(key):
        return [r[key] for r in results.values() if r[key] != -1]

    def count(key):
        return sum(1 for r in results.values() if r.get(key))

    answered = sum(1 for r in results.values() if not r["answer"].startswith("ERROR"))
    skipped  = sum(1 for r in results.values() if r["answer"].startswith(SKIPPED_PREFIX))
    return {
        "total_latency_s":     round(sum(r["latency_s"] for r in results.values()), 3),
        "total_tokens_input":  sum(valid("tokens_input")),
        "total_tokens_output": sum(valid("tokens_output")),
        "total_tokens_total":  sum(valid("tokens_total")),
        "total_data_tokens":   sum(valid("data_tokens")),
        "questions_answered":  answered,
        "questions_failed":    len(results) - answered,
        "questions_skipped":   skipped,
        "context_limit":       context_limit,
        "num_ctx":             num_ctx,
        "num_predict":         num_predict,
        "questions_truncation_suspected": count("truncation_suspected"),
        "questions_margin_violated":      count("margin_violated"),
        "questions_output_truncated":     count("output_truncated"),
    }


def _output_header(trace_stem, model_name, view, temperature, num_ctx, num_predict):
    return {
        "Filename":       f"{trace_stem}.pcapng",
        "Model":          model_name,
        "Answer_Method":  "Ollama",
        "Ollama_Version": get_ollama_version(),
        "Mode":           view,
        "Temperature":    temperature,
        "Num_Ctx":        num_ctx,
        "Num_Predict":    num_predict,
        "Prompt_Hash":    PROMPT_HASH,
    }

# ==============================================================================
# FULL-TRACE VIEWS (general, wide) — all questions, one CSV per trace
# ==============================================================================

def run_full_view(view: str, model_name: str, csv_folder: str, output_folder: str,
                  num_ctx: int, num_predict: int = 1024,
                  trace_filter: str = None, temperature: float = 0, timeout: int = 600,
                  retries: int = 1, max_failures: int = 3):
    """
    Answers ALL_QUESTIONS using the CSV of the given view ("general" or "wide")
    for each trace.
    The general view has no header row, so csv_rows counts every non-blank line.
    For the "wide" view the header is assumed to be present only if it is not "general".
    """
    view_folder = os.path.join(csv_folder, view)
    if not os.path.exists(view_folder):
        print(f"⚠️  {view} CSV folder not found: {view_folder}")
        return

    traces = sorted(f for f in os.listdir(view_folder) if f.endswith(".csv"))

    if trace_filter:
        traces = [f for f in traces if os.path.splitext(f)[0] == trace_filter]
        if not traces:
            print(f"⚠️  Trace not found: {trace_filter}")
            return

    out_dir = os.path.join(output_folder, view)
    os.makedirs(out_dir, exist_ok=True)

    view_description = VIEW_DESCRIPTIONS.get(view)
    has_header = (view != "general")   # general: no header row; adjust if your wide CSVs differ

    print(f"\n[{view}] Measuring context limit and question overhead for {model_name}...")
    context_limit = get_model_context_limit(model_name)
    if context_limit is not None and num_ctx > context_limit:
        print(f"⚠️  num_ctx ({num_ctx}) > model max context ({context_limit})")
    overhead_cache = build_overhead_cache(model_name, constants.ALL_QUESTIONS, view_description, num_ctx)
    print(f"[{view}] context_limit={context_limit}  num_ctx={num_ctx}  num_predict={num_predict}  "
          f"prompt={PROMPT_HASH}  ollama={get_ollama_version()}")

    for csv_file in traces:
        trace_stem = os.path.splitext(csv_file)[0]
        print(f"\n[{view}] Processing: {trace_stem}")

        csv_data = load_csv(csv_folder, view, trace_stem)
        if csv_data is None:
            continue

        csv_rows = count_data_rows(csv_data, has_header)
        csv_empty = csv_rows == 0
        if csv_empty:
            print(f"  ℹ️  [{view}] CSV has no data rows")

        questions_results = {}
        consecutive_failures = 0
        for question in constants.ALL_QUESTIONS:
            print(f"  Q: {question[:60]}...")
            if max_failures and consecutive_failures >= max_failures:
                print(f"    ⏭️  skipped after {consecutive_failures} consecutive failures")
                result = _error_result(
                    f"{SKIPPED_PREFIX} after {consecutive_failures} consecutive failures", 0,
                    overhead_cache.get(question, -1), context_limit, num_ctx, num_predict)
            else:
                result = ask_question(
                    model_name, question, csv_data, view_description,
                    num_ctx=num_ctx,
                    num_predict=num_predict,
                    timeout=timeout,
                    temperature=temperature,
                    question_tokens=overhead_cache.get(question, -1),
                    context_limit=context_limit,
                    retries=retries,
                )
                consecutive_failures = consecutive_failures + 1 if result["answer"].startswith("ERROR") else 0
            result["csv_rows"] = csv_rows
            result["csv_empty"] = csv_empty
            questions_results[question] = result

        output = _output_header(trace_stem, model_name, view, temperature, num_ctx, num_predict)
        output["Metrics"] = _aggregate_metrics(questions_results, context_limit, num_ctx, num_predict)
        output["Questions"] = questions_results

        out_path = os.path.join(out_dir, f"{trace_stem}_answers.json")
        save_json_to_file(output, out_path)
        print(f"  ✅ Saved: {out_path}")

# ==============================================================================
# FILTERED MODE — layer-specific questions + layer-specific CSV
# ==============================================================================

def run_filtered(model_name: str, csv_folder: str, output_folder: str,
                 num_ctx: int, num_predict: int = 1024,
                 trace_filter: str = None, temperature: float = 0, timeout: int = 600,
                 retries: int = 1, max_failures: int = 3):
    """
    For each trace, answers each layer's questions using its specific CSV.
    Traces are discovered as the intersection of stems across all layer folders.
    All layers are combined into a single JSON per trace.
    A layer CSV WITHOUT DATA ROWS (0 bytes, or only the header row: trace without packets
    of that protocol) is still sent to the model (flagged csv_empty=True, csv_rows=0);
    only a MISSING file is an error.
    """
    layer_stems = []
    for layer in LAYER_QUESTIONS:
        layer_folder = os.path.join(csv_folder, layer)
        if os.path.exists(layer_folder):
            stems = {os.path.splitext(f)[0] for f in os.listdir(layer_folder) if f.endswith(".csv")}
            layer_stems.append(stems)

    if not layer_stems:
        print(f"⚠️  No layer folders found in: {csv_folder}")
        return

    traces = sorted(set.intersection(*layer_stems))

    if trace_filter:
        traces = [t for t in traces if t == trace_filter]
        if not traces:
            print(f"⚠️  Trace not found: {trace_filter}")
            return

    out_dir = os.path.join(output_folder, "filtered")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n[filtered] Measuring context limit and question overhead for {model_name}...")
    context_limit = get_model_context_limit(model_name)
    if context_limit is not None and num_ctx > context_limit:
        print(f"⚠️  num_ctx ({num_ctx}) > model max context ({context_limit})")
    overhead_cache = {}
    for layer, questions in LAYER_QUESTIONS.items():
        overhead_cache.update(
            build_overhead_cache(model_name, questions, None, num_ctx)
        )
    print(f"[filtered] context_limit={context_limit}  num_ctx={num_ctx}  num_predict={num_predict}  "
          f"prompt={PROMPT_HASH}  ollama={get_ollama_version()}")

    for trace_stem in traces:
        print(f"\n[filtered] Processing: {trace_stem}")

        questions_results = {}

        for layer, questions in LAYER_QUESTIONS.items():
            csv_data = load_csv(csv_folder, layer, trace_stem)
            if csv_data is None:
                for question in questions:
                    result = _error_result("CSV not found", 0, overhead_cache.get(question, -1),
                                           context_limit, num_ctx, num_predict)
                    result["csv_source"] = layer
                    result["csv_rows"] = None
                    result["csv_empty"] = None
                    questions_results[question] = result
                continue

            # Filtered CSVs have a header row: data rows = non-blank lines - 1.
            csv_rows = count_data_rows(csv_data, has_header=True)
            csv_empty = csv_rows == 0
            if csv_empty:
                print(f"  ℹ️  [{layer}] CSV has no data rows (no packets of this protocol)")

            view_description = None   # the CSV header already names the columns
            consecutive_failures = 0     # the breaker is per layer: each layer has its own CSV size
            for question in questions:
                print(f"  [{layer}] Q: {question[:60]}...")
                if max_failures and consecutive_failures >= max_failures:
                    print(f"    ⏭️  skipped after {consecutive_failures} consecutive failures")
                    result = _error_result(
                        f"{SKIPPED_PREFIX} after {consecutive_failures} consecutive failures", 0,
                        overhead_cache.get(question, -1), context_limit, num_ctx, num_predict)
                else:
                    result = ask_question(
                        model_name, question, csv_data, view_description,
                        num_ctx=num_ctx,
                        num_predict=num_predict,
                        timeout=timeout,
                        temperature=temperature,
                        question_tokens=overhead_cache.get(question, -1),
                        context_limit=context_limit,
                        retries=retries,
                    )
                    consecutive_failures = consecutive_failures + 1 if result["answer"].startswith("ERROR") else 0
                result["csv_source"] = layer
                result["csv_rows"] = csv_rows
                result["csv_empty"] = csv_empty
                questions_results[question] = result

        output = _output_header(trace_stem, model_name, "filtered", temperature, num_ctx, num_predict)
        output["Metrics"] = _aggregate_metrics(questions_results, context_limit, num_ctx, num_predict)
        output["Questions"] = questions_results

        out_path = os.path.join(out_dir, f"{trace_stem}_answers.json")
        save_json_to_file(output, out_path)
        print(f"  ✅ Saved: {out_path}")

# ==============================================================================
# MODEL HELPERS
# ==============================================================================

def get_model_context_limit(model_name: str) -> int | None:
    """
    Queries Ollama for the model's MAXIMUM context window (in tokens). This is not
    the window actually used: that is the num_ctx passed with --num-ctx.
    Returns None if it cannot be determined.
    """
    try:
        info = ollama.show(model_name)
        model_info = info.modelinfo or {}
        for key, value in model_info.items():
            if key.endswith("context_length"):
                return int(value)
    except Exception as e:
        print(f"⚠️  Could not determine context limit for {model_name}: {e}")
    return None


def measure_question_overhead(model_name: str, question: str, view_description: str | None,
                              timeout: int = 600, num_ctx: int | None = None) -> int:
    """
    Measures how many tokens the fixed template + view description + question
    consume ALONE (empty DATA section), using the model's own tokenizer via Ollama.
    Uses num_predict=1 to keep this measurement call cheap. The generous timeout
    covers the first call, which also loads the model.
    """
    prompt = build_prompt(question, "", view_description)
    options = {"temperature": 0, "num_predict": 1}
    if num_ctx:
        options["num_ctx"] = num_ctx

    try:
        client = ollama.Client(timeout=timeout)
        response = client.generate(model=model_name, prompt=prompt, options=options)
        return response.prompt_eval_count if response.prompt_eval_count else -1
    except Exception as e:
        print(f"⚠️  Could not measure overhead for question '{question[:40]}...': {e}")
        return -1


def build_overhead_cache(model_name: str, questions: list, view_description: str | None,
                         num_ctx: int | None = None) -> dict:
    """
    Precomputes the template + question token overhead once per unique question
    text for a given view description, so it is not re-measured per trace.
    """
    cache = {}
    for question in questions:
        if question not in cache:
            cache[question] = measure_question_overhead(
                model_name, question, view_description, num_ctx=num_ctx
            )
    return cache

# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Answer network trace questions using a local Ollama model.")
    parser.add_argument("--model",       required=True,  help="Ollama model name (e.g. llama3.2:3b)")
    parser.add_argument("--num-ctx",     type=int, default=None, help="Context window passed to Ollama (num_ctx). Default: the model's own maximum context length, read from Ollama, so every model uses its full context. Pass a value to cap it (KV-cache memory grows with it).")
    parser.add_argument("--num-predict", type=int, default=1024, help="Maximum output tokens (default: 1024)")
    parser.add_argument("--run",         default="run1", help="Run identifier (default: run1)")
    parser.add_argument("--results-dir", default="results/basic", help="Root folder for the model outputs (default: results/basic)")
    parser.add_argument("--trace",       default=None, help="Run only this trace stem (e.g. Monday-WorkingHours_300pkts). Default: all traces.")
    parser.add_argument("--csv-folder",  default="data/traces/processed_csv", help="Base folder with per-view CSV subfolders")
    parser.add_argument("--mode",        default="all", choices=["general", "wide", "filtered", "all"], help="Which view(s) to run (default: all = general + filtered; 'wide' only when requested)")
    parser.add_argument("--temperature", type=float, default=0, help="Sampling temperature (default: 0)")
    parser.add_argument("--timeout",     type=int, default=600, help="Timeout in seconds of the first attempt of each question; retries use 2x, 3x... (default: 600)")
    parser.add_argument("--retries",     type=int, default=1, help="Retries per question after a timeout or a transient server/connection error (default: 1)")
    parser.add_argument("--max-consecutive-failures", type=int, default=3, help="Skip the rest of a view/layer after this many consecutive failed questions, to avoid hours of timeouts on a prompt that is too slow (0 = never skip; default: 3)")
    args = parser.parse_args()

    # Context window: explicit value, or the model's own maximum. Never the server default,
    # which varies between models/memory and can truncate the prompt silently.
    num_ctx = args.num_ctx or get_model_context_limit(args.model)
    if not num_ctx:
        parser.error("Could not read the model's context length from Ollama; pass --num-ctx explicitly.")
    print(f"num_ctx = {num_ctx} ({'given with --num-ctx' if args.num_ctx else 'model maximum'})")

    output_base = os.path.join(args.results_dir, args.model, args.run, "llm_answers")

    common = dict(
        model_name=args.model,
        csv_folder=args.csv_folder,
        output_folder=output_base,
        num_ctx=num_ctx,
        num_predict=args.num_predict,
        trace_filter=args.trace,
        temperature=args.temperature,
        timeout=args.timeout,
        retries=args.retries,
        max_failures=args.max_consecutive_failures,
    )

    if args.mode in ("general", "all"):
        run_full_view("general", **common)

    if args.mode == "wide":   # the wide view is not part of "all" for now
        run_full_view("wide", **common)

    if args.mode in ("filtered", "all"):
        run_filtered(**common)