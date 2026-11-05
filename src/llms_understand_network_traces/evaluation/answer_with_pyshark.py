import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pyshark
import os
import ipaddress
from collections import Counter, defaultdict
from tqdm import tqdm

import utils.constants as constants 
from utils.utils import saveJsonToFile

# ==============================================================================
# CONFIG
# ==============================================================================

# [GT-FIX, OPTIONAL] ARP questions 1 and 2 do not say which layer "MAC address"
# refers to (ARP header vs Ethernet header). If True, the GT lists BOTH
# interpretations and the judge accepts a candidate that fully matches either
# one (see rule 7 in the judge rubric). If False, only the ARP-header version
# is used (original behaviour).
ARP_ACCEPT_BOTH_LAYERS = False

# ==============================================================================
# HELPERS  [GT-FIX]
# ==============================================================================

# RFC 1918 private ranges. Python's ip.is_private is much broader (it also
# covers loopback, link-local, 0.0.0.0/8, 255.255.255.255, documentation and
# reserved ranges), so it is NOT used to answer the "RFC 1918" question.
RFC1918_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]

# TCP flag bits
TCP_SYN, TCP_RST, TCP_ACK = 0x02, 0x04, 0x10


def _l3_endpoints(pkt):
    """(src, dst) from IPv4 or IPv6, so TCP over IPv6 is handled like the port questions."""
    if hasattr(pkt, 'ip'):
        return pkt.ip.src, pkt.ip.dst
    if hasattr(pkt, 'ipv6'):
        return pkt.ipv6.src, pkt.ipv6.dst
    raise AttributeError("no IP layer")


def _pair_key(pair_str):
    """Numeric sort key for 'a -> b' strings."""
    return tuple(int(x) for x in pair_str.split(" -> "))


def _is_syn(flags):      # SYN set, ACK clear (tolerates ECN/NS bits)
    return (flags & (TCP_SYN | TCP_ACK)) == TCP_SYN


def _is_synack(flags):   # SYN and ACK set
    return (flags & (TCP_SYN | TCP_ACK)) == (TCP_SYN | TCP_ACK)


def _is_final_ack(flags):  # ACK set, SYN and RST clear (may carry PSH/data)
    return (flags & (TCP_SYN | TCP_RST | TCP_ACK)) == TCP_ACK


# ==============================================================================
# 1. FUNCTIONS FOR ARP
# ==============================================================================

# ARP_QUESTIONS[0]
# "List the unique MAC addresses of the hosts involved in ARP exchanges"
# Convention: hardware addresses of the ARP header (sender and target) of all ARP packets,
# excluding the all-zero placeholder and group (multicast/broadcast) addresses, which do
# not identify a host. A host that only appears as target (e.g. the reply to a request
# captured before the trace starts) is included.
def _is_host_mac(mac: str) -> bool:
    """A MAC that identifies a host: not the all-zero placeholder and not a group
    (multicast/broadcast) address, i.e. the I/G bit of the first octet is 0."""
    mac = mac.lower()
    return mac != "00:00:00:00:00:00" and not (int(mac.split(":")[0], 16) & 1)

def listARPMacAddresses(network_trace):
    cap = pyshark.FileCapture(network_trace, display_filter="arp")
    macs = set()
    for pkt in cap:
        if hasattr(pkt, 'arp'):
            for mac in (pkt.arp.src_hw_mac, pkt.arp.dst_hw_mac):
                if _is_host_mac(mac):
                    macs.add(mac.lower())
    cap.close()
    return "Unique MAC addresses of hosts involved in ARP exchanges:\n" + ("\n".join(sorted(macs)) if macs else "None")

