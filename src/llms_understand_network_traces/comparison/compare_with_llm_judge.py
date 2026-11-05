"""
compare_with_llm_judge.py
================================================================================
LLM-as-a-Judge comparison module.

Compares pyshark ground truth answers against LLM answers using a judge LLM.

Prompting strategies applied (Li et al., 2024 - "From Generation to Judgment"):
  - Rule Augmentation:    explicit rubric with criteria per answer type
  - Swapping Operation:   two passes (position swap) to detect position bias
  - Demonstration:        examples per answer type to calibrate the judge
  - Chain-of-thought:     judge reasons (briefly) before giving the label
  - Structured output:    JSON {reasoning, label} enforced with a JSON schema

Labels in the output:
  C / P / I  judged answers (Correct / Partial / Incorrect)
  E          judge error (no valid verdict) -> excluded from C/P/I percentages
  N          the LLM produced no answer (timeout / error / missing) -> excluded
             from C/P/I percentages (a view-size effect, not a reasoning error)

Changes vs previous version:
  - Rubric updated to the current questions and prompt:
      * "None", "No X found" and "Not found in trace" are all equivalent (no items).
      * Right identifier + wrong number (count) -> Partial, never Incorrect.
      * Right ports/addresses in the wrong direction -> Partial, never Incorrect.
      * Sender/Target MAC labels added to the label equivalences.
      * OUI-resolved MAC equivalence kept (should not appear with tshark -n).
  - There is no special abstention handling: every answer is sent to the judge.
  - LLM errors are labelled N instead of I.
  - LLM metadata (csv_empty, csv_rows, tokens_input...) is copied to the result.
  - rubric_hash / prompt_hash stored for traceability.
"""

import os
import json
import hashlib
import argparse
import ollama
import httpx

from llms_understand_network_traces.utils.utils import save_json_to_file

# ==============================================================================
# JUDGE CONFIG
# ==============================================================================

JUDGE_KEEP_ALIVE  = "30m"   # keep the judge loaded between calls

# Context window: computed per prompt. Estimate is deliberately conservative
# because MACs / IPs / port lists tokenize badly (~2.5 chars per token).
CHARS_PER_TOKEN   = 2.5
JUDGE_NUM_CTX_MIN = 4096
JUDGE_NUM_CTX_MAX = 16384   # ~0.3 MB of KV cache per token on a 70B model; raise if you have VRAM

# Attempts, in order: (timeout_s, num_predict, with_reasoning)
#   1) normal call
#   2) longer timeout and larger output cap (for truncated / slow generations)
#   3) label-only answer: fast, but no chain-of-thought -> flagged "degraded"
JUDGE_ATTEMPTS = [
    (300,  768, True),
    (600, 2048, True),
    (300,   32, False),
]

VALID_LABELS = ("C", "P", "I")
LABEL_RANK = {"C": 3, "P": 2, "I": 1}   # used to resolve pass1/pass2 disagreements

_LABEL_PROP = {"type": "string", "enum": list(VALID_LABELS)}
JUDGE_SCHEMA_FULL = {
    "type": "object",
    "properties": {"reasoning": {"type": "string"}, "label": _LABEL_PROP},
    "required": ["reasoning", "label"],
}
JUDGE_SCHEMA_LABEL = {
    "type": "object",
    "properties": {"label": _LABEL_PROP},
    "required": ["label"],
}

# ==============================================================================
# RUBRIC + DEMONSTRATIONS
# ==============================================================================

