import re
from typing import Any

_WORD_RE = re.compile(r"[a-z0-9+#.]+")

_GENERIC_TERMS: frozenset[str] = frozenset({
    "and", "for", "job", "jobs", "opening", "openings", "opportunity",
    "opportunities", "position", "positions", "role", "roles", "vacancy",
    "vacancies", "remote", "hybrid", "junior", "senior", "urgent", "hiring",
    "internship", "intern", "full", "time", "part",
})

_TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "ai": ("ai", "artificial intelligence", "machine learning", "ml", "llm"),
    "ml": ("ml", "machine learning", "ai", "artificial intelligence"),
    "developer": ("developer", "software engineer", "programmer"),
    "engineer": ("engineer", "engineering"),
}


def _tokens(value: Any) -> list[str]:
    return [
        token
        for token in _WORD_RE.findall(str(value or "").lower())
        if token not in _GENERIC_TERMS and (len(token) >= 3 or token in {"ai", "ml", "qa", "hr"})
    ]


def _term_matches(term: str, text: str) -> bool:
    aliases = _TERM_ALIASES.get(term, (term,))
    return any(re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text) for alias in aliases)


def matches_job_title(job_title: Any, *values: Any) -> bool:
    """
    Return True when a result is relevant to the role entered by the user.

    Search snippets often mention related jobs in sidebars, so this requires a
    meaningful share of the user's title terms instead of accepting one loose
    mention buried anywhere on the page.
    """
    required_terms = list(dict.fromkeys(_tokens(job_title)))
    if not required_terms:
        return True

    title_text = str(values[0] or "").lower() if values else ""
    title_tokens = _tokens(title_text)
    if title_tokens and not any(_term_matches(term, title_text) for term in required_terms):
        return False

    text = " ".join(str(v or "") for v in values).lower()
    if not text:
        return False

    matched = [term for term in required_terms if _term_matches(term, text)]
    if len(required_terms) == 1:
        return bool(matched)

    if "ai" in required_terms and "engineer" in required_terms:
        return "ai" in matched and "engineer" in matched

    minimum_matches = max(1, (len(required_terms) + 1) // 2)
    return len(matched) >= minimum_matches
