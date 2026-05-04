from typing import Any

# Maps a normalized country name to substrings that should NOT match it.
# Prevents false positives like "West Jordan, Utah" matching country="jordan".
_COUNTRY_FALSE_POSITIVES: dict[str, tuple[str, ...]] = {
    "jordan": (
        "west jordan",
        "south jordan",
        "jordan, ut",
        "jordan ut",
        "utah",
        "united states",
    ),
}


def normalize_country(country: Any) -> str:
    return str(country or "").strip().lower()


def mentions_country(country: Any, *values: Any) -> bool:
    """
    Return True if any of *values* mentions the given country.

    Joins all values into a single lowercase string so the search is O(n)
    instead of O(n * k) per value.
    """
    normalized = normalize_country(country)
    if not normalized:
        return True

    text = " ".join(str(v or "") for v in values).lower()

    false_positives = _COUNTRY_FALSE_POSITIVES.get(normalized, ())
    if false_positives and any(fp in text for fp in false_positives):
        return False

    return normalized in text
