from typing import Any

import pytest

from llms_understand_network_traces.comparison import compare_with_llm_judge as judge


def verdict(label: str | None, degraded: bool = False) -> dict[str, Any]:
    return {
        "reasoning": "",
        "label": label,
        "error": label is None,
        "degraded": degraded,
        "attempt": 1,
    }


def patch_passes(monkeypatch: pytest.MonkeyPatch, first: str | None, second: str | None) -> None:
    results = iter([verdict(first), verdict(second)])
    monkeypatch.setattr(judge, "call_judge", lambda model, build: next(results))


def test_sanitize_answer_strips_control_characters() -> None:
    assert judge.sanitize_answer("a\x00b\x07c\n d\t ") == "abc\n d"
    assert judge.sanitize_answer("") == ""


def test_pick_num_ctx_is_multiple_of_1024_and_bounded_below() -> None:
    assert judge.pick_num_ctx("x", 10) == judge.JUDGE_NUM_CTX_MIN
    ctx = judge.pick_num_ctx("x" * 20000, 500)
    assert ctx % 1024 == 0 and ctx > judge.JUDGE_NUM_CTX_MIN


def test_judge_prompt_swap_changes_order_only() -> None:
    plain = judge.build_judge_prompt("Q", "GT_TEXT", "LLM_TEXT", candidate_first=False)
    swapped = judge.build_judge_prompt("Q", "GT_TEXT", "LLM_TEXT", candidate_first=True)
    assert plain.index("GT_TEXT") < plain.index("LLM_TEXT")
    assert swapped.index("LLM_TEXT") < swapped.index("GT_TEXT")
    assert sorted(plain.split()) == sorted(swapped.split())


def test_judge_prompt_without_reasoning_asks_for_label_only() -> None:
    prompt = judge.build_judge_prompt("Q", "g", "l", with_reasoning=False)
    assert '{"label": "<C|P|I>"}' in prompt
    assert "reasoning" not in prompt.split("Now evaluate the following:")[1]


def test_call_judge_rejects_prompts_that_exceed_the_context() -> None:
    huge = "x" * (int(judge.JUDGE_NUM_CTX_MAX * judge.CHARS_PER_TOKEN) + 10_000)
    result = judge.call_judge("any-model", lambda with_reasoning: huge)
    assert result["error"] is True and result["label"] is None
    assert "too long" in result["reasoning"]


def test_swap_agreement_is_consistent(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_passes(monkeypatch, "C", "C")
    out = judge.judge_with_swap("m", "q", "gt", "llm")
    assert out["final_label"] == "C"
    assert out["consistent"] and out["unanimous"] and not out["single_pass"]
    assert out["votes"] == {"pass1": "C", "pass2": "C"}


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [("C", "P", "P"), ("P", "C", "P"), ("C", "I", "I"), ("P", "I", "I"), ("I", "P", "I")],
)
def test_swap_disagreement_keeps_the_stricter_label(
    monkeypatch: pytest.MonkeyPatch, first: str, second: str, expected: str
) -> None:
    patch_passes(monkeypatch, first, second)
    out = judge.judge_with_swap("m", "q", "gt", "llm")
    assert out["final_label"] == expected
    assert not out["consistent"] and not out["unanimous"]


@pytest.mark.parametrize(("first", "second"), [("P", None), (None, "P")])
def test_swap_single_valid_pass(monkeypatch: pytest.MonkeyPatch, first: str | None, second: str | None) -> None:
    patch_passes(monkeypatch, first, second)
    out = judge.judge_with_swap("m", "q", "gt", "llm")
    assert out["final_label"] == "P"
    assert out["single_pass"] and not out["consistent"]


def test_swap_without_valid_pass_is_judge_error(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_passes(monkeypatch, None, None)
    out = judge.judge_with_swap("m", "q", "gt", "llm")
    assert out["final_label"] == "E"
    assert not out["consistent"] and not out["unanimous"]