# ARP_QUESTIONS[1]
# "List the unique ARP flows found in the trace. For each one report: sender MAC address, target MAC address,
# sender IP address, and target IP address"
# Convention: the four values are fields of the ARP header (arp.src.hw_mac, arp.dst.hw_mac,
# arp.src.proto_ipv4, arp.dst.proto_ipv4), not of the Ethernet header.
# Target MAC is 00:00:00:00:00:00 in requests and probes.
# A flow is listed once, however many packets (or capture duplicates) carry it.
def listARPFlows(network_trace):
    cap = pyshark.FileCapture(network_trace, display_filter="arp")
    flows = set()
    for pkt in cap:
        if hasattr(pkt, 'arp'):
            flows.add(
                f"Sender MAC: {pkt.arp.src_hw_mac}, Target MAC: {pkt.arp.dst_hw_mac}, "
                f"Sender IP: {pkt.arp.src_proto_ipv4}, Target IP: {pkt.arp.dst_proto_ipv4}"
            )
    cap.close()
    return "ARP flows:\n" + ("\n".join(sorted(flows)) if flows else "None")

# ARP_QUESTIONS[2]
# "List all complete ARP request-reply exchanges found in the trace. For each one report: the resolved IP address,
# its MAC address, and the IP address that requested it"
# Convention: an exchange is complete when a reply (opcode 2) is seen after a request (opcode 1) whose
# target IP is the reply's sender IP and whose sender IP is the reply's target IP. MAC taken from the ARP header
# (arp.src.hw_mac of the reply). Exact duplicates collapse into one exchange (set). ARP probes and
# announcements get no reply, so they never count as exchanges.
def identifyCompletedARPExchanges(network_trace):
    cap = pyshark.FileCapture(network_trace, display_filter="arp")
    requests = {} 
    completed = set()
    for pkt in cap:
        if hasattr(pkt, 'arp'):
            opcode = pkt.arp.opcode # 1=req, 2=rep
            src_ip = pkt.arp.src_proto_ipv4
            dst_ip = pkt.arp.dst_proto_ipv4
            src_mac = pkt.arp.src_hw_mac
            if opcode == "1":
                requests[(dst_ip, src_ip)] = src_mac
            elif opcode == "2" and (src_ip, dst_ip) in requests:
                completed.add(f"IP {src_ip} is at {src_mac} (Requested by {dst_ip})")
    cap.close()
    return "Completed exchanges:\n" + ("\n".join(sorted(completed)) if completed else "None")

# ==============================================================================
# 2. FUNCTIONS FOR IPv4
# ==============================================================================

# IP_QUESTIONS[0]
# "List all unique IPv4 addresses that appear as source or destination of IPv4 packets in the trace"
# Convention: ip.src / ip.dst of the (outer) IPv4 header. Multicast addresses in the IPv4 header
# (e.g. 224.0.0.22) are included; addresses that only appear inside ARP packets
# (e.g. 0.0.0.0, 192.168.10.1) are not.
def listIPv4Addresses(network_trace):
    cap = pyshark.FileCapture(network_trace, display_filter="ip")
    ips = set()
    for p in cap:
        ips.add(p.ip.src)
        ips.add(p.ip.dst)
    cap.close()
    return "Unique IPv4 addresses:\n" + ("\n".join(sorted(ips, key=ipaddress.ip_address)) if ips else "None")


# IP_QUESTIONS[1]
# "List the unique values of the IPv4 protocol field (ip.proto) found in the trace. For each one report:
# protocol number and protocol name (format: number - NAME)"
# Convention: ip.proto of the (outer) IPv4 header; names from constants.PROTOCOLS (IANA);
# values not in the table are "Unknown Protocol".
def listIPv4Protocols(network_trace):
    cap = pyshark.FileCapture(network_trace, display_filter="ip")
    layer3_protocols = set()
    for p in cap:
        proto_num = p.ip.proto
        proto_name = constants.PROTOCOLS.get(proto_num, "Unknown Protocol")
        layer3_protocols.add(f"{proto_num} - {proto_name}")
    cap.close()
    return "IPv4 protocols:\n" + ("\n".join(sorted(layer3_protocols, key=lambda s: int(s.split(" - ")[0]))) if layer3_protocols else "None")