RUBRIC = """
You are a strict network traffic analysis evaluator.
Your task is to judge whether a CANDIDATE answer correctly answers a question
about a network trace, given the REFERENCE answer as ground truth.

EVALUATION CRITERIA (apply in order):
1. Factual completeness: does the candidate contain all elements present in the reference?
2. Factual precision:    does the candidate introduce elements NOT present in the reference?
3. Format is irrelevant: ignore differences in order, formatting, or phrasing.
4. Empty results: if the reference states that there are no items (for example "None" or
   "No X found"), the candidate must also state that there are none. "None", "No X found"
   and "Not found in trace" all count as stating that there are none. If the reference is
   empty and the candidate lists any item, it is Incorrect (I).
5. Duplicate elements: if the candidate repeats the same correct element multiple times,
   ignore the duplicates — treat it as listed once. Repetition is a formatting issue, not a factual error.
6. Set matching: when both answers contain the same set of elements in different order,
   treat them as identical. Match each element from the reference against ALL elements
   in the candidate, not just the element at the same position.
7. Numbers attached to an element (for example packet counts): they must match the reference.
   If an element has the right identifier (IP address, port) but a wrong number, it is a
   PARTIAL match: it prevents the label C, but it is not a completely wrong element.
8. Direction in pairs: "A -> B" and "B -> A" contain the same two ports but are different
   elements. A reversed pair is a PARTIAL match: it prevents the label C, but it is not
   a completely wrong element.

EQUIVALENCES (treat these as identical):
- MAC addresses may appear in full format (08:00:27:12:c4:2f) or OUI-resolved format
  (PCSSystemtec_12:c4:2f). These refer to the same address — treat them as equivalent.
- Field label abbreviations are equivalent:
  "Src MAC" = "Source MAC address" = "source MAC" = "src_mac"
  "Dst MAC" = "Destination MAC address" = "destination MAC" = "dst_mac"
  "Sender MAC" = "Sender MAC address" = "sender hardware address" = "sender_mac"
  "Target MAC" = "Target MAC address" = "target hardware address" = "target_mac"
  "Sender IP" = "Sender IP address" = "sender_ip"
  "Target IP" = "Target IP address" = "target_ip"
- Empty results: "None", "No X found", "X: None" and "Not found in trace" all mean the
  same thing (there are no items).

LABELS:
  C (Correct):   all reference elements are present with correct values AND no incorrect elements are added.
  P (Partial):   at least one reference element is present (fully, or partially: right identifier
                 with a wrong number, or a pair in the reversed direction), BUT something is
                 missing, wrong or extra.
  I (Incorrect): none of the reference elements is present, not even partially; or the answer is
                 empty or completely wrong; or the candidate states that there are no items
                 while the reference lists some.

DEMONSTRATIONS:
  Question: "List the unique MAC addresses of the hosts that send ARP packets"
  Reference: "08:00:27:12:c4:2f\n08:00:27:d1:7b:b1"
  Candidate: "08:00:27:12:c4:2f\n08:00:27:d1:7b:b1"
  → C  (all elements present, nothing extra)

  Question: "List the unique MAC addresses of the hosts that send ARP packets"
  Reference: "08:00:27:12:c4:2f\n08:00:27:d1:7b:b1"
  Candidate: "PCSSystemtec_12:c4:2f\nPCSSystemtec_d1:7b:b1"
  → C  (OUI-resolved format — same addresses as reference)

  Question: "List the unique MAC addresses of the hosts that send ARP packets"
  Reference: "08:00:27:12:c4:2f\n08:00:27:d1:7b:b1"
  Candidate: "08:00:27:12:c4:2f"
  → P  (one element missing)

  Question: "List the unique MAC addresses of the hosts that send ARP packets"
  Reference: "08:00:27:12:c4:2f\n08:00:27:d1:7b:b1"
  Candidate: "Not found in trace"
  → I  (the candidate says there are no items, but the reference lists two)

  Question: "List the unique MAC addresses of the hosts that send ARP packets"
  Reference: "08:00:27:12:c4:2f\n08:00:27:d1:7b:b1"
  Candidate: "aa:bb:cc:dd:ee:ff\n11:22:33:44:55:66"
  → I  (elements present but all incorrect — none match the reference)

  Question: "TCP: List the port pairs that successfully completed a TCP three-way handshake."
  Reference: "53322 -> 80\n41558 -> 22\n37912 -> 53"
  Candidate: "53322 -> 80\n41558 -> 22\n37912 -> 53\n55020 -> 443"
  → P  (all reference elements present but one incorrect element added)

  Question: "List the unique ARP flows found in the trace."
  Reference: "Flow A\nFlow B\nFlow C\nFlow D"
  Candidate: "Flow C\nFlow A\nFlow D\nFlow B"
  → C  (same 4 flows, different order — order is irrelevant for sets)

  Question: "List the unique values of the IPv4 protocol field."
  Reference: "17 - UDP\n6 - TCP\n1 - ICMP"
  Candidate: "17 - UDP\n6 - TCP\n1 - ICMP\n17 - UDP\n6 - TCP"
  → C  (correct elements present, duplicates ignored per Criterion 5)

  Question: "TCP: List the port pairs of TCP sessions closed with a FIN."
  Reference: "80 -> 49188\n1031 -> 88"
  Candidate: "49188 -> 80\n1031 -> 88"
  → P  (the first pair is reversed: a partial match, so the answer is not C)

  Question: "TCP: List the port pairs of TCP sessions closed with a FIN."
  Reference: "80 -> 49188\n1031 -> 88"
  Candidate: "49188 -> 80\n88 -> 1031"
  → P  (every pair has the right ports in the reversed direction: partial matches, never I)

  Question: "List the private IPv4 addresses. Report the packets in which each appears as source and as destination."
  Reference: "192.168.10.3 (as src: 120 packets, as dst: 90 packets)\n192.168.10.9 (as src: 100 packets, as dst: 130 packets)"
  Candidate: "192.168.10.3 (as src: 12 packets, as dst: 9 packets)\n192.168.10.9 (as src: 10 packets, as dst: 13 packets)"
  → P  (right addresses, wrong counts: partial matches, never I)

  Question: "List the private IPv4 addresses. Report the packets in which each appears as source and as destination."
  Reference: "192.168.10.3 (as src: 120 packets, as dst: 90 packets)\n192.168.10.9 (as src: 100 packets, as dst: 130 packets)"
  Candidate: "192.168.10.3 (as src: 120 packets, as dst: 90 packets)\n192.168.10.9 (as src: 100 packets, as dst: 130 packets)"
  → C  (addresses and counts all match)

  Question: "TCP: List the destination ports where a connection attempt was explicitly refused with a RST."
  Reference: "No explicitly refused TCP connection attempts found"
  Candidate: "None"
  → C  (both state that there are no items)

  Question: "TCP: List the destination ports where a connection attempt was explicitly refused with a RST."
  Reference: "No explicitly refused TCP connection attempts found"
  Candidate: "Not found in trace"
  → C  (both state that there are no items)

  Question: "TCP: List the destination ports where a connection attempt was explicitly refused with a RST."
  Reference: "No explicitly refused TCP connection attempts found"
  Candidate: "88"
  → I  (the candidate lists an item, but there are none)
"""

