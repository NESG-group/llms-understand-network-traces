import importlib
import re
from pathlib import Path

import pytest

from llms_understand_network_traces.utils.text import gt_empty, norm

SRC = Path(__file__).resolve().parents[1] / "src" / "llms_understand_network_traces"


def test_norm_collapses_whitespace() -> None:
    assert norm("  a \n  b\t c ") == "a b c"
    assert norm(12) == "12"


@pytest.mark.parametrize(
    ("gt", "expected"),
    [("None", True), ("No TCP found", True), ("a\nNone", True), ("a\nb", False), ("", False)],
)
def test_gt_empty(gt: str, expected: bool) -> None:
    assert gt_empty(gt) is expected


def test_constants_default_is_importable_everywhere() -> None:
    pattern = re.compile(r'"--constants",\s*default="([^"]+)"')
    found = {m for path in SRC.rglob("*.py") for m in pattern.findall(path.read_text())}
    assert found
    for module_name in found:
        assert importlib.import_module(module_name).ALL_QUESTIONS


def test_judge_default_model_is_the_paper_judge() -> None:
    source = (SRC / "comparison" / "compare_with_llm_judge.py").read_text()
    assert 'default="llama3.3:70b"' in source
