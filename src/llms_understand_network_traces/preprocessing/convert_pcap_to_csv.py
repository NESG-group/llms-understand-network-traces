"""
convert_pcap_to_csv.py
================================================================================
Converts PCAPNG traces to the CSV views that are fed to the models, using TShark:
  general   all protocols, one line per packet (tshark -n -T tabs), no header row
  IP, ARP,  one view per protocol with a selected set of header fields
  TCP, UDP  (ICMP packets are excluded from the TCP and UDP views)
It also writes preprocess_meta.json with the TShark version and the views generated.

Usage (from the repository root):
  uv run python -m llms_understand_network_traces.preprocessing.convert_pcap_to_csv \
      --input data/traces/raw/basic --output data/traces/processed_csv/basic
================================================================================
"""
import os
import csv
import json
import shutil
import argparse
import subprocess
from datetime import datetime

from llms_understand_network_traces.utils.constants import PROTOCOLS

DEFAULT_RAW = "data/traces/raw/basic"
DEFAULT_OUT = "data/traces/processed_csv/basic"

# --- Field definitions --- #

BASE_FIELDS = ["frame.number", "frame.time_relative"]

IP_FIELDS = [
    "ip.version", "ip.hdr_len", "ip.dsfield", "ip.len", "ip.id", "ip.flags",
    "ip.frag_offset", "ip.ttl", "ip.proto", "ip.checksum", "ip.src", "ip.dst",
]
ARP_FIELDS = [
    "arp.hw.type", "arp.proto.type", "arp.hw.size", "arp.proto.size", "arp.opcode",
    "arp.src.hw_mac", "arp.src.proto_ipv4", "arp.dst.hw_mac", "arp.dst.proto_ipv4",
]
# The six boolean flag fields are not extracted. tcp.flags (hex bitmask) is
# extracted only to derive tcp.flags.str (e.g. SYN|ACK) in _postprocess_tcp_flags(),
# which then drops the hex column.
TCP_FIELDS = [
    "tcp.srcport", "tcp.dstport", "tcp.seq", "tcp.ack", "tcp.flags",
    "tcp.len", "tcp.checksum", "tcp.window_size",
]
UDP_FIELDS = ["udp.srcport", "udp.dstport", "udp.length", "udp.checksum"]

# Same names and order as Wireshark's Info column ([FIN, ACK] -> FIN|ACK).
TCP_FLAG_BITS = [("FIN", 0x01), ("SYN", 0x02), ("RST", 0x04),
                 ("PSH", 0x08), ("ACK", 0x10), ("URG", 0x20)]


# --- Generic helpers --- #

def _fields_cmd(filename, fields, display_filter=None):
    """Builds a tshark command extracting raw fields as CSV.
    -n disables ALL name resolution (MAC vendor names, hosts, ports)."""
    cmd = ["tshark", "-n", "-r", filename]
    if display_filter:
        cmd += ["-Y", display_filter]
    cmd += ["-T", "fields", "-E", "header=y", "-E", "separator=,", "-E", "occurrence=f"]
    for f in fields:
        cmd += ["-e", f]
    return cmd


def run_tshark(filename, tshark_args, output_folder, delimiter=","):
    """Runs tshark and saves output as CSV, printing stdout/stderr for debug."""
    print(f"\n➡ Processing file: {filename}")
    print(f"tshark command: {' '.join(tshark_args)}")

    result = subprocess.run(tshark_args, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"⚠️ tshark exited with code {result.returncode}")
    if result.stderr:
        print(f"⚠️ tshark error:\n{result.stderr}")

    csv_file = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(filename))[0]}.csv")

    os.makedirs(output_folder, exist_ok=True)

    with open(csv_file, "w") as f:
        f.write(result.stdout)

    if not result.stdout.strip():
        print(f"⚠️ Warning: generated CSV is empty: {csv_file}")
    else:
        print(f"✅ CSV generated successfully: {csv_file}")
        _validate_column_integrity(csv_file, output_folder, delimiter=delimiter)

    return csv_file


# --- Conversion functions --- #

