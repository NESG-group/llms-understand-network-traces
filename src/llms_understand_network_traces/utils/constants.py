# =============================================================================
# PROTOCOL DEFINITIONS
# =============================================================================

# Dictionary of IP protocol numbers to names based on IANA assignments
PROTOCOLS = {
    "0": "HOPOPT",
    "1": "ICMP",
    "2": "IGMP",
    "3": "GGP",
    "4": "IP-in-IP (encapsulation)",
    "5": "ST",
    "6": "TCP",
    "7": "CBT",
    "8": "EGP",
    "9": "IGP",
    "10": "BBN-RCC-MON",
    "11": "NVP-II",
    "12": "PUP",
    "13": "ARGUS",
    "14": "EMCON",
    "15": "XNET",
    "16": "CHAOS",
    "17": "UDP",
    "18": "MUX",
    "19": "DCN-MEAS",
    "20": "HMP",
    "21": "PRM",
    "22": "XNS-IDP",
    "23": "TRUNK-1",
    "24": "TRUNK-2",
    "25": "LEAF-1",
    "26": "LEAF-2",
    "27": "RDP",
    "28": "IRTP",
    "29": "ISO-TP4",
    "30": "NETBLT",
    "31": "MFE-NSP",
    "32": "MERIT-INP",
    "33": "DCCP",
    "34": "3PC",
    "35": "IDPR",
    "36": "XTP",
    "37": "DDP",
    "38": "IDPR-CMTP",
    "39": "TP++",
    "40": "IL",
    "41": "IPv6",
    "42": "SDRP",
    "43": "IPv6-Route",
    "44": "IPv6-Frag",
    "45": "IDRP",
    "46": "RSVP",
    "47": "GRE",
    "48": "DSR",
    "49": "BNA",
    "50": "ESP",
    "51": "AH",
    "52": "I-NLSP",
    "53": "SWIPE",
    "54": "NARP",
    "55": "MOBILE",
    "56": "TLSP",
    "57": "SKIP",
    "58": "ICMPv6",
    "59": "IPv6-NoNxt",
    "60": "IPv6-Opts",
    "61": "Any host internal protocol",
    "62": "CFTP",
    "63": "Any local network",
    "64": "SAT-EXPAK",
    "65": "KRYPTOLAN",
    "66": "RVD",
    "67": "IPPC",
    "68": "Any distributed file system",
    "69": "SAT-MON",
    "70": "VISA",
    "71": "IPCV",
    "72": "CPNX",
    "73": "CPHB",
    "74": "WSN",
    "75": "PVP",
    "76": "BR-SAT-MON",
    "77": "SUN-ND",
    "78": "WB-MON",
    "79": "WB-EXPAK",
    "80": "ISO-IP",
    "81": "VMTP",
    "82": "SECURE-VMTP",
    "83": "VINES",
    "84": "TTP/IPTM",
    "85": "NSFNET-IGP",
    "86": "DGP",
    "87": "TCF",
    "88": "EIGRP",
    "89": "OSPF",
    "90": "Sprite-RPC",
    "91": "LARP",
    "92": "MTP",
    "93": "AX.25",
    "94": "IPIP",
    "95": "MICP (deprecated)",
    "96": "SCC-SP",
    "97": "ETHERIP",
    "98": "ENCAP",
    "99": "Any private encryption scheme",
    "100": "GMTP",
    "101": "IFMP",
    "102": "PNNI",
    "103": "PIM",
    "104": "ARIS",
    "105": "SCPS",
    "106": "QNX",
    "107": "A/N",
    "108": "IPComp",
    "109": "SNP",
    "110": "Compaq-Peer",
    "111": "IPX-in-IP",
    "112": "VRRP",
    "113": "PGM",
    "114": "Any 0-hop protocol",
    "115": "L2TP",
    "116": "DDX",
    "117": "IATP",
    "118": "STP",
    "119": "SRP",
    "120": "UTI",
    "121": "SMP",
    "122": "SM (deprecated)",
    "123": "PTP",
    "124": "IS-IS over IPv4",
    "125": "FIRE",
    "126": "CRTP",
    "127": "CRUDP",
    "128": "SSCOPMCE",
    "129": "IPLT",
    "130": "SPS",
    "131": "PIPE",
    "132": "SCTP",
    "133": "FC",
    "134": "RSVP-E2E-IGNORE",
    "135": "Mobility Header",
    "136": "UDPLite",
    "137": "MPLS-in-IP",
    "138": "MANET",
    "139": "HIP",
    "140": "Shim6",
    "141": "WESP",
    "142": "ROHC",
    "253": "Experimentation and testing",
    "254": "Experimentation and testing",
    "255": "Reserved",
}

