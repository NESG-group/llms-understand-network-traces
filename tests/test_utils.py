import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from llms_understand_network_traces.utils.utils import convert_to_epoch, save_json_to_file


def test_convert_to_epoch_uses_utc_minus_5() -> None:
    expected = datetime(2018, 2, 14, 10, 32, tzinfo=timezone(timedelta(hours=-5))).timestamp()
    assert convert_to_epoch("Wed-14-02-2018 10:32") == expected


def test_convert_to_epoch_is_five_hours_after_utc_wall_clock() -> None:
    utc = datetime(2018, 2, 14, 15, 32, tzinfo=timezone.utc).timestamp()
    assert convert_to_epoch("Wed-14-02-2018 10:32") == utc


def test_save_json_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    data = {"a": [1, 2, 3], "b": {"c": "d"}}
    save_json_to_file(data, str(target))
    assert json.loads(target.read_text()) == data
