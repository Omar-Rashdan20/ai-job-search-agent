import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any, TypedDict

from crewai import Crew, Process
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

from app.agents.llm_factory import get_active_llm_provider, set_llm_provider_override
from app.agents.query_agent import create_query_agent
from app.agents.scraping_agent import create_scraping_agent
from app.agents.search_agent import create_search_agent
from app.agents.summary_agent import create_summary_agent
from app.config import (
    DEFAULT_COUNTRY,
    DEFAULT_JOB_TITLE,
    DEFAULT_TOP_RESULTS,
    DEFAULT_WEBSITES,
    LLM_FALLBACK_TO_OLLAMA,
    LLM_PROVIDER,
    LINK_CHECK_TIMEOUT_SECONDS,
    MAX_SCRAPE_URLS,
    OUTPUT_DIR,
)
from app.tasks.query_tasks import create_query_task
from app.tasks.scraping_tasks import create_scraping_task
from app.tasks.search_tasks import create_search_task
from app.tasks.summary_tasks import create_summary_task
from app.tools.scraping_tool import build_web_scraping_tool
from app.tools.search_tool import build_search_engine_tool, search_jobs
from app.models.workflow_types import DateConstraints
from app.utils.date_utils import extract_posting_date, is_on_or_after
from app.utils.job_fallback import jobs_from_search_results
from app.utils.job_relevance import matches_job_title
from app.utils.location_utils import mentions_country
from app.utils.url_utils import is_allowed_domain, is_reachable_job_url, sanitize_job_links

RANKED_JOBS_FILE = "step_4_ranked_jobs.json"
ERROR_FILE = "last_error.txt"
OUTPUT_FILES = [
    "step_1_search_queries.json",
    "step_2_search_results.json",
    "step_3_extracted_jobs.json",
    RANKED_JOBS_FILE,
    ERROR_FILE,
]


class JobSearchResult(TypedDict):
    jobs_json_path: str
    jobs: list[dict]


# ---------------------------------------------------------------------------
# Helpers — dates & I/O
# ---------------------------------------------------------------------------

def _get_date_constraints() -> DateConstraints:
    today = date.today()
    return {
        "today": today.isoformat(),
        "cutoff": (today - timedelta(days=30)).isoformat(),
        "month_year": today.strftime("%B %Y"),
    }


def _clear_previous_outputs() -> None:
    for filename in OUTPUT_FILES:
        path = os.path.join(OUTPUT_DIR, filename)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def _prepare_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["job_title"] = prepared.get("job_title") or DEFAULT_JOB_TITLE
    prepared["country"] = prepared.get("country") or DEFAULT_COUNTRY
    prepared["user_skills"] = prepared.get("user_skills") or "Not specified"
    prepared["no_results"] = max(1, int(prepared.get("no_results") or DEFAULT_TOP_RESULTS))
    prepared["scrape_limit"] = min(prepared["no_results"], MAX_SCRAPE_URLS)

    websites = prepared.get("websites_list") or DEFAULT_WEBSITES
    if isinstance(websites, str):
        websites = [item.strip() for item in websites.split(",") if item.strip()]
    prepared["websites_list"] = websites or DEFAULT_WEBSITES

    return prepared


def _build_user_context(inputs: dict[str, Any], dates: DateConstraints) -> StringKnowledgeSource:
    return StringKnowledgeSource(
        content=(
            f"The user is looking for a {inputs['job_title']} role "
            f"in {inputs['country']}. "
            f"Target job websites: {inputs['websites_list']}. "
            f"Their current skills are: {inputs['user_skills']}. "
            f"TODAY is {dates['today']}. Only use jobs posted after {dates['cutoff']}. "
            f"Only use jobs located in or clearly tied to {inputs['country']}. "
            "Only keep direct single job posting pages from the target websites. "
            "Reject listing pages, search pages, aggregators, old postings, salary-only pages, "
            "and any invented or rewritten URLs."
        )
    )


def _save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_error(message: str) -> None:
    path = os.path.join(OUTPUT_DIR, ERROR_FILE)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(message)


# ---------------------------------------------------------------------------
# Job filtering & sanitisation
# ---------------------------------------------------------------------------