RUBRIC_HASH = hashlib.sha256(RUBRIC.encode("utf-8")).hexdigest()[:12]

# ==============================================================================
# PROMPT BUILDER
# ==============================================================================

def build_judge_prompt(question: str, gt_answer: str, llm_answer: str,
                       candidate_first: bool = False, with_reasoning: bool = True) -> str:
    """
    Roles are FIXED: GROUND TRUTH is always the reference, LLM ANSWER is always
    the candidate. `candidate_first` only changes the ORDER of the two blocks
    (position swap), it never changes who is judged against whom.
    """
    ref_block  = f"GROUND TRUTH (reference):\n{gt_answer}"
    cand_block = f"LLM ANSWER (candidate):\n{llm_answer}"
    blocks = [cand_block, ref_block] if candidate_first else [ref_block, cand_block]

    if with_reasoning:
        tail = (
            f"Think briefly (reasoning must be under 100 words; do NOT re-copy the answers):\n"
            f"1. Note which reference elements are missing from the candidate.\n"
            f"2. Note which candidate elements are not in the reference "
            f"(and which have a wrong number or a reversed direction).\n"
            f"3. Assign a label: C, P, or I.\n\n"
            f"Respond ONLY with a JSON object in this exact format:\n"
            f'{{"reasoning": "<short analysis>", "label": "<C|P|I>"}}\n'
            f"No text before or after the JSON."
        )
    else:
        tail = (
            f"Assign a label: C, P, or I.\n\n"
            f"Respond ONLY with a JSON object in this exact format:\n"
            f'{{"label": "<C|P|I>"}}\n'
            f"No text before or after the JSON."
        )

    return (
        f"{RUBRIC}\n\n"
        f"Now evaluate the following:\n\n"
        f"QUESTION: {question}\n\n"
        f"{blocks[0]}\n\n"
        f"{blocks[1]}\n\n"
        f"{tail}"
    )

