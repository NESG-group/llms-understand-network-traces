"""
make_context_levels_pcap.py
================================================================================
Para UN modelo y UN run: elige una ventana contigua aleatoria (semilla = run) de
un pcap fuente grande, calcula cuántos paquetes caben en cada nivel de contexto
(contando tokens sobre el CSV general REAL) y escribe un pcapng por nivel.

Flujo (modo por defecto = generar):
  1. Presupuesto de datos del modelo:
        (num_ctx - overhead_max - num_predict) * (1 - margen)
     overhead_max = plantilla de build_prompt + descripción de la vista general
     + la pregunta más larga de constants.ALL_QUESTIONS (tokenizer del modelo).
  2. Ventana contigua aleatoria del pcap fuente (editcap). El inicio depende SOLO
     del run (no del modelo), así los modelos comparten inicio.
  3. Se renderiza la ventana con pcap2csvGeneral (tu script de preprocesado) y se
     cuentan tokens por bloques con el tokenizer del modelo, hasta cubrir el
     mayor objetivo.
  4. Niveles anidados (prefijos de la misma ventana). Por defecto:
        100 -> 1.25 del presupuesto (NO cabe),  75 -> 1.00,  50 -> 0.75,  25 -> 0.50
  5. Se escribe un pcapng por nivel (editcap 1-N) en la carpeta de preparación
     y un manifest.json.

Modo --verify (paso posterior, tras generar):
  Renderiza el CSV general real de cada pcap de la carpeta de preparación, recuenta
  sus tokens, comprueba el % real del contexto y que cada CSV es prefijo de la ventana.

Requisitos: ollama en marcha, tshark y editcap en el PATH.

Uso:
    python make_context_levels_pcap.py --model llama3.1:8b --run 1 \
        --source data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng \
        --disable-protocol <los que uses en cicids>

    python make_context_levels_pcap.py --model llama3.1:8b --run 1 \
        --source data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng \
        --disable-protocol <los mismos> --verify
"""

import os
import re
import sys
import json
import random
import argparse
import subprocess
import importlib.util
from pathlib import Path

import ollama

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "utils" / "constants.py").exists())
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "evaluation"))

import utils.constants as constants
import answer_with_llm as gen   # build_prompt, GENERAL_DESCRIPTION, get_model_context_limit

COUNT_NUM_CTX = 32768     # contexto usado SOLO para medir bloques
BLOCK_FILL    = 0.40      # fracción de COUNT_NUM_CTX que ocupa cada bloque
TIMEOUT       = 900
DEFAULT_LEVELS = "100:1.25,75:1.0,50:0.75,25:0.5"
VIEW_DESC = gen.GENERAL_DESCRIPTION


# ==============================================================================
# PREPROCESADO (se importa tu script para que el renderizado sea idéntico)
# ==============================================================================

