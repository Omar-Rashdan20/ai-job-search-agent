from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional

from crewai.tools import tool
from scrapegraph_py import Client

from app.config import SCRAPE_TIMEOUT_SECONDS, SCRAPEGRAPH_API_KEY
from app.models.job_model import SingleJob
from app.utils.url_utils import should_skip_scraping

# Module-level singleton — read-only after init, safe for concurrent reads.
_client: Optional[Client] = None

# Shared executor — avoids spawning a new thread pool on every scrape call.
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
    allowed_domains: Optional[list[str]] = None,
):
    schema_json = SingleJob.schema_json()
    target_websites = ", ".join(allowed_domains or [])

    prompt = (
        f"Target job websites: {target_websites}. "
        f"TODAY is {today}. Only extract jobs posted after {cutoff}. "
        f"Only extract jobs located in or clearly tied to {country}. "
        "Only read direct single job posting pages from the target websites. "
        "If the page is old, expired, outside the country, a listing page, a search page, "
        "or outside the target websites, return an empty JSON object {} immediately.\n\n"
        "Otherwise, extract the structured job information from this page.\n"
        f"Return a JSON object matching this schema:\n```json\n{schema_json}\n```\n"
        "Rules:\n"
        "- If a field is not available, set it to null or an empty list.\n"
        "- Do not fabricate any information. Only extract what is explicitly stated.\n"
        "- If this page lists multiple jobs instead of a single posting, return {}.\n"
        "- Do not extract salary information."
    )

    def _scrape(page_url: str) -> dict:
        return _get_client().smartscraper(website_url=page_url, user_prompt=prompt)

    @tool
    def web_scraping_tool(page_url: str) -> dict:
        """
        Scrape one job posting page and extract structured job details.

        Args:
            page_url: The direct URL of a single job posting.

        Returns:
            dict with keys page_url, details (extracted data), and optional error/skipped.
        """
        if should_skip_scraping(page_url):
            return {"page_url": page_url, "details": {}, "skipped": "blocked_or_slow_site"}

        future = _executor.submit(_scrape, page_url)
        try:
            details = future.result(timeout=SCRAPE_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            future.cancel()
            return {"page_url": page_url, "details": {}, "error": "scrape_timeout"}
        except Exception as exc:
            return {"page_url": page_url, "details": {}, "error": str(exc)}

        return {"page_url": page_url, "details": details or {}}

    return web_scraping_tool
