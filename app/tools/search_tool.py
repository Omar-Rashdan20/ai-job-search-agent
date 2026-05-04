from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from crewai.tools import tool
from tavily import TavilyClient

from app.config import TAVILY_API_KEY
from app.utils.cache_utils import cache_get, cache_set
from app.utils.date_utils import extract_posting_date, is_on_or_after
from app.utils.job_relevance import matches_job_title
from app.utils.location_utils import mentions_country, normalize_country
from app.utils.url_utils import (
    classify_source,
    deduplicate_results,
    is_likely_job_page,
    normalize_url,
)
from app.utils.work_mode import matches_work_mode, normalize_work_mode

SEARCH_RESULTS_PER_QUERY = 5

_client: Optional[TavilyClient] = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=TAVILY_API_KEY)
    return _client


def build_search_engine_tool(
    today: str,
    cutoff: str,
    month_year: str,
    country: str,
    job_title: str,
    work_mode: str = "Any",
):
    @tool
    def search_engine_tool(query: str) -> dict:
        return search_jobs(
            query=query,
            today=today,
            cutoff=cutoff,
            month_year=month_year,
            country=country,
            job_title=job_title,
            work_mode=work_mode,
        )

    return search_engine_tool


def _enrich_query(
    query: str,
    month_year: str,
    country: str,
    job_title: str,
    work_mode: str,
) -> str:
    q = query.strip()

    if job_title and job_title.lower() not in q.lower():
        q = f"{job_title} {q}"

    normalized_work_mode = normalize_work_mode(work_mode)
    if normalized_work_mode != "Any" and normalized_work_mode.lower() not in q.lower():
        q = f"{q} {normalized_work_mode}"

    if month_year.lower() not in q.lower():
        q = f"{q} {month_year}"

    if "job" not in q.lower():
        q = f"{q} job"

    q = f"{q} apply now job description"

    normalized_country = normalize_country(country)
    if normalized_country and normalized_country not in q.lower():
        q = f"{q} {country}"

    return q


def _is_remote_text(*parts: str) -> bool:
    text = " ".join(str(p or "") for p in parts).lower()
    return any(word in text for word in ["remote", "work from home", "anywhere"])


def _passes_country_filter(
    country: str,
    work_mode: str,
    title: str = "",
    content: str = "",
    raw_content: str = "",
    url: str = "",
) -> bool:
    """
    Country filter:
    - If country is mentioned, pass.
    - If work mode is Remote and result looks remote, pass.
    - Otherwise reject.
    """
    if mentions_country(country, title, content, raw_content, url):
        return True

    if normalize_work_mode(work_mode) == "Remote" and _is_remote_text(
        title, content, raw_content, url
    ):
        return True

    return False


def search_jobs(
    query: str,
    today: str,
    cutoff: str,
    month_year: str,
    country: str,
    job_title: str = "",
    work_mode: str = "Any",
    max_results: int = SEARCH_RESULTS_PER_QUERY,
) -> dict:
    enriched = _enrich_query(query, month_year, country, job_title, work_mode)

    cached = cache_get("tavily_search", enriched)

    if cached is None:
        try:
            raw = _get_client().search(
                enriched,
                max_results=max_results,
                search_depth="basic",
            )
            cache_set("tavily_search", enriched, raw)
        except Exception as exc:
            return {"query": enriched, "results": [], "error": str(exc)}
    else:
        raw = cached

    filtered: list[dict] = []
    seen_urls: set[str] = set()

    for result in deduplicate_results(raw.get("results", [])):
        url = normalize_url(result.get("url"))

        if not url or url in seen_urls:
            continue

        source_type = classify_source(url)

        if source_type == "invalid":
            continue

        if not is_likely_job_page(url):
            continue

        title = result.get("title", "")
        content = result.get("content", "")
        raw_content = result.get("raw_content", "")

        if not _passes_country_filter(
            country=country,
            work_mode=work_mode,
            title=title,
            content=content,
            raw_content=raw_content,
            url=url,
        ):
            continue

        if not matches_job_title(
            job_title,
            title,
            content,
            raw_content,
            url,
            enriched,
        ):
            continue

        if not matches_work_mode(
            work_mode,
            title,
            content,
            raw_content,
            url,
            enriched,
        ):
            continue

        text = " ".join(
            str(result.get(key, ""))
            for key in ("title", "url", "content", "raw_content")
        ).lower()

        if f"posted before {cutoff}" in text:
            continue

        posting_date = extract_posting_date(
            title,
            content,
            raw_content,
            today=today,
        )

        if posting_date and not is_on_or_after(posting_date, cutoff):
            continue

        result["url"] = url
        result["search_query"] = query
        result["source_type"] = source_type
        result["source_note"] = (
            "Search-only result. Open the link to view full details."
            if source_type == "search_only"
            else ""
        )
        result["is_verified_url"] = True

        if posting_date:
            result["posting_date"] = posting_date

        filtered.append(result)
        seen_urls.add(url)

    return {"query": enriched, "results": filtered}


def search_jobs_concurrent(
    queries: list[str],
    today: str,
    cutoff: str,
    month_year: str,
    country: str,
    job_title: str,
    work_mode: str,
    limit: int,
) -> list[dict]:
    results: list[dict] = []
    seen_urls: set[str] = set()

    if not queries:
        return results

    with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as pool:
        futures = {
            pool.submit(
                search_jobs,
                query,
                today,
                cutoff,
                month_year,
                country,
                job_title,
                work_mode,
                SEARCH_RESULTS_PER_QUERY,
            ): query
            for query in queries
        }

        for future in as_completed(futures):
            try:
                batch = future.result().get("results", [])
            except Exception:
                continue

            for item in batch:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    results.append(item)
                    seen_urls.add(url)

                    if len(results) >= limit:
                        return results

    return results