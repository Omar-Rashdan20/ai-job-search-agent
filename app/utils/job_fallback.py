from urllib.parse import urlparse
from typing import Optional

from app.utils.date_utils import extract_posting_date, is_on_or_after
from app.utils.job_relevance import matches_job_title
from app.utils.location_utils import mentions_country
from app.utils.url_utils import sanitize_job_links


def jobs_from_search_results(
    results: list[dict],
    limit: int,
    country: str,
    job_title: str = "",
    today: str = "",
    cutoff: str = "",
    allowed_domains: Optional[list[str]] = None,
) -> list[dict]:
    """
    Build lightweight job dicts from raw Tavily search results.

    Used as a fallback when scraping is blocked or the crew returned no jobs.
    """
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    for rank, result in enumerate(results, start=1):
        if len(jobs) >= limit:
            break

        url = str(result.get("url") or "").strip()
        if not url or url in seen_urls:
            continue

        title = str(result.get("title") or "Job posting").strip()
        content = str(result.get("content") or result.get("raw_content") or "").strip()

        if not mentions_country(country, title, content, url):
            continue
        if not matches_job_title(job_title, title, content, url):
            continue

        posting_date = extract_posting_date(title, content, today=today)
        if cutoff and not is_on_or_after(posting_date, cutoff):
            continue

        host = urlparse(url).netloc.replace("www.", "") or "unknown"
        summary = content or (
            "This job card was built from search data because detailed "
            "scraping or summarisation was unavailable."
        )

        job = sanitize_job_links(
            {
                "page_url": url,
                "apply_url": url,
                "job_title": title,
                "company_name": host,
                "job_location": country,
                "job_type": "",
                "posting_date": posting_date,
                "application_deadline": None,
                "expected_start_date": None,
                "required_experience": None,
                "required_skills": [],
                "education_level": None,
                "job_description": content or title,
                "job_summary": summary,
                "recommendation_rank": rank,
                "recommendation_notes": [
                    "Scraping was unavailable — this card uses Tavily search data."
                ],
                "skill_gap": [],
            },
            allowed_domains=allowed_domains,
        )

        if job:
            jobs.append(job)
            seen_urls.add(url)

    return jobs
