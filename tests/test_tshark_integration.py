import csv
import json
from pathlib import Path

import pytest

from llms_understand_network_traces.evaluation import answer_with_pyshark
from llms_understand_network_traces.preprocessing import convert_pcap_to_csv as conv
from llms_understand_network_traces.utils import constants

from conftest import CSV_DIR, RAW_DIR, TRACES

pytestmark = pytest.mark.tshark


def read_rows(path: Path) -> list[list[str]]:
    with path.open(newline="") as handle:
        return list(csv.reader(handle))


@pytest.fixture(scope="module")
def converted(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("csv")
    for view in ("ARP", "IP", "TCP", "UDP"):
        conv.convertpcap2csv(str(RAW_DIR), str(out), type=view)
    return out


@pytest.mark.parametrize("trace", TRACES)
@pytest.mark.parametrize("view", ["arp", "ip", "tcp", "udp"])
def test_filtered_views_match_the_committed_csv(converted: Path, trace: str, view: str) -> None:
    fresh = read_rows(converted / view / f"{trace}.csv")
    committed = read_rows(CSV_DIR / view / f"{trace}.csv")
    assert fresh[:1] == committed[:1]
    assert [row[0] for row in fresh] == [row[0] for row in committed]


@pytest.fixture(scope="module")
def reference_answers(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict[str, str]]:
    out = tmp_path_factory.mktemp("qa")
    answer_with_pyshark.pyshark_answers(str(RAW_DIR), str(out))
    return {
        trace: json.loads((out / f"{trace}_answers.json").read_text())["Questions"]
        for trace in TRACES
    }


@pytest.mark.parametrize("trace", TRACES)
def test_reference_answers_cover_all_questions_without_errors(
    reference_answers: dict[str, dict[str, str]], trace: str
) -> None:
    answers = reference_answers[trace]
    assert set(answers) == set(constants.ALL_QUESTIONS)
    assert not [q for q, a in answers.items() if str(a).startswith("ERROR")]


def test_handshake_trace_reports_a_completed_handshake(reference_answers: dict[str, dict[str, str]]) -> None:
    answers = reference_answers["nmap22-23-53-80-443-threewayhandshake"]
    handshake = answers[constants.TCP_QUESTIONS[5]]
    assert "->" in str(handshake)


def test_arp_trace_has_no_tcp_activity(reference_answers: dict[str, dict[str, str]]) -> None:
    answers = reference_answers["arp-icmp"]
    assert str(answers[constants.TCP_QUESTIONS[5]]).strip().lower().endswith("none")
