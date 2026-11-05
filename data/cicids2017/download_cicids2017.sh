#!/usr/bin/env bash
# ==============================================================================
# download_cicids2017.sh
# Descarga un pcap del dataset CIC-IDS-2017 (HuggingFace) y extrae un extracto.
#
# Nota: HuggingFace usa Xet storage y no soporta range requests, por lo que
# siempre se descarga el fichero completo. El pcap queda cacheado en
# ~/.cache/huggingface/ y no se vuelve a descargar en ejecuciones posteriores.
#
# Uso:
#   bash download_cicids2017.sh
#   bash download_cicids2017.sh --file Tuesday-WorkingHours.pcap
#   bash download_cicids2017.sh --file Tuesday-WorkingHours.pcap --max-packets 500
#   bash download_cicids2017.sh --file Tuesday-WorkingHours.pcap --duration 300
#
# Argumentos opcionales:
#   --file          Nombre del pcap en el repo HF  (default: Monday-WorkingHours.pcap)
#   --duration      Segundos a recortar (opcional, por defecto no se aplica)
#   --max-packets   Límite de paquetes             (default: 1000)
#   --out-dir       Directorio de salida           (default: ./output)
# ==============================================================================

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
HF_FILE="Monday-WorkingHours.pcap"
DURATION=""        # vacío = sin filtro de tiempo
MAX_PACKETS=1000
OUT_DIR="./output"

# ── Argumentos ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --file)          HF_FILE="$2";       shift 2 ;;
        --duration)      DURATION="$2";      shift 2 ;;
        --max-packets)   MAX_PACKETS="$2";   shift 2 ;;
        --out-dir)       OUT_DIR="$2";       shift 2 ;;
        *) echo "[ERROR] Argumento desconocido: $1"; exit 1 ;;
    esac
done

# ── Nombres de fichero ─────────────────────────────────────────────────────────
STEM="${HF_FILE%.pcap}"
mkdir -p "$OUT_DIR"
OUT_CLIP="${OUT_DIR}/${STEM}_${MAX_PACKETS}pkts.pcapng"

# ── Construir filtro tshark ───────────────────────────────────────────────────
TSHARK_FILTER=""
if [[ -n "$DURATION" ]]; then
    TSHARK_FILTER="-Y frame.time_relative < ${DURATION}"
fi

echo "============================================================"
echo "  Dataset      : bencorn/CICIDS2017 (HuggingFace)"
echo "  Fichero      : $HF_FILE"
echo "  Paquetes max : ${MAX_PACKETS}"
echo "  Duración max : ${DURATION:-sin límite}"
echo "  Salida       : $OUT_CLIP"
echo "============================================================"

# ── 1. Descargar (usa caché si ya existe) ─────────────────────────────────────
echo ""
echo "[1/3] Descargando $HF_FILE (queda cacheado en ~/.cache/huggingface/)..."

HF_CACHED=$(python3 - <<PYEOF
from huggingface_hub import hf_hub_download
p = hf_hub_download(
    repo_id="bencorn/CICIDS2017",
    repo_type="dataset",
    filename="pcaps/$HF_FILE",
)
print(p)
PYEOF
)

echo "      OK: $HF_CACHED"

# ── 2. Recortar ───────────────────────────────────────────────────────────────
echo ""
echo "[2/3] Recortando a ${MAX_PACKETS} paquetes → $OUT_CLIP ..."

if [[ -n "$DURATION" ]]; then
    tshark -r "$HF_CACHED" \
           -Y "frame.time_relative < ${DURATION}" \
           -c "${MAX_PACKETS}" \
           -w "$OUT_CLIP"
else
    tshark -r "$HF_CACHED" \
           -c "${MAX_PACKETS}" \
           -w "$OUT_CLIP"
fi

# ── 3. Verificar ──────────────────────────────────────────────────────────────
echo ""
echo "[3/3] Información del extracto:"
capinfos "$OUT_CLIP"

ACTUAL_PKTS=$(capinfos "$OUT_CLIP" | grep "Number of packets" | awk '{print $NF}')
echo ""
echo "[OK] Listo: $OUT_CLIP  (${ACTUAL_PKTS} paquetes)"