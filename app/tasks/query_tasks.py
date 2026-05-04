import os
from crewai import Task
from app.config import (
    DEFAULT_COUNTRY, DEFAULT_JOB_TITLE, DEFAULT_LANGUAGE,
    DEFAULT_TOP_RESULTS, DEFAULT_WEBSITES, OUTPUT_DIR,
)
from app.models.job_model import SearchQuery
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_query_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    job_title = inputs.get("job_title", DEFAULT_JOB_TITLE)
    top_results = inputs.get("no_results", DEFAULT_TOP_RESULTS)
    websites = inputs.get("websites_list", DEFAULT_WEBSITES)
    language = inputs.get("language", DEFAULT_LANGUAGE)

    # Build one example query per website so the agent sees the exact pattern
    example_queries = ", ".join(
        f'site:{w} "{job_title}" {country} job description apply now {dates["month_year"]}'
        for w in (websites if isinstance(websites, list) else [websites])
    )

    return Task(
        description="\n".join([
            f"A job seeker is looking for: {job_title} positions in {country}.",
            f"Target job websites: {websites}.",
            f"TODAY is {dates['today']}. Only search for jobs posted after {dates['cutoff']}.",
            f"Generate exactly {top_results} unique, complete search queries in {language}.",
            "",
            "STRICT RULES — every query MUST:",
            f"  1. Start with a complete site: operator, e.g. site:linkedin.com",
            f'  2. Include the job title in double quotes, e.g. "{job_title}"',
            f"  3. Include the country name: {country}",
            f"  4. End with: {dates['month_year']}",
            "  5. Include one of: apply now | job description | urgent hiring",
            "  6. Be a single complete string — no truncation, no ellipsis",
            "",
            "Spread queries across the target websites — use each site at least once.",
            "Vary role level: remote, hybrid, junior, senior.",
            "Do NOT use salary terms. Do NOT produce partial or cut-off queries.",
            "",
            f"EXAMPLE output (showing the correct shape):\n{example_queries}",
        ]),
        expected_output=(
            "Return ONLY valid TOON. No markdown, no prose, no explanation.\n"
            "Each query must be a fully written string — no truncation.\n\n"
            "Format:\n"
            f"queries[{top_results}]: <query 1>,<query 2>,<query 3>"
        ),
        output_pydantic=SearchQuery,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_1_search_queries.json"),
        agent=agent,
    )