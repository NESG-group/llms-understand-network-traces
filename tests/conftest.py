import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "traces" / "raw" / "basic"
CSV_DIR = REPO_ROOT / "data" / "traces" / "processed_csv" / "basic"
TRACES = (
    "arp-icmp",
    "ip-networktrace2",
    "nmap22-23-53-80-443",
    "nmap22-23-53-80-443-threewayhandshake",
)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if shutil.which("tshark") is not None:
        return
    skip = pytest.mark.skip(reason="tshark is not installed")
    for item in items:
        if "tshark" in item.keywords:
            item.add_marker(skip)