def _job_matches_country(job: dict, country: str) -> bool:
    return mentions_country(
        country,
        job.get("job_location"),
        job.get("job_title"),
        job.get("job_description"),
        job.get("job_summary"),
        job.get("page_url"),
        job.get("apply_url"),
    )


def _job_matches_title(job: dict, job_title: str) -> bool:
    return matches_job_title(
        job_title,
        job.get("job_title"),
        job.get("job_description"),
        job.get("job_summary"),
        job.get("required_skills"),
        job.get("page_url"),
        job.get("apply_url"),
    )


def _sanitize_jobs(
    jobs: list[dict], allowed_domains: list[str], country: str, job_title: str
) -> list[dict]:
    out: list[dict] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if not _job_matches_country(job, country):
            continue
        if not _job_matches_title(job, job_title):
            continue
        cleaned = sanitize_job_links(job, allowed_domains=allowed_domains)
        if cleaned:
            out.append(cleaned)
    return out


def _load_sanitized_jobs(
    jobs_path: str, allowed_domains: list[str], country: str, job_title: str
) -> list[dict]:
    if not os.path.exists(jobs_path):
        return []
    try:
        data = _load_json(jobs_path)
    except (OSError, json.JSONDecodeError):
        return []

    jobs = _sanitize_jobs(data.get("jobs", []), allowed_domains, country, job_title)
    if jobs:
        # Only write back when something actually changed.
        data["jobs"] = jobs
        _save_json(jobs_path, data)
    return jobs


def _load_extracted_jobs(allowed_domains: list[str], country: str, job_title: str) -> list[dict]:
    path = os.path.join(OUTPUT_DIR, "step_3_extracted_jobs.json")
    if not os.path.exists(path):
        return []
    try:
        data = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return []

    jobs: list[dict] = []
    for index, job in enumerate(
        _sanitize_jobs(data.get("jobs", []), allowed_domains, country, job_title), start=1
    ):
        job.setdefault("job_summary", job.get("job_description", ""))
        job.setdefault("recommendation_rank", index)
        job.setdefault(
            "recommendation_notes",
            ["Summary ranking was unavailable — this card uses extracted job details."],
        )
        jobs.append(job)
    return jobs


def _load_search_results(allowed_domains: list[str], country: str, job_title: str) -> list[dict]:
    path = os.path.join(OUTPUT_DIR, "step_2_search_results.json")
    if not os.path.exists(path):
        return []
    try:
        data = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return []

    return [
        item
        for item in data.get("results", [])
        if (
            isinstance(item, dict)
            and is_allowed_domain(item.get("url"), allowed_domains)
            and mentions_country(
                country,
                item.get("title"),
                item.get("content"),
                item.get("raw_content"),
                item.get("url"),
            )
            and matches_job_title(
                job_title,
                item.get("title"),
                item.get("content"),
                item.get("raw_content"),
                item.get("url"),
            )
        )
    ]


def _save_jobs(jobs_path: str, jobs: list[dict]) -> None:
    _save_json(jobs_path, {"jobs": jobs})


