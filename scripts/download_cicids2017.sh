#!/usr/bin/env bash
# ==============================================================================
# download_cicids2017.sh
# Downloads a pcap of the CIC-IDS-2017 dataset (Hugging Face) and clips an excerpt.
#
# Note: Hugging Face uses Xet storage and does not support range requests, so the
# whole file is always downloaded. The pcap is cached in ~/.cache/huggingface/ and
# is not downloaded again on later runs.
#
# Usage:
#   bash download_cicids2017.sh
#   bash download_cicids2017.sh --file Tuesday-WorkingHours.pcap
#   bash download_cicids2017.sh --file Tuesday-WorkingHours.pcap --max-packets 500
#   bash download_cicids2017.sh --file Tuesday-WorkingHours.pcap --duration 300
#
# Optional arguments:
#   --file          Name of the pcap in the HF repo  (default: Monday-WorkingHours.pcap)
#   --duration      Seconds to keep (optional, not applied by default)
#   --max-packets   Packet limit                   (default: 1000)
#   --out-dir       Output directory               (default: ./output)
# ==============================================================================

set -euo pipefail

# ── Defaults ───────────────────────────────────────────────────────────────
HF_FILE="Monday-WorkingHours.pcap"
DURATION=""        # empty = no time filter
MAX_PACKETS=1000
OUT_DIR="./output"

# ── Arguments ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --file)          HF_FILE="$2";       shift 2 ;;
        --duration)      DURATION="$2";      shift 2 ;;
        --max-packets)   MAX_PACKETS="$2";   shift 2 ;;
        --out-dir)       OUT_DIR="$2";       shift 2 ;;
        *) echo "[ERROR] Unknown argument: $1"; exit 1 ;;
    esac
done

# ── File names ─────────────────────────────────────────────────────────────
STEM="${HF_FILE%.pcap}"
mkdir -p "$OUT_DIR"
OUT_CLIP="${OUT_DIR}/${STEM}_${MAX_PACKETS}pkts.pcapng"

# ── Build tshark filter ────────────────────────────────────────────────────
TSHARK_FILTER=""
if [[ -n "$DURATION" ]]; then
    TSHARK_FILTER="-Y frame.time_relative < ${DURATION}"
fi

echo "============================================================"
echo "  Dataset      : bencorn/CICIDS2017 (HuggingFace)"
echo "  File         : $HF_FILE"
echo "  Max packets  : ${MAX_PACKETS}"
echo "  Max duration : ${DURATION:-no limit}"
echo "  Output       : $OUT_CLIP"
echo "============================================================"

# ── 1. Download (uses the cache if the file is already there) ──────────────
echo ""
echo "[1/3] Downloading $HF_FILE (cached in ~/.cache/huggingface/)..."

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

# ── 2. Clip ────────────────────────────────────────────────────────────────
echo ""
echo "[2/3] Clipping to ${MAX_PACKETS} packets → $OUT_CLIP ..."

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

# ── 3. Verify ──────────────────────────────────────────────────────────────
echo ""
echo "[3/3] Excerpt information:"
capinfos "$OUT_CLIP"

ACTUAL_PKTS=$(capinfos "$OUT_CLIP" | grep "Number of packets" | awk '{print $NF}')
echo ""
echo "[OK] Done: $OUT_CLIP  (${ACTUAL_PKTS} packets)"