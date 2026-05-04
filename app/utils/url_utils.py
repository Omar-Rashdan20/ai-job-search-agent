from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from typing import Optional

_EMPTY_URL_VALUES: frozenset[str] = frozenset({"", "None", "none", "null", "N/A", "n/a", "#"})

_SEARCH_URL_MARKERS: tuple[str, ...] = (
    "/jobs/search",
    "/jobsearch",
    "/s/jobs/",
    "/q?",
    "/q/",
    "keywords=",
    "location=",
    "page_no=",
    "order_by=",
    "search_period=",
    "customized_search_type=",
)

_GENERIC_LISTING_PATHS: frozenset[str] = frozenset({
    "", "/", "/jobs", "/job", "/careers", "/career", "/en/jobs",
})

# Domains that block automated scraping — use search/fallback data only.
_BLOCKED_SCRAPE_DOMAINS: tuple[str, ...] = (
    "linkedin.com",
    "indeed.",
    "bayt.com",
)


def _clean_url(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text in _EMPTY_URL_VALUES else text


def is_http_url(value: object) -> bool:
    url = _clean_url(value)
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_domain(value: object) -> str:
    text = _clean_url(value).lower()
    if not text:
        return ""
    if "://" in text:
        text = urlparse(text).netloc
    return text.replace("www.", "").strip("/")


def is_allowed_domain(value: object, allowed_domains: Optional[list[str]]) -> bool:
    if not allowed_domains:
        return True
    url = _clean_url(value)
    if not is_http_url(url):
        return False
    host = normalize_domain(url)
    normalized = [normalize_domain(d) for d in allowed_domains if normalize_domain(d)]
    return any(host == d or host.endswith(f".{d}") for d in normalized)


def is_likely_job_posting_url(value: object) -> bool:
    url = _clean_url(value)
    if not is_http_url(url):
        return False

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = (parsed.path or "").lower().rstrip("/")
    query = (parsed.query or "").lower()
    combined = f"{path}?{query}"

    if any(marker in combined for marker in _SEARCH_URL_MARKERS):
        return False
    if path in _GENERIC_LISTING_PATHS:
        return False

    if "linkedin.com" in host:
        return "/jobs/view/" in path
    if "indeed." in host:
        return "viewjob" in path or "/rc/clk" in path
    if "bayt.com" in host:
        return any(ch.isdigit() for ch in path)
    if "akhtaboot.com" in host:
        return "/jobs" in path and any(ch.isdigit() for ch in path)
    if "tanqeeb.com" in host:
        return path not in {"", "/", "/en", "/ar"} and "jobs" in path

    return True


def should_skip_scraping(value: object) -> bool:
    url = _clean_url(value)
    if not is_http_url(url):
        return True
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in _BLOCKED_SCRAPE_DOMAINS)


def is_reachable_job_url(value: object, timeout_seconds: float = 4) -> bool:
    """
    Check whether a candidate job URL resolves to a live page.

    Some job boards block automated checks with 401/403 even when the link opens
    fine in a browser, so those are treated as reachable. Clear missing/expired
    signals such as 404/410 are rejected.
    """
    url = _clean_url(value)
    if not is_likely_job_posting_url(url):
        return False

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    for method in ("HEAD", "GET"):
        try:
            request = Request(url, headers=headers, method=method)
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.status < 400
        except HTTPError as exc:
            if exc.code in {401, 403, 405, 429}:
                return True
            if exc.code in {404, 410}:
                return False
            if method == "GET":
                return exc.code < 500
        except (TimeoutError, URLError, OSError, ValueError):
            if method == "GET":
                return False

    return False


def sanitize_job_links(
    job: dict,
    allowed_domains: Optional[list[str]] = None,
) -> Optional[dict]:
    """
    Validate and normalise page_url / apply_url on a job dict.

    Returns a new dict with cleaned URLs, or None if the job should be dropped.
    Neither URL may be a listing page, and both must be on an allowed domain.
    """
    cleaned = dict(job)
    page_url = _clean_url(cleaned.get("page_url"))
    apply_url = _clean_url(cleaned.get("apply_url"))

    page_ok = is_likely_job_posting_url(page_url)
    apply_ok = is_likely_job_posting_url(apply_url)

    # Cross-fill missing URLs before rejecting.
    if not apply_ok and page_ok:
        apply_url, apply_ok = page_url, True
    if not page_ok and apply_ok:
        page_url, page_ok = apply_url, True

    if not page_ok or not apply_ok:
        return None
    if not is_allowed_domain(page_url, allowed_domains):
        return None
    if not is_allowed_domain(apply_url, allowed_domains):
        return None

    cleaned["page_url"] = page_url
    cleaned["apply_url"] = apply_url
    return cleaned