# =============================================================================
# DATA PATHS
# =============================================================================

PROCESSED_CSV_BASE = "data/networkTracesSamples/processed_csv"

CSV_FOLDERS = ["general", "wide", "arp", "ip", "tcp", "udp"]

# =============================================================================
# QUESTIONS — v3 (version actual)
# =============================================================================

ARP_QUESTIONS = [
    # 1. MACs de los emisores (arp.src.hw_mac)
    "List the unique MAC addresses of the hosts involved in ARP exchanges",
    # 2. Flujos ARP únicos
    "List the unique ARP flows found in the trace. For each one report: sender MAC address, target MAC address, sender IP address, and target IP address",
    # 3. Intercambios request-reply completos (sin cambios)
    "List all complete ARP request-reply exchanges found in the trace. For each one report: the resolved IP address, its MAC address, and the IP address that requested it",
]

IP_QUESTIONS = [
    # 4. IPs únicas (solo cabecera IPv4)
    "List all unique IPv4 addresses that appear as source or destination of IPv4 packets in the trace",    
    # 5. Protocolos encapsulados (sin cambios)
        "List the unique values of the IPv4 protocol field (ip.proto) found in the trace. For each one report: protocol number and protocol name (format: number - NAME)",
    # 6. IPs privadas (RFC 1918), contando paquetes
    "List all IPv4 addresses in the trace that belong to private ranges (RFC 1918). For each one report: the IP address, the number of packets in which it appears as source, and the number of packets in which it appears as destination.",
    # 7. IPs públicas, excluyendo rangos especiales
    "List all IPv4 addresses in the trace that are public (globally routable) unicast addresses. For each one report: the IP address, the number of packets in which it appears as source, and the number of packets in which it appears as destination.",
]

TCP_QUESTIONS = [
    # 1. Puertos más comunes
    "TCP: List the top 5 source ports and top 5 destination ports observed in TCP packets, ranked by packet count (descending). Include ties at the 5th position, even if this results in more than 5 ports. Report each port with its packet count.",
    # 2. Well-known ports (0–1023)
    "TCP: List all the well-known destination ports (ports 0 to 1023) observed in TCP packets. Report as a simple list of ports.",
    # TCP 3 (FIN): fijar dirección
    "TCP: List the port pairs of TCP sessions closed with a FIN. Report each pair in the direction of the packet that carried the FIN flag, as: source_port -> destination_port",
    # TCP 4 (RST): fijar dirección
    "TCP: List the port pairs of TCP sessions that were reset (RST). Report each pair in the direction of the packet that carried the RST flag, as: source_port -> destination_port",
    # TCP 5 (rechazadas): definir "explícitamente"
    "TCP: List the destination ports where a TCP connection attempt was explicitly refused with a RST packet. Report as a simple list of ports.",
    # TCP 6 (handshake): fijar dirección
    "TCP: List the port pairs that successfully completed a TCP three-way handshake. Report as: client_port -> server_port",
    # 7. Múltiples intentos desde el mismo origen
    "TCP: List all the source ports that initiated more than one TCP session attempt (sent more than one SYN packet). Report as a simple list of ports.",
    # 8. Intentos fallidos de handshake
    "TCP: List all the source ports that sent a TCP SYN packet but failed to complete the three-way handshake. Report as a simple list of ports.",
    # 9. SYNs repetidos sin respuesta (posible firewall/drop)
    "TCP: List all the port pairs where a source port sent repeated TCP SYN packets without receiving a single SYN-ACK response. Report as: source_port -> destination_port",
]

UDP_QUESTIONS = [
    # 1. Puertos más comunes
    "UDP: List the top 5 source ports and top 5 destination ports observed in UDP packets, ranked by packet count (descending). Include ties at the 5th position, even if this results in more than 5 ports. Report each port with its packet count.",
    # 2. Well-known ports (0–1023)
    "UDP: List all the well-known destination ports (ports 0 to 1023) observed in UDP packets. Report as a simple list of ports.",
    # UDP 3 (sin respuesta): fijar la regla de emparejado
    "UDP: List all the destination ports that received more than one UDP packet and never appear as a UDP source port in the trace. Report as a simple list of ports."
]

# Combined — used when running all questions in sequence
ALL_QUESTIONS = ARP_QUESTIONS + IP_QUESTIONS + TCP_QUESTIONS + UDP_QUESTIONS