import os

from crewai import Task

from app.config import (
    DEFAULT_COUNTRY,
    DEFAULT_JOB_TITLE,
    DEFAULT_LANGUAGE,
    DEFAULT_TOP_RESULTS,
    DEFAULT_WORK_MODE,
    OUTPUT_DIR,
)
from app.models.job_model import SearchQuery
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_query_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    job_title = inputs.get("job_title", DEFAULT_JOB_TITLE)
    top_results = inputs.get("no_results", DEFAULT_TOP_RESULTS)
    language = inputs.get("language", DEFAULT_LANGUAGE)
    work_mode = inputs.get("work_mode", DEFAULT_WORK_MODE)

    return Task(
        description="\n".join([
            f"A job seeker is looking for: {job_title} positions in {country}.",
            f"Selected work mode: {work_mode}.",
            f"TODAY is {dates['today']}. Only search for jobs posted after {dates['cutoff']}.",
            f"Generate exactly {top_results} unique, complete search queries in {language}.",
            "Do not require or ask for target websites.",
            "Generate broad web queries that can surface official company career pages, ATS pages, and job boards.",
            "Include official/ATS signals: careers, jobs, greenhouse.io, lever.co, workable.com, ashbyhq.com, smartrecruiters.com.",
            "Include search-only board signals when useful: LinkedIn, Bayt, Indeed, Glassdoor.",
            f"Append '{dates['month_year']}' OR 'posted this month' to surface fresh listings.",
            "Respect selected work mode. If work mode is Any, include a mix of remote, hybrid, and onsite phrasing.",
            "Every query should include the job title, country, and one of: apply now | job description | urgent hiring.",
            "Each query should aim for a direct single job posting page, not a listing page.",
            "Do not invent URLs. Only the search tool may return URLs.",
            "Do NOT use salary terms. Do NOT produce partial or cut-off queries.",
        ]),
        expected_output=(
            "Return ONLY valid TOON. No markdown, no prose, no explanation.\n"
            "Each query must be a fully written string, no truncation.\n\n"
            "Format:\n"
            f"queries[{top_results}]: <query 1>,<query 2>,<query 3>"
        ),
        output_pydantic=SearchQuery,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_1_search_queries.json"),
        agent=agent,
    )
