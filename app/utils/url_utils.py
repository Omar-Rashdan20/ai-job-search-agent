from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

try:
    import requests
except ModuleNotFoundError:
    requests = None

from app.utils.cache_utils import cache_get, cache_set

REQUEST_TIMEOUT_SECONDS = 5

_EMPTY_URL_VALUES: frozenset[str] = frozenset({"", "None", "none", "null", "N/A", "n/a", "#"})

_SEARCH_URL_MARKERS: tuple[str, ...] = (
    "/jobs/search",
    "/job-search",
    "/jobsearch",
    "/search/jobs",
    "/search?",
    "/s/jobs/",
    "/jobs-in-",
    "/job-vacancies",
    "/vacancies",
    "/q?",
    "/q/",
    "keywords=",
    "location=",
    "page_no=",
    "order_by=",
    "search_period=",
    "customized_search_type=",
)

_ATS_DOMAINS: tuple[str, ...] = (
    "greenhouse.io",
    "lever.co",
    "workable.com",
    "ashbyhq.com",
    "smartrecruiters.com",
)

_JOB_BOARD_DOMAINS: tuple[str, ...] = (
    *SEARCH_ONLY_DOMAINS,
    "akhtaboot.com",
    "tanqeeb.com",
    "shine.com",
    "jooble.org",
    "careerjet.",
    "monster.",
    "naukri.",
    "naukrigulf.com",
    "gulftalent.com",
    "ziprecruiter.com",
    "simplyhired.com",
    "dice.com",
    "remoteok.com",
    "weworkremotely.com",
)

_GENERIC_LISTING_PATHS: frozenset[str] = frozenset({
    "", "/", "/jobs", "/job", "/careers", "/career", "/en/jobs",
})

_TRACKING_PARAMS: frozenset[str] = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid",
})


def _clean_url(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text in _EMPTY_URL_VALUES else text


def normalize_url(url: object) -> str:
    text = _clean_url(url)
    if not text:
        return ""

    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return text

    query = urlencode(
        [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
         if key.lower() not in _TRACKING_PARAMS],
        doseq=True,
    )
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower().replace("www.", ""),
        query=query,
        fragment="",
    )
    return urlunparse(normalized).rstrip("/")


def is_valid_url(url: object) -> bool:
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_http_url(value: object) -> bool:
    return is_valid_url(value)


def normalize_domain(value: object) -> str:
    text = _clean_url(value).lower()
    if not text:
        return ""
    if "://" in text:
        text = urlparse(normalize_url(text)).netloc
    return text.replace("www.", "").strip("/")


def _host_matches(host: str, domains: list[str] | tuple[str, ...]) -> bool:
    normalized = normalize_domain(host)
    return any(
        normalized == domain
        or normalized.endswith(f".{domain}")
        or domain in normalized
        for domain in domains
    )


def is_allowed_domain(value: object, allowed_domains: Optional[list[str]]) -> bool:
    if not allowed_domains:
        return True
    if not is_valid_url(value):
        return False
    host = urlparse(normalize_url(value)).netloc
    normalized_domains = [normalize_domain(domain) for domain in allowed_domains if normalize_domain(domain)]
    return _host_matches(host, normalized_domains)


def is_reachable_url(url: object, timeout: int = REQUEST_TIMEOUT_SECONDS) -> bool:
    normalized = normalize_url(url)
    if not is_valid_url(normalized):
        return False

    cached = cache_get("url_reachable", normalized)
    if isinstance(cached, bool):
        return cached

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    if requests is not None:
        for request_fn in (requests.head, requests.get):
            try:
                response = request_fn(
                    normalized,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True,
                )
                reachable = response.status_code < 400
                cache_set("url_reachable", normalized, reachable)
                return reachable
            except requests.RequestException:
                continue

    for method in ("HEAD", "GET"):
        try:
            request = Request(normalized, headers=headers, method=method)
            with urlopen(request, timeout=timeout) as response:
                reachable = response.status < 400
                cache_set("url_reachable", normalized, reachable)
                return reachable
        except HTTPError as exc:
            reachable = exc.code < 400
            cache_set("url_reachable", normalized, reachable)
            return reachable
        except (TimeoutError, URLError, OSError, ValueError):
            continue

    cache_set("url_reachable", normalized, False)
    return False