def _filter_reachable_jobs(jobs: list[dict], limit: int) -> list[dict]:
    """Keep only final jobs whose apply/page link appears to resolve."""
    if not jobs:
        return []

    reachable_by_index: dict[int, bool] = {}
    with ThreadPoolExecutor(max_workers=min(len(jobs), 4)) as pool:
        futures = {
            pool.submit(
                is_reachable_job_url,
                job.get("apply_url") or job.get("page_url"),
                LINK_CHECK_TIMEOUT_SECONDS,
            ): index
            for index, job in enumerate(jobs)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                reachable_by_index[index] = future.result()
            except Exception:
                reachable_by_index[index] = False

    verified: list[dict] = []
    for index, job in enumerate(jobs):
        if not reachable_by_index.get(index):
            continue
        job["link_status"] = "verified"
        job["recommendation_rank"] = len(verified) + 1
        verified.append(job)
        if len(verified) >= limit:
            break

    return verified


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------

def _merge_jobs(
    primary: list[dict],
    fallback: list[dict],
    limit: int,
    allowed_domains: list[str],
    country: str,
    job_title: str,
) -> list[dict]:
    """
    Merge primary (crew-ranked) with fallback (search-result) jobs.

    Primary jobs are already sanitised — skip the second sanitise pass.
    Fallback jobs need sanitisation since they came from raw search results.
    """
    merged: list[dict] = []
    seen_urls: set[str] = set()

    for job in primary:
        if len(merged) >= limit:
            break
        if not _job_matches_country(job, country):
            continue
        if not _job_matches_title(job, job_title):
            continue
        url = job.get("apply_url", "")
        if not url or url in seen_urls:
            continue
        job["recommendation_rank"] = len(merged) + 1
        merged.append(job)
        seen_urls.add(url)

    for job in fallback:
        if len(merged) >= limit:
            break
        if not _job_matches_country(job, country):
            continue
        if not _job_matches_title(job, job_title):
            continue
        cleaned = sanitize_job_links(job, allowed_domains=allowed_domains)
        if not cleaned:
            continue
        url = cleaned["apply_url"]
        if url in seen_urls:
            continue
        cleaned["recommendation_rank"] = len(merged) + 1
        merged.append(cleaned)
        seen_urls.add(url)

    return merged


def _enrich_job_fit_fields(
    jobs: list[dict], user_skills: str, today: str, cutoff: str
) -> list[dict]:
    user_skill_set = {
        s.strip().lower()
        for s in user_skills.replace(";", ",").split(",")
        if s.strip()
    }

    for job in jobs:
        if not job.get("posting_date"):
            job["posting_date"] = extract_posting_date(
                job.get("job_title"),
                job.get("job_description"),
                job.get("job_summary"),
                today=today,
            )

        if not job.get("job_summary"):
            description = str(job.get("job_description") or "").strip()
            title = str(job.get("job_title") or "This role").strip()
            company = str(job.get("company_name") or "the company").strip()
            job["job_summary"] = description or f"{title} at {company}."

        required = [str(s).strip() for s in (job.get("required_skills") or []) if str(s).strip()]
        if not job.get("skill_gap") and required and user_skill_set:
            # Bug fix: normalise required skills to lowercase before comparison.
            job["skill_gap"] = [s for s in required if s.lower() not in user_skill_set]

    return [job for job in jobs if is_on_or_after(job.get("posting_date"), cutoff)]


# ---------------------------------------------------------------------------
# Tavily direct fallback (parallel)
# ---------------------------------------------------------------------------

def _direct_tavily_results(inputs: dict[str, Any], dates: DateConstraints) -> list[dict]:
    websites = inputs.get("websites_list") or []
    queries = [
        f"{inputs['job_title']} {inputs['country']} site:{website}"
        for website in websites
    ]
    limit = max(inputs["no_results"] * 3, inputs["no_results"] + 4)
    results: list[dict] = []
    seen: set[str] = set()

    with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as pool:
        futures = {
            pool.submit(
                search_jobs,
                q,
                dates["today"],
                dates["cutoff"],
                dates["month_year"],
                country=inputs["country"],
                job_title=inputs["job_title"],
                allowed_domains=websites,
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
                if url and url not in seen:
                    results.append(item)
                    seen.add(url)
            if len(results) >= limit:
                break

    return results


# ---------------------------------------------------------------------------
# Crew execution
# ---------------------------------------------------------------------------

def _is_quota_or_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in ("429", "quota", "rate limit", "ratelimit", "resource_exhausted", "too many requests")
    )


def _run_crew_once(
    inputs: dict[str, Any],
    dates: DateConstraints,
    search_tool: Any,
    scraping_tool: Any,
) -> None:
    query_agent = create_query_agent()
    search_agent = create_search_agent(search_tool)
    scraping_agent = create_scraping_agent(scraping_tool)
    summary_agent = create_summary_agent()

    crew = Crew(
        agents=[query_agent, search_agent, scraping_agent, summary_agent],
        tasks=[
            create_query_task(query_agent, inputs, dates),
            create_search_task(search_agent, inputs, dates),
            create_scraping_task(scraping_agent, inputs, dates),
            create_summary_task(summary_agent, inputs, dates),
        ],
        process=Process.sequential,
        knowledge_sources=[_build_user_context(inputs, dates)],
        memory=False,
    )
    crew.kickoff(inputs=inputs)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_job_search_crew(inputs: dict) -> JobSearchResult:
    """
    Run the AI job-search workflow and return sanitised, ranked job results.

    Args:
        inputs: Search parameters from the UI.

    Returns:
        JobSearchResult with the path to the ranked-jobs JSON and the job list.
    """
    inputs = _prepare_inputs(inputs)
    dates = _get_date_constraints()
    _clear_previous_outputs()

    search_tool = build_search_engine_tool(
        today=dates["today"],
        cutoff=dates["cutoff"],
        month_year=dates["month_year"],
        country=inputs["country"],
        job_title=inputs["job_title"],
        allowed_domains=inputs["websites_list"],
    )
    scraping_tool = build_web_scraping_tool(
        today=dates["today"],
        cutoff=dates["cutoff"],
        country=inputs["country"],
        allowed_domains=inputs["websites_list"],
    )

    crew_error: str | None = None
    set_llm_provider_override(None)

    try:
        _run_crew_once(inputs, dates, search_tool, scraping_tool)
    except Exception as exc:
        if (
            LLM_FALLBACK_TO_OLLAMA
            and LLM_PROVIDER == "gemini"
            and _is_quota_or_rate_limit_error(exc)
        ):
            first_error = f"{type(exc).__name__}: {exc}"
            try:
                set_llm_provider_override("ollama")
                _run_crew_once(inputs, dates, search_tool, scraping_tool)
                _save_error(
                    f"Gemini failed with quota/rate-limit; retried with Ollama "
                    f"({get_active_llm_provider()}). "
                    f"Original Gemini error: {first_error}"
                )
            except Exception as fallback_exc:
                crew_error = (
                    f"Gemini failed, then Ollama fallback also failed.\n"
                    f"Gemini error: {first_error}\n"
                    f"Ollama error: {type(fallback_exc).__name__}: {fallback_exc}\n"
                    f"Ollama traceback:\n{traceback.format_exc()}"
                )
                _save_error(crew_error)
        else:
            crew_error = f"{type(exc).__name__}: {exc}"
            _save_error(crew_error)
    finally:
        set_llm_provider_override(None)

    # --- Load outputs produced by the crew ---
    jobs_path = os.path.join(OUTPUT_DIR, RANKED_JOBS_FILE)
    jobs = _load_sanitized_jobs(
        jobs_path, inputs["websites_list"], inputs["country"], inputs["job_title"]
    )
    extracted_jobs = _load_extracted_jobs(
        inputs["websites_list"], inputs["country"], inputs["job_title"]
    )
    search_results = _load_search_results(
        inputs["websites_list"], inputs["country"], inputs["job_title"]
    )

    # --- Supplement with direct Tavily results when the crew fell short ---
    if not search_results or len(jobs) < inputs["no_results"]:
        search_results.extend(_direct_tavily_results(inputs, dates))

    candidate_limit = max(inputs["no_results"] * 3, inputs["no_results"] + 4)
    fallback_jobs = jobs_from_search_results(
        search_results,
        candidate_limit,
        country=inputs["country"],
        job_title=inputs["job_title"],
        today=dates["today"],
        cutoff=dates["cutoff"],
        allowed_domains=inputs["websites_list"],
    )

    jobs = _merge_jobs(
        jobs + extracted_jobs,
        fallback_jobs,
        candidate_limit,
        allowed_domains=inputs["websites_list"],
        country=inputs["country"],
        job_title=inputs["job_title"],
    )
    jobs = _filter_reachable_jobs(jobs, inputs["no_results"])
    jobs = _enrich_job_fit_fields(
        jobs, inputs["user_skills"], dates["today"], dates["cutoff"]
    )
    _save_jobs(jobs_path, jobs)

    if crew_error and not jobs:
        raise RuntimeError(
            "The job search returned no results because the CrewAI workflow failed. "
            f"Details saved to {os.path.join(OUTPUT_DIR, ERROR_FILE)}: {crew_error}"
        )

    return {"jobs_json_path": jobs_path, "jobs": jobs}
