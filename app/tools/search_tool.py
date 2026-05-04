from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from crewai.tools import tool
from tavily import TavilyClient

from app.config import TAVILY_API_KEY
from app.utils.date_utils import extract_posting_date, is_on_or_after
from app.utils.location_utils import mentions_country, normalize_country
from app.utils.job_relevance import matches_job_title
from app.utils.url_utils import is_allowed_domain, is_likely_job_posting_url, normalize_domain

SEARCH_RESULTS_PER_QUERY = 8

# Module-level singleton — read-only after init, safe for concurrent use.
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
    allowed_domains: Optional[list[str]] = None,
):
    @tool
    def search_engine_tool(query: str) -> dict:
        """
        Search for job postings on the web using a search engine.
        Returns a list of relevant URLs and snippets.

        Args:
            query: A specific job search query string.

        Returns:
            dict: Search results with title, url, content, and score.
        """
        return search_jobs(
            query,
            today,
            cutoff,
            month_year,
            country=country,
            job_title=job_title,
            allowed_domains=allowed_domains,
        )

    return search_engine_tool


def _build_site_filter(allowed_domains: Optional[list[str]]) -> str:
    domains = [normalize_domain(d) for d in (allowed_domains or []) if normalize_domain(d)]
    return " OR ".join(f"site:{d}" for d in domains)


def _enrich_query(query: str, month_year: str, country: str, job_title: str = "") -> str:
    """Append freshness and location signals without duplicating site: operators."""
    q = query.strip()

    if job_title and job_title.lower() not in q.lower():
        q = f"{job_title} {q}"

    # Add month/year freshness signal
    if month_year.lower() not in q.lower():
        q = f"{q} {month_year}"

    q = f"{q} job opening apply now"

    # Add country if missing
    normalized = normalize_country(country)
    if normalized and normalized not in q.lower():
        q = f"{q} {country}"

    return q


def search_jobs(
    query: str,
    today: str,
    cutoff: str,
    month_year: str,
    country: str,
    job_title: str = "",
    max_results: int = SEARCH_RESULTS_PER_QUERY,
    allowed_domains: Optional[list[str]] = None,
) -> dict:
    # Build query — only inject site: filter when the caller hasn't already included it.
    enriched = _enrich_query(query, month_year, country, job_title)
    if "site:" not in enriched.lower():
        site_filter = _build_site_filter(allowed_domains)
        if site_filter:
            enriched = f"{enriched} ({site_filter})"

    try:
        raw = _get_client().search(enriched, max_results=max_results, search_depth="basic")
    except Exception as exc:
        return {"query": enriched, "results": [], "error": str(exc)}

    filtered: list[dict] = []
    seen_urls: set[str] = set()

    for result in raw.get("results", []):
        url = str(result.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        if not is_allowed_domain(url, allowed_domains):
            continue
        if not is_likely_job_posting_url(url):
            continue

        text = " ".join(
            str(result.get(k, ""))
            for k in ("title", "url", "content", "raw_content")
        ).lower()

        if not mentions_country(country, text):
            continue
        if not matches_job_title(
            job_title,
            result.get("title"),
            result.get("content"),
            result.get("raw_content"),
            result.get("url"),
        ):
            continue
        if f"posted before {cutoff}" in text:
            continue
        posting_date = extract_posting_date(
            result.get("title"),
            result.get("content"),
            result.get("raw_content"),
            today=today,
        )
        if posting_date and not is_on_or_after(posting_date, cutoff):
            continue

        result["url"] = url
        if posting_date:
            result["posting_date"] = posting_date
        result["search_query"] = query
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
    limit: int,
    allowed_domains: Optional[list[str]] = None,
) -> list[dict]:
    """Run multiple Tavily queries in parallel and return deduplicated results."""
    results: list[dict] = []
    seen_urls: set[str] = set()

    with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as pool:
        futures = {
            pool.submit(
                search_jobs,
                q,
                today,
                cutoff,
                month_year,
                country,
                job_title,
                SEARCH_RESULTS_PER_QUERY,
                allowed_domains,
            ): q
            for q in queries
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
