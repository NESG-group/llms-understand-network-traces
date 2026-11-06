#!/usr/bin/env bash
# cicids_runs.sh — funciones para el experimento de contexto con CICIDS-2017
#
# Uso (desde la raíz del proyecto y con el entorno activado):
#   source .venv/bin/activate
#   source cicids_runs.sh          # carga las funciones en la terminal
#   prep  MODELO RONDA             # niveles + CSV de una ronda
#   gt    MODELO RONDA             # ground truth con pyshark (reintentos)
#   gtcopy ORIGEN DESTINO RONDA    # copia el GT si las trazas son idénticas
#   gtok  RONDA                    # gt_problems de los 4 modelos (debe dar [])
#   chk   MODELO RONDA             # prefijo de la ventana y filas por capa
#   st    FICHERO_LOG              # estado de una generación en segundo plano
#   tok   MODELO RONDA             # tokens estimados frente a reales
#   ver   MODELO RONDA             # --verify del recuento de tokens
#   jd    MODELO RONDA             # juez + dotplot de un modelo
#   chkj  MODELO RONDA             # rubric_hash y errores del juez
#   resumen RONDA                  # tabla de C/P/I de los 4 modelos
#
# En segundo plano (también se puede llamar como script):
#   nohup bash cicids_runs.sh genloop   RONDA MODELO... > logs/x.log 2>&1 &
#   nohup bash cicids_runs.sh judgeloop RONDA MODELO... > logs/y.log 2>&1 &
#
# NO lances nunca generación, juez o --verify a la vez: comparten la memoria de Ollama.

SRC=data/cicids2017/source/Monday-WorkingHours_50000pkts.pcapng
GT=results/ground_truth_cicids2017
CSV=data/cicids2017/processed_csv
JUDGE=llama3.3:70b
MODELS=(llama3.1:8b llama3.1:70b qwen2.5:7b qwen2.5:72b)

slug() { echo "${1//:/-}"; }
stg()  { echo "data/cicids2017/staging/$(slug "$1")_run$2"; }

stems() {   # MODELO RONDA -> nombres de las trazas, de menor a mayor
  python3 - "$(stg "$1" "$2")" <<'EOF'
import json, sys
m = json.load(open(sys.argv[1] + "/manifest.json"))
print(" ".join(l["stem"] for l in sorted(m["levels"], key=lambda l: l["packets"])))
EOF
}

# ---------------------------------------------------------------- preparación
prep() {   # MODELO RONDA
  local M=$1 R=$2
  mkdir -p logs
  python cicids_context.py --model "$M" --run "$R" --source "$SRC" 2>&1 \
    | tee "logs/ctx_$(slug "$M")_run$R.log"
  local L="logs/prep_$(slug "$M")_run$R.log"
  python src/preprocessing/convert_pcap_to_csv.py --input "$(stg "$M" "$R")" --output "$CSV" > "$L" 2>&1 \
    && echo "CSV generados (log: $L)" || echo "ERROR en el preprocesado, mira $L"
}

chk() {   # MODELO RONDA
  python3 - "$(stg "$1" "$2")" <<'EOF'
import json, sys
S = sys.argv[1]
P = "data/cicids2017/processed_csv"
m = json.load(open(f"{S}/manifest.json"))
win = open(m["window_csv"]).readlines()
for l in sorted(m["levels"], key=lambda l: l["packets"]):
    lines = open(f"{P}/general/{l['stem']}.csv").readlines()
    rows = {c: sum(1 for _ in open(f"{P}/{c}/{l['stem']}.csv")) - 1 for c in ("arp", "ip", "tcp", "udp")}
    print(f"{l['label']:>4} {l['packets']:>5} pkts  prefijo {lines == win[:len(lines)]}  filas {rows}")
EOF
}