def load_preprocess(path=None):
    """Importa tu script de preprocesado. Si no se indica, lo busca por su función."""
    needle = "def " + "pcap2csvGeneral"
    me = Path(__file__).resolve()
    if path is None:
        candidates = sorted((ROOT / "src").rglob("*.py")) + sorted(ROOT.glob("*.py"))
        for p in candidates:
            if p.resolve() == me:
                continue
            try:
                if needle in p.read_text(errors="ignore"):
                    path = p
                    break
            except OSError:
                pass
    if path is None:
        sys.exit("No encuentro tu script de preprocesado; indícalo con --preprocess-script.")
    spec = importlib.util.spec_from_file_location("preprocess_mod", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, Path(path)


def render_general(mod, pcap: Path, out_base: Path, disable_protocols) -> tuple:
    csv_path = mod.pcap2csvGeneral(str(pcap), base_folder=str(out_base),
                                   disable_protocols=tuple(disable_protocols))
    return read_lines(csv_path), csv_path


# ==============================================================================
# HERRAMIENTAS DE PCAP
# ==============================================================================

def count_packets(pcap: Path) -> int:
    r = subprocess.run(["tshark", "-n", "-r", str(pcap), "-T", "fields", "-e", "frame.number"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"tshark falló al contar paquetes de {pcap}: {r.stderr[:200]}")
    return sum(1 for l in r.stdout.splitlines() if l.strip())


def cut(src: Path, dst: Path, first: int, last: int):
    """Conserva los paquetes first..last (numeración 1-based), con sus timestamps."""
    subprocess.run(["editcap", "-r", "-F", "pcapng", str(src), str(dst), f"{first}-{last}"], check=True)


def read_lines(csv_path) -> list:
    with open(csv_path, "r") as f:
        lines = f.readlines()
    return [l if l.endswith("\n") else l + "\n" for l in lines if l.strip()]


# ==============================================================================
# MEDICIÓN CON OLLAMA
# ==============================================================================

def nonce() -> str:
    """Prefijo aleatorio de ancho fijo: invalida la caché de prefijo de Ollama."""
    return f"ID{random.randint(100000, 999999)}\n"


def prompt_eval(client, model: str, prompt: str, num_ctx: int) -> int:
    r = client.generate(
        model=model, prompt=prompt, keep_alive="30m",
        options={"temperature": 0, "num_predict": 1, "num_ctx": num_ctx},
    )
    n = r.prompt_eval_count
    if not n:
        raise RuntimeError("Ollama no devolvió prompt_eval_count")
    return n


def setup_counting(client, model: str) -> dict:
    base = prompt_eval(client, model, "x", COUNT_NUM_CTX)
    nonce_cost = max(prompt_eval(client, model, nonce() + "x", COUNT_NUM_CTX) - base, 0)
    overheads = {}
    for q in constants.ALL_QUESTIONS:
        c = prompt_eval(client, model, nonce() + gen.build_prompt(q, "", VIEW_DESC), COUNT_NUM_CTX)
        overheads[q] = c - nonce_cost
    ref_q = max(overheads, key=overheads.get)
    return {
        "nonce_cost": nonce_cost,
        "overhead_max": overheads[ref_q],
        "baseline": overheads[ref_q] + nonce_cost,
        "ref_q": ref_q,
    }


def make_counter(client, model: str, st: dict):
    def count_fn(text: str) -> int:
        p = nonce() + gen.build_prompt(st["ref_q"], text, VIEW_DESC)
        return prompt_eval(client, model, p, COUNT_NUM_CTX) - st["baseline"]
    return count_fn


def choose_block_lines(count_fn, lines: list) -> int:
    n = min(100, len(lines))
    tpl = max(count_fn("".join(lines[:n])) / n, 1)
    return max(50, int(BLOCK_FILL * COUNT_NUM_CTX / tpl))


def count_blocks(count_fn, lines: list, target, block_lines: int) -> list:
    """Cuenta tokens de datos por bloques hasta cubrir `target` (o agotar las líneas)."""
    blocks, start, cum = [], 0, 0
    while cum < target and start < len(lines):
        end = min(start + block_lines, len(lines))
        t = count_fn("".join(lines[start:end]))
        if t + COUNT_NUM_CTX * 0.05 > COUNT_NUM_CTX * 0.95:
            raise RuntimeError("Un bloque se acerca al contexto de medición: reduce BLOCK_FILL.")
        blocks.append({"start": start, "end": end, "tokens": t, "cum_before": cum})
        cum += t
        start = end
        print(f"    bloque {len(blocks):>3}: líneas {blocks[-1]['start']:>7}-{end:<7} "
              f"{t:>7,} tokens   acumulado {cum:>9,}")
    return blocks


def lines_for_target(count_fn, lines: list, blocks: list, target: int):
    """Número de líneas N cuyos datos suman ~target tokens (refinado dentro del bloque)."""
    for b in blocks:
        if b["cum_before"] + b["tokens"] < target:
            continue
        size = b["end"] - b["start"]
        tpl = b["tokens"] / size
        k = max(1, int((target - b["cum_before"]) / tpl))
        total = b["cum_before"]
        for _ in range(4):
            k = min(max(k, 1), size)
            total = b["cum_before"] + count_fn("".join(lines[b["start"]:b["start"] + k]))
            diff = target - total
            if abs(diff) <= tpl:
                break
            k += int(diff / tpl)
        k = min(max(k, 1), size)
        return b["start"] + k, total
    return None, None


# ==============================================================================
# UTILIDADES
# ==============================================================================

def parse_levels(spec: str) -> list:
    out = []
    for item in spec.split(","):
        label, factor = item.split(":")
        out.append((label.strip(), float(factor)))
    return out


def model_tag(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9.\-]+", "-", model)


# ==============================================================================
# MODO GENERAR
# ==============================================================================

def generate(args, mod, client, ctx, count_model, levels, staging: Path, work: Path):
    print("\n[1/5] Midiendo plantilla + pregunta...")
    st = setup_counting(client, count_model)
    count_fn = make_counter(client, count_model, st)
    overhead_max = st["overhead_max"]
    print(f"      overhead máximo: {overhead_max:,} tokens (id de caché: {st['nonce_cost']})")

    available = ctx - overhead_max - args.num_predict
    budget = int((available) * (1 - args.margin))
    if budget <= 0:
        sys.exit("El presupuesto de datos es <= 0.")
    print(f"\n[2/5] Presupuesto de datos: {budget:,} tokens "
          f"(= {ctx:,} - {overhead_max:,} - {args.num_predict:,}, margen {args.margin:.0%})")
    max_target = int(max(f for _, f in levels) * budget)

    source = Path(args.source)
    total = count_packets(source)
    max_window = min(args.max_window, total)
    rng = random.Random(args.run)
    start = rng.randint(1, total - max_window + 1)
    print(f"\n[3/5] Fuente: {total:,} paquetes. Run {args.run} -> inicio de ventana: paquete {start:,} "
          f"(ventana máxima {max_window:,})")

    work.mkdir(parents=True, exist_ok=True)
    win_pcap = work / "window.pcapng"
    W = min(max_window, 8000)
    while True:
        last = start + W - 1
        cut(source, win_pcap, start, last)
        lines, csv_path = render_general(mod, win_pcap, work / "render", args.disable_protocol)
        if len(lines) != W:
            print(f"⚠️  El CSV tiene {len(lines):,} líneas y la ventana {W:,} paquetes: "
                  f"los N en líneas pueden no coincidir con paquetes. Revisa el preprocesado.")
        block_lines = choose_block_lines(count_fn, lines)
        print(f"      ventana {W:,} paquetes -> contando tokens (bloques de {block_lines} líneas)...")
        blocks = count_blocks(count_fn, lines, max_target, block_lines)
        got = sum(b["tokens"] for b in blocks)
        if got >= max_target:
            break
        if W >= max_window:
            sys.exit(f"La ventana máxima ({max_window:,} paquetes) solo aporta {got:,} tokens y el mayor "
                     f"nivel necesita {max_target:,}. Usa una fuente más grande o sube --max-window.")
        W = min(max_window, W * 2)
        print(f"      no llega al objetivo: se amplía la ventana a {W:,} paquetes")

    print("\n[4/5] Calculando niveles (anidados)...")
    base_stem = re.sub(r"_\d+pkts$", "", source.stem)
    tag = model_tag(args.model)
    rows = []
    for label, factor in levels:
        target = int(factor * budget)
        n, data_tokens = lines_for_target(count_fn, lines, blocks, target)
        if n is None:
            sys.exit(f"No se pudo calcular el nivel {label}.")
        prompt_tokens = data_tokens + overhead_max
        stem = f"{base_stem}_{tag}_run{args.run}_L{label}_{n}pkts"
        rows.append({
            "label": label, "factor": factor, "target_data_tokens": target,
            "packets": n, "est_data_tokens": data_tokens, "est_prompt_tokens": prompt_tokens,
            "est_pct_of_ctx": round(prompt_tokens / ctx * 100, 1),
            "fits": prompt_tokens + args.num_predict <= ctx,
            "stem": stem,
        })

    print(f"\n[5/5] Escribiendo pcapng en {staging} ...")
    staging.mkdir(parents=True, exist_ok=True)
    for r in rows:
        out = staging / f"{r['stem']}.pcapng"
        cut(win_pcap, out, 1, r["packets"])
        r["file"] = str(out)
        print(f"      nivel {r['label']}: {out.name}")

    print(f"\n{'nivel':>6} {'factor':>7} {'paquetes':>9} {'tokens datos':>13} {'prompt total':>13} {'% ctx':>7}  cabe")
    for r in rows:
        print(f"{r['label']:>6} {r['factor']:>7.2f} {r['packets']:>9,} {r['est_data_tokens']:>13,} "
              f"{r['est_prompt_tokens']:>13,} {r['est_pct_of_ctx']:>6}%  {'sí' if r['fits'] else 'NO'}")

    manifest = {
        "model": args.model, "count_model": count_model, "run": args.run, "seed": args.run,
        "source": str(source), "source_packets": total,
        "window_first_packet": start, "window_packets": W, "window_pcap": str(win_pcap),
        "window_csv": str(csv_path),
        "num_ctx": ctx, "num_predict": args.num_predict, "margin": args.margin,
        "overhead_max": overhead_max, "budget": budget,
        "disable_protocols": list(args.disable_protocol),
        "prompt_hash": gen.PROMPT_HASH,
        "levels": rows,
    }
    mpath = staging / "manifest.json"
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest: {mpath}")


# ==============================================================================
# MODO VERIFICAR
# ==============================================================================

def verify(args, mod, client, ctx, count_model, staging: Path, work: Path):
    mpath = staging / "manifest.json"
    if not mpath.exists():
        sys.exit(f"No existe {mpath}: ejecuta primero el modo generar.")
    with open(mpath) as f:
        manifest = json.load(f)

    st = setup_counting(client, count_model)
    count_fn = make_counter(client, count_model, st)
    window_lines = read_lines(manifest["window_csv"])
    ctx = manifest["num_ctx"]
    num_predict = manifest["num_predict"]
    overhead_max = st["overhead_max"]
    print(f"\nVerificando {len(manifest['levels'])} niveles (contexto {ctx:,}, overhead {overhead_max:,})...")

    all_ok = True
    for r in manifest["levels"]:
        pcap = Path(r["file"])
        lines, _ = render_general(mod, pcap, work / "verify", manifest["disable_protocols"])
        prefix_ok = lines == window_lines[:len(lines)] and len(lines) == r["packets"]
        block_lines = choose_block_lines(count_fn, lines)
        print(f"  nivel {r['label']}: contando {len(lines):,} líneas...")
        blocks = count_blocks(count_fn, lines, float("inf"), block_lines)
        data_tokens = sum(b["tokens"] for b in blocks)
        prompt_tokens = data_tokens + overhead_max
        rel_dev = abs(data_tokens - r["est_data_tokens"]) / max(r["est_data_tokens"], 1)
        r["real_data_tokens"] = data_tokens
        r["real_prompt_tokens"] = prompt_tokens
        r["real_pct_of_ctx"] = round(prompt_tokens / ctx * 100, 1)
        r["real_fits"] = prompt_tokens + num_predict <= ctx
        r["prefix_of_window"] = prefix_ok
        r["deviation_vs_estimate"] = round(rel_dev, 4)
        ok = prefix_ok and rel_dev <= args.tolerance and (r["real_fits"] == r["fits"])
        r["verified"] = ok
        all_ok &= ok

    print(f"\n{'nivel':>6} {'paquetes':>9} {'datos est.':>11} {'datos real':>11} {'desv.':>7} "
          f"{'% ctx real':>10} {'cabe':>5} {'prefijo':>8}  ok")
    for r in manifest["levels"]:
        print(f"{r['label']:>6} {r['packets']:>9,} {r['est_data_tokens']:>11,} {r['real_data_tokens']:>11,} "
              f"{r['deviation_vs_estimate']:>6.1%} {r['real_pct_of_ctx']:>9}% "
              f"{'sí' if r['real_fits'] else 'NO':>5} {'sí' if r['prefix_of_window'] else 'NO':>8}  "
              f"{'✔' if r['verified'] else '✘'}")

    manifest["verification"] = {"tolerance": args.tolerance, "all_ok": all_ok}
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print("\nTodo verificado." if all_ok else
          "\n⚠️  Algún nivel no pasa la verificación: revisa la tabla antes de ejecutar los modelos.")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    ap = argparse.ArgumentParser(description="Ventana aleatoria y niveles de contexto para un modelo y un run.")
    ap.add_argument("--model", required=True, help="Modelo del que se toma el contexto (p. ej. llama3.1:8b)")
    ap.add_argument("--count-model", default=None, help="Modelo con el mismo tokenizer para contar. Default: --model")
    ap.add_argument("--run", type=int, required=True, help="Número de run (es la semilla de la ventana)")
    ap.add_argument("--source", required=True, help="Pcap fuente grande (p. ej. 50000 paquetes)")
    ap.add_argument("--staging-dir", default=None,
                    help="Carpeta de salida. Default: data/cicids2017/staging/<modelo>_run<N>")
    ap.add_argument("--num-ctx", type=int, default=None, help="Contexto a usar. Default: máximo del modelo")
    ap.add_argument("--num-predict", type=int, default=1024, help="Debe coincidir con el de la generación")
    ap.add_argument("--margin", type=float, default=0.01)
    ap.add_argument("--levels", default=DEFAULT_LEVELS, help=f"etiqueta:factor separados por coma (default {DEFAULT_LEVELS})")
    ap.add_argument("--max-window", type=int, default=20000,
                    help="Ventana máxima en paquetes. Mantén el mismo valor en todos los modelos (fija el inicio)")
    ap.add_argument("--disable-protocol", nargs="*", default=[], metavar="PROTO",
                    help="Los MISMOS dissectors que usas al preprocesar cicids para la vista general")
    ap.add_argument("--preprocess-script", default=None, help="Ruta a tu script de preprocesado (si no, se busca)")
    ap.add_argument("--verify", action="store_true", help="Verifica los pcap ya generados en lugar de generarlos")
    ap.add_argument("--tolerance", type=float, default=0.02, help="Desviación relativa admitida en --verify (default 0.02)")
    args = ap.parse_args()

    count_model = args.count_model or args.model
    levels = parse_levels(args.levels)
    client = ollama.Client(timeout=TIMEOUT)

    ctx = args.num_ctx or gen.get_model_context_limit(args.model)
    if not ctx:
        sys.exit("No se pudo leer el contexto del modelo; usa --num-ctx.")

    mod, mod_path = load_preprocess(args.preprocess_script)
    staging = Path(args.staging_dir) if args.staging_dir else \
        Path("data/cicids2017/staging") / f"{model_tag(args.model)}_run{args.run}"
    work = staging / "_work"     # subcarpeta: el preprocesado solo lee los .pcapng de la carpeta principal

    print(f"Modelo: {args.model}   contexto: {ctx:,}   tokenizer de: {count_model}   run: {args.run}")
    print(f"Preprocesado: {mod_path}   disable-protocol: {args.disable_protocol or '(ninguno)'}")
    print(f"Carpeta de preparación: {staging}")

    if args.verify:
        verify(args, mod, client, ctx, count_model, staging, work)
    else:
        generate(args, mod, client, ctx, count_model, levels, staging, work)


if __name__ == "__main__":
    main()