# IP_QUESTIONS[2]
# "List all IPv4 addresses in the trace that belong to private ranges (RFC 1918). For each one report:
# the IP address, the number of packets in which it appears as source, and the number of packets in which it appears as destination."
# IP_QUESTIONS[3]
# "List all IPv4 addresses in the trace that are public (globally routable) unicast addresses. For each one report:
# the IP address, the number of packets in which it appears as source, and the number of packets in which it appears as destination."
# Convention: counts are per packet as observed in the trace (capture duplicates count as packets).
# private = RFC 1918 only; public = globally routable unicast, i.e. excluding private, multicast, loopback,
# link-local and other reserved addresses (see _classify_ipv4).

def _classify_ipv4(ip_obj):
    """[GT-FIX] 'private' = RFC 1918 only; 'public' = globally routable unicast; else None."""
    if ip_obj.is_multicast:
        return None
    if any(ip_obj in net for net in RFC1918_NETWORKS):
        return "private"
    if ip_obj.is_global:
        return "public"
    return None   # loopback, link-local, 0.0.0.0, broadcast, CGNAT, reserved...


def listIPv4ByRange(network_trace, type_range):
    # cap captures ip packets and counts occurrences of private/public IPs
    cap = pyshark.FileCapture(network_trace, display_filter="ip")
    src_counts = Counter()
    dst_counts = Counter()
    # For each packet, check if the source and destination IPs are private or public based on the type_range argument
    for p in cap:
        for addr, counter in [(p.ip.src, src_counts), (p.ip.dst, dst_counts)]:
            try:
                kind = _classify_ipv4(ipaddress.ip_address(addr))
            except ValueError:
                continue
            if kind == type_range:
                counter[addr] += 1
    cap.close()

    all_ips = set(src_counts) | set(dst_counts)
    if not all_ips:
        return f"{type_range.capitalize()} IPs:\nNone"

    lines = [
        f"{ip} (as src: {src_counts.get(ip, 0)} packets, as dst: {dst_counts.get(ip, 0)} packets)"
        for ip in sorted(all_ips, key=ipaddress.ip_address)
    ]
    return f"{type_range.capitalize()} IPs:\n" + "\n".join(lines)

# ==============================================================================
# 3. FUNCTIONS FOR LAYER 4: TCP
# ==============================================================================

# TCP_QUESTIONS[0]
# "TCP: List the top 5 source ports and top 5 destination ports observed in TCP packets, ranked by packet count
# (descending). Include ties at the 5th position, even if this results in more than 5 ports. Report each port with its packet count."
# Convention: counts are per packet as observed (capture duplicates count as packets).
def common_tcp_ports(pcap_file, top_k=5):
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp")
    src_ports, dst_ports = Counter(), Counter()
    for pkt in cap:
        if hasattr(pkt, 'tcp'):
            src_ports[pkt.tcp.srcport] += 1
            dst_ports[pkt.tcp.dstport] += 1
    cap.close()
    if not src_ports:
        return "No TCP packets found"

    def top_k_with_ties(counter, k):
        sorted_counts = sorted(counter.items(), key=lambda x: (-x[1], int(x[0])))
        if len(sorted_counts) <= k:
            return sorted_counts
        min_count = sorted_counts[k-1][1]
        return [(p, c) for p, c in sorted_counts if c >= min_count]

    src = top_k_with_ties(src_ports, top_k)
    dst = top_k_with_ties(dst_ports, top_k)

    src_str = ", ".join(f"{p} - {c} packets" for p, c in src)
    dst_str = ", ".join(f"{p} - {c} packets" for p, c in dst)
    return f"Top {top_k} source ports (ties included): {src_str}\nTop {top_k} destination ports (ties included): {dst_str}"