# ---------------------------------------------------------------- ground truth
gt() {   # MODELO RONDA: una traza por proceso, hasta 5 intentos
  local M=$1 R=$2 S stem try
  S=$(stg "$M" "$R")
  mkdir -p /tmp/gt_backup
  for stem in $(stems "$M" "$R"); do
    for try in 1 2 3 4 5; do
      rm -rf /tmp/gt_single && mkdir -p /tmp/gt_single && cp "$S/$stem.pcapng" /tmp/gt_single/
      [ -f "$GT/${stem}_answers.json" ] && mv "$GT/${stem}_answers.json" "/tmp/gt_backup/${stem}_$(date +%H%M%S).json"
      python src/evaluation/answer_with_pyshark.py --input /tmp/gt_single --output "$GT" > /dev/null 2>&1
      if python -c "import main; print(main.gt_problems('$GT', '$S'))" 2>/dev/null | grep -q "$stem"; then
        echo "$stem: intento $try con ERROR"
      else
        echo "$stem: OK (intento $try)"; break
      fi
    done
  done
  python -c "import main; print('gt_problems:', main.gt_problems('$GT', '$S'))"
}

gtcopy() {   # ORIGEN DESTINO RONDA: copia el GT si los 5 CSV de cada nivel son idénticos
  python3 - "$(slug "$1")" "$(slug "$2")" "$3" <<'EOF'
import sys, json, os, shutil, filecmp
a, b, run = sys.argv[1:4]
P = "data/cicids2017/processed_csv"; GT = "results/ground_truth_cicids2017"
la = {l["label"]: l for l in json.load(open(f"data/cicids2017/staging/{a}_run{run}/manifest.json"))["levels"]}
lb = {l["label"]: l for l in json.load(open(f"data/cicids2017/staging/{b}_run{run}/manifest.json"))["levels"]}
os.makedirs("/tmp/gt_backup", exist_ok=True)
for lab in sorted(lb, key=lambda k: lb[k]["packets"]):
    if lab not in la or la[lab]["packets"] != lb[lab]["packets"]:
        print(f"L{lab}: distinto número de paquetes -> usa 'gt' para este modelo"); continue
    sa, sb = la[lab]["stem"], lb[lab]["stem"]
    if not all(filecmp.cmp(f"{P}/{c}/{sa}.csv", f"{P}/{c}/{sb}.csv", shallow=False)
               for c in ("general", "ip", "arp", "tcp", "udp")):
        print(f"L{lab}: CSV distintos -> usa 'gt' para este modelo"); continue
    dst = f"{GT}/{sb}_answers.json"
    if os.path.exists(dst):
        shutil.move(dst, f"/tmp/gt_backup/{sb}_answers_old.json")
    d = json.load(open(f"{GT}/{sa}_answers.json")); d["Filename"] = f"{sb}.pcapng"
    json.dump(d, open(dst, "w"), indent=4)
    print(f"L{lab}: GT copiado")
EOF
  python -c "import main; print('gt_problems:', main.gt_problems('$GT', '$(stg "$2" "$3")'))"
}

gtok() {   # RONDA
  local M
  for M in "${MODELS[@]}"; do
    echo -n "$M run$1 -> "
    python -c "import main; print(main.gt_problems('$GT', '$(stg "$M" "$1")'))"
  done
}

# ---------------------------------------------------------------- generación y juez
genloop() {   # RONDA MODELO... (uno tras otro; niveles de menor a mayor)
  local R=$1 M stem; shift
  for M in "$@"; do
    for stem in $(stems "$M" "$R"); do
      python -u main.py --dataset cicids --model "$M" --first-run "$R" --runs 1 --trace "$stem" --action llm
    done
  done
}

judgeloop() {   # RONDA MODELO...
  local R=$1 M; shift
  for M in "$@"; do
    python main.py --dataset cicids --model "$M" --judge "$JUDGE" --first-run "$R" --runs 1 --action judge \
      && python main.py --dataset cicids --model "$M" --judge "$JUDGE" --first-run "$R" --runs 1 --action dotplot
  done
}

jd() { judgeloop "$2" "$1"; }   # MODELO RONDA

