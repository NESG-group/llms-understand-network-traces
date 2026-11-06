import json
from pathlib import Path

import pytest

from llms_understand_network_traces import pipeline
from llms_understand_network_traces.utils import constants


def write_gt(folder: Path, stem: str, answers: dict[str, str]) -> None:
    (folder / f"{stem}_answers.json").write_text(json.dumps({"Questions": answers}))


def test_gt_problems_detects_missing_file(tmp_path: Path) -> None:
    assert pipeline.gt_problems(tmp_path, ["t1"]) == ["missing ground truth for t1"]


def test_gt_problems_accepts_complete_gt(tmp_path: Path) -> None:
    write_gt(tmp_path, "t1", {q: "ok" for q in constants.ALL_QUESTIONS})
    assert pipeline.gt_problems(tmp_path, ["t1"]) == []


def test_gt_problems_detects_error_answers(tmp_path: Path) -> None:
    answers = {q: "ok" for q in constants.ALL_QUESTIONS}
    answers[constants.ALL_QUESTIONS[0]] = "ERROR: boom"
    write_gt(tmp_path, "t1", answers)
    assert "1 answer(s) with ERROR" in pipeline.gt_problems(tmp_path, ["t1"])[0]


def test_gt_problems_detects_question_mismatch(tmp_path: Path) -> None:
    write_gt(tmp_path, "t1", {"other question": "x"})
    assert "differs" in pipeline.gt_problems(tmp_path, ["t1"])[0]


def test_slug_and_staging_dir() -> None:
    assert pipeline.slug("llama3.1:8b") == "llama3.1-8b"
    assert pipeline.staging_dir("qwen2.5:7b", 3) == Path("data/cicids2017/staging/qwen2.5-7b_run3")


def test_cicids_stems_sorted_by_packets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    folder = pipeline.staging_dir("m:1b", 1)
    folder.mkdir(parents=True)
    levels = [{"stem": "big", "packets": 9}, {"stem": "small", "packets": 1}]
    (folder / "manifest.json").write_text(json.dumps({"levels": levels}))
    assert pipeline.cicids_stems("m:1b", 1) == ["small", "big"]


def test_cicids_stems_without_manifest_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        pipeline.cicids_stems("m:1b", 1)


def test_llm_requires_model() -> None:
    with pytest.raises(SystemExit):
        pipeline.main(["llm", "--dataset", "basic"])


def test_prepare_only_for_cicids() -> None:
    with pytest.raises(SystemExit):
        pipeline.main(["prepare", "--dataset", "basic", "--model", "m"])


def test_llm_step_builds_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(pipeline, "run_module", lambda module, args: calls.append((module, list(args))))
    pipeline.main(["llm", "--dataset", "basic", "--model", "m:1b", "--first-run", "2", "--runs", "2"])
    assert [c[1][c[1].index("--run") + 1] for c in calls] == ["run2", "run3"]
    assert all(c[0] == "evaluation.answer_with_llm" for c in calls)
    assert "results/basic" in calls[0][1]


def test_judge_step_covers_both_views(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(pipeline, "run_module", lambda module, args: calls.append(list(args)))
    pipeline.main(["judge", "--dataset", "basic", "--model", "m:1b"])
    assert len(calls) == 2
    assert calls[0][calls[0].index("--gt-folder") + 1] == "data/qa"