# TCP_QUESTIONS[1]
# "TCP: List all the well-known destination ports (ports 0 to 1023) observed in TCP packets. Report as a simple list of ports."
# Convention: destination ports of TCP packets with value <= 1023 (any direction of the connection).
def tcp_well_known_ports(pcap_file):
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp")
    well_known = set()
    for pkt in cap:
        if hasattr(pkt, 'tcp'):
            try:
                dport = int(pkt.tcp.dstport)
                if dport <= 1023:
                    well_known.add(dport)
            except (ValueError, AttributeError):
                continue
    cap.close()
    if not well_known:
        return "No well-known destination ports (0-1023) found in TCP packets"
    return "Well-known TCP destination ports:\n" + "\n".join(str(p) for p in sorted(well_known))


# TCP_QUESTIONS[2]
# "TCP: List the port pairs of TCP sessions closed with a FIN. Report each pair in the direction of the packet
# that carried the FIN flag, as: source_port -> destination_port"
# Convention: port pair = direction of the packet carrying the FIN flag.
# A pair is listed once, however many FIN packets (or capture duplicates) carry it.
def tcp_sessions_with_fin(pcap_file):
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp.flags.fin == 1")
    pairs = set()
    for pkt in cap:
        if hasattr(pkt, 'tcp'):
            pairs.add(f"{pkt.tcp.srcport} -> {pkt.tcp.dstport}")
    cap.close()
    if not pairs:
        return "No FIN sessions found"
    return "FIN sessions (port pairs):\n" + "\n".join(sorted(pairs, key=_pair_key))

# TCP_QUESTIONS[3]
# "TCP: List the port pairs of TCP sessions that were reset (RST). Report each pair in the direction of the packet
# that carried the RST flag, as: source_port -> destination_port"
# Convention: port pair = direction of the packet carrying the RST flag.
# A pair is listed once, however many RST packets (or capture duplicates) carry it.
def tcp_sessions_with_reset(pcap_file):
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp.flags.reset == 1")
    pairs = set()
    for pkt in cap:
        if hasattr(pkt, 'tcp'):
            pairs.add(f"{pkt.tcp.srcport} -> {pkt.tcp.dstport}")
    cap.close()
    if not pairs:
        return "No RST sessions found"
    return "RST sessions (port pairs):\n" + "\n".join(sorted(pairs, key=_pair_key))


# TCP_QUESTIONS[4]
# "TCP: List the destination ports where a TCP connection attempt was explicitly refused with a RST packet.
# Report as a simple list of ports."
# Convention: "refused" = a SYN answered with a RST for a connection that never received a SYN-ACK.
# [GT-FIX]
# Convention: the reported port is the server (destination) port of the refused SYN.
def tcp_refused_with_rst(pcap_file):
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp")
    syn_sent = set()      # client 4-tuples that sent a SYN
    synack_seen = set()   # client 4-tuples that received a SYN-ACK
    refused = set()

    for pkt in cap:
        try:
            src, dst = _l3_endpoints(pkt)
            sport, dport = int(pkt.tcp.srcport), int(pkt.tcp.dstport)
            flags = int(pkt.tcp.flags, 16)
        except (AttributeError, ValueError):
            continue

        if _is_syn(flags):
            syn_sent.add((src, dst, sport, dport))
        elif _is_synack(flags):
            synack_seen.add((dst, src, dport, sport))       # client-oriented 4-tuple
        elif flags & TCP_RST:
            client = (dst, src, dport, sport)                # RST from server to client
            if client in syn_sent and client not in synack_seen:
                refused.add(sport)                           # server (destination) port
    cap.close()

    if not refused:
        return "No explicitly refused TCP connection attempts found"
    return "Destination ports that refused TCP connections with RST:\n" + "\n".join(str(p) for p in sorted(refused))

