import re


def norm(text: object) -> str:
    return re.sub(r"\s+", " ", str(text).strip())


def gt_empty(gt: object) -> bool:
    lines = [line.strip() for line in str(gt).splitlines() if line.strip()]
    return bool(lines) and (lines[-1].lower().endswith("none") or lines[0].lower().startswith("no "))
