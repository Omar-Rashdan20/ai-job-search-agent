from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


EMPTY_VALUES: frozenset[Any] = frozenset({
    None, "", "None", "none", "null", "N/A", "n/a", "-", "\u2014",
})

MAX_QUERIES = 10
MAX_SKILLS = 8

_LIST_SEP: re.Pattern[str] = re.compile(r"[,;\n]+")


def _is_empty(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip() in EMPTY_VALUES
    try:
        return value in EMPTY_VALUES
    except TypeError:
        return False


def _first_value(data: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = data.get(key)
        if not _is_empty(value):
            return value
    return default


def _clean_text(value: Any, default: str = "") -> str:
    return default if _is_empty(value) else str(value).strip()


def _optional_text(value: Any) -> Optional[str]:
    text = _clean_text(value)
    return text or None


def _listify(value: Any) -> list[str]:
    if _is_empty(value):
        return []
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            if isinstance(item, dict):
                item = _first_value(item, "query", "search_query", "title", "value")
            if text := _clean_text(item):
                values.append(text)
        return values
    if isinstance(value, dict):
        return _listify(_first_value(value, "queries", "search_queries", "query", default=[]))
    return [text for part in _LIST_SEP.split(str(value)) if (text := part.strip())]


def _safe_int(value: Any, default: int = 0) -> int:
    if _is_empty(value):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if _is_empty(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if _is_empty(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "verified"}
    return bool(value)


class _NormalizedModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _run_normalizer(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return cls._normalize(dict(data))
        return cls._normalize_other(data)

    @classmethod
    def _normalize(cls, data: dict[str, Any]) -> dict[str, Any]:
        return data

    @classmethod
    def _normalize_other(cls, data: Any) -> Any:
        return data


class SearchQuery(_NormalizedModel):
    queries: list[str] = Field(default_factory=list, title="Optimized job search queries")

    @classmethod
    def _normalize(cls, data: dict[str, Any]) -> dict[str, Any]:
        raw = _first_value(data, "queries", "search_queries", "query", default=[])
        return {"queries": _listify(raw)[:MAX_QUERIES]}

    @classmethod
    def _normalize_other(cls, data: Any) -> dict[str, Any]:
        if isinstance(data, list):
            return {"queries": _listify(data)[:MAX_QUERIES]}
        return {"queries": []}


class SingleSearchResult(_NormalizedModel):
    title: str = ""
    url: str = Field(default="", title="The job posting URL")
    content: str = ""
    score: float = 0.0
    search_query: str = ""
    posting_date: Optional[str] = None
    source_type: str = "scraped"
    source_note: str = ""
    is_verified_url: bool = False

    @classmethod
    def _normalize(cls, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": _clean_text(_first_value(data, "title", "name")),
            "url": _clean_text(_first_value(data, "url", "link", "href")),
            "content": _clean_text(
                _first_value(data, "content", "raw_content", "snippet", "description")
            ),
            "score": _safe_float(data.get("score")),
            "search_query": _clean_text(_first_value(data, "search_query", "query")),
            "posting_date": _optional_text(_first_value(data, "posting_date", "posted_date")),
            "source_type": _clean_text(_first_value(data, "source_type"), "scraped"),
            "source_note": _clean_text(_first_value(data, "source_note", "note")),
            "is_verified_url": _safe_bool(data.get("is_verified_url", False)),
        }


class AllSearchResults(BaseModel):
    results: list[SingleSearchResult] = Field(default_factory=list)


class SingleJob(_NormalizedModel):
    page_url: str = Field(default="", title="Original URL of the job posting")
    job_title: str = Field(default="", title="Job title")
    company_name: str = Field(default="", title="Company name")
    job_location: str = Field(default="", title="Job location")
    job_type: str = Field(default="", title="Employment type")
    posting_date: Optional[str] = Field(default=None, title="Posting date")
    application_deadline: Optional[str] = Field(default=None, title="Application deadline")
    expected_start_date: Optional[str] = Field(default=None, title="Expected start date")
    required_experience: Optional[str] = Field(default=None, title="Required experience")
    required_skills: list[str] = Field(default_factory=list, title="Required skills")
    education_level: Optional[str] = Field(default=None, title="Education level")
    job_description: str = Field(default="", title="Job description")
    apply_url: str = Field(default="", title="Direct apply URL")
    source_type: str = Field(default="scraped", title="Source type")
    source_note: str = Field(default="", title="Source note")
    is_verified_url: bool = Field(default=False, title="Whether the URL was verified")

    @classmethod
    def _normalize(cls, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "page_url": _clean_text(_first_value(data, "page_url", "url", "link")),
            "job_title": _clean_text(_first_value(data, "job_title", "title", "role", "position")),
            "company_name": _clean_text(_first_value(data, "company_name", "company", "employer")),
            "job_location": _clean_text(_first_value(data, "job_location", "location")),
            "job_type": _clean_text(_first_value(data, "job_type", "employment_type", "type")),
            "posting_date": _optional_text(
                _first_value(data, "posting_date", "posted_date", "date_posted", "publish_date")
            ),
            "application_deadline": _optional_text(
                _first_value(data, "application_deadline", "deadline", "closing_date")
            ),
            "expected_start_date": _optional_text(
                _first_value(data, "expected_start_date", "start_date")
            ),
            "required_experience": _optional_text(
                _first_value(data, "required_experience", "experience")
            ),
            "required_skills": _listify(
                _first_value(data, "required_skills", "skills", "requirements", default=[])
            )[:MAX_SKILLS],
            "education_level": _optional_text(_first_value(data, "education_level", "education")),
            "job_description": _clean_text(
                _first_value(data, "job_description", "description", "content")
            ),
            "apply_url": _clean_text(
                _first_value(data, "apply_url", "application_url", "apply_link", "page_url", "url")
            ),
            "source_type": _clean_text(_first_value(data, "source_type"), "scraped"),
            "source_note": _clean_text(_first_value(data, "source_note", "note")),
            "is_verified_url": _safe_bool(data.get("is_verified_url", False)),
        }


class JobWithSummary(SingleJob):
    job_summary: str = Field(default="", title="3-5 sentence summary of the job")
    recommendation_rank: int = Field(default=0, title="Rank from 1 (best) to N (worst)")
    recommendation_notes: list[str] = Field(default_factory=list, title="Recommendation notes")
    skill_gap: list[str] = Field(default_factory=list, title="Missing skills")

    @classmethod
    def _normalize(cls, data: dict[str, Any]) -> dict[str, Any]:
        normalized = SingleJob._normalize(data)
        normalized.update({
            "job_summary": _clean_text(
                _first_value(data, "job_summary", "summary", "description_summary", "recommendation_summary")
            ),
            "recommendation_rank": _safe_int(data.get("recommendation_rank")),
            "recommendation_notes": _listify(
                _first_value(data, "recommendation_notes", "notes", default=[])
            ),
            "skill_gap": _listify(
                _first_value(data, "skill_gap", "missing_skills", default=[])
            ),
        })
        return normalized


class AllJobs(BaseModel):
    jobs: list[SingleJob] = Field(default_factory=list)


class AllJobsWithSummary(BaseModel):
    jobs: list[JobWithSummary] = Field(default_factory=list)