# TCP_QUESTIONS[5]
# "TCP: List the port pairs that successfully completed a TCP three-way handshake. Report as: client_port -> server_port"
# Convention: client = sender of the initial SYN; port pair = client port -> server port.
def _track_handshakes(pcap_file):
    """Returns (completed, pending): sets/dicts keyed by the client 4-tuple (src, dst, sport, dport)."""
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp")
    states = {}        # key -> "SYN_SENT" | "SYN_ACK_RECEIVED"
    completed = set()

    for pkt in cap:
        try:
            src, dst   = _l3_endpoints(pkt)
            sport, dport = pkt.tcp.srcport, pkt.tcp.dstport
            flags = int(pkt.tcp.flags, 16)
            key     = (src, dst, sport, dport)
            rev_key = (dst, src, dport, sport)

            if _is_syn(flags):          # SYN
                if key not in completed and key not in states:
                    states[key] = "SYN_SENT"
            elif _is_synack(flags):     # SYN-ACK
                if states.get(rev_key) == "SYN_SENT":
                    states[rev_key] = "SYN_ACK_RECEIVED"
            elif _is_final_ack(flags):  # ACK
                if states.get(key) == "SYN_ACK_RECEIVED":
                    completed.add(key)
                    del states[key]
        except (AttributeError, ValueError):
            continue
    cap.close()
    return completed, states

def tcp_three_way_handshake(pcap_file):
    completed, _ = _track_handshakes(pcap_file)
    pairs = {f"{k[2]} -> {k[3]}" for k in completed}
    return "Completed handshakes (port pairs):\n" + ("\n".join(sorted(pairs, key=_pair_key)) if pairs else "None")


# TCP_QUESTIONS[6]
# "TCP: List all the source ports that initiated more than one TCP session attempt (sent more than one SYN packet).
# Report as a simple list of ports."
# Convention: counts SYN packets (SYN set, ACK clear) per source port number as observed in the trace
# (capture duplicates / retransmissions count as packets). Matched by port only, not by host.
def tcp_multiple_syn_sources(pcap_file):
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp.flags.syn == 1 and tcp.flags.ack == 0")
    syn_counts = Counter()
    for pkt in cap:
        if hasattr(pkt, 'tcp'):
            syn_counts[pkt.tcp.srcport] += 1
    cap.close()
    repeated = sorted((str(port) for port, count in syn_counts.items() if count > 1), key=int)
    if not repeated:
        return "No source ports sent more than one SYN packet"
    return "Source ports with more than one SYN attempt:\n" + "\n".join(repeated)

# TCP_QUESTIONS[7]
# "TCP: List all the source ports that sent a TCP SYN packet but failed to complete the three-way handshake.
# Report as a simple list of ports."
# Convention: same handshake tracking as TCP_QUESTIONS[5]. A handshake still incomplete at the end of the trace
# counts as "not completed" (it can be an artifact of where the trace is cut).
def tcp_failed_handshakes(pcap_file):
    _, pending = _track_handshakes(pcap_file)
    failed = {k[2] for k in pending}
    if not failed:
        return "No failed TCP handshakes found"
    return "Source ports that sent SYN but failed to complete handshake:\n" + "\n".join(sorted(failed, key=int))


# TCP_QUESTIONS[8]
# "TCP: List all the port pairs where a source port sent repeated TCP SYN packets without receiving a single
# SYN-ACK response. Report as: source_port -> destination_port"
# Convention: matched by port pair only (not by host); capture duplicates of a SYN count as repeated SYNs.
def tcp_repeated_syn_no_response(pcap_file):
    # First pass: count SYNs per (sport, dport) pair
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp.flags.syn == 1 and tcp.flags.ack == 0")
    syn_counts = Counter()
    for pkt in cap:
        if hasattr(pkt, 'tcp'):
            syn_counts[(pkt.tcp.srcport, pkt.tcp.dstport)] += 1
    cap.close()

    repeated_pairs = {pair for pair, count in syn_counts.items() if count > 1}
    if not repeated_pairs:
        return "No repeated SYN packets without SYN-ACK found"

    # Second pass: check which of those pairs never received a SYN-ACK
    cap = pyshark.FileCapture(pcap_file, display_filter="tcp.flags.syn == 1 and tcp.flags.ack == 1")
    got_synack = set()
    for pkt in cap:
        if hasattr(pkt, 'tcp'):
            # SYN-ACK goes from dport back to sport
            got_synack.add((pkt.tcp.dstport, pkt.tcp.srcport))
    cap.close()

    no_response = repeated_pairs - got_synack
    if not no_response:
        return "No port pairs with repeated SYNs and no SYN-ACK found"
    lines = [f"{pair[0]} -> {pair[1]}" for pair in sorted(no_response, key=lambda p: (int(p[0]), int(p[1])))]
    return "Port pairs with repeated SYNs and no SYN-ACK response:\n" + "\n".join(lines)

