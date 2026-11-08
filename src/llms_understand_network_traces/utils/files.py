"""File helpers."""

import json


def save_json_to_file(data, file_name):
    """Write `data` to `file_name` as indented JSON."""
    with open(file_name, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
