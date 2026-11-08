"""Text helpers shared by the analysis and judging code."""

import re


def norm(text: object) -> str:
    """Collapse whitespace so that the same question matches across files."""
    return re.sub(r"\s+", " ", str(text).strip())


def gt_empty(gt: object) -> bool:
    """True if the reference answer says that nothing was found (last line ends with 'none' or first line starts with 'no ')."""
    lines = [line.strip() for line in str(gt).splitlines() if line.strip()]
    return bool(lines) and (lines[-1].lower().endswith("none") or lines[0].lower().startswith("no "))
