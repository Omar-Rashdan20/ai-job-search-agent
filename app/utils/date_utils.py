import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_ISO_RE = re.compile(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b")
_DAY_MONTH_RE = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])\s+"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+(20\d{2})\b",
    re.IGNORECASE,
)
_MONTH_DAY_RE = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+(0?[1-9]|[12]\d|3[01]),?\s+(20\d{2})\b",
    re.IGNORECASE,
)
_NUMERIC_RE = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})\b")
_DAYS_AGO_RE = re.compile(r"\bposted\s+(\d{1,3})\s+days?\s+ago\b", re.IGNORECASE)
_HOURS_AGO_RE = re.compile(r"\bposted\s+(\d{1,3})\s+hours?\s+ago\b", re.IGNORECASE)


def _today(value: Optional[str] = None) -> date:
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return date.today()


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _to_iso(found: Optional[date]) -> Optional[str]:
    return found.isoformat() if found else None


def extract_posting_date(*values: Any, today: Optional[str] = None) -> Optional[str]:
    """Extract a likely posting date from job-board title/snippet text."""
    text = " ".join(str(value or "") for value in values)
    if not text.strip():
        return None

    base = _today(today)
    lowered = text.lower()

    if re.search(r"\bposted\s+today\b", lowered):
        return base.isoformat()
    if re.search(r"\bposted\s+yesterday\b", lowered):
        return (base - timedelta(days=1)).isoformat()

    if match := _HOURS_AGO_RE.search(text):
        return base.isoformat()
    if match := _DAYS_AGO_RE.search(text):
        return (base - timedelta(days=int(match.group(1)))).isoformat()

    if match := _ISO_RE.search(text):
        return _to_iso(_safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3))))

    if match := _DAY_MONTH_RE.search(text):
        day, month_name, year = match.groups()
        month = _MONTHS[month_name.lower()]
        return _to_iso(_safe_date(int(year), month, int(day)))

    if match := _MONTH_DAY_RE.search(text):
        month_name, day, year = match.groups()
        month = _MONTHS[month_name.lower()]
        return _to_iso(_safe_date(int(year), month, int(day)))

    if match := _NUMERIC_RE.search(text):
        day, month, year = match.groups()
        return _to_iso(_safe_date(int(year), int(month), int(day)))

    return None


def is_on_or_after(date_text: Any, cutoff: str) -> bool:
    if not date_text:
        return True
    try:
        found = datetime.fromisoformat(str(date_text)).date()
        minimum = date.fromisoformat(cutoff)
    except ValueError:
        return True
    return found >= minimum