def pcap2csvGeneral(filename, base_folder=DEFAULT_OUT, disable_protocols=()):
    """Wireshark main-view equivalent (-T tabs), no name resolution.
    disable_protocols: dissectors to disable (e.g. ['cldap'] to avoid the
    'Dissector bug' text in the Info column). Only applied to this view."""
    output_folder = os.path.join(base_folder, "general")
    args = ["tshark", "-n"]
    for proto in disable_protocols:
        args += ["--disable-protocol", proto]
    args += ["-r", filename, "-T", "tabs"]
    return run_tshark(filename, args, output_folder, delimiter="\t")


def pcap2csvIP(filename, base_folder=DEFAULT_OUT):
    output_folder = os.path.join(base_folder, "ip")
    args = _fields_cmd(filename, BASE_FIELDS + IP_FIELDS, display_filter="ip")
    csv_file = run_tshark(filename, args, output_folder)
    _postprocess_ip_proto(csv_file)
    return csv_file


def pcap2csvARP(filename, base_folder=DEFAULT_OUT):
    output_folder = os.path.join(base_folder, "arp")
    args = _fields_cmd(filename, BASE_FIELDS + ARP_FIELDS, display_filter="arp")
    return run_tshark(filename, args, output_folder)


def pcap2csvTCP(filename, base_folder=DEFAULT_OUT):
    output_folder = os.path.join(base_folder, "tcp")
    # "!icmp && !icmpv6": ICMP errors quote the original TCP header, and a bare "tcp"
    # filter matches that quoted copy. A TCP packet is one whose OUTER transport is TCP.
    args = _fields_cmd(filename, BASE_FIELDS + TCP_FIELDS, display_filter="tcp && !icmp && !icmpv6")
    csv_file = run_tshark(filename, args, output_folder)
    _postprocess_tcp_flags(csv_file)
    return csv_file


def pcap2csvUDP(filename, base_folder=DEFAULT_OUT):
    output_folder = os.path.join(base_folder, "udp")
    # "!icmp && !icmpv6": ICMP "port unreachable" messages quote the original UDP header,
    # and a bare "udp" filter matches that quoted copy. A UDP packet is one whose
    # OUTER transport is UDP.
    args = _fields_cmd(filename, BASE_FIELDS + UDP_FIELDS, display_filter="udp && !icmp && !icmpv6")
    return run_tshark(filename, args, output_folder)


# --- Postprocessing --- #

def _flags_to_str(value):
    """'0x0012' -> 'SYN|ACK'. Empty input (non-TCP row) -> ''. No flags set -> 'NONE'.
    '|' is used as separator because ',' would break the CSV."""
    value = (value or "").strip()
    if not value:
        return ""
    try:
        bits = int(value, 16)
    except ValueError:
        return ""
    names = "|".join(name for name, mask in TCP_FLAG_BITS if bits & mask)
    return names or "NONE"