# ---------------------------------------------------------------- comprobaciones
st() {   # FICHERO_LOG
  if pgrep -f "answer_with_llm|compare_with_llm_judge" > /dev/null; then
    echo "en curso: $(pgrep -af answer_with_llm | grep -o -- '--model [^ ]*\|--trace [^ ]*' | tr '\n' ' ')"
  else
    echo "nada en curso"
  fi
  echo "'Saved:' $(grep -c 'Saved:' "$1")   'All done' $(grep -c 'All done' "$1")"
  tail -n 3 "$1"
}

tok() {   # MODELO RONDA
  python3 - "$1" "$(stg "$1" "$2")" "$2" <<'EOF'
import json, sys
M, S, R = sys.argv[1:4]
for l in sorted(json.load(open(f"{S}/manifest.json"))["levels"], key=lambda l: l["packets"]):
    f = f"results/models/{M}/run{R}/llm_answers/general/{l['stem']}_answers.json"
    try:
        q = list(json.load(open(f))["Questions"].values())[0]
        print(f"{M} run{R} L{l['label']:<3} estimado {l.get('est_data_tokens', 0):>7,}  real {q['data_tokens']:>7,}  tokens_input {q['tokens_input']:>7,}  truncado {q['truncation_suspected']}")
    except FileNotFoundError:
        print(f"{M} run{R} L{l['label']:<3} (sin resultados)")
EOF
}

ver() { python cicids_context.py --model "$1" --run "$2" --source "$SRC" --verify; }   # MODELO RONDA

chkj() {   # MODELO RONDA
  grep -h '"rubric_hash"\|"judge_errors"\|"no_answer"' \
    results/models/$1/run$2/comparison/judge/*/judge_Monday*$(slug "$1")_run$2_*.json | sort | uniq -c
}

resumen() {   # RONDA
  python3 - "$1" <<'EOF'
import glob, json, re, sys
R = sys.argv[1]
MODELS = ["llama3.1:8b", "llama3.1:70b", "qwen2.5:7b", "qwen2.5:72b"]
pct = {25: 50, 50: 75, 75: 100, 100: 125}
data = {}
for model in MODELS:
    for mode in ("general", "filtered"):
        for f in glob.glob(f"results/models/{model}/run{R}/comparison/judge/{mode}/judge_Monday*_answers.json"):
            m = re.search(r"_L(\d+)_(\d+)pkts", f)
            data[(model, int(m.group(1)), mode)] = (int(m.group(2)), json.load(open(f))["summary"])
print(f"RONDA {R}")
print(f"{'modelo':<13}{'nivel':>10} {'pkts':>5} {'vista':<9} {'C':>3} {'P':>3} {'I':>3}  {'err.juez':>8} {'prompt trunc.':>13} {'salida cortada':>14} {'desempates':>10}")
for model in MODELS:
    for (mo, lvl, mode), (n, s) in sorted(((k, v) for k, v in data.items() if k[0] == model), key=lambda kv: (kv[0][1], kv[0][2])):
        print(f"{mo:<13}L{lvl:<3}({pct[lvl]:>3}%) {n:>5} {mode:<9} {s['C']:>3} {s['P']:>3} {s['I']:>3}  {s['judge_errors']:>8} {s['prompt_truncated_suspected']:>13} {s['output_truncated']:>14} {s['inconsistent_swaps']:>10}")
print("\nC (general / filtered)")
print(f"{'modelo':<13}" + "".join(f"{'L'+str(l)+' ('+str(pct[l])+'%)':>14}" for l in pct))
for model in MODELS:
    cells = []
    for l in pct:
        g, f = data.get((model, l, "general")), data.get((model, l, "filtered"))
        cells.append(f"{g[1]['C'] if g else '-'}/{f[1]['C'] if f else '-'}")
    print(f"{model:<13}" + "".join(f"{c:>14}" for c in cells))
EOF
}

# Si se ejecuta como script (bash cicids_runs.sh funcion args...), llama a la función.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  "$@"
fi