# ==============================================================================
# 4. FUNCTIONS FOR LAYER 4: UDP
# ==============================================================================

# UDP_QUESTIONS[0]
# "UDP: List the top 5 source ports and top 5 destination ports observed in UDP packets, ranked by packet count
# (descending). Include ties at the 5th position, even if this results in more than 5 ports. Report each port with its packet count."
# Convention: counts are per packet as observed (capture duplicates count as packets).
def common_udp_ports(pcap_file, top_k=5):
    cap = pyshark.FileCapture(pcap_file, display_filter="udp")
    src_ports, dst_ports = Counter(), Counter()
    for pkt in cap:
        if hasattr(pkt, 'udp'):
            src_ports[pkt.udp.srcport] += 1
            dst_ports[pkt.udp.dstport] += 1
    cap.close()
    if not src_ports:
        return "No UDP packets found"

    def top_k_with_ties(counter, k):
        sorted_counts = sorted(counter.items(), key=lambda x: (-x[1], int(x[0])))
        if len(sorted_counts) <= k:
            return sorted_counts
        min_count = sorted_counts[k-1][1]
        return [(p, c) for p, c in sorted_counts if c >= min_count]

    src = top_k_with_ties(src_ports, top_k)
    dst = top_k_with_ties(dst_ports, top_k)

    src_str = ", ".join(f"{p} - {c} packets" for p, c in src)
    dst_str = ", ".join(f"{p} - {c} packets" for p, c in dst)
    return f"Top {top_k} source ports (ties included): {src_str}\nTop {top_k} destination ports (ties included): {dst_str}"


# UDP_QUESTIONS[1]
# "UDP: List all the well-known destination ports (ports 0 to 1023) observed in UDP packets. Report as a simple list of ports."
# Convention: destination ports of UDP packets with value <= 1023 (any direction of the exchange).
def udp_well_known_ports(pcap_file):
    cap = pyshark.FileCapture(pcap_file, display_filter="udp")
    well_known = set()
    for pkt in cap:
        if hasattr(pkt, 'udp'):
            try:
                dport = int(pkt.udp.dstport)
                if dport <= 1023:
                    well_known.add(dport)
            except (ValueError, AttributeError):
                continue
    cap.close()
    if not well_known:
        return "No well-known destination ports (0-1023) found in UDP packets"
    return "Well-known UDP destination ports:\n" + "\n".join(str(p) for p in sorted(well_known))


# UDP_QUESTIONS[2]
# "UDP: List all the destination ports that received more than one UDP packet and never appear as a UDP source
# port in the trace. Report as a simple list of ports."
# Convention: matched by port number only (not by host); capture duplicates count as packets received.
def udp_no_response_ports(pcap_file):
    cap = pyshark.FileCapture(pcap_file, display_filter="udp")
    dst_counts = Counter()   # packets received per destination port
    src_ports  = set()       # ports that appear as UDP source

    for pkt in cap:
        if hasattr(pkt, 'udp'):
            try:
                dst_counts[int(pkt.udp.dstport)] += 1
                src_ports.add(int(pkt.udp.srcport))
            except (ValueError, AttributeError):
                continue
    cap.close()

    # Ports that received more than one packet but never appeared as source
    no_response = {
        port for port, count in dst_counts.items()
        if count > 1 and port not in src_ports
    }
    if not no_response:
        return "No UDP destination ports found that received more than one packet and never appear as a source port"
    return "UDP destination ports with more than one packet received and never seen as source:\n" + "\n".join(str(p) for p in sorted(no_response))

