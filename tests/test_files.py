import json
from pathlib import Path

from llms_understand_network_traces.utils.files import save_json_to_file


def test_save_json_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    data = {"a": [1, 2, 3], "b": {"c": "d"}}
    save_json_to_file(data, str(target))
    assert json.loads(target.read_text()) == data
