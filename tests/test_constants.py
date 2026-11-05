from llms_understand_network_traces.utils import constants


def test_question_counts_per_layer() -> None:
    assert len(constants.ARP_QUESTIONS) == 3
    assert len(constants.IP_QUESTIONS) == 4
    assert len(constants.TCP_QUESTIONS) == 9
    assert len(constants.UDP_QUESTIONS) == 3


def test_all_questions_is_ordered_concatenation() -> None:
    expected = (
        constants.ARP_QUESTIONS
        + constants.IP_QUESTIONS
        + constants.TCP_QUESTIONS
        + constants.UDP_QUESTIONS
    )
    assert constants.ALL_QUESTIONS == expected
    assert len(constants.ALL_QUESTIONS) == 19


def test_questions_are_unique_non_empty_strings() -> None:
    questions = constants.ALL_QUESTIONS
    assert all(isinstance(q, str) and q.strip() for q in questions)
    assert len(set(questions)) == len(questions)


def test_transport_questions_name_their_protocol() -> None:
    assert all(q.startswith("TCP:") for q in constants.TCP_QUESTIONS)
    assert all(q.startswith("UDP:") for q in constants.UDP_QUESTIONS)


def test_protocol_table() -> None:
    assert constants.PROTOCOLS["1"] == "ICMP"
    assert constants.PROTOCOLS["6"] == "TCP"
    assert constants.PROTOCOLS["17"] == "UDP"


def test_csv_folders_cover_all_views() -> None:
    assert {"general", "arp", "ip", "tcp", "udp"} <= set(constants.CSV_FOLDERS)
    assert constants.PROCESSED_CSV_BASE == "data/traces/processed_csv"
