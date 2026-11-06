import argparse
import json
import re
import time
import urllib.request
import uuid
from typing import Any

QUESTION = (
    "\n\nQuestion: in the data above, what are the numbers of the FIRST row and of the LAST row "
    "you can see? Answer exactly in the form: first=<number> last=<number>"
)


def build(rows: int) -> str:
    nonce = uuid.uuid4().hex[:12]
    body = "\n".join(f"ROW {i:06d} | alpha beta gamma delta epsilon zeta eta theta" for i in range(1, rows + 1))
    return f"Session {nonce}\n{body}{QUESTION}"


def call(host: str, model: str, prompt: str, num_ctx: int) -> tuple[dict[str, Any], float]:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": num_ctx, "temperature": 0, "num_predict": 24},
        }
    ).encode()
    request = urllib.request.Request(
        f"{host}/api/generate", data=payload, headers={"Content-Type": "application/json"}
    )
    start = time.time()
    with urllib.request.urlopen(request, timeout=7200) as response:
        data: dict[str, Any] = json.load(response)
    return data, time.time() - start


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check what Ollama does when the prompt exceeds num_ctx: for several fractions of the "
        "context it reports the tokens the server processed, the tokens expected, and the first and last "
        "numbered row the model says it sees. Processed close to num_ctx / 2 + 2 means the server halved "
        "the context. Uses the GPU: do not run it while a generation or the judge is running."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--num-ctx", type=int, required=True)
    parser.add_argument("--fractions", type=float, nargs="*", default=[0.5, 0.95, 1.25])
    parser.add_argument("--host", default="http://localhost:11434")
    args = parser.parse_args()

    small, _ = call(args.host, args.model, build(100), args.num_ctx)
    large, _ = call(args.host, args.model, build(400), args.num_ctx)
    n_small, n_large = small["prompt_eval_count"], large["prompt_eval_count"]
    tokens_per_row = (n_large - n_small) / 300
    overhead = n_small - 100 * tokens_per_row
    print(f"Model {args.model}, num_ctx {args.num_ctx}: {tokens_per_row:.2f} tokens per row, overhead {overhead:.0f}\n")
    print(f"{'fraction':>8} {'rows':>7} {'expected':>10} {'processed':>11} {'% ctx':>7}  {'first':>8} {'last':>8}  {'sec':>6}")
    for fraction in args.fractions:
        rows = max(10, int((fraction * args.num_ctx - overhead) / tokens_per_row))
        data, seconds = call(args.host, args.model, build(rows), args.num_ctx)
        expected = int(overhead + rows * tokens_per_row)
        processed = data["prompt_eval_count"]
        match = re.search(r"first\s*=\s*0*(\d+).*?last\s*=\s*0*(\d+)", data.get("response", ""), re.S)
        first, last = (match.group(1), match.group(2)) if match else ("?", "?")
        print(
            f"{fraction:>8.2f} {rows:>7} {expected:>10,} {processed:>11,} "
            f"{100 * processed / args.num_ctx:>6.1f}%  {first:>8} {last:>8}  {seconds:>6.0f}"
        )
        if processed < 0.9 * expected:
            print(
                f"         -> processed {processed:,} of {expected:,} expected ({100 * processed / expected:.0f} %); "
                f"half the context + 2 = {args.num_ctx // 2 + 2:,}"
            )
    print("\nNow run `ollama ps` (with the model still loaded) and read the CONTEXT column.")


if __name__ == "__main__":
    main()
