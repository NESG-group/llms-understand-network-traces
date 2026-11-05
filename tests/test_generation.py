from pathlib import Path

import httpx
import pytest

from llms_understand_network_traces.evaluation import answer_with_llm as gen


def test_prompt_places_data_before_question_and_rules() -> None:
    prompt = gen.build_prompt("What?", "row1\nrow2")
    assert prompt.index("DATA:") < prompt.index("row1") < prompt.index("QUESTION: What?")
    assert prompt.index("QUESTION: What?") < prompt.index("respond with: 'None'")


def test_prompt_includes_view_description_only_when_given() -> None:
    with_desc = gen.build_prompt("Q", "d", gen.GENERAL_DESCRIPTION)
    without = gen.build_prompt("Q", "d", None)
    assert f"DATA ({gen.GENERAL_DESCRIPTION}):" in with_desc
    assert "DATA:" in without and "DATA (" not in without


def test_prompt_hash_is_short_hex_and_stable() -> None:
    assert len(gen.PROMPT_HASH) == 12
    int(gen.PROMPT_HASH, 16)


def test_only_general_view_has_description() -> None:
    assert set(gen.VIEW_DESCRIPTIONS) == {"general"}


@pytest.mark.parametrize(
    ("tokens", "num_ctx", "expected"),
    [(-1, 8192, None), (4098, 8192, True), (4100, 8192, True), (100, 8192, False), (8000, 8192, False)],
)
def test_truncation_suspected(tokens: int, num_ctx: int, expected: bool | None) -> None:
    assert gen.truncation_suspected(tokens, num_ctx) is expected


@pytest.mark.parametrize(
    ("text", "has_header", "expected"),
    [
        ("", True, 0),
        ("h1,h2\n", True, 0),
        ("h1,h2\na,b\nc,d\n", True, 2),
        ("a,b\nc,d\n", False, 2),
        ("h\n\n  \na\n", True, 1),
    ],
)
def test_count_data_rows(text: str, has_header: bool, expected: int) -> None:
    assert gen.count_data_rows(text, has_header) == expected


def test_load_csv_returns_content_empty_string_or_none(tmp_path: Path) -> None:
    (tmp_path / "tcp").mkdir()
    (tmp_path / "tcp" / "t1.csv").write_text("a,b\n1,2\n")
    (tmp_path / "tcp" / "empty.csv").write_text("")
    assert gen.load_csv(str(tmp_path), "tcp", "t1") == "a,b\n1,2\n"
    assert gen.load_csv(str(tmp_path), "tcp", "empty") == ""
    assert gen.load_csv(str(tmp_path), "tcp", "missing") is None


def test_ollama_version_falls_back_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("offline")

    gen.get_ollama_version.cache_clear()
    monkeypatch.setattr(gen.httpx, "get", fail)
    assert gen.get_ollama_version() == "unknown"
    gen.get_ollama_version.cache_clear()


def test_layer_questions_cover_every_question() -> None:
    merged = [q for qs in gen.LAYER_QUESTIONS.values() for q in qs]
    assert sorted(merged) == sorted(gen.constants.ALL_QUESTIONS)