def _postprocess_tcp_flags(csv_file):
    """Replaces the tcp.flags hex column with tcp.flags.str (names joined by '|',
    Wireshark order: FIN, SYN, RST, PSH, ACK, URG). The new column goes at the end."""
    tmp = csv_file + ".tmp"
    with open(csv_file, newline="") as fin:
        reader = csv.DictReader(fin)
        if not reader.fieldnames or "tcp.flags" not in reader.fieldnames:
            return  # nothing created yet -> no orphan .tmp

        out_fields = [c for c in reader.fieldnames if c != "tcp.flags"] + ["tcp.flags.str"]
        with open(tmp, "w", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            for row in reader:
                row["tcp.flags.str"] = _flags_to_str(row.get("tcp.flags"))
                writer.writerow(row)

    shutil.move(tmp, csv_file)
    print(f"🔤 TCP flags converted to string format in: {csv_file}")


def _postprocess_ip_proto(csv_file):
    """Appends ip.proto.name using the PROTOCOLS dict (same default as the GT)."""
    tmp = csv_file + ".tmp"
    with open(csv_file, newline="") as fin:
        reader = csv.DictReader(fin)
        if not reader.fieldnames or "ip.proto" not in reader.fieldnames:
            return  # nothing created yet -> no orphan .tmp

        out_fields = list(reader.fieldnames) + ["ip.proto.name"]
        with open(tmp, "w", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            for row in reader:
                proto = (row.get("ip.proto") or "").strip()
                row["ip.proto.name"] = PROTOCOLS.get(proto, "Unknown Protocol") if proto else ""
                writer.writerow(row)

    shutil.move(tmp, csv_file)
    print(f"🔤 IP proto names added to: {csv_file}")


# --- Validation --- #

def _validate_column_integrity(csv_file, output_folder, delimiter=","):
    """Checks that every row has the same number of fields as the first line
    (the header in field-based CSVs; the first packet in the headerless tabs view).
    With -E occurrence=f a field cannot yield several values, so mismatches are
    unexpected; they would point to separator characters inside values.
    Quoting is disabled because tshark does not quote its output (the Info column
    of the general view contains literal double quotes).
    Mismatches are appended to integrity_log.txt in the output folder. The rows
    are detected, NOT corrected."""
    with open(csv_file, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_NONE)
        first = next(reader, None)
        if first is None:
            return
        expected = len(first)
        bad_rows = [
            i for i, row in enumerate(reader, start=2)
            if len(row) != expected
        ]

    trace_id = os.path.splitext(os.path.basename(csv_file))[0]

    if bad_rows:
        print(f"⚠️  Column mismatch in {csv_file}: {len(bad_rows)} row(s) "
              f"with unexpected field count (lines: {bad_rows[:10]}"
              f"{'...' if len(bad_rows) > 10 else ''})")

        log_path = os.path.join(output_folder, "integrity_log.txt")
        with open(log_path, "a") as log:
            timestamp = datetime.now().isoformat(timespec="seconds")
            log.write(
                f"[{timestamp}] {trace_id}: {len(bad_rows)} row(s) with "
                f"unexpected field count (lines: {bad_rows})\n"
            )
    else:
        print(f"✅ Column integrity OK: {csv_file}")


# --- Reproducibility metadata --- #

def _write_meta(output_folder, types, disable_protocols):
    """Write preprocess_meta.json with the TShark version and the views generated."""
    try:
        out = subprocess.run(["tshark", "-v"], capture_output=True, text=True).stdout
        version = out.splitlines()[0] if out else "unknown"
    except OSError:
        version = "unknown"
    meta = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "tshark_version": version,
        "name_resolution": "disabled (-n)",
        "general_disabled_protocols": list(disable_protocols),
        "representations": list(types),
    }
    os.makedirs(output_folder, exist_ok=True)
    with open(os.path.join(output_folder, "preprocess_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


# --- Main conversion function --- #

def convert_pcap_to_csv(
    pcapng_folder=DEFAULT_RAW,
    output_folder=DEFAULT_OUT,
    type="general",
    disable_protocols=(),
):
    """Convert every PCAPNG of `pcapng_folder` to the CSV view `type` ('general', 'IP', 'ARP', 'TCP' or 'UDP') in `output_folder`."""
    if not os.path.exists(pcapng_folder):
        print(f"⚠️ Folder not found: {pcapng_folder}")
        return

    network_trace_list = sorted(f for f in os.listdir(pcapng_folder) if f.endswith(".pcapng"))
    if not network_trace_list:
        print(f"⚠️ No .pcapng files found in: {pcapng_folder}")
        return

    print(f"\n--- Converting PCAPNG to CSV (type: {type}) ---")

    func_map = {
        "general": pcap2csvGeneral,
        "IP":      pcap2csvIP,
        "ARP":     pcap2csvARP,
        "TCP":     pcap2csvTCP,
        "UDP":     pcap2csvUDP,
    }

    func = func_map.get(type)
    if func is None:
        print(f"⚠️ Unknown type: {type}. Valid options: {list(func_map.keys())}")
        return

    for network_trace in network_trace_list:
        file_path = os.path.join(pcapng_folder, network_trace)
        if type == "general":
            func(file_path, base_folder=output_folder, disable_protocols=disable_protocols)
        else:
            func(file_path, base_folder=output_folder)


# --- Entry point --- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PCAPNG files to CSV using tshark.")
    parser.add_argument("--input",  default=DEFAULT_RAW, help="Folder with .pcapng input files")
    parser.add_argument("--output", default=DEFAULT_OUT, help="Base folder for CSV output subfolders")
    parser.add_argument("--disable-protocol", nargs="*", default=[], metavar="PROTO",
                        help="Dissectors to disable in the GENERAL view only (e.g. cldap)")
    args = parser.parse_args()

    types = ["general", "IP", "ARP", "TCP", "UDP"]
    for t in types:
        convert_pcap_to_csv(pcapng_folder=args.input, output_folder=args.output,
                        type=t, disable_protocols=args.disable_protocol)

    _write_meta(args.output, types, args.disable_protocol)