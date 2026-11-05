import math

import pytest

from llms_understand_network_traces.comparison import compare_manual as cm


def test_norm_collapses_whitespace() -> None:
    assert cm.norm("  a \n  b\t c ") == "a b c"


@pytest.mark.parametrize(
    ("gt", "expected"),
    [("None", True), ("No ARP packets found", True), ("10.0.0.1\nNone", True), ("10.0.0.1\n10.0.0.2", False), ("", False)],
)
def test_gt_empty(gt: str, expected: bool) -> None:
    assert cm.gt_empty(gt) is expected


def test_wilson_interval() -> None:
    assert all(math.isnan(x) for x in cm.wilson(0, 0))
    low, high = cm.wilson(5, 10)
    assert 0 < low < 0.5 < high < 1
    assert low + high == pytest.approx(1.0)
    low_all, high_all = cm.wilson(10, 10)
    assert high_all == pytest.approx(1.0) and low_all < 1


def test_kappa_perfect_agreement() -> None:
    pairs = [("C", "C"), ("P", "P"), ("I", "I"), ("C", "C")]
    assert cm.kappa(pairs) == pytest.approx(1.0)
    assert cm.kappa(pairs, weighted=True) == pytest.approx(1.0)


def test_kappa_degenerate_cases_are_nan() -> None:
    assert math.isnan(cm.kappa([]))
    assert math.isnan(cm.kappa([("C", "C")] * 5))


def test_kappa_known_value() -> None:
    pairs = [("C", "C")] * 20 + [("C", "I")] * 5 + [("I", "C")] * 10 + [("I", "I")] * 15
    assert cm.kappa(pairs) == pytest.approx(0.4, abs=1e-9)


def test_weighted_kappa_penalises_distant_disagreement_more() -> None:
    near = [("C", "C")] * 6 + [("C", "P")] * 2 + [("I", "I")] * 6
    far = [("C", "C")] * 6 + [("C", "I")] * 2 + [("I", "I")] * 6
    assert cm.kappa(near, weighted=True) > cm.kappa(far, weighted=True)


def test_sign_test_p() -> None:
    assert math.isnan(cm.sign_test_p(0, 0))
    assert cm.sign_test_p(5, 5) == pytest.approx(1.0)
    assert cm.sign_test_p(10, 0) == pytest.approx(2 / 1024)
    assert cm.sign_test_p(0, 10) == cm.sign_test_p(10, 0)


def test_boot_ci_requires_enough_groups_and_is_reproducible() -> None:
    few = [[("C", "C")]] * 7
    assert all(math.isnan(x) for x in cm.boot_ci(few, cm.kappa))
    groups = [[("C", "C"), ("I", "I")], [("C", "C")], [("I", "I")], [("P", "P")]] * 3
    first = cm.boot_ci(groups, lambda pairs: sum(a == b for a, b in pairs) / len(pairs), iters=200)
    second = cm.boot_ci(groups, lambda pairs: sum(a == b for a, b in pairs) / len(pairs), iters=200)
    assert first == second
    assert first[0] <= first[1] <= 1.0


def test_lenient_label_takes_the_laxest_vote_only_on_ties() -> None:
    assert cm.lenient({"tie": True, "votes": "I/C", "judge": "I"}) == "C"
    assert cm.lenient({"tie": True, "votes": "I/P", "judge": "I"}) == "P"
    assert cm.lenient({"tie": False, "votes": "C/C", "judge": "C"}) == "C"
