import os

from crewai import Task

from app.config import (
    DEFAULT_COUNTRY,
    DEFAULT_JOB_TITLE,
    DEFAULT_LANGUAGE,
    DEFAULT_TOP_RESULTS,
    DEFAULT_WEBSITES,
    OUTPUT_DIR,
)
from app.models.job_model import SearchQuery
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_query_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    job_title = inputs.get("job_title", DEFAULT_JOB_TITLE)
    top_results = inputs.get("no_results", DEFAULT_TOP_RESULTS)
    websites = inputs.get("websites_list", DEFAULT_WEBSITES)

    return Task(
        description="\n".join([
            f"A job seeker is looking for: {job_title} positions in {country}.",
            f"Target job websites: {websites}.",
            f"Every query MUST include the provided country: {country}.",
            f"TODAY is {dates['today']}. Only search for jobs posted after {dates['cutoff']}.",
            f"Generate up to {top_results} unique, targeted search queries in {DEFAULT_LANGUAGE}.",
            "Every query MUST include one target website using the site: operator.",
            f"Append '{dates['month_year']}' OR 'posted this month' to every query to surface fresh listings.",
            "Include variations: remote, hybrid, junior, senior, urgent hiring, internship.",
            "Each query MUST target a SINGLE job posting page with a unique job ID, not a listing page.",
            "Add 'apply now' OR 'job description' to surface direct postings.",
            "Do NOT generate queries that return aggregator pages or search result pages.",
            "Do NOT include salary terms in the queries.",
        ]),
        expected_output=(
            "Return ONLY valid TOON, no markdown or prose. Example:\n"
            "queries[2]: query 1,query 2"
        ),
        output_pydantic=SearchQuery,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_1_search_queries.json"),
        agent=agent,
    )