def _contains_allowed_scrape_keyword(url: str) -> bool:
    lowered = url.lower()
    return any(keyword in lowered for keyword in SCRAPE_ALLOWED_KEYWORDS)


def is_likely_job_page(url: object) -> bool:
    normalized = normalize_url(url)
    if not is_valid_url(normalized):
        return False

    parsed = urlparse(normalized)
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
        return "viewjob" in query or "/rc/clk" in path
    if "bayt.com" in host:
        return any(ch.isdigit() for ch in path)
    if "glassdoor." in host:
        return "job-listing" in path or "joblisting" in path
    if _host_matches(host, _ATS_DOMAINS):
        return len(path.strip("/")) > 0
    if _host_matches(host, _JOB_BOARD_DOMAINS):
        return any(ch.isdigit() for ch in path) or "job" in path

    has_source_keyword = _contains_allowed_scrape_keyword(normalized)
    has_specific_path = len([part for part in path.split("/") if part]) >= 2
    has_detail_signal = any(ch.isdigit() for ch in path) or any(
        marker in path for marker in ("engineer", "developer", "analyst", "manager", "specialist", "consultant")
    )
    return has_source_keyword and has_specific_path and has_detail_signal


def is_likely_job_posting_url(value: object) -> bool:
    return is_likely_job_page(value)


def classify_source(url: object) -> str:
    normalized = normalize_url(url)
    if not is_likely_job_page(normalized):
        return "invalid"

    host = urlparse(normalized).netloc
    if _host_matches(host, SEARCH_ONLY_DOMAINS):
        return "search_only"
    if _host_matches(host, _JOB_BOARD_DOMAINS):
        return "search_only"
    if _host_matches(host, _ATS_DOMAINS):
        return "scraped"
    if _contains_allowed_scrape_keyword(normalized):
        return "scraped"
    return "invalid"


def should_skip_scraping(value: object) -> bool:
    return classify_source(value) != "scraped"


def is_reachable_job_url(value: object, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS) -> bool:
    return is_likely_job_page(value) and is_reachable_url(value, timeout=int(timeout_seconds))


def deduplicate_results(results: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen_urls: set[str] = set()

    for result in results:
        if not isinstance(result, dict):
            continue
        url = normalize_url(result.get("url") or result.get("page_url") or result.get("apply_url"))
        if not url or url in seen_urls or not is_valid_url(url):
            continue
        cleaned = dict(result)
        cleaned["url"] = url
        deduped.append(cleaned)
        seen_urls.add(url)

    return deduped


def sanitize_job_links(
    job: dict,
    allowed_domains: Optional[list[str]] = None,
) -> Optional[dict]:
    cleaned = dict(job)
    page_url = normalize_url(cleaned.get("page_url"))
    apply_url = normalize_url(cleaned.get("apply_url")) or page_url

    page_source = classify_source(page_url)
    apply_source = classify_source(apply_url)

    if page_source == "invalid" and apply_source != "invalid":
        page_url, page_source = apply_url, apply_source
    if apply_source == "invalid" and page_source != "invalid":
        apply_url, apply_source = page_url, page_source

    if page_source == "invalid" or apply_source == "invalid":
        return None
    if not is_allowed_domain(page_url, allowed_domains):
        return None
    if not is_allowed_domain(apply_url, allowed_domains):
        return None

    source_type = cleaned.get("source_type") or page_source
    if source_type not in {"scraped", "search_only"}:
        source_type = page_source

    cleaned["page_url"] = page_url
    cleaned["apply_url"] = apply_url
    cleaned["source_type"] = source_type
    if source_type == "search_only":
        cleaned.setdefault(
            "source_note",
            "Search-only result. Open the link to view full details.",
        )
    return cleaned
