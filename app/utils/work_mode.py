from typing import Any

WORK_MODES = ("Any", "Remote", "Hybrid", "Onsite")

_MODE_TERMS = {
    "remote": ("remote", "work from home", "wfh", "anywhere"),
    "hybrid": ("hybrid", "part remote"),
    "onsite": ("onsite", "on-site", "on site", "office-based", "office based"),
}


def normalize_work_mode(value: Any) -> str:
    text = str(value or "Any").strip().title()
    return text if text in WORK_MODES else "Any"


def matches_work_mode(work_mode: Any, *values: Any) -> bool:
    normalized = normalize_work_mode(work_mode).lower()
    if normalized == "any":
        return True

    text = " ".join(str(value or "") for value in values).lower()
    return any(term in text for term in _MODE_TERMS[normalized])
