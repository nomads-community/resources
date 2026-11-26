import re
from datetime import date

_DATE_PATTERNS = [
    (re.compile(r"(?<!\d)(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})(?!\d)"), ("y", "m", "d")),
    (re.compile(r"(?<!\d)(\d{2})[-_.]?(\d{2})[-_.]?(20\d{2})(?!\d)"), ("d", "m", "y")),
]

def extract_date(text) -> date | None:
    """Return the first valid date found in `text`, or None."""
    if not isinstance(text, str):
        return None
    for pattern, order in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            parts = dict(zip(order, map(int, match.groups())))
            try:
                return date(parts["y"], parts["m"], parts["d"])
            except ValueError:  # e.g. month 13 or Feb 30, so try the next match
                continue
    return None