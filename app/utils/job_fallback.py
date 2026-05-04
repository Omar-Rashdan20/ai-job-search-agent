from urllib.parse import urlparse

from app.utils.date_utils import extract_posting_date, is_on_or_after
from app.utils.job_relevance import matches_job_title
from app.utils.location_utils import mentions_country
from app.utils.url_utils import classify_source, normalize_url, sanitize_job_links
from app.utils.work_mode import matches_work_mode


def jobs_from_search_results(
    results: list[dict],
    limit: int,
    country: str,
    job_title: str = "",
    work_mode: str = "Any",
    today: str = "",
    cutoff: str = "",
) -> list[dict]:
    jobs: list[dict] = []
    seen_urls: set[str] = set()

    for rank, result in enumerate(results, start=1):
        if len(jobs) >= limit:
            break

        url = normalize_url(result.get("url"))
        if not url or url in seen_urls:
            continue

        title = str(result.get("title") or "Job posting").strip()
        content = str(result.get("content") or result.get("raw_content") or "").strip()

        search_query = str(result.get("search_query") or "")

        if not mentions_country(country, title, content, url):
            continue
        if not matches_job_title(job_title, title, content, url, search_query):
            continue
        if not matches_work_mode(work_mode, title, content, url, search_query):
            continue

        posting_date = result.get("posting_date") or extract_posting_date(title, content, today=today)
        if cutoff and not is_on_or_after(posting_date, cutoff):
            continue

        source_type = result.get("source_type") or classify_source(url)
        source_note = str(result.get("source_note") or "").strip()
        if source_type == "search_only" and not source_note:
            source_note = "Search-only result. Open the link to view full details."

        host = urlparse(url).netloc.replace("www.", "") or "unknown"
        summary = content or (
            "This job card was built from search data because detailed "
            "scraping or summarization was unavailable."
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
                    source_note or "This card uses Tavily search data."
                ],
                "skill_gap": [],
                "source_type": source_type,
                "source_note": source_note,
                "is_verified_url": bool(result.get("is_verified_url", False)),
                "search_query": search_query,
            },
        )

        if job:
            jobs.append(job)
            seen_urls.add(url)

    return jobs