# ==============================================================================
# MAIN ORCHESTRATOR
# ==============================================================================

def pyshark_answers(
    pcapng_folder="data/networkTracesSamples/raw",
    answers_folder="results/ground_truth",
):
    pcapng_path = os.path.abspath(pcapng_folder)
    out_path    = os.path.abspath(answers_folder)
    os.makedirs(out_path, exist_ok=True)

    question_function_map = {
        # ARP
        constants.ARP_QUESTIONS[0]: listARPMacAddresses,
        constants.ARP_QUESTIONS[1]: listARPFlows,
        constants.ARP_QUESTIONS[2]: identifyCompletedARPExchanges,
        # IPv4
        constants.IP_QUESTIONS[0]: listIPv4Addresses,
        constants.IP_QUESTIONS[1]: listIPv4Protocols,
        constants.IP_QUESTIONS[2]: lambda p: listIPv4ByRange(p, "private"),
        constants.IP_QUESTIONS[3]: lambda p: listIPv4ByRange(p, "public"),
        # TCP
        constants.TCP_QUESTIONS[0]: common_tcp_ports,
        constants.TCP_QUESTIONS[1]: tcp_well_known_ports,
        constants.TCP_QUESTIONS[2]: tcp_sessions_with_fin,
        constants.TCP_QUESTIONS[3]: tcp_sessions_with_reset,
        constants.TCP_QUESTIONS[4]: tcp_refused_with_rst,
        constants.TCP_QUESTIONS[5]: tcp_three_way_handshake,
        constants.TCP_QUESTIONS[6]: tcp_multiple_syn_sources,
        constants.TCP_QUESTIONS[7]: tcp_failed_handshakes,
        constants.TCP_QUESTIONS[8]: tcp_repeated_syn_no_response,
        # UDP
        constants.UDP_QUESTIONS[0]: common_udp_ports,
        constants.UDP_QUESTIONS[1]: udp_well_known_ports,
        constants.UDP_QUESTIONS[2]: udp_no_response_ports,
    }

    assert set(question_function_map) == set(constants.ALL_QUESTIONS), \
        "question_function_map and ALL_QUESTIONS are out of sync"

    files = sorted(f for f in os.listdir(pcapng_path) if f.endswith(".pcapng"))
    if not files:
        print(f"⚠️ No .pcapng files found in: {pcapng_path}")
        return

    for trace_file in tqdm(files, desc="Processing traces"):
        trace_full_path = os.path.join(pcapng_path, trace_file)
        current_answers = {}

        for question_text, func in question_function_map.items():
            try:
                current_answers[question_text] = func(trace_full_path)
            except Exception as e:
                current_answers[question_text] = f"ERROR: {e}"

        filename_base = os.path.splitext(trace_file)[0]
        output_file   = os.path.join(out_path, f"{filename_base}_answers.json")
        output_data   = {
            "Filename":      trace_file,
            "Answer_Method": "Pyshark",
            "Questions":     current_answers,
        }
        saveJsonToFile(output_data, output_file)
        print(f"✅ Answers saved: {output_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate ground-truth answers from PCAPNG files using pyshark.")
    parser.add_argument("--input",  default="data/networkTracesSamples/raw", help="Folder with .pcapng input files")
    parser.add_argument("--output", default="results/ground_truth",          help="Folder to save the answers JSON files")
    args = parser.parse_args()

    pyshark_answers(pcapng_folder=args.input, answers_folder=args.output)