import json
from pathlib import Path

import pytest

from llms_understand_network_traces.cicids import windows as cc

STAGING = Path(__file__).resolve().parents[1] / "data" / "traces" / "raw" / "cicids"
MANIFESTS = sorted(STAGING.glob("*/manifest.json"))


def test_parse_levels() -> None:
    assert cc.parse_levels("100:1.25, 75:1.0") == [("100", 1.25), ("75", 1.0)]
    assert cc.parse_levels(cc.DEFAULT_LEVELS) == [("100", 1.25), ("75", 1.0), ("50", 0.75), ("25", 0.5)]


def test_model_tag_is_filesystem_safe() -> None:
    assert cc.model_tag("llama3.1:70b") == "llama3.1-70b"
    assert cc.model_tag("qwen2.5:7b") == "qwen2.5-7b"


def test_manifests_are_present() -> None:
    assert MANIFESTS


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.parent.name)
def test_manifest_is_consistent(path: Path) -> None:
    manifest = json.loads(path.read_text())
    assert path.parent.name == f"{cc.model_tag(manifest['model'])}_run{manifest['run']}"
    assert not Path(manifest["source"]).is_absolute()
    assert manifest["source_packets"] == 50000
    assert manifest["window_first_packet"] + manifest["window_packets"] <= manifest["source_packets"] + 1
    levels = sorted(manifest["levels"], key=lambda level: level["factor"])
    assert [level["packets"] for level in levels] == sorted(level["packets"] for level in levels)
    assert all(level["packets"] <= manifest["window_packets"] for level in levels)
    assert all(level["fits"] is (level["est_pct_of_ctx"] <= 100) for level in levels)


def test_runs_share_the_seed_across_models() -> None:
    seeds: dict[int, set[int]] = {}
    for path in MANIFESTS:
        manifest = json.loads(path.read_text())
        seeds.setdefault(manifest["run"], set()).add(manifest["seed"])
    assert all(len(values) == 1 for values in seeds.values())
