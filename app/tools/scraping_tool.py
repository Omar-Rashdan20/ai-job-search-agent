import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional

from crewai.tools import tool
from scrapegraph_py import Client

from app.config import SCRAPE_TIMEOUT_SECONDS, SCRAPEGRAPH_API_KEY
from app.models.job_model import SingleJob
from app.utils.cache_utils import cache_get, cache_set
from app.utils.url_utils import classify_source, normalize_url, should_skip_scraping

_client: Optional[Client] = None
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scrape")


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(api_key=SCRAPEGRAPH_API_KEY)
    return _client


def build_web_scraping_tool(
    today: str,
    cutoff: str,
    country: str,
    work_mode: str = "Any",
):
    schema_json = json.dumps(SingleJob.model_json_schema(), indent=2)

    prompt = (
        f"TODAY is {today}. Only extract jobs posted after {cutoff}. "
        f"Only extract jobs located in or clearly tied to {country}. "
        f"Respect this work mode: {work_mode}. "
        "Only read official company career pages or ATS job pages. "
        "Never scrape LinkedIn, Bayt, Indeed, or Glassdoor. "
        "If the page is old, expired, outside the country, outside the work mode, "
        "a listing page, a search page, a blocked job board, or not an official/ATS page, "
        "return an empty JSON object {} immediately.\n\n"
        "Otherwise, extract the structured job information from this page.\n"
        f"Return a JSON object matching this schema:\n```json\n{schema_json}\n```\n"
        "Rules:\n"
        "- If a field is not available, set it to null or an empty list.\n"
        "- Do not fabricate any information. Only extract what is explicitly stated.\n"
        "- If this page lists multiple jobs instead of a single posting, return {}.\n"
        "- Do not extract salary information."
    )

    def _scrape(page_url: str) -> dict:
        return _get_client().smartscraper(
            website_url=page_url,
            user_prompt=prompt,
        )

    @tool
    def web_scraping_tool(page_url: str) -> dict:
        normalized_url = normalize_url(page_url)
        source_type = classify_source(normalized_url)

        if should_skip_scraping(normalized_url):
            return {
                "page_url": normalized_url,
                "details": {
                    "page_url": normalized_url,
                    "apply_url": normalized_url,
                    "source_type": source_type or "search_only",
                    "source_note": "Search-only result. Open the link to view full details.",
                    "is_verified_url": True,
                },
                "skipped": "search_only_or_not_official_ats",
                "source_type": source_type or "search_only",
            }

        cached = cache_get("scrapegraph", normalized_url)
        if cached:
            return {
                "page_url": normalized_url,
                "details": cached,
                "source_type": "scraped",
                "cached": True,
            }

        future = _executor.submit(_scrape, normalized_url)

        try:
            details = future.result(timeout=SCRAPE_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            future.cancel()
            return {
                "page_url": normalized_url,
                "details": {},
                "source_type": "scraped",
                "error": "scrape_timeout",
            }
        except Exception as exc:
            return {
                "page_url": normalized_url,
                "details": {},
                "source_type": "scraped",
                "error": str(exc),
            }

        details = details or {}

        if details:
            details["page_url"] = details.get("page_url") or normalized_url
            details["apply_url"] = details.get("apply_url") or normalized_url
            details["source_type"] = "scraped"
            details["source_note"] = ""
            details["is_verified_url"] = True

            cache_set("scrapegraph", normalized_url, details)

        return {
            "page_url": normalized_url,
            "details": details,
            "source_type": "scraped",
        }

    return web_scraping_tool