# ==============================================================================
# SINGLE JUDGE CALL
# ==============================================================================

def _error_result(msg: str) -> dict:
    return {"reasoning": f"ERROR: {msg}", "label": None, "error": True,
            "degraded": False, "attempt": None}


def pick_num_ctx(prompt: str, num_predict: int) -> int:
    """Context needed for this prompt + output, rounded up to a multiple of 1024."""
    est = int(len(prompt) / CHARS_PER_TOKEN) + num_predict + 256
    ctx = ((est + 1023) // 1024) * 1024
    return max(JUDGE_NUM_CTX_MIN, ctx)


def call_judge(judge_model: str, build_prompt) -> dict:
    """
    build_prompt(with_reasoning: bool) -> str.
    Tries JUDGE_ATTEMPTS in order. Returns
    {"reasoning", "label", "error", "degraded", "attempt"}.
    label is None (error=True) only if every attempt failed — never defaults to "I".
    """
    last_error = "no attempts made"

    for i, (timeout, num_predict, with_reasoning) in enumerate(JUDGE_ATTEMPTS, start=1):
        prompt  = build_prompt(with_reasoning)
        num_ctx = pick_num_ctx(prompt, num_predict)

        if num_ctx > JUDGE_NUM_CTX_MAX:
            # Retrying cannot help; truncating silently would corrupt the verdict.
            return _error_result(
                f"Prompt too long for judge context (needs ~{num_ctx} > {JUDGE_NUM_CTX_MAX}); "
                f"raise JUDGE_NUM_CTX_MAX or shorten the answers"
            )

        client = ollama.Client(timeout=timeout)
        try:
            response = client.generate(
                model=judge_model,
                prompt=prompt,
                format=JUDGE_SCHEMA_FULL if with_reasoning else JUDGE_SCHEMA_LABEL,
                keep_alive=JUDGE_KEEP_ALIVE,
                options={"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict},
            )
        except httpx.TimeoutException:
            last_error = f"timeout after {timeout}s"
            print(f"  ⚠️  Judge {last_error} (attempt {i}/{len(JUDGE_ATTEMPTS)})")
            continue
        except Exception as e:
            return _error_result(str(e))   # connection/model errors: retrying will not help

        if getattr(response, "done_reason", None) == "length":
            last_error = f"output truncated at num_predict={num_predict}"
            print(f"  ⚠️  Judge {last_error} (attempt {i}/{len(JUDGE_ATTEMPTS)})")
            continue

        text = response.response.strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            last_error = f"JSON parse failed: {e} | raw[:200]={text[:200]!r}"
            print(f"  ⚠️  Judge {last_error[:80]} (attempt {i}/{len(JUDGE_ATTEMPTS)})")
            continue

        label = str(parsed.get("label", "")).strip().upper()
        if label not in VALID_LABELS:
            last_error = f"invalid label {label!r}"
            continue

        return {
            "reasoning": parsed.get("reasoning", ""),
            "label":     label,
            "error":     False,
            "degraded":  not with_reasoning,
            "attempt":   i,
        }

    return _error_result(f"all {len(JUDGE_ATTEMPTS)} attempts failed (last: {last_error})")

# ==============================================================================
# SWAPPING OPERATION (position swap)
# ==============================================================================

def judge_with_swap(judge_model: str, question: str, gt_answer: str, llm_answer: str) -> dict:
    """
    Position swap (Li et al., 2024). Roles are fixed (GT = reference, LLM = candidate):
    - Pass 1: GROUND TRUTH block first, LLM ANSWER second
    - Pass 2: LLM ANSWER block first, GROUND TRUTH second

    - Both valid and equal   -> that label, consistent=True
    - Both valid, different  -> lower label wins (C > P > I), consistent=False
    - Only one valid         -> that label, consistent=False, single_pass=True
    - Neither valid          -> "E" (judge error, excluded from C/P/I)
    """
    result1 = call_judge(
        judge_model,
        lambda wr: build_judge_prompt(question, gt_answer, llm_answer, candidate_first=False, with_reasoning=wr),
    )
    result2 = call_judge(
        judge_model,
        lambda wr: build_judge_prompt(question, gt_answer, llm_answer, candidate_first=True, with_reasoning=wr),
    )

    label1, label2 = result1["label"], result2["label"]
    single_pass = False

    if label1 is None and label2 is None:
        final_label, consistent = "E", False
    elif label1 is None or label2 is None:
        final_label = label1 or label2
        consistent, single_pass = False, True
    elif label1 == label2:
        final_label, consistent = label1, True
    else:
        final_label = min(label1, label2, key=lambda l: LABEL_RANK[l])
        consistent = False

    return {
        "final_label": final_label,
        "consistent":  consistent,
        "unanimous":   label1 is not None and label1 == label2,
        "single_pass": single_pass,
        "degraded":    bool(result1.get("degraded") or result2.get("degraded")),
        "votes":       {"pass1": label1, "pass2": label2},
        "pass1":       result1,
        "pass2":       result2,
    }


def sanitize_answer(text: str) -> str:
    """Remove non-printable control characters that break JSON parsing."""
    if not text:
        return text
    text = ''.join(
        c for c in text
        if c.isprintable() or c in ('\n', '\t')
    )
    return text.strip()

# ==============================================================================
# COMPARE ONE TRACE
# ==============================================================================

def _non_judged_entry(question, gt_answer, llm_answer, label, reason, meta) -> dict:
    """Entry for answers that are not sent to the judge (LLM error)."""
    return {
        "question":    question,
        "gt_answer":   gt_answer,
        "llm_answer":  llm_answer,
        "final_label": label,
        "consistent":  None,
        "unanimous":   None,
        "pass1":       {"reasoning": reason, "label": label},
        "pass2":       {"reasoning": reason, "label": label},
        **meta,
    }


def compare_trace(gt_path: str, llm_path: str, judge_model: str) -> dict:
    with open(gt_path)  as f: gt_data  = json.load(f)
    with open(llm_path) as f: llm_data = json.load(f)

    gt_questions  = gt_data.get("Questions", {})
    llm_questions = llm_data.get("Questions", {})

    only_gt, only_llm = set(gt_questions) - set(llm_questions), set(llm_questions) - set(gt_questions)
    if only_gt or only_llm:
       raise ValueError(
           f"Question sets differ between GT and LLM output "
           f"({len(only_gt)} only in GT, {len(only_llm)} only in LLM). "
           f"The GT was probably generated with a different version of the questions: "
           f"regenerate it. GT: {gt_path} | LLM: {llm_path}"
       )

    results = {}
    for question, gt_answer in gt_questions.items():
        print(f"  Q: {question[:70]}...")

        llm_entry = llm_questions.get(question)
        if llm_entry is None:
            results[question] = _non_judged_entry(
                question, gt_answer, "ERROR: Question not found in LLM output",
                "N", "Question not found in LLM output", {},
            )
            continue

        llm_answer = llm_entry.get("answer", llm_entry) if isinstance(llm_entry, dict) else llm_entry
        meta = (
            {k: llm_entry.get(k) for k in (
                "truncation_suspected", "margin_violated", "output_truncated",
                "csv_empty", "csv_rows", "tokens_input",
            )}
            if isinstance(llm_entry, dict) else {}
        )

        # The LLM produced no answer (timeout / error): not a reasoning error.
        if str(llm_answer).startswith("ERROR"):
            results[question] = _non_judged_entry(
                question, gt_answer, llm_answer, "N", "LLM error (no answer produced)", meta,
            )
            continue

        swap_result = judge_with_swap(
            judge_model,
            question,
            sanitize_answer(str(gt_answer)),
            sanitize_answer(str(llm_answer))
        )

        results[question] = {
            "question":   question,
            "gt_answer":  gt_answer,
            "llm_answer": llm_answer,
            **meta,
            **swap_result,
        }

    # Summary: judge errors ("E") and missing LLM answers ("N") are excluded
    # from C/P/I and their percentages.
    labels       = [v.get("final_label", "I") for v in results.values()]
    total        = len(labels)
    judge_errors = labels.count("E")
    no_answer    = labels.count("N")
    evaluated    = total - judge_errors - no_answer
    inconsistent = sum(1 for v in results.values()
                       if "votes" in v and v.get("final_label") != "E" and not v.get("consistent", True))
    unanimous    = sum(1 for v in results.values() if v.get("unanimous"))
    degraded     = sum(1 for v in results.values() if v.get("degraded", False))
    prompt_truncated = sum(1 for v in results.values() if v.get("truncation_suspected"))
    output_truncated = sum(1 for v in results.values() if v.get("output_truncated"))

    def pct(n):
        return round(n / evaluated * 100, 1) if evaluated else 0

    summary = {
        "total":              total,
        "evaluated":          evaluated,
        "judge_errors":       judge_errors,
        "no_answer":          no_answer,
        "prompt_truncated_suspected": prompt_truncated,
        "output_truncated":   output_truncated,
        "C":                  labels.count("C"),
        "P":                  labels.count("P"),
        "I":                  labels.count("I"),
        "C_pct":              pct(labels.count("C")),
        "P_pct":              pct(labels.count("P")),
        "I_pct":              pct(labels.count("I")),
        "inconsistent_swaps": inconsistent,
        "unanimous":          unanimous,
        "degraded":           degraded,
    }

    return {
        "gt_file":        gt_path,
        "llm_file":       llm_path,
        "judge_model":    judge_model,
        "llm_model":      llm_data.get("Model", "unknown"),
        "mode":           llm_data.get("Mode", "unknown"),
        "temperature":    llm_data.get("Temperature", None),
        "prompt_hash":    llm_data.get("Prompt_Hash"),
        "rubric_hash":    RUBRIC_HASH,
        "summary":        summary,
        "questions":      results,
    }

# ==============================================================================
# ORCHESTRATOR
# ==============================================================================

def run_judge_evaluation(
    gt_folder:     str,
    llm_folder:    str,
    output_folder: str,
    judge_model:   str,
):
    os.makedirs(output_folder, exist_ok=True)

    gt_files  = {f for f in os.listdir(gt_folder)  if f.endswith(".json")}
    llm_files = {f for f in os.listdir(llm_folder) if f.endswith(".json")}
    common    = gt_files & llm_files

    if not common:
        print(f"⚠️  No matching files between:\n  {gt_folder}\n  {llm_folder}")
        return

    for filename in sorted(common):
        gt_path  = os.path.join(gt_folder,  filename)
        llm_path = os.path.join(llm_folder, filename)
        out_path = os.path.join(output_folder, f"judge_{filename}")

        print(f"\n[Judge: {judge_model}] {filename}")
        result = compare_trace(gt_path, llm_path, judge_model)
        save_json_to_file(result, out_path)

        s = result["summary"]
        print(f"  C: {s['C']} ({s['C_pct']}%)  "
              f"P: {s['P']} ({s['P_pct']}%)  "
              f"I: {s['I']} ({s['I_pct']}%)  "
              f"no answer: {s['no_answer']}  "
              f"judge errors: {s['judge_errors']}/{s['total']}  "
              f"degraded: {s['degraded']}  "
              f"inconsistent swaps: {s['inconsistent_swaps']}")
        print(f"  → Saved: {out_path}")

# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge evaluation of LLM answers vs pyshark ground truth.")
    parser.add_argument("--judge-model",   default="llama3.3:70b", help="Ollama model to use as judge")
    parser.add_argument("--gt-folder",     required=True,         help="Folder with ground truth JSONs")
    parser.add_argument("--llm-folder",    required=True,         help="Folder with LLM answer JSONs")
    parser.add_argument("--output-folder", required=True,         help="Folder to save judge evaluation results")
    args = parser.parse_args()

    run_judge_evaluation(
        gt_folder=args.gt_folder,
        llm_folder=args.llm_folder,
        output_folder=args.output_folder,
        judge_model=args.judge_model,
    )