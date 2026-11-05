import pytest

from llms_understand_network_traces.analysis import metrics as mt


def test_vote_majority_and_tie_breaks() -> None:
    labels = [["C", "I"], ["I", "I"], ["C", "P"]]
    assert mt.vote(labels, mt.PRIO["CPI"]) == ["C", "I"]
    assert mt.vote([["C"], ["I"]], mt.PRIO["CPI"]) == ["C"]
    assert mt.vote([["C"], ["I"]], mt.PRIO["IPC"]) == ["I"]


def test_vote_ignores_missing_labels() -> None:
    assert mt.vote([[None, "P"], [None, "P"]], mt.PRIO["CPI"]) == [None, "P"]


def test_formatting_helpers() -> None:
    assert mt.pc(1, 3) == 33.3
    assert mt.pc(1, 0) is None
    assert mt.ms([]) == "n/a"
    assert mt.ms([50.0]) == "50.0"
    assert mt.ms([40.0, 60.0]) == "50.0 ± 14.1"
    assert mt.ms([None, 10.0]) == "10.0"
    assert mt.fnum(None) == "n/a"
    assert mt.fnum(3.14159, 2) == "3.14"
    assert mt.fnum(3.0, 1, sign=True) == "+3.0"


def test_sign_test() -> None:
    assert mt.sign_test(0, 0) is None
    assert mt.sign_test(5, 5) == pytest.approx(1.0)
    assert mt.sign_test(10, 0) == pytest.approx(2 / 1024)


def test_md_table() -> None:
    table = mt.md_table(["a", "b"], [[1, 2], [3, 4]])
    assert table.splitlines() == ["| a | b |", "|---|---|", "| 1 | 2 |", "| 3 | 4 |"]


def test_improvement_score_table() -> None:
    assert mt.SCORE[("I", "C")] == 2
    assert mt.SCORE[("I", "P")] == mt.SCORE[("P", "C")] == 1
    assert mt.SCORE[("C", "I")] == -2
    assert mt.SCORE[("C", "P")] == mt.SCORE[("P", "I")] == -1


def make_records() -> dict[tuple[str, int, str, str], dict[str, list[object]]]:
    return {
        ("m", 1, "general", "u"): {"lab": ["I", "P"]},
        ("m", 1, "filtered", "u"): {
            "lab": ["C", "P"],
            "cempty": [False, False],
            "gempty": [False, False],
        },
    }


def test_make_pairs_by_runs_and_transition_summary() -> None:
    pairs = mt.make_pairs(make_records(), "m", None, "runs", mt.PRIO["CPI"])
    assert pairs == [("I", "C", "with content"), ("P", "P", "with content")]
    summary = mt.trans(pairs)
    assert (summary["n"], summary["imp"], summary["same"], summary["wor"]) == (2, 1, 1, 0)
    assert summary["score"] == 50.0
    assert summary["d"] == {"C": 50.0, "P": 0.0, "I": -50.0}


def test_make_pairs_by_mode_matches_runs_when_single_run() -> None:
    by_runs = mt.make_pairs(make_records(), "m", None, "runs", mt.PRIO["CPI"])
    by_mode = mt.make_pairs(make_records(), "m", None, "mode", mt.PRIO["CPI"])
    assert by_mode == by_runs


def test_trans_without_pairs() -> None:
    summary = mt.trans([])
    assert summary["n"] == 0 and summary["score"] is None
    assert all(v is None for v in summary["d"].values())
