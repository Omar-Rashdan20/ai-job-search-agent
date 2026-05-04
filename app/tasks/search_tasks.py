import os

from crewai import Task

from app.config import DEFAULT_COUNTRY, DEFAULT_WORK_MODE, OUTPUT_DIR, SEARCH_SCORE_THRESHOLD
from app.models.job_model import AllSearchResults
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_search_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    work_mode = inputs.get("work_mode", DEFAULT_WORK_MODE)
    score_floor = max(0.05, float(inputs.get("score_th", SEARCH_SCORE_THRESHOLD)) - 0.15)

    return Task(
        description="\n".join([
            "Run the search engine tool for EVERY query produced in the previous step.",
            f"Country filter: keep only results that mention {country}.",
            f"Work mode filter: respect selected work mode {work_mode}.",
            f"Date filter: TODAY is {dates['today']}. Keep only jobs posted after {dates['cutoff']}.",
            "",
            "URL/source rules:",
            "  - Never invent URLs.",
            "  - Only use URLs returned by the search tool.",
            "  - Remove invalid URLs and duplicate URLs.",
            "  - Keep LinkedIn, Bayt, Indeed, and Glassdoor as search-only results.",
            "  - Scrape only official company or ATS job pages.",
            "  - Reject aggregator pages, search pages, category pages, blogs, and salary-only pages.",
            f"  - Prefer confidence score >= {score_floor:.2f}.",
            "",
            "If no valid URLs are found after all queries, return an empty result list.",
        ]),
        expected_output=(
            "Return ONLY valid TOON. No markdown, no prose.\n\n"
            "If results were found:\n"
            "results[N]{title,url,content,score,search_query,posting_date,source_type,source_note,is_verified_url}:\n"
            "  Job Title,https://site.com/jobs/12345,Short snippet,0.85,original query,2026-05-01,scraped,,true\n\n"
            "If truly nothing was found after running all queries:\n"
            "results[0]{title,url,content,score,search_query,posting_date,source_type,source_note,is_verified_url}:"
        ),
        output_pydantic=AllSearchResults,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_2_search_results.json"),
        agent=agent,
    )